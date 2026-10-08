from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .project import Studio
from .prompts import STAGE_SPECS, STAGES, PromptPack
from .ssmd import SSMDUnavailableError, check_ssmd, materialize_voice_bindings
from .store import atomic_write_text
from .templates import TemplateLibrary, create_empty_draft
from .workspace import Workspace


def _studio(project: str | None = None) -> Studio:
    if project is None:
        try:
            return Studio.open(".")
        except FileNotFoundError as standalone_error:
            try:
                return Workspace.open(".").resolve_project()
            except FileNotFoundError:
                raise standalone_error

    path = Path(project)
    if project in {".", ".."}:
        try:
            return Studio.open(path)
        except FileNotFoundError:
            return Workspace.open(path).resolve_project()
    if path.exists() or path.is_absolute() or path.parent != Path("."):
        return Studio.open(path)
    return Workspace.open(".").resolve_project(project)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ssmdstudio",
        description="Structured authoring projects for LLM-assisted SSMD creation.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create a new standalone authoring project")
    p_init.add_argument("path")
    p_init.add_argument("--title", required=True)
    p_init.add_argument("--brief", required=True)
    p_init.add_argument("--prompt-pack")
    p_init.add_argument("--id", dest="project_id")
    p_init.add_argument("--recipe", default="funny-story")
    p_init.add_argument("--language", default="en")
    p_init.add_argument("--audience", default="general")
    p_init.add_argument("--tone", default="warm comic")
    p_init.add_argument("--duration-minutes", type=float)
    p_init.add_argument("--constraint", action="append", default=[])
    p_init.add_argument("--allow-nested", action="store_true")

    p_workspace = sub.add_parser("workspace", help="manage an SSMD Studio workspace")
    workspace_sub = p_workspace.add_subparsers(dest="workspace_command", required=True)
    p_workspace_init = workspace_sub.add_parser("init", help="initialize a workspace")
    p_workspace_init.add_argument("path", nargs="?", default=".")

    p_project = sub.add_parser("project", help="manage projects in the current workspace")
    project_sub = p_project.add_subparsers(dest="project_command", required=True)
    p_project_create = project_sub.add_parser("create", help="create a workspace project")
    p_project_create.add_argument("project_id")
    p_project_create.add_argument("--title", required=True)
    p_project_create.add_argument("--brief", required=True)
    p_project_create.add_argument("--prompt-pack")
    p_project_create.add_argument("--recipe", default="funny-story")
    p_project_create.add_argument("--language", default="en")
    p_project_create.add_argument("--audience", default="general")
    p_project_create.add_argument("--tone", default="warm comic")
    p_project_create.add_argument("--duration-minutes", type=float)
    p_project_create.add_argument("--constraint", action="append", default=[])
    project_sub.add_parser("list", help="list workspace projects")
    p_project_use = project_sub.add_parser("use", help="select the active workspace project")
    p_project_use.add_argument("project_id")
    p_project_show = project_sub.add_parser("show", help="show a workspace project")
    p_project_show.add_argument("project_id", nargs="?")

    p_character = sub.add_parser("character", help="manage characters")
    character_sub = p_character.add_subparsers(dest="character_command", required=True)
    p_character_add = character_sub.add_parser("add")
    p_character_add.add_argument("id")
    p_character_add.add_argument("--project")
    p_character_add.add_argument("--name", required=True)
    p_character_add.add_argument("--role", required=True)
    p_character_add.add_argument("--description", required=True)
    p_character_add.add_argument("--trait", action="append", default=[])
    p_character_add.add_argument("--goal", action="append", default=[])
    p_character_add.add_argument("--voice-notes", default="")
    p_character_add.add_argument("--ssmd-role")
    p_character_add.add_argument("--constraint", action="append", default=[])

    p_character_import = character_sub.add_parser(
        "import", help="import model-generated character YAML"
    )
    p_character_import.add_argument("file")
    p_character_import.add_argument("--project")
    p_character_import.add_argument("--merge", action="store_true")

    p_scene = sub.add_parser("scene", help="manage scenes")
    scene_sub = p_scene.add_subparsers(dest="scene_command", required=True)
    p_scene_add = scene_sub.add_parser("add")
    p_scene_add.add_argument("id")
    p_scene_add.add_argument("--project")
    p_scene_add.add_argument("--title", required=True)
    p_scene_add.add_argument("--purpose", required=True)
    p_scene_add.add_argument("--character", action="append", default=[])
    p_scene_add.add_argument("--event", action="append", default=[])
    p_scene_add.add_argument("--comic-function", default="")
    p_scene_add.add_argument("--constraint", action="append", default=[])
    p_scene_add.add_argument("--locked", action="store_true")

    p_scene_import = scene_sub.add_parser("import", help="import model-generated scene YAML")
    p_scene_import.add_argument("file")
    p_scene_import.add_argument("--project")
    p_scene_import.add_argument("--merge", action="store_true")

    p_feedback = sub.add_parser("feedback", help="manage human feedback")
    feedback_sub = p_feedback.add_subparsers(dest="feedback_command", required=True)
    p_feedback_add = feedback_sub.add_parser("add")
    p_feedback_add.add_argument("id")
    p_feedback_add.add_argument("--project")
    p_feedback_add.add_argument("--instruction", action="append", required=True)
    p_feedback_add.add_argument("--scope", action="append", default=[])
    p_feedback_add.add_argument("--lock", action="append", default=[])

    p_draft = sub.add_parser("draft", help="manage the current prose draft")
    draft_sub = p_draft.add_subparsers(dest="draft_command", required=True)
    p_draft_set = draft_sub.add_parser("set")
    p_draft_set.add_argument("file")
    p_draft_set.add_argument("--project")

    p_draft_new = draft_sub.add_parser(
        "new", help="create a standalone empty or template-based draft"
    )
    p_draft_new.add_argument("--output", required=True)
    p_draft_new.add_argument("--template")
    p_draft_new.add_argument("--force", action="store_true")

    p_template = sub.add_parser("template", help="manage standalone SSMD starter templates")
    template_sub = p_template.add_subparsers(dest="template_command", required=True)
    p_template_path = template_sub.add_parser(
        "path", help="show the template library or a template path"
    )
    p_template_path.add_argument("name", nargs="?")
    p_template_list = template_sub.add_parser("list", help="list user templates")
    p_template_list.add_argument("--json", action="store_true")
    p_template_show = template_sub.add_parser("show", help="print a template")
    p_template_show.add_argument("name")
    p_template_add = template_sub.add_parser("add", help="add a user template")
    p_template_add.add_argument("name")
    p_template_add.add_argument("--file", required=True)
    p_template_add.add_argument("--force", action="store_true")
    p_template_remove = template_sub.add_parser("remove", help="remove a user template")
    p_template_remove.add_argument("name")
    p_template_reset = template_sub.add_parser("reset", help="restore built-in template defaults")
    p_template_reset.add_argument("name", nargs="?")
    p_template_reset.add_argument("--all", action="store_true")
    p_template_validate = template_sub.add_parser("validate", help="validate one or all templates")
    p_template_validate.add_argument("name", nargs="?")
    p_template_validate.add_argument("--all", action="store_true")
    p_template_validate.add_argument("--roundtrip", action="store_true")
    p_template_validate.add_argument("--json", action="store_true")
    p_template_use = template_sub.add_parser("use", help="copy a template to an output file")
    p_template_use.add_argument("name")
    p_template_use.add_argument("--output", required=True)
    p_template_use.add_argument("--force", action="store_true")

    p_ssmd = sub.add_parser("ssmd", help="author and validate standalone SSMD files")
    ssmd_sub = p_ssmd.add_subparsers(dest="ssmd_command", required=True)
    p_ssmd_bind = ssmd_sub.add_parser("bind", help="materialize explicit provider voice bindings")
    p_ssmd_bind.add_argument("file")
    p_ssmd_bind.add_argument("--provider", required=True)
    p_ssmd_bind.add_argument("--voice-bind", action="append", required=True, metavar="ROLE=VOICE")
    p_ssmd_bind.add_argument("--output")
    p_ssmd_bind.add_argument("--in-place", action="store_true")
    p_ssmd_bind.add_argument("--force", action="store_true")
    p_ssmd_bind.add_argument("--json", action="store_true")

    p_ssmd_lint = ssmd_sub.add_parser("lint", help="lint SSMD syntax and optionally roundtrip")
    p_ssmd_lint.add_argument("file")
    p_ssmd_lint.add_argument("--roundtrip", action="store_true")
    p_ssmd_lint.add_argument("--fail-on-warn", action="store_true")
    p_ssmd_lint.add_argument("--config")
    p_ssmd_lint.add_argument("--dialect", choices=("auto", "0.8", "0.9"), default="0.9")
    p_ssmd_lint.add_argument("--json", action="store_true")
    p_output = sub.add_parser("output", help="manage the current generated SSMD")
    output_sub = p_output.add_subparsers(dest="output_command", required=True)
    p_output_set = output_sub.add_parser("set")
    p_output_set.add_argument("file")
    p_output_set.add_argument("--project")
    p_output_validate = output_sub.add_parser("validate", help="validate the stored SSMD output")
    p_output_validate.add_argument("--project")

    p_prompt = sub.add_parser("prompt", help="compile prompts from stored project state")
    prompt_sub = p_prompt.add_subparsers(dest="prompt_command", required=True)
    p_prompt_pack = prompt_sub.add_parser("pack", help="manage workflow prompt packs")
    prompt_pack_sub = p_prompt_pack.add_subparsers(dest="prompt_pack_command", required=True)
    p_prompt_pack_install = prompt_pack_sub.add_parser(
        "install", help="install a workflow prompt pack"
    )
    p_prompt_pack_install.add_argument("path")
    p_prompt_pack_install.add_argument("--project")
    p_prompt_pack_install.add_argument("--replace", action="store_true")
    p_prompt_pack_path = prompt_pack_sub.add_parser(
        "path", help="show the project prompt directory"
    )
    p_prompt_pack_path.add_argument("--project")
    p_prompt_pack_validate = prompt_pack_sub.add_parser(
        "validate", help="validate a workflow prompt pack"
    )
    p_prompt_pack_validate.add_argument("path")
    p_prompt_build = prompt_sub.add_parser("build")
    p_prompt_build.add_argument("stage", choices=STAGES)
    p_prompt_build.add_argument("--project")
    p_prompt_build.add_argument("--output")
    p_prompt_build.add_argument("--save", action="store_true")

    p_prompt_next = prompt_sub.add_parser("next", help="build a prompt for the next stage")
    p_prompt_next.add_argument("--project")
    p_prompt_next.add_argument("--output")
    p_prompt_next.add_argument("--save", action="store_true")

    p_next = sub.add_parser("next", help="show the next authoring action")
    p_next.add_argument("--project")

    p_apply = sub.add_parser("apply", help="apply a model-generated artifact")
    p_apply.add_argument("file")
    p_apply.add_argument("--project")
    p_apply.add_argument("--stage", choices=STAGES)

    p_status = sub.add_parser("status", help="show authoring state and prompt staleness")
    p_status.add_argument("--project")
    p_status.add_argument("--json", action="store_true")
    return parser


def _write_prompt(studio: Studio, stage: str, prompt: str, output: str | None) -> None:
    if output:
        atomic_write_text(Path(output), prompt)
    else:
        sys.stdout.write(prompt)
    run_dir = studio.save_prompt_run(stage, prompt)
    artifact = STAGE_SPECS[stage].expected_artifact(studio.config.id)
    print(f"stage: {stage}", file=sys.stderr)
    print(f"saved prompt: {run_dir.relative_to(studio.root) / 'prompt.md'}", file=sys.stderr)
    print(f"expected artifact: {artifact}", file=sys.stderr)
    print(f"apply with: ssmdstudio apply {artifact}", file=sys.stderr)


def _show_next(studio: Studio) -> None:
    stage = studio.next_stage()
    print(f"project: {studio.config.id}")
    if stage is None:
        print("project complete")
        print("final stored output: output/current.ssmd.md")
        print(f"export name: {studio.config.id}.ssmd.md")
        return

    print(f"next stage: {stage}")
    latest = next(
        (run for run in reversed(studio.run_statuses()) if run["stage"] == stage),
        None,
    )
    if latest is None:
        print("prompt: not generated yet")
    else:
        print(f"prompt: runs/{latest['run']}/prompt.md")
    artifact = STAGE_SPECS[stage].expected_artifact(studio.config.id)
    print(f"expected artifact: {artifact}")
    print("\nrun:")
    print("  ssmdstudio prompt next --save")
    print("\nafter the LLM returns the file:")
    print(f"  ssmdstudio apply {artifact}")


def _parse_voice_bindings(values: list[str]) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for value in values:
        role, separator, voice = value.partition("=")
        if not separator or not role or not voice:
            raise ValueError("--voice-bind values must use ROLE=VOICE with non-empty names")
        if role in bindings and bindings[role] != voice:
            raise ValueError(f"conflicting --voice-bind values were supplied for role {role!r}")
        bindings[role] = voice
    return bindings


def _run_ssmd_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.ssmd_command == "bind":
        result = materialize_voice_bindings(
            Path(args.file),
            _parse_voice_bindings(args.voice_bind),
            provider=args.provider,
            output=Path(args.output) if args.output is not None else None,
            in_place=args.in_place,
            force=args.force,
        )
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False))
        else:
            print(result.output)
        return
    if args.ssmd_command == "lint":
        result = check_ssmd(
            Path(args.file),
            roundtrip=args.roundtrip,
            fail_on_warn=args.fail_on_warn,
            config=Path(args.config) if args.config is not None else None,
            dialect=args.dialect,
        )
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False))
        else:
            print(f"source: {result.source}")
            print(f"validation: {result.state}")
            if result.state == "unavailable":
                print(result.message or "SSMD validation is unavailable", file=sys.stderr)
            elif result.ok:
                print("syntax lint: passed")
                if result.roundtrip:
                    print("round-trip lint: passed")
            else:
                for diagnostic in result.diagnostics:
                    print(
                        f"{diagnostic.severity}: {diagnostic.message} ({diagnostic.code})",
                        file=sys.stderr,
                    )
                if result.stderr:
                    sys.stderr.write(result.stderr)
        if not result.ok:
            raise SystemExit(1)
        return
    parser.error("unsupported SSMD command")


def _run_template_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    library = TemplateLibrary()
    command = args.template_command
    if command == "path":
        print(library.path(args.name) if args.name else library.directory())
        return
    if command == "list":
        names = library.list()
        if args.json:
            print(
                json.dumps(
                    {
                        "schema": "ssmdstudio.templates.v1",
                        "directory": str(library.directory()),
                        "templates": list(names),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            for name in names:
                print(name)
        return
    if command == "show":
        sys.stdout.write(library.show(args.name))
        return
    if command == "add":
        print(library.add(args.name, source=Path(args.file), force=args.force))
        return
    if command == "remove":
        path = library.path(args.name)
        library.remove(args.name)
        print(f"removed {path}")
        return
    if command == "reset":
        for path in library.reset(args.name, all=args.all):
            print(path)
        return
    if command == "use":
        print(library.use(args.name, output=Path(args.output), force=args.force))
        return
    if command == "validate":
        if args.all and args.name is not None:
            raise ValueError("template validate accepts a name or --all, not both")
        if not args.all and args.name is None:
            raise ValueError("template validate requires NAME or --all")
        names = library.list() if args.all else (args.name,)
        results = [library.validate(name, roundtrip=args.roundtrip) for name in names]
        payloads = [result.to_dict() for result in results]
        ok = all(result.ok for result in results)
        if args.json:
            print(
                json.dumps(
                    {
                        "schema": "ssmdstudio.template-validation.v1",
                        "ok": ok,
                        "templates": payloads,
                    },
                    ensure_ascii=False,
                )
            )
        else:
            for result in results:
                print(f"{result.source}: {result.state}")
                for diagnostic in result.diagnostics:
                    print(f"{diagnostic.severity}: {diagnostic.message}", file=sys.stderr)
        if not ok:
            raise SystemExit(1)
        return
    parser.error("unsupported template command")


def _run_draft_new(args: argparse.Namespace) -> None:
    if args.template:
        output = TemplateLibrary().use(args.template, output=Path(args.output), force=args.force)
    else:
        output = create_empty_draft(Path(args.output), force=args.force)
    print(output)


def main(argv: list[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "ssmd":
            _run_ssmd_command(args, parser)
            return

        if args.command == "template":
            _run_template_command(args, parser)
            return

        if args.command == "draft" and args.draft_command == "new":
            _run_draft_new(args)
            return

        if args.command == "init":
            studio = Studio.init(
                args.path,
                title=args.title,
                brief=args.brief,
                project_id=args.project_id,
                recipe=args.recipe,
                language=args.language,
                audience=args.audience,
                tone=args.tone,
                duration_minutes=args.duration_minutes,
                constraints=args.constraint,
                allow_nested=args.allow_nested,
                prompt_pack=args.prompt_pack,
            )
            print(studio.root)
            return

        if args.command == "workspace" and args.workspace_command == "init":
            print(Workspace.init(args.path).root)
            return

        if args.command == "project" and args.project_command == "create":
            workspace = Workspace.open()
            studio = workspace.create_project(
                args.project_id,
                title=args.title,
                brief=args.brief,
                recipe=args.recipe,
                language=args.language,
                audience=args.audience,
                tone=args.tone,
                duration_minutes=args.duration_minutes,
                constraints=args.constraint,
                prompt_pack=args.prompt_pack,
            )
            print(studio.root)
            return

        if args.command == "project" and args.project_command == "list":
            workspace = Workspace.open()
            projects = workspace.list_projects()
            if not projects:
                print("no projects")
                return
            for studio in projects:
                active = "*" if studio.config.id == workspace.active_project_id else " "
                print(f"{active} {studio.config.id}\t{studio.config.title}")
            return

        if args.command == "project" and args.project_command == "use":
            studio = Workspace.open().use_project(args.project_id)
            print(f"active project: {studio.config.id}")
            return

        if args.command == "project" and args.project_command == "show":
            studio, active = Workspace.open().show_project(args.project_id)
            print(f"project: {studio.config.id}{' (active)' if active else ''}")
            print(f"root: {studio.root}")
            print(f"title: {studio.config.title}")
            print(f"brief: {studio.config.brief}")
            print(f"next stage: {studio.next_stage() or 'complete'}")
            return

        if args.command == "character" and args.character_command == "add":
            character = _studio(args.project).add_character(
                id=args.id,
                name=args.name,
                role=args.role,
                description=args.description,
                traits=args.trait,
                goals=args.goal,
                voice_notes=args.voice_notes,
                ssmd_role=args.ssmd_role,
                constraints=args.constraint,
            )
            print(character.id)
            return

        if args.command == "character" and args.character_command == "import":
            imported = _studio(args.project).import_characters(args.file, merge=args.merge)
            for character in imported:
                print(character.id)
            return

        if args.command == "scene" and args.scene_command == "add":
            scene = _studio(args.project).add_scene(
                id=args.id,
                title=args.title,
                purpose=args.purpose,
                characters=args.character,
                events=args.event,
                comic_function=args.comic_function,
                constraints=args.constraint,
                locked=args.locked,
            )
            print(scene.id)
            return

        if args.command == "scene" and args.scene_command == "import":
            imported = _studio(args.project).import_scenes(args.file, merge=args.merge)
            for scene in imported:
                print(scene.id)
            return

        if args.command == "feedback" and args.feedback_command == "add":
            feedback = _studio(args.project).add_feedback(
                id=args.id,
                instructions=args.instruction,
                scope=args.scope,
                locked=args.lock,
            )
            print(feedback.id)
            return

        if args.command == "draft" and args.draft_command == "set":
            print(_studio(args.project).set_draft(args.file))
            return

        if args.command == "output" and args.output_command == "set":
            print(_studio(args.project).set_output(args.file))
            return

        if args.command == "output" and args.output_command == "validate":
            result = _studio(args.project).validate_output()
            print(f"SSMD stored: {result['path']}")
            print(f"validation: {result['state']}")
            if result["state"] == "unavailable":
                print(f"detail: {result['message']}")
                return
            if result["state"] == "passed":
                print("syntax lint: passed")
                print("round-trip lint: passed")
                return
            if result["stdout"]:
                sys.stdout.write(result["stdout"])
            if result["stderr"]:
                sys.stderr.write(result["stderr"])
            parser.exit(1, "validation failed\n")

        if args.command == "prompt" and args.prompt_command == "pack":
            if args.prompt_pack_command == "install":
                studio = _studio(args.project)
                print(studio.install_prompt_pack(args.path, replace=args.replace))
                return
            if args.prompt_pack_command == "path":
                print(_studio(args.project).prompt_pack_path)
                return
            if args.prompt_pack_command == "validate":
                pack = PromptPack.open(args.path)
                print(f"valid workflow prompt pack: {pack.id}")
                return

        if args.command == "prompt" and args.prompt_command == "build":
            studio = _studio(args.project)
            prompt = studio.build_prompt(args.stage)
            if args.save:
                _write_prompt(studio, args.stage, prompt, args.output)
            elif args.output:
                atomic_write_text(Path(args.output), prompt)
            else:
                sys.stdout.write(prompt)
            return

        if args.command == "prompt" and args.prompt_command == "next":
            studio = _studio(args.project)
            stage = studio.next_stage()
            if stage is None:
                raise ValueError("project is complete; there is no next prompt")
            prompt = studio.build_prompt(stage)
            if args.save:
                _write_prompt(studio, stage, prompt, args.output)
            elif args.output:
                atomic_write_text(Path(args.output), prompt)
            else:
                sys.stdout.write(prompt)
            return

        if args.command == "next":
            _show_next(_studio(args.project))
            return

        if args.command == "apply":
            studio = _studio(args.project)
            result = studio.apply(args.file, stage=args.stage)
            print(f"stage: {result['stage']}")
            print(f"applied: {result['expected_artifact']}")
            if result["changed_files"]:
                print("changed files:")
                for path in result["changed_files"]:
                    print(f"  {path}")
            if result["run"]:
                print(f"response: runs/{result['run']}/{result['response_file']}")
            return

        if args.command == "status":
            status = _studio(args.project).status()
            if args.json:
                print(json.dumps(status, indent=2))
                return
            print(f"project: {status['project']}")
            print(f"root: {status['root']}")
            print(f"recipe: {status['recipe']}")
            pack = status["prompt_pack"]
            print(f"prompt pack: {pack['id'] or 'not installed'}")
            print(f"prompt path: {pack['path']}/")
            print(f"characters: {status['characters']}")
            print(f"scenes: {status['scenes']}")
            print(f"open feedback: {status['open_feedback']}")
            print(f"draft: {'yes' if status['draft'] else 'no'}")
            print(f"output: {'yes' if status['output'] else 'no'}")
            print(f"validation: {status['validation']}")
            print(f"next stage: {status['next_stage'] or 'complete'}")
            if status["runs"]:
                print("runs:")
                for run in status["runs"]:
                    print(f"  {run['run']}  {run['stage']}  {run['state']}")
            return

        parser.error("unsupported command")
    except (OSError, TypeError, ValueError, SSMDUnavailableError) as exc:
        if getattr(args, "json", False):
            print(
                json.dumps(
                    {
                        "schema": "ssmdstudio.error.v1",
                        "ok": False,
                        "error": {"type": type(exc).__name__, "message": str(exc)},
                    },
                    ensure_ascii=False,
                )
            )
            raise SystemExit(2) from exc
        parser.exit(2, f"error: {exc}\n")

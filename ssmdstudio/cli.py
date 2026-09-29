from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib.resources import as_file, files
from pathlib import Path

from . import __version__
from .project import Studio
from .prompts import STAGES, STAGE_SPECS
from .store import atomic_write_text
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

    p_skill = sub.add_parser("skill", help="show or install the bundled harness skill")
    skill_sub = p_skill.add_subparsers(dest="skill_command", required=True)
    skill_sub.add_parser("show", help="print the bundled skill")
    skill_sub.add_parser("path", help="print the bundled skill path")
    p_skill_install = skill_sub.add_parser(
        "install", help="install the skill into a target directory"
    )
    p_skill_install.add_argument("target")

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

    p_output = sub.add_parser("output", help="manage the current generated SSMD")
    output_sub = p_output.add_subparsers(dest="output_command", required=True)
    p_output_set = output_sub.add_parser("set")
    p_output_set.add_argument("file")
    p_output_set.add_argument("--project")
    p_output_validate = output_sub.add_parser("validate", help="validate the stored SSMD output")
    p_output_validate.add_argument("--project")

    p_prompt = sub.add_parser("prompt", help="compile prompts from stored project state")
    prompt_sub = p_prompt.add_subparsers(dest="prompt_command", required=True)
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


def main(argv: list[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)

    try:
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
            )
            print(studio.root)
            return

        if args.command == "workspace" and args.workspace_command == "init":
            print(Workspace.init(args.path).root)
            return

        if args.command == "skill":
            skill = files("ssmdstudio").joinpath("resources", "skills", "ssmdstudio", "SKILL.md")
            if args.skill_command == "show":
                sys.stdout.write(skill.read_text(encoding="utf-8"))
                return
            if args.skill_command == "path":
                with as_file(skill) as skill_path:
                    print(skill_path)
                return
            if args.skill_command == "install":
                target = Path(args.target)
                target.mkdir(parents=True, exist_ok=True)
                installed = target / "SKILL.md"
                with as_file(skill) as skill_path:
                    shutil.copyfile(skill_path, installed)
                print(installed)
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
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")

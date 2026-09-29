from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .models import SSMDRole
from .project import Studio
from .store import atomic_write_text


def _studio(path: str) -> Studio:
    return Studio.open(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ssmdstudio",
        description="Structured authoring projects for LLM-assisted SSMD creation.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create a new authoring project")
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

    p_character = sub.add_parser("character", help="manage characters")
    character_sub = p_character.add_subparsers(dest="character_command", required=True)
    p_character_add = character_sub.add_parser("add")
    p_character_add.add_argument("id")
    p_character_add.add_argument("--project", default=".")
    p_character_add.add_argument("--name", required=True)
    p_character_add.add_argument("--role", required=True)
    p_character_add.add_argument("--description", required=True)
    p_character_add.add_argument("--trait", action="append", default=[])
    p_character_add.add_argument("--goal", action="append", default=[])
    p_character_add.add_argument("--voice-notes", default="")
    p_character_add.add_argument(
        "--ssmd-role",
        choices=["narrator", "host", "guest", "analyst"],
    )
    p_character_add.add_argument("--constraint", action="append", default=[])

    p_character_import = character_sub.add_parser(
        "import", help="import model-generated character YAML"
    )
    p_character_import.add_argument("file")
    p_character_import.add_argument("--project", default=".")

    p_scene = sub.add_parser("scene", help="manage scenes")
    scene_sub = p_scene.add_subparsers(dest="scene_command", required=True)
    p_scene_add = scene_sub.add_parser("add")
    p_scene_add.add_argument("id")
    p_scene_add.add_argument("--project", default=".")
    p_scene_add.add_argument("--title", required=True)
    p_scene_add.add_argument("--purpose", required=True)
    p_scene_add.add_argument("--character", action="append", default=[])
    p_scene_add.add_argument("--event", action="append", default=[])
    p_scene_add.add_argument("--comic-function", default="")
    p_scene_add.add_argument("--constraint", action="append", default=[])
    p_scene_add.add_argument("--locked", action="store_true")

    p_scene_import = scene_sub.add_parser("import", help="import model-generated scene YAML")
    p_scene_import.add_argument("file")
    p_scene_import.add_argument("--project", default=".")

    p_feedback = sub.add_parser("feedback", help="manage human feedback")
    feedback_sub = p_feedback.add_subparsers(dest="feedback_command", required=True)
    p_feedback_add = feedback_sub.add_parser("add")
    p_feedback_add.add_argument("id")
    p_feedback_add.add_argument("--project", default=".")
    p_feedback_add.add_argument("--instruction", action="append", required=True)
    p_feedback_add.add_argument("--scope", action="append", default=[])
    p_feedback_add.add_argument("--lock", action="append", default=[])

    p_draft = sub.add_parser("draft", help="manage the current prose draft")
    draft_sub = p_draft.add_subparsers(dest="draft_command", required=True)
    p_draft_set = draft_sub.add_parser("set")
    p_draft_set.add_argument("file")
    p_draft_set.add_argument("--project", default=".")

    p_output = sub.add_parser("output", help="manage the current generated SSMD")
    output_sub = p_output.add_subparsers(dest="output_command", required=True)
    p_output_set = output_sub.add_parser("set")
    p_output_set.add_argument("file")
    p_output_set.add_argument("--project", default=".")

    p_prompt = sub.add_parser("prompt", help="compile prompts from stored project state")
    prompt_sub = p_prompt.add_subparsers(dest="prompt_command", required=True)
    p_prompt_build = prompt_sub.add_parser("build")
    p_prompt_build.add_argument(
        "stage",
        choices=["characters", "scenes", "draft", "revise", "ssmd"],
    )
    p_prompt_build.add_argument("--project", default=".")
    p_prompt_build.add_argument("--output")
    p_prompt_build.add_argument("--save", action="store_true")

    p_status = sub.add_parser("status", help="show authoring state and prompt staleness")
    p_status.add_argument("--project", default=".")
    p_status.add_argument("--json", action="store_true")

    return parser


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
            )
            print(studio.root)
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
            imported = _studio(args.project).import_characters(args.file)
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
            imported = _studio(args.project).import_scenes(args.file)
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

        if args.command == "prompt" and args.prompt_command == "build":
            studio = _studio(args.project)
            prompt = studio.build_prompt(args.stage)
            if args.output:
                atomic_write_text(Path(args.output), prompt)
            else:
                sys.stdout.write(prompt)
            if args.save:
                run_dir = studio.save_prompt_run(args.stage, prompt)
                print(f"saved run: {run_dir}", file=sys.stderr)
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
            if status["runs"]:
                print("runs:")
                for run in status["runs"]:
                    print(f"  {run['run']}  {run['stage']}  {run['state']}")
            return

        parser.error("unsupported command")
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")

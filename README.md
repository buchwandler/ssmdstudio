# ssmdstudio

`ssmdstudio` is a small Python framework and CLI for building structured authoring projects
that an LLM or harness can turn into SSMD. Characters, scenes, feedback, prompts, drafts, and
output live in a filesystem-backed project store. The store is the source of truth, not chat
history.

## Design boundary

SSMDStudio's Python package stores authoring state, validates project data, assembles prompt context, renders project-owned workflow templates, applies returned artifacts, and optionally validates final SSMD. It contains no prompt prose or Agent Skill content. Prompt packs and skills are repository/user data outside the Python wheel; a project's installed workflow pack is copied into `PROJECT/prompts/` and can be edited independently of Python releases.

## Prompt families

- `prompts/workflows/funny-story/` is a structured workflow pack. Its five stage templates receive project context and produce artifacts consumed by SSMDStudio; the final `ssmd.md` converts an approved locked draft.
- `prompts/standalone/ssmd/` contains 15 self-contained authoring guides for direct use with a generic LLM. They create SSMD documents without the structured project workflow.

The standalone creative `funny-story.md` and the workflow conversion `ssmd.md` are different prompts. Readio runtime `.ssmd` templates are not LLM prompts and are not included in the catalog. See `prompts/README.md` and `prompts/standalone/README.md` for details.

## Standalone projects and workspaces

A standalone project remains the simplest option and keeps the original flat layout:

```bash
ssmdstudio init picnic --title "The Picnic Problem" --brief \
  "Anna prepares a picnic while a curious dog keeps stealing napkins." \
  --prompt-pack /path/to/ssmdstudio/prompts/workflows/funny-story
cd picnic
ssmdstudio status
```

A workspace is an optional collection for multiple stories. It keeps projects as siblings under
`projects/`, with workspace selection stored in `.ssmdstudio/workspace.yaml`:

```text
my-stories/
├── .ssmdstudio/workspace.yaml
└── projects/
    ├── printer-story/
    └── picnic/
```

Create and select workspace projects with:

```bash
ssmdstudio workspace init
ssmdstudio project create printer-story \
  --title "Funny printer story" \
  --brief "A person tries to print while the printer develops a bureaucratic personality." \
  --prompt-pack /path/to/ssmdstudio/prompts/workflows/funny-story
ssmdstudio project list
ssmdstudio project use printer-story
ssmdstudio project show
```

The active project is a convenience. Scriptable commands can use `--project ID` or a project path to select a project explicitly. Existing standalone directories continue to work with `Studio.open(PATH)` and the original `ssmdstudio init PATH` command. Nested projects are refused by default; `--allow-nested` is an explicit override.

Prompt packs are optional for project-state operations but required for prompt compilation. Include `--prompt-pack` at creation or install one later with `ssmdstudio prompt pack install PATH`.

## Two authoring workflows

Both workflows use the same project store, prompt builders, and `apply` command.

### Manual / copy prompt

Use this when the user wants to run prompts in another chat or model UI. This mode does not ask
the harness to spend generation tokens:

```bash
ssmdstudio next
ssmdstudio prompt next --save
# Run the saved prompt elsewhere and save the response under its requested filename.
ssmdstudio apply characters.yaml
ssmdstudio next
ssmdstudio prompt next --save
ssmdstudio apply scenes.yaml
ssmdstudio prompt next --save
ssmdstudio apply draft.md
ssmdstudio prompt next --save
ssmdstudio apply printer-story.ssmd.md
```

`next` reports the stage, expected artifact, saved prompt when available, and the next command.
Every prompt requests a downloadable file when supported, or complete raw file contents otherwise.
The expected filenames are `characters.yaml`, `scenes.yaml`, `draft.md`, and
`<project-id>.ssmd.md`.

### Harness / skill

Use this when the user asks a harness to create the story. The harness runs the project's installed prompt files and applies responses through SSMD Studio. Pause for approval after the character and scene checkpoints, present the draft for review, record requested edits as feedback, and use targeted revisions before converting approved prose to SSMD.

The canonical Agent Skill is repository data at `skill/ssmdstudio/SKILL.md`; it is not bundled in the Python wheel. SSMDStudio does not provide `skill show`, `skill path`, or `skill install` commands. The harness should load the skill from the repository or user-managed skill location, and should use the project's own prompt files rather than assuming package-owned templates.

## Prompt-pack setup

Select a workflow pack when creating a project:

```bash
ssmdstudio init picnic --title "The Picnic Problem" --brief \
  "Anna prepares a picnic while a curious dog keeps stealing napkins." \
  --prompt-pack /path/to/ssmdstudio/prompts/workflows/funny-story
```

`--prompt-pack` is optional: project state, validation, and artifact operations work without prompt data, but `prompt build` and `prompt next` report a clear error until a pack is installed. For an existing project, run installation from its directory or pass `--project ID/PATH`:

```bash
ssmdstudio prompt pack validate /path/to/prompt-pack
ssmdstudio prompt pack install /path/to/ssmdstudio/prompts/workflows/funny-story
ssmdstudio prompt pack path
# Use --replace to explicitly replace the project's installed pack.
```

The installed copy is `PROJECT/prompts/`; edits to its manifest or stage template affect prompt-run staleness. `status` reports the installed pack id and path.

## Prompt and artifact workflow

`ssmdstudio prompt build STAGE --save` remains available for explicit stage selection. The guided
alternative is:

```bash
ssmdstudio next
ssmdstudio prompt next --save
ssmdstudio apply FILE
```

`apply` infers the waiting stage from stored state, checks the expected filename and file format,
updates the store, and records the response in the latest matching prompt run. Use `--stage` only
when explicitly overriding the inferred stage. Character and scene imports replace the complete
stored set atomically by default. The lower-level commands accept `--merge` for preserving
unspecified existing entities.

The workflow proceeds through characters, scenes, draft, optional revise stages for open
feedback, SSMD conversion, and completion. A draft without open feedback is considered approved
for the MVP. The SSMD conversion prompt treats the approved draft as locked wording and uses a
compact speaker map, including an explicit narrator role when present.

## Validation

Storing SSMD and validating SSMD are separate operations. `ssmdstudio output validate` uses the
installed `ssmd` runtime when available and reports passed, failed, or unavailable. SSMD Studio
does not claim validation when the runtime did not run, and it does not add `ssmd` as a required
dependency.
The result is stored at `output/validation.json` and tied to a content hash. `status` shows `stale` if the SSMD changes after validation.

## Project store

A standalone project contains plain YAML and Markdown:

```text
project.yaml
prompts/ (optional project-owned workflow pack)
characters/
scenes/
feedback/
drafts/current.md
output/current.ssmd.md
output/validation.json
runs/
```

Prompt runs store the generated prompt, stage-template provenance (pack id, schema, template path, and SHA-256), and a fingerprint of project state plus the prompt pack manifest and stage template. `ssmdstudio status` reports inventory, installed prompt pack, next stage, prompt staleness, and current validation state.

## Python API

```python
from ssmdstudio import Studio, Workspace

workspace = Workspace.open("my-stories")
studio = workspace.resolve_project("printer-story")
# This project must already have an installed workflow pack.
prompt = studio.build_prompt("characters")
print(prompt)
```

For Python callers, `studio.install_prompt_pack(PATH)` installs external pack data into the project, and `studio.prompt_pack_path` points to its editable copy.

For a standalone project, use `Studio.open("picnic")`. The Python API and CLI share the same
filesystem-backed state.

## Development

There is intentionally no `src/` directory. Versioning is dynamic through `setuptools-scm`.

```bash
python -m pip install -e ".[dev]"
pytest -q
ruff check .
python -m build --wheel
```

## Non-goals

SSMD Studio does not include model-provider clients, a database, a GUI, audio rendering, concrete
provider voice IDs, semantic merge machinery, or background jobs. The SSMD runtime owns final
validation, binding, and rendering.

# ssmdstudio

`ssmdstudio` is a small Python framework and CLI for building structured authoring projects
that an LLM or harness can turn into SSMD. Characters, scenes, feedback, prompts, drafts, and
output live in a filesystem-backed project store. The store is the source of truth, not chat
history.

## Design boundary

SSMDStudio's Python package stores project authoring state, manages user-scoped SSMD starter documents, validates project data, assembles prompt context, renders project-owned workflow templates, applies returned artifacts, and optionally validates final SSMD. It packages only first-party SSMD starter documents; workflow prompt packs and the Agent Skill remain repository/user data outside the wheel. A project's installed workflow pack is copied into `PROJECT/prompts/` and can be edited independently of Python releases. The optional `authoring` extra provides `ssmd` for standalone lint, roundtrip, binding, and template validation; core project operations do not require it.

## Prompt families

- `prompts/workflows/funny-story/` is a structured workflow pack. Its five stage templates receive project context and produce artifacts consumed by SSMDStudio; the final `ssmd.md` converts an approved locked draft.
- Three first-party `.ssmd` starter documents are packaged under `ssmdstudio/resources/templates/` and exposed through `ssmdstudio template`; they are editable documents, not LLM prompts.
- `prompts/standalone/ssmd/` contains 15 self-contained authoring guides for direct use with a generic LLM. They create SSMD documents without the structured project workflow.

The standalone creative `funny-story.md` and the workflow conversion `ssmd.md` are different prompts. Readio runtime `.ssmd` templates are separate from Studio-owned starter documents; neither kind of starter document is an LLM prompt or part of the prompt catalog. See `prompts/README.md` and `prompts/standalone/README.md` for details.

## Standalone SSMD authoring

Standalone authoring is audio-first: each SSMD file should make sense when heard without source layout, markup, or speaker labels. Give different recurring speakers distinct, stable symbolic roles; never use pitch, rate, volume, or other acoustic qualities as speaker identity. Use spoken context and attribution to clarify turns, preserve source meaning, and give the requested arc a useful ending. This file-oriented workflow needs no Studio project, model provider, or audio renderer. Built-in starters are installed in the user template library before use; `reset --all` restores the packaged starter names and overwrites local edits to those names, while custom templates are preserved.

```bash
ssmdstudio template reset --all
ssmdstudio template list
ssmdstudio template use podcast --output episode.ssmd.md
# Or create a blank file, or start from a library template:
ssmdstudio draft new --output notes.ssmd.md
ssmdstudio draft new --output another-episode.ssmd.md --template podcast

# Optional structural validation, roundtrip, and explicit provider binding:
python -m pip install "ssmdstudio[authoring]"
ssmdstudio ssmd lint episode.ssmd.md --roundtrip --json
ssmdstudio ssmd bind episode.ssmd.md --provider kokoro \
  --voice-bind host="$HOST_VOICE_ID" \
  --voice-bind guest="$GUEST_VOICE_ID" \
  --output episode.bound.ssmd.md
```

Replace the voice placeholders with IDs selected for the named provider; Studio does not discover or verify provider voices. Core project operations do not require the optional `ssmd` runtime. Studio lint checks SSMD structure and optional roundtrip only; a pass does not establish renderability by Readio or another consumer. It does not resolve semantic plans, synthesize, listen to, or export audio. To check Readio-specific render readiness, separately use its no-audio dry run:

```bash
python -m readio render --file episode.bound.ssmd.md --input-format ssmd \
  --engine kokoro --dry-run --json
```

`ssmdstudio draft new` creates a standalone file. It is distinct from `ssmdstudio draft set FILE`, which imports a prose draft into an existing authoring project.

## Readio authoring command migration

Use these Studio commands for standalone authoring. They do not replace Readio's runtime planning or rendering responsibilities.

| Readio command                                                | SSMDStudio replacement / boundary                                                                                                                                                   |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `readio template path [NAME]`                                 | `ssmdstudio template path [NAME]`                                                                                                                                                   |
| `readio template list`                                        | `ssmdstudio template list` (the user library; run `template reset --all` to install packaged starters)                                                                              |
| `readio template show NAME`                                   | `ssmdstudio template show NAME`                                                                                                                                                     |
| `readio template add NAME --file FILE`                        | `ssmdstudio template add NAME --file FILE`                                                                                                                                          |
| `readio template remove NAME`                                 | `ssmdstudio template remove NAME`                                                                                                                                                   |
| `readio template reset NAME` / `--all`                        | `ssmdstudio template reset NAME` / `--all` (only bundled names reset; custom templates remain)                                                                                      |
| `readio template validate NAME` / `--all`                     | `ssmdstudio template validate NAME` / `--all`; `--roundtrip` is optional SSMD validation, not a Readio renderability check                                                          |
| `readio template use TEMPLATE [--name FILE]`                  | `ssmdstudio template use TEMPLATE --output FILE`, or `ssmdstudio draft new --output FILE --template TEMPLATE`; writes an SSMD starter file, not a Readio ingest/conversion artifact |
| `readio ingest new [--name NAME] [--template TEMPLATE]`       | `ssmdstudio draft new --output FILE [--template TEMPLATE]`; creates a standalone file at the requested path                                                                         |
| `readio ingest list` / `path`                                 | No managed ingest directory in Studio; use filesystem paths. `ssmdstudio draft set FILE` imports a prose draft into a selected project.                                             |
| `readio ssmd bind FILE --provider P --voice-bind ROLE=ID ...` | `ssmdstudio ssmd bind FILE --provider P --voice-bind ROLE=ID ...`; materializes explicit bindings without checking voice availability                                               |
| `readio ssmd check FILE --roundtrip --json`                   | `ssmdstudio ssmd lint FILE --roundtrip --json` for structural lint. For Readio-specific plan/voice preflight, separately run `readio render --file FILE --dry-run --json`.          |

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

The standalone APIs are also exported from the package root. `check_ssmd` reports `unavailable` when the optional runtime is absent; binding requires the `authoring` extra and explicit provider IDs.

```python
from pathlib import Path
from ssmdstudio import TemplateLibrary, check_ssmd, materialize_voice_bindings

templates = TemplateLibrary()  # run `ssmdstudio template reset --all` to install bundled starters
print(templates.path("podcast"))
result = check_ssmd(Path("episode.ssmd.md"), roundtrip=True)
bound = materialize_voice_bindings(
    Path("episode.ssmd.md"),
    {"host": "HOST_VOICE_ID"},  # replace with an ID selected for this provider
    provider="kokoro",
)
print(result.state, bound.output)
```

## Development

There is intentionally no `src/` directory. Versioning is dynamic through `setuptools-scm`.

```bash
python -m pip install -e ".[dev]"
pytest -q
ruff check .
python -m build --wheel
```

## Non-goals

SSMDStudio does not include model-provider clients, a database, a GUI, audio rendering, concrete
provider voice IDs, semantic merge machinery, or background jobs. Structural checking and explicit
binding use the optional `ssmd` runtime; downstream consumers own role resolution, render planning,
synthesis, audio rendering, and export.

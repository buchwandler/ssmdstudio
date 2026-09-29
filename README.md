# ssmdstudio

`ssmdstudio` is a small Python framework and CLI for building structured authoring projects
that an LLM or harness can turn into SSMD. Characters, scenes, feedback, prompts, drafts, and
output live in a filesystem-backed project store. The store is the source of truth, not chat
history.

## Design boundary

SSMD Studio stores authoring state, compiles provider-neutral prompts, and applies returned files.
A human or harness executes the prompts. SSMD Studio does not call model providers or render
audio. The optional `ssmd` runtime validates the final document when installed.

## Standalone projects and workspaces

A standalone project remains the simplest option and keeps the original flat layout:

```bash
ssmdstudio init picnic --title "The Picnic Problem" --brief \
  "Anna prepares a picnic while a curious dog keeps stealing napkins."
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
  --brief "A person tries to print while the printer develops a bureaucratic personality."
ssmdstudio project list
ssmdstudio project use printer-story
ssmdstudio project show
```

The active project is a convenience. Scriptable commands can use `--project ID` or a project
path to select a project explicitly. Existing standalone directories continue to work with
`Studio.open(PATH)` and the original `ssmdstudio init PATH` command. Nested projects are refused
by default; `--allow-nested` is an explicit override.

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

Use this when the user asks a harness to create the story. The harness runs the same compiled
prompts and applies its responses through SSMD Studio. It should pause for approval after the
character and scene checkpoints, present the draft for review, record requested edits as feedback,
and use targeted revisions before converting approved prose to SSMD.

The skill is bundled in the wheel and can be shown, located, or installed into a directory chosen
by the user or harness:

```bash
ssmdstudio skill show
ssmdstudio skill path
ssmdstudio skill install ~/.agents/skills/ssmdstudio
```

The install command writes `SKILL.md` under the specified directory. SSMD Studio does not choose a
vendor-specific global skills directory.

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
characters/
scenes/
feedback/
drafts/current.md
output/current.ssmd.md
output/validation.json
runs/
```

Prompt runs store the generated prompt and a manifest containing the input fingerprint, expected
artifact, and response provenance. `ssmdstudio status` reports inventory, next stage, prompt
staleness, and current validation state.

## Python API

```python
from ssmdstudio import Studio, Workspace

workspace = Workspace.open("my-stories")
studio = workspace.resolve_project("printer-story")
prompt = studio.build_prompt("characters")
print(prompt)
```

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

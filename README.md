# ssmdstudio

`ssmdstudio` is a small Python framework and CLI for building **structured authoring
projects** that an LLM can turn into SSMD.

The project store is the source of truth. Characters, scenes, human feedback, prompts,
drafts, and generated SSMD stay separate so a human can revise one part without
reconstructing the whole creative brief from chat history.

This MVP starts with one recipe: `funny-story`.

## Design boundary

`ssmdstudio` creates and manages authoring state and compiles prompts.

It deliberately does **not** call a model provider and does not render audio. A human,
agent harness, CI job, or model-specific adapter can execute the generated prompts.
The final `.ssmd.md` can then be consumed by Readio or another SSMD-compatible runtime.

## Layout

There is intentionally **no `src/` directory**:

```text
ssmdstudio/
├── pyproject.toml
├── ssmdstudio/
│   ├── cli.py
│   ├── models.py
│   ├── project.py
│   ├── prompts.py
│   ├── store.py
│   └── resources/
├── skill/ssmdstudio/SKILL.md
└── tests/
```

Versioning is dynamic through `setuptools-scm`. In a Git checkout, tags drive package
versions. For example, tag `v0.1.0` produces version `0.1.0`. A source tree without Git
metadata falls back to `0+unknown`.

## Install for development

```bash
python -m pip install -e ".[dev]"
```

## Quick start

```bash
ssmdstudio init picnic --title "The Picnic Problem" --brief \
  "Anna tries to prepare a picnic before her friends arrive, while a curious dog steals napkins."

cd picnic

ssmdstudio character add anna \
  --name Anna \
  --role protagonist \
  --description "Organized and patient; increasingly baffled by the missing napkins." \
  --trait organized --trait patient \
  --voice-notes "Warm, natural, restrained dry humor" \
  --ssmd-role host

ssmdstudio character add dog \
  --name "Milo the dog" \
  --role counterpart \
  --description "Curious, harmless, and convinced loose napkins are toys." \
  --trait curious --trait harmless

ssmdstudio scene add setup \
  --title "The first missing napkin" \
  --purpose "Introduce Anna's ordinary goal and the running problem." \
  --character anna --character dog \
  --event "Anna lays out the picnic." \
  --event "The dog quietly takes one napkin." \
  --event "Anna notices that something is missing."

ssmdstudio prompt build scenes --save --output prompt-scenes.md
```

Give `prompt-scenes.md` to an LLM. The prompt returns a `scenes:` YAML list, which can be
imported directly:

```bash
ssmdstudio scene import scenes.yaml
```

The same round-trip works for characters:

```bash
ssmdstudio prompt build characters --save --output prompt-characters.md
# execute the prompt with your LLM and save its YAML response
ssmdstudio character import characters.yaml
```

Build the plain-story draft prompt:

```bash
ssmdstudio prompt build draft --save --output prompt-draft.md
```

After the LLM writes the story:

```bash
ssmdstudio draft set draft.md
```

Add human feedback:

```bash
ssmdstudio feedback add slower-middle \
  --scope scene:escalation \
  --instruction "The escalation is too fast; add one smaller failure first." \
  --lock scene:payoff
```

Build a revision prompt:

```bash
ssmdstudio prompt build revise --save --output prompt-revise.md
```

When the prose draft is approved, compile the SSMD prompt:

```bash
ssmdstudio prompt build ssmd --save --output prompt-ssmd.md
```

Import the generated SSMD artifact:

```bash
ssmdstudio output set story.ssmd.md
```

Inspect the project:

```bash
ssmdstudio status
```

## Project store

A project is plain YAML and Markdown:

```text
project.yaml
characters/
scenes/
feedback/
drafts/current.md
output/current.ssmd.md
runs/
```

The format is deliberately boring: human-readable, Git-friendly, and easy for agents
to modify with normal filesystem tools.

## Python API

```python
from ssmdstudio import Studio

studio = Studio.open("picnic")

studio.add_character(
    id="jo",
    name="Jo",
    role="friend",
    description="Arrives halfway through and notices the pattern.",
    traits=["observant"],
    voice_notes="Friendly and matter-of-fact",
    ssmd_role="guest",
)

studio.add_scene(
    id="arrival",
    title="Jo arrives",
    purpose="Let another person recognize the running gag.",
    characters=["anna", "jo", "dog"],
    events=["Jo arrives.", "The dog passes carrying another napkin."],
)

prompt = studio.build_prompt("draft")
print(prompt)
```

## Prompt runs and staleness

`ssmdstudio prompt build ... --save` stores the prompt and a manifest under `runs/`.
The manifest contains a SHA-256 fingerprint of the inputs used for that prompt.

If characters, scenes, the brief, feedback, or draft change later, `ssmdstudio status`
marks previous prompt runs as `stale`. This is a small but useful dependency mechanism
without requiring a database or workflow engine.

## MVP non-goals

The MVP intentionally does not:

- call OpenAI, Anthropic, Gemini, or another provider;
- render audio;
- bind concrete TTS voices;
- provide a GUI;
- implement every Readio authoring recipe;
- attempt automatic semantic merges of model output.

Those can be layered on the stable project/store/prompt API later.

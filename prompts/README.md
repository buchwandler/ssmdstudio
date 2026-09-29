# SSMDStudio prompt data

This directory contains prompt data. It is intentionally outside the `ssmdstudio` Python package and is not required to be present in the wheel.

- `workflows/` contains prompt packs for structured SSMDStudio projects.
- `standalone/` contains complete prompts for direct use with generic LLMs.

Workflow packs may be copied into a project and edited by the user. Standalone prompts are self-contained and do not require SSMDStudio Python.

## Workflow prompt-pack manifest

A workflow pack has a `prompt-pack.yaml` manifest with this v1 shape:

```yaml
schema: ssmdstudio.prompt-pack.v1
id: funny-story
kind: workflow
stages:
  characters: characters.md
  scenes: scenes.md
  draft: draft.md
  revise: revise.md
  ssmd: ssmd.md
```

The supported stages are exactly `characters`, `scenes`, `draft`, `revise`, and `ssmd`. Each stage must map to a relative UTF-8 Markdown file inside the pack directory. The manifest is data only: it cannot name Python modules, providers, models, or executable hooks. A project can install a compatible pack with `ssmdstudio prompt pack install PATH`; the installed project copy is ordinary editable project data.

## Two different prompt families

Workflow prompts receive structured project context and produce artifacts understood by SSMDStudio's staged workflow. Standalone prompts are complete authoring guides that can be attached directly to a generic LLM without installing SSMDStudio. In particular, `workflows/funny-story/ssmd.md` converts an approved locked draft, while `standalone/ssmd/funny-story.md` creates a new comic story directly. They are not interchangeable.

Readio's runtime `.ssmd` templates are not LLM prompts and are not catalogued here.

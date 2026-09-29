---
name: ssmdstudio
description: Build and revise structured SSMD authoring projects with characters, scenes, feedback, drafts, and compiled prompts.
compatibility: Requires the ssmdstudio CLI. Model execution is provided by the surrounding harness, not by ssmdstudio itself.
---

# SSMD Studio

Use SSMD Studio when the user is creating or revising SSMD content rather than rendering it.

## Core rule

The project store is the source of truth. Do not keep important character, scene, or revision
decisions only in chat history.

## Funny-story workflow

1. Initialize a project with `ssmdstudio init`.
2. Build `ssmdstudio prompt build characters --save`.
3. Execute that prompt with the available LLM.
4. Store approved character briefs with `ssmdstudio character import FILE` (or `character add` for manual entry).
5. Build `ssmdstudio prompt build scenes --save`.
6. Execute it and store approved scenes with `ssmdstudio scene import FILE` (or `scene add` for manual entry).
7. Build `ssmdstudio prompt build draft --save`.
8. Save the returned prose to a file and import it with `ssmdstudio draft set FILE`.
9. Let the human review the draft.
10. Store concrete changes with `ssmdstudio feedback add`.
11. Build and execute `ssmdstudio prompt build revise --save` until the prose is approved.
12. Build `ssmdstudio prompt build ssmd --save`.
13. Save the returned raw SSMD and import it with `ssmdstudio output set FILE`.
14. Hand the final `.ssmd.md` to an SSMD runtime such as Readio for validation, binding,
    rendering, or publication.

## Authoring boundaries

- Do not invent concrete TTS voice IDs.
- Do not use pitch/rate/volume as character identity.
- Keep symbolic roles stable.
- Do not mark model output as validated or rendered unless a runtime actually performed it.
- Preserve locked scenes and explicit human constraints.
- Prefer targeted revisions over regenerating unrelated approved material.

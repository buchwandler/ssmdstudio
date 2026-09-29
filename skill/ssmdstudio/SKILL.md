---
name: ssmdstudio
description: Build and revise structured SSMD authoring projects with characters, scenes, feedback, drafts, and compiled prompts.
compatibility: Requires the ssmdstudio CLI. Model execution is provided by the surrounding harness, not by ssmdstudio itself.
---

# SSMD Studio

Use SSMD Studio when the user is creating or revising SSMD content rather than rendering it.

## Core rules

- The project store is the source of truth. Do not keep important character, scene, or revision decisions only in chat history.
- Keep SSMD Studio provider-independent. The harness executes prompts; the CLI stores state, compiles prompts, applies artifacts, and reports validation.
- Workflow prompt packs are external, editable project data, not packaged Python resources. Before `prompt build` or `prompt next`, confirm a pack is installed; use `ssmdstudio prompt pack path` or install available user/repository data with `ssmdstudio prompt pack install PATH --project ID`. Project-state commands still work without a pack.
- The canonical Agent Skill is repository/user-managed data at `skill/ssmdstudio/SKILL.md`. The wheel and CLI do not provide skill show/path/install commands.
- Do not invent concrete TTS voice IDs. Use stable symbolic roles and do not use prosody as speaker identity.
- Preserve locked scenes and explicit human constraints.
- Do not report SSMD as validated unless an installed SSMD runtime actually ran.

## Choose a workflow

Use **Manual / copy prompt** when the user wants to run prompts in another chat or model UI. Do not spend harness generation tokens in this mode.

Use **Harness / skill** when the user asks this harness to write the story. Execute prompts with the harness and stop for user review at each approval checkpoint.

## Manual / copy prompt

1. Open the standalone project, or create/select a workspace project:

   ```bash
   ssmdstudio workspace init
   ssmdstudio project create printer-story \
     --title "Funny printer story" \
     --brief "A person tries to print a document while the office printer develops a bureaucratic personality." \
     --prompt-pack /path/to/ssmdstudio/prompts/workflows/funny-story
   ssmdstudio project use printer-story
   ```

2. Run `ssmdstudio next`, then `ssmdstudio prompt next --save`. Give the saved prompt to the user's chosen LLM. The command reports the exact expected artifact name and the command to apply it.
3. Let the user run the prompt elsewhere and return with the requested file. Do not generate that artifact on the user's behalf in manual mode.
4. Apply the returned file using the reported command, normally `ssmdstudio apply FILE`.
5. Repeat `next`, `prompt next --save`, and `apply FILE` until the project is complete.

The expected files are `characters.yaml`, `scenes.yaml`, `draft.md`, and `<project-id>.ssmd.md`. Text-only model responses are supported: save the complete raw contents under the requested filename.

Standalone projects remain supported. From a standalone project directory, use `ssmdstudio status` and the same prompt/apply loop without workspace commands.

## Harness / skill

### Start

If the user has not supplied a story premise and title, ask only for those two essentials. Use project defaults for recipe, language, audience, tone, and duration unless the user asks to change them. Open an existing project when requested; otherwise create a standalone project or a workspace project according to the user's preference.

After creating or opening a project, check `ssmdstudio status` for an installed prompt pack before generating. If none is installed, use an available external pack or ask the user where their workflow prompts are; do not substitute standalone guides or Readio runtime `.ssmd` templates.

Use explicit `--project ID` or a project path when addressing projects. The active project is a convenience, not the only way to select one.

For an existing project without a pack, install an available workflow pack explicitly, for example `ssmdstudio prompt pack install /path/to/prompt-pack --project printer-story`. Do not assume prompt data is inside the Python package.

### Characters checkpoint

1. Build the current characters prompt with `ssmdstudio prompt build characters --save` or `ssmdstudio prompt next --save` when characters are the next stage.
2. Execute the prompt with the harness, save the exact requested `characters.yaml`, and apply it with `ssmdstudio apply characters.yaml`.
3. Present a concise review of each character's name, story function, goal, voice direction, and symbolic role.
4. Ask the user to approve or request changes. For changes, rebuild the characters prompt with `ssmdstudio prompt build characters --save`, revise the complete character set, save `characters.yaml`, and apply it with `ssmdstudio apply --stage characters characters.yaml`. Repeat review and continue only after approval.

### Scenes checkpoint

1. Generate and apply the complete `scenes.yaml` plan.
2. Present the sequence compactly with each scene's title, purpose, major beat, and comic function.
3. Ask for approval or requested changes. For changes, rebuild the scenes prompt with `ssmdstudio prompt build scenes --save`, revise the complete scene plan, save `scenes.yaml`, and apply it with `ssmdstudio apply --stage scenes scenes.yaml`. Repeat review and continue only after approval.

### Draft and targeted revision

1. Generate and apply the complete plain-language `draft.md`.
2. Present the draft for review. Turn requested edits into concrete feedback records with `ssmdstudio feedback add`.
3. Use the `revise` prompt for targeted changes. Apply the returned complete `draft.md`; this resolves the currently open feedback records. Preserve unaffected approved text and do not return patches.
4. Repeat review and targeted revision until the user approves the draft. The approved prose is the wording source of truth for SSMD conversion.

### Final SSMD

1. Generate the SSMD conversion prompt only after the draft has no open feedback.
2. Apply the returned `<project-id>.ssmd.md` with `ssmdstudio apply FILE`.
3. Run `ssmdstudio output validate` and report passed, failed, or unavailable accurately, surfacing diagnostics. Never describe unavailable validation as success.
4. If markup validation fails, retain the generated draft and correct only the SSMD conversion artifact unless diagnostics identify a source-content issue.
5. Leave the final named `.ssmd.md` file in the project and report its path and validation result.

## Project commands

- `ssmdstudio next` shows the next stage, expected file, and follow-up command.
- `ssmdstudio status` shows stored state and stage progress.
- `ssmdstudio prompt pack install PATH`, `prompt pack path`, and `prompt pack validate PATH` manage external workflow packs; use `--replace` only when the user approves replacement.
- The standalone LLM guides live in repository data under `prompts/standalone/`; they do not replace the structured workflow pack.
- `ssmdstudio project list`, `project use ID`, and `project show` manage workspace projects.
- An explicit `--project ID` overrides the active workspace project.
- Keep the project's files as the source of truth. Chat history is not a substitute for applying artifacts and feedback to the store.

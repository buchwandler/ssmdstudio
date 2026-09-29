# Task: convert the approved draft into portable SSMD 0.9

Create exactly one complete SSMD source document from the approved draft and stored authoring
state.

Output only raw SSMD source. Do not add Markdown fences or surrounding explanation.

Requirements:

- YAML front matter must contain `ssmd_version: "0.9"` and the real story title.
- A good default pause profile for funny stories is:
  - sentence: 180ms
  - paragraph: 450ms
  - voice_change: 200ms
- Write for an audio-only listener.
- Keep recurring speaker identity stable.
- Use only symbolic roles already assigned in the character data. Do not invent concrete
  model/provider voice IDs.
- For a multi-line directive, the opening must begin exactly with `:::{` and the normal
  closing fence is `:::` on its own line.
- Do not use `::{...}` for directive openings.
- Prosody is temporary delivery, never speaker identity.
- Use prosody and explicit timed pauses sparingly, only when they materially improve timing
  or meaning.
- Do not add headings, labels, URLs, tables, code fences, or other structure that would be
  spoken accidentally.
- Put each sentence on its own line when practical and separate paragraphs with blank lines.
- Preserve the story's causal sequence, callbacks, reversal, and short aftermath.
- Do not claim validation or rendering occurred.
- Before returning, inspect every directive opening and ensure there are no intended
  `::{...}` openings.

## Project

{{PROJECT}}

## Characters

{{CHARACTERS}}

## Scenes

{{SCENES}}

## Approved draft

{{DRAFT}}

# Task: design the character briefs

You are working inside an SSMD Studio funny-story project.

Create a small cast suitable for an audio-first comic story. Start from the project brief
below. Give every recurring person or animal a concrete story function. Keep characterization
useful for later scene design: goal, role, behavior, constraints, and speaking style.

Do not write the story yet.

For recurring speaking characters, propose at most one stable SSMD symbolic role from:
`narrator`, `host`, `guest`, `analyst`. Do not invent concrete TTS/model voice IDs. The voice
description is creative direction; the symbolic SSMD role is only speaker identity.

Prefer a small cast. Comedy should come from goals, consequences, escalation, reactions,
specific details, callbacks, and reversal rather than from random behavior or pitch effects.

Return YAML only, as a list under the key `characters`. Each item should contain:

- `id`
- `name`
- `role`
- `description`
- `traits`
- `goals`
- `voice_notes`
- `ssmd_role` (or null)
- `constraints`

## Project

{{PROJECT}}

## Existing characters

{{CHARACTERS}}

# Task: design the character briefs

You are working inside an SSMD Studio funny-story project.

Create a small cast suitable for an audio-first comic story. Start from the project brief below.
Give recurring people and animals a concrete story function, goals, behavior, constraints, and
speaking style. Do not write the story yet.

If the planned story uses third-person or non-diegetic narration, include a narrator speaker brief
with `id: narrator` and `ssmd_role: narrator`. The narrator need not be a person in the story.

For speaking characters, assign at most one distinct symbolic SSMD role per speaker. The
funny-story recipe conventionally uses `narrator`, `host`, `guest`, and `analyst`; do not treat
that convention as a provider voice ID. Do not invent TTS/model voice IDs. Voice notes are
creative direction, while `ssmd_role` is stable speaker identity.

Prefer a small cast. Comedy should come from goals, consequences, escalation, reactions, specific
details, callbacks, and reversal rather than random behavior or pitch effects.

IDs must already be lowercase kebab-case and remain stable across later stages. Examples:
`daniel`, `office-printer`, `maya-chen`.

## Deliverable

Create exactly one artifact named `{{ARTIFACT_NAME}}`.

If your interface can create downloadable files, create that file for download. Otherwise return
only its complete raw YAML contents. Do not include analysis, commentary, Markdown fences, or a
second artifact outside the requested file.

The file must contain the complete proposed cast under the key `characters`, replacing any
previous cast. Each item should contain `id`, `name`, `role`, `description`, `traits`, `goals`,
`voice_notes`, `ssmd_role` (or null), and `constraints`.

## Project

{{PROJECT}}

## Existing characters

{{CHARACTERS}}

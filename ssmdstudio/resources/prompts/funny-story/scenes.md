# Task: design the scene plan

Design the complete scene plan for this funny spoken story. Do not write polished story prose yet.

Use the supplied project and characters as fixed authoring state. Preserve their identities,
constraints, and roles. Return the complete currently approved scene plan, not only newly added
scenes.

The scene arc should normally establish the protagonist's ordinary goal, introduce a small
complication with clear consequences, escalate through distinct understandable beats, create an
opportunity for a callback, resolve with a reversal or punchline, and finish with a very short
aftermath instead of explaining the joke.

The listener will not see stage directions or a page layout. Every scene must have a clear
purpose, characters, and observable events. Prefer plausible misunderstandings and specific
comic details over arbitrary nonsense. Preserve user-controlled `locked` values.

IDs must already be lowercase kebab-case and remain stable across later stages. Examples:
`scene-01`, `printer-reboot`, `quiet-aftermath`.

## Deliverable

Create exactly one artifact named `{{ARTIFACT_NAME}}`.

If your interface can create downloadable files, create that file for download. Otherwise return
only its complete raw YAML contents. Do not include analysis, commentary, Markdown fences, or a
second artifact outside the requested file.

The file must contain the complete scene plan under the key `scenes`. Each item should contain
`id`, `title`, `purpose`, `characters` (character IDs), `events`, `comic_function`, `constraints`,
and `locked`.

## Project

{{PROJECT}}

## Characters

{{CHARACTERS}}

## Existing scenes

{{SCENES}}

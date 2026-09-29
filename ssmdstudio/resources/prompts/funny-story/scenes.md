# Task: design the scene plan

Design the scenes for this funny spoken story. Do not write polished story prose yet.

Use the supplied project and characters as fixed authoring state. Preserve their identities,
constraints, and roles.

The scene arc should normally:

1. establish the protagonist's ordinary goal;
2. introduce a small complication with a clear consequence;
3. escalate through distinct, understandable beats;
4. create an opportunity for a callback to an earlier detail;
5. resolve with a reversal or punchline;
6. finish with a very short aftermath instead of explaining the joke.

The listener will not see stage directions or a page layout. Every scene must therefore have
a clear purpose, characters, and observable events. Prefer plausible misunderstandings and
specific comic details over arbitrary nonsense.

Return YAML only, as a list under the key `scenes`. Each item should contain:

- `id`
- `title`
- `purpose`
- `characters` (character IDs)
- `events`
- `comic_function`
- `constraints`
- `locked` (false unless already constrained)

## Project

{{PROJECT}}

## Characters

{{CHARACTERS}}

## Existing scenes

{{SCENES}}

# Task: convert the approved draft into portable SSMD 0.9

Convert the approved story draft into exactly one complete SSMD 0.9 source artifact. This is a
markup/conversion stage, not a creative rewrite stage.

## Deliverable

Create exactly one artifact named `{{ARTIFACT_NAME}}`.

If your interface can create downloadable files, create that file for download. Otherwise return
only the complete raw SSMD source. Do not add analysis, commentary, Markdown fences, or a second
artifact.

## Content preservation

Treat the approved draft as locked story wording. Do not add, remove, rephrase, shorten, improve,
or punch up story content except for the minimum mechanical changes needed to turn attributed
dialogue into SSMD voice scopes, remove redundant speech-attribution glue when it would otherwise
be spoken twice, and normalize whitespace required by valid SSMD syntax.

Preserve wording, causal sequence, callbacks, reversal, meaningful capitalization, and the short
aftermath.

## SSMD requirements

- Use `ssmd_version: "0.9"` as a string, include the real story title, and include the supplied language.
- Use these funny-story pause defaults unless the project supplies another profile: sentence 180ms,
  paragraph 450ms, and voice_change 200ms.
- Use only symbolic voice references supplied in the speaker map. Do not invent provider, model,
  or TTS voice IDs.
- For multiline directives use `:::{...}` and close with `:::` on its own line.
- Do not use `::{...}` for directive openings.
- Prosody is temporary delivery, never speaker identity. Use prosody and explicit timed pauses
  sparingly, only when they materially improve meaning or comic timing.
- Do not add headings, labels, URLs, tables, or code fences that could be spoken.

## Dialogue pacing

A voice change is not automatically a paragraph boundary. Consecutive speaker turns in the same
conversational beat should normally be adjacent fenced directives with no blank line between the
closing `:::` and the next opening `:::{...}`. Use a blank line only when intentionally creating a
paragraph or pacing break.

```ssmd
:::{voice="host"}
No.
:::
:::{voice="guest"}
The survey contains only six questions.
:::
:::{voice="host"}
No.
:::
```

## Narration

When a narrator role exists, put narrative runs in `voice="narrator"` scopes. Group natural runs;
do not create one narrator directive per sentence.

## Final self-check

Before returning, ensure every directive opening is valid SSMD 0.9 syntax, dialogue maps to the
correct stored symbolic role, speaker changes do not create accidental paragraph breaks, the
approved prose has not been creatively rewritten, and the artifact is exactly one complete SSMD
document. Do not claim validation or rendering occurred.

## Project

{{PROJECT}}

## Speaker map

{{SPEAKERS}}

## Approved draft

{{DRAFT}}

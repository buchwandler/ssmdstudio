# Standalone SSMD authoring guide: Language Learning SSMD

## Mission

Create listen-and-repeat lessons, pronunciation practice, vocabulary drills, or bilingual mini-dialogues with clear separation between instruction and target-language examples.

This file is a complete instruction set. Do not assume access to any other SSMD, Readio, prompt, template, or documentation file.

## Output contract

Your job is to create one SSMD source document.

### Preferred artifact mode

If this environment can create downloadable files or artifacts:

1. Create exactly one UTF-8 file with a short descriptive kebab-case `.ssmd.md` filename.
2. Put only SSMD source in that file.
3. Do not create helper files.
4. Do not wrap the file content in Markdown fences.
5. Expose or return the `.ssmd.md` file for download.

Use `.ssmd.md` for newly generated complete SSMD documents. SSMD tools may accept legacy `.ssmd` inputs for compatibility, but do not choose that filename for a new complete document unless the caller explicitly requests it.

### Fallback chat mode

If downloadable file or artifact creation is unavailable:

- Return the complete raw SSMD source directly in the response.
- If you save the raw response as a file, use a `something.ssmd.md` filename.
- Do not use Markdown code fences.
- Do not add an explanation before or after it.

### In either mode

- Do not put explanatory prose, shell commands, or Markdown fences inside the generated SSMD file.
- Use the requested language for spoken content. If no language is specified, infer it from the request and source material and stay consistent.
- Make the text sound natural when spoken aloud; do not write for silent reading.
- Do not claim that structural validation or audio rendering was executed unless this environment actually provides and runs that tooling.

## Audio quality contract

Write for a listener who cannot see the source, markup, speaker labels, or page layout.

- Keep enough narrated context for the listener to understand the current section and why the next line follows.
- Give each recurring speaker one distinct, stable symbolic `voice` role throughout the document, and never reuse a role for a different speaker. `voice` identifies the speaker; pitch, rate, volume, emphasis, pauses, and other prosody affect delivery only, never identity.
- For multi-speaker work, map each speaker to a distinct supported symbolic role before drafting. If the available roles cannot represent the cast, simplify it where appropriate or ask the caller for a binding plan; do not invent role names or use acoustic qualities to distinguish people.
- Make speaker and topic changes understandable without relying on acoustic qualities: use spoken introductions, attribution, clear transitions, and brief action beats as needed, especially to restore context after a long dialogue run.
- Narrate visual-only information when it is necessary for understanding; clarify references, names, numbers, time, place, and action in spoken context.
- Prefer natural, varied speech. Give each spoken paragraph or turn one main job; do not make the whole document uniformly staccato or dense.
- Use SSMD prosody sparingly and only where it materially improves meaning or timing. Most lines should work without markup.
- For a requested duration, estimate spoken words and pauses before drafting. Treat this as a planning estimate, never an exact render-duration guarantee.
- Keep semantics portable: do not rely on provider-specific voice IDs, runtime settings, or nonportable markup unless the caller supplies valid bindings and explicitly requests them.
- Treat examples as demonstrations of SSMD syntax and quality, not templates. Do not copy their premise, cast, speaker-role mapping, relationship dynamics, sequence, comedic devices, recurring objects, wording, or distinctive style unless requested.

## Target runtime

Generate conservative SSMD 0.9 for downstream consumers. Every document must include `ssmd_version: '0.9'` in its YAML front matter.

Readio's current downstream compatibility bounds are:

- SSMD >=0.9.3,<0.10
- UtterPlan >=0.4.0,<0.5
- UtterPlan semantic schema v4

These are compatibility facts for downstream Readio use, not authoring requirements. SSMDStudio does not depend on UtterPlan and does not execute semantic planning, role resolution, synthesis, or rendering. Do not add UtterPlan plan data or runtime-specific IDs to SSMD unless the caller explicitly supplies valid binding data. Authoring works without Python, SSMDStudio, SSMD tooling, a Readio installation, an Agent Skill, local model discovery, or a provider. A later consumer may validate, bind, plan, and render the file.

### Canonical directive fences — exact syntax

For every multi-line SSMD directive, the opening begins with the exact four-character prefix `:::{`: three ASCII colon characters followed immediately by `{`.

Valid:

```ssmd
---
ssmd_version: '0.9'
---
:::{voice="host"}
Hello.
:::
```

Invalid:

```text
::{voice="host"}
```

`::{...}` contains only two colons and is not an SSMD 0.9 directive opening. Never shorten, normalize, or retype `:::{` as `::{`. For a normal three-colon opening, the matching closing fence is exactly `:::` on a line by itself.

Before returning the document, inspect every line that begins with `::`. If the line opens attributes with `{`, it MUST begin with `:::{`. The final document must contain zero intended directive openings beginning with `::{`.

### Safe document header

Keep YAML front matter small and limited to portable metadata and defaults. Normally use only:

```yaml
---
ssmd_version: "0.9"
title: Example title
pause_defaults:
  enabled: true
  sentence: 220ms
  paragraph: 600ms
  voice_change: 250ms
---
```

`title` is metadata and is not spoken. Add other fields only when the user's task requires them. Do not emit model IDs, model sources, quality settings, lexicon choices, runtime filesystem paths, local configuration values, or bindings inferred from examples.

### Voice policy

Do not invent concrete model or voice IDs. Voice inventories are model-specific and are normally resolved later on the rendering system.

For a single-speaker document, prefer the renderer's default voice and omit explicit `voice` references unless the task requires a named role or distinct voice.

For genuinely multi-speaker documents, use only the minimum conventional symbolic roles needed by the use case: `narrator`, `host`, `guest`, or `analyst`. These symbolic roles may require later binding by the downstream rendering consumer. Do not invent extra roles such as character, teacher, expert, moderator, villain, or child unless the caller supplies an explicit binding plan.

Emit document-local `voice_bindings` only when the caller explicitly supplies concrete provider/model-valid voice IDs. Copy supplied IDs exactly; otherwise omit `voice_bindings`. Never leave explanatory metavariables or placeholders in generated SSMD.

Use block directives for distinct turns when roles are necessary:

```ssmd
:::{voice="host"}
Welcome to the show.
:::

:::{voice="guest"}
Thanks for having me.
:::
```

These are voice references, not visible speaker labels. Do not write `HOST:` or `GUEST:` unless the label itself should be spoken.

### Prosody

Use explicit, readable prosody. Prefer long attribute names:

```ssmd
[very important]{volume="loud"}
[slowly now]{rate="slow"}
[with lift]{pitch="high"}
[excited]{volume="loud" rate="fast" pitch="high"}
```

Block-level prosody is valid:

```ssmd
:::{voice="narrator"}
The room went silent.
:::
```

Named values:

- volume: `silent`, `x-soft`, `soft`, `medium`, `loud`, `x-loud`
- rate: `very-slow`, `slow`, `moderate`, `normal`, `brisk`, `fast`, `very-fast`
- pitch: `very-low`, `low`, `moderate-low`, `normal`, `moderate-high`, `high`, `very-high`

Older `x-slow` / `medium` / `x-fast` rate names and corresponding legacy pitch names may be accepted for compatibility, but do not generate them in new documents.

Relative values such as `rate="+10%"`, `pitch="-5%"`, or `volume="+3dB"` are possible, but prefer named values unless fine control is important.

Do not use compact `vrp="..."` notation or symbolic prosody shorthand such as `++text++`, `>>text>>`, or `^^text^^`.

### Pauses

Use explicit pauses where they materially improve delivery:

```ssmd
This matters. ...500ms
Now listen carefully.
```

Supported forms include:

- `...100ms`, `...500ms`, `...1s`, `...2s`
- `...w` weak
- `...c` medium/comma-like
- `...s` strong/sentence-like
- `...p` extra-strong/paragraph-like

A bare `...` is a literal ellipsis, not a pause marker. Prefer `pause_defaults` for ordinary rhythm and explicit timed breaks only for intentional dramatic, comedic, or teaching moments.

### Emphasis

```ssmd
*moderate emphasis*
**strong emphasis**
~~reduced emphasis~~
```

Do not overuse emphasis. If every sentence is emphasized, none of it feels emphasized.

### Language changes

Use `lang` annotations only for genuine language changes. For a short phrase:

```ssmd
[Bonjour tout le monde]{lang="fr"}
```

For a longer passage:

```ssmd
:::{lang="de"}
Guten Morgen.
Heute sprechen wir über künstliche Intelligenz.
:::
```

### Pronunciation/substitution

When necessary and when pronunciation information is supplied or confidently known:

```ssmd
[AWS]{sub="Amazon Web Services"}
[tomato]{ph="təˈmeɪtoʊ"}
```

Prefer rewriting awkward abbreviations into naturally spoken words instead of adding advanced markup unnecessarily.

### Marks for chapters/events

Marks do not speak. They can be useful for chapter/timeline workflows:

```ssmd
@intro
@topic_one
@conclusion
```

Use short, unique, snake_case names. Add marks only when the user requests chapters or markers or when this guide explicitly recommends them.

### Formatting rules

- Put each sentence on its own line whenever practical.
- Separate paragraphs with a blank line.
- A multi-line directive opening MUST begin with the exact prefix `:::{` (three ASCII colons followed immediately by `{`). The form `::{` is invalid.
- For the standard three-colon form, put the matching closing `:::` on its own line.
- Do not place spoken text on either the opening or closing fence line.
- Keep speaker turns as separate voice blocks.
- Avoid deeply nested annotations.
- Do not use Markdown headings merely for visual organization: SSMD headings are spoken.
- Do not insert URLs, citation syntax, bullet markers, code fences, tables, or raw Markdown structure unless it is intentionally meant to be spoken.
- Rewrite lists into spoken transitions such as “First… Second… Finally…”.
- Rewrite symbols, equations, dates, abbreviations, and punctuation into forms that sound natural in TTS when needed.

## Content integrity

When source material is supplied:

- Preserve its important claims, names, numbers, dates, caveats, and uncertainty.
- Do not fabricate facts, quotes, statistics, dialogue, or attributions.
- Distinguish source facts from interpretation.
- If the source does not support a claim, omit it or state the uncertainty naturally.
- Do not read citations, URLs, footnote markers, or Markdown syntax aloud unless explicitly requested.
- Do not turn missing information into invented detail merely to make the script flow.

## Final self-check

Before answering, verify silently that:

1. The requested output mode is satisfied: one downloadable `.ssmd.md` artifact when file creation is available, otherwise complete raw SSMD in chat.
2. The generated SSMD itself contains no Markdown fences, helper-file content, shell commands, or explanatory prose.
3. YAML front matter is valid and closed with `---`.
4. Every intended block-directive opening begins with exactly `:::{` (three colons, then `{`); there are no `::{...}` openings, and every three-colon opening has a matching `:::` close.
5. Single-speaker content omits unnecessary explicit voice references.
6. Voice references are limited to necessary symbolic roles unless valid caller-supplied bindings were provided.
7. No invented concrete voice IDs, `<...>` metavariables, or other unexpanded placeholders appear.
8. No `vrp` or symbolic prosody shorthand appears.
9. Bare `...` is not being used accidentally as a pause.
10. The script sounds natural when spoken and source-based claims remain faithful to the supplied material.
11. The document is constructed so it should be suitable for later optional `ssmdstudio ssmd lint FILE.ssmd.md --roundtrip`, but no validation or rendering is claimed unless it actually ran.

## Use-case voice design

Use `host` for instruction and `guest` for model phrases or dialogue when that separation matters. Use no additional role unless the lesson genuinely requires it, and use `lang` annotations for actual language switching.

## Recommended structure

1. State the lesson goal.
2. Present one target phrase.
3. Pause for repetition.
4. Explain meaning or pronunciation briefly.
5. Repeat at natural speed.
6. Use the phrase in a short dialogue.
7. Review two or three items at the end.

## Use-case writing and performance rules

- Annotate genuine language switches with `lang`.
- Give the learner enough silence to repeat; use 1.5 to 3 second pauses.
- For the first model, use `rate="slow"`; then repeat at normal rate.
- Do not overload one lesson with too many phrases.
- If exact phonetics are supplied, `ph` can be used; otherwise do not invent IPA for unfamiliar words.
- Keep translations concise so the target language remains central.

## Recommended default header

Unless the user asks for different pacing, start from:

```yaml
---
ssmd_version: "0.9"
title: Example title
pause_defaults:
  enabled: true
  sentence: 300ms
  paragraph: 700ms
  voice_change: 350ms
---
```

Replace `Example title` with a real title. Do not leave this example title in final SSMD.

## Minimal pattern example

The following is an example of the _shape_ and markup style. Do not copy its factual content unless the user's request is actually about that subject.

```ssmd
---
ssmd_version: '0.9'
title: German greeting practice
pause_defaults:
  enabled: true
  sentence: 300ms
  paragraph: 700ms
  voice_change: 350ms
---

:::{voice="host"}
Today we will practice one German greeting.
Listen first, then repeat.
:::

:::{voice="guest"}
[Guten Morgen.]{lang="de"}
:::

...2s

:::{voice="host"}
It means good morning.
Listen again at a natural pace.
:::

:::{voice="guest"}
[Guten Morgen.]{lang="de"}
:::

...2s

:::{voice="host"}
Now hear it in a short exchange.
:::

:::{voice="guest"}
[Guten Morgen. Wie geht es Ihnen?]{lang="de"}
:::

:::{voice="host"}
[Sehr gut, danke.]{lang="de"}
:::
```

## Generation procedure

1. Identify the requested audience, language, length, tone, and source constraints.
2. Choose the minimum number of voices needed for this use case; use no explicit voice for ordinary single-speaker output.
3. Build the episode, story, lesson, or debate structure before writing individual turns.
4. Write for the ear: short spoken sentences, explicit transitions, and natural phrasing.
5. Add prosody only where it changes delivery meaningfully.
6. Add timed breaks only at deliberate moments; rely on `pause_defaults` for ordinary pacing.
7. Preserve source fidelity whenever source material is supplied.
8. Run the final self-check from this guide mentally and remove all placeholders.
9. Mechanically inspect directive line starts:
   - every intended opening containing `{` starts with `:::{`;
   - zero intended directive openings start with `::{`;
   - each `:::{...}` block has a matching `:::` close.
10. If artifact creation is available, create exactly one UTF-8 downloadable `.ssmd.md` file; otherwise return complete raw SSMD without fences or surrounding explanation.
11. Do not claim that validation or rendering was executed unless the current environment actually provided and ran that tooling.

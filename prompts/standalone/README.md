# Standalone SSMD authoring guides

These self-contained guides teach a generic LLM to author portable SSMD source. They do not require Readio, Python, an Agent Skill, SSMD tooling, a provider, or a local audio engine on the authoring system. SSMDStudio owns authoring and structural validation; downstream consumers own planning, voice resolution, synthesis, rendering, and export.

## Authoring versus downstream use

Standalone guides are not runtime templates:

- `ssmdstudio template` manages real, editable starter `.ssmd` documents packaged by SSMDStudio.
- `prompts/standalone/ssmd/` contains complete Markdown instructions for authoring `.ssmd.md` source.
- The guide produces source only; it does not create audio or bind voices by default.
- Structural and optional roundtrip validation can be run with `ssmdstudio ssmd lint FILE.ssmd.md --roundtrip` when the CLI and SSMD runtime are available.
- `ssmdstudio ssmd bind` is an explicit optional post-authoring step that writes provider-scoped bindings only from caller-supplied voice IDs.
- A downstream consumer such as Readio performs engine/role resolution, planning, synthesis, rendering, and export.

The intended lifecycle is:

```text
source or task
    ↓
generic LLM + one standalone guide
    ↓
downloadable .ssmd.md file
    ↓
optional SSMDStudio lint / explicit voice binding
    ↓
downstream consumer such as Readio
    ↓
planning, synthesis, composition, or export
```

## How to use

Choose exactly one guide and attach it together with the task and any source material.

Example request:

> Follow the attached standalone SSMD authoring guide. Turn the supplied report into a 7-minute German interview podcast. Create a downloadable `.ssmd.md` file. Do not create audio.

The guides repeat their own technical rules. The LLM must not need another guide, a shared prompt fragment, a source checkout, an installed SSMDStudio wheel, local configuration, model discovery, or runtime documentation.

## Artifact mode

When the web harness can create files or artifacts, ask the LLM to:

1. Create exactly one UTF-8 `.ssmd.md` file.
2. Use a short descriptive kebab-case filename.
3. Put only SSMD source in the file.
4. Expose the file for download.
5. Create no helper files and no audio.

Use `.ssmd.md` for newly authored complete documents. SSMD tools may accept legacy `.ssmd` inputs for compatibility; the three starter documents managed by `ssmdstudio template` may keep their `.ssmd` filenames.

The generated file must not contain Markdown fences, surrounding explanation, shell commands, or unexpanded placeholders.

## Chat fallback mode

When file creation is unavailable, return the complete raw SSMD source directly in the response, without Markdown fences or surrounding explanation. Save that response as a `.ssmd.md` file before handing it to a downstream consumer.

## Downstream compatibility context

SSMDStudio authors SSMD 0.9 and does not depend on UtterPlan. For downstream Readio use, the current declared compatibility bounds are:

- SSMD >=0.9.3,<0.10
- UtterPlan >=0.4.0,<0.5
- UtterPlan semantic schema v4

These facts describe the downstream consumer, not a requirement on the authoring system or the contents of an SSMD file. A generated file should be structurally checked before downstream use; do not claim validation, binding, planning, rendering, or listening unless it actually occurred.

## Voice portability

A portable standalone-generated SSMD file:

1. does not require the authoring environment to know local configuration;
2. does not invent model-specific voice IDs;
3. uses no unnecessary provider-specific metadata;
4. keeps speaker roles symbolic when speaker distinction is necessary;
5. can be moved to another system for validation and downstream role resolution; and
6. may still require valid role binding at render time for multi-speaker content.

Portable does not mean guaranteed to render on every model with no later configuration. Concrete `voice_bindings` belong in the document only when the caller supplies provider-valid IDs and asks for them; otherwise role resolution is deferred to the downstream consumer.

## Guide catalog

- [`ssmd/general-narration.md`](ssmd/general-narration.md) — general narration
- [`ssmd/podcast-solo.md`](ssmd/podcast-solo.md) — one-speaker podcast or commentary
- [`ssmd/podcast-interview.md`](ssmd/podcast-interview.md) — host and guest interview
- [`ssmd/podcast-roundtable.md`](ssmd/podcast-roundtable.md) — moderated three-role discussion
- [`ssmd/news-briefing.md`](ssmd/news-briefing.md) — source-grounded news briefing
- [`ssmd/educational-explainer.md`](ssmd/educational-explainer.md) — tutorial or teaching audio
- [`ssmd/document-summary.md`](ssmd/document-summary.md) — faithful source summary
- [`ssmd/funny-story.md`](ssmd/funny-story.md) — comedy or funny story
- [`ssmd/dramatic-story.md`](ssmd/dramatic-story.md) — dramatic narrative or audiobook scene
- [`ssmd/kids-story.md`](ssmd/kids-story.md) — kids or bedtime story
- [`ssmd/audio-drama.md`](ssmd/audio-drama.md) — dialogue-forward audio drama
- [`ssmd/guided-meditation.md`](ssmd/guided-meditation.md) — meditation, grounding, or sleep narration
- [`ssmd/language-learning.md`](ssmd/language-learning.md) — listen/repeat or bilingual lesson
- [`ssmd/debate-pro-con.md`](ssmd/debate-pro-con.md) — balanced debate or tradeoff discussion
- [`ssmd/quiz-trivia.md`](ssmd/quiz-trivia.md) — quiz or trivia with thinking pauses

Keep these standalone guides distinct from the five-stage staged workflow pack in `prompts/workflows/funny-story/`. The standalone guide creates an SSMD artifact directly; workflow prompts operate on structured project context and produce artifacts for SSMDStudio's staged authoring workflow.

## Guide evaluations

[`../evals/`](../evals/) contains representative evaluation prompts and a manual content rubric. Content review is separate from hard syntax/roundtrip tests; CI does not generate model output or require synthesis, listening, or a provider.

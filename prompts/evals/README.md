# Standalone SSMD guide evaluation corpus

This corpus supports manual release review and optional model-to-model content evaluations. It contains one representative task for each of the 15 standalone guides, plus a source- or constraint-based task for six higher-risk formats: audio drama, dramatic story, funny story, kids' story, podcast interview, and podcast roundtable.

## Use

1. Choose exactly one guide from [`../standalone/ssmd/`](../standalone/ssmd/) and its matching prompt from [`prompts/`](prompts/).
2. Give both to the model under review, along with any source text included in the prompt.
3. Save the generated `.ssmd.md` artifact. Structural and roundtrip validation are separate checks; when available, run `ssmdstudio ssmd lint FILE.ssmd.md --roundtrip`.
4. Score the authoring/content with [`rubric.md`](rubric.md). Do not treat valid syntax as evidence of content quality, or a content score as proof of structural validity.
5. Record the model, guide revision, prompt, artifact, and any optional listening or downstream binding context separately.

Do not use another guide as a hidden shared include or treat one model's output as an expected-answer template. The tasks vary topics and structures so reviewers can notice whether a guide example is being cloned.

This is evaluation material, not a CI benchmark. External-model generation, synthesis, listening, and scoring are optional manual activities. Normal CI must not require a model, provider account, audio engine, or rendered audio.

## Prompt coverage

Each guide has a plain generative prompt:

- `audio-drama.md`
- `debate-pro-con.md`
- `document-summary.md`
- `dramatic-story.md`
- `educational-explainer.md`
- `funny-story.md`
- `general-narration.md`
- `guided-meditation.md`
- `kids-story.md`
- `language-learning.md`
- `news-briefing.md`
- `podcast-interview.md`
- `podcast-roundtable.md`
- `podcast-solo.md`
- `quiz-trivia.md`

The higher-risk formats also have a source- or constraint-based prompt:

- `audio-drama-source.md`
- `dramatic-story-constraints.md`
- `funny-story-source.md`
- `kids-story-constraints.md`
- `podcast-interview-source.md`
- `podcast-roundtable-source.md`

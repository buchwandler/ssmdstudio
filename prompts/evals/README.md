# Standalone SSMD guide evaluation corpus

This corpus supports manual release review and optional model-to-model content evaluations. It contains one representative task for each of the 26 standalone guides, plus a source- or constraint-based task for six higher-risk formats. Five image-input tasks use the reproducible image fixtures in `fixtures/images/`; two additional tasks cover exact reading and Markdown narration.

## Use

1. Choose exactly one guide from [`../standalone/ssmd/`](../standalone/ssmd/) and its matching prompt from [`prompts/`](prompts/).
2. Give both to the model under review, along with any source text included in the prompt. For `image-*.md` tasks, attach the named fixture image from `fixtures/images/`.
3. Save the generated `.ssmd.md` artifact. Structural and roundtrip validation are separate checks; when available, run `ssmdstudio ssmd lint FILE.ssmd.md --roundtrip`.
4. Score the authoring/content with [`rubric.md`](rubric.md). Do not treat valid syntax as evidence of content quality, or a content score as proof of structural validity.
5. Record the model, guide revision, prompt, artifact, and any optional listening or downstream binding context separately.

Do not use another guide as a hidden shared include or treat one model's output as an expected-answer template. The tasks vary topics and structures so reviewers can notice whether a guide example is being cloned.

This is evaluation material, not a CI benchmark. External-model generation, synthesis, listening, and scoring are optional manual activities. Normal CI must not require a model, provider account, audio engine, or rendered audio.

For manual content review, verify that different recurring speakers have unique, stable, non-reused symbolic roles and that pitch, rate, volume, or other effects are never doing identity work. Check scene and topic transitions in spoken context, plus a useful ending. For source-grounded tasks, check source fidelity and caveats. Mark audio-dependent claims unverified unless someone actually heard rendered audio; prompt inputs and SSMD markup alone are not listening evidence.

## Image fixtures

The five fixtures are small, reproducible visual inputs for manual review. They cover photographed text, a flowchart with a correction loop, whiteboard notes that distinguish ideas from decisions, a bar chart with visible values, and a three-panel storyboard. They are evaluation assets, not training examples and not guaranteed ground truth for every visual model.

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
- `faq-troubleshooting.md`
- `how-to-walkthrough.md`
- `meeting-recap.md`
- `timeline-biography.md`
- `image-text-to-ssmd.md`
- `image-diagram-to-ssmd.md`
- `image-whiteboard-to-ssmd.md`
- `image-chart-to-ssmd.md`
- `image-storyboard-to-ssmd.md`
- `verbatim-reading.md`
- `markdown-narration.md`

The higher-risk formats also have a source- or constraint-based prompt:

- `audio-drama-source.md`
- `dramatic-story-constraints.md`
- `funny-story-source.md`
- `kids-story-constraints.md`
- `podcast-interview-source.md`
- `podcast-roundtable-source.md`

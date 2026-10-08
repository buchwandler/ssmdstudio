# Manual SSMD authoring and audio-quality rubric

Score each dimension from 0 to 2. This is a content and authoring review, not structural validation or runtime preflight. Run hard syntax/roundtrip checks separately (for example, `ssmdstudio ssmd lint FILE.ssmd.md --roundtrip` when available). Do not infer content quality from valid syntax.

The rubric does not assume a particular renderer, provider, voice inventory, or audio engine. Listening is optional: when an audio-dependent judgment cannot be verified without rendered audio, mark it **unverified** rather than inferring it from SSMD markup. Do not require concrete voice bindings for a portable authoring artifact.

| Dimension                        | 0                                                                  | 1                                                               | 2                                                                                           |
| -------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Requested artifact and mode      | Wrong mode, malformed output, or incomplete artifact               | Usable with a correctable artifact issue                        | One complete standalone SSMD 0.9 artifact in the requested mode                             |
| Role stability                   | Recurring identities change or depend on prosody                   | Roles are mostly stable, with attribution ambiguity             | Stable symbolic roles and clear spoken introductions or transitions                         |
| Speaker distinction              | Turns are confusing without a particular rendered voice            | Roles are identifiable with occasional ambiguity                | Wording, context, and attribution keep speakers clear without relying on voice effects      |
| Audio-only comprehension         | Requires markup, page layout, or visual inference                  | Mostly understandable, with a few unclear references or actions | Topic, scene, action, and references are clear in audio alone                               |
| Narrated context and transitions | Missing context makes the sequence hard to follow                  | Basic progression exists, but some transitions are unclear      | Narration and transitions make changes in time, place, speaker, or topic easy to follow     |
| Requested length and pacing      | Clearly ignores the request or pads/drops necessary content        | Approximate fit with some pacing or scope issues                | Useful content and pause budget fit the request; no exact render time is assumed            |
| Prosody restraint                | Effects define identity or decorate many lines                     | Some unnecessary or stacked effects                             | Sparse, purposeful changes serve meaning or timing                                          |
| Pause usefulness                 | Pauses interrupt, arrive too soon, or are decorative               | Some pauses help, others feel mistimed or excessive             | Pauses support thinking, breathing, suspense, comedy, learning, or interaction              |
| Semantic portability             | Meaning depends on provider IDs or nonportable runtime assumptions | Mostly portable, with avoidable runtime-specific material       | Meaning survives downstream role resolution; no invented IDs or engine-specific assumptions |
| Example non-cloning              | Reuses the guide example's premise, roles, or progression          | Noticeable scaffolding overlap                                  | Independently structured and clearly unrelated to the guide example                         |
| Natural spoken language          | Stilted, repetitive, or consistently staccato                      | Understandable but uneven                                       | Varied, coherent, and natural when spoken                                                   |
| Ending quality                   | Abrupt, unresolved, or introduces an unrelated idea                | Concludes, but weakly or repetitively                           | Resolves or closes the requested arc without unnecessary padding                            |

## Source-grounded tasks

Score these separately when the prompt supplies source material:

| Dimension                           | 0                                                              | 1                                                  | 2                                                               |
| ----------------------------------- | -------------------------------------------------------------- | -------------------------------------------------- | --------------------------------------------------------------- |
| Source fidelity                     | Material is distorted or unsupported claims are added          | Mostly faithful, with a lost distinction or caveat | Claims and attribution remain faithful to the supplied material |
| Caveats and uncertainty             | Caveats disappear or uncertainty becomes fact                  | Most caveats survive, with some flattening         | Scope, uncertainty, and limits remain clear in spoken form      |
| Invented quotes or personal details | Adds unsupported quotes, biography, credentials, or experience | Includes a minor unsupported detail                | Adds no unsupported quotes or personal details                  |

## Review record

Record the prompt filename, guide filename and revision, model and date, artifact path, scores, any unverified audio-dependent judgments, and brief evidence for every score below 2. Record whether optional rendering/listening or downstream binding occurred; do not claim validation, rendering, or listening unless it actually happened.

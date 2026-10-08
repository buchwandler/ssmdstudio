# SSMD authoring migration fixtures

These fixtures capture the behavior to preserve while moving Readio-owned authoring capabilities into SSMDStudio. They are standalone data, not imports from Readio.

## Audited source baseline

- Readio's packaged starter documents are `../readio/readio/resources/templates/{briefing,dialogue,podcast}.ssmd`; all use `ssmd_version: '0.9'` and symbolic roles (`narrator`, `host`, `guest`, `analyst`).
- The relevant behavior suites are Readio's `tests/test_templates.py`, `tests/test_template_validate.py`, and `tests/test_ssmd_authoring_09.py`. Coverage to translate includes seed idempotence, reset, forced add, traversal refusal, `.ssmd.md` logical names and output suffix, structural lint, strict SSMD 0.9 parsing, and binding roundtrip/failure behavior. Studio tests must exercise Studio's own public API/CLI and must not import Readio.
- The installed SSMD runtime is 0.9.3 and exports `parse_structure`, `parse_front_matter`, `merge_generated_header`, and `serialize_front_matter`. These are the candidate public APIs for loss-preserving binding edits; check them against the declared bounded dependency during implementation.
- All 15 guide filenames exist on both sides. Their contents differ: the Studio/Readio line counts and unified-diff additions/removals are recorded below so reconciliation is selective rather than a wholesale replacement.

| Guide                    | Studio/Readio lines | Diff additions/removals |
| ------------------------ | ------------------: | ----------------------: |
| audio-drama.md           |             362/375 |                   95/82 |
| debate-pro-con.md        |             364/374 |                   74/64 |
| document-summary.md      |             344/358 |                   77/63 |
| dramatic-story.md        |             360/371 |                   77/66 |
| educational-explainer.md |             350/357 |                   73/66 |
| funny-story.md           |             371/385 |                  110/96 |
| general-narration.md     |             340/353 |                   74/61 |
| guided-meditation.md     |             344/355 |                   74/63 |
| kids-story.md            |             363/373 |                   69/59 |
| language-learning.md     |             367/388 |                   89/68 |
| news-briefing.md         |             347/355 |                   74/66 |
| podcast-interview.md     |             369/380 |                   75/64 |
| podcast-roundtable.md    |             365/375 |                   70/60 |
| podcast-solo.md          |             350/353 |                   86/83 |
| quiz-trivia.md           |             349/365 |                   78/62 |

## Fixture intent

- `binding-preservation.ssmd.md` exercises preservation of the original SSMD version, unknown header keys, a second provider namespace, Unicode, directive syntax, and exact body text while adding/updating one explicit provider.
- `legacy-div.ssmd` is an invalid legacy directive sample: authoring/binding must fail before creating an output.
- `readio-preflight.ssmd.md` is the provider-neutral handoff fixture for the opt-in sibling-repository smoke. The test lints and binds a temporary copy with Studio, then runs the current Readio `render --dry-run --json` preflight without rendering audio or importing Readio into Studio.
- Tests should also generate CRLF, malformed CLI JSON, timeout, collision, symlink, and simulated atomic-write failures as temporary inputs; those cases are environment-dependent and are intentionally not frozen in files here.

## Optional cross-repository smoke

Run `SSMDSTUDIO_READIO_SMOKE=1 python -m pytest -q tests/test_readio_smoke.py` from the Studio checkout to lint and bind the fixture with Studio, then pass a temporary bound copy to the sibling `../readio` render preflight (`--dry-run --json`). This requires the optional `ssmd` CLI and current Readio dependencies. No audio is rendered and no files are written into the Readio checkout.

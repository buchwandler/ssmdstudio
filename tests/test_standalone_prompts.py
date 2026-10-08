from __future__ import annotations

import re
from pathlib import Path

import pytest

PROMPT_ROOT = Path(__file__).parents[1] / "prompts"
GUIDE_DIR = PROMPT_ROOT / "standalone" / "ssmd"
EVAL_ROOT = PROMPT_ROOT / "evals"
EXPECTED_GUIDES = {
    "audio-drama.md",
    "debate-pro-con.md",
    "document-summary.md",
    "dramatic-story.md",
    "educational-explainer.md",
    "funny-story.md",
    "general-narration.md",
    "guided-meditation.md",
    "kids-story.md",
    "language-learning.md",
    "news-briefing.md",
    "podcast-interview.md",
    "podcast-roundtable.md",
    "podcast-solo.md",
    "quiz-trivia.md",
}

EXPECTED_EVAL_PROMPTS = {
    "audio-drama.md",
    "audio-drama-source.md",
    "debate-pro-con.md",
    "document-summary.md",
    "dramatic-story-constraints.md",
    "dramatic-story.md",
    "educational-explainer.md",
    "funny-story-source.md",
    "funny-story.md",
    "general-narration.md",
    "guided-meditation.md",
    "kids-story-constraints.md",
    "kids-story.md",
    "language-learning.md",
    "news-briefing.md",
    "podcast-interview-source.md",
    "podcast-interview.md",
    "podcast-roundtable-source.md",
    "podcast-roundtable.md",
    "podcast-solo.md",
    "quiz-trivia.md",
}
REQUIRED_SECTIONS = {
    "Mission",
    "Output contract",
    "Audio quality contract",
    "Target runtime",
    "Content integrity",
    "Final self-check",
    "Generation procedure",
}
SHARED_SECTIONS = REQUIRED_SECTIONS - {"Mission", "Target runtime"}
KNOWN_DEFAULT_VOICE_IDS = {
    "af_sarah",
    "am_michael",
    "af_bella",
    "am_adam",
    "bf_emma",
    "bm_george",
}


def _section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text)
    assert match, f"missing section: {heading}"
    return match.group(1).strip()


def _guides() -> list[tuple[Path, str]]:
    paths = sorted(GUIDE_DIR.glob("*.md"))
    assert {path.name for path in paths} == EXPECTED_GUIDES
    return [(path, path.read_text(encoding="utf-8")) for path in paths]


def test_standalone_catalog_has_exact_kebab_case_inventory() -> None:
    paths = sorted(GUIDE_DIR.glob("*.md"))
    assert len(paths) == 15
    assert {path.name for path in paths} == EXPECTED_GUIDES
    assert all(re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.md", path.name) for path in paths)


def test_guides_are_self_contained_with_required_sections_and_ssmd_09_examples() -> None:
    for path, text in _guides():
        assert len(re.findall(r"^# (?!#)", text, flags=re.MULTILINE)) == 1, path.name
        assert REQUIRED_SECTIONS <= set(re.findall(r"^## (.+)$", text, flags=re.MULTILINE)), (
            path.name
        )
        lowered = text.casefold()
        for phrase in (
            "this file is a complete instruction set",
            "without python",
            "a readio installation",
            "an agent skill",
            "ssmd tooling",
            "local model discovery",
        ):
            assert phrase in lowered, (path.name, phrase)
        assert "ssmd_version: '0.9'" in _section(text, "Target runtime"), path.name
        assert "ssmd_version: '0.9'" in _section(text, "Minimal pattern example"), path.name
        header = _section(text, "Recommended default header")
        assert re.search(r"(?m)^ssmd_version: (?:'0\.9'|\"0\.9\")$", header), path.name


def test_guides_preserve_standalone_output_contract_and_model_agnostic_voice_policy() -> None:
    for path, text in _guides():
        lowered = text.casefold()
        output = _section(text, "Output contract").casefold()
        final = _section(text, "Final self-check")
        assert "downloadable files or artifacts" in output, path.name
        assert "exactly one utf-8" in output, path.name
        assert "`.ssmd.md` filename" in output, path.name
        assert "ssmd tools may accept legacy `.ssmd` inputs for compatibility" in output, path.name
        assert "fallback chat mode" in lowered, path.name
        assert "complete raw ssmd source" in output, path.name
        assert "markdown code fences" in output, path.name
        assert "do not create helper files" in output, path.name
        assert (
            "do not claim that structural validation or audio rendering was executed" in output
        ), path.name
        assert "do not invent concrete model or voice ids" in lowered, path.name
        assert "voice_bindings" in text, path.name
        assert "No invented concrete voice IDs" in final, path.name
        assert "unexpanded placeholders" in final, path.name
        assert not KNOWN_DEFAULT_VOICE_IDS.intersection(text.split()), path.name


def test_shared_technical_sections_do_not_drift() -> None:
    texts = [text for _, text in _guides()]
    for heading in SHARED_SECTIONS:
        assert len({_section(text, heading) for text in texts}) == 1, heading

    for path, text in _guides():
        target = _section(text, "Target runtime")
        assert ":::" in target and "::{" in target, path.name
        assert "three ASCII colon characters" in target, path.name
        assert "followed immediately by `{`" in target, path.name
        assert "invalid" in target.casefold(), path.name


def test_guide_authorship_branding_and_downstream_compatibility_are_current() -> None:
    compatibility_blocks: list[str] = []
    for path, text in _guides():
        assert not re.search(r"(?im)^# .*readio", text), path.name
        target = _section(text, "Target runtime")
        compatibility_blocks.append(target.split("### Canonical directive fences", 1)[0].strip())
        assert "SSMD >=0.9.3,<0.10" in target, path.name
        assert "UtterPlan >=0.4.0,<0.5" in target, path.name
        assert "UtterPlan semantic schema v4" in target, path.name
        assert "SSMDStudio does not depend on UtterPlan" in target, path.name
        assert "0.3.0" not in target, path.name
        assert "schema-v3" not in target.casefold(), path.name
    assert len(set(compatibility_blocks)) == 1


def test_all_guides_share_audio_quality_contract_and_audio_drama_has_narrator() -> None:
    required = (
        "listener who cannot see",
        "narrated context",
        "distinct, stable symbolic `voice` role",
        "never reuse a role for a different speaker",
        "pitch, rate, volume, emphasis, pauses, and other prosody affect delivery only, never identity",
        "distinct supported symbolic role",
        "spoken introductions",
        "brief action beats as needed",
        "restore context after a long dialogue run",
        "visual-only information",
        "natural, varied speech",
        "requested duration",
        "keep semantics portable",
        "speaker-role mapping",
        "relationship dynamics",
        "distinctive style",
    )
    role_prosody_pattern = re.compile(
        r'(?m)^:::[{].*(?:voice="[^"]+".*(?:pitch|rate|volume)=|(?:pitch|rate|volume)=.*voice="[^"]+")'
    )
    for path, text in _guides():
        contract = _section(text, "Audio quality contract").casefold()
        for phrase in required:
            assert phrase in contract, (path.name, phrase)
        assert not role_prosody_pattern.search(text), path.name

    drama = _section(
        (GUIDE_DIR / "audio-drama.md").read_text(encoding="utf-8"),
        "Use-case voice design",
    ).casefold()
    assert "narrator" in drama
    assert "essential scene information" in drama


def test_catalog_readme_documents_ssmd_authoring_and_runtime_template_distinction() -> None:
    readme = (PROMPT_ROOT / "standalone" / "README.md").read_text(encoding="utf-8")
    lowered = readme.casefold()
    assert "downloadable .ssmd.md file" in lowered
    assert "create exactly one utf-8 `.ssmd.md` file" in lowered
    assert "legacy `.ssmd`" in lowered
    assert "starter documents managed by `ssmdstudio template`" in lowered
    assert "audio-first quality" in lowered
    assert "never reuse a role" in lowered
    assert (
        "pitch, rate, volume, and other prosody are temporary delivery choices, not speaker identity"
        in lowered
    )
    assert "does not establish readio renderability" in lowered
    assert "mark listening claims unverified" in lowered
    assert not list(PROMPT_ROOT.rglob("*.ssmd"))
    assert not (PROMPT_ROOT / "standalone" / "readio" / "SKILL.md").exists()


def test_package_readme_documents_audio_first_and_renderability_boundary() -> None:
    readme = Path(__file__).parents[1] / "README.md"
    lowered = readme.read_text(encoding="utf-8").casefold()
    assert "audio-first" in lowered
    assert (
        "never use pitch, rate, volume, or other acoustic qualities as speaker identity" in lowered
    )
    assert "a pass does not establish renderability by readio or another consumer" in lowered
    assert "does not resolve semantic plans, synthesize, listen to, or export audio" in lowered


def test_evaluation_corpus_is_complete_and_separate_from_hard_validation() -> None:
    prompt_dir = EVAL_ROOT / "prompts"
    paths = sorted(prompt_dir.glob("*.md"))
    assert {path.name for path in paths} == EXPECTED_EVAL_PROMPTS
    assert len(paths) == 21
    assert (EVAL_ROOT / "README.md").is_file()
    assert (EVAL_ROOT / "rubric.md").is_file()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "standalone ssmd 0.9 document" in text.casefold(), path.name
        assert (
            "do not claim validation, rendering, or listening unless it occurred" in text.casefold()
        ), path.name

    corpus = (EVAL_ROOT / "README.md").read_text(encoding="utf-8").casefold()
    rubric = (EVAL_ROOT / "rubric.md").read_text(encoding="utf-8").casefold()
    assert "not a ci benchmark" in corpus
    assert "structural and roundtrip validation are separate checks" in corpus
    assert "not structural validation or runtime preflight" in rubric
    assert (
        "does not assume a particular renderer, provider, voice inventory, or audio engine"
        in rubric
    )
    assert "mark it **unverified**" in rubric
    assert "unique, stable, non-reused symbolic roles" in corpus
    assert "pitch, rate, volume, or other effects are never doing identity work" in corpus
    assert "spoken context" in corpus
    assert "useful ending" in corpus
    assert "source fidelity and caveats" in corpus
    assert "distinct, stable, non-reused symbolic role" in rubric
    assert "pitch/rate/volume or other effects define identity" in rubric
    assert "action beats restore context after long dialogue" in rubric
    assert "ending quality" in rubric
    assert "source fidelity" in rubric


def test_ssmd_examples_parse_when_runtime_is_available() -> None:
    runtime = pytest.importorskip("ssmd")
    parser = getattr(runtime, "parse_ssmd", None) or getattr(runtime, "parse_ssmd_09", None)
    if parser is None:
        pytest.skip("installed ssmd runtime does not expose a parser entry point")

    for path, text in _guides():
        examples = re.findall(r"```ssmd\n(.*?)```", text, flags=re.DOTALL)
        assert examples, path.name
        for source in examples:
            assert re.search(r"(?m)^::\{", source) is None, path.name
            parser(source)

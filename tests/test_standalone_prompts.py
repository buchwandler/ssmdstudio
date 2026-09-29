from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

PROMPT_ROOT = Path(__file__).parents[1] / "prompts"
GUIDE_DIR = PROMPT_ROOT / "standalone" / "ssmd"
EXPECTED_HASHES = {
    "audio-drama.md": "d930ddb9275f7d3c6f3f76ab1402df9349dbff7c30d81f64a09cf10db5c97cf3",
    "debate-pro-con.md": "d2d8689a832c590c936aedb50f606b9d24c04081fc29bdfc153b11fa63d81604",
    "document-summary.md": "5abbf76c8e2b4ef33afeff8615d9d48a6dc9d95b517d467843cc908512587abf",
    "dramatic-story.md": "71ec0610379fa01fbd4b0a446f073f616b8d35ededaca08d8a5171d199822228",
    "educational-explainer.md": "b54306680cc117afe77782dc44d6bbdb830dbe89817e3667719de4db35383f25",
    "funny-story.md": "004ff355db9483971aa1361f14291c1938b869a2e4d198a5c4090272fcd99064",
    "general-narration.md": "14dfe5a1dd53ff2c3e6d62da6528e21d18c67ecb84c1e514775aaaacdd664561",
    "guided-meditation.md": "795e445703d0e342f76a90b658f27a8484afd553cda21bec9f34569f0bd08941",
    "kids-story.md": "82d747b46531e153df5d2b136031d9702236ef59a57d261e5175cb00a04aee97",
    "language-learning.md": "be803a387650157f5aaf011655f634c1b0377c398ea9a2dca23aebe3362f2e0c",
    "news-briefing.md": "de06f1bab6ba4b9bdb3e0ecfcb747f502a8a6e1ed54fed0fa17176c84bb23169",
    "podcast-interview.md": "35be6a15588e65101431c4331b89b6f16f6f93f4139140bce63e6e8140bae184",
    "podcast-roundtable.md": "9d1442c359f72133bc5c13ff7787c77c32023c02e092a7b7c974fc8be46b0261",
    "podcast-solo.md": "4c7466fd2d3a0249ac19e083d9df11937d4b29d62ec6e92e6af52c960dd8b41f",
    "quiz-trivia.md": "6fb99b94ac9c7746532bba119c4d127621835d4f9c07ada54e1144f32d278b9a",
}
REQUIRED_SECTIONS = {
    "Mission",
    "Output contract",
    "Target runtime",
    "Content integrity",
    "Final self-check",
    "Generation procedure",
}
SHARED_SECTIONS = REQUIRED_SECTIONS - {"Mission"}
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
    assert {path.name for path in paths} == set(EXPECTED_HASHES)
    return [(path, path.read_text(encoding="utf-8")) for path in paths]


def test_standalone_catalog_has_exact_hashed_kebab_case_inventory() -> None:
    paths = sorted(GUIDE_DIR.glob("*.md"))
    assert len(paths) == 15
    assert {path.name for path in paths} == set(EXPECTED_HASHES)
    assert all(re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.md", path.name) for path in paths)
    for path in paths:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_HASHES[path.name]


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
            "readio agent skill",
            "local ssmd tooling",
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
        assert "accept `.ssmd` for compatibility" in output, path.name
        assert "fallback chat mode" in lowered, path.name
        assert "complete raw ssmd source" in output, path.name
        assert "markdown code fences" in output, path.name
        assert "do not create helper files" in output, path.name
        assert "do not claim that readio/ssmd validation" in output, path.name
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


def test_catalog_readme_documents_ssmd_authoring_and_runtime_template_distinction() -> None:
    readme = (PROMPT_ROOT / "standalone" / "README.md").read_text(encoding="utf-8")
    lowered = readme.casefold()
    assert "downloadable .ssmd.md file" in lowered
    assert "create exactly one utf-8 `.ssmd.md` file" in lowered
    assert "legacy `.ssmd`" in lowered
    assert "existing runtime templates managed by `readio template`" in lowered
    assert not list(PROMPT_ROOT.rglob("*.ssmd"))
    assert not (PROMPT_ROOT / "standalone" / "readio" / "SKILL.md").exists()


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

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

LANGS = ["en", "zh", "ru", "ja", "ko", "es"]
ALLOWED_FUNCTIONS = {
    "Role", "FirstLastFrame", "Camera", "Shot", "Lens", "Lighting", "Motion",
    "VFX", "Audio", "Text", "Editing", "Constraint", "Constraints", "Safety",
}
STRICT_REQUIRED_FUNCTIONS = {"Role", "FirstLastFrame", "Camera", "Audio", "Text", "Editing", "Constraint", "Safety"}
PROTECTED_TERMS = ["Studio Ghibli", "Ghibli", "Spider-Man", "Disney", "Marvel"]
NATIVE_REVIEW_FIXTURE = "evals/multilingual-native-review.json"
NATIVE_REVIEW_RUBRIC = "references/multilingual-native-review.md"
NATIVE_REVIEW_EVIDENCE = "evals/multilingual-native-review-evidence.json"
EXPECTED_RUBRIC_SHA256 = "214fb2dcf10ef24195ee16873f43b86b6edccf9bbda0c868b65f3bfeafec2e16"
EXPECTED_REVIEW_PROTOCOL_SHA256 = "131618e662fe7074aa344b18041a690888ee5ab98c81394754d63bd6b8574c9e"
EXPECTED_EVIDENCE_PURPOSE = (
    "Store CI-validated review-record structures bound to the exact current fixture input and "
    "review protocol. An empty list means no completed language-quality review has "
    "been submitted."
)
EXPECTED_COMMON_BRIEF = (
    "Direct one restrained closing-time beat at a small food counter. Duration is fixed at "
    "eight seconds by the surface, outside prompt prose. An older proprietor silently shows "
    "care to a younger regular. Use one visible action, one camera move with an endpoint, one "
    "motivated practical light, and room tone. @Image1 owns identity and wardrobe. @Video1 "
    "controls camera rhythm only. @Audio1 controls tempo only. Do not generate on-screen text."
)
EXPECTED_COMMON_BRIEF_SHA256 = hashlib.sha256(EXPECTED_COMMON_BRIEF.encode("utf-8")).hexdigest()
EXPECTED_REVIEW_CASES = {
    "zh-CN": {
        "id": "zh_cn_bowl_pause_closing_time",
        "script": "Hans",
        "script_re": r"[\u4e00-\u9fff]",
        "candidate_sha256": "d4137600b8e20533886e64f0260ab6732dcdf3c68c9e69c43125b162d533e0dd",
        "binding_span_sha256": [
            "603bfee74fe746487f3accd227a7c8840ca4617f01b2c16919ac2dbff8514b7a",
            "2d19fc1020c7f720160e808921c7fdbba1013dab2fa3e6ad96299f99480edde8",
            "7838e72447b4b17ca988aa8dbef028bae3596c071e110cebd7403d1b61ef2b47",
        ],
    },
    "ja-JP": {
        "id": "ja_jp_two_beat_hold_closing_time",
        "script": "Jpan",
        "script_re": r"[\u3040-\u30ff]",
        "candidate_sha256": "6b32e63be46a5d41674488b0a5c89aa73b0758b5ae7aeaedd4494b8181a7eb3d",
        "binding_span_sha256": [
            "15ce0659570eab244374cbcac9699ffe451c62601eab0570afbdcb7241e2097b",
            "8bf6f9085ecc66876aacb4e5afcabd1198f9646006879c49b00170b19509de81",
            "a562f29025fd65c91cbbdc5e261fff7780488199980238f58f965b3fec2dd32e",
        ],
    },
    "ko-KR": {
        "id": "ko_kr_glove_bag_closing_time",
        "script": "Kore",
        "script_re": r"[\uac00-\ud7a3]",
        "candidate_sha256": "07f38b3460ebb9c3f435941b7a24ea1e29c1a8f9684df3342fdd9cc679b13438",
        "binding_span_sha256": [
            "dd4b6aadbedb538e7be82c2dd09525d3a7d3eeac6589577a157411a1962ee989",
            "82b0be6ed180478ea541b01dc9a9d5476a20056bdc876234ea112b0346ab41e8",
            "5791ae30eaf0823dc38e4bedc40a61f536b51475f5398da19878a2b96f09c961",
        ],
    },
}
# Intentionally non-derived: advancing an input requires a visible revision, round, and digest edit here.
EXPECTED_REVIEW_INPUT_PINS = {
    "zh-CN": {
        "fixture_revision": 2,
        "review_round": 2,
        "review_input_sha256": "19eab52fd794813e899e53e34602332ba15402db3b02f5ca753a3c8de83e86ce",
    },
    "ja-JP": {
        "fixture_revision": 2,
        "review_round": 2,
        "review_input_sha256": "9d2f4e2538477f223889b06b6b401cc43b39b18c4ca46f6b6e76b9a7ee1a87ba",
    },
    "ko-KR": {
        "fixture_revision": 2,
        "review_round": 2,
        "review_input_sha256": "3edaafa0cd9413ef78e6a7bf92e82f513a5773b9402d975fdc5c469ce3b4b7b0",
    },
}
EXPECTED_REFERENCE_TOKEN_BYTES = [
    {"token": "@Image1", "utf8_hex": "40496d61676531"},
    {"token": "@Video1", "utf8_hex": "40566964656f31"},
    {"token": "@Audio1", "utf8_hex": "40417564696f31"},
]
EXPECTED_REFERENCE_ROLES = [
    ("@Image1", "identity_and_wardrobe"),
    ("@Video1", "camera_rhythm_only"),
    ("@Audio1", "tempo_only"),
]
EXPECTED_STATIC_SCOPE = {
    "fixture structure",
    "source-path existence",
    "byte-exact reference-token preservation",
    "canonical reference-binding span integrity",
    "non-derived canonical review-input pins",
    "literal cross-locale realization overlap",
    "pending-review claim boundary",
    "best-effort English known-phrase lint on declared public text surfaces",
}
EXPECTED_LIMITATIONS = {
    "native fluency",
    "cultural authenticity",
    "native authorship",
    "author provenance",
    "semantic differentiation across locales",
    "reference-role semantic correctness",
    "reviewer identity",
    "reviewer qualifications",
    "truth or adequacy of reviewer reasoning",
    "model output quality",
    "generated-video quality",
}
EXPECTED_REVIEW_DIMENSIONS = {
    "brief_and_reference_fidelity": ("both", False, True),
    "idiomatic_production_language": ("target-locale language editor", False, False),
    "language_register_and_relationship": ("target-locale language editor", False, False),
    "creative_lens_realization": ("target-locale culture and production reviewer", False, False),
    "production_directability": ("target-locale culture and production reviewer", False, False),
    "representation_and_stereotype_risk": ("both", False, True),
}
EXPECTED_CRITERION_QUOTE_SOURCES = {
    criterion_id: "candidate_prompt" for criterion_id in EXPECTED_REVIEW_DIMENSIONS
}
EXPECTED_CRITERION_EVIDENCE_ANCHORS = {
    "zh-CN": {
        "brief_and_reference_fidelity": ["@Image1锁定店主与年轻熟客的身份和衣着"],
        "idiomatic_production_language": ["镜头从双人中景缓慢推进，到碗与两只手同框时停住"],
        "language_register_and_relationship": ["店主不说话，把最后一碗热汤推到年轻熟客面前"],
        "creative_lens_realization": ["两只手与碗同时进入画面后保持两拍"],
        "production_directability": ["到碗与两只手同框时停住"],
        "representation_and_stereotype_risk": ["收银台边缘留着一小块擦拭后的水痕"],
    },
    "ja-JP": {
        "brief_and_reference_fidelity": ["@Image1で店主と若い常連客の顔・髪・衣装を固定する"],
        "idiomatic_production_language": ["カメラは入口側からカウンターに沿ってゆっくり横移動し"],
        "language_register_and_relationship": ["会話なし、換気扇と引き出しが閉まる音だけ"],
        "creative_lens_realization": ["動作の後も二拍そのまま保持する"],
        "production_directability": ["手が画面を離れたところでカメラを止める"],
        "representation_and_stereotype_risk": ["店主は会計皿の横に温かいおしぼりを一枚置く"],
    },
    "ko-KR": {
        "brief_and_reference_fidelity": ["@Image1로 주인과 젊은 단골의 얼굴·머리·의상을 고정한다"],
        "idiomatic_production_language": ["카메라는 두 사람의 미디엄 숏에서 봉투 쪽으로 천천히 틸트 다운하고"],
        "language_register_and_relationship": ["주인은 말없이 단골이 두고 간 장갑을 종이봉투에 넣어 가방 손잡이에 건다"],
        "creative_lens_realization": ["대사 없이 환풍기와 종이봉투가 접히는 소리만 남긴다"],
        "production_directability": ["봉투 손잡이가 단골의 가방 손잡이에 걸리면 멈춘다"],
        "representation_and_stereotype_risk": ["단골이 두고 간 장갑을 종이봉투에 넣어 가방 손잡이에 건다"],
    },
}
MINIMUM_TARGET_SCRIPT_CHARACTERS_PER_QUOTE = 8
MINIMUM_REASON_CHARACTERS = 32
MINIMUM_REASON_ALPHANUMERIC_CHARACTERS = 12
REVIEWER_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+@:/-]{2,127}\Z")

# The disclaimer record is an exact byte contract. The separate prose linter is
# deliberately described as best-effort: it cannot prove the absence of a
# semantic claim in arbitrary natural language.
PUBLIC_CLAIM_ALLOWLIST_VERSION = "public-claim-disclaimer-v1"
PUBLIC_CLAIM_CANONICAL_DISCLAIMER = (
    "Static validation cannot establish native fluency, native-language quality, "
    "cultural authenticity, native authorship, author provenance, reviewer identity or "
    "qualifications, model-output quality, or generated-video quality;\n"
    "independent human review remains required."
)
PUBLIC_CLAIM_CANONICAL_DISCLAIMER_SHA256 = (
    "6b678ea969ed788b8968d55eba0a8f2806570edbd623b6ab025872c8c0e9ef2c"
)
EXPECTED_PUBLIC_CLAIM_ALLOWLIST = [
    {
        "path": "references/multilingual-native-review.md",
        "text_lf": PUBLIC_CLAIM_CANONICAL_DISCLAIMER,
        "sha256_lf": PUBLIC_CLAIM_CANONICAL_DISCLAIMER_SHA256,
        "line_endings": "LF_or_CRLF_only",
    }
]
PUBLIC_CLAIM_LINT_POLICY = {
    "version": "public-claim-lint-v1",
    "guarantee": "best_effort_english_known_phrase_lint_only",
    "included_files": "tracked_or_unignored_regular_utf8_outside_excluded_roots",
    "excluded_roots": [
        ".git", ".seedance_backups", "__pycache__", "assets", "evals", "scripts", "tests"
    ],
    "max_bytes": 2_000_000,
}
PUBLIC_CLAIM_DASH_SET_VERSION = "public-claim-dashes-v1"
# Explicit and versioned: do not delegate this security boundary to a moving
# Unicode category database. It includes the commonly confusable hyphen/dash,
# minus, wave-dash, and vertical presentation forms accepted by the scanner.
PUBLIC_CLAIM_DASH_CODEPOINTS = (
    0x002D,
    0x00AD,
    0x058A,
    0x05BE,
    0x1400,
    0x1806,
    0x2010,
    0x2011,
    0x2012,
    0x2013,
    0x2014,
    0x2015,
    0x2043,
    0x2053,
    0x207B,
    0x208B,
    0x2212,
    0x2E17,
    0x2E1A,
    0x2E3A,
    0x2E3B,
    0x2E40,
    0x2E43,
    0x2E5D,
    0x301C,
    0x3030,
    0x30A0,
    0xFE31,
    0xFE32,
    0xFE58,
    0xFE63,
    0xFF0D,
    0x10EAD,
)
PUBLIC_CLAIM_DASH_LABELS = tuple(
    f"U+{codepoint:04X}" for codepoint in PUBLIC_CLAIM_DASH_CODEPOINTS
)
PUBLIC_CLAIM_DASH_CHARACTERS = frozenset(
    chr(codepoint) for codepoint in PUBLIC_CLAIM_DASH_CODEPOINTS
)
PUBLIC_KNOWN_CLAIM_RE = re.compile(
    r"\b(?:"
    r"native[- ]+(?:authors?|authored|authorship|fluent|fluency|quality|readers?|"
    r"speakers?|writing)|"
    r"native[- ]+(?:chinese|language|speaker)(?:[- ]+prompt)?[- ]+(?:authored|docs?|"
    r"examples?|guidance|quality|readers?|writing)|"
    r"native[- ]+(?:equivalent|grade|caliber|standard|level|like|edited|written|"
    r"verified|linguistic)(?:[- ]+language)?(?:[- ]+(?:command|copy|fluent|fluency|"
    r"idiomaticity|localization|proficiency|prompts?|prose|quality|translations?|"
    r"writing))?|"
    r"natively[- ]+(?:authored|edited|fluent|written)|"
    r"(?:reads?|feels?|sounds?|passes)(?:[- ]+as)?(?:[- ]+like)?[- ]+(?:a[- ]+)?native|"
    r"reviewed[- ]+by[- ]+native[- ]+editors?|"
    r"(?:authored|written)[- ]+by[- ]+(?:a[- ]+)?native(?:[- ]+speakers?)?|"
    r"(?:first[- ]+language|l1)[- ]+(?:fluency|quality|writing)|"
    r"author[- ]+provenance|culturally[- ]+authentic|cultural[- ]+authenticity|"
    r"reviewer[- ]+(?:identity|qualifications)|feel[- ]+native|"
    r"mother[- ]+tongue(?:[- ]+(?:fluency|quality))?|"
    r"model(?:['’]s)?[- ]+output[- ]+quality|"
    r"(?:(?:generated|rendered)[- ]+)?(?:clip|video)[- ]+quality"
    r")\b",
    re.IGNORECASE,
)
MARKDOWN_STRUCTURAL_LINE_RE = re.compile(
    r"^(?:#{1,6}\s|[-+*]\s|\d+[.)]\s|>\s?|```|~~~|\|)"
)
EXPECTED_ADVERSARIAL_GATES = {
    "reference-token-confusable": "machine_fixture_check",
    "pan-cjk-template-copy": "machine_literal_overlap_and_independent_review",
    "bare-register-label": "native_review",
    "stereotype-substitution": "native_review",
    "static-native-quality-claim": "claim_boundary",
    "model-output-inference": "claim_boundary",
}
EXPECTED_PRODUCTION_CONTRACT_FIELDS = {
    "action", "camera_endpoint", "practical_light", "room_tone", "textless_delivery"
}
TOKEN_LIKE_RE = re.compile(r"[@＠](?:[^\W\d_]+)\d+", re.UNICODE)
EXPECTED_NATIVE_REVIEW_ROOT_FIELDS = {
    "schema_version",
    "rubric",
    "review_evidence",
    "rubric_sha256",
    "review_protocol_sha256",
    "purpose",
    "review_state",
    "model_output_state",
    "generated_video_state",
    "native_quality_verified",
    "static_validation_scope",
    "static_checks_do_not_establish",
    "review_policy",
    "rubric_dimensions",
    "cases",
    "adversarial_contract",
}
EXPECTED_NATIVE_REVIEW_CASE_FIELDS = {
    "id",
    "locale",
    "script",
    "fixture_revision",
    "review_round",
    "source_paths",
    "common_brief",
    "common_brief_sha256",
    "external_controls",
    "reference_token_bytes",
    "reference_bindings",
    "creative_lens_hypothesis",
    "language_register",
    "production_contract",
    "criterion_evidence_anchors",
    "candidate_prompt",
    "candidate_sha256",
    "review_input_sha256",
    "review_record",
}
REVIEW_INPUT_EXCLUDED_FIELDS = {"review_input_sha256", "review_record"}
REVIEWER_ROLES = {
    "target-locale language editor",
    "target-locale culture and production reviewer",
}
REVIEW_VERDICTS = {"pass", "revise", "fail"}
QUOTE_SOURCES = set(EXPECTED_CRITERION_QUOTE_SOURCES.values())
REVIEW_SET_FIELDS = {
    "case_id",
    "locale",
    "review_evidence_schema_version",
    "fixture_schema_version",
    "fixture_revision",
    "review_round",
    "candidate_sha256",
    "common_brief_sha256",
    "review_input_sha256",
    "rubric_sha256",
    "review_protocol_sha256",
    "reference_token_bytes",
    "reviewers",
    "disagreement",
    "verdict",
}
REVIEWER_FIELDS = {
    "reviewer_id",
    "reviewer_role",
    "authorship_disclosure",
    "is_specimen_author",
    "conflict_disclosure",
    "has_material_conflict",
    "criterion_results",
    "verdict",
}
CRITERION_RESULT_FIELDS = {
    "criterion_id",
    "score_0_to_3",
    "quoted_source",
    "quoted_span",
    "reason",
    "proposed_revision",
}


def table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        if "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 3 and cells[0] != "Function":
            rows.append(cells)
    return rows


def load_json(path: Path) -> object:
    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate object key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)


def _string_list(value: object, *, minimum: int = 0) -> list[str] | None:
    if not isinstance(value, list) or len(value) < minimum:
        return None
    if not all(isinstance(item, str) and item.strip() for item in value):
        return None
    return value


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_review_input(case: dict[str, object]) -> dict[str, object]:
    """Return every accepted case field except the digest and its result record."""
    return {
        field: case.get(field)
        for field in sorted(EXPECTED_NATIVE_REVIEW_CASE_FIELDS - REVIEW_INPUT_EXCLUDED_FIELDS)
    }


def _review_input_sha256(case: dict[str, object]) -> str:
    return _canonical_sha256(_canonical_review_input(case))


def _review_protocol_sha256(fixture: dict[str, object]) -> str:
    return _canonical_sha256(
        {
            "rubric_sha256": fixture.get("rubric_sha256"),
            "review_policy": fixture.get("review_policy"),
            "rubric_dimensions": fixture.get("rubric_dimensions"),
            "canonical_review_input_pins": EXPECTED_REVIEW_INPUT_PINS,
        }
    )


def _target_script_character_count(case: dict[str, object], text: str) -> int:
    """Count locale-script evidence without treating Latin reference tags as localized prose."""
    script = case.get("script")
    if script == "Hans":
        pattern = r"[\u3400-\u4dbf\u4e00-\u9fff]"
    elif script == "Jpan":
        pattern = r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]"
    elif script == "Kore":
        pattern = r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7a3]"
    else:
        return 0
    return len(re.findall(pattern, text))


def _canonical_reason_body(text: str) -> str:
    """Compare lexical reason content without punctuation, spacing, case, or width tricks."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens: list[str] = []
    current: list[str] = []
    for character in normalized:
        if unicodedata.category(character) in {"Cc", "Cf"}:
            continue
        if character.isalnum():
            current.append(character)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return " ".join(tokens)


PUBLIC_CLAIM_CONFUSABLES = str.maketrans(
    {
        "а": "a",  # Cyrillic small a
        "α": "a",  # Greek small alpha
        "і": "i",  # Cyrillic small Byelorussian-Ukrainian i
        "ı": "i",  # dotless i
        "ι": "i",  # Greek small iota
        "ν": "v",  # Greek small nu
        "ѵ": "v",  # Cyrillic small izhitsa
        "е": "e",  # Cyrillic small ie
        "ε": "e",  # Greek small epsilon
        "τ": "t",  # Greek small tau
        "т": "t",  # Cyrillic small te
        "η": "n",  # Greek small eta
    }
)
PUBLIC_CLAIM_ESCAPE_RE = re.compile(
    r"\\(?:x([0-9A-Fa-f]{2})|u([0-9A-Fa-f]{4})|U([0-9A-Fa-f]{8}))"
)


class _PublicHTMLTextExtractor(HTMLParser):
    """Collect rendered text plus accessibility/title strings for linting."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.attributes: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name.casefold() in {"alt", "title", "aria-label"} and value:
                self.attributes.append(value)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _decode_public_scalar_escapes(text: str) -> str:
    """Decode JSON/YAML/TOML-style hex escapes without requiring optional parsers."""

    def replace(match: re.Match[str]) -> str:
        raw = next(group for group in match.groups() if group is not None)
        try:
            value = int(raw, 16)
            if value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
                return match.group(0)
            return chr(value)
        except ValueError:
            return match.group(0)

    return PUBLIC_CLAIM_ESCAPE_RE.sub(replace, text)


def _markdown_labels_and_html_text(text: str) -> tuple[str, str]:
    """Expose link labels and both joined/spaced HTML render approximations."""
    expanded = html.unescape(_decode_public_scalar_escapes(text))
    expanded = re.sub(r"^\s{0,3}\[[^\]]+\]:.*$", "", expanded, flags=re.MULTILINE)
    expanded = re.sub(r"!\[([^\]]*)\]\s*\[[^\]]*\]", r"\1", expanded)
    expanded = re.sub(r"\[([^\]]+)\]\s*\[[^\]]*\]", r"\1", expanded)
    expanded = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", expanded)
    expanded = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", expanded)
    expanded = re.sub(r"\\([\\`*_{}\[\]()#+.!~-])", r"\1", expanded)
    extractor = _PublicHTMLTextExtractor()
    try:
        extractor.feed(expanded)
        extractor.close()
    except (ValueError, AssertionError):
        pass
    joined = "".join(extractor.parts)
    spaced = re.sub(r"<!--.*?-->", "", expanded, flags=re.DOTALL)
    spaced = re.sub(r"<[^>]*>", " ", spaced)
    attributes = "\n".join(extractor.attributes)
    return joined + "\n" + attributes, spaced + "\n" + attributes


def _public_claim_skeleton(
    text: str,
    controls_as_space: bool,
    separators_as_empty: bool,
) -> str:
    output: list[str] = []
    for character in unicodedata.normalize("NFKD", text):
        category = unicodedata.category(character)
        if character in PUBLIC_CLAIM_DASH_CHARACTERS or character == "_":
            if not separators_as_empty:
                output.append("-")
        elif category.startswith(("C", "M")):
            if controls_as_space:
                output.append(" ")
        elif category.startswith(("P", "S")):
            if not separators_as_empty:
                output.append("-")
        else:
            output.append(character.casefold().translate(PUBLIC_CLAIM_CONFUSABLES))
    return " ".join("".join(output).split())


def _public_claim_scan_views(text: str) -> set[str]:
    bases = _markdown_labels_and_html_text(text)
    return {
        _public_claim_skeleton(
            base,
            controls_as_space=controls_as_space,
            separators_as_empty=separators_as_empty,
        )
        for base in bases
        for controls_as_space in (False, True)
        for separators_as_empty in (False, True)
    }


def _public_claim_units(text: str) -> list[tuple[int, str]]:
    """Join soft-wrapped prose while keeping headings and list items isolated."""
    units: list[tuple[int, str]] = []
    buffered: list[str] = []
    start_line = 1

    def flush() -> None:
        nonlocal buffered
        if buffered:
            units.append((start_line, " ".join(buffered)))
            buffered = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        structural = MARKDOWN_STRUCTURAL_LINE_RE.match(stripped) is not None
        if structural:
            flush()
            start_line = line_number
            buffered = [stripped]
            if stripped.startswith("#") or stripped.startswith(("```", "~~~", "|")):
                flush()
            continue
        if not buffered:
            start_line = line_number
        buffered.append(stripped)
        if re.search(r"[.!?;。！？；]\s*$", stripped):
            flush()
    flush()
    return units


def _public_text_paths(root: Path) -> list[Path]:
    """Return declared public text surfaces, independent of filename extension."""
    root_resolved = root.resolve()
    excluded_roots = set(PUBLIC_CLAIM_LINT_POLICY["excluded_roots"])

    def is_contained_public_file(path: Path) -> bool:
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root_resolved)
            relative = path.relative_to(root)
        except (OSError, ValueError):
            return False
        return resolved.is_file() and not excluded_roots.intersection(relative.parts)

    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            capture_output=True,
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        proc = None

    if proc is not None:
        paths = []
        for raw in proc.stdout.split(b"\0"):
            if not raw:
                continue
            relative = Path(raw.decode("utf-8", "replace"))
            path = root / relative
            if is_contained_public_file(path):
                paths.append(path)
        return sorted(set(paths))

    return sorted(
        path
        for path in root.rglob("*")
        if is_contained_public_file(path)
    )


def _canonical_disclaimer_is_top_level_prose(text: str, start: int) -> bool:
    """Require the exact block at column zero, outside code, comments, and metadata."""
    lines = text.splitlines()
    line_index = text[:start].count("\n")
    line_start = text.rfind("\n", 0, start) + 1
    if start != line_start:
        return False
    expected_lines = PUBLIC_CLAIM_CANONICAL_DISCLAIMER.split("\n")
    if lines[line_index:line_index + len(expected_lines)] != expected_lines:
        return False

    prefix = text[:start]
    if prefix.rfind("<!--") > prefix.rfind("-->"):
        return False
    if prefix.rfind("<") > prefix.rfind(">"):
        return False
    fence: str | None = None
    for line in lines[:line_index]:
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if match is None:
            continue
        marker = match.group(1)[0]
        if fence is None:
            fence = marker
        elif fence == marker:
            fence = None
    if fence is not None:
        return False

    if lines and lines[0].strip() == "---":
        for close_index, line in enumerate(lines[1:], start=1):
            if line.strip() in {"---", "..."}:
                if line_index <= close_index:
                    return False
                break
    return True


def validate_public_claim_boundaries(root: Path) -> list[str]:
    """Enforce the exact disclaimer and run a best-effort English phrase lint."""
    errors: list[str] = []
    canonical_digest = hashlib.sha256(
        PUBLIC_CLAIM_CANONICAL_DISCLAIMER.encode("utf-8")
    ).hexdigest()
    if canonical_digest != PUBLIC_CLAIM_CANONICAL_DISCLAIMER_SHA256:
        errors.append("public claim disclaimer digest drifted from its pinned bytes")

    canonical_path = root / str(EXPECTED_PUBLIC_CLAIM_ALLOWLIST[0]["path"])
    canonical_scan_text: str | None = None
    if not canonical_path.is_file():
        errors.append(
            f"{NATIVE_REVIEW_RUBRIC}: exact canonical public claim disclaimer is missing"
        )
    else:
        try:
            canonical_raw_text = canonical_path.read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{NATIVE_REVIEW_RUBRIC}: cannot read exact disclaimer bytes: {exc}")
        else:
            canonical_lf_text = canonical_raw_text.replace("\r\n", "\n")
            if "\r" in canonical_lf_text:
                errors.append(
                    f"{NATIVE_REVIEW_RUBRIC}: canonical disclaimer uses an unsupported line ending"
                )
            occurrence_count = canonical_lf_text.count(PUBLIC_CLAIM_CANONICAL_DISCLAIMER)
            if occurrence_count != 1:
                errors.append(
                    f"{NATIVE_REVIEW_RUBRIC}: exact canonical public claim disclaimer must "
                    f"occur once, found {occurrence_count}"
                )
            else:
                start = canonical_lf_text.index(PUBLIC_CLAIM_CANONICAL_DISCLAIMER)
                if not _canonical_disclaimer_is_top_level_prose(canonical_lf_text, start):
                    errors.append(
                        f"{NATIVE_REVIEW_RUBRIC}: canonical public claim disclaimer must be "
                        "a top-level rendered prose block"
                    )
                canonical_scan_text = (
                    canonical_lf_text[:start]
                    + "\n"
                    + canonical_lf_text[start + len(PUBLIC_CLAIM_CANONICAL_DISCLAIMER):]
                )

    for path in _public_text_paths(root):
        relative = path.relative_to(root).as_posix()
        try:
            raw = path.read_bytes()
            if len(raw) > int(PUBLIC_CLAIM_LINT_POLICY["max_bytes"]):
                errors.append(
                    f"{relative}: declared public text surface exceeds "
                    f"{PUBLIC_CLAIM_LINT_POLICY['max_bytes']} bytes"
                )
                continue
            text = raw.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative}: cannot inspect declared public text surface: {exc}")
            continue
        if relative == NATIVE_REVIEW_RUBRIC and canonical_scan_text is not None:
            text = canonical_scan_text
        if any(PUBLIC_KNOWN_CLAIM_RE.search(view) for view in _public_claim_scan_views(text)):
            errors.append(
                f"{relative}:1: best-effort English known-phrase lint found a public claim "
                "that requires independent human review"
            )
    return errors


def validate_native_review_evidence(root: Path, fixture: dict[str, object]) -> list[str]:
    """Validate recorded human evidence without treating it as proof of reviewer identity."""
    errors: list[str] = []
    evidence_path = root / NATIVE_REVIEW_EVIDENCE
    if not evidence_path.is_file():
        return [f"missing {NATIVE_REVIEW_EVIDENCE}"]

    try:
        artifact = load_json(evidence_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"{NATIVE_REVIEW_EVIDENCE}: invalid JSON: {exc}"]
    if not isinstance(artifact, dict):
        return [f"{NATIVE_REVIEW_EVIDENCE}: root must be an object"]
    if set(artifact) != {
        "schema_version", "fixture", "purpose", "review_state", "completed_review_sets"
    }:
        errors.append(f"{NATIVE_REVIEW_EVIDENCE}: root fields do not match schema 1.0")

    if artifact.get("schema_version") != "1.0":
        errors.append(f"{NATIVE_REVIEW_EVIDENCE}: schema_version must be 1.0")
    if artifact.get("fixture") != NATIVE_REVIEW_FIXTURE:
        errors.append(f"{NATIVE_REVIEW_EVIDENCE}: fixture must point to {NATIVE_REVIEW_FIXTURE}")
    if artifact.get("purpose") != EXPECTED_EVIDENCE_PURPOSE:
        errors.append(f"{NATIVE_REVIEW_EVIDENCE}: purpose or claim boundary drifted")

    fixture_cases = fixture.get("cases")
    cases_by_id: dict[str, dict[str, object]] = {}
    if isinstance(fixture_cases, list):
        for case in fixture_cases:
            if isinstance(case, dict) and isinstance(case.get("id"), str):
                cases_by_id[case["id"]] = case

    review_sets = artifact.get("completed_review_sets")
    if not isinstance(review_sets, list):
        errors.append(f"{NATIVE_REVIEW_EVIDENCE}: completed_review_sets must be an array")
        review_sets = []

    seen_cases: set[str] = set()
    passed_cases: set[str] = set()
    for set_index, review_set in enumerate(review_sets):
        label = f"review set {set_index}"
        start_error_count = len(errors)
        if not isinstance(review_set, dict):
            errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} must be an object")
            continue
        if set(review_set) != REVIEW_SET_FIELDS:
            errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} fields do not match schema 1.0")

        case_id = review_set.get("case_id")
        case = cases_by_id.get(case_id) if isinstance(case_id, str) else None
        if case is None:
            errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} references unknown case {case_id!r}")
            continue
        label = str(case_id)
        if case_id in seen_cases:
            errors.append(f"{NATIVE_REVIEW_EVIDENCE}: duplicate current review set for {case_id}")
        seen_cases.add(case_id)

        bindings = {
            "locale": case.get("locale"),
            "review_evidence_schema_version": "1.0",
            "fixture_schema_version": fixture.get("schema_version"),
            "fixture_revision": case.get("fixture_revision"),
            "review_round": case.get("review_round"),
            "candidate_sha256": case.get("candidate_sha256"),
            "common_brief_sha256": case.get("common_brief_sha256"),
            "review_input_sha256": case.get("review_input_sha256"),
            "rubric_sha256": fixture.get("rubric_sha256"),
            "review_protocol_sha256": fixture.get("review_protocol_sha256"),
            "reference_token_bytes": case.get("reference_token_bytes"),
        }
        for field, expected in bindings.items():
            if review_set.get(field) != expected:
                errors.append(
                    f"{NATIVE_REVIEW_EVIDENCE}: {label} has stale or mismatched {field}"
                )

        reviewers = review_set.get("reviewers")
        if not isinstance(reviewers, list):
            errors.append(
                f"{NATIVE_REVIEW_EVIDENCE}: {label} reviewers must be an array"
            )
            reviewers = []
        elif len(reviewers) != 2:
            errors.append(
                f"{NATIVE_REVIEW_EVIDENCE}: {label} requires exactly two independent reviewers"
            )

        reviewer_ids: set[str] = set()
        role_counts = {role: 0 for role in REVIEWER_ROLES}
        reviewer_verdicts: list[str] = []
        criterion_scores: dict[str, list[int]] = {
            dimension_id: [] for dimension_id in EXPECTED_REVIEW_DIMENSIONS
        }

        for reviewer_index, reviewer in enumerate(reviewers):
            reviewer_label = f"{label} reviewer {reviewer_index}"
            if not isinstance(reviewer, dict):
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} must be an object")
                continue
            if set(reviewer) != REVIEWER_FIELDS:
                errors.append(
                    f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} fields do not match schema 1.0"
                )

            reviewer_id = reviewer.get("reviewer_id")
            if not isinstance(reviewer_id, str) or not reviewer_id.strip():
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} needs a stable reviewer_id")
            elif (
                REVIEWER_ID_RE.fullmatch(reviewer_id) is None
                or unicodedata.normalize("NFKC", reviewer_id) != reviewer_id
                or any(unicodedata.category(character).startswith("C") for character in reviewer_id)
            ):
                errors.append(
                    f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} reviewer_id must use visible "
                    "canonical ASCII"
                )
            else:
                normalized_id = unicodedata.normalize("NFKC", reviewer_id).casefold()
                if normalized_id in reviewer_ids:
                    errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} reviewer_id values must be distinct")
                else:
                    reviewer_ids.add(normalized_id)

            role = reviewer.get("reviewer_role")
            if not isinstance(role, str) or role not in REVIEWER_ROLES:
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} has an unsupported role")
                role = None
            else:
                role_counts[str(role)] += 1

            authorship = reviewer.get("authorship_disclosure")
            if authorship != "not_specimen_author":
                errors.append(
                    f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} authorship_disclosure must be "
                    "`not_specimen_author`"
                )
            if reviewer.get("is_specimen_author") is not False:
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} is not independent of authorship")
            conflict = reviewer.get("conflict_disclosure")
            if not isinstance(conflict, str) or not conflict.strip():
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} lacks conflict disclosure")
            elif conflict.strip().casefold() != "none":
                errors.append(
                    f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} conflict_disclosure must be `none`"
                )
            if reviewer.get("has_material_conflict") is not False:
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} has a material conflict")

            expected_criteria = {
                dimension_id
                for dimension_id, (owner, _, _) in EXPECTED_REVIEW_DIMENSIONS.items()
                if owner == "both" or owner == role
            }
            results = reviewer.get("criterion_results")
            if not isinstance(results, list):
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} criterion_results must be an array")
                results = []

            actual_criteria: set[str] = set()
            scores: dict[str, int] = {}
            quoted_spans: set[str] = set()
            reason_bodies: set[str] = set()
            for result_index, result in enumerate(results):
                result_label = f"{reviewer_label} criterion {result_index}"
                if not isinstance(result, dict):
                    errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {result_label} must be an object")
                    continue
                if set(result) != CRITERION_RESULT_FIELDS:
                    errors.append(
                        f"{NATIVE_REVIEW_EVIDENCE}: {result_label} fields do not match schema 1.0"
                    )
                criterion_id = result.get("criterion_id")
                if not isinstance(criterion_id, str) or criterion_id not in EXPECTED_REVIEW_DIMENSIONS:
                    errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {result_label} has unknown criterion_id")
                    continue
                if criterion_id in actual_criteria:
                    errors.append(
                        f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} duplicates {criterion_id}"
                    )
                actual_criteria.add(criterion_id)

                score = result.get("score_0_to_3")
                if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 3:
                    errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {result_label} score must be 0 to 3")
                    continue
                scores[criterion_id] = score
                criterion_scores[criterion_id].append(score)

                quoted_source = result.get("quoted_source")
                quoted_span = result.get("quoted_span")
                expected_quoted_source = EXPECTED_CRITERION_QUOTE_SOURCES[criterion_id]
                source_text = (
                    case.get(quoted_source)
                    if isinstance(quoted_source, str) and quoted_source in QUOTE_SOURCES
                    else None
                )
                if quoted_source != expected_quoted_source:
                    errors.append(
                        f"{NATIVE_REVIEW_EVIDENCE}: {result_label} {criterion_id} quoted_source "
                        f"must be `{expected_quoted_source}`"
                    )
                if (
                    not isinstance(quoted_span, str)
                    or not isinstance(source_text, str)
                    or quoted_span not in source_text
                ):
                    errors.append(
                        f"{NATIVE_REVIEW_EVIDENCE}: {result_label} quoted_span is not grounded in quoted_source"
                    )
                elif _target_script_character_count(case, quoted_span) < (
                    MINIMUM_TARGET_SCRIPT_CHARACTERS_PER_QUOTE
                ):
                    errors.append(
                        f"{NATIVE_REVIEW_EVIDENCE}: {result_label} quoted_span must contain at least "
                        f"{MINIMUM_TARGET_SCRIPT_CHARACTERS_PER_QUOTE} target-script characters"
                    )
                else:
                    normalized_quote = " ".join(quoted_span.split()).casefold()
                    if normalized_quote in quoted_spans:
                        errors.append(
                            f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} reuses one quote for "
                            "multiple criteria"
                        )
                    quoted_spans.add(normalized_quote)
                    locale_anchors = EXPECTED_CRITERION_EVIDENCE_ANCHORS.get(
                        str(case.get("locale")), {}
                    )
                    criterion_anchors = locale_anchors.get(criterion_id, [])
                    if not criterion_anchors or quoted_span not in criterion_anchors:
                        errors.append(
                            f"{NATIVE_REVIEW_EVIDENCE}: {result_label} quoted_span does not "
                            f"equal a {criterion_id} evidence anchor"
                        )
                reason = result.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {result_label} needs a reason")
                else:
                    stripped_reason = reason.strip()
                    reason_prefix = f"{criterion_id}: "
                    reason_has_prefix = stripped_reason.startswith(reason_prefix)
                    reason_body = (
                        stripped_reason[len(reason_prefix):].strip()
                        if reason_has_prefix
                        else ""
                    )
                    reason_body_has_controls = any(
                        unicodedata.category(character) in {"Cc", "Cf"}
                        for character in reason_body
                    )
                    normalized_reason_body = unicodedata.normalize("NFKC", reason_body)
                    alphanumeric_count = sum(
                        character.isalnum() for character in normalized_reason_body
                    )
                    if len(stripped_reason) < MINIMUM_REASON_CHARACTERS or not reason_has_prefix:
                        errors.append(
                            f"{NATIVE_REVIEW_EVIDENCE}: {result_label} reason must begin with "
                            f"`{criterion_id}: ` and contain at least {MINIMUM_REASON_CHARACTERS} "
                            "characters"
                        )
                    if alphanumeric_count < MINIMUM_REASON_ALPHANUMERIC_CHARACTERS:
                        errors.append(
                            f"{NATIVE_REVIEW_EVIDENCE}: {result_label} reason body must contain "
                            f"at least {MINIMUM_REASON_ALPHANUMERIC_CHARACTERS} meaningful "
                            "alphanumeric characters"
                        )
                    if reason_body_has_controls:
                        errors.append(
                            f"{NATIVE_REVIEW_EVIDENCE}: {result_label} reason body contains "
                            "Unicode control or format characters"
                        )
                    canonical_body = _canonical_reason_body(reason_body)
                    if canonical_body and canonical_body in reason_bodies:
                        errors.append(
                            f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} reuses one canonical "
                            "lexical reason body for multiple criteria"
                        )
                    if canonical_body:
                        reason_bodies.add(canonical_body)
                proposed_revision = result.get("proposed_revision")
                if not isinstance(proposed_revision, str):
                    errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {result_label} proposed_revision must be text")
                elif score < 3 and (
                    not proposed_revision.strip()
                    or _target_script_character_count(case, proposed_revision)
                    < MINIMUM_TARGET_SCRIPT_CHARACTERS_PER_QUOTE
                ):
                    errors.append(
                        f"{NATIVE_REVIEW_EVIDENCE}: {result_label} needs a concrete localized "
                        "proposed revision"
                    )
                elif score == 3 and proposed_revision.strip():
                    errors.append(
                        f"{NATIVE_REVIEW_EVIDENCE}: {result_label} score 3 must not propose a revision"
                    )

            if actual_criteria != expected_criteria:
                errors.append(
                    f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} criterion ownership is incomplete or excessive"
                )

            verdict = reviewer.get("verdict")
            if not isinstance(verdict, str) or verdict not in REVIEW_VERDICTS:
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} has invalid verdict")
            else:
                reviewer_verdicts.append(str(verdict))
            below_threshold = []
            for criterion_id in expected_criteria:
                minimum = 3 if EXPECTED_REVIEW_DIMENSIONS[criterion_id][0] == "both" else 2
                if scores.get(criterion_id, -1) < minimum:
                    below_threshold.append(criterion_id)
            derived_reviewer_verdict = (
                "fail"
                if any(scores.get(criterion_id) == 0 for criterion_id in expected_criteria)
                else "revise"
                if below_threshold
                else "pass"
            )
            if verdict != derived_reviewer_verdict:
                errors.append(
                    f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} verdict must derive as "
                    f"{derived_reviewer_verdict}"
                )
            if verdict == "pass":
                for criterion_id in below_threshold:
                    errors.append(
                        f"{NATIVE_REVIEW_EVIDENCE}: {reviewer_label} pass violates {criterion_id} threshold"
                    )

        if role_counts != {role: 1 for role in REVIEWER_ROLES}:
            errors.append(
                f"{NATIVE_REVIEW_EVIDENCE}: {label} does not cover both required roles exactly once"
            )

        disagreement = review_set.get("disagreement")
        disagreement_status: object = None
        if not isinstance(disagreement, dict) or set(disagreement) != {"status", "summary"}:
            errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} disagreement record is malformed")
        else:
            disagreement_status = disagreement.get("status")
            if (
                not isinstance(disagreement_status, str)
                or disagreement_status not in {"none", "unresolved"}
            ):
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} disagreement status is invalid")
            summary = disagreement.get("summary")
            if not isinstance(summary, str):
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} disagreement summary must be text")
            elif disagreement_status == "none" and summary.strip():
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} no disagreement requires an empty summary")
            elif disagreement_status == "unresolved" and not summary.strip():
                errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} unresolved disagreement needs a summary")

        score_disagreement = any(
            len(scores) > 1 and len(set(scores)) > 1
            for scores in criterion_scores.values()
        )
        verdict_disagreement = len(set(reviewer_verdicts)) > 1
        has_reviewer_disagreement = score_disagreement or verdict_disagreement
        if has_reviewer_disagreement and disagreement_status != "unresolved":
            errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} hides a reviewer disagreement")
        elif not has_reviewer_disagreement and disagreement_status == "unresolved":
            errors.append(
                f"{NATIVE_REVIEW_EVIDENCE}: {label} claims an unresolved disagreement "
                "without differing reviewer scores or verdicts"
            )

        derived_verdict = (
            "fail"
            if "fail" in reviewer_verdicts
            else "revise"
            if "revise" in reviewer_verdicts
            else "pass"
            if reviewer_verdicts and len(reviewer_verdicts) == len(reviewers)
            else None
        )
        if review_set.get("verdict") != derived_verdict:
            errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} verdict does not derive from reviewers")
        if review_set.get("verdict") == "pass" and disagreement_status != "none":
            errors.append(f"{NATIVE_REVIEW_EVIDENCE}: {label} unresolved disagreement blocks pass")

        if len(errors) == start_error_count and review_set.get("verdict") == "pass":
            passed_cases.add(case_id)

    expected_case_ids = set(cases_by_id)
    derived_state = (
        "review_records_structurally_complete"
        if expected_case_ids and passed_cases == expected_case_ids
        else "pending_native_review"
    )
    if artifact.get("review_state") != derived_state:
        errors.append(
            f"{NATIVE_REVIEW_EVIDENCE}: review_state must derive as {derived_state}"
        )
    return errors


def validate_native_review(root: Path) -> list[str]:
    """Validate the review fixture's structure, never its linguistic quality."""
    errors: list[str] = []
    fixture_path = root / NATIVE_REVIEW_FIXTURE
    rubric_path = root / NATIVE_REVIEW_RUBRIC

    if not fixture_path.is_file():
        return [f"missing {NATIVE_REVIEW_FIXTURE}"]
    if not rubric_path.is_file():
        return [f"missing {NATIVE_REVIEW_RUBRIC}"]

    try:
        data = load_json(fixture_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"{NATIVE_REVIEW_FIXTURE}: invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return [f"{NATIVE_REVIEW_FIXTURE}: root must be an object"]
    if set(data) != EXPECTED_NATIVE_REVIEW_ROOT_FIELDS:
        errors.append(
            f"{NATIVE_REVIEW_FIXTURE}: root fields do not match the exact schema 1.0"
        )

    if data.get("schema_version") != "1.0":
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: schema_version must be 1.0")
    if data.get("rubric") != NATIVE_REVIEW_RUBRIC:
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: rubric must point to {NATIVE_REVIEW_RUBRIC}")
    if data.get("review_evidence") != NATIVE_REVIEW_EVIDENCE:
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: review_evidence must point to {NATIVE_REVIEW_EVIDENCE}")
    if data.get("review_state") != "pending_native_review":
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: canonical fixture must remain pending_native_review")
    if data.get("model_output_state") != "not_evaluated":
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: static fixture cannot claim model output evaluation")
    if data.get("generated_video_state") != "not_evaluated":
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: static fixture cannot claim generated-video evaluation")
    if data.get("native_quality_verified") is not False:
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: static fixture cannot claim verified native quality")

    static_scope = _string_list(data.get("static_validation_scope"))
    if static_scope is None or set(static_scope) != EXPECTED_STATIC_SCOPE:
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: static validation scope overclaims or is incomplete")

    limitations = _string_list(data.get("static_checks_do_not_establish"))
    if limitations is None or set(limitations) != EXPECTED_LIMITATIONS:
        errors.append(
            f"{NATIVE_REVIEW_FIXTURE}: static_checks_do_not_establish must name every epistemic limitation"
        )

    policy = data.get("review_policy")
    if not isinstance(policy, dict):
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: review_policy must be an object")
    else:
        if policy.get("review_evidence_schema_version") != "1.0":
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: review evidence schema version must be 1.0")
        if policy.get("canonical_review_input_pins_required") is not True:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: canonical review-input pins must be required")
        if policy.get("public_claim_allowlist_version") != PUBLIC_CLAIM_ALLOWLIST_VERSION:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: public-claim allowlist version drifted")
        allowlist = policy.get("public_claim_allowlist")
        if allowlist != EXPECTED_PUBLIC_CLAIM_ALLOWLIST:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: public-claim allowlist record drifted")
        if isinstance(allowlist, list):
            seen_allowlist_records: set[tuple[str, str]] = set()
            for record_index, record in enumerate(allowlist):
                if not isinstance(record, dict) or set(record) != {
                    "path", "text_lf", "sha256_lf", "line_endings"
                }:
                    errors.append(
                        f"{NATIVE_REVIEW_FIXTURE}: public-claim allowlist record "
                        f"{record_index} is malformed"
                    )
                    continue
                record_path = record.get("path")
                record_text = record.get("text_lf")
                record_sha256 = record.get("sha256_lf")
                line_endings = record.get("line_endings")
                if not all(
                    isinstance(value, str)
                    for value in (record_path, record_text, record_sha256, line_endings)
                ):
                    errors.append(
                        f"{NATIVE_REVIEW_FIXTURE}: public-claim allowlist record "
                        f"{record_index} must contain strings"
                    )
                    continue
                if "\r" in record_text or line_endings != "LF_or_CRLF_only":
                    errors.append(
                        f"{NATIVE_REVIEW_FIXTURE}: public-claim allowlist record "
                        f"{record_index} line-ending contract drifted"
                    )
                if hashlib.sha256(record_text.encode("utf-8")).hexdigest() != record_sha256:
                    errors.append(
                        f"{NATIVE_REVIEW_FIXTURE}: public-claim allowlist record "
                        f"{record_index} digest is false"
                    )
                record_key = (record_path, record_text)
                if record_key in seen_allowlist_records:
                    errors.append(
                        f"{NATIVE_REVIEW_FIXTURE}: public-claim allowlist record "
                        f"{record_index} is duplicated"
                    )
                seen_allowlist_records.add(record_key)
        if policy.get("public_claim_lint_policy") != PUBLIC_CLAIM_LINT_POLICY:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: public-claim lint surface policy drifted")
        if policy.get("public_claim_dash_set_version") != PUBLIC_CLAIM_DASH_SET_VERSION:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: public-claim dash-set version drifted")
        if policy.get("public_claim_dash_codepoints") != list(PUBLIC_CLAIM_DASH_LABELS):
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: public-claim dash repertoire drifted")
        if policy.get("required_independent_reviewers_per_locale") != 2:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: require exactly two independent reviewers per locale")
        if policy.get("specimen_authors_may_not_review") is not True:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: specimen authors may not review their own specimen")
        if policy.get("reviewers_must_record_conflicts") is not True:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: reviewers must record conflicts")
        if policy.get("material_conflicts_block_review") is not True:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: material reviewer conflicts must block review")
        roles = _string_list(policy.get("required_roles"), minimum=2)
        if roles is None or set(roles) != REVIEWER_ROLES:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: required reviewer roles are incomplete")
        if policy.get("criterion_quote_sources") != EXPECTED_CRITERION_QUOTE_SOURCES:
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: every criterion must quote the localized candidate_prompt"
            )
        if policy.get("minimum_target_script_characters_per_quote") != (
            MINIMUM_TARGET_SCRIPT_CHARACTERS_PER_QUOTE
        ):
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: minimum target-script quote length drifted")
        if policy.get("criterion_evidence_anchor_required") is not True:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: criterion evidence anchors must be required")
        if policy.get("quotes_unique_per_reviewer") is not True:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: reviewer quotes must be criterion-specific")
        if policy.get("reviewer_id_format") != "visible_canonical_ascii":
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: reviewer ID format boundary drifted")
        if policy.get("minimum_reason_characters") != MINIMUM_REASON_CHARACTERS:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: minimum reason length drifted")
        if policy.get("minimum_reason_alphanumeric_characters") != (
            MINIMUM_REASON_ALPHANUMERIC_CHARACTERS
        ):
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: minimum meaningful reason content drifted"
            )
        if policy.get("reason_prefix") != "<criterion_id>: ":
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: criterion reason prefix drifted")
        if policy.get("reason_body_forbids_unicode_controls") is not True:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: reason control-character boundary drifted")
        if policy.get("reason_body_comparison") != "nfkc_casefold_alphanumeric_tokens":
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: reason-body comparison rule drifted")
        if policy.get("reasons_unique_per_reviewer") is not True:
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: reviewer reason bodies must be criterion-specific"
            )
        if policy.get("minimum_target_script_characters_per_revision") != (
            MINIMUM_TARGET_SCRIPT_CHARACTERS_PER_QUOTE
        ):
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: minimum localized revision length drifted")
        if policy.get("score_3_revision_must_be_empty") is not True:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: score-3 revision boundary drifted")
        evidence_fields = _string_list(policy.get("evidence_fields"), minimum=27)
        if evidence_fields is None or set(evidence_fields) != {
            "case_id", "locale", "review_evidence_schema_version", "fixture_schema_version",
            "fixture_revision", "review_round", "candidate_sha256", "common_brief_sha256",
            "review_input_sha256",
            "rubric_sha256", "review_protocol_sha256",
            "reference_token_bytes", "reviewer_id", "reviewer_role", "conflict_disclosure",
            "has_material_conflict", "authorship_disclosure", "is_specimen_author", "criterion_id",
            "score_0_to_3", "quoted_source", "quoted_span", "reason", "proposed_revision", "verdict",
            "disagreement_status", "disagreement_summary",
        }:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: review evidence fields are incomplete")
        if policy.get("pass_derivation") != {
            "owned_dimension_minimum": 2,
            "both_role_hard_dimensions_minimum": 3,
            "not_applicable_allowed": False,
            "unresolved_disagreement_blocks_pass": True,
            "all_reviewer_verdicts_must_pass": True,
            "all_multiscored_dimension_disagreements_must_be_recorded": True,
        }:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: review pass derivation drifted")
        if not isinstance(policy.get("adjudication"), str) or not policy["adjudication"].strip():
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: missing disagreement adjudication rule")

    dimensions = data.get("rubric_dimensions")
    actual_dimensions: dict[str, object] = {}
    if not isinstance(dimensions, list):
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: rubric_dimensions must be an array")
    else:
        for index, dimension in enumerate(dimensions):
            if not isinstance(dimension, dict) or not isinstance(dimension.get("id"), str):
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: rubric dimension {index} is malformed")
                continue
            dimension_id = dimension["id"]
            if dimension_id in actual_dimensions:
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: duplicate rubric dimension {dimension_id}")
            actual_dimensions[dimension_id] = (
                dimension.get("owner"),
                dimension.get("not_applicable_allowed"),
                dimension.get("hard_fail"),
            )
        if actual_dimensions != EXPECTED_REVIEW_DIMENSIONS:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: rubric dimension contract is incomplete")

    cases = data.get("cases")
    if not isinstance(cases, list):
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: cases must be an array")
        cases = []

    seen_locales: set[str] = set()
    common_briefs: set[str] = set()
    realization_sets: dict[str, set[str]] = {}
    expected_tokens = [entry["token"] for entry in EXPECTED_REFERENCE_TOKEN_BYTES]

    for index, case in enumerate(cases):
        case_label = f"case {index}"
        if not isinstance(case, dict):
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {case_label} must be an object")
            continue
        if set(case) != EXPECTED_NATIVE_REVIEW_CASE_FIELDS:
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: {case_label} fields do not match the exact case schema 1.0"
            )
        locale = case.get("locale")
        if not isinstance(locale, str) or locale not in EXPECTED_REVIEW_CASES:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {case_label} has unsupported locale {locale!r}")
            continue
        case_label = locale
        if locale in seen_locales:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: duplicate locale {locale}")
        seen_locales.add(locale)

        expected_case = EXPECTED_REVIEW_CASES[locale]
        expected_input_pin = EXPECTED_REVIEW_INPUT_PINS[locale]
        if case.get("id") != expected_case["id"]:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} case id drifted")
        if case.get("script") != expected_case["script"]:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} script must be {expected_case['script']}")
        fixture_revision = case.get("fixture_revision")
        if fixture_revision != expected_input_pin["fixture_revision"]:
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: {locale} fixture_revision must be "
                f"{expected_input_pin['fixture_revision']} for the pinned review input"
            )
        review_round = case.get("review_round")
        if review_round != expected_input_pin["review_round"]:
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: {locale} review_round must be "
                f"{expected_input_pin['review_round']} for the pinned review input"
            )

        if case.get("external_controls") != {
            "duration_seconds": 8,
            "duration_owner": "surface_setting_not_prompt_prose",
        }:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} duration ownership drifted")

        source_paths = _string_list(case.get("source_paths"), minimum=3)
        if source_paths is None:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} needs at least three source paths")
        else:
            for relative in source_paths:
                path = Path(relative)
                if path.is_absolute() or ".." in path.parts or not (root / path).is_file():
                    errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} source path is missing or unsafe: {relative}")

        common_brief = case.get("common_brief")
        candidate = case.get("candidate_prompt")
        if common_brief != EXPECTED_COMMON_BRIEF:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} canonical common brief drifted")
            if not isinstance(common_brief, str):
                common_brief = ""
        if not common_brief:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} common_brief is missing")
            common_brief = ""
        else:
            common_briefs.add(common_brief)
        common_brief_sha256 = hashlib.sha256(common_brief.encode("utf-8")).hexdigest()
        if (
            case.get("common_brief_sha256") != common_brief_sha256
            or common_brief_sha256 != EXPECTED_COMMON_BRIEF_SHA256
        ):
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} common_brief_sha256 drifted")
        if not isinstance(candidate, str) or not candidate.strip():
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} candidate_prompt is missing")
            candidate = ""

        criterion_anchors = case.get("criterion_evidence_anchors")
        expected_anchors = EXPECTED_CRITERION_EVIDENCE_ANCHORS[locale]
        if criterion_anchors != expected_anchors:
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: {locale} criterion evidence anchors drifted"
            )
        else:
            for criterion_id, anchors in criterion_anchors.items():
                for anchor in anchors:
                    if anchor not in candidate:
                        errors.append(
                            f"{NATIVE_REVIEW_FIXTURE}: {locale} {criterion_id} evidence anchor "
                            "is absent from candidate"
                        )
                    elif _target_script_character_count(case, anchor) < (
                        MINIMUM_TARGET_SCRIPT_CHARACTERS_PER_QUOTE
                    ):
                        errors.append(
                            f"{NATIVE_REVIEW_FIXTURE}: {locale} {criterion_id} evidence anchor "
                            "is too short"
                        )

        token_bytes = case.get("reference_token_bytes")
        if token_bytes != EXPECTED_REFERENCE_TOKEN_BYTES:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} reference-token byte manifest drifted")
        else:
            for entry in token_bytes:
                if entry["token"].encode("utf-8").hex() != entry["utf8_hex"]:
                    errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} reference-token byte manifest is false")
        if TOKEN_LIKE_RE.findall(common_brief) != expected_tokens:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} source brief reference tokens drifted")
        if TOKEN_LIKE_RE.findall(candidate) != expected_tokens:
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: {locale} candidate must preserve byte-exact reference tokens once and in order"
            )
        if candidate and not re.search(str(expected_case["script_re"]), candidate):
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} candidate lacks its declared script")

        candidate_sha256 = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        if case.get("candidate_sha256") != candidate_sha256:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} candidate_sha256 does not bind this revision")
        if candidate_sha256 != expected_case["candidate_sha256"]:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} canonical candidate bytes drifted")

        review_input_sha256 = _review_input_sha256(case)
        if case.get("review_input_sha256") != review_input_sha256:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} review_input_sha256 is stale")
        if {
            "fixture_revision": fixture_revision,
            "review_round": review_round,
            "review_input_sha256": review_input_sha256,
        } != expected_input_pin:
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: {locale} canonical review-input pin drifted; "
                "advance its pinned revision, round, and digest as one visible protocol change"
            )

        bindings = case.get("reference_bindings")
        if not isinstance(bindings, list) or len(bindings) != len(EXPECTED_REFERENCE_ROLES):
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} reference binding evidence is incomplete")
        else:
            for binding_index, ((expected_token, expected_role), binding) in enumerate(
                zip(EXPECTED_REFERENCE_ROLES, bindings)
            ):
                if not isinstance(binding, dict):
                    errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} binding {binding_index} is malformed")
                    continue
                span = binding.get("candidate_span")
                if binding.get("token") != expected_token or binding.get("role") != expected_role:
                    errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} reference role binding drifted")
                if not isinstance(span, str) or expected_token not in span or span not in candidate:
                    errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} reference role lacks candidate evidence")
                elif (
                    binding.get("candidate_span_sha256") != hashlib.sha256(span.encode("utf-8")).hexdigest()
                    or binding["candidate_span_sha256"]
                    != expected_case["binding_span_sha256"][binding_index]
                ):
                    errors.append(
                        f"{NATIVE_REVIEW_FIXTURE}: {locale} canonical reference binding span drifted"
                    )

        production_contract = case.get("production_contract")
        if not isinstance(production_contract, dict) or set(production_contract) != EXPECTED_PRODUCTION_CONTRACT_FIELDS:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} production contract is incomplete")
        else:
            for field, realization in production_contract.items():
                if not isinstance(realization, str) or not realization.strip():
                    errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} production contract {field} is empty")
                elif realization not in candidate:
                    errors.append(
                        f"{NATIVE_REVIEW_FIXTURE}: {locale} production contract {field} is absent from candidate"
                    )

        register = case.get("creative_lens_hypothesis")
        if not isinstance(register, dict):
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} creative lens hypothesis must be an object")
        else:
            label = register.get("label")
            if not isinstance(label, str) or not label.strip():
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} creative lens label is missing")
            if register.get("hypothesis_status") != "requires_native_review":
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} creative lens must remain a review hypothesis")
            if register.get("label_required_in_candidate") is not False:
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} must not require label theater in the prompt")
            if not isinstance(register.get("intent"), str) or not register["intent"].strip():
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} creative-lens intent is missing")
            realizations = _string_list(register.get("physical_realizations"), minimum=3)
            if realizations is None:
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} needs three concrete creative-lens realizations")
            else:
                realization_sets[locale] = set(realizations)
                if len(realization_sets[locale]) != len(realizations):
                    errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} creative-lens realizations must be unique")
                for realization in realizations:
                    if realization not in candidate:
                        errors.append(
                            f"{NATIVE_REVIEW_FIXTURE}: {locale} declared realization is absent from candidate: {realization}"
                        )
            failures = _string_list(register.get("anti_flattening_failures"), minimum=3)
            if failures is None:
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} needs three anti-flattening failure notes")

        language_register = case.get("language_register")
        if not isinstance(language_register, dict):
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} language_register must be an object")
        else:
            if language_register.get("dialogue_mode") != "no_dialogue":
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} dialogue mode drifted")
            question = language_register.get("review_question")
            if not isinstance(question, str) or not question.strip():
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: {locale} language-register review question is missing")

        review_record = case.get("review_record")
        expected_empty_review = {
            "case_id": case.get("id"),
            "locale": locale,
            "fixture_schema_version": "1.0",
            "fixture_revision": fixture_revision,
            "common_brief_sha256": common_brief_sha256,
            "candidate_sha256": candidate_sha256,
            "review_input_sha256": review_input_sha256,
            "reference_token_bytes": EXPECTED_REFERENCE_TOKEN_BYTES,
            "review_round": review_round,
            "status": "pending_native_review",
            "reviewers": [],
            "verdict": None,
            "criterion_results": [],
            "evidence": [],
        }
        if review_record != expected_empty_review:
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: {locale} canonical review record must remain empty and pending"
            )

    if seen_locales != set(EXPECTED_REVIEW_CASES):
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: expected exactly zh-CN, ja-JP, and ko-KR cases")
    if len(common_briefs) != 1:
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: locale cases must answer one identical common brief")
    locales = sorted(realization_sets)
    for left_index, left in enumerate(locales):
        for right in locales[left_index + 1:]:
            overlap = realization_sets[left] & realization_sets[right]
            if overlap:
                errors.append(
                    f"{NATIVE_REVIEW_FIXTURE}: {left} and {right} reuse exact creative-lens realizations: {sorted(overlap)}"
                )

    adversarial = data.get("adversarial_contract")
    actual_gates: dict[str, object] = {}
    if not isinstance(adversarial, list):
        errors.append(f"{NATIVE_REVIEW_FIXTURE}: adversarial_contract must be an array")
    else:
        for index, case in enumerate(adversarial):
            if not isinstance(case, dict) or not isinstance(case.get("id"), str):
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: adversarial case {index} is malformed")
                continue
            case_id = case["id"]
            if case_id in actual_gates:
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: duplicate adversarial case {case_id}")
            actual_gates[case_id] = case.get("gate")
            if not isinstance(case.get("failure"), str) or not case["failure"].strip():
                errors.append(f"{NATIVE_REVIEW_FIXTURE}: adversarial case {case_id} lacks a failure description")
        if actual_gates != EXPECTED_ADVERSARIAL_GATES:
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: adversarial gate contract is incomplete")

    try:
        rubric = rubric_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{NATIVE_REVIEW_RUBRIC}: cannot read rubric: {exc}")
    else:
        actual_rubric_sha256 = hashlib.sha256(rubric.encode("utf-8")).hexdigest()
        if (
            data.get("rubric_sha256") != actual_rubric_sha256
            or actual_rubric_sha256 != EXPECTED_RUBRIC_SHA256
        ):
            errors.append(f"{NATIVE_REVIEW_FIXTURE}: rubric_sha256 is stale or noncanonical")
        if (
            data.get("review_protocol_sha256") != _review_protocol_sha256(data)
            or data.get("review_protocol_sha256") != EXPECTED_REVIEW_PROTOCOL_SHA256
        ):
            errors.append(
                f"{NATIVE_REVIEW_FIXTURE}: review_protocol_sha256 is stale or noncanonical"
            )
        for required in (
            "## Claim boundary",
            PUBLIC_CLAIM_CANONICAL_DISCLAIMER,
            "two independent reviewers per locale",
            "byte-for-byte reference-token preservation",
            "The fixture is repository-authored",
            "Keep the canonical fixture pending and unscored.",
            "Completed evidence is valid only through the CI-checked evidence artifact",
        ):
            if required not in rubric:
                errors.append(f"{NATIVE_REVIEW_RUBRIC}: missing claim-boundary text `{required}`")

    errors.extend(validate_native_review_evidence(root, data))
    errors.extend(validate_public_claim_boundaries(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require at least 40 rows and the complete production-function set",
    )
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    errors: list[str] = []

    for lang in LANGS:
        path = root / "references" / "vocab" / f"{lang}.md"
        if not path.exists():
            errors.append(f"missing {path.relative_to(root).as_posix()}")
            continue

        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        if not text.startswith("# "):
            errors.append(f"{rel}: missing H1")
        if "Keep reference tags unchanged" not in text and "reference tags unchanged" not in text:
            errors.append(f"{rel}: missing reference-tag preservation note")
        if "| Function |" not in text:
            errors.append(f"{rel}: missing Function vocabulary table")
        if "## Slop Traps" not in text:
            errors.append(f"{rel}: missing Slop Traps section (language-specific empty-quality words)")

        rows = table_rows(text)
        min_rows = 40
        if args.strict and len(rows) < min_rows:
            errors.append(f"{rel}: expected at least {min_rows} rows, found {len(rows)}")

        functions = set()
        for i, row in enumerate(rows, start=1):
            function, term, meaning = row[0], row[1], row[2]
            functions.add(function)
            if function not in ALLOWED_FUNCTIONS:
                errors.append(f"{rel}: row {i} has unsupported function `{function}`")
            if not function or not term or not meaning:
                errors.append(f"{rel}: row {i} has an empty cell")

        if args.strict:
            missing = STRICT_REQUIRED_FUNCTIONS - functions
            if missing:
                errors.append(f"{rel}: missing strict functions " + ", ".join(sorted(missing)))

        for protected in PROTECTED_TERMS:
            if protected in text:
                errors.append(f"{rel}: protected term `{protected}` should not appear in active vocab")

        if not re.search(r"@Image1.*@Video1|@Image1.*@Audio1", text, re.S):
            errors.append(f"{rel}: expected unchanged reference tag examples")

    errors.extend(validate_native_review(root))

    if errors:
        print("Vocab schema errors:")
        for error in errors:
            print(f"- {error}")
        return 1

    evidence = load_json(root / NATIVE_REVIEW_EVIDENCE)
    evidence_state = evidence.get("review_state") if isinstance(evidence, dict) else None
    if evidence_state == "review_records_structurally_complete":
        print(
            "Vocab schema check passed. Review records are structurally complete; "
            "reviewer identity, reasoning adequacy, universal native fluency, and author "
            "provenance are not inferred."
        )
    else:
        print(
            "Vocab schema check passed. Native-language quality remains pending human review; "
            "author provenance is not inferred."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import unicodedata
from collections import Counter
from pathlib import Path, PurePosixPath

if __package__:
    from .strict_json import diagnostic_text, load_json
else:
    from strict_json import diagnostic_text, load_json


REQUIRED_SNIPPETS = {
    "SKILL.md": [
        "## Sequence Gate",
        "## Director's Read Gate",
        "[Director's Read](references/directors-read.md)",
        "skills/seedance-sequence/SKILL.md",
        "skills/seedance-continuation/SKILL.md",
        "accepted observed state overrides planned state",
        "rejected footage",
        "exact reference tags",
    ],
    "skills/seedance-sequence/SKILL.md": [
        "Plan globally",
        "final outcome",
        "provisional intent cards",
        "Clip 01 final Seedance prompt",
    ],
    "skills/seedance-continuation/SKILL.md": [
        "Required Input Gate",
        "accepted previous clip or accepted final frame",
        "observed_end_state",
        "Do not hide this uncertainty",
    ],
    "references/prompt-compiler.md": [
        "[Director's Read](directors-read.md)",
        "visible or audible carriers",
        "natural-language Seedance prompt",
        "Do not emit internal JSON",
        "Do not replay completed actions",
        "Do not perform reserved later actions",
    ],
    "references/surface-prompt-profiles.md": [
        "Do not hardcode duration",
        "conservative generic profile",
    ],
}


PROMPT_PRODUCING_SKILLS = {
    "skills/seedance-antislop/SKILL.md",
    "skills/seedance-audio/SKILL.md",
    "skills/seedance-camera/SKILL.md",
    "skills/seedance-continuation/SKILL.md",
    "skills/seedance-copyright/SKILL.md",
    "skills/seedance-examples-ja/SKILL.md",
    "skills/seedance-examples-ko/SKILL.md",
    "skills/seedance-examples-zh/SKILL.md",
    "skills/seedance-filter/SKILL.md",
    "skills/seedance-interview-short/SKILL.md",
    "skills/seedance-interview/SKILL.md",
    "skills/seedance-lighting/SKILL.md",
    "skills/seedance-motion/SKILL.md",
    "skills/seedance-prompt-short/SKILL.md",
    "skills/seedance-prompt/SKILL.md",
    "skills/seedance-recipes/SKILL.md",
    "skills/seedance-sequence/SKILL.md",
    "skills/seedance-style/SKILL.md",
    "skills/seedance-troubleshoot/SKILL.md",
    "skills/seedance-vfx/SKILL.md",
    "skills/seedance-vocab-en/SKILL.md",
    "skills/seedance-vocab-es/SKILL.md",
    "skills/seedance-vocab-ja/SKILL.md",
    "skills/seedance-vocab-ko/SKILL.md",
    "skills/seedance-vocab-ru/SKILL.md",
    "skills/seedance-vocab-zh/SKILL.md",
}

# Keep exemptions explicit and exhaustive. A newly added skill cannot silently
# escape the Director's Read merely because this route table was not updated.
NON_PROMPT_PRODUCING_SKILLS = {
    "skills/seedance-characters/SKILL.md": (
        "returns a character card and continuity constraints, not prompt text"
    ),
    "skills/seedance-pipeline/SKILL.md": (
        "returns a sourced workflow plan and names the next artifact, not prompt text"
    ),
}

DIRECTORS_READ_ROUTES = {
    "SKILL.md": "references/directors-read.md",
    **{
        rel: "../../references/directors-read.md"
        for rel in sorted(PROMPT_PRODUCING_SKILLS)
    },
    "references/directing-engine.md": "directors-read.md",
    "references/prompt-compiler.md": "directors-read.md",
}

DIRECTORS_READ_ACTIVATION_PHRASES = {
    "SKILL.md": "before any route drafts, compresses, or compiles a prompt",
    **{rel: "before producing prompt text" for rel in PROMPT_PRODUCING_SKILLS},
    "references/directing-engine.md": "load the [Director's Read](directors-read.md) first on every route",
    "references/prompt-compiler.md": "before compilation",
}

MARKDOWN_LINK_RE = re.compile(r"\[[^\]\n]+\]\((?P<target>[^)\n]+)\)")

NO_MEMORY_ESCAPE_FILES = list(DIRECTORS_READ_ROUTES) + [
    "references/progressive-disclosure.md",
]

DIRECTORS_READ_FIELDS = [
    "dramatic function",
    "turn",
    "POV",
    "power shift",
    "hidden want/objective",
    "obstacle/tactic",
    "subtext/contradiction",
    "visible suppressed behavior",
    "non-transferable detail",
    "stock solution refused",
]

DIRECTORS_READ_CASES = {
    "silent-breakup": "narrative",
    "perfume-turntable": "non_narrative",
    "product-with-performer-choice": "narrative",
    "abstract-logo-reveal": "non_narrative",
    "dancer-masks-missed-cue": "narrative",
    "hands-only-assembly-demo": "non_narrative",
}

GENRE_LIBRARY_LANES = {
    "Product / commercial reveal": "non-narrative",
    "Music video beat": "narrative",
    "Horror / suspense": "narrative",
    "Anime / 2D power-up": "narrative",
    "Action / pursuit": "narrative",
    "Comedy pratfall": "narrative",
    "UGC / caught real moment": "narrative",
    "Transformation / VFX brand reveal": "non-narrative",
    "Establishing / landscape": "non-narrative",
    "Beauty / cosmetics": "non-narrative",
    "Food / culinary": "non-narrative",
    "Automotive / commercial": "non-narrative",
    "High fashion / editorial": "narrative",
    "Fashion runway": "narrative",
    "Real estate / property tour": "non-narrative",
    "Talking-head pitch (口播)": "narrative",
    "Sports / hype": "narrative",
    "Fitness / workout": "narrative",
    "Travel / cinematic vlog": "narrative",
    "Dialogue-driven two-hander": "narrative",
    "Short drama (短剧)": "narrative",
    "Romance": "narrative",
    "Noir / detective": "narrative",
    "Fantasy / epic": "narrative",
    "Sci-fi": "narrative",
    "Nostalgia / vintage memory": "narrative",
    "3D / CG animation": "narrative",
    "Stop-motion / claymation": "narrative",
    "Kids / children's content": "narrative",
    "Documentary interview": "narrative",
    "Nature / wildlife": "narrative",
    "Pet / animal portrait": "narrative",
    "Time-lapse / hyperlapse": "non-narrative",
}

GENRE_FIELD_RE = re.compile(
    r"`(?P<field>[^`]+)`:\s*(?P<value>.*?)(?=;\s*`[^`]+`:\s*|$)"
)
GENRE_ENTRY_RE = re.compile(
    r"^### (?P<name>.+?)\n(?P<body>.*?)(?=^### |\Z)",
    re.MULTILINE | re.DOTALL,
)

CREATIVE_STOP_TERMS = {
    "a", "after", "an", "and", "as", "at", "be", "before", "but", "by", "for",
    "from", "in", "into", "is", "it", "its", "of", "on", "or", "over",
    "that", "the", "then", "this", "through", "to", "under", "while", "with",
}
CREATIVE_GENERIC_TERMS = {
    "act", "action", "another", "appear", "camera", "change", "character",
    "cinematic", "control", "creative", "dramatic", "event", "feeling", "generic",
    "good", "happen", "interesting", "moment", "move", "object", "obstacle",
    "occur", "ordinary", "outcome", "person", "quality", "reaction", "scene",
    "shot", "show", "side", "situation", "small", "something", "state", "story",
    "stuff", "subject", "thing", "use", "video", "want",
}
CREATIVE_GENERIC_PHRASES = {
    "handled from memory",
    "make it cinematic",
    "make it interesting",
    "something happens",
    "use good judgment",
}
CREATIVE_DEFAULT_IGNORABLE_RANGES = (
    (0x034F, 0x034F),
    (0x115F, 0x1160),
    (0x17B4, 0x17B5),
    (0x180B, 0x180F),
    (0x2800, 0x2800),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFFA0, 0xFFA0),
    (0xFFF0, 0xFFF8),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)


def _creative_default_ignorable(character: str) -> bool:
    if unicodedata.category(character) == "Cf":
        return True
    codepoint = ord(character)
    return any(
        start <= codepoint <= end
        for start, end in CREATIVE_DEFAULT_IGNORABLE_RANGES
    )


def _creative_normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = "".join(
        character
        for character in normalized
        if not _creative_default_ignorable(character)
    )
    return " ".join(normalized.split())


def _term_variants(term: str) -> set[str]:
    variants = {term}
    for suffix in ("ing", "ed", "es", "s"):
        if term.endswith(suffix) and len(term) - len(suffix) >= 4:
            variants.add(term[: -len(suffix)])
    return variants


def _uses_unsegmented_script(term: str) -> bool:
    return any(
        "CJK" in unicodedata.name(character, "")
        or "HIRAGANA" in unicodedata.name(character, "")
        or "KATAKANA" in unicodedata.name(character, "")
        or "HANGUL" in unicodedata.name(character, "")
        or "THAI" in unicodedata.name(character, "")
        or "LAO" in unicodedata.name(character, "")
        or "KHMER" in unicodedata.name(character, "")
        or "MYANMAR" in unicodedata.name(character, "")
        for character in term
    )


def creative_terms(value: str) -> set[str]:
    """Return concrete comparison terms without treating style words as evidence."""

    terms: set[str] = set()
    for term in re.findall(r"[^\W_]+", _creative_normalize(value), re.UNICODE):
        if term in CREATIVE_STOP_TERMS:
            continue
        if _uses_unsegmented_script(term) and len(term) > 1:
            terms.update(term[index:index + 2] for index in range(len(term) - 1))
            continue
        variants = _term_variants(term)
        if variants & CREATIVE_GENERIC_TERMS:
            continue
        terms.update(variants)
    return terms


def creative_specificity_errors(
    fields: dict[str, str],
    carriers: str | list[str],
    *,
    label: str,
    carrier_fields: tuple[str, ...],
) -> list[str]:
    """Reject a filled-in taxonomy whose choices do not reach filmable carriers."""

    errors: list[str] = []
    normalized = {
        field: _creative_normalize(value)
        for field, value in fields.items()
        if isinstance(value, str)
    }
    duplicates = Counter(normalized.values())
    repeated = sorted(
        field
        for field, value in normalized.items()
        if value and duplicates[value] > 1
    )
    if repeated:
        errors.append(
            f"{label} reuses the same content across Director's Read fields: "
            f"{', '.join(repeated)}"
        )

    field_terms: dict[str, set[str]] = {}
    for field, value in fields.items():
        if not isinstance(value, str):
            continue
        terms = creative_terms(value)
        field_terms[field] = terms
        phrase = re.sub(r"[^\w]+", " ", _creative_normalize(value)).strip()
        normalized_field = field.replace("_", " ").replace("-", " ").casefold()
        minimum_terms = 1 if normalized_field == "pov" else 2
        if normalized_field in {
            "non transferable detail",
            "stock solution refused",
            "visible suppressed behavior",
        }:
            minimum_terms = 3
        if len(terms) < minimum_terms or phrase in CREATIVE_GENERIC_PHRASES:
            errors.append(f"{label} {field} lacks creative specificity")

    distinct_terms = set().union(*field_terms.values()) if field_terms else set()
    if len(distinct_terms) < 20:
        errors.append(
            f"{label} lacks creative specificity across the complete Director's Read"
        )

    carrier_text = (
        " ".join(item for item in carriers if isinstance(item, str))
        if isinstance(carriers, list)
        else carriers
    )
    carrier_terms = creative_terms(carrier_text) if isinstance(carrier_text, str) else set()
    for field in carrier_fields:
        terms = field_terms.get(field, set())
        if terms and len(terms.intersection(carrier_terms)) < 2:
            errors.append(
                f"{label} compiled carriers do not carry {field} into visible or audible action"
            )
    return errors


def utility_prompt_relevance_errors(intent: str, prompt: str, *, label: str) -> list[str]:
    """Require a non-narrative prompt to retain the concrete utility it was given."""

    intent_terms = creative_terms(intent)
    if not intent_terms:
        return [f"{label}: utility_intent lacks concrete utility specificity"]
    if len(intent_terms.intersection(creative_terms(prompt))) < 2:
        return [f"{label}: generation prompt is unrelated to utility_intent"]
    return []


def validate_directors_read_routes(root: Path, errors: list[str]) -> None:
    """Statically check that each documented route is explicit and install-relative."""

    root = root.resolve()
    canonical = (root / "references" / "directors-read.md").resolve()
    actual_skills = {
        path.relative_to(root).as_posix()
        for path in (root / "skills").rglob("SKILL.md")
    }
    classified_skills = PROMPT_PRODUCING_SKILLS | set(NON_PROMPT_PRODUCING_SKILLS)
    for rel in sorted(actual_skills - classified_skills):
        errors.append(
            f"{rel}: skill must be classified as prompt-producing or explicitly exempt"
        )
    for rel in sorted(classified_skills - actual_skills):
        errors.append(f"{rel}: stale Director's Read skill classification")

    for rel, target in DIRECTORS_READ_ROUTES.items():
        path = root / rel
        if not path.is_file():
            errors.append(f"missing {rel}")
            continue

        text = path.read_text(encoding="utf-8")
        if "[ref:directors-read]" in text.casefold():
            errors.append(f"{rel}: opaque Director's Read alias is not portable")

        link_targets = {match.group("target") for match in MARKDOWN_LINK_RE.finditer(text)}
        if target not in link_targets:
            errors.append(
                f"{rel}: must link the canonical Director's Read as `{target}`"
            )

        phrase = DIRECTORS_READ_ACTIVATION_PHRASES[rel]
        if phrase.casefold() not in text.casefold():
            errors.append(f"{rel}: must require the Director's Read `{phrase}`")

        if "\\" in target or ":" in target or target.startswith("/"):
            errors.append(f"{rel}: Director's Read route is not a portable relative path")
            continue
        candidate = path.parent.joinpath(*PurePosixPath(target).parts)
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            errors.append(f"{rel}: Director's Read route target does not exist: {target}")
            continue
        if resolved != canonical or not candidate.is_file():
            errors.append(f"{rel}: Director's Read route does not resolve to the canonical file")


def validate_directors_read_cases(root: Path, errors: list[str]) -> None:
    cases_rel = "validation/fixtures/directors-read-cases.json"
    cases_path = root / cases_rel
    if not cases_path.exists():
        errors.append(f"missing {cases_rel}")
        return
    try:
        cases = load_json(cases_path, expected_type=list, root=root)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        errors.append(diagnostic_text(f"{cases_rel}: invalid JSON: {exc}"))
        return
    if not all(isinstance(case, dict) for case in cases):
        errors.append(f"{cases_rel}: expected a list of case objects")
        return

    actual: dict[str, str] = {}
    for index, case in enumerate(cases):
        case_id = case.get("id")
        lane = case.get("expected_lane")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{cases_rel}: case[{index}] id must be a non-empty string")
            continue
        if not isinstance(lane, str):
            errors.append(f"{cases_rel}: {case_id} expected_lane must be a string")
            continue
        if case_id in actual:
            errors.append(f"{cases_rel}: duplicate case id {case_id}")
            continue
        actual[case_id] = lane
    if len(cases) != len(DIRECTORS_READ_CASES) or actual != DIRECTORS_READ_CASES:
        errors.append(f"{cases_rel}: adversarial lane map must stay deterministic")
    for case in cases:
        case_id = case.get("id", "<missing id>")
        case_label = f"{cases_rel}: {case_id}"
        if not isinstance(case.get("brief"), str) or not case["brief"].strip():
            errors.append(f"{case_label} brief must be a non-empty string")
        if case.get("expected_lane") == "narrative":
            read = case.get("directors_read")
            if not isinstance(read, dict) or list(read) != DIRECTORS_READ_FIELDS:
                errors.append(f"{case_label} must carry the ordered canonical narrative read")
            elif not all(isinstance(value, str) and value.strip() for value in read.values()):
                errors.append(f"{case_label} has an empty narrative field")
            else:
                errors.extend(
                    creative_specificity_errors(
                        read,
                        str(case.get("compiled_carriers", "")),
                        label=case_label,
                        carrier_fields=(
                            "visible suppressed behavior",
                            "non-transferable detail",
                        ),
                    )
                )
            if (
                not isinstance(case.get("compiled_carriers"), str)
                or not case["compiled_carriers"].strip()
            ):
                errors.append(f"{case_label} needs compiled visible or audible carriers")
            compiled = (
                case["compiled_carriers"].lower()
                if isinstance(case.get("compiled_carriers"), str)
                else ""
            )
            leaked = [field for field in DIRECTORS_READ_FIELDS if f"{field.lower()}:" in compiled]
            if leaked:
                errors.append(f"{case_label} leaked internal labels: {', '.join(leaked)}")
        elif case.get("expected_lane") == "non_narrative":
            if case.get("directors_read") is not None:
                errors.append(f"{case_label} must not fabricate a narrative read")
            if (
                not isinstance(case.get("utility_intent"), str)
                or not case["utility_intent"].strip()
            ):
                errors.append(f"{case_label} needs a utility intent")
            if (
                not isinstance(case.get("refusal"), str)
                or "no invented" not in case["refusal"].lower()
            ):
                errors.append(f"{case_label} needs an explicit no-invented-drama refusal")
        else:
            errors.append(f"{case_label} has an unsupported expected_lane")


def validate_directors_read_genre_library(root: Path, errors: list[str]) -> None:
    """Require every genre example to exercise a complete canonical lane record."""

    rel = "references/directing-engine-genre-library.md"
    path = root / rel
    if not path.is_file():
        errors.append(f"missing {rel}")
        return
    entries = {
        match.group("name"): match.group("body")
        for match in GENRE_ENTRY_RE.finditer(path.read_text(encoding="utf-8"))
    }
    if set(entries) != set(GENRE_LIBRARY_LANES):
        missing = sorted(set(GENRE_LIBRARY_LANES) - set(entries))
        extra = sorted(set(entries) - set(GENRE_LIBRARY_LANES))
        errors.append(
            f"{rel}: expected the canonical 33 genre entries; missing={missing}, extra={extra}"
        )
        return

    for name, expected_lane in GENRE_LIBRARY_LANES.items():
        label = f"{rel}: {name}"
        body = entries[name]
        read_match = re.search(
            r"^- \*\*Read - (narrative|non-narrative) lane\.\*\* (?P<record>.+)$",
            body,
            re.MULTILINE,
        )
        if read_match is None:
            errors.append(f"{label} must declare one canonical lane record")
            continue
        actual_lane = read_match.group(1)
        if actual_lane != expected_lane:
            errors.append(f"{label} must use the {expected_lane} lane")
            continue
        pairs = GENRE_FIELD_RE.findall(read_match.group("record"))
        record = {field: value.strip() for field, value in pairs}
        if len(record) != len(pairs):
            errors.append(f"{label} repeats a canonical record field")

        prompt_match = re.search(r"^- \*\*Prompt:\*\* `(.+)`$", body, re.MULTILINE)
        if prompt_match is None:
            errors.append(f"{label} needs one compiled prompt")
            continue
        prompt = prompt_match.group(1)

        if expected_lane == "narrative":
            if list(record) != DIRECTORS_READ_FIELDS:
                errors.append(f"{label} must carry the ordered ten-field narrative record")
                continue
            if not all(record.values()):
                errors.append(f"{label} has an empty narrative field")
                continue
            errors.extend(
                creative_specificity_errors(
                    record,
                    prompt,
                    label=label,
                    carrier_fields=(
                        "visible suppressed behavior",
                        "non-transferable detail",
                    ),
                )
            )
            leaked = [
                field for field in DIRECTORS_READ_FIELDS
                if f"{field.casefold()}:" in prompt.casefold()
            ]
            if leaked:
                errors.append(f"{label} leaked internal labels: {', '.join(leaked)}")
        else:
            if list(record) != ["utility intent", "non-narrative refusal"]:
                errors.append(f"{label} must carry only the two-field non-narrative record")
                continue
            if "no invented" not in record["non-narrative refusal"].casefold():
                errors.append(f"{label} needs an explicit no-invented-drama refusal")
            errors.extend(
                utility_prompt_relevance_errors(
                    record["utility intent"], prompt, label=label
                )
            )


DOMAIN_FILES = [
    "skills/seedance-camera/SKILL.md",
    "skills/seedance-motion/SKILL.md",
    "skills/seedance-characters/SKILL.md",
    "skills/seedance-audio/SKILL.md",
    "skills/seedance-lighting/SKILL.md",
    "skills/seedance-style/SKILL.md",
    "skills/seedance-recipes/SKILL.md",
    "skills/seedance-prompt-short/SKILL.md",
    "skills/seedance-troubleshoot/SKILL.md",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    errors: list[str] = []

    for rel, snippets in REQUIRED_SNIPPETS.items():
        path = root / rel
        if not path.exists():
            errors.append(f"missing {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        low = text.lower()
        for snippet in snippets:
            if snippet.lower() not in low:
                errors.append(f"{rel}: missing behavior phrase `{snippet}`")

    for rel in DOMAIN_FILES:
        path = root / rel
        if not path.exists():
            errors.append(f"missing {rel}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        if "sequence state" not in text or "reserved" not in text or "continuity locks" not in text:
            errors.append(f"{rel}: must read sequence state, continuity locks, and reserved beats when present")

    canonical_rel = "references/directors-read.md"
    canonical_path = root / canonical_rel
    if not canonical_path.exists():
        errors.append(f"missing {canonical_rel}")
    else:
        canonical = canonical_path.read_text(encoding="utf-8")
        canonical_low = canonical.lower()
        for field in DIRECTORS_READ_FIELDS:
            if f"`{field}`" not in canonical:
                errors.append(f"{canonical_rel}: missing canonical field `{field}`")
        for phrase in (
            "narrative lane",
            "non-narrative lane",
            "do not fabricate",
            "internal planning only",
            "visible or audible carriers",
            "before prompt compilation",
        ):
            if phrase not in canonical_low:
                errors.append(f"{canonical_rel}: missing boundary phrase `{phrase}`")

    validate_directors_read_routes(root, errors)

    for rel in NO_MEMORY_ESCAPE_FILES:
        path = root / rel
        if not path.exists():
            continue
        low = path.read_text(encoding="utf-8").lower()
        if "inline from memory" in low or "apply craft from memory" in low:
            errors.append(f"{rel}: must not replace the Director's Read with memory")

    validate_directors_read_cases(root, errors)
    validate_directors_read_genre_library(root, errors)

    if errors:
        print("Behavior contract errors:")
        for error in errors:
            print(diagnostic_text(f"- {error}"))
        return 1
    print("Behavior contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

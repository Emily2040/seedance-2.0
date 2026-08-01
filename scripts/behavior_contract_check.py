#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_SNIPPETS = {
    "SKILL.md": [
        "## Sequence Gate",
        "## Director's Read Gate",
        "[ref:directors-read]",
        "[skill:seedance-sequence]",
        "[skill:seedance-continuation]",
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
        "[ref:directors-read]",
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


DIRECTORS_READ_ROUTES = [
    "SKILL.md",
    "skills/seedance-interview/SKILL.md",
    "skills/seedance-interview-short/SKILL.md",
    "skills/seedance-prompt/SKILL.md",
    "skills/seedance-prompt-short/SKILL.md",
    "skills/seedance-sequence/SKILL.md",
    "skills/seedance-continuation/SKILL.md",
    "references/prompt-compiler.md",
]

NO_MEMORY_ESCAPE_FILES = DIRECTORS_READ_ROUTES + [
    "references/directing-engine.md",
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
    parser.add_argument("--strict", action="store_true")
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

    for rel in DIRECTORS_READ_ROUTES:
        path = root / rel
        if not path.exists():
            errors.append(f"missing {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        low = text.lower()
        if "[ref:directors-read]" not in text:
            errors.append(f"{rel}: must route through the canonical Director's Read")

    for rel in NO_MEMORY_ESCAPE_FILES:
        path = root / rel
        if not path.exists():
            continue
        low = path.read_text(encoding="utf-8").lower()
        if "inline from memory" in low or "apply craft from memory" in low:
            errors.append(f"{rel}: must not replace the Director's Read with memory")

    cases_rel = "validation/fixtures/directors-read-cases.json"
    cases_path = root / cases_rel
    if not cases_path.exists():
        errors.append(f"missing {cases_rel}")
    else:
        try:
            cases = json.loads(cases_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{cases_rel}: invalid JSON: {exc}")
        else:
            if not isinstance(cases, list) or not all(isinstance(case, dict) for case in cases):
                errors.append(f"{cases_rel}: expected a list of case objects")
                cases = []
            actual = {case.get("id"): case.get("expected_lane") for case in cases}
            if len(cases) != len(DIRECTORS_READ_CASES) or actual != DIRECTORS_READ_CASES:
                errors.append(f"{cases_rel}: adversarial lane map must stay deterministic")
            for case in cases:
                case_id = case.get("id", "<missing id>")
                if case.get("expected_lane") == "narrative":
                    read = case.get("directors_read")
                    if not isinstance(read, dict) or list(read) != DIRECTORS_READ_FIELDS:
                        errors.append(f"{cases_rel}: {case_id} must carry the ordered canonical narrative read")
                    elif not all(isinstance(value, str) and value.strip() for value in read.values()):
                        errors.append(f"{cases_rel}: {case_id} has an empty narrative field")
                    if not str(case.get("compiled_carriers", "")).strip():
                        errors.append(f"{cases_rel}: {case_id} needs compiled visible or audible carriers")
                    compiled = str(case.get("compiled_carriers", "")).lower()
                    leaked = [field for field in DIRECTORS_READ_FIELDS if f"{field.lower()}:" in compiled]
                    if leaked:
                        errors.append(f"{cases_rel}: {case_id} leaked internal labels: {', '.join(leaked)}")
                elif case.get("expected_lane") == "non_narrative":
                    if case.get("directors_read") is not None:
                        errors.append(f"{cases_rel}: {case_id} must not fabricate a narrative read")
                    if not str(case.get("utility_intent", "")).strip():
                        errors.append(f"{cases_rel}: {case_id} needs a utility intent")
                    if "no invented" not in str(case.get("refusal", "")).lower():
                        errors.append(f"{cases_rel}: {case_id} needs an explicit no-invented-drama refusal")

    if errors:
        print("Behavior contract errors:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Behavior contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

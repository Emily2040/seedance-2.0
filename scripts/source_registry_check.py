#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

REQUIRED_LABELS = ["confirmed", "volatile", "field-observed", "unverified", "internal"]
REQUIRED_OFFICIAL_MARKERS = ["seed.bytedance.com", "volcengine.com", "arxiv.org", "runwayml.com"]
LAST_VERIFIED_FIELD = re.compile(r"^last_verified:\s*(.*?)\s*$", re.M)

# Wall-clock staleness thresholds for references/source-registry.md.
STALE_WARN_DAYS = 14
STALE_ERROR_DAYS = 30


def parse_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def checked_in_last_verified(
    text: str, label: str, today: date, errors: list[str]
) -> date | None:
    """Read one explicit checked-in verification stamp.

    Other dates in the document may describe launches, releases, retrievals, or
    historical events. They are not evidence that this document was re-read.
    """
    values = LAST_VERIFIED_FIELD.findall(text)
    if not values:
        errors.append(f"{label} missing last_verified: YYYY-MM-DD")
        return None
    if len(values) != 1:
        errors.append(f"{label} must contain exactly one last_verified field")
        return None
    raw = values[0]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        errors.append(f"{label} has malformed last_verified `{raw}`; expected YYYY-MM-DD")
        return None
    verified = parse_date(raw)
    if verified is None:
        errors.append(f"{label} has invalid last_verified date `{raw}`")
        return None
    if verified > today:
        days = (verified - today).days
        errors.append(
            f"{label} last_verified {verified.isoformat()} is {days} "
            f"day{'s' if days != 1 else ''} in the future"
        )
        return None
    return verified


def freshness_findings(
    verified: date, today: date, enforce: bool
) -> tuple[list[str], list[str]]:
    """Classify how stale `last_verified` is.

    Staleness depends on the wall clock, so an unchanged commit changes verdict
    as days pass. Reporting it as an error would make every unrelated pull
    request fail on a calendar boundary, so it is a warning unless enforcement
    is requested explicitly (scheduled review or release).
    """
    age = (today - verified).days
    if age < 0:
        days = -age
        return [
            f"source-registry.md last_verified {verified.isoformat()} is {days} "
            f"day{'s' if days != 1 else ''} in the future"
        ], []
    if age <= STALE_WARN_DAYS:
        return [], []
    message = f"source-registry.md last_verified is {age} days old"
    if age > STALE_ERROR_DAYS and enforce:
        return [message], []
    return [], [message]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate checked-in source metadata offline; no URLs are fetched."
    )
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--enforce-freshness",
        action="store_true",
        help=(
            "fail when checked-in source-registry.md last_verified metadata is older than "
            f"{STALE_ERROR_DAYS} days; intended for scheduled review and release, "
            "not for per-pull-request validation; does not verify upstream claims"
        ),
    )
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    registry = root / "references" / "source-registry.md"
    if not registry.exists():
        errors.append("missing references/source-registry.md")
    else:
        text = registry.read_text(encoding="utf-8")
        today = date.today()
        verified = checked_in_last_verified(text, "source-registry.md", today, errors)
        if verified:
            stale_errors, stale_warnings = freshness_findings(
                verified, today, args.enforce_freshness
            )
            errors.extend(stale_errors)
            warnings.extend(stale_warnings)

        for label in REQUIRED_LABELS:
            if f"`{label}`" not in text:
                errors.append(f"source-registry.md missing evidence label `{label}`")

        for marker in REQUIRED_OFFICIAL_MARKERS:
            if marker not in text:
                errors.append(f"source-registry.md missing official source marker `{marker}`")

        for line in text.splitlines():
            if "|" not in line or line.lstrip().startswith("|---"):
                continue
            if "volatile" in line and "Recheck" not in line and "recheck" not in line:
                errors.append("volatile source row must include recheck wording")
            if any(word in line.lower() for word in ["reddit", "community", "corpus", "forum"]) and not any(
                label in line for label in ["field-observed", "unverified", "internal"]
            ):
                errors.append("community source row must be field-observed, unverified, or internal")

        if "Seedance 2.0 Pro" in text and "ambiguous" not in text.lower():
            errors.append("Seedance 2.0 Pro appears without an ambiguity correction")

    data_path = root / "data" / "sources.seedance-2026-05-30.json"
    if not data_path.exists():
        errors.append("missing data/sources.seedance-2026-05-30.json")
    else:
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"source data JSON parse error: {exc}")
        else:
            sources = data.get("sources")
            if not isinstance(sources, list) or len(sources) < 20:
                errors.append("source data must contain at least twenty source records")
            else:
                for i, source in enumerate(sources):
                    for key in ["id", "title", "url", "language", "source_type", "retrieved_at", "confidence", "claims"]:
                        if key not in source:
                            errors.append(f"source record {i} missing `{key}`")
                    if source.get("source_type", "").startswith("community") and source.get("confidence") == "high":
                        warnings.append(f"community source `{source.get('id')}` should rarely be high confidence")

    # Internal-consistency gate: volatile platform references must not drift far behind
    # api-status.md. This compares two checked-in dates, so its verdict depends only on
    # repository content and never on the wall clock. It stays a hard error.
    api_status = root / "references" / "api-status.md"
    if api_status.exists():
        today = date.today()
        anchor = checked_in_last_verified(
            api_status.read_text(encoding="utf-8"), "api-status.md", today, errors
        )
        if anchor:
            freshness_critical = [
                "platform-surface-matrix.md", "api-workflow.md", "model-name-map.md",
                "platform-constraints.md", "field-observed-tips.md", "agent-compatibility.md",
            ]
            for name in freshness_critical:
                ref = root / "references" / name
                if not ref.exists():
                    continue
                ref_verified = checked_in_last_verified(
                    ref.read_text(encoding="utf-8"), name, today, errors
                )
                if ref_verified is None:
                    continue
                drift = (anchor - ref_verified).days
                if drift > 30:
                    errors.append(
                        f"{name} is {drift} days behind api-status last_verified ({anchor.isoformat()}); "
                        "re-verify and re-stamp before release"
                    )

    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"- {warning}")
        print()

    if errors:
        print("Source registry errors:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Offline source metadata check passed.")
    print(
        "Boundary: checked-in dates, labels, and source markers were validated; "
        "this does not fetch URLs or verify upstream claims live."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

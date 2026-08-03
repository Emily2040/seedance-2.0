#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
from datetime import date
from pathlib import Path

if __package__:
    from .strict_json import (
        diagnostic_path,
        diagnostic_text,
        load_json,
        read_repo_text,
        validate_repo_input_path,
    )
else:
    from strict_json import (
        diagnostic_path,
        diagnostic_text,
        load_json,
        read_repo_text,
        validate_repo_input_path,
    )

REQUIRED_LABELS = ["confirmed", "volatile", "field-observed", "unverified", "internal"]
REQUIRED_OFFICIAL_MARKERS = ["seed.bytedance.com", "volcengine.com", "arxiv.org", "runwayml.com"]
# Match one logical metadata line on both LF and CRLF checkouts.  ``$`` in
# multiline mode stops before ``\n`` but not before the preceding ``\r``;
# excluding line terminators from the value keeps the parsed date independent
# of Git's working-tree newline conversion.
LAST_VERIFIED_FIELD = re.compile(
    r"^last_verified:[ \t]*([^\r\n]*?)[ \t]*\r?$", re.M
)

# Wall-clock staleness thresholds for references/source-registry.md.
STALE_WARN_DAYS = 14
STALE_ERROR_DAYS = 30


def parse_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def repository_head_date(root: Path) -> date | None:
    """Return HEAD's stable committer date, or None outside a Git checkout.

    Pull-request validation needs an upper bound for impossible future
    verification stamps, but the wall clock is not a property of the commit.
    Git's ``%cs`` value is stored in the commit object, so every runner judging
    the same HEAD uses the same date.  Downloaded archives have no such anchor;
    they still receive syntax and checked-in cross-file consistency checks.
    """
    try:
        top_level_result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    # `git -C` searches parent directories.  Without this containment check,
    # an extracted archive nested inside an unrelated checkout would inherit
    # that checkout's HEAD date and receive a false future-date verdict.
    top_level = top_level_result.stdout.rstrip("\r\n")
    try:
        if not top_level or Path(top_level).resolve() != root.resolve():
            return None
    except OSError:
        return None

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show", "-s", "--format=%cs", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    raw = result.stdout.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return None
    return parse_date(raw)


def checked_in_last_verified(
    text: str, label: str, today: date | None, errors: list[str]
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
    # The caller supplies either today's date for explicit freshness
    # enforcement or the stable HEAD date for pull-request validation.  It
    # passes None only when no deterministic anchor exists (for example, a
    # downloaded archive with no Git metadata).
    if today is not None and verified > today:
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
        message = (
            f"source-registry.md last_verified {verified.isoformat()} is {days} "
            f"day{'s' if days != 1 else ''} in the future"
        )
        return ([message], []) if enforce else ([], [message])
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
    freshness_date = date.today() if args.enforce_freshness else None
    ordering_date = freshness_date or repository_head_date(root)

    references = root / "references"
    if os.path.lexists(references):
        try:
            validate_repo_input_path(root, references)
        except ValueError as exc:
            errors.append(f"references: {exc}")

    registry = root / "references" / "source-registry.md"
    if not os.path.lexists(registry):
        errors.append("missing references/source-registry.md")
    else:
        try:
            text = read_repo_text(root=root, path=registry)
        except ValueError as exc:
            errors.append(f"references/source-registry.md: {exc}")
            text = ""
        verified = checked_in_last_verified(
            text, "source-registry.md", ordering_date, errors
        )
        if verified and freshness_date is not None:
            stale_errors, stale_warnings = freshness_findings(
                verified, freshness_date, True
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
            data = load_json(data_path, expected_type=dict, root=root)
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
    if os.path.lexists(api_status):
        try:
            api_status_text = read_repo_text(root=root, path=api_status)
        except ValueError as exc:
            errors.append(f"references/api-status.md: {exc}")
            api_status_text = ""
        anchor = checked_in_last_verified(
            api_status_text,
            "api-status.md",
            ordering_date,
            errors,
        )
        if anchor:
            freshness_critical = [
                "platform-surface-matrix.md", "api-workflow.md", "model-name-map.md",
                "platform-constraints.md", "field-observed-tips.md", "agent-compatibility.md",
            ]
            for name in freshness_critical:
                ref = root / "references" / name
                if not os.path.lexists(ref):
                    continue
                try:
                    ref_text = read_repo_text(root=root, path=ref)
                except ValueError as exc:
                    errors.append(
                        f"{diagnostic_path(ref.relative_to(root))}: {exc}"
                    )
                    continue
                ref_verified = checked_in_last_verified(
                    ref_text,
                    name,
                    ordering_date,
                    errors,
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
            print(diagnostic_text(f"- {warning}"))
        print()

    if errors:
        print("Source registry errors:")
        for error in errors:
            print(diagnostic_text(f"- {error}"))
        return 1

    print("Offline source metadata check passed.")
    print(
        "Boundary: checked-in dates, labels, and source markers were validated; "
        "this does not fetch URLs or verify upstream claims live."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

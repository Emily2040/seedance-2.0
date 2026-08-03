"""Shared project-lineage rules for every state consumer."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Literal

from strict_json import (
    MAX_DIAGNOSTIC_CHARS,
    MAX_DIAGNOSTIC_COUNT,
    MAX_DIAGNOSTIC_TOTAL_CHARS,
    bound_diagnostics,
    json_integer as strict_json_integer,
    load as load_strict_json,
    loads as loads_strict_json,
    safe_diagnostic_text,
)


ACCEPTED_PARENT_STATUSES = frozenset({"accepted", "accepted_with_deviation"})
PROVISIONAL_PARENT_STATUSES = frozenset({"planned", "ready"})
ALL_CLIP_STATUSES = frozenset(
    {
        "planned",
        "ready",
        "generated",
        "reviewed",
        "accepted",
        "accepted_with_deviation",
        "repair",
        "rejected",
    }
)
MAX_LINEAGE_ERRORS = MAX_DIAGNOSTIC_COUNT
MAX_ERROR_CHARS = MAX_DIAGNOSTIC_CHARS
MAX_TOTAL_DIAGNOSTIC_CHARS = MAX_DIAGNOSTIC_TOTAL_CHARS
MAX_IDENTIFIER_CHARS = 256
MAX_CYCLE_DISPLAY_NODES = 8
MAX_TAKE_HISTORY_ITEMS = 4096
MAX_TAKE_EVIDENCE_CHARS = 4096
MAX_TAKE_REVIEW_FILES_PER_DIRECTORY = 4096
MAX_TAKE_REVIEW_BYTES = 1024 * 1024
MAX_TAKE_REVIEW_BYTES_PER_DIRECTORY = 16 * 1024 * 1024
MAX_REVIEWS_PER_TAKE_KEY = 2

VERDICT_CLIP_STATUS = {
    "accept": "accepted",
    "accept_with_deviation": "accepted_with_deviation",
    "repair": "repair",
    "reject": "rejected",
}
POST_REVIEW_CLIP_STATUSES = frozenset(VERDICT_CLIP_STATUS.values())
TAKE_HISTORY_REQUIRED_FIELDS = frozenset({"take_id", "clip_id", "verdict"})
TAKE_HISTORY_ALLOWED_FIELDS = frozenset(
    {*TAKE_HISTORY_REQUIRED_FIELDS, "evidence"}
)
TAKE_REVIEW_FIELDS = frozenset(
    {
        "project_id",
        "clip_id",
        "take_id",
        "source_status",
        "verdict",
        "observed_start_state",
        "observed_end_state",
        "completed_beats",
        "incomplete_beats",
        "unexpected_completed_beats",
        "continuity_breaks",
        "accepted_deviations",
        "observation_confidence",
        "uncertainties",
        "requires_user_confirmation",
    }
)
TAKE_REVIEW_SOURCE_STATUSES = frozenset(
    {"generated", "reviewed", "accepted", "accepted_with_deviation", "repair", "rejected"}
)
TAKE_REVIEW_OBSERVED_STATE_FIELDS = frozenset(
    {"observed_start_state", "observed_end_state"}
)
TAKE_REVIEW_STRING_ARRAY_FIELDS = frozenset(
    {
        "completed_beats",
        "incomplete_beats",
        "unexpected_completed_beats",
        "uncertainties",
    }
)
TAKE_REVIEW_ARRAY_FIELDS = frozenset(
    {"continuity_breaks", "accepted_deviations"}
)
TAKE_REVIEW_CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})

ParentIdKind = Literal["root", "invalid", "parent"]
ParentLinkMode = Literal[
    "accepted",
    "provisional",
    "missing_observed_end_state",
    "unusable_status",
]


@dataclass(frozen=True)
class LineageAnalysis:
    clips: list[dict]
    clips_by_id: dict[str, dict]
    accepted_links: list[tuple[dict, dict]]
    provisional_links: list[tuple[dict, dict]]
    errors: list[str]


@dataclass(frozen=True)
class TakeReviewRecord:
    path: Path
    data: dict


@dataclass(frozen=True)
class TakeReviewIndex:
    directory: Path
    records_by_key: dict[tuple[str, str, str], list[TakeReviewRecord]]
    diagnostics: tuple[str, ...]


def _bounded(value: object, limit: int = 80) -> str:
    """Render untrusted JSON values without terminal-control or size leakage."""

    if isinstance(value, str):
        if len(value) <= limit:
            return repr(value)
        preview = value[:limit] + "..."
        return f"{preview!r} ({len(value)} chars)"
    if isinstance(value, Decimal):
        _, digits, exponent = value.as_tuple()
        if len(digits) > limit:
            return f"<Decimal {len(digits)} digits exponent {exponent}>"
        return str(value)
    if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > 4096:
        return f"<integer {value.bit_length()} bits>"
    if isinstance(value, (dict, list, tuple, set)):
        return f"<{type(value).__name__}>"
    rendered = repr(value)
    if len(rendered) <= limit:
        return rendered
    return rendered[: limit - 3] + "..."


def _identifier(value: str) -> str:
    if (
        len(value) <= 80
        and value.isascii()
        and all(character.isalnum() or character in "._:-" for character in value)
    ):
        return value
    return _bounded(value)


def _safe_detail(value: str, limit: int = 200) -> str:
    return safe_diagnostic_text(value, limit)


def _fit_error(message: str) -> str:
    return safe_diagnostic_text(message, MAX_ERROR_CHARS)


def bound_validation_diagnostics(messages: list[str], rel: str) -> list[str]:
    return bound_diagnostics(messages, f"{rel}: additional validation diagnostics omitted")


def _append_error(errors: list[str], message: str, rel: str) -> None:
    omission = _fit_error(f"{rel}: additional lineage errors omitted")
    if errors and errors[-1] == omission:
        return

    def finish_with_omission() -> None:
        total = sum(len(error) for error in errors)
        while errors and total + len(omission) > MAX_TOTAL_DIAGNOSTIC_CHARS:
            total -= len(errors.pop())
        if len(errors) < MAX_LINEAGE_ERRORS:
            errors.append(omission)

    if len(errors) >= MAX_LINEAGE_ERRORS - 1:
        if len(errors) == MAX_LINEAGE_ERRORS - 1:
            finish_with_omission()
        return
    candidate = _fit_error(message)
    if sum(len(error) for error in errors) + len(candidate) > MAX_TOTAL_DIAGNOSTIC_CHARS:
        finish_with_omission()
        return
    errors.append(candidate)


def _append_take_error(errors: list[str], message: str, rel: str) -> None:
    omission = _fit_error(f"{rel}: additional take reconciliation diagnostics omitted")
    if errors and errors[-1] == omission:
        return

    def finish_with_omission() -> None:
        total = sum(len(error) for error in errors)
        while errors and total + len(omission) > MAX_TOTAL_DIAGNOSTIC_CHARS:
            total -= len(errors.pop())
        if len(errors) < MAX_LINEAGE_ERRORS:
            errors.append(omission)

    if len(errors) >= MAX_LINEAGE_ERRORS - 1:
        if len(errors) == MAX_LINEAGE_ERRORS - 1:
            finish_with_omission()
        return
    candidate = _fit_error(message)
    if sum(len(error) for error in errors) + len(candidate) > MAX_TOTAL_DIAGNOSTIC_CHARS:
        finish_with_omission()
        return
    errors.append(candidate)


def _is_bounded_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value) <= MAX_IDENTIFIER_CHARS
    )


def validate_take_review_record(review: object, label: str) -> list[str]:
    """Validate one take-review with the same record-local rules as its schema."""

    errors: list[str] = []
    if not isinstance(review, dict):
        _append_take_error(errors, f"{label}: take-review must be an object", label)
        return errors

    missing = sorted(TAKE_REVIEW_FIELDS - set(review))
    if missing:
        _append_take_error(
            errors,
            f"{label}: missing fields: {', '.join(missing)}",
            label,
        )

    unexpected_count = 0
    unexpected_preview: list[str] = []
    for field in review:
        if field in TAKE_REVIEW_FIELDS:
            continue
        unexpected_count += 1
        if len(unexpected_preview) < 8:
            unexpected_preview.append(_bounded(field, 64))
    if unexpected_count:
        rendered = ", ".join(unexpected_preview)
        if unexpected_count > len(unexpected_preview):
            rendered += f", ... ({unexpected_count} fields)"
        _append_take_error(
            errors,
            f"{label}: unexpected fields: {rendered}",
            label,
        )

    for field in ("project_id", "clip_id", "take_id"):
        value = review.get(field)
        if not _is_bounded_identifier(value):
            _append_take_error(
                errors,
                f"{label}: {field} must be a non-empty string of at most "
                f"{MAX_IDENTIFIER_CHARS} characters; got {_bounded(value)}",
                label,
            )

    source_status = review.get("source_status")
    if (
        not isinstance(source_status, str)
        or source_status not in TAKE_REVIEW_SOURCE_STATUSES
    ):
        _append_take_error(
            errors,
            f"{label}: invalid source_status {_bounded(source_status)}",
            label,
        )

    verdict = review.get("verdict")
    if not isinstance(verdict, str) or verdict not in VERDICT_CLIP_STATUS:
        _append_take_error(
            errors,
            f"{label}: invalid verdict {_bounded(verdict)}",
            label,
        )

    for field in sorted(TAKE_REVIEW_OBSERVED_STATE_FIELDS):
        value = review.get(field)
        if not isinstance(value, dict):
            _append_take_error(
                errors,
                f"{label}: {field} must be an object; got {_bounded(value)}",
                label,
            )

    for field in sorted(TAKE_REVIEW_STRING_ARRAY_FIELDS):
        value = review.get(field)
        if not isinstance(value, list):
            _append_take_error(
                errors,
                f"{label}: {field} must be an array of strings; got {_bounded(value)}",
                label,
            )
            continue
        for index, item in enumerate(value):
            if not isinstance(item, str):
                _append_take_error(
                    errors,
                    f"{label}: {field}[{index}] must be a string; got {_bounded(item)}",
                    label,
                )
                break

    for field in sorted(TAKE_REVIEW_ARRAY_FIELDS):
        value = review.get(field)
        if not isinstance(value, list):
            _append_take_error(
                errors,
                f"{label}: {field} must be an array; got {_bounded(value)}",
                label,
            )

    confidence = review.get("observation_confidence")
    if (
        not isinstance(confidence, str)
        or confidence not in TAKE_REVIEW_CONFIDENCE_LEVELS
    ):
        _append_take_error(
            errors,
            f"{label}: invalid observation_confidence {_bounded(confidence)}",
            label,
        )

    confirmation = review.get("requires_user_confirmation")
    if not isinstance(confirmation, bool):
        _append_take_error(
            errors,
            f"{label}: requires_user_confirmation must be a boolean; "
            f"got {_bounded(confirmation)}",
            label,
        )

    accepted_deviations = review.get("accepted_deviations")
    if verdict == "reject" and isinstance(accepted_deviations, list) and accepted_deviations:
        _append_take_error(
            errors,
            f"{label}: rejected take must not accept deviations",
            label,
        )
    return errors


def is_take_review_path(path: Path) -> bool:
    name = path.name
    return (
        "project-state" not in name
        and (name == "take-review.json" or name.endswith("-take-review.json"))
    )


def _file_identity(info: os.stat_result) -> tuple[int, int] | None:
    """Return a stable same-file identity, or None when the filesystem has none."""

    if not info.st_ino:
        return None
    return info.st_dev, info.st_ino


def _is_regular_non_link(info: os.stat_result) -> bool:
    """Reject links, Windows reparse points, devices, pipes, and sockets."""

    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not (file_attributes & reparse_flag)


def _read_bounded_take_review_bytes(descriptor: int) -> bytes:
    """Capture at most the authority-file limit plus one detection byte."""

    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = MAX_TAKE_REVIEW_BYTES + 1
    while remaining:
        chunk = os.read(descriptor, min(64 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _load_checked_take_review(
    path: Path,
    excluded_file_ids: set[tuple[int, int]],
) -> tuple[Literal["loaded", "excluded", "error"], object, int]:
    """Open one regular file safely and parse a bounded, stable byte snapshot."""

    try:
        path_before = path.lstat()
    except OSError as exc:
        return "error", f"cannot be read safely: {_safe_detail(str(exc))}", 0
    if not _is_regular_non_link(path_before):
        return "error", "must be a regular non-link file", 0
    identity_before = _file_identity(path_before)
    if identity_before is None:
        return "error", "cannot establish a stable file identity", 0

    flags = os.O_RDONLY
    for flag_name in (
        "O_BINARY",
        "O_CLOEXEC",
        "O_NOINHERIT",
        "O_NOFOLLOW",
        "O_NONBLOCK",
    ):
        flags |= getattr(os, flag_name, 0)

    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        return "error", f"cannot be opened safely: {_safe_detail(str(exc))}", 0

    captured_bytes = 0
    try:
        opened = os.fstat(descriptor)
        identity = _file_identity(opened)
        if not _is_regular_non_link(opened):
            return "error", "must be a regular non-link file", 0
        if identity is None:
            return "error", "cannot establish a stable file identity", 0
        if identity != identity_before:
            return "error", "changed while being opened", 0
        if identity in excluded_file_ids:
            return "excluded", None, 0
        if opened.st_size > MAX_TAKE_REVIEW_BYTES:
            return (
                "error",
                f"exceeds the {MAX_TAKE_REVIEW_BYTES}-byte take-review limit",
                0,
            )

        first_capture = _read_bounded_take_review_bytes(descriptor)
        captured_bytes = len(first_capture)
        if captured_bytes > MAX_TAKE_REVIEW_BYTES:
            return (
                "error",
                f"exceeds the {MAX_TAKE_REVIEW_BYTES}-byte take-review limit",
                captured_bytes,
            )
        between_captures = os.fstat(descriptor)
        second_capture = _read_bounded_take_review_bytes(descriptor)
        captured_bytes = max(captured_bytes, len(second_capture))
        if captured_bytes > MAX_TAKE_REVIEW_BYTES:
            return (
                "error",
                f"exceeds the {MAX_TAKE_REVIEW_BYTES}-byte take-review limit",
                captured_bytes,
            )
        after_capture = os.fstat(descriptor)
        path_after = path.lstat()

        observed = (opened, between_captures, after_capture, path_after)
        if any(not _is_regular_non_link(info) for info in observed):
            return (
                "error",
                "changed into a non-regular or linked file while being read",
                captured_bytes,
            )
        if any(_file_identity(info) != identity for info in observed):
            return "error", "changed identity while being read", captured_bytes
        if any(info.st_size != len(first_capture) for info in observed):
            return "error", "changed size while being read", captured_bytes
        if first_capture != second_capture:
            return "error", "changed contents while being read", captured_bytes
    except (OSError, ValueError) as exc:
        return (
            "error",
            f"cannot be read safely: {_safe_detail(str(exc))}",
            captured_bytes,
        )
    finally:
        os.close(descriptor)

    try:
        text = first_capture.decode("utf-8")
        return "loaded", loads_strict_json(text), captured_bytes
    except (UnicodeError, ValueError) as exc:
        return (
            "error",
            f"is invalid JSON: {_safe_detail(str(exc))}",
            captured_bytes,
        )


def load_bounded_take_review(path: Path) -> object:
    """Load one standalone review through the same bounded authority path."""

    status, payload, _ = _load_checked_take_review(path, set())
    if status != "loaded":
        detail = payload if isinstance(payload, str) else "cannot be loaded safely"
        raise ValueError(f"take-review {detail}")
    return payload


def build_take_review_index(
    directory: Path,
    *,
    excluded_project_paths: Iterable[Path] = (),
) -> TakeReviewIndex:
    """Load candidate sibling reviews once, excluding every project document.

    The hard file cap keeps an attacker-controlled directory from turning the
    semantic check into an unbounded scan. A directory over the cap is invalid;
    it never silently drops a review and reports success.
    """

    resolved_directory = directory.resolve()
    diagnostics: list[str] = []
    excluded_file_ids: set[tuple[int, int]] = set()
    for path in excluded_project_paths:
        try:
            with path.open("rb") as handle:
                identity = _file_identity(os.fstat(handle.fileno()))
        except OSError as exc:
            diagnostics.append(
                f"cannot identify project-state file "
                f"{safe_diagnostic_text(path.name, 120)}: {_safe_detail(str(exc))}"
            )
            continue
        if identity is None:
            diagnostics.append(
                f"cannot establish a stable identity for project-state file "
                f"{safe_diagnostic_text(path.name, 120)}"
            )
            continue
        excluded_file_ids.add(identity)

    candidates: list[Path] = []
    try:
        entries = resolved_directory.iterdir()
        for path in entries:
            if not is_take_review_path(path):
                continue
            candidates.append(path)
            if len(candidates) > MAX_TAKE_REVIEW_FILES_PER_DIRECTORY:
                diagnostics.append(
                    f"sibling take-review file count exceeds "
                    f"{MAX_TAKE_REVIEW_FILES_PER_DIRECTORY}"
                )
                candidates = candidates[:MAX_TAKE_REVIEW_FILES_PER_DIRECTORY]
                break
    except OSError as exc:
        diagnostics.append(
            f"cannot scan sibling take-review directory: {_safe_detail(str(exc))}"
        )

    records_by_key: dict[tuple[str, str, str], list[TakeReviewRecord]] = {}
    captured_review_bytes = 0
    for path in sorted(candidates, key=lambda candidate: candidate.name):
        load_status, payload, captured_bytes = _load_checked_take_review(
            path,
            excluded_file_ids,
        )
        if (
            captured_review_bytes + captured_bytes
            > MAX_TAKE_REVIEW_BYTES_PER_DIRECTORY
        ):
            diagnostics.append(
                f"sibling take-review bytes exceed the "
                f"{MAX_TAKE_REVIEW_BYTES_PER_DIRECTORY}-byte directory limit"
            )
            break
        captured_review_bytes += captured_bytes
        if load_status == "excluded":
            continue
        if load_status == "error":
            diagnostics.append(
                f"sibling {safe_diagnostic_text(path.name, 120)} {payload}"
            )
            continue
        review = payload

        label = f"sibling {safe_diagnostic_text(path.name, 120)}"
        review_errors = validate_take_review_record(review, label)
        if review_errors:
            for error in review_errors:
                _append_take_error(diagnostics, error, "sibling take-review index")
            continue

        assert isinstance(review, dict)
        project_id = review["project_id"]
        clip_id = review["clip_id"]
        take_id = review["take_id"]
        assert isinstance(project_id, str)
        assert isinstance(clip_id, str)
        assert isinstance(take_id, str)
        key = (project_id, clip_id, take_id)
        records = records_by_key.setdefault(key, [])
        if len(records) < MAX_REVIEWS_PER_TAKE_KEY:
            records.append(TakeReviewRecord(path=path, data=review))

    return TakeReviewIndex(
        directory=resolved_directory,
        records_by_key=records_by_key,
        diagnostics=tuple(
            bound_diagnostics(
                diagnostics,
                "additional sibling take-review index diagnostics omitted",
            )
        ),
    )


def build_take_review_indexes(project_paths: Iterable[Path]) -> dict[Path, TakeReviewIndex]:
    """Build one review index per project directory for an entire validator run."""

    excluded_by_directory: dict[Path, set[Path]] = {}
    for project_path in project_paths:
        resolved_path = project_path.resolve()
        excluded_by_directory.setdefault(resolved_path.parent, set()).add(resolved_path)
    return {
        directory: build_take_review_index(
            directory,
            excluded_project_paths=excluded_paths,
        )
        for directory, excluded_paths in sorted(
            excluded_by_directory.items(), key=lambda item: str(item[0])
        )
    }


def validate_take_reconciliation(
    data: dict,
    clips_by_id: dict[str, dict],
    rel: str,
    review_index: TakeReviewIndex,
) -> list[str]:
    """Bind current post-review clip state to one history entry and one review."""

    errors: list[str] = []
    for diagnostic in review_index.diagnostics:
        _append_take_error(errors, f"{rel}: {diagnostic}", rel)

    history = data.get("take_history")
    if not isinstance(history, list):
        _append_take_error(errors, f"{rel}: take_history must be an array", rel)
        history_entries: list[object] = []
    else:
        if len(history) > MAX_TAKE_HISTORY_ITEMS:
            _append_take_error(
                errors,
                f"{rel}: take_history must contain at most {MAX_TAKE_HISTORY_ITEMS} entries; "
                f"got {len(history)}",
                rel,
            )
        history_entries = history[:MAX_TAKE_HISTORY_ITEMS]

    latest_by_clip: dict[str, tuple[str, str]] = {}
    seen_keys: set[tuple[str, str]] = set()
    for index, entry in enumerate(history_entries):
        label = f"{rel}: take_history[{index}]"
        if not isinstance(entry, dict):
            _append_take_error(errors, f"{label} must be an object", rel)
            continue

        missing = sorted(TAKE_HISTORY_REQUIRED_FIELDS - set(entry))
        if missing:
            _append_take_error(
                errors,
                f"{label} missing fields: {', '.join(missing)}",
                rel,
            )
        unexpected = sorted(set(entry) - TAKE_HISTORY_ALLOWED_FIELDS)
        if unexpected:
            rendered_unexpected = ", ".join(
                _bounded(field, 64) for field in unexpected[:8]
            )
            if len(unexpected) > 8:
                rendered_unexpected += f", ... ({len(unexpected)} fields)"
            _append_take_error(
                errors,
                f"{label} has unexpected fields: {rendered_unexpected}",
                rel,
            )

        clip_id = entry.get("clip_id")
        take_id = entry.get("take_id")
        verdict = entry.get("verdict")
        valid_entry = True
        if not _is_bounded_identifier(clip_id):
            _append_take_error(
                errors,
                f"{label} clip_id must be a non-empty string of at most "
                f"{MAX_IDENTIFIER_CHARS} characters; got {_bounded(clip_id)}",
                rel,
            )
            valid_entry = False
        if not _is_bounded_identifier(take_id):
            _append_take_error(
                errors,
                f"{label} take_id must be a non-empty string of at most "
                f"{MAX_IDENTIFIER_CHARS} characters; got {_bounded(take_id)}",
                rel,
            )
            valid_entry = False
        if not isinstance(verdict, str) or verdict not in VERDICT_CLIP_STATUS:
            _append_take_error(
                errors,
                f"{label} has invalid verdict {_bounded(verdict)}",
                rel,
            )
            valid_entry = False
        evidence = entry.get("evidence")
        if "evidence" in entry and (
            not isinstance(evidence, str) or len(evidence) > MAX_TAKE_EVIDENCE_CHARS
        ):
            _append_take_error(
                errors,
                f"{label} evidence must be a string of at most "
                f"{MAX_TAKE_EVIDENCE_CHARS} characters",
                rel,
            )
            valid_entry = False
        if not valid_entry:
            continue

        assert isinstance(clip_id, str)
        assert isinstance(take_id, str)
        assert isinstance(verdict, str)
        key = (clip_id, take_id)
        if key in seen_keys:
            _append_take_error(
                errors,
                f"{label} duplicates take {_identifier(take_id)} for clip "
                f"{_identifier(clip_id)}",
                rel,
            )
            continue
        seen_keys.add(key)
        if clip_id not in clips_by_id:
            _append_take_error(
                errors,
                f"{label} refers to missing clip {_identifier(clip_id)}",
                rel,
            )
            continue
        latest_by_clip[clip_id] = (take_id, verdict)

    project_id = data.get("project_id")
    valid_project_id = _is_bounded_identifier(project_id)
    if not valid_project_id:
        _append_take_error(
            errors,
            f"{rel}: project_id must be a non-empty string of at most "
            f"{MAX_IDENTIFIER_CHARS} characters for take reconciliation; "
            f"got {_bounded(project_id)}",
            rel,
        )

    for clip_id, (take_id, verdict) in latest_by_clip.items():
        actual = clips_by_id[clip_id].get("status")
        if not (
            isinstance(actual, str) and actual in POST_REVIEW_CLIP_STATUSES
        ):
            continue
        matches: list[TakeReviewRecord] = []
        if valid_project_id:
            assert isinstance(project_id, str)
            matches = review_index.records_by_key.get((project_id, clip_id, take_id), [])
        if not matches:
            _append_take_error(
                errors,
                f"{rel}: latest take {_identifier(take_id)} for clip "
                f"{_identifier(clip_id)} is missing its sibling take-review record",
                rel,
            )
        elif len(matches) > 1:
            _append_take_error(
                errors,
                f"{rel}: latest take {_identifier(take_id)} for clip "
                f"{_identifier(clip_id)} has multiple sibling take-review records",
                rel,
            )
        else:
            review = matches[0].data
            review_label = (
                f"{rel}: sibling take-review for take {_identifier(take_id)}"
            )
            review_errors = validate_take_review_record(review, review_label)
            for review_error in review_errors:
                _append_take_error(errors, review_error, rel)
            review_verdict = review.get("verdict") if not review_errors else None
            if isinstance(review_verdict, str) and review_verdict != verdict:
                _append_take_error(
                    errors,
                    f"{rel}: take_history verdict {verdict} for take "
                    f"{_identifier(take_id)} does not match sibling take-review verdict "
                    f"{review_verdict}",
                    rel,
                )

        expected = VERDICT_CLIP_STATUS[verdict]
        if actual != expected:
            rendered_actual = (
                actual
                if isinstance(actual, str) and actual in ALL_CLIP_STATUSES
                else _bounded(actual)
            )
            _append_take_error(
                errors,
                f"{rel}: latest take {_identifier(take_id)} for clip "
                f"{_identifier(clip_id)} has verdict {verdict}; clip status must be "
                f"{expected}, not {rendered_actual}",
                rel,
            )

    for clip_id, clip in clips_by_id.items():
        status = clip.get("status")
        if (
            isinstance(status, str)
            and status in POST_REVIEW_CLIP_STATUSES
            and clip_id not in latest_by_clip
        ):
            _append_take_error(
                errors,
                f"{rel}: clip {_identifier(clip_id)} status {status} requires a current "
                "take_history entry and sibling take-review record",
                rel,
            )

    return errors


def load_project_document(path: Path, root: Path) -> tuple[dict | None, str, list[str]]:
    """Load one project document with bounded, non-throwing diagnostics."""

    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.name
    try:
        data = load_strict_json(path)
    except (OSError, UnicodeError, ValueError) as exc:
        return None, rel, [f"{rel}: invalid JSON: {_safe_detail(str(exc))}"]
    if not isinstance(data, dict):
        return None, rel, [f"{rel}: project state must be an object"]
    return data, rel, []


def has_usable_observed_end_state(clip: dict) -> bool:
    observed_end_state = clip.get("observed_end_state")
    return isinstance(observed_end_state, dict) and bool(observed_end_state)


def classify_parent_id(clip: dict) -> tuple[ParentIdKind, object | None]:
    """Distinguish a root from an invalid falsey parent identifier.

    Only an absent key or JSON null denotes a root. Empty, whitespace-only,
    and non-string values are invalid rather than silently becoming roots.
    """

    if "parent_clip_id" not in clip or clip["parent_clip_id"] is None:
        return "root", None
    parent_id = clip["parent_clip_id"]
    if not isinstance(parent_id, str) or not parent_id.strip():
        return "invalid", parent_id
    return "parent", parent_id


def parent_link_mode(child: dict, parent: dict) -> ParentLinkMode:
    """Return whether ``parent`` can back this child link.

    A generation-ready or later child can only descend from accepted footage
    with an observed endpoint. A still-planned child may retain a provisional
    graph edge to a planned/ready predecessor, but that edge is planning data,
    never generation authority. Pending-review, repair, and rejected footage
    are unusable in both modes.
    """

    parent_status = parent.get("status")
    if isinstance(parent_status, str) and parent_status in ACCEPTED_PARENT_STATUSES:
        if not has_usable_observed_end_state(parent):
            return "missing_observed_end_state"
        return "accepted"
    if (
        child.get("status") == "planned"
        and isinstance(parent_status, str)
        and parent_status in PROVISIONAL_PARENT_STATUSES
    ):
        return "provisional"
    return "unusable_status"


def json_integer(value: object) -> int | float | Decimal | None:
    """Match JSON Schema's integer type, including finite integral floats."""

    return strict_json_integer(value)


def _cycle_summary(path: list[str], start: int, closing_id: str) -> str:
    node_count = len(path) - start
    if node_count <= MAX_CYCLE_DISPLAY_NODES:
        nodes = path[start:] + [closing_id]
        return " -> ".join(_identifier(node) for node in nodes)
    head = path[start : start + 4]
    tail = path[-2:] + [closing_id]
    rendered = " -> ".join(_identifier(node) for node in head)
    rendered += " -> ... -> " + " -> ".join(_identifier(node) for node in tail)
    return f"{rendered} ({node_count} nodes)"


def analyze_lineage(clips_value: object, rel: str) -> LineageAnalysis:
    """Validate graph identity, roots, order, cycles, and parent usability."""

    errors: list[str] = []
    if not isinstance(clips_value, list):
        return LineageAnalysis(
            clips=[],
            clips_by_id={},
            accepted_links=[],
            provisional_links=[],
            errors=[f"{rel}: clips must be an array of clip objects"],
        )

    clips: list[dict] = []
    clips_by_id: dict[str, dict] = {}
    sequence_by_id: dict[str, int | float | Decimal | None] = {}
    unique_clips: list[tuple[str, dict]] = []

    for index, clip in enumerate(clips_value):
        if not isinstance(clip, dict):
            _append_error(errors, f"{rel}: clips[{index}] must be an object", rel)
            continue
        clips.append(clip)
        clip_id = clip.get("clip_id")
        if not isinstance(clip_id, str) or not clip_id.strip():
            _append_error(
                errors,
                f"{rel}: clips[{index}] clip_id must be a non-empty string",
                rel,
            )
            continue
        if len(clip_id) > MAX_IDENTIFIER_CHARS:
            _append_error(
                errors,
                f"{rel}: clips[{index}] clip_id must be at most {MAX_IDENTIFIER_CHARS} characters; "
                f"got {_identifier(clip_id)}",
                rel,
            )
            continue
        sequence_index = json_integer(clip.get("sequence_index"))
        if sequence_index is None or sequence_index < 1:
            _append_error(
                errors,
                f"{rel}: clip {_identifier(clip_id)} sequence_index must be a JSON integer >= 1",
                rel,
            )
        if clip_id in clips_by_id:
            _append_error(errors, f"{rel}: duplicate clip_id {_identifier(clip_id)}", rel)
            continue
        clips_by_id[clip_id] = clip
        sequence_by_id[clip_id] = sequence_index
        unique_clips.append((clip_id, clip))

        status = clip.get("status")
        if not isinstance(status, str) or status not in ALL_CLIP_STATUSES:
            _append_error(
                errors,
                f"{rel}: clip {_identifier(clip_id)} status {_bounded(status)} is invalid",
                rel,
            )
        elif status in ACCEPTED_PARENT_STATUSES and not has_usable_observed_end_state(clip):
            _append_error(
                errors,
                f"{rel}: accepted clip {_identifier(clip_id)} observed_end_state "
                "must be a non-empty object",
                rel,
            )
        elif status == "rejected" and (
            "observed_end_state" not in clip or clip["observed_end_state"] is not None
        ):
            _append_error(
                errors,
                f"{rel}: rejected clip {_identifier(clip_id)} observed_end_state must be null",
                rel,
            )

    parent_by_id: dict[str, str | None] = {}
    accepted_links: list[tuple[dict, dict]] = []
    provisional_links: list[tuple[dict, dict]] = []

    for clip_id, clip in unique_clips:
        sequence_index = sequence_by_id[clip_id]
        parent_kind, parent_id = classify_parent_id(clip)
        if parent_kind == "root":
            parent_by_id[clip_id] = None
            if sequence_index is not None and sequence_index != 1:
                _append_error(
                    errors,
                    f"{rel}: later clip {_identifier(clip_id)} sequence_index "
                    f"{_bounded(clip.get('sequence_index'))} "
                    "must declare a non-empty parent_clip_id",
                    rel,
                )
            continue
        if parent_kind == "invalid":
            _append_error(
                errors,
                f"{rel}: clip {_identifier(clip_id)} parent_clip_id must be null or a non-empty string",
                rel,
            )
            continue

        assert isinstance(parent_id, str)
        if len(parent_id) > MAX_IDENTIFIER_CHARS:
            _append_error(
                errors,
                f"{rel}: clip {_identifier(clip_id)} parent_clip_id must be at most "
                f"{MAX_IDENTIFIER_CHARS} characters; got {_identifier(parent_id)}",
                rel,
            )
            continue
        parent_by_id[clip_id] = parent_id
        if parent_id == clip_id:
            _append_error(
                errors,
                f"{rel}: clip {_identifier(clip_id)} cannot parent itself",
                rel,
            )
            continue
        parent = clips_by_id.get(parent_id)
        if parent is None:
            _append_error(
                errors,
                f"{rel}: clip {_identifier(clip_id)} parent {_identifier(parent_id)} is missing",
                rel,
            )
            continue

        parent_index = sequence_by_id.get(parent_id)
        if (
            sequence_index is not None
            and parent_index is not None
            and parent_index >= sequence_index
        ):
            _append_error(
                errors,
                f"{rel}: clip {_identifier(clip_id)} sequence_index "
                f"{_bounded(clip.get('sequence_index'))} must be greater than parent "
                f"{_identifier(parent_id)} sequence_index "
                f"{_bounded(parent.get('sequence_index'))}",
                rel,
            )

        link_mode = parent_link_mode(clip, parent)
        if link_mode == "accepted":
            accepted_links.append((clip, parent))
        elif link_mode == "provisional":
            provisional_links.append((clip, parent))
        elif link_mode == "missing_observed_end_state":
            _append_error(
                errors,
                f"{rel}: clip {_identifier(clip_id)} parent {_identifier(parent_id)} is accepted "
                "but missing a usable observed_end_state",
                rel,
            )
        else:
            _append_error(
                errors,
                f"{rel}: clip {_identifier(clip_id)} parent {_identifier(parent_id)} status "
                f"{_bounded(parent.get('status'))} is not usable",
                rel,
            )

    state: dict[str, int] = {clip_id: 0 for clip_id in clips_by_id}
    for start_id in clips_by_id:
        if state[start_id] != 0:
            continue
        path: list[str] = []
        positions: dict[str, int] = {}
        clip_id: str | None = start_id
        while clip_id is not None and clip_id in clips_by_id and state[clip_id] == 0:
            state[clip_id] = 1
            positions[clip_id] = len(path)
            path.append(clip_id)
            parent_id = parent_by_id.get(clip_id)
            clip_id = parent_id if parent_id != clip_id else None
        if clip_id is not None and clip_id in positions:
            _append_error(
                errors,
                f"{rel}: clip lineage cycle: "
                f"{_cycle_summary(path, positions[clip_id], clip_id)}",
                rel,
            )
        for visited_id in path:
            state[visited_id] = 2

    return LineageAnalysis(
        clips=clips,
        clips_by_id=clips_by_id,
        accepted_links=accepted_links,
        provisional_links=provisional_links,
        errors=errors,
    )

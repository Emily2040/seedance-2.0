"""Shared project-lineage rules for every state consumer."""

from __future__ import annotations

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
AUTHORITATIVE_TAKE_REVIEW_FIELDS = frozenset(
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


def _is_take_review_path(path: Path) -> bool:
    name = path.name
    return (
        "project-state" not in name
        and (name == "take-review.json" or name.endswith("-take-review.json"))
    )


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
    excluded = {path.resolve() for path in excluded_project_paths}
    excluded_file_ids: set[tuple[int, int]] = set()
    for path in excluded:
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_ino:
            excluded_file_ids.add((stat.st_dev, stat.st_ino))
    candidates: list[Path] = []
    diagnostics: list[str] = []
    try:
        entries = resolved_directory.iterdir()
        for path in entries:
            if not _is_take_review_path(path) or path.resolve() in excluded:
                continue
            try:
                stat = path.stat()
            except OSError:
                stat = None
            if (
                stat is not None
                and stat.st_ino
                and (stat.st_dev, stat.st_ino) in excluded_file_ids
            ):
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
    for path in sorted(candidates, key=lambda candidate: candidate.name):
        try:
            review = load_strict_json(path)
        except (OSError, UnicodeError, ValueError) as exc:
            diagnostics.append(
                f"sibling {safe_diagnostic_text(path.name, 120)} is invalid JSON: "
                f"{_safe_detail(str(exc))}"
            )
            continue
        if not isinstance(review, dict):
            diagnostics.append(
                f"sibling {safe_diagnostic_text(path.name, 120)} take-review must be an object"
            )
            continue

        key_values = tuple(review.get(field) for field in ("project_id", "clip_id", "take_id"))
        invalid_fields = [
            field
            for field, value in zip(("project_id", "clip_id", "take_id"), key_values)
            if not _is_bounded_identifier(value)
        ]
        if invalid_fields:
            diagnostics.append(
                f"sibling {safe_diagnostic_text(path.name, 120)} take-review has invalid "
                f"identity fields: {', '.join(invalid_fields)}"
            )
            continue

        project_id, clip_id, take_id = key_values
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
            missing_review_fields = sorted(AUTHORITATIVE_TAKE_REVIEW_FIELDS - set(review))
            if missing_review_fields:
                _append_take_error(
                    errors,
                    f"{rel}: sibling take-review for take {_identifier(take_id)} is not "
                    f"authoritative; missing fields: {', '.join(missing_review_fields)}",
                    rel,
                )
            source_status = review.get("source_status")
            if not isinstance(source_status, str) or source_status not in TAKE_REVIEW_SOURCE_STATUSES:
                _append_take_error(
                    errors,
                    f"{rel}: sibling take-review for take {_identifier(take_id)} has invalid "
                    f"source_status {_bounded(source_status)}",
                    rel,
                )
            review_verdict = review.get("verdict")
            if not isinstance(review_verdict, str) or review_verdict not in VERDICT_CLIP_STATUS:
                _append_take_error(
                    errors,
                    f"{rel}: sibling take-review for take {_identifier(take_id)} has invalid "
                    f"verdict {_bounded(review_verdict)}",
                    rel,
                )
            elif review_verdict != verdict:
                _append_take_error(
                    errors,
                    f"{rel}: take_history verdict {verdict} for take "
                    f"{_identifier(take_id)} does not match sibling take-review verdict "
                    f"{review_verdict}",
                    rel,
                )

        actual = clips_by_id[clip_id].get("status")
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

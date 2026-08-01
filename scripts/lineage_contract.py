"""Shared project-lineage rules for every state consumer."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal

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

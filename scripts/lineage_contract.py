"""Shared parent-link rules for project and continuity validation."""

from __future__ import annotations

from typing import Literal


ACCEPTED_PARENT_STATUSES = frozenset({"accepted", "accepted_with_deviation"})
PROVISIONAL_PARENT_STATUSES = frozenset({"planned", "ready"})

ParentIdKind = Literal["root", "invalid", "parent"]
ParentLinkMode = Literal[
    "accepted",
    "provisional",
    "missing_observed_end_state",
    "unusable_status",
]


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
    if parent_status in ACCEPTED_PARENT_STATUSES:
        if not has_usable_observed_end_state(parent):
            return "missing_observed_end_state"
        return "accepted"
    if child.get("status") == "planned" and parent_status in PROVISIONAL_PARENT_STATUSES:
        return "provisional"
    return "unusable_status"

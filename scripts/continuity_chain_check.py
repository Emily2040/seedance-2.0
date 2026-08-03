#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path

if __package__:
    from .lineage_contract import (
        analyze_lineage,
        build_take_review_indexes,
        bound_validation_diagnostics,
        load_project_document,
        TakeReviewIndex,
        validate_take_reconciliation,
    )
    from .strict_json import (
        bound_diagnostics,
        diagnostic_path,
        diagnostic_text,
        validate_repo_input_path,
    )
else:
    from lineage_contract import (
        analyze_lineage,
        build_take_review_indexes,
        bound_validation_diagnostics,
        load_project_document,
        TakeReviewIndex,
        validate_take_reconciliation,
    )
    from strict_json import (
        bound_diagnostics,
        diagnostic_path,
        diagnostic_text,
        validate_repo_input_path,
    )


IdentityToken = tuple[str, str | int]
ListIdentity = tuple[str, str, str | int]
IdentityAliases = dict[str, set[IdentityToken]]
FieldSpan = tuple[int, int, str]
MISSING = object()


IMMUTABLE_KEYS = [
    "canonical_identity_id",
    "wardrobe",
    "product_identity",
    "prop_owner",
    "location",
    "vehicle_identity",
    "persistent_environment",
    "reference_tags",
]
TRANSIENT_KEYS = [
    "pose",
    "position_in_frame",
    "travel_direction",
    "motion_vector",
    "camera_phase",
    "focus_state",
    "lighting_phase",
    "emotional_state",
    "audio_phase",
]
TRACKED_KEYS = frozenset(IMMUTABLE_KEYS) | frozenset(TRANSIENT_KEYS)

FIELD_ALIASES = {
    "canonical_identity_id": ("canonical identity", "character identity"),
    "product_identity": ("product identity",),
    "prop_owner": ("prop owner", "prop ownership"),
    "vehicle_identity": ("vehicle identity",),
    "persistent_environment": ("persistent environment",),
    "reference_tags": ("reference tag", "reference tags"),
    "position_in_frame": ("position in frame",),
    "travel_direction": ("travel direction", "screen direction"),
    "motion_vector": ("motion vector",),
    "camera_phase": ("camera phase",),
    "focus_state": ("focus state",),
    "lighting_phase": ("lighting phase",),
    "emotional_state": ("emotional state",),
    "audio_phase": ("audio phase",),
}

TRANSITION_CHANGE_WORDS = {
    "allow",
    "allowed",
    "allows",
    "alter",
    "altered",
    "break",
    "can",
    "change",
    "changed",
    "changes",
    "changing",
    "deviation",
    "different",
    "drift",
    "drifted",
    "drifts",
    "may",
    "mismatch",
    "mismatched",
    "new",
    "permit",
    "permitted",
    "replace",
    "replaced",
    "replacement",
    "reset",
    "shift",
    "swap",
    "swapped",
    "switch",
    "variation",
}
NEGATION_WORDS = {
    "avoid",
    "avoided",
    "avoids",
    "ban",
    "banned",
    "bar",
    "barred",
    "block",
    "blocked",
    "cannot",
    "denied",
    "deny",
    "disallow",
    "disallowed",
    "forbid",
    "forbidden",
    "never",
    "no",
    "not",
    "prevent",
    "prevented",
    "prohibit",
    "prohibited",
    "refuse",
    "refused",
    "without",
}
NEGATING_CONTRACTION_STEMS = {
    "aren",
    "can",
    "couldn",
    "didn",
    "doesn",
    "don",
    "isn",
    "mustn",
    "shouldn",
    "wasn",
    "weren",
    "won",
    "wouldn",
}
PRESERVATION_WORDS = {
    "constant",
    "fixed",
    "intact",
    "identical",
    "keep",
    "keeps",
    "lock",
    "locked",
    "maintain",
    "maintains",
    "match",
    "matches",
    "matching",
    "preserve",
    "preserved",
    "preserves",
    "retain",
    "retained",
    "retains",
    "remain",
    "remains",
    "same",
    "stay",
    "stays",
    "unchanged",
}
GLOBAL_WAIVER_GRAMMAR = {
    "a",
    "all",
    "an",
    "are",
    "be",
    "being",
    "explicit",
    "explicitly",
    "global",
    "globally",
    "intentional",
    "intentionally",
    "is",
    "must",
    "of",
    "or",
    "the",
    "this",
    "to",
    "will",
}
GENERIC_IDENTITY_PATH_WORDS = {
    "character",
    "characters",
    "data",
    "entry",
    "item",
    "record",
    "records",
    "slot",
    "slots",
    "state",
    "value",
}
FIELD_COORDINATORS = {"a", "an", "and", "or", "the"}
HARD_CLAUSE_CONNECTORS = {"whereas", "while"}
QUALIFIER_MODIFIERS = {"exclusively", "only", "specifically"}
AXIS_RESET_SHOT_QUALIFIERS = {
    ("for", "reverse", "angle"),
    ("for", "the", "reverse", "angle"),
}
WAIVER_CONTEXT_WORDS = {
    "after",
    "also",
    "alternatively",
    "approved",
    "as",
    "before",
    "cut",
    "deliberately",
    "during",
    "following",
    "indirectly",
    "jump",
    "next",
    "restriction",
    "scene",
    "sequence",
    "shot",
    "time",
    "transition",
    "when",
    "well",
}
WAIVER_PREDICATE_WORDS = (
    TRANSITION_CHANGE_WORDS
    | NEGATION_WORDS
    | PRESERVATION_WORDS
    | NEGATING_CONTRACTION_STEMS
    | GLOBAL_WAIVER_GRAMMAR
    | FIELD_COORDINATORS
    | WAIVER_CONTEXT_WORDS
    | {"altering", "t"}
)
TEMPORAL_CONTEXT_LEADERS = {"after", "before", "during", "following"}
TEMPORAL_CONTEXT_NOUNS = {"cut", "jump", "scene", "sequence", "shot", "transition"}
ENTITY_LIST_CONNECTORS = {"and", "or"}

# A coordinated field list has no predicate before its coordinator (for
# example, ``wardrobe and product identity may change``). Conversely, a word
# here before ``and``/``or`` proves the preceding field already has its own
# predicate and begins a new field clause: ``wardrobe is fixed and canonical
# identity may change``.
CLAUSE_PREDICATE_WORDS = (
    (TRANSITION_CHANGE_WORDS - {"change", "changed", "changes", "changing"})
    | NEGATION_WORDS
    | PRESERVATION_WORDS
    | NEGATING_CONTRACTION_STEMS
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_phrase(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))


def field_phrases(key: str) -> set[str]:
    phrases = {normalize_phrase(key)}
    phrases.update(normalize_phrase(alias) for alias in FIELD_ALIASES.get(key, ()))
    return phrases


def mentions_field(text: str, key: str) -> bool:
    padded = f" {normalize_phrase(text)} "
    return any(f" {phrase} " in padded for phrase in field_phrases(key))


def is_scope_fragment(text: object) -> bool:
    """Return whether a fieldless fragment has explicit scoping grammar."""
    tokens = normalize_phrase(text).split()
    return bool(tokens) and not field_groups(tokens) and bool(
        set(tokens) & QUALIFIER_MODIFIERS
        or tokens[0] in {"for", "of"}
    )


def has_completed_field_predicate(text: str) -> bool:
    """Return whether a comma-left field fragment already has a predicate.

    A comma after a completed field clause is a clause boundary. A comma before
    the one shared predicate in ``wardrobe, location, and product identity must
    not change`` is a list coordinator. Looking for predicate vocabulary only
    outside recognized field spans keeps field names from deciding this split.
    """
    tokens = normalize_phrase(text).split()
    groups = field_groups(tokens)
    if not groups:
        return False
    occupied = {
        index
        for group in groups
        for start, end, _candidate in group
        for index in range(start, end)
    }
    predicate_words = (
        TRANSITION_CHANGE_WORDS
        | NEGATION_WORDS
        | PRESERVATION_WORDS
        | NEGATING_CONTRACTION_STEMS
    )
    return any(
        index not in occupied and token in predicate_words
        for index, token in enumerate(tokens)
    )


def split_comma_clauses(text: str) -> list[str]:
    """Split comma clauses while retaining comma-coordinated field lists.

    ``normalize_phrase`` deliberately drops punctuation, so list commas are
    converted to an explicit coordinator before semantic tokenization. This
    preserves every item in both Oxford- and non-Oxford-comma lists without
    merging independent clauses that already carry their own predicate.
    """
    parts = text.split(",")
    if len(parts) == 1:
        stripped = text.strip()
        return [stripped] if normalize_phrase(stripped) else []

    clauses: list[str] = []
    current = parts[0].strip()
    for part_index, raw_part in enumerate(parts[1:], start=1):
        right = raw_part.strip()
        if not normalize_phrase(right):
            continue
        remainder = ",".join(parts[part_index:])
        right_starts_connector = bool(
            re.match(r"^(?:and|or|as\s+well\s+as)\b", right, flags=re.IGNORECASE)
        )
        current_has_field = bool(field_groups(normalize_phrase(current).split()))
        remainder_groups = field_groups(normalize_phrase(remainder).split())
        remainder_field_count = sum(len(group) for group in remainder_groups)
        remainder_has_connector = bool(
            re.search(
                r"\b(?:and|or|as\s+well\s+as)\b",
                remainder,
                flags=re.IGNORECASE,
            )
        )
        shared_field_list = (
            current_has_field
            and not has_completed_field_predicate(current)
            and remainder_field_count >= 2
            and remainder_has_connector
        )
        if right_starts_connector:
            current = f"{current} {right}".strip()
        elif shared_field_list:
            current = f"{current} and {right}".strip()
        else:
            if normalize_phrase(current):
                clauses.append(current)
            current = right
    if normalize_phrase(current):
        clauses.append(current)
    return clauses


def text_segments(text: object) -> list[str]:
    """Split independent clauses while preserving attached scope fragments.

    Splitting first, then attaching a qualifier avoids regex backtracking at a
    combined boundary such as ``.\nOnly for hero``. A leading qualifier belongs
    to the following field clause; a later qualifier belongs to the preceding
    one. Unknown names remain attached when they carry explicit scope grammar,
    so bounded parsing can reject rather than discard them.
    """
    # Normalize compatibility punctuation before splitting so fullwidth ASCII
    # forms follow exactly the same grammar. U+3002 is not compatibility-mapped
    # by NFKC, so it remains an explicit sentence boundary below.
    normalized_text = unicodedata.normalize("NFKC", str(text))
    hard_segments = re.split(
        r"(?:[.;:!?\r\n\u3002\u2013\u2014]+|\bbut\b|\bhowever\b)",
        normalized_text,
        flags=re.IGNORECASE,
    )
    raw_segments = [
        segment
        for hard_segment in hard_segments
        for segment in split_comma_clauses(hard_segment)
        if normalize_phrase(segment)
    ]
    segments: list[str] = []
    leading_scope: list[str] = []
    for segment in raw_segments:
        if is_scope_fragment(segment):
            if segments:
                segments[-1] = f"{segments[-1]} {segment}"
            else:
                leading_scope.append(segment)
            continue
        if leading_scope:
            segment = " ".join((*leading_scope, segment))
            leading_scope.clear()
        segments.append(segment)
    if leading_scope:
        # A qualifier with no field clause cannot grant a waiver. Keeping it as
        # its own segment lets whole-entry validation fail closed.
        segments.append(" ".join(leading_scope))
    return segments


def field_groups(tokens: list[str]) -> list[list[FieldSpan]]:
    """Return mentioned continuity fields, preserving coordinated field lists."""
    mentions: set[FieldSpan] = set()
    for candidate in TRACKED_KEYS:
        phrases = field_phrases(candidate)
        if candidate == "travel_direction":
            phrases = phrases | {"axis reset"}
        for phrase in phrases:
            phrase_tokens = phrase.split()
            width = len(phrase_tokens)
            for index in range(len(tokens) - width + 1):
                if tokens[index : index + width] == phrase_tokens:
                    mentions.add((index, index + width, candidate))

    ordered = sorted(mentions, key=lambda item: (item[0], -(item[1] - item[0]), item[2]))
    groups: list[list[FieldSpan]] = []
    occupied_until = -1
    for mention in ordered:
        start, end, _candidate = mention
        if start < occupied_until:
            continue
        if groups:
            between = tokens[groups[-1][-1][1] : start]
            if between and set(between) <= FIELD_COORDINATORS:
                groups[-1].append(mention)
                occupied_until = end
                continue
        groups.append([mention])
        occupied_until = end
    return groups


def semantic_token_clauses(text: object) -> list[list[str]]:
    """Split prose where distinct field predicates cannot share polarity.

    Punctuation and contrast conjunctions are hard boundaries. ``while`` and
    ``whereas`` also separate predicates even when one side has no action word.
    ``and``/``or`` split only after a completed predicate, preserving natural
    coordinated field lists such as ``wardrobe and product identity may
    change``.
    """
    clauses: list[list[str]] = []
    for segment in text_segments(text):
        tokens = normalize_phrase(segment).split()
        if not tokens:
            continue
        groups = field_groups(tokens)
        mentions = [mention for group in groups for mention in group]
        boundaries = {
            index
            for index, token in enumerate(tokens)
            if token in HARD_CLAUSE_CONNECTORS
        }
        for index, token in enumerate(tokens):
            if token not in {"and", "or"}:
                continue
            clause_start = max(
                (boundary + 1 for boundary in boundaries if boundary < index),
                default=0,
            )
            clause_end = min(
                (boundary for boundary in boundaries if boundary > index),
                default=len(tokens),
            )
            fields_before = [
                mention for mention in mentions if clause_start <= mention[0] and mention[1] <= index
            ]
            fields_after = [
                mention for mention in mentions if index < mention[0] < clause_end
            ]
            if not fields_before or not fields_after:
                continue
            next_field_start = min(mention[0] for mention in fields_after)
            if not set(tokens[index + 1 : next_field_start]) <= FIELD_COORDINATORS:
                continue
            if set(tokens[clause_start:index]) & CLAUSE_PREDICATE_WORDS:
                boundaries.add(index)

        start = 0
        for boundary in sorted(boundaries):
            if tokens[start:boundary]:
                clauses.append(tokens[start:boundary])
            start = boundary + 1
        if tokens[start:]:
            clauses.append(tokens[start:])
    return clauses


def event_distance(index: int, group: list[FieldSpan]) -> int:
    start = group[0][0]
    end = group[-1][1]
    if index < start:
        return start - index
    if index >= end:
        return index - end + 1
    return 0


def bound_field_group(
    index: int,
    groups: list[list[FieldSpan]],
    *,
    prefer_forward: bool = False,
) -> list[FieldSpan] | None:
    """Bind one lexical event to one local field group.

    Ordinary predicate words attach backward on a distance tie. The subordinate
    negator ``without`` attaches forward (``without altering identity``). This
    avoids making a denial at the end of one clause also negate the next field.
    """
    if not groups:
        return None
    if prefer_forward:
        forward = [group for group in groups if group[0][0] > index]
        if forward:
            return min(forward, key=lambda group: group[0][0])
        return None
    nearest_distance = min(event_distance(index, group) for group in groups)
    nearest = [group for group in groups if event_distance(index, group) == nearest_distance]
    if len(nearest) == 1:
        return nearest[0]
    backward = [group for group in nearest if group[-1][1] <= index]
    if backward:
        return max(backward, key=lambda group: group[-1][1])
    return min(nearest, key=lambda group: group[0][0])


def groups_share_predicate(
    left: list[FieldSpan],
    right: list[FieldSpan],
    tokens: list[str],
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> bool:
    """Recognize a coordinated entity/field list before its shared predicate."""
    start = left[-1][1]
    end = right[0][0]
    identity_spans, _ambiguous = identity_token_spans(
        tokens,
        identity_aliases,
        alias_widths,
    )
    identity_indexes = {
        index
        for span_start, span_end, _identities in identity_spans
        for index in range(span_start, span_end)
        if start <= index < end
    }
    between = [
        token
        for index, token in enumerate(tokens[start:end], start=start)
        if index not in identity_indexes and token not in {"s", "the"}
    ]
    has_connector = (
        bool(set(between) & ENTITY_LIST_CONNECTORS)
        or any(
            between[index : index + 3] == ["as", "well", "as"]
            for index in range(max(0, len(between) - 2))
        )
    )
    # Unknown words around an explicit coordinator are treated as unresolved
    # entity labels, not as permission to bind the predicate only to the last
    # field. A real intervening predicate still ends the coordination chain.
    return has_connector and not bool(set(between) & CLAUSE_PREDICATE_WORDS)


def coordinated_field_cluster(
    group: list[FieldSpan],
    groups: list[list[FieldSpan]],
    tokens: list[str],
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> list[list[FieldSpan]]:
    """Expand one bound group across an explicit coordinated field list."""
    index = groups.index(group)
    first = index
    last = index
    while first > 0 and groups_share_predicate(
        groups[first - 1],
        groups[first],
        tokens,
        identity_aliases,
        alias_widths,
    ):
        first -= 1
    while last + 1 < len(groups) and groups_share_predicate(
        groups[last],
        groups[last + 1],
        tokens,
        identity_aliases,
        alias_widths,
    ):
        last += 1
    return groups[first : last + 1]


def clause_field_polarities(
    tokens: list[str],
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> tuple[
    list[list[FieldSpan]],
    set[tuple[FieldSpan, ...]],
    set[tuple[FieldSpan, ...]],
]:
    """Bind affirmative and preservation events to their local field groups."""
    groups = field_groups(tokens)
    positive_groups: set[tuple[FieldSpan, ...]] = set()
    denied_groups: set[tuple[FieldSpan, ...]] = set()
    for index, token in enumerate(tokens):
        if token in TRANSITION_CHANGE_WORDS:
            group = bound_field_group(index, groups)
            if group is not None:
                positive_groups.update(
                    tuple(member)
                    for member in coordinated_field_cluster(
                        group,
                        groups,
                        tokens,
                        identity_aliases,
                        alias_widths,
                    )
                )
        if token in NEGATION_WORDS:
            group = bound_field_group(
                index,
                groups,
                prefer_forward=token == "without",
            )
            if group is not None:
                denied_groups.update(
                    tuple(member)
                    for member in coordinated_field_cluster(
                        group,
                        groups,
                        tokens,
                        identity_aliases,
                        alias_widths,
                    )
                )
        if token in PRESERVATION_WORDS:
            group = bound_field_group(index, groups)
            if group is not None and event_distance(index, group) <= 4:
                denied_groups.update(
                    tuple(member)
                    for member in coordinated_field_cluster(
                        group,
                        groups,
                        tokens,
                        identity_aliases,
                        alias_widths,
                    )
                )

    for index, (left, right) in enumerate(zip(tokens, tokens[1:])):
        if left not in NEGATING_CONTRACTION_STEMS or right != "t":
            continue
        group = bound_field_group(index, groups)
        if group is not None:
            denied_groups.update(
                tuple(member)
                for member in coordinated_field_cluster(
                    group,
                    groups,
                    tokens,
                    identity_aliases,
                    alias_widths,
                )
            )
    return groups, positive_groups, denied_groups


def anaphorically_denies_change(tokens: list[str]) -> bool:
    """Recognize a fieldless preservation tail without treating prose as NLP."""
    token_set = set(tokens)
    if token_set & PRESERVATION_WORDS:
        return True
    if any(
        left in NEGATING_CONTRACTION_STEMS and right == "t"
        for left, right in zip(tokens, tokens[1:])
    ):
        return True
    return bool(token_set & NEGATION_WORDS and token_set & TRANSITION_CHANGE_WORDS)


def analyze_field_entry(
    text: object,
    key: str,
    *,
    allow_bare: bool,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> tuple[list[str], list[str], bool]:
    """Return positive clauses, scoped denial contexts, and unsafe structure.

    Polarity is aggregated across the whole entry. A fieldless denial inherits
    the immediately preceding field group, so punctuation cannot turn
    ``wardrobe may change; must remain unchanged`` into a waiver. Other
    fieldless residual clauses are unsafe: dropping one could silently promote
    a scoped or qualified statement to a global allowance.
    """
    positive: list[str] = []
    denials: list[str] = []
    unsafe = False
    previous_fields: set[str] = set()
    previous_context = ""
    entry_mentions_key = mentions_field(str(text), key)
    for tokens in semantic_token_clauses(text):
        groups, positive_groups, denied_groups = clause_field_polarities(
            tokens,
            identity_aliases,
            alias_widths,
        )
        if not groups:
            inherited_denial = (
                key in previous_fields and anaphorically_denies_change(tokens)
            )
            if inherited_denial:
                # The omitted field and entity both inherit from the preceding
                # clause: ``hero wardrobe may change; must remain unchanged``.
                denials.append(previous_context)
            if entry_mentions_key and not inherited_denial:
                unsafe = True
            continue

        current_context = " ".join(tokens)
        current_fields = {
            candidate
            for group in groups
            for _start, _end, candidate in group
        }
        previous_fields = current_fields
        previous_context = current_context
        for group in groups:
            group_token = tuple(group)
            group_keys = {candidate for _start, _end, candidate in group}
            if key not in group_keys:
                continue
            if group_token in denied_groups:
                denials.append(current_context)
            bare_group = allow_bare and current_context in field_phrases(key)
            if (
                group_token not in denied_groups
                and (group_token in positive_groups or bare_group)
            ):
                positive.append(current_context)
    return positive, denials, unsafe


def identity_token_spans(
    tokens: list[str],
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None = None,
) -> tuple[list[tuple[int, int, set[IdentityToken]]], bool]:
    candidates: list[tuple[int, int, str, set[IdentityToken]]] = []
    widths = alias_widths
    if widths is None:
        widths = tuple(
            sorted(
                {len(phrase.split()) for phrase in identity_aliases if phrase},
                reverse=True,
            )
        )
    for width in widths:
        if not width or width > len(tokens):
            continue
        for index in range(len(tokens) - width + 1):
            phrase = " ".join(tokens[index : index + width])
            identities = identity_aliases.get(phrase)
            if identities:
                candidates.append((index, index + width, phrase, identities))

    # Resolve overlapping aliases by longest span first. This keeps an ID such
    # as "hero" from also matching inside the distinct ID "super hero".
    candidates.sort(key=lambda item: (-(item[1] - item[0]), item[0], item[2]))
    occupied: set[int] = set()
    selected: list[tuple[int, int, set[IdentityToken]]] = []
    ambiguous = False
    for start, end, _phrase, identities in candidates:
        span = set(range(start, end))
        if occupied & span:
            continue
        occupied.update(span)
        if len(identities) > 1:
            ambiguous = True
        selected.append((start, end, identities))
    return selected, ambiguous


def is_temporal_identity_span(
    tokens: list[str],
    start: int,
    end: int,
) -> bool:
    before = tokens[max(0, start - 2) : start]
    noun_index = end + 1 if end < len(tokens) and tokens[end] == "s" else end
    after = tokens[noun_index : noun_index + 1]
    has_leader = bool(before) and (
        before[-1] in TEMPORAL_CONTEXT_LEADERS
        or (
            len(before) == 2
            and before[0] in TEMPORAL_CONTEXT_LEADERS
            and before[1] == "the"
        )
    )
    return has_leader and bool(after) and after[0] in TEMPORAL_CONTEXT_NOUNS


def identity_span_attaches_to_group(
    tokens: list[str],
    span: tuple[int, int, set[IdentityToken]],
    group: list[FieldSpan],
    identity_indexes: set[int],
) -> bool:
    start, end, _identities = span
    field_start = group[0][0]
    field_end = group[-1][1]
    if is_temporal_identity_span(tokens, start, end):
        return False

    prefix_tokens = [
        token
        for index, token in enumerate(tokens[start:field_start], start=start)
        if index not in identity_indexes
    ]
    if end <= field_start and set(prefix_tokens) <= {
        "and",
        "as",
        "exclusively",
        "for",
        "of",
        "only",
        "or",
        "s",
        "specifically",
        "the",
        "well",
    }:
        return True

    if start < field_end:
        return False
    between = tokens[field_end:start]
    for marker_index in range(field_end, start):
        marker = tokens[marker_index]
        if marker not in {
            "exclusively",
            "for",
            "of",
            "only",
            "specifically",
        }:
            continue
        if (
            marker != "for"
            and set(tokens[field_end:marker_index]) & TEMPORAL_CONTEXT_LEADERS
        ):
            continue
        tail = [
            token
            for index, token in enumerate(
                tokens[marker_index + 1 : start],
                start=marker_index + 1,
            )
            if index not in identity_indexes
        ]
        # An explicit ``for`` suffix binds the following identity even when a
        # separate temporal phrase precedes it: ``after hero shot for guide``.
        # The temporal identity is rejected above; its leader must not erase
        # the later, grammatically explicit scope. Ambiguous ``of guide`` and
        # bare ``guide only`` tails remain fail-closed in temporal prose.
        if set(tail) <= {
            "and",
            "as",
            "exclusively",
            "only",
            "or",
            "specifically",
            "the",
            "well",
        }:
            return True
    return (
        end < len(tokens)
        and tokens[end] in QUALIFIER_MODIFIERS
        and not (set(between) & TEMPORAL_CONTEXT_LEADERS)
    )


def grammatical_identity_scope(
    text: str,
    key: str,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None = None,
) -> tuple[set[IdentityToken], bool, set[int], set[int]]:
    """Return field-attached identities and identity tokens valid as context.

    Identity words in temporal phrases such as ``during hero scene`` remain
    valid prose but do not scope the field. Prefix, possessive, and explicit
    suffix qualifiers do. The two index sets are all selected identity tokens
    and the subset licensed by either attachment or temporal grammar.
    """
    tokens = normalize_phrase(text).split()
    spans, _broad_ambiguity = identity_token_spans(
        tokens,
        identity_aliases,
        alias_widths,
    )
    all_identity_indexes = {
        index
        for start, end, _identities in spans
        for index in range(start, end)
    }
    groups = field_groups(tokens)
    target_identities: set[IdentityToken] = set()
    ambiguous_scope = False
    licensed_indexes: set[int] = set()
    for span in spans:
        start, end, identities = span
        temporal = is_temporal_identity_span(tokens, start, end)
        attached_groups = [
            group
            for group in groups
            if identity_span_attaches_to_group(
                tokens,
                span,
                group,
                all_identity_indexes,
            )
        ]
        if temporal or attached_groups:
            licensed_indexes.update(range(start, end))
        if any(
            key in {candidate for _start, _end, candidate in group}
            for group in attached_groups
        ):
            target_identities.update(identities)
            ambiguous_scope = ambiguous_scope or len(identities) > 1
    return (
        target_identities,
        ambiguous_scope,
        all_identity_indexes,
        licensed_indexes,
    )


def has_bounded_waiver_grammar(
    text: str,
    key: str,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None = None,
) -> bool:
    """Accept only explicit field, predicate, context, and entity grammar.

    An unknown residual token is never discarded. This is intentionally a
    bounded command grammar rather than open-ended natural-language inference:
    callers can use the documented bare-field shorthand or an explicit change
    predicate, but an unknown ``stranger only`` tail cannot become global.
    """
    tokens = normalize_phrase(text).split()
    groups = field_groups(tokens)
    if not any(
        key in {candidate for _start, _end, candidate in group}
        for group in groups
    ):
        return False

    mentioned, ambiguous, identity_indexes, licensed_identity_indexes = (
        grammatical_identity_scope(
            text,
            key,
            identity_aliases,
            alias_widths,
        )
    )
    if ambiguous or len(mentioned) > 1:
        return False
    if identity_indexes - licensed_identity_indexes:
        return False

    occupied: set[int] = set()
    for group in groups:
        for start, end, _candidate in group:
            occupied.update(range(start, end))
    occupied.update(licensed_identity_indexes)

    special_axis_tokens: set[int] = set()
    if key == "travel_direction":
        for group in groups:
            if not any(
                candidate == "travel_direction"
                and tokens[start:end] == ["axis", "reset"]
                for start, end, candidate in group
            ):
                continue
            suffix_start = group[-1][1]
            if tuple(tokens[suffix_start:]) in AXIS_RESET_SHOT_QUALIFIERS:
                special_axis_tokens.update(range(suffix_start, len(tokens)))

    allowed = set(WAIVER_PREDICATE_WORDS)
    if mentioned:
        allowed.update(QUALIFIER_MODIFIERS)
        allowed.update({"for", "of"})
    for index, token in enumerate(tokens):
        if index in occupied or index in special_axis_tokens:
            continue
        if (
            token == "s"
            and index > 0
            and index - 1 in licensed_identity_indexes
        ):
            continue
        if token not in allowed:
            return False
        # Scope markers without a recognized entity are not global grammar.
        if not mentioned and token in QUALIFIER_MODIFIERS | {"for"}:
            return False
    return True


def is_unqualified_global_waiver(
    text: str,
    key: str,
    identity_aliases: IdentityAliases | None = None,
    alias_widths: tuple[int, ...] | None = None,
) -> bool:
    aliases = identity_aliases or {}
    if not has_bounded_waiver_grammar(text, key, aliases, alias_widths):
        return False
    mentioned, ambiguous, _all_indexes, _licensed_indexes = (
        grammatical_identity_scope(
            text,
            key,
            aliases,
            alias_widths,
        )
    )
    return not ambiguous and not mentioned


def allowance_matches_scope(
    text: str,
    key: str,
    scope_identity: IdentityToken | None,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None = None,
    *,
    identity_context: str | None = None,
) -> bool:
    if not has_bounded_waiver_grammar(
        text,
        key,
        identity_aliases,
        alias_widths,
    ):
        return False
    mentioned, ambiguous, _all_indexes, _licensed_indexes = (
        grammatical_identity_scope(
            identity_context if identity_context is not None else text,
            key,
            identity_aliases,
            alias_widths,
        )
    )
    if ambiguous or len(mentioned) > 1:
        return False
    if not mentioned:
        return is_unqualified_global_waiver(
            text,
            key,
            identity_aliases,
            alias_widths,
        )
    return scope_identity is not None and scope_identity == next(iter(mentioned))


def denial_conflicts_scope(
    text: str,
    key: str,
    scope_identity: IdentityToken | None,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None = None,
) -> bool:
    """Apply a denial globally or only to its one unambiguous entity scope."""
    mentioned, ambiguous, all_indexes, licensed_indexes = (
        grammatical_identity_scope(
            text,
            key,
            identity_aliases,
            alias_widths,
        )
    )
    tokens = normalize_phrase(text).split()
    occupied = set(licensed_indexes)
    for group in field_groups(tokens):
        for start, end, _candidate in group:
            occupied.update(range(start, end))
    unknown_residual = bool(all_indexes - licensed_indexes)
    for index, token in enumerate(tokens):
        if index in occupied:
            continue
        if token == "s" and index > 0 and index - 1 in licensed_indexes:
            continue
        if token in WAIVER_PREDICATE_WORDS | QUALIFIER_MODIFIERS | {"for", "of"}:
            continue
        unknown_residual = True
    # An unscoped, unknown, or alias-ambiguous denial fails closed globally.
    if ambiguous or unknown_residual or not mentioned:
        return True
    # A grammatical multi-identity denial applies exactly to the named set.
    return scope_identity in mentioned


def has_allowance(
    clip: dict,
    key: str,
    *,
    scope_identity: IdentityToken | None = None,
    identity_aliases: IdentityAliases | None = None,
    alias_widths: tuple[int, ...] | None = None,
) -> bool:
    aliases = identity_aliases or {}
    candidates: list[str] = []
    denials: list[str] = []
    unsafe = False
    for field in ("allowed_changes", "accepted_deviations", "continuity_breaks"):
        entries = clip.get(field, [])
        if not isinstance(entries, list):
            continue
        for text in entries:
            if not isinstance(text, str):
                continue
            bare_entry = normalize_phrase(text) in field_phrases(key)
            positive, entry_denials, entry_unsafe = analyze_field_entry(
                text,
                key,
                allow_bare=bare_entry,
                identity_aliases=aliases,
                alias_widths=alias_widths,
            )
            denials.extend(entry_denials)
            unsafe = unsafe or entry_unsafe
            for clause in positive:
                if not has_bounded_waiver_grammar(
                    clause,
                    key,
                    aliases,
                    alias_widths,
                ):
                    unsafe = True
                    continue
                candidates.append(clause)

    transition_value = clip.get("transition_in", "")
    if isinstance(transition_value, str):
        positive, entry_denials, entry_unsafe = analyze_field_entry(
            transition_value,
            key,
            allow_bare=False,
            identity_aliases=aliases,
            alias_widths=alias_widths,
        )
        denials.extend(entry_denials)
        unsafe = unsafe or entry_unsafe
        for clause in positive:
            if not has_bounded_waiver_grammar(
                clause,
                key,
                aliases,
                alias_widths,
            ):
                unsafe = True
                continue
            candidates.append(clause)

    # Denials and preservation claims are authoritative across the complete
    # entry set for their entity scope. Returning on the first positive would
    # let a later same-entity or global conflict disappear because of list order.
    if unsafe:
        return False
    return any(
        allowance_matches_scope(
            clause,
            key,
            scope_identity,
            aliases,
            alias_widths,
            identity_context=clause,
        )
        and not any(
            denial_conflicts_scope(
                denial,
                key,
                scope_identity,
                aliases,
                alias_widths,
            )
            for denial in denials
        )
        for clause in candidates
    )


def identity_value_token(value: object) -> tuple[str, str | int] | None:
    if type(value) is int:
        return ("int", value)
    if (
        isinstance(value, str)
        and value
        and value == value.strip()
        and not any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in value)
    ):
        return ("str", value)
    return None


def direct_list_item_identity(value: dict) -> ListIdentity | None:
    for identity_key in ("canonical_identity_id", "character_id", "id", "name"):
        if identity_key not in value:
            continue
        token = identity_value_token(value[identity_key])
        if token is not None:
            return (identity_key, *token)
    return None


def wrapped_list_identity(value: dict) -> ListIdentity | None:
    """Find one identity below a dictionary-only presentation wrapper."""
    found: set[ListIdentity] = set()
    pending = [child for child in value.values() if isinstance(child, dict)]
    while pending:
        current = pending.pop()
        identity = direct_list_item_identity(current)
        if identity is not None:
            found.add(identity)
            # An identified record owns its descendants; nested IDs are separate
            # entities and cannot identify the presentation wrapper itself.
            continue
        pending.extend(child for child in current.values() if isinstance(child, dict))
    if len(found) == 1:
        return next(iter(found))
    return None


def list_item_identity(value: dict) -> ListIdentity | None:
    return direct_list_item_identity(value) or wrapped_list_identity(value)


def list_item_label(value: dict, index: int) -> str:
    identity = list_item_identity(value)
    if identity is not None:
        return str(identity[2])
    return str(index)


def contains_continuity_field(value: object) -> bool:
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            if TRACKED_KEYS & current.keys():
                return True
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
    return False


def add_identity_alias(
    aliases: IdentityAliases,
    value: object,
    identity: IdentityToken,
) -> None:
    phrase = normalize_phrase(value)
    if phrase:
        aliases.setdefault(phrase, set()).add(identity)


def merge_identity_aliases(*registries: IdentityAliases) -> IdentityAliases:
    merged: IdentityAliases = {}
    for registry in registries:
        for phrase, identities in registry.items():
            merged.setdefault(phrase, set()).update(identities)
    return merged


def identity_inventory(
    state: dict | None,
    side: str,
) -> tuple[
    dict[
        tuple[object, ...],
        tuple[str, tuple[ListIdentity, ...]],
    ],
    list[str],
    set[IdentityToken],
    set[ListIdentity],
    IdentityAliases,
]:
    """Return globally unique canonical IDs and reject ambiguous list identities."""
    if not isinstance(state, dict):
        return {}, [], set(), set(), {}

    canonical_paths: dict[IdentityToken, list[str]] = {}
    canonical_fields: dict[
        tuple[tuple[str, str | int], str],
        list[str],
    ] = {}
    canonical_collections: dict[
        tuple[object, ...],
        tuple[str, tuple[ListIdentity, ...]],
    ] = {}
    list_identities: set[ListIdentity] = set()
    aliases: IdentityAliases = {}
    issues: list[str] = []

    pending: list[
        tuple[
            object,
            tuple[str, ...],
            tuple[tuple[object, ...], ...],
            tuple[str, str | int] | None,
            tuple[tuple[object, ...], ...],
        ]
    ] = [(state, (), (), None, ())]
    while pending:
        value, path, structural_path, canonical_identity, relative_path = pending.pop()
        if isinstance(value, dict):
            if "canonical_identity_id" in value:
                raw_identity = value["canonical_identity_id"]
                token = identity_value_token(raw_identity)
                field_path = ".".join(path + ("canonical_identity_id",))
                if token is None:
                    issues.append(
                        f"{side} {field_path} must be a non-empty string or integer"
                    )
                else:
                    canonical_paths.setdefault(token, []).append(".".join(path) or "<root>")
                    canonical_identity = token
                    relative_path = ()
                    add_identity_alias(aliases, raw_identity, token)
                    for identity_key in ("character_id", "id", "name"):
                        alias_value = value.get(identity_key)
                        if identity_value_token(alias_value) is not None:
                            add_identity_alias(aliases, alias_value, token)
                    for path_segment in reversed(path):
                        phrase = normalize_phrase(path_segment)
                        if (
                            phrase
                            and not phrase.isdigit()
                            and phrase not in GENERIC_IDENTITY_PATH_WORDS
                        ):
                            add_identity_alias(aliases, path_segment, token)
                            break
            for child_key, child_value in reversed(tuple(value.items())):
                if (
                    canonical_identity is not None
                    and child_key in TRACKED_KEYS
                    and child_value is not None
                ):
                    canonical_fields.setdefault(
                        (canonical_identity, child_key),
                        [],
                    ).append(".".join(path + (str(child_key),)))
                if isinstance(child_value, (dict, list)):
                    pending.append(
                        (
                            child_value,
                            path + (str(child_key),),
                            structural_path + (("key", str(child_key)),),
                            canonical_identity,
                            relative_path + (("key", str(child_key)),),
                        )
                    )
            continue

        if not isinstance(value, list):
            continue

        if canonical_identity is not None:
            collection_locator = (
                "canonical-collection",
                *canonical_identity,
                *relative_path,
            )
        else:
            collection_locator = ("structural", *structural_path)

        if not value:
            canonical_collections[collection_locator] = (
                ".".join(path) or "<root>",
                (),
            )
        elif contains_continuity_field(value):
            identities = [
                list_item_identity(item) if isinstance(item, dict) else None
                for item in value
            ]
            canonical_count = sum(
                identity is not None and identity[0] == "canonical_identity_id"
                for identity in identities
            )
            if canonical_count and canonical_count != len(value):
                issues.append(
                    f"{side} {'.'.join(path) or '<root>'} mixes canonical-identity "
                    "records with positional or differently identified items"
                )
            elif not canonical_count:
                present = [identity for identity in identities if identity is not None]
                if present and len(present) != len(value):
                    issues.append(
                        f"{side} {'.'.join(path) or '<root>'} mixes identified "
                        "records with positional items"
                    )
                duplicates = [
                    identity
                    for identity, count in Counter(present).items()
                    if count > 1
                ]
                if duplicates:
                    issues.append(
                        f"{side} {'.'.join(path) or '<root>'} has duplicate list "
                        f"identities {duplicates!r}"
                    )
                identity_kinds = {identity[0] for identity in present}
                if len(identity_kinds) > 1:
                    issues.append(
                        f"{side} {'.'.join(path) or '<root>'} mixes differently "
                        f"identified records {sorted(identity_kinds)!r}"
                    )
            present_identities = {
                identity for identity in identities if identity is not None
            }
            list_identities.update(present_identities)
            canonical_collections[collection_locator] = (
                ".".join(path) or "<root>",
                tuple(
                    sorted(
                        present_identities,
                        key=repr,
                    )
                ),
            )

        for index in range(len(value) - 1, -1, -1):
            child_value = value[index]
            if isinstance(child_value, dict):
                label = list_item_label(child_value, index)
            else:
                label = str(index)
            if isinstance(child_value, (dict, list)):
                if isinstance(child_value, dict):
                    identity = list_item_identity(child_value)
                else:
                    identity = None
                if identity is None:
                    child_segment = ("index", index)
                else:
                    child_segment = ("list-identity", *identity)
                pending.append(
                    (
                        child_value,
                        path + (label,),
                        structural_path + (child_segment,),
                        canonical_identity,
                        relative_path + (child_segment,),
                    )
                )
    for token, paths in canonical_paths.items():
        if len(paths) > 1:
            issues.append(
                f"{side} canonical_identity_id {token!r} is duplicated at {paths!r}"
            )
    for (token, field), paths in canonical_fields.items():
        if len(paths) > 1:
            issues.append(
                f"{side} canonical identity {token!r} has ambiguous repeated "
                f"continuity field {field!r} at {paths!r}"
            )
    return (
        canonical_collections,
        issues,
        set(canonical_paths),
        list_identities,
        aliases,
    )


def state_values(
    state: dict | None,
    key: str,
) -> list[
    tuple[
        tuple[object, ...],
        tuple[object, ...],
        str,
        object,
        tuple[str, str | int] | None,
    ]
]:
    if not isinstance(state, dict):
        return []

    matches: list[
        tuple[
            tuple[object, ...],
            tuple[object, ...],
            str,
            object,
            tuple[str, str | int] | None,
        ]
    ] = []

    pending: list[
        tuple[
            object,
            tuple[str, ...],
            tuple[tuple[object, ...], ...],
            tuple[str, str | int] | None,
            tuple[tuple[object, ...], ...],
        ]
    ] = [(state, (), (), None, ())]
    while pending:
        value, path, structural_path, canonical_identity, relative_path = pending.pop()
        if isinstance(value, dict):
            own_identity = identity_value_token(value.get("canonical_identity_id"))
            if own_identity is not None:
                canonical_identity = own_identity
                relative_path = ()
            for child_key, child_value in reversed(tuple(value.items())):
                child_path = path + (str(child_key),)
                child_segment = ("key", str(child_key))
                child_structural_path = structural_path + (child_segment,)
                child_relative_path = relative_path + (child_segment,)
                if child_key == key:
                    if canonical_identity is not None:
                        locator: tuple[object, ...] = (
                            "canonical",
                            *canonical_identity,
                            ("field", str(child_key)),
                        )
                    else:
                        locator = ("structural", *child_structural_path)
                    matches.append(
                        (
                            locator,
                            ("structural", *child_structural_path),
                            ".".join(child_path),
                            child_value,
                            canonical_identity,
                        )
                    )
                if isinstance(child_value, (dict, list)):
                    pending.append(
                        (
                            child_value,
                            child_path,
                            child_structural_path,
                            canonical_identity,
                            child_relative_path,
                        )
                    )
        elif isinstance(value, list):
            for index in range(len(value) - 1, -1, -1):
                child_value = value[index]
                if isinstance(child_value, dict):
                    identity = list_item_identity(child_value)
                    label = list_item_label(child_value, index)
                else:
                    identity = None
                    label = str(index)
                if identity is None:
                    child_segment = ("index", index)
                else:
                    child_segment = ("list-identity", *identity)
                pending.append(
                    (
                        child_value,
                        path + (label,),
                        structural_path + (child_segment,),
                        canonical_identity,
                        relative_path + (child_segment,),
                    )
                )
    return matches


def comparable_values(
    end_state: dict,
    start_state: dict,
    key: str,
) -> list[
    tuple[
        str,
        object,
        object,
        tuple[str, str | int] | None,
    ]
]:
    end_values = state_values(end_state, key)
    start_values = state_values(start_state, key)
    end_by_locator = {
        locator: (structural_locator, display_path, value, identity)
        for locator, structural_locator, display_path, value, identity in end_values
    }
    start_by_locator = {
        locator: (structural_locator, display_path, value, identity)
        for locator, structural_locator, display_path, value, identity in start_values
    }
    shared_semantic = end_by_locator.keys() & start_by_locator.keys()
    comparisons = [
        (
            end_by_locator[locator][1],
            end_by_locator[locator][2],
            start_by_locator[locator][2],
            (
                end_by_locator[locator][3]
                if end_by_locator[locator][3] == start_by_locator[locator][3]
                else None
            ),
        )
        for locator in sorted(
            shared_semantic,
            key=repr,
        )
    ]
    matched_end_structural = {
        end_by_locator[locator][0]
        for locator in shared_semantic
    }
    matched_start_structural = {
        start_by_locator[locator][0]
        for locator in shared_semantic
    }
    end_by_structural = {
        structural_locator: (display_path, value, identity)
        for _, structural_locator, display_path, value, identity in end_values
        if structural_locator not in matched_end_structural
    }
    start_by_structural = {
        structural_locator: (display_path, value, identity)
        for _, structural_locator, display_path, value, identity in start_values
        if structural_locator not in matched_start_structural
    }
    comparisons.extend(
        (
            end_by_structural[locator][0],
            end_by_structural[locator][1],
            start_by_structural[locator][1],
            (
                end_by_structural[locator][2]
                if end_by_structural[locator][2] == start_by_structural[locator][2]
                else None
            ),
        )
        for locator in sorted(
            end_by_structural.keys() & start_by_structural.keys(),
            key=repr,
        )
    )
    shared_structural = end_by_structural.keys() & start_by_structural.keys()
    unmatched_singletons_are_distinct = (
        len(end_values) == 1
        and len(start_values) == 1
        and not shared_semantic
        and not shared_structural
    )
    if not unmatched_singletons_are_distinct:
        comparisons.extend(
            (
                end_by_structural[locator][0],
                end_by_structural[locator][1],
                MISSING,
                end_by_structural[locator][2],
            )
            for locator in sorted(
                end_by_structural.keys() - shared_structural,
                key=repr,
            )
        )
        comparisons.extend(
            (
                start_by_structural[locator][0],
                MISSING,
                start_by_structural[locator][1],
                start_by_structural[locator][2],
            )
            for locator in sorted(
                start_by_structural.keys() - shared_structural,
                key=repr,
            )
        )
    return comparisons


def validate(
    path: Path,
    root: Path,
    review_index: TakeReviewIndex | None = None,
) -> tuple[list[str], list[str]]:
    data, rel, errors = load_project_document(path, root)
    warnings: list[str] = []
    if data is None:
        return bound_validation_diagnostics(errors, rel), warnings
    lineage = analyze_lineage(data.get("clips"), rel)
    errors.extend(lineage.errors)
    if review_index is None:
        review_index = build_take_review_indexes([path])[path.resolve().parent]
    errors.extend(
        validate_take_reconciliation(data, lineage.clips_by_id, rel, review_index)
    )
    for clip, parent in lineage.accepted_links:
        end_state = parent.get("observed_end_state")
        start_state = clip.get("planned_start_state")
        if not isinstance(start_state, dict) or not start_state:
            errors.append(f"{rel}: clip {clip['clip_id']} missing planned_start_state")
            continue
        (
            end_collections,
            end_identity_issues,
            end_canonical_identities,
            end_list_identities,
            end_aliases,
        ) = identity_inventory(
            end_state,
            "observed end state",
        )
        (
            start_collections,
            start_identity_issues,
            start_canonical_identities,
            start_list_identities,
            start_aliases,
        ) = identity_inventory(
            start_state,
            "planned start state",
        )
        errors.extend(
            f"{rel}: {issue}"
            for issue in (*end_identity_issues, *start_identity_issues)
        )
        identity_aliases = merge_identity_aliases(end_aliases, start_aliases)
        identity_alias_widths = tuple(
            sorted(
                {len(phrase.split()) for phrase in identity_aliases if phrase},
                reverse=True,
            )
        )
        allowance_cache: dict[tuple[str, IdentityToken | None], bool] = {}

        def field_has_allowance(
            field: str,
            scope_identity: IdentityToken | None,
        ) -> bool:
            cache_key = (field, scope_identity)
            if cache_key not in allowance_cache:
                allowance_cache[cache_key] = has_allowance(
                    clip,
                    field,
                    scope_identity=scope_identity,
                    identity_aliases=identity_aliases,
                    alias_widths=identity_alias_widths,
                )
            return allowance_cache[cache_key]

        has_global_identity_allowance = field_has_allowance(
            "canonical_identity_id",
            None,
        )
        if not has_global_identity_allowance:
            if end_canonical_identities != start_canonical_identities:
                errors.append(
                    f"{rel}: immutable canonical_identity_id inventory changes "
                    f"from {tuple(sorted(end_canonical_identities, key=repr))!r} to "
                    f"{tuple(sorted(start_canonical_identities, key=repr))!r} "
                    "without allowance"
                )
            end_fallback_identities = {
                identity
                for identity in end_list_identities
                if identity[0] != "canonical_identity_id"
            }
            start_fallback_identities = {
                identity
                for identity in start_list_identities
                if identity[0] != "canonical_identity_id"
            }
            if end_fallback_identities != start_fallback_identities:
                errors.append(
                    f"{rel}: immutable fallback list identity inventory changes "
                    f"from {tuple(sorted(end_fallback_identities, key=repr))!r} to "
                    f"{tuple(sorted(start_fallback_identities, key=repr))!r} "
                    "without allowance"
                )
            for collection_locator in sorted(
                end_collections.keys() & start_collections.keys(),
                key=repr,
            ):
                display_path, end_collection_identities = end_collections[
                    collection_locator
                ]
                _, start_collection_identities = start_collections[collection_locator]
                if end_collection_identities != start_collection_identities:
                    errors.append(
                        f"{rel}: immutable {display_path} identity inventory changes "
                        f"from {end_collection_identities!r} to "
                        f"{start_collection_identities!r} without allowance"
                    )
        for key in IMMUTABLE_KEYS:
            for field_path, a, b, scope_identity in comparable_values(
                end_state,
                start_state,
                key,
            ):
                if a is MISSING or b is MISSING:
                    present = b if a is MISSING else a
                    if present is None or field_has_allowance(key, scope_identity):
                        continue
                    direction = "appears" if a is MISSING else "disappears"
                    errors.append(
                        f"{rel}: immutable {field_path} {direction} without allowance"
                    )
                elif a is not None and b is not None and a != b and not field_has_allowance(
                    key,
                    scope_identity,
                ):
                    errors.append(
                        f"{rel}: immutable {field_path} changes from {a!r} to {b!r} without allowance"
                    )
        for key in TRANSIENT_KEYS:
            for field_path, a, b, scope_identity in comparable_values(
                end_state,
                start_state,
                key,
            ):
                if a is MISSING or b is MISSING:
                    present = b if a is MISSING else a
                    if present is None or field_has_allowance(key, scope_identity):
                        continue
                    direction = "appears" if a is MISSING else "disappears"
                    warnings.append(
                        f"{rel}: transient {field_path} {direction} without allowance"
                    )
                elif a is not None and b is not None and a != b and not field_has_allowance(
                    key,
                    scope_identity,
                ):
                    warnings.append(
                        f"{rel}: transient {field_path} changes from {a!r} to {b!r} without allowance"
                    )
    return (
        bound_validation_diagnostics(errors, rel),
        bound_validation_diagnostics(warnings, rel),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat transient continuity warnings as validation errors",
    )
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    examples = root / "examples"
    if os.path.lexists(examples):
        try:
            examples = validate_repo_input_path(root, examples)
        except ValueError as exc:
            errors.append(f"examples: {exc}")
            examples = None
    else:
        examples = None
    candidates = (
        sorted(examples.rglob("*project-state*.json"))
        if examples is not None
        else []
    )
    paths: list[Path] = []
    for path in candidates:
        try:
            paths.append(validate_repo_input_path(root, path))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(
                f"{diagnostic_path(path.relative_to(root))}: "
                f"invalid project state: {exc}"
            )
    review_indexes = build_take_review_indexes(paths)
    for path in paths:
        try:
            e, w = validate(path, root, review_indexes[path.resolve().parent])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(
                f"{diagnostic_path(path.relative_to(root))}: "
                f"invalid project state: {exc}"
            )
            continue
        errors.extend(e)
        warnings.extend(w)
    warnings = bound_diagnostics(warnings, "additional continuity warnings omitted")
    errors = bound_diagnostics(errors, "additional continuity errors omitted")
    if warnings:
        print("Continuity warnings:")
        for warning in warnings:
            print(diagnostic_text(f"- {warning}"))
        print()
    if errors or (args.strict and warnings):
        print("Continuity errors:")
        for error in errors:
            print(diagnostic_text(f"- {error}"))
        if args.strict:
            for warning in warnings:
                print(diagnostic_text(f"- {warning}"))
        return 1
    print("Continuity chain check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

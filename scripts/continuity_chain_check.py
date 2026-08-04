#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from bisect import bisect_left, bisect_right
from collections import Counter
from decimal import Decimal
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
MAX_WAIVER_TOKENS = 1024
MAX_IDENTITY_MATCH_CANDIDATES = 65_536
MAX_JSON_COMPARE_NODES = 100_000
IDENTITY_MATCH_OVERFLOW: IdentityToken = ("internal", "identity-match-overflow")

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
ALL_CLAUSE_PREDICATE_WORDS = (
    TRANSITION_CHANGE_WORDS
    | NEGATION_WORDS
    | PRESERVATION_WORDS
    | NEGATING_CONTRACTION_STEMS
)
MODAL_OR_NONIMPERATIVE_PREFIX_WORDS = {
    "allowed",
    "allows",
    "are",
    "be",
    "being",
    "can",
    "changed",
    "changes",
    "changing",
    "deviation",
    "different",
    "drift",
    "drifted",
    "drifts",
    "is",
    "may",
    "must",
    "mismatch",
    "mismatched",
    "new",
    "permitted",
    "replacement",
    "variation",
    "will",
}
SERIAL_REDUNDANT_CONTEXT_WORDS = {
    "explicit",
    "explicitly",
    "global",
    "globally",
    "intentional",
    "intentionally",
}
SERIAL_AMBIGUOUS_DETERMINERS = {"all", "the", "this"}
LINKING_PREPOSITION_HEADS = {
    "change",
    "changes",
    "changing",
    "shift",
    "switch",
    "transition",
    "variation",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_phrase(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))


def clause_connector_spans(tokens: list[str]) -> list[tuple[int, int]]:
    """Return single- and multi-token field-clause coordinators."""
    spans: list[tuple[int, int]] = []
    index = 0
    while index < len(tokens):
        if tokens[index : index + 3] == ["as", "well", "as"]:
            spans.append((index, index + 3))
            index += 3
            continue
        if tokens[index] in ENTITY_LIST_CONNECTORS:
            spans.append((index, index + 1))
        index += 1
    return spans


def has_clause_connector(tokens: list[str], start: int, end: int) -> bool:
    """Return whether a complete connector occurs inside ``[start, end)``."""
    return any(
        start <= connector_start and connector_end <= end
        for connector_start, connector_end in clause_connector_spans(tokens)
    )


def field_phrases(key: str) -> set[str]:
    phrases = {normalize_phrase(key)}
    phrases.update(normalize_phrase(alias) for alias in FIELD_ALIASES.get(key, ()))
    return phrases


def mentions_field(text: str, key: str) -> bool:
    padded = f" {normalize_phrase(text)} "
    return any(f" {phrase} " in padded for phrase in field_phrases(key))


def is_scope_fragment(
    text: object,
    identity_aliases: IdentityAliases | None = None,
    alias_widths: tuple[int, ...] | None = None,
) -> bool:
    """Return whether a fieldless fragment is only explicit scope grammar.

    A scoped denial such as ``for guide must remain unchanged`` is a complete
    anaphoric clause, not a qualifier to glue onto the previous sentence.
    Known grammar-word identities are excluded before testing predicate words,
    so a pure suffix such as ``only for May`` remains a scope fragment.
    """
    tokens = normalize_phrase(text).split()
    raw_spans, _ambiguous = identity_token_spans(
        tokens,
        identity_aliases or {},
        alias_widths,
    )
    spans = [
        span
        for span in raw_spans
        if fieldless_identity_span_is_explicit(tokens, span)
    ]
    identity_indexes = {
        index
        for start, end, _identities in spans
        for index in range(start, end)
    }
    has_clause_predicate = any(
        index not in identity_indexes
        and token in (ALL_CLAUSE_PREDICATE_WORDS | NEGATING_CONTRACTION_STEMS)
        for index, token in enumerate(tokens)
    )
    return bool(tokens) and not field_groups(tokens) and bool(
        set(tokens) & QUALIFIER_MODIFIERS
        or tokens[0] in {"for", "of"}
    ) and not has_clause_predicate


def identity_indexes_for_tokens(
    tokens: list[str],
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> set[int]:
    """Return aliases that occupy a grammatical identity or temporal slot.

    A spelling match alone is insufficient. If a character is named ``May``,
    the modal in ``wardrobe may change`` is still grammar, while the first token
    in ``May wardrobe may change`` is identity data. Polarity parsing therefore
    excludes only aliases attached to a local field or a bounded temporal
    phrase. Ambiguous denial/preservation words retain their conservative
    polarity separately in :func:`clause_field_polarities`.
    """
    groups = field_groups(tokens)
    raw_spans, _ambiguous = identity_token_spans(
        tokens,
        identity_aliases,
        alias_widths,
    )
    spans = [
        span
        for span in raw_spans
        if not identity_span_is_field_grammar(span, groups, tokens)
    ]
    group_starts = tuple(group[0][0] for group in groups)
    group_ends = tuple(group[-1][1] for group in groups)
    lexical_identity_indexes = {
        index
        for start, end, _identities in spans
        for index in range(start, end)
    }
    return {
        index
        for span in spans
        if is_temporal_identity_span(tokens, span[0], span[1])
        or any(
            identity_span_attaches_to_group(
                tokens,
                span,
                groups[group_index],
                groups,
                group_index,
                lexical_identity_indexes,
            )
            for group_index in neighboring_field_group_indexes(
                span,
                groups,
                group_starts,
                group_ends,
            )
        )
        for index in range(span[0], span[1])
    }


def has_completed_field_predicate(
    text: str,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> bool:
    """Return whether a comma-left field fragment ends in a predicate.

    A comma after a completed field clause is a clause boundary. A comma before
    the one shared predicate in ``wardrobe, location, and product identity must
    not change`` is a list coordinator. Looking only after the final recognized
    field keeps prefix predicates shared across a following serial list. Every
    identity span is excluded so ``May`` or ``Change`` cannot create a boundary.
    """
    tokens = normalize_phrase(text).split()
    if len(tokens) > MAX_WAIVER_TOKENS:
        return False
    _has_predicate, completed_after_field = field_predicate_summary(
        tokens,
        field_groups(tokens),
        identity_aliases,
        alias_widths,
    )
    return completed_after_field


def field_predicate_summary(
    tokens: list[str],
    groups: list[list[FieldSpan]],
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> tuple[bool, bool]:
    """Return predicate presence and whether one follows the final field."""
    if not tokens:
        return False, False
    occupied = {
        index
        for group in groups
        for start, end, _candidate in group
        for index in range(start, end)
    }
    occupied.update(
        identity_indexes_for_tokens(tokens, identity_aliases, alias_widths)
    )
    predicate_words = (
        TRANSITION_CHANGE_WORDS
        | NEGATION_WORDS
        | PRESERVATION_WORDS
        | NEGATING_CONTRACTION_STEMS
    )
    predicate_indexes = {
        index
        for index, token in enumerate(tokens)
        if index not in occupied and token in predicate_words
    }
    if not groups:
        return bool(predicate_indexes), False
    final_field_end = max(group[-1][1] for group in groups)
    return bool(predicate_indexes), any(
        index >= final_field_end for index in predicate_indexes
    )


def split_comma_clauses(
    text: str,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> list[str]:
    """Split comma clauses while retaining comma-coordinated field lists.

    ``normalize_phrase`` deliberately drops punctuation, so list commas are
    converted to an explicit coordinator before semantic tokenization. This
    preserves every item in both Oxford- and non-Oxford-comma lists without
    merging independent clauses that already carry their own predicate.
    """
    raw_parts = text.split(",")
    if len(raw_parts) == 1:
        stripped = text.strip()
        return [stripped] if normalize_phrase(stripped) else []

    parts = [part.strip() for part in raw_parts]
    part_tokens = [normalize_phrase(part).split() for part in parts]
    part_groups = [field_groups(tokens) for tokens in part_tokens]
    part_field_counts = [
        sum(len(group) for group in groups) for groups in part_groups
    ]
    predicate_summaries = [
        field_predicate_summary(
            tokens,
            groups,
            identity_aliases,
            alias_widths,
        )
        for tokens, groups in zip(part_tokens, part_groups)
    ]
    part_has_connectors = [
        bool(clause_connector_spans(tokens)) for tokens in part_tokens
    ]
    part_starts_connector = [
        bool(tokens)
        and (
            tokens[0] in ENTITY_LIST_CONNECTORS
            or tokens[:3] == ["as", "well", "as"]
        )
        for tokens in part_tokens
    ]
    suffix_field_counts = [0] * (len(parts) + 1)
    suffix_has_connector = [False] * (len(parts) + 1)
    for index in range(len(parts) - 1, -1, -1):
        suffix_field_counts[index] = (
            part_field_counts[index] + suffix_field_counts[index + 1]
        )
        suffix_has_connector[index] = (
            part_has_connectors[index] or suffix_has_connector[index + 1]
        )

    clauses: list[str] = []
    current_parts: list[str] = []
    current_has_field = False
    current_completed = False
    for part_index, right in enumerate(parts):
        if not part_tokens[part_index]:
            continue
        right_has_field = part_field_counts[part_index] > 0
        right_has_predicate, right_completed = predicate_summaries[part_index]
        if not current_parts:
            current_parts.append(right)
            current_has_field = right_has_field
            current_completed = right_completed
            continue
        shared_field_list = (
            current_has_field
            and not current_completed
            and suffix_field_counts[part_index] >= 1
            and suffix_has_connector[part_index]
        )
        if part_starts_connector[part_index]:
            current_parts.append(right)
        elif shared_field_list:
            current_parts.extend(("and", right))
        else:
            clauses.append(" ".join(current_parts))
            current_parts = [right]
            current_has_field = right_has_field
            current_completed = right_completed
            continue

        if right_has_field:
            # The final field is now in this part, so only a predicate after
            # that field completes the growing clause.
            current_completed = right_completed
        elif current_has_field and right_has_predicate:
            current_completed = True
        current_has_field = current_has_field or right_has_field

    if current_parts:
        clauses.append(" ".join(current_parts))
    return clauses


def normalize_clause_punctuation(text: object) -> str:
    """Fold compatibility punctuation and every Unicode punctuation comma.

    The previous fixed table silently dropped valid comma characters from
    Armenian, NKo, Ethiopic, Mongolian, Vai, Bamum, Newa, and related scripts.
    Unicode gives those punctuation characters stable names ending in
    ``COMMA``; restricting the rule to punctuation categories avoids folding
    modifier letters or combining marks whose names merely mention a comma.
    """
    normalized = unicodedata.normalize("NFKC", str(text))
    return "".join(
        ","
        if unicodedata.category(character).startswith("P")
        and unicodedata.name(character, "").endswith("COMMA")
        else character
        for character in normalized
    )


def text_segments(
    text: object,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> list[str]:
    """Split independent clauses while preserving attached scope fragments.

    Splitting first, then attaching a qualifier avoids regex backtracking at a
    combined boundary such as ``.\nOnly for hero``. A leading qualifier belongs
    to the following field clause; a later qualifier belongs to the preceding
    one. Unknown names remain attached when they carry explicit scope grammar,
    so bounded parsing can reject rather than discard them.
    """
    # U+3002 is not compatibility-mapped by NFKC, so it remains an explicit
    # sentence boundary below.
    normalized_text = normalize_clause_punctuation(text)
    hard_segments = re.split(
        r"(?:[.;:!?\r\n\u3002\u2013\u2014]+|\bbut\b|\bhowever\b)",
        normalized_text,
        flags=re.IGNORECASE,
    )
    segments: list[str] = []
    for hard_segment in hard_segments:
        raw_segments = [
            segment
            for segment in split_comma_clauses(
                hard_segment,
                identity_aliases,
                alias_widths,
            )
            if normalize_phrase(segment)
        ]
        if not raw_segments:
            continue

        local_segments: list[str] = []
        leading_scope: list[str] = []
        for index, segment in enumerate(raw_segments):
            if is_scope_fragment(segment, identity_aliases, alias_widths):
                # A qualifier at the start of this hard sentence belongs to a
                # following field in the same sentence. A later qualifier is
                # postpositive and belongs to the preceding local field. If the
                # complete hard sentence is only a qualifier (``. Only hero``),
                # preserve the established cross-boundary trailing shorthand.
                has_later_field_clause = any(
                    not is_scope_fragment(
                        candidate,
                        identity_aliases,
                        alias_widths,
                    )
                    for candidate in raw_segments[index + 1 :]
                )
                if local_segments:
                    local_segments[-1] = f"{local_segments[-1]} {segment}"
                elif has_later_field_clause:
                    leading_scope.append(segment)
                elif segments:
                    segments[-1] = f"{segments[-1]} {segment}"
                else:
                    leading_scope.append(segment)
                continue
            if leading_scope:
                segment = " ".join((*leading_scope, segment))
                leading_scope.clear()
            local_segments.append(segment)
        segments.extend(local_segments)
        if leading_scope:
            # A qualifier with no field anywhere cannot grant a waiver. Keeping
            # it as its own segment lets whole-entry validation fail closed.
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
            non_articles = [
                token for token in between if token not in {"a", "an", "the"}
            ]
            if between and (
                set(between) <= FIELD_COORDINATORS
                or non_articles == ["as", "well", "as"]
            ):
                groups[-1].append(mention)
                occupied_until = end
                continue
        groups.append([mention])
        occupied_until = end
    return groups


def identity_span_is_field_grammar(
    span: tuple[int, int, set[IdentityToken]],
    groups: list[list[FieldSpan]],
    tokens: list[str] | None = None,
) -> bool:
    """Return whether an alias occurrence is wholly inside a known field.

    ``Identity``, ``Phase``, and ``State`` can be legitimate entity aliases,
    but inside ``product identity``, ``camera phase``, or ``focus state`` they
    are field grammar. Treating those occurrences as entity data would poison
    an otherwise global waiver.
    """
    start, end, _identities = span
    inside_field = any(
        field_start <= start and end <= field_end
        for group in groups
        for field_start, field_end, _candidate in group
    )
    if not inside_field:
        return False
    if tokens is None:
        return True

    # A complete entity alias may itself spell a field phrase. In
    # ``Product Identity product identity may change`` the first occurrence is
    # the entity prefix and the second is field grammar. Preserve only that
    # prefix occurrence; a lone ``product identity may change`` remains a
    # global field waiver. Possessive normalization contributes the bounded
    # ``s`` gap.
    for group in groups:
        for field_start, _field_end, _candidate in group:
            if field_start < end:
                continue
            gap = tokens[end:field_start]
            if gap in ([], ["s"], ["s", "the"]):
                return False
    return True


def neighboring_field_group_indexes(
    span: tuple[int, int, set[IdentityToken]],
    groups: list[list[FieldSpan]],
    group_starts: tuple[int, ...],
    group_ends: tuple[int, ...],
) -> tuple[int, ...]:
    """Return the only groups a non-overlapping identity span can modify.

    Prefix identities attach to the immediately following field group; suffix
    identities attach to the immediately preceding one. Binary search avoids
    testing every identity against every field in a long serial clause.
    """
    if not groups:
        return ()
    start, end, _identities = span
    candidates: set[int] = set()
    preceding = bisect_right(group_ends, start) - 1
    if preceding >= 0:
        candidates.add(preceding)
    following = bisect_left(group_starts, end)
    if following < len(groups):
        candidates.add(following)
    return tuple(sorted(candidates))


def semantic_token_clauses(
    text: object,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> list[list[str]]:
    """Split prose where distinct field predicates cannot share polarity.

    Punctuation and contrast conjunctions are hard boundaries. ``while`` and
    ``whereas`` also separate predicates even when one side has no action word.
    ``and``/``or`` split only after a completed predicate, preserving natural
    coordinated field lists such as ``wardrobe and product identity may
    change``.
    """
    clauses: list[list[str]] = []
    for segment in text_segments(text, identity_aliases, alias_widths):
        tokens = normalize_phrase(segment).split()
        if not tokens:
            continue
        groups = field_groups(tokens)
        mentions = [mention for group in groups for mention in group]
        identity_indexes = identity_indexes_for_tokens(
            tokens,
            identity_aliases,
            alias_widths,
        )
        connector_spans = [
            (start, end)
            for start, end in clause_connector_spans(tokens)
            if not set(range(start, end)) <= identity_indexes
        ]
        boundaries = {
            index: index + 1
            for index, token in enumerate(tokens)
            if token in HARD_CLAUSE_CONNECTORS
        }
        for connector_start, connector_end in connector_spans:
            clause_start = max(
                (
                    boundary_end
                    for boundary_start, boundary_end in boundaries.items()
                    if boundary_start < connector_start
                ),
                default=0,
            )
            clause_end = min(
                (
                    boundary_start
                    for boundary_start in boundaries
                    if boundary_start > connector_start
                ),
                default=len(tokens),
            )
            fields_before = [
                mention
                for mention in mentions
                if clause_start <= mention[0] and mention[1] <= connector_start
            ]
            fields_after = [
                mention
                for mention in mentions
                if connector_end <= mention[0] < clause_end
            ]
            if not fields_before:
                continue
            next_connector = min(
                (
                    candidate_start
                    for candidate_start, _candidate_end in connector_spans
                    if connector_end <= candidate_start < clause_end
                ),
                default=clause_end,
            )

            def is_event(event_index: int) -> bool:
                event = tokens[event_index]
                if event not in ALL_CLAUSE_PREDICATE_WORDS:
                    return False
                # An attached identity spelling can never create permission.
                # If it is also denial/preservation vocabulary, retaining that
                # polarity is the conservative interpretation.
                return event_index not in identity_indexes or event in (
                    NEGATION_WORDS | PRESERVATION_WORDS
                )

            left_events = [
                event_index
                for event_index in range(clause_start, connector_start)
                if is_event(event_index)
            ]
            if not left_events:
                continue
            first_left_field = min(mention[0] for mention in fields_before)
            final_left_field = max(mention[1] for mention in fields_before)
            completed_left_predicate = any(
                event_index >= final_left_field for event_index in left_events
            )
            prefix_left_predicate = any(
                event_index < first_left_field for event_index in left_events
            )
            right_has_local_predicate = any(
                is_event(event_index)
                for event_index in range(connector_end, next_connector)
            )
            fieldless_denial_tail = (
                not fields_after
                and completed_left_predicate
                and anaphorically_denies_change(
                    tokens[connector_end:clause_end],
                    identity_aliases,
                    alias_widths,
                )
            )
            # A suffix predicate completes the left clause. A prefix predicate
            # remains shared across a pure serial list, but not when the right
            # field declares its own prefix or suffix predicate.
            if completed_left_predicate or (
                prefix_left_predicate and right_has_local_predicate
            ):
                if fields_after or fieldless_denial_tail:
                    boundaries[connector_start] = connector_end

        start = 0
        for boundary_start, boundary_end in sorted(boundaries.items()):
            if tokens[start:boundary_start]:
                clauses.append(tokens[start:boundary_start])
            start = boundary_end
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
    identity_indexes: set[int],
) -> bool:
    """Recognize a coordinated entity/field list before its shared predicate."""
    start = left[-1][1]
    end = right[0][0]
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
    identity_indexes: set[int],
) -> list[list[FieldSpan]]:
    """Expand one bound group across an explicit coordinated field list."""
    index = groups.index(group)
    first = index
    last = index
    while first > 0 and groups_share_predicate(
        groups[first - 1],
        groups[first],
        tokens,
        identity_indexes,
    ):
        first -= 1
    while last + 1 < len(groups) and groups_share_predicate(
        groups[last],
        groups[last + 1],
        tokens,
        identity_indexes,
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
    identity_indexes = identity_indexes_for_tokens(
        tokens,
        identity_aliases,
        alias_widths,
    )
    positive_groups: set[tuple[FieldSpan, ...]] = set()
    denied_groups: set[tuple[FieldSpan, ...]] = set()
    for index, token in enumerate(tokens):
        is_identity_token = index in identity_indexes
        if token in TRANSITION_CHANGE_WORDS and not is_identity_token:
            group = bound_field_group(index, groups)
            if group is not None:
                positive_groups.update(
                    tuple(member)
                    for member in coordinated_field_cluster(
                        group,
                        groups,
                        tokens,
                        identity_indexes,
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
                        identity_indexes,
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
                        identity_indexes,
                    )
                )

    for index, (left, right) in enumerate(zip(tokens, tokens[1:])):
        if (
            left not in NEGATING_CONTRACTION_STEMS
            or right != "t"
        ):
            continue
        group = bound_field_group(index, groups)
        if group is not None:
            denied_groups.update(
                tuple(member)
                for member in coordinated_field_cluster(
                    group,
                    groups,
                    tokens,
                    identity_indexes,
                )
            )
    return groups, positive_groups, denied_groups


def anaphorically_denies_change(
    tokens: list[str],
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> bool:
    """Recognize a fieldless preservation tail without treating prose as NLP."""
    identity_indexes = identity_indexes_for_tokens(
        tokens,
        identity_aliases,
        alias_widths,
    )
    token_set = {
        token for index, token in enumerate(tokens) if index not in identity_indexes
    }
    if token_set & PRESERVATION_WORDS:
        return True
    if any(
        left in NEGATING_CONTRACTION_STEMS and right == "t"
        for index, (left, right) in enumerate(zip(tokens, tokens[1:]))
        if index not in identity_indexes and index + 1 not in identity_indexes
    ):
        return True
    return bool(token_set & NEGATION_WORDS and token_set & TRANSITION_CHANGE_WORDS)


def inherited_denial_context(
    tokens: list[str],
    key: str,
    previous_context: str,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> str:
    """Inherit an omitted field without discarding an explicit tail scope."""
    raw_spans, _ambiguous = identity_token_spans(
        tokens,
        identity_aliases,
        alias_widths,
    )
    spans = [
        span
        for span in raw_spans
        if fieldless_identity_span_is_explicit(tokens, span)
    ]
    span_indexes = {
        index
        for start, end, _identities in spans
        for index in range(start, end)
    }
    residual_indexes = [
        index
        for index, token in enumerate(tokens)
        if index not in span_indexes and token not in WAIVER_PREDICATE_WORDS
    ]
    has_explicit_scope = bool(
        spans
        or residual_indexes
        or set(tokens) & (QUALIFIER_MODIFIERS | {"for", "of"})
    )
    if not has_explicit_scope:
        return previous_context

    field_tokens = normalize_phrase(key).split()
    if spans and spans[0][0] == 0:
        insertion = spans[0][1]
        return " ".join((*tokens[:insertion], *field_tokens, *tokens[insertion:]))
    return " ".join((*field_tokens, *tokens))


def fieldless_identity_span_is_explicit(
    tokens: list[str],
    span: tuple[int, int, set[IdentityToken]],
) -> bool:
    """Reject predicate-only alias matches as fieldless entity scope.

    Literal names remain explicit. An alias made only of grammar vocabulary
    needs an entity marker (for/of/only/specifically/exclusively); otherwise
    ``change is not allowed`` could target a character named ``Change`` rather
    than inherit the preceding field and entity.
    """
    start, end, _identities = span
    if any(token not in WAIVER_PREDICATE_WORDS for token in tokens[start:end]):
        return True
    before = tokens[max(0, start - 2) : start]
    explicit_before = bool(before) and (
        before[-1] in (QUALIFIER_MODIFIERS | {"for", "of"})
        or (
            len(before) == 2
            and before[0] in (QUALIFIER_MODIFIERS | {"for", "of"})
            and before[1] == "the"
        )
    )
    explicit_after = end < len(tokens) and tokens[end] in QUALIFIER_MODIFIERS
    return explicit_before or explicit_after


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
    if len(normalize_phrase(text).split()) > MAX_WAIVER_TOKENS:
        return [], [], True
    entry_mentions_key = mentions_field(str(text), key)
    # Validate the unsplit entry first. Otherwise an event-looking unknown
    # identity inside a serial list can be isolated into one rejected clause
    # while its syntactically valid siblings still grant a waiver.
    if entry_mentions_key and has_unresolved_serial_identity_role(
        text,
        identity_aliases,
        alias_widths,
    ):
        return [], [], True
    for tokens in semantic_token_clauses(
        text,
        identity_aliases,
        alias_widths,
    ):
        groups, positive_groups, denied_groups = clause_field_polarities(
            tokens,
            identity_aliases,
            alias_widths,
        )
        if not groups:
            inherited_denial = (
                key in previous_fields
                and anaphorically_denies_change(
                    tokens,
                    identity_aliases,
                    alias_widths,
                )
            )
            if inherited_denial:
                # The omitted field inherits. The entity inherits only if the
                # tail has no explicit or unresolved scope of its own.
                denials.append(
                    inherited_denial_context(
                        tokens,
                        key,
                        previous_context,
                        identity_aliases,
                        alias_widths,
                    )
                )
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
                if current_context not in denials:
                    denials.append(current_context)
            bare_group = allow_bare and current_context in field_phrases(key)
            if (
                group_token not in denied_groups
                and (group_token in positive_groups or bare_group)
            ):
                if current_context not in positive:
                    positive.append(current_context)
    return positive, denials, unsafe


def identity_token_spans(
    tokens: list[str],
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None = None,
) -> tuple[list[tuple[int, int, set[IdentityToken]]], bool]:
    """Match aliases with a token trie and bounded overlap resolution.

    The former width-by-window matcher repeatedly joined the same token slices
    and became cubic for inventories containing aliases of every width. A trie
    visits only viable token prefixes. Candidate overflow returns one internal
    full-span ambiguity marker so every public waiver path fails closed.
    """
    if not tokens or not identity_aliases:
        return [], False

    allowed_widths = None
    if alias_widths is not None:
        allowed_widths = {
            width for width in alias_widths if 0 < width <= len(tokens)
        }

    terminal = object()
    trie: dict[object, object] = {}
    for phrase, identities in identity_aliases.items():
        if not phrase or not identities:
            continue
        phrase_tokens = phrase.split()
        width = len(phrase_tokens)
        if width > len(tokens) or (
            allowed_widths is not None and width not in allowed_widths
        ):
            continue
        node = trie
        for token in phrase_tokens:
            child = node.get(token)
            if not isinstance(child, dict):
                child = {}
                node[token] = child
            node = child
        node[terminal] = identities

    if not trie:
        return [], False

    candidates: list[tuple[int, int, set[IdentityToken]]] = []
    for start in range(len(tokens)):
        node = trie
        for end in range(start, len(tokens)):
            child = node.get(tokens[end])
            if not isinstance(child, dict):
                break
            node = child
            identities = node.get(terminal)
            if not isinstance(identities, set) or not identities:
                continue
            if len(candidates) >= MAX_IDENTITY_MATCH_CANDIDATES:
                return [
                    (0, len(tokens), {IDENTITY_MATCH_OVERFLOW})
                ], True
            candidates.append((start, end + 1, identities))

    # Resolve overlapping aliases by longest span first. This keeps an ID such
    # as "hero" from also matching inside the distinct ID "super hero".
    candidates.sort(key=lambda item: (-(item[1] - item[0]), item[0]))
    occupancy_tree = [0] * (len(tokens) + 1)

    def occupied_prefix(end: int) -> int:
        total = 0
        while end > 0:
            total += occupancy_tree[end]
            end -= end & -end
        return total

    def range_is_occupied(start: int, end: int) -> bool:
        return occupied_prefix(end) != occupied_prefix(start)

    def occupy_range(start: int, end: int) -> None:
        # Selected spans never overlap, so at most len(tokens) point updates are
        # performed across the complete resolution pass.
        for point in range(start, end):
            tree_index = point + 1
            while tree_index < len(occupancy_tree):
                occupancy_tree[tree_index] += 1
                tree_index += tree_index & -tree_index

    selected: list[tuple[int, int, set[IdentityToken]]] = []
    ambiguous = False
    for start, end, identities in candidates:
        if range_is_occupied(start, end):
            continue
        occupy_range(start, end)
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
    groups: list[list[FieldSpan]],
    group_index: int,
    identity_indexes: set[int],
) -> bool:
    start, end, _identities = span
    field_start = group[0][0]
    field_end = group[-1][1]
    previous_field_end = (
        groups[group_index - 1][-1][1] if group_index > 0 else 0
    )
    next_field_start = (
        groups[group_index + 1][0][0]
        if group_index + 1 < len(groups)
        else len(tokens)
    )
    if is_temporal_identity_span(tokens, start, end):
        return False

    # If an entity's full alias is also a recognized field phrase, its prefix
    # occurrence appears as the preceding field group. Bind that occurrence to
    # the following real field instead of discarding both spelling matches.
    # The actual field occurrence is not a prefix of any later group and stays
    # suppressed as grammar.
    collides_with_previous_field = any(
        field_start <= start and end <= field_end
        for previous_group in groups[:group_index]
        for field_start, field_end, _candidate in previous_group
    )
    if (
        collides_with_previous_field
        and end <= field_start
        and tokens[end:field_start] in ([], ["s"], ["s", "the"])
    ):
        return True

    connector_ends = [
        index + 1
        for index in range(previous_field_end, field_start)
        if tokens[index] in {"and", "or"}
    ]
    connector_ends.extend(
        index + 3
        for index in range(previous_field_end, max(previous_field_end, field_start - 2))
        if tokens[index : index + 3] == ["as", "well", "as"]
    )
    prefix_floor = (
        0 if group_index == 0 else max(connector_ends, default=previous_field_end)
    )
    prefix_tokens = [
        token
        for index, token in enumerate(tokens[start:field_start], start=start)
        if index not in identity_indexes
    ]
    prefix_has_local_connector = group_index == 0 or bool(connector_ends)
    if (
        prefix_has_local_connector
        and start >= prefix_floor
        and end <= field_start
        and set(prefix_tokens) <= {
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
        }
    ):
        return True

    if start < field_end or start >= next_field_start:
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
        if has_clause_connector(tokens, field_end, marker_index + 1):
            continue
        intervening_identity = any(
            index in identity_indexes
            for index in range(marker_index + 1, start)
        )
        latest_identity_index = max(
            (
                index
                for index in range(marker_index + 1, start)
                if index in identity_indexes
            ),
            default=marker_index,
        )
        identity_list_connector = any(
            latest_identity_index + 1 <= connector_start
            and connector_end <= start
            and not set(range(connector_start, connector_end)) <= identity_indexes
            for connector_start, connector_end in clause_connector_spans(tokens)
        )
        if intervening_identity and not identity_list_connector:
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
        and not has_clause_connector(tokens, field_end, start)
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
    groups = field_groups(tokens)
    raw_spans, _broad_ambiguity = identity_token_spans(
        tokens,
        identity_aliases,
        alias_widths,
    )
    spans = [
        span
        for span in raw_spans
        if not identity_span_is_field_grammar(span, groups, tokens)
    ]
    lexical_identity_indexes = {
        index
        for start, end, _identities in spans
        for index in range(start, end)
    }
    group_starts = tuple(group[0][0] for group in groups)
    group_ends = tuple(group[-1][1] for group in groups)
    target_identities: set[IdentityToken] = set()
    ambiguous_scope = any(
        IDENTITY_MATCH_OVERFLOW in identities
        for _start, _end, identities in spans
    )
    licensed_indexes: set[int] = set()
    for span in spans:
        start, end, identities = span
        temporal = is_temporal_identity_span(tokens, start, end)
        attached_groups = [
            groups[group_index]
            for group_index in neighboring_field_group_indexes(
                span,
                groups,
                group_starts,
                group_ends,
            )
            if identity_span_attaches_to_group(
                tokens,
                span,
                groups[group_index],
                groups,
                group_index,
                lexical_identity_indexes,
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
    # A nonattached alias made entirely of predicate/context vocabulary is a
    # grammar occurrence, not automatically identity data (for example the
    # modal ``May`` in ``wardrobe may change``). Literal aliases outside that
    # vocabulary remain unlicensed so bounded validation rejects them.
    identity_indexes = set(licensed_indexes)
    for start, end, _identities in spans:
        if set(range(start, end)) & licensed_indexes:
            continue
        if any(token not in WAIVER_PREDICATE_WORDS for token in tokens[start:end]):
            identity_indexes.update(range(start, end))
    return (
        target_identities,
        ambiguous_scope,
        identity_indexes,
        licensed_indexes,
    )


def has_suspicious_event_identity_role(
    tokens: list[str],
    groups: list[list[FieldSpan]],
    licensed_identity_indexes: set[int],
) -> bool:
    """Reject predicate-looking tokens occupying unresolved identity slots.

    The bounded grammar still supports imperative prefixes such as ``change
    wardrobe``. It rejects modals in that prefix slot, event words inserted
    inside a serial entity list, redundant event tails, and unrecognized names
    in temporal identity slots. These positional checks close the hole where an
    unknown character named ``May`` or ``Change`` was accepted merely because
    its spelling appeared in the global predicate allowlist.
    """
    positive_indexes = [
        index
        for index, token in enumerate(tokens)
        if token in TRANSITION_CHANGE_WORDS
        and index not in licensed_identity_indexes
    ]
    if len(positive_indexes) > 2:
        return True

    for group_index, group in enumerate(groups):
        field_start = group[0][0]
        if field_start == 0:
            continue
        candidate_index = field_start - 1
        if candidate_index in licensed_identity_indexes:
            continue
        candidate = tokens[candidate_index]
        if candidate in MODAL_OR_NONIMPERATIVE_PREFIX_WORDS:
            return True
        if candidate in {"of", "to"} and (
            candidate_index == 0
            or tokens[candidate_index - 1] not in LINKING_PREPOSITION_HEADS
        ):
            return True
        if candidate == "or" and (
            candidate_index == 0
            or tokens[candidate_index - 1] not in ALL_CLAUSE_PREDICATE_WORDS
        ):
            return True
        if group_index > 0 and candidate in TRANSITION_CHANGE_WORDS:
            return True

    for leader_index, leader in enumerate(tokens):
        if leader not in TEMPORAL_CONTEXT_LEADERS:
            continue
        for noun_index in range(leader_index + 1, min(len(tokens), leader_index + 6)):
            if tokens[noun_index] not in TEMPORAL_CONTEXT_NOUNS:
                continue
            candidate_indexes = [
                index
                for index in range(leader_index + 1, noun_index)
                if tokens[index] not in {"s", "the", "time"}
            ]
            if candidate_indexes and not all(
                index in licensed_identity_indexes for index in candidate_indexes
            ) and any(
                tokens[index] in TRANSITION_CHANGE_WORDS
                for index in candidate_indexes
            ):
                return True
            break
    return False


def has_unresolved_serial_identity_role(
    text: object,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None,
) -> bool:
    """Reject a redundant event word occupying an unknown serial entity slot.

    This check intentionally runs before semantic clause splitting. Consider
    ``allow changes to hero wardrobe, Change location, and extra product
    identity``: after splitting, ``Change location`` is a valid imperative in
    isolation and the other two clauses can survive. In the original serial
    construction, however, ``Change`` is redundant with the shared prefix and
    occupies exactly the position where a recognized identity would appear.

    A lone imperative remains supported. So does a genuinely independent pair
    such as ``change wardrobe and change location``. The fail-closed signal is
    the combination of an unresolved field-adjacent event word and another
    predicate outside the field list (a shared prefix or suffix).
    """
    for segment in text_segments(text, identity_aliases, alias_widths):
        tokens = normalize_phrase(segment).split()
        groups = field_groups(tokens)
        if len(groups) < 2:
            continue
        licensed_identity_indexes = identity_indexes_for_tokens(
            tokens,
            identity_aliases,
            alias_widths,
        )
        first_field_start = groups[0][0][0]
        final_field_end = groups[-1][-1][1]
        predicate_indexes = {
            index
            for index, token in enumerate(tokens)
            if token in ALL_CLAUSE_PREDICATE_WORDS
            and index not in licensed_identity_indexes
        }
        outside_predicate_indexes = {
            index
            for index in predicate_indexes
            if index < first_field_start or index >= final_field_end
        }

        unresolved_candidates: list[tuple[int, str]] = []
        for group in groups:
            field_start = group[0][0]
            if field_start == 0:
                continue
            candidate_index = field_start - 1
            if candidate_index in licensed_identity_indexes:
                continue
            candidate = tokens[candidate_index]
            if candidate in {"of", "to"} and (
                candidate_index == 0
                or tokens[candidate_index - 1] not in LINKING_PREPOSITION_HEADS
            ):
                return True
            if candidate == "or" and (
                candidate_index == 0
                or tokens[candidate_index - 1] not in ALL_CLAUSE_PREDICATE_WORDS
            ):
                return True
            if candidate in SERIAL_REDUNDANT_CONTEXT_WORDS and any(
                predicate_index < candidate_index
                for predicate_index in outside_predicate_indexes
            ):
                return True
            if (
                candidate in SERIAL_AMBIGUOUS_DETERMINERS
                and licensed_identity_indexes
                and any(
                    predicate_index < candidate_index
                    for predicate_index in outside_predicate_indexes
                )
            ):
                return True
            if candidate not in TRANSITION_CHANGE_WORDS:
                continue
            if candidate in MODAL_OR_NONIMPERATIVE_PREFIX_WORDS:
                return True
            unresolved_candidates.append((candidate_index, candidate))

        # Every field having its own imperative is an ordinary coordinated
        # command (``change wardrobe and change location``), not a serial
        # entity list. A trailing shared predicate would make those same words
        # redundant and therefore ambiguous again.
        suffix_predicate_indexes = {
            index for index in predicate_indexes if index >= final_field_end
        }
        if len(unresolved_candidates) == len(groups) and not suffix_predicate_indexes:
            continue

        for candidate_index, _candidate in unresolved_candidates:
            if outside_predicate_indexes - {candidate_index}:
                return True
    return False


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
    if len(tokens) > MAX_WAIVER_TOKENS:
        return False
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
    if has_suspicious_event_identity_role(
        tokens,
        groups,
        licensed_identity_indexes,
    ):
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
            unsafe = True
            continue
        for text in entries:
            if not isinstance(text, str):
                unsafe = True
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
    elif "transition_in" in clip:
        unsafe = True

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


def fallback_list_field_locator(
    structural_locator: tuple[object, ...],
) -> tuple[tuple[object, ...], IdentityToken] | None:
    """Return a container-independent locator for one fallback-identified field.

    Fallback list IDs are meaningful across harmless collection-key renames, but
    only when the same identity/field pair occurs exactly once on each side.
    ``comparable_values`` enforces that uniqueness before using this locator.
    """
    if len(structural_locator) < 3:
        return None
    field_segment = structural_locator[-1]
    if (
        not isinstance(field_segment, tuple)
        or len(field_segment) != 2
        or field_segment[0] != "key"
    ):
        return None
    for segment in reversed(structural_locator[1:-1]):
        if (
            isinstance(segment, tuple)
            and len(segment) == 4
            and segment[0] == "list-identity"
            and segment[1] != "canonical_identity_id"
        ):
            identity: IdentityToken = (segment[2], segment[3])
            return (
                (
                    "fallback-list-field",
                    segment[1],
                    *identity,
                    field_segment,
                ),
                identity,
            )
    return None


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

    end_fallback: dict[
        tuple[object, ...],
        list[tuple[tuple[object, ...], IdentityToken]],
    ] = {}
    start_fallback: dict[
        tuple[object, ...],
        list[tuple[tuple[object, ...], IdentityToken]],
    ] = {}
    for structural_locator in end_by_structural:
        fallback = fallback_list_field_locator(structural_locator)
        if fallback is not None:
            semantic_locator, identity = fallback
            end_fallback.setdefault(semantic_locator, []).append(
                (structural_locator, identity)
            )
    for structural_locator in start_by_structural:
        fallback = fallback_list_field_locator(structural_locator)
        if fallback is not None:
            semantic_locator, identity = fallback
            start_fallback.setdefault(semantic_locator, []).append(
                (structural_locator, identity)
            )

    matched_end_fallback: set[tuple[object, ...]] = set()
    matched_start_fallback: set[tuple[object, ...]] = set()
    for semantic_locator in sorted(
        end_fallback.keys() & start_fallback.keys(),
        key=repr,
    ):
        end_candidates = end_fallback[semantic_locator]
        start_candidates = start_fallback[semantic_locator]
        if len(end_candidates) != 1 or len(start_candidates) != 1:
            continue
        end_locator, end_identity = end_candidates[0]
        start_locator, start_identity = start_candidates[0]
        comparisons.append(
            (
                end_by_structural[end_locator][0],
                end_by_structural[end_locator][1],
                start_by_structural[start_locator][1],
                end_identity if end_identity == start_identity else None,
            )
        )
        matched_end_fallback.add(end_locator)
        matched_start_fallback.add(start_locator)

    end_by_structural = {
        locator: value
        for locator, value in end_by_structural.items()
        if locator not in matched_end_fallback
    }
    start_by_structural = {
        locator: value
        for locator, value in start_by_structural.items()
        if locator not in matched_start_fallback
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


def json_values_equal(left: object, right: object) -> bool:
    """Iteratively compare parsed JSON with a finite node budget."""
    pending: list[tuple[object, object]] = [(left, right)]
    compared = 0
    while pending:
        compared += 1
        if compared > MAX_JSON_COMPARE_NODES:
            return False
        left_value, right_value = pending.pop()
        if isinstance(left_value, bool) or isinstance(right_value, bool):
            if not (
                type(left_value) is bool
                and type(right_value) is bool
                and left_value == right_value
            ):
                return False
            continue
        if isinstance(left_value, (int, float, Decimal)) and isinstance(
            right_value, (int, float, Decimal)
        ):
            if left_value != right_value:
                return False
            continue
        if type(left_value) is not type(right_value):
            return False
        if isinstance(left_value, list):
            if len(left_value) != len(right_value):
                return False
            if len(left_value) > MAX_JSON_COMPARE_NODES - compared - len(pending):
                return False
            pending.extend(zip(left_value, right_value))
            continue
        if isinstance(left_value, dict):
            if left_value.keys() != right_value.keys():
                return False
            if len(left_value) > MAX_JSON_COMPARE_NODES - compared - len(pending):
                return False
            pending.extend(
                (left_value[key], right_value[key]) for key in left_value
            )
            continue
        if left_value != right_value:
            return False
    return True


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
                elif a is not None and b is not None and not json_values_equal(
                    a,
                    b,
                ) and not field_has_allowance(
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
                elif a is not None and b is not None and not json_values_equal(
                    a,
                    b,
                ) and not field_has_allowance(
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

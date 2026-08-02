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


def is_axis_reset(text: str) -> bool:
    return " axis reset " in f" {normalize_phrase(text)} "


def text_segments(text: object) -> list[str]:
    return [
        segment
        for segment in re.split(
            r"(?:[.;,\n]+|\bbut\b|\bhowever\b)",
            str(text),
            flags=re.IGNORECASE,
        )
        if normalize_phrase(segment)
    ]


def negates_field_change(text: str, key: str) -> bool:
    tokens = normalize_phrase(text).split()
    if set(tokens) & NEGATION_WORDS:
        return True
    if any(
        left in NEGATING_CONTRACTION_STEMS and right == "t"
        for left, right in zip(tokens, tokens[1:])
    ):
        return True

    for phrase in field_phrases(key):
        phrase_tokens = phrase.split()
        width = len(phrase_tokens)
        for index in range(len(tokens) - width + 1):
            if tokens[index : index + width] != phrase_tokens:
                continue
            before = tokens[max(0, index - 3) : index]
            after = tokens[index + width : index + width + 4]
            if set(before) & PRESERVATION_WORDS:
                return True
            if set(after) & PRESERVATION_WORDS:
                return True
    return False


def positively_mentions_field(text: object, key: str) -> bool:
    for segment in text_segments(text):
        if not mentions_field(segment, key) or negates_field_change(segment, key):
            continue
        normalized = normalize_phrase(segment)
        if normalized in field_phrases(key):
            return True
        if set(normalized.split()) & TRANSITION_CHANGE_WORDS:
            return True
    return False


def positively_resets_axis(text: object) -> bool:
    return any(
        is_axis_reset(segment)
        and not negates_field_change(segment, "travel_direction")
        and not (set(normalize_phrase(segment).split()) & NEGATION_WORDS)
        for segment in text_segments(text)
    )


def mentioned_identity_tokens(
    text: str,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None = None,
) -> tuple[set[IdentityToken], bool]:
    tokens = normalize_phrase(text).split()
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
    mentioned: set[IdentityToken] = set()
    ambiguous = False
    for start, end, _phrase, identities in candidates:
        span = set(range(start, end))
        if occupied & span:
            continue
        occupied.update(span)
        if len(identities) > 1:
            ambiguous = True
        mentioned.update(identities)
    return mentioned, ambiguous


def is_unqualified_global_waiver(text: str, key: str) -> bool:
    tokens = normalize_phrase(text).split()
    field_token_groups = [phrase.split() for phrase in field_phrases(key)]
    if key == "travel_direction":
        field_token_groups.append(["axis", "reset"])
    starts = [
        index
        for phrase_tokens in field_token_groups
        for index in range(len(tokens) - len(phrase_tokens) + 1)
        if tokens[index : index + len(phrase_tokens)] == phrase_tokens
    ]
    if not starts:
        return False
    prefix = set(tokens[: min(starts)])
    allowed_prefix = set(TRANSITION_CHANGE_WORDS) | GLOBAL_WAIVER_GRAMMAR
    return prefix <= allowed_prefix


def allowance_matches_scope(
    text: str,
    key: str,
    scope_identity: IdentityToken | None,
    identity_aliases: IdentityAliases,
    alias_widths: tuple[int, ...] | None = None,
) -> bool:
    mentioned, ambiguous = mentioned_identity_tokens(
        text,
        identity_aliases,
        alias_widths,
    )
    if ambiguous or len(mentioned) > 1:
        return False
    if not mentioned:
        return is_unqualified_global_waiver(text, key)
    return scope_identity is not None and scope_identity == next(iter(mentioned))


def has_allowance(
    clip: dict,
    key: str,
    *,
    scope_identity: IdentityToken | None = None,
    identity_aliases: IdentityAliases | None = None,
    alias_widths: tuple[int, ...] | None = None,
) -> bool:
    aliases = identity_aliases or {}
    for field in ("allowed_changes", "accepted_deviations", "continuity_breaks"):
        entries = clip.get(field, [])
        if not isinstance(entries, list):
            continue
        for text in entries:
            if not isinstance(text, str):
                continue
            for segment in text_segments(text):
                permits_field = positively_mentions_field(segment, key) or (
                    key == "travel_direction" and positively_resets_axis(segment)
                )
                if permits_field and allowance_matches_scope(
                    segment,
                    key,
                    scope_identity,
                    aliases,
                    alias_widths,
                ):
                    return True

    transition_value = clip.get("transition_in", "")
    if not isinstance(transition_value, str):
        return False
    for transition in text_segments(transition_value):
        normalized_transition = normalize_phrase(transition)
        permits_field = (
            key == "travel_direction" and positively_resets_axis(transition)
        ) or (
            mentions_field(transition, key)
            and not negates_field_change(transition, key)
            and bool(set(normalized_transition.split()) & TRANSITION_CHANGE_WORDS)
        )
        if permits_field and allowance_matches_scope(
            transition,
            key,
            scope_identity,
            aliases,
            alias_widths,
        ):
            return True
    return False


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
    comparisons.extend(
        (
            end_by_structural[locator][0],
            end_by_structural[locator][1],
            MISSING,
            end_by_structural[locator][2],
        )
        for locator in sorted(end_by_structural.keys() - shared_structural, key=repr)
    )
    comparisons.extend(
        (
            start_by_structural[locator][0],
            MISSING,
            start_by_structural[locator][1],
            start_by_structural[locator][2],
        )
        for locator in sorted(start_by_structural.keys() - shared_structural, key=repr)
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

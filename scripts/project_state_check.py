#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
from decimal import Decimal
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

if __package__:
    from .behavior_contract_check import (
        creative_specificity_errors,
        utility_prompt_relevance_errors,
    )
    from .lineage_contract import (
        ACCEPTED_PARENT_STATUSES,
        analyze_lineage,
        build_take_review_indexes,
        bound_validation_diagnostics,
        classify_parent_id,
        json_integer,
        has_usable_observed_end_state,
        is_take_review_path,
        load_bounded_take_review,
        load_project_document,
        TakeReviewIndex,
        validate_take_review_record,
        validate_take_reconciliation,
    )
    from .strict_json import (
        bound_diagnostics,
        diagnostic_path,
        diagnostic_text,
        load_json as load_strict_json,
        read_repo_text,
        validate_repo_input_path,
    )
else:
    from behavior_contract_check import (
        creative_specificity_errors,
        utility_prompt_relevance_errors,
    )
    from lineage_contract import (
        ACCEPTED_PARENT_STATUSES,
        analyze_lineage,
        build_take_review_indexes,
        bound_validation_diagnostics,
        classify_parent_id,
        json_integer,
        has_usable_observed_end_state,
        is_take_review_path,
        load_bounded_take_review,
        load_project_document,
        TakeReviewIndex,
        validate_take_review_record,
        validate_take_reconciliation,
    )
    from strict_json import (
        bound_diagnostics,
        diagnostic_path,
        diagnostic_text,
        load_json as load_strict_json,
        read_repo_text,
        validate_repo_input_path,
    )


REQUIRED_PROJECT_FIELDS = {
    "schema_version", "state_revision", "project_id", "project_mode", "surface",
    "clip_budget_sec", "prompt_budget", "story", "world_bible", "reference_registry",
    "scenes", "beats", "clips", "take_history", "current_clip_id", "canon_revision", "updated_at",
}
REQUIRED_SCENE_FIELDS = {
    "scene_id", "scene_index", "narrative_function", "arc_position", "location",
    "time_of_day", "anchor_source", "max_chain_depth", "audio_plan",
    "assigned_clip_ids", "transition_out", "status",
}
ARC_POSITIONS = {"open", "rising", "turn", "climax", "release"}
SCENE_STATUSES = {"planned", "current", "completed", "omitted", "replaced"}
MAX_CHAIN_DEPTH_CEILING = 3
REQUIRED_STORY_FIELDS = {
    "logline", "story_promise", "objective", "initial_condition", "final_outcome",
    "target_duration_sec", "tone", "medium",
}
REQUIRED_BEAT_FIELDS = {
    "beat_id", "description", "narrative_function", "status", "assigned_clip_id", "dependencies",
}
REQUIRED_CLIP_FIELDS = {
    "clip_id", "scene_id", "sequence_index", "prompt_version", "generation_mode",
    "status", "narrative_job", "felt_intent", "already_happened", "this_clip_only", "reserved_for_later",
    "planned_start_state", "planned_end_state", "observed_start_state", "observed_end_state",
    "continuity_locks", "allowed_changes", "continuity_breaks", "accepted_deviations",
    "transition_in", "transition_out", "open_motion_vectors", "handoff_requirements",
    "extension_depth",
}
REQUIRED_CLIP_CONTRACT_FIELDS = {
    "project_id", "clip_id", "scene_id", "sequence_index", "narrative_job", "felt_intent",
    "target_duration_sec", "generation_mode", "shot_structure", "already_happened",
    "this_clip_only", "reserved_for_later", "planned_start_state", "planned_end_state",
    "continuity_locks", "allowed_changes", "status",
}
REQUIRED_TAKE_REVIEW_FIELDS = {
    "project_id", "clip_id", "take_id", "source_status", "verdict",
    "observed_start_state", "observed_end_state", "completed_beats", "incomplete_beats",
    "unexpected_completed_beats", "continuity_breaks", "accepted_deviations",
    "observation_confidence", "uncertainties", "requires_user_confirmation",
}
ACCEPTED = {"accepted", "accepted_with_deviation"}
HISTORICAL_CONTRACT_STATUSES = {"accepted", "accepted_with_deviation", "rejected"}
CURRENT_CONTRACT_STATUSES = {"planned", "ready", "generated", "reviewed", "repair"}
CONTRACT_STATUSES = HISTORICAL_CONTRACT_STATUSES | CURRENT_CONTRACT_STATUSES
NARRATIVE_AUTHORING_FIELDS = {
    "dramatic_function", "turn", "pov", "power_shift", "hidden_want_objective",
    "obstacle_tactic", "subtext_contradiction", "visible_suppressed_behavior",
    "non_transferable_detail", "non_transferable_detail_provenance",
    "non_transferable_detail_source",
    "stock_solution_refused", "value_before", "value_after", "prompt_carriers",
}
NON_NARRATIVE_AUTHORING_FIELDS = {"utility_intent", "non_narrative_refusal"}
AUTHORING_STATE_FIELDS = NARRATIVE_AUTHORING_FIELDS | NON_NARRATIVE_AUTHORING_FIELDS
AUTHORING_TEXT_FIELDS = AUTHORING_STATE_FIELDS - {
    "prompt_carriers", "non_transferable_detail_source",
}
NON_TRANSFERABLE_PROVENANCE = {"source_bound", "authored_choice"}
DIRECTORS_READ_LANES = {"narrative", "non_narrative"}
AUTHORING_STATE_PROVENANCE_FIELDS = {
    "project_id", "clip_id", "canon_revision", "state_revision", "authoring_state_sha256",
}
SOURCE_EVIDENCE_RE = re.compile(
    r"^(?:@[a-z][a-z0-9]*(?:[ \t]+\d+)?|\[[^\]\r\n]+\]|https?://\S+|(?:file|ref|evidence):\S+)$",
    re.IGNORECASE,
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROVENANCE_LEDGER_RELATIVE_PATH = Path("validation/authoring-state-provenance-ledger.json")
PROVENANCE_LEDGER_SCHEMA_VERSION = "1.0"
PROVENANCE_LEDGER_REVISION = 1
PROVENANCE_LEDGER_SHA256 = "8b195e875a30a0c560e6ef48c64079451d80512cff04f168e28ddd64591cb870"
PROVENANCE_LEDGER_FIELDS = {
    "schema_version", "ledger_revision", "append_only", "entries",
}
PROVENANCE_LEDGER_ENTRY_FIELDS = {
    "entry_sequence", "project_id", "clip_id", "canon_revision", "state_revision",
    "contract_status", "authoring_state_sha256", "contract_sha256", "prompt_sha256",
}
AUTHORING_LABEL_ALIASES = {
    "dramatic_function": ("dramatic function",),
    "turn": ("turn",),
    "pov": ("pov", "point of view"),
    "power_shift": ("power shift",),
    "hidden_want_objective": ("hidden want/objective", "hidden want", "objective"),
    "obstacle_tactic": ("obstacle/tactic", "obstacle", "tactic"),
    "subtext_contradiction": ("subtext/contradiction", "subtext", "contradiction"),
    "visible_suppressed_behavior": ("visible suppressed behavior",),
    "non_transferable_detail": ("non-transferable detail", "non transferable detail"),
    "non_transferable_detail_provenance": (
        "non-transferable detail provenance", "non transferable detail provenance",
    ),
    "non_transferable_detail_source": (
        "non-transferable detail source", "non transferable detail source",
    ),
    "stock_solution_refused": ("stock solution refused",),
    "value_before": ("value before",),
    "value_after": ("value after",),
    "prompt_carriers": ("prompt carriers",),
    "utility_intent": ("utility intent",),
    "non_narrative_refusal": ("non-narrative refusal", "non narrative refusal"),
    "authoring_state_provenance": ("authoring state provenance",),
    "authoring_state_sha256": ("authoring state sha256", "authoring state digest"),
    "canon_revision": ("canon revision",),
    "state_revision": ("state revision",),
}


def load_json(path: Path, root: Path | None = None) -> object:
    return load_strict_json(path, root=root)


def is_string_enum(value: object, allowed: set[str]) -> bool:
    """Contain wrong JSON types before set membership and report them normally."""
    return isinstance(value, str) and value in allowed


def load_protected_provenance_ledger(
    root: Path,
    errors: list[str],
) -> dict[tuple[str, str, int, int], dict] | None:
    """Load the append-only historical contract ledger and verify its independent pin."""
    start_error_count = len(errors)
    path = root / PROVENANCE_LEDGER_RELATIVE_PATH
    label = PROVENANCE_LEDGER_RELATIVE_PATH.as_posix()
    try:
        ledger = load_json(path, root=root)
    except Exception as exc:
        errors.append(f"{label}: missing or invalid protected provenance ledger: {exc}")
        return None
    if not isinstance(ledger, dict):
        errors.append(f"{label}: protected provenance ledger must be an object")
        return None

    missing = sorted(PROVENANCE_LEDGER_FIELDS - set(ledger))
    extra = sorted(set(ledger) - PROVENANCE_LEDGER_FIELDS)
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"{label}: unknown fields: {', '.join(extra)}")
    if ledger.get("schema_version") != PROVENANCE_LEDGER_SCHEMA_VERSION:
        errors.append(
            f"{label}: schema_version must be {PROVENANCE_LEDGER_SCHEMA_VERSION}"
        )
    if ledger.get("ledger_revision") != PROVENANCE_LEDGER_REVISION:
        errors.append(
            f"{label}: ledger_revision must remain pinned at {PROVENANCE_LEDGER_REVISION}"
        )
    if ledger.get("append_only") is not True:
        errors.append(f"{label}: append_only must be true")
    actual_digest = canonical_json_digest(ledger)
    if actual_digest != PROVENANCE_LEDGER_SHA256:
        errors.append(
            f"{label}: protected ledger digest {actual_digest} does not match pinned "
            f"digest {PROVENANCE_LEDGER_SHA256}; ledger refresh requires an explicit "
            "reviewed pin change"
        )

    entries = ledger.get("entries")
    if not isinstance(entries, list):
        errors.append(f"{label}: entries must be an array")
        return None
    indexed: dict[tuple[str, str, int, int], dict] = {}
    for index, entry in enumerate(entries, start=1):
        entry_label = f"{label}: entries[{index - 1}]"
        if not isinstance(entry, dict):
            errors.append(f"{entry_label} must be an object")
            continue
        missing = sorted(PROVENANCE_LEDGER_ENTRY_FIELDS - set(entry))
        extra = sorted(set(entry) - PROVENANCE_LEDGER_ENTRY_FIELDS)
        if missing:
            errors.append(f"{entry_label} missing fields: {', '.join(missing)}")
        if extra:
            errors.append(f"{entry_label} unknown fields: {', '.join(extra)}")
        entry_sequence = entry.get("entry_sequence")
        if (
            not isinstance(entry_sequence, int)
            or isinstance(entry_sequence, bool)
            or entry_sequence != index
        ):
            errors.append(f"{entry_label} entry_sequence must be append-only position {index}")
        project_id = entry.get("project_id")
        clip_id = entry.get("clip_id")
        canon_revision = entry.get("canon_revision")
        state_revision = entry.get("state_revision")
        if not has_visible_text(project_id) or not is_one_line_text(project_id):
            errors.append(f"{entry_label} project_id must be a non-empty string")
        if not has_visible_text(clip_id) or not is_one_line_text(clip_id):
            errors.append(f"{entry_label} clip_id must be a non-empty string")
        for field, value in (
            ("canon_revision", canon_revision),
            ("state_revision", state_revision),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                errors.append(f"{entry_label} {field} must be an integer >= 1")
        for field in ("authoring_state_sha256", "contract_sha256", "prompt_sha256"):
            value = entry.get(field)
            if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
                errors.append(f"{entry_label} {field} must be 64 lowercase hex characters")
        if not is_string_enum(entry.get("contract_status"), HISTORICAL_CONTRACT_STATUSES):
            errors.append(f"{entry_label} contract_status must be terminal/historical")
        if (
            isinstance(project_id, str)
            and isinstance(clip_id, str)
            and isinstance(canon_revision, int)
            and not isinstance(canon_revision, bool)
            and isinstance(state_revision, int)
            and not isinstance(state_revision, bool)
        ):
            key = (project_id, clip_id, canon_revision, state_revision)
            if key in indexed:
                errors.append(f"{entry_label} duplicates historical provenance key {key}")
            indexed[key] = entry

    if len(errors) != start_error_count:
        return None
    return indexed


def check_required(obj: dict, required: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(required - set(obj))
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(missing)}")


def checked_string_array(value: object, label: str, errors: list[str]) -> set[str]:
    """Return safe set semantics while retaining diagnostics for malformed JSON."""

    if not isinstance(value, list):
        errors.append(f"{label} must be an array of strings")
        return set()
    values: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{label}[{index}] must be a non-empty string")
            continue
        values.add(item)
    return values


DEFAULT_IGNORABLE_RANGES = (
    (0x034F, 0x034F),
    (0x115F, 0x1160),
    (0x17B4, 0x17B5),
    (0x180B, 0x180F),
    (0x2800, 0x2800),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFFA0, 0xFFA0),
    (0xFFF0, 0xFFF8),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)
HTML_COMMENT_RE = re.compile(r"<!--(?:.*?-->|.*\Z)", re.DOTALL)
FRONT_MATTER_RE = re.compile(
    r"\A\ufeff?---[ \t]*(?:\r\n?|\n).*?(?:\r\n?|\n)"
    r"(?:---|\.\.\.)[ \t]*(?:(?:\r\n?|\n)|\Z)",
    re.DOTALL,
)


def is_default_ignorable(character: str) -> bool:
    """Return True for format/default-ignorable code points with no visible value."""
    if unicodedata.category(character) == "Cf":
        return True
    codepoint = ord(character)
    return any(start <= codepoint <= end for start, end in DEFAULT_IGNORABLE_RANGES)


def has_visible_text(value: object) -> bool:
    """Require a visible letter, number, or symbol beyond spacing/format tricks."""
    if not isinstance(value, str):
        return False
    for character in unicodedata.normalize("NFKC", value):
        category = unicodedata.category(character)
        if character.isspace() or is_default_ignorable(character):
            continue
        if category[0] in {"L", "N", "S"}:
            return True
    return False


LINE_BREAK_CHARACTERS = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")


def is_one_line_text(value: object) -> bool:
    return isinstance(value, str) and not any(
        character in LINE_BREAK_CHARACTERS for character in value
    )


def source_evidence_has_visible_payload(value: str) -> bool:
    """Require content after a locator wrapper, not merely a visible prefix."""
    stripped = value.strip()
    if stripped.startswith("@"):
        payload = stripped[1:]
    elif stripped.startswith("[") and stripped.endswith("]"):
        payload = stripped[1:-1]
    elif "://" in stripped:
        payload = stripped.split("://", 1)[1]
    elif ":" in stripped:
        payload = stripped.split(":", 1)[1]
    else:
        return False
    return has_visible_text(payload)


def normalized_dramatic_value(value: str) -> str:
    """Normalize differences that cannot constitute a dramatic value change."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(
        character
        for character in normalized
        if not character.isspace()
        and not unicodedata.category(character).startswith("P")
        and not is_default_ignorable(character)
    )


def canonical_json_digest(value: object) -> str:
    payload = canonical_json_text(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_json_text(value: object) -> str:
    """Serialize strict-JSON values without converting Decimal through binary float."""

    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("canonical JSON does not allow a non-finite Decimal")
        return str(value)
    if isinstance(value, float):
        return json.dumps(value, allow_nan=False, separators=(",", ":"))
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonical_json_text(item) for item in value) + "]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical JSON object keys must be strings")
        return "{" + ",".join(
            f"{json.dumps(key, ensure_ascii=False)}:{canonical_json_text(value[key])}"
            for key in sorted(value)
        ) + "}"
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def authoring_state_digest(state: dict) -> str:
    return canonical_json_digest(state)


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


NON_RENDERED_HTML_TAGS = {
    "canvas", "code", "desc", "head", "iframe", "link", "metadata", "meta",
    "noscript", "pre", "script", "style", "template", "textarea", "title",
}
VOID_HTML_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
}
RAW_HTML_BLOCK_TAGS = {
    "address", "article", "aside", "base", "basefont", "blockquote", "body",
    "caption", "center", "col", "colgroup", "dd", "details", "dialog", "dir",
    "div", "dl", "dt", "fieldset", "frame",
    "figcaption", "figure", "footer", "form", "frameset", "h1", "h2", "h3", "h4",
    "h5", "h6", "head", "header", "hr", "html", "iframe", "legend", "li",
    "link", "main", "menu", "menuitem", "nav", "noframes", "noscript", "ol",
    "optgroup", "option", "p", "param", "pre", "script", "search", "section",
    "style", "summary", "table",
    "tbody", "td", "textarea", "tfoot", "th", "thead", "title", "tr", "track", "ul",
}
class RenderedHTMLTextExtractor(HTMLParser):
    """Extract visible text with quote-aware tags and a nesting-aware hidden stack."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.stack: list[tuple[str, bool, bool, bool, bool, bool]] = []
        self.hidden_depth = 0
        self.closed_details_depth = 0
        self.summary_reveal_depth = 0
        self.raw_markdown_depth = 0
        self.stylesheet_control_seen = False
        self.non_rendered_lines: set[int] = set()
        self.non_markdown_lines: set[int] = set()

    @staticmethod
    def element_is_hidden(tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag in NON_RENDERED_HTML_TAGS:
            return True
        attributes: dict[str, str | None] = {}
        for name, value in attrs:
            attributes[name.casefold()] = value
        if "hidden" in attributes:
            return True
        aria_hidden = attributes.get("aria-hidden")
        if isinstance(aria_hidden, str) and aria_hidden.strip().casefold() == "true":
            return True
        if "style" in attributes:
            return True
        if tag == "dialog" and "open" not in attributes:
            return True
        return False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        folded_tag = tag.casefold()
        attributes = {name.casefold(): value for name, value in attrs}
        if folded_tag == "style" or (
            folded_tag == "link"
            and isinstance(attributes.get("rel"), str)
            and "stylesheet" in attributes["rel"].casefold().split()
        ):
            self.stylesheet_control_seen = True
        hidden = self.element_is_hidden(folded_tag, attrs)
        if folded_tag in VOID_HTML_TAGS:
            return
        raw_block = folded_tag in RAW_HTML_BLOCK_TAGS
        closed_details = folded_tag == "details" and "open" not in attributes
        summary_reveal = (
            folded_tag == "summary"
            and bool(self.stack)
            and self.stack[-1][0] == "details"
            and self.stack[-1][2]
            and not self.stack[-1][4]
        )
        if summary_reveal:
            (
                parent_tag,
                parent_hidden,
                parent_closed,
                parent_reveal,
                _,
                parent_raw,
            ) = self.stack[-1]
            self.stack[-1] = (
                parent_tag,
                parent_hidden,
                parent_closed,
                parent_reveal,
                True,
                parent_raw,
            )
        self.stack.append(
            (folded_tag, hidden, closed_details, summary_reveal, False, raw_block)
        )
        if hidden:
            self.hidden_depth += 1
        if closed_details:
            self.closed_details_depth += 1
        if summary_reveal:
            self.summary_reveal_depth += 1
        if raw_block:
            self.raw_markdown_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in VOID_HTML_TAGS:
            attributes = {name.casefold(): value for name, value in attrs}
            if (
                tag.casefold() == "link"
                and isinstance(attributes.get("rel"), str)
                and "stylesheet" in attributes["rel"].casefold().split()
            ):
                self.stylesheet_control_seen = True
        else:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        folded_tag = tag.casefold()
        matching_index = next(
            (
                index
                for index in range(len(self.stack) - 1, -1, -1)
                if self.stack[index][0] == folded_tag
            ),
            None,
        )
        if matching_index is None:
            return
        for _, hidden, closed_details, summary_reveal, _, raw_block in self.stack[
            matching_index:
        ]:
            if hidden:
                self.hidden_depth -= 1
            if closed_details:
                self.closed_details_depth -= 1
            if summary_reveal:
                self.summary_reveal_depth -= 1
            if raw_block:
                self.raw_markdown_depth -= 1
        del self.stack[matching_index:]

    def handle_data(self, data: str) -> None:
        start_line = self.getpos()[0]
        line_break_count = len(re.findall(r"\r\n?|\n", data))
        line_range = range(start_line, start_line + line_break_count + 1)
        if self.raw_markdown_depth:
            self.non_markdown_lines.update(line_range)
        visible = (
            self.hidden_depth == 0
            and self.closed_details_depth == self.summary_reveal_depth
        )
        if visible:
            self.output.append(data)
        else:
            self.non_rendered_lines.update(line_range)

    def handle_comment(self, data: str) -> None:
        return

    def handle_decl(self, decl: str) -> None:
        return

    def handle_pi(self, data: str) -> None:
        return


class HTMLDataExtractor(HTMLParser):
    """Drop tags while retaining every data body for global label rejection."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []

    def handle_data(self, data: str) -> None:
        self.output.append(data)


def strip_html_tags_keep_data(text: str) -> str:
    parser = HTMLDataExtractor()
    parser.feed(text)
    parser.close()
    return "".join(parser.output)


def strip_html_metadata(text: str) -> str:
    parser = inspect_html_visibility(text)
    if parser.stylesheet_control_seen:
        return ""
    return "".join(parser.output)


def inspect_html_visibility(text: str) -> RenderedHTMLTextExtractor:
    parser = RenderedHTMLTextExtractor()
    parser.feed(text)
    parser.close()
    return parser


def is_markdown_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


MARKDOWN_ESCAPABLE_PUNCTUATION = frozenset(
    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
)


def markdown_punctuation_escape_at(text: str, index: int) -> bool:
    return (
        index + 1 < len(text)
        and text[index] == "\\"
        and text[index + 1] in MARKDOWN_ESCAPABLE_PUNCTUATION
    )


MARKDOWN_BLANK_LINE_RE = re.compile(r"(?:\r\n?|\n)[ \t]*(?:\r\n?|\n)")


def markdown_component_whitespace_is_valid(value: str) -> bool:
    """Allow spaces/tabs and at most one CR, LF, or CRLF component break."""
    if any(character not in " \t\r\n" for character in value):
        return False
    line_endings = re.findall(r"\r\n?|\n", value)
    without_line_endings = re.sub(r"\r\n?|\n", "", value)
    return len(line_endings) <= 1 and all(
        character in " \t" for character in without_line_endings
    )


def markdown_title_is_valid(candidate: str) -> bool:
    closer = reference_title_closer(candidate)
    if closer is None or MARKDOWN_BLANK_LINE_RE.search(candidate):
        return False
    closer_index = escaped_title_closer_index(candidate, closer)
    return closer_index is not None and markdown_component_whitespace_is_valid(
        candidate[closer_index + 1:]
    )


def inline_link_payload_is_valid(payload: str) -> bool:
    """Validate a CommonMark-like destination/title before treating it as metadata."""
    leading_length = len(payload) - len(payload.lstrip(" \t\r\n"))
    leading = payload[:leading_length]
    if not markdown_component_whitespace_is_valid(leading):
        return False
    content = payload[leading_length:]
    if not content:
        return True

    cursor = 0
    if content[0] == "<":
        cursor = 1
        escaped = False
        while cursor < len(content):
            character = content[cursor]
            if escaped:
                escaped = False
            elif character == "\\" and markdown_punctuation_escape_at(content, cursor):
                escaped = True
            elif character in "\r\n" or character == "<":
                return False
            elif character == ">":
                cursor += 1
                break
            cursor += 1
        else:
            return False
    else:
        paren_depth = 0
        escaped = False
        while cursor < len(content):
            character = content[cursor]
            if escaped:
                escaped = False
            elif character == "\\" and markdown_punctuation_escape_at(content, cursor):
                escaped = True
            elif character in " \t\r\n":
                break
            elif ord(character) < 0x20:
                return False
            elif character.isspace():
                return False
            elif character == "(":
                paren_depth += 1
                if paren_depth > 32:
                    return False
            elif character == ")":
                if paren_depth == 0:
                    return False
                paren_depth -= 1
            cursor += 1
        if paren_depth:
            return False

    trailing = content[cursor:]
    separator_length = len(trailing) - len(trailing.lstrip(" \t\r\n"))
    separator = trailing[:separator_length]
    if not markdown_component_whitespace_is_valid(separator):
        return False
    candidate = trailing[separator_length:]
    if not candidate:
        return True
    if not separator:
        return False
    return markdown_title_is_valid(candidate)


def strip_inline_markdown_links(text: str) -> str:
    """Keep visible link text while removing escape-aware destinations and titles."""
    output: list[str] = []
    index = 0
    while index < len(text):
        escaped = is_markdown_escaped(text, index)
        image = text.startswith("![", index) and not escaped
        if image:
            bracket_start = index + 1
        elif text[index] == "[" and not escaped:
            bracket_start = index
        else:
            output.append(text[index])
            index += 1
            continue

        cursor = bracket_start + 1
        bracket_depth = 1
        while cursor < len(text) and bracket_depth:
            if markdown_punctuation_escape_at(text, cursor):
                cursor += 2
                continue
            if text[cursor] == "[":
                bracket_depth += 1
            elif text[cursor] == "]":
                bracket_depth -= 1
            cursor += 1
        if bracket_depth or cursor >= len(text) or text[cursor] != "(":
            output.append(text[index])
            index += 1
            continue

        label_end = cursor - 1
        cursor += 1
        paren_depth = 1
        quote: str | None = None
        while cursor < len(text) and paren_depth:
            character = text[cursor]
            if markdown_punctuation_escape_at(text, cursor):
                cursor += 2
                continue
            if quote is not None:
                if character == quote:
                    quote = None
                cursor += 1
                continue
            if (
                character in {"\"", "'"}
                and paren_depth == 1
                and (cursor == label_end + 2 or text[cursor - 1].isspace())
            ):
                quote = character
            elif character == "(":
                paren_depth += 1
            elif character == ")":
                paren_depth -= 1
            cursor += 1
        if paren_depth:
            output.append(text[index])
            index += 1
            continue
        payload = text[label_end + 2:cursor - 1]
        if not inline_link_payload_is_valid(payload):
            output.append(text[index])
            index += 1
            continue

        if not image:
            output.append(text[bracket_start + 1:label_end])
        index = cursor
    return "".join(output)


def normalize_markdown_reference_label(label: str) -> str:
    return re.sub(r"[ \t\r\n]+", " ", label).strip(" \t\r\n").casefold()


def strip_markdown_reference_images(text: str, definitions: set[str]) -> str:
    """Remove alt metadata only for image references that actually resolve."""
    output: list[str] = []
    index = 0
    while index < len(text):
        if not text.startswith("![", index) or is_markdown_escaped(text, index):
            output.append(text[index])
            index += 1
            continue
        cursor = index + 2
        bracket_depth = 1
        while cursor < len(text) and bracket_depth:
            if markdown_punctuation_escape_at(text, cursor):
                cursor += 2
                continue
            if text[cursor] == "[":
                bracket_depth += 1
            elif text[cursor] == "]":
                bracket_depth -= 1
            cursor += 1
        if bracket_depth:
            output.append(text[index])
            index += 1
            continue
        alt_text = text[index + 2:cursor - 1]
        reference_end = cursor
        reference_label = alt_text
        if cursor < len(text) and text[cursor] == "[":
            label_cursor = cursor + 1
            label_end: int | None = None
            invalid_label = False
            while label_cursor < len(text):
                if markdown_punctuation_escape_at(text, label_cursor):
                    label_cursor += 2
                    continue
                if text[label_cursor] == "[":
                    invalid_label = True
                if text[label_cursor] == "]":
                    label_end = label_cursor
                    break
                label_cursor += 1
            if label_end is None:
                output.append(text[index])
                index += 1
                continue
            explicit_label = text[cursor + 1:label_end]
            reference_label = explicit_label or alt_text
            reference_end = label_end + 1
            if invalid_label:
                output.append(text[index:reference_end])
                index = reference_end
                continue
        if (
            len(reference_label) <= 999
            and normalize_markdown_reference_label(reference_label) in definitions
        ):
            index = reference_end
        else:
            output.append(text[index:reference_end])
            index = reference_end
    return "".join(output)


MARKDOWN_CONTAINER_PREFIX_RE = re.compile(
    r"^ {0,3}(?:>[ \t]?|(?:[-+*]|[0-9]{1,9}[.)])[ \t]+)"
)
MARKDOWN_BLOCKQUOTE_PREFIX_RE = re.compile(r"^ {0,3}>[ \t]?")


def markdown_indentation_columns(text: str) -> int:
    """Return CommonMark-style columns for a short whitespace/prefix fragment."""
    columns = 0
    for character in text:
        if character == "\t":
            columns += 4 - (columns % 4)
        else:
            columns += 1
    return columns


def markdown_container_details(
    line: str,
) -> tuple[str, tuple[str, ...], tuple[tuple[str, int], ...]]:
    """Split visible content from its quote/list container continuation contract."""
    content = line
    signature: list[str] = []
    context: list[tuple[str, int]] = []
    while True:
        match = MARKDOWN_CONTAINER_PREFIX_RE.match(content)
        if match is None:
            return content, tuple(signature), tuple(context)
        raw_prefix = match.group(0)
        prefix = raw_prefix.lstrip(" ")
        if prefix.startswith(">"):
            signature.append(">")
            context.append(("quote", 0))
        else:
            signature.append(prefix.split()[0])
            context.append(("list", markdown_indentation_columns(raw_prefix)))
        content = content[match.end():]


def consume_markdown_indentation(text: str, required_columns: int) -> str | None:
    """Consume enough leading whitespace to continue a list-item container."""
    columns = 0
    index = 0
    while index < len(text) and text[index] in " \t" and columns < required_columns:
        if text[index] == "\t":
            columns += 4 - (columns % 4)
        else:
            columns += 1
        index += 1
    if columns < required_columns:
        return None
    return text[index:]


def markdown_same_container_continuation(
    context: tuple[tuple[str, int], ...] | None,
    line: str,
) -> bool:
    """Whether line continues one block container rather than entering a sibling."""
    if context is None:
        return False
    remainder = line
    for kind, required_columns in context:
        if kind == "quote":
            match = MARKDOWN_BLOCKQUOTE_PREFIX_RE.match(remainder)
            if match is None:
                return False
            remainder = remainder[match.end():]
        else:
            remainder = consume_markdown_indentation(remainder, required_columns)
            if remainder is None:
                return False
    # A fresh marker here enters a nested or sibling block; it cannot continue
    # the same link-reference definition or its optional continuation title.
    return MARKDOWN_CONTAINER_PREFIX_RE.match(remainder) is None


def strip_markdown_container_prefix_with_signature(line: str) -> tuple[str, tuple[str, ...]]:
    content, signature, _ = markdown_container_details(line)
    return content, signature


def strip_markdown_container_prefix(line: str) -> str:
    return strip_markdown_container_prefix_with_signature(line)[0]


def reference_title_closer(line: str) -> str | None:
    """Return a CommonMark continuation-title closer for an eligible next line."""
    candidate = line.lstrip(" \t")
    if not candidate:
        return None
    return {"\"": "\"", "'": "'", "(": ")"}.get(candidate[0])


def escaped_title_closer_index(text: str, closer: str, *, start: int = 1) -> int | None:
    escaped = False
    for index, character in enumerate(text[start:], start=start):
        if escaped:
            escaped = False
        elif character == "\\" and markdown_punctuation_escape_at(text, index):
            escaped = True
        elif character == closer:
            return index
    return None


def markdown_reference_definition_prefix(content: str) -> tuple[str, str] | None:
    """Split a definition at its first unescaped closing label bracket."""
    indent = re.match(r"^ {0,3}", content)
    if indent is None:
        return None
    cursor = indent.end()
    if cursor >= len(content) or content[cursor] != "[":
        return None
    cursor += 1
    label_start = cursor
    escaped = False
    while cursor < len(content):
        character = content[cursor]
        if escaped:
            escaped = False
        elif character == "\\" and markdown_punctuation_escape_at(content, cursor):
            escaped = True
        elif character == "[":
            return None
        elif character == "]":
            break
        elif character in "\r\n":
            return None
        cursor += 1
    if cursor >= len(content) or cursor + 1 >= len(content) or content[cursor + 1] != ":":
        return None
    return content[label_start:cursor], content[cursor + 2:].lstrip(" \t")


def markdown_reference_open_label(content: str) -> str | None:
    """Return an unfinished first-line label fragment, or None if it is invalid."""
    indent = re.match(r"^ {0,3}", content)
    if indent is None:
        return None
    cursor = indent.end()
    if cursor >= len(content) or content[cursor] != "[":
        return None
    cursor += 1
    label_start = cursor
    while cursor < len(content):
        if markdown_punctuation_escape_at(content, cursor):
            cursor += 2
            continue
        if content[cursor] in "[]\r\n":
            return None
        cursor += 1
    return content[label_start:]


def markdown_reference_label_continuation(
    content: str,
) -> tuple[str, str | None, bool]:
    """Scan a later label line: fragment, remainder on close, invalid flag."""
    cursor = 0
    while cursor < len(content):
        if markdown_punctuation_escape_at(content, cursor):
            cursor += 2
            continue
        character = content[cursor]
        if character == "[":
            return content[:cursor], None, True
        if character == "]":
            if cursor + 1 < len(content) and content[cursor + 1] == ":":
                return content[:cursor], content[cursor + 2:].lstrip(" \t"), False
            return content[:cursor], None, True
        if character in "\r\n":
            return content[:cursor], None, True
        cursor += 1
    return content, None, False


def markdown_reference_payload(
    label: str,
    remainder: str,
) -> tuple[str, bool, str | None] | None:
    """Parse the destination/title portion after a validated reference label."""
    if not remainder:
        return None

    cursor = 0
    if remainder[0] == "<":
        cursor = 1
        escaped = False
        while cursor < len(remainder):
            character = remainder[cursor]
            if escaped:
                escaped = False
            elif character == "\\" and markdown_punctuation_escape_at(remainder, cursor):
                escaped = True
            elif character == "<":
                return None
            elif character == ">":
                cursor += 1
                break
            cursor += 1
        else:
            return None
    else:
        paren_depth = 0
        escaped = False
        while cursor < len(remainder):
            character = remainder[cursor]
            if escaped:
                escaped = False
            elif character == "\\" and markdown_punctuation_escape_at(remainder, cursor):
                escaped = True
            elif character in " \t\r\n":
                break
            elif ord(character) < 0x20:
                return None
            elif character.isspace():
                return None
            elif character == "(":
                paren_depth += 1
                if paren_depth > 32:
                    return None
            elif character == ")":
                if paren_depth == 0:
                    return None
                paren_depth -= 1
            cursor += 1
        if cursor == 0 or paren_depth:
            return None

    trailing = remainder[cursor:]
    separator_length = len(trailing) - len(trailing.lstrip(" \t\r\n"))
    separator = trailing[:separator_length]
    if not markdown_component_whitespace_is_valid(separator):
        return None
    candidate = trailing[separator_length:]
    if not candidate:
        return label, True, None
    if not separator:
        return None
    closer = reference_title_closer(candidate)
    if closer is None:
        return None
    closer_index = escaped_title_closer_index(candidate, closer)
    if closer_index is None:
        return label, False, closer
    if not markdown_component_whitespace_is_valid(candidate[closer_index + 1:]):
        return None
    return label, False, None


def lf_lines_with_endings(text: str) -> list[str]:
    """Split only normalized LF boundaries; VT/FF/etc. remain literal content."""
    parts = text.split("\n")
    return [
        part + ("\n" if index < len(parts) - 1 else "")
        for index, part in enumerate(parts)
        if part or index < len(parts) - 1
    ]


def markdown_fence_marker(content: str) -> tuple[str, str] | None:
    match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", content)
    if match is None:
        return None
    marker, tail = match.groups()
    if marker[0] == "`" and "`" in tail:
        return None
    return marker, tail


def markdown_raw_html_block_lines(text: str) -> set[int]:
    """Locate CommonMark raw HTML block lines, including void/type-7 lifetimes."""
    raw_lines: set[int] = set()
    fence_character: str | None = None
    fence_length = 0
    raw_end_pattern: re.Pattern[str] | None = None
    raw_until_blank = False
    paragraph_open = False
    block_tags = "|".join(sorted(re.escape(tag) for tag in RAW_HTML_BLOCK_TAGS))
    type_one = re.compile(
        r"^ {0,3}<(?P<tag>script|pre|style|textarea)(?:[ \t]|>|$)",
        re.IGNORECASE,
    )
    type_six = re.compile(
        rf"^ {{0,3}}</?(?:{block_tags})(?:[ \t]|/?>|$)",
        re.IGNORECASE,
    )
    type_seven = re.compile(
        r"^ {0,3}</?[A-Za-z][A-Za-z0-9-]*(?:[ \t]+[^<>]*)?/?>[ \t]*$"
    )

    for line_number, line in enumerate(lf_lines_with_endings(text), start=1):
        bare = line.rstrip("\n")
        content = strip_markdown_container_prefix(bare)
        if raw_end_pattern is not None:
            raw_lines.add(line_number)
            if raw_end_pattern.search(content):
                raw_end_pattern = None
            paragraph_open = False
            continue
        if raw_until_blank:
            if not content.strip(" \t"):
                raw_until_blank = False
            else:
                raw_lines.add(line_number)
            paragraph_open = False
            continue

        fence = markdown_fence_marker(content)
        if fence_character is not None:
            if fence is not None:
                marker, tail = fence
                if (
                    marker[0] == fence_character
                    and len(marker) >= fence_length
                    and not tail.strip(" \t")
                ):
                    fence_character = None
                    fence_length = 0
                    paragraph_open = False
            continue
        if fence is not None:
            marker, _ = fence
            fence_character = marker[0]
            fence_length = len(marker)
            paragraph_open = False
            continue

        if not content.strip(" \t"):
            paragraph_open = False
            continue

        special_raw_end: re.Pattern[str] | None = None
        if re.match(r"^ {0,3}<\?", content):
            special_raw_end = re.compile(r"\?>")
        elif re.match(r"^ {0,3}<!\[CDATA\[", content):
            special_raw_end = re.compile(r"\]\]>")
        elif re.match(r"^ {0,3}<![A-Z]", content):
            special_raw_end = re.compile(r">")
        if special_raw_end is not None:
            raw_lines.add(line_number)
            if special_raw_end.search(content) is None:
                raw_end_pattern = special_raw_end
            paragraph_open = False
            continue

        type_one_match = type_one.match(content)
        if type_one_match is not None:
            raw_lines.add(line_number)
            tag = type_one_match.group("tag").casefold()
            if re.search(rf"</{re.escape(tag)}[ \t]*>", content, re.IGNORECASE) is None:
                raw_end_pattern = re.compile(
                    rf"</{re.escape(tag)}[ \t]*>",
                    re.IGNORECASE,
                )
            paragraph_open = False
            continue
        if type_six.match(content) is not None:
            raw_lines.add(line_number)
            raw_until_blank = True
            paragraph_open = False
            continue
        if not paragraph_open and type_seven.match(content) is not None:
            raw_lines.add(line_number)
            raw_until_blank = True
            paragraph_open = False
            continue
        paragraph_open = True
    return raw_lines


def strip_inline_markdown_code(text: str) -> str:
    """Remove only well-formed backtick code spans; malformed runs stay visible."""
    output: list[str] = []
    index = 0
    while index < len(text):
        if text[index] != "`" or is_markdown_escaped(text, index):
            output.append(text[index])
            index += 1
            continue
        opener_end = index
        while opener_end < len(text) and text[opener_end] == "`":
            opener_end += 1
        run_length = opener_end - index
        cursor = opener_end
        closer_end: int | None = None
        while cursor < len(text):
            if text[cursor] != "`":
                cursor += 1
                continue
            candidate_end = cursor
            while candidate_end < len(text) and text[candidate_end] == "`":
                candidate_end += 1
            if candidate_end - cursor == run_length:
                closer_end = candidate_end
                break
            cursor = candidate_end
        if closer_end is None:
            output.append(text[index:opener_end])
            index = opener_end
        else:
            index = closer_end
    return "".join(output)


def strip_markdown_code_contexts(
    text: str,
    raw_html_lines: set[int] | None = None,
) -> str:
    """Code is rendered, but it is not executable generation prose evidence."""
    raw_html_lines = raw_html_lines or set()
    kept: list[tuple[str, bool]] = []
    fence_character: str | None = None
    fence_length = 0
    paragraph_open = False
    paragraph_signature: tuple[str, ...] | None = None
    for line_number, line in enumerate(lf_lines_with_endings(text), start=1):
        bare = line.rstrip("\n")
        if line_number in raw_html_lines:
            kept.append((line, True))
            paragraph_open = False
            paragraph_signature = None
            continue
        content, container_signature = strip_markdown_container_prefix_with_signature(bare)
        fence = markdown_fence_marker(content)
        if fence_character is not None:
            if fence is not None:
                marker, tail = fence
                if (
                    marker[0] == fence_character
                    and len(marker) >= fence_length
                    and not tail.strip(" \t")
                ):
                    fence_character = None
                    fence_length = 0
                    paragraph_open = False
                    paragraph_signature = None
            continue
        if fence is not None:
            marker, _ = fence
            fence_character = marker[0]
            fence_length = len(marker)
            paragraph_open = False
            paragraph_signature = None
            continue
        if content.startswith("\t") or content.startswith("    "):
            if paragraph_open and container_signature == paragraph_signature:
                kept.append((line, False))
            continue
        kept.append((line, False))
        if not content.strip(" \t"):
            paragraph_open = False
            paragraph_signature = None
        elif re.match(r"^ {0,3}(?:#{1,6}(?:[ \t]|$)|(?:[-*_][ \t]*){3,}$)", content):
            paragraph_open = False
            paragraph_signature = None
        else:
            paragraph_open = True
            paragraph_signature = container_signature

    output: list[str] = []
    ordinary_chunk: list[str] = []
    for line, raw_html in kept:
        if raw_html:
            if ordinary_chunk:
                output.append(strip_inline_markdown_code("".join(ordinary_chunk)))
                ordinary_chunk = []
            output.append(line)
        else:
            ordinary_chunk.append(line)
    if ordinary_chunk:
        output.append(strip_inline_markdown_code("".join(ordinary_chunk)))
    return "".join(output)


def strip_markdown_reference_metadata(
    text: str,
    ignored_html_lines: set[int] | None = None,
) -> tuple[str, set[str]]:
    """Remove real definitions/titles outside fenced or hidden HTML contexts."""
    ignored_html_lines = ignored_html_lines or set()
    kept: list[str] = []
    possible_reference_title = False
    possible_reference_title_context: tuple[tuple[str, int], ...] | None = None
    open_reference_title: str | None = None
    open_title_lines: list[str] = []
    open_title_context: tuple[tuple[str, int], ...] | None = None
    pending_reference_label: str | None = None
    pending_destination_label: str | None = None
    pending_destination_lines: list[str] = []
    pending_destination_context: tuple[tuple[str, int], ...] | None = None
    pending_label_raw: str | None = None
    pending_label_lines: list[str] = []
    pending_label_context: tuple[tuple[str, int], ...] | None = None
    definitions: set[str] = set()
    fence_character: str | None = None
    fence_length = 0
    paragraph_open = False
    paragraph_context: tuple[tuple[str, int], ...] | None = None

    for line_number, line in enumerate(lf_lines_with_endings(text), start=1):
        bare = line.rstrip("\r\n")
        content, _, container_context = markdown_container_details(bare)

        fence_match = markdown_fence_marker(content)
        in_suppressed_context = line_number in ignored_html_lines
        if fence_character is not None:
            in_suppressed_context = True
            if fence_match is not None:
                marker, tail = fence_match
                if (
                    marker[0] == fence_character
                    and len(marker) >= fence_length
                    and not tail.strip(" \t")
                ):
                    fence_character = None
                    fence_length = 0
        elif fence_match is not None:
            marker, _ = fence_match
            fence_character = marker[0]
            fence_length = len(marker)
            in_suppressed_context = True

        if in_suppressed_context:
            kept.extend(open_title_lines)
            kept.extend(pending_destination_lines)
            kept.extend(pending_label_lines)
            open_title_lines = []
            open_title_context = None
            pending_destination_lines = []
            pending_destination_context = None
            pending_label_lines = []
            pending_label_context = None
            open_reference_title = None
            pending_reference_label = None
            pending_destination_label = None
            pending_label_raw = None
            possible_reference_title = False
            possible_reference_title_context = None
            paragraph_open = False
            paragraph_context = None
            kept.append(line)
            continue

        if open_reference_title is not None:
            if not markdown_same_container_continuation(open_title_context, bare):
                kept.extend(open_title_lines)
                open_title_lines = []
                open_title_context = None
                open_reference_title = None
                pending_reference_label = None
            elif not content.strip(" \t"):
                kept.extend(open_title_lines)
                kept.append(line)
                open_title_lines = []
                open_title_context = None
                open_reference_title = None
                pending_reference_label = None
                continue
            else:
                closer_index = escaped_title_closer_index(
                    content, open_reference_title, start=0
                )
                if closer_index is None:
                    open_title_lines.append(line)
                    continue
                if not markdown_component_whitespace_is_valid(
                    content[closer_index + 1:]
                ):
                    kept.extend(open_title_lines)
                    kept.append(line)
                    pending_reference_label = None
                elif pending_reference_label is not None:
                    definitions.add(pending_reference_label)
                open_title_lines = []
                open_title_context = None
                open_reference_title = None
                pending_reference_label = None
                continue

        if pending_label_raw is not None:
            if not markdown_same_container_continuation(pending_label_context, bare):
                kept.extend(pending_label_lines)
                pending_label_lines = []
                pending_label_raw = None
                pending_label_context = None
            else:
                fragment, remainder, invalid = markdown_reference_label_continuation(content)
                combined_raw = f"{pending_label_raw}\n{fragment}"
                if invalid or not content.strip(" \t") or len(combined_raw) > 999:
                    kept.extend(pending_label_lines)
                    pending_label_lines = []
                    pending_label_raw = None
                    pending_label_context = None
                elif remainder is None:
                    pending_label_raw = combined_raw
                    pending_label_lines.append(line)
                    continue
                else:
                    source_lines = [*pending_label_lines, line]
                    source_context = pending_label_context
                    pending_label_lines = []
                    pending_label_raw = None
                    pending_label_context = None
                    reference_label = normalize_markdown_reference_label(combined_raw)
                    if not reference_label:
                        kept.extend(source_lines)
                        continue
                    if not remainder:
                        pending_destination_label = reference_label
                        pending_destination_lines = source_lines
                        pending_destination_context = source_context
                        possible_reference_title = False
                        possible_reference_title_context = None
                        continue
                    definition = markdown_reference_payload(reference_label, remainder)
                    if definition is None:
                        kept.extend(source_lines)
                        continue
                    reference_label, possible_reference_title, inline_title_closer = definition
                    possible_reference_title_context = (
                        source_context if possible_reference_title else None
                    )
                    if inline_title_closer is None:
                        definitions.add(reference_label)
                    else:
                        open_reference_title = inline_title_closer
                        open_title_lines = source_lines
                        open_title_context = source_context
                        pending_reference_label = reference_label
                        possible_reference_title = False
                        possible_reference_title_context = None
                    continue

        if pending_destination_label is not None:
            saved_lines = pending_destination_lines
            saved_label = pending_destination_label
            saved_context = pending_destination_context
            pending_destination_lines = []
            pending_destination_label = None
            pending_destination_context = None
            if markdown_same_container_continuation(saved_context, bare):
                definition = markdown_reference_payload(
                    saved_label,
                    content.lstrip(" \t"),
                )
                if definition is not None:
                    reference_label, possible_reference_title, inline_title_closer = definition
                    possible_reference_title_context = (
                        saved_context if possible_reference_title else None
                    )
                    if inline_title_closer is None:
                        definitions.add(reference_label)
                    else:
                        open_reference_title = inline_title_closer
                        open_title_lines = [*saved_lines, line]
                        open_title_context = saved_context
                        pending_reference_label = reference_label
                        possible_reference_title = False
                        possible_reference_title_context = None
                    continue
            kept.extend(saved_lines)

        definition: tuple[str, bool, str | None] | None = None
        can_start_definition = (
            not paragraph_open
            or not markdown_same_container_continuation(paragraph_context, bare)
        )
        prefix = (
            markdown_reference_definition_prefix(content)
            if can_start_definition
            else None
        )
        if prefix is not None:
            raw_label, remainder = prefix
            reference_label = normalize_markdown_reference_label(raw_label)
            if reference_label and len(raw_label) <= 999:
                if not remainder:
                    pending_destination_label = reference_label
                    pending_destination_lines = [line]
                    pending_destination_context = container_context
                    possible_reference_title = False
                    possible_reference_title_context = None
                    paragraph_open = False
                    paragraph_context = None
                    continue
                definition = markdown_reference_payload(reference_label, remainder)
        if definition is not None:
            reference_label, possible_reference_title, inline_title_closer = definition
            possible_reference_title_context = (
                container_context if possible_reference_title else None
            )
            if inline_title_closer is None:
                definitions.add(reference_label)
            else:
                open_reference_title = inline_title_closer
                open_title_lines = [line]
                open_title_context = container_context
                pending_reference_label = reference_label
                possible_reference_title = False
                possible_reference_title_context = None
            paragraph_open = False
            paragraph_context = None
            continue

        open_label = (
            markdown_reference_open_label(content)
            if can_start_definition
            else None
        )
        if open_label is not None and len(open_label) <= 999:
            pending_label_raw = open_label
            pending_label_lines = [line]
            pending_label_context = container_context
            possible_reference_title = False
            possible_reference_title_context = None
            paragraph_open = False
            paragraph_context = None
            continue

        if possible_reference_title:
            if markdown_same_container_continuation(
                possible_reference_title_context, bare
            ):
                closer = reference_title_closer(content)
                if closer is not None:
                    candidate = content.lstrip(" \t")
                    closer_index = escaped_title_closer_index(candidate, closer)
                    if closer_index is None:
                        open_reference_title = closer
                        open_title_lines = [line]
                        open_title_context = container_context
                    elif not markdown_component_whitespace_is_valid(
                        candidate[closer_index + 1:]
                    ):
                        kept.append(line)
                    possible_reference_title = False
                    possible_reference_title_context = None
                    continue
        possible_reference_title = False
        possible_reference_title_context = None
        kept.append(line)
        if not content.strip(" \t"):
            paragraph_open = False
            paragraph_context = None
        elif re.match(
            r"^ {0,3}(?:#{1,6}(?:[ \t]|$)|(?:[-*_][ \t]*){3,}$)",
            content,
        ):
            paragraph_open = False
            paragraph_context = None
        else:
            paragraph_open = True
            paragraph_context = container_context

    kept.extend(open_title_lines)
    kept.extend(pending_destination_lines)
    kept.extend(pending_label_lines)
    return "".join(kept), definitions


def strip_non_rendered_markdown(text: str) -> str:
    """Remove prompt regions that are metadata/comments rather than generation prose."""
    rendered = FRONT_MATTER_RE.sub("", text, count=1)
    rendered = HTML_COMMENT_RE.sub("", rendered)
    rendered = rendered.replace("\r\n", "\n").replace("\r", "\n")
    rendered = strip_markdown_code_contexts(
        rendered,
        markdown_raw_html_block_lines(rendered),
    )
    html_visibility = inspect_html_visibility(rendered)
    if html_visibility.stylesheet_control_seen:
        return ""
    rendered, reference_definitions = strip_markdown_reference_metadata(
        rendered,
        html_visibility.non_rendered_lines
        | html_visibility.non_markdown_lines
        | markdown_raw_html_block_lines(rendered),
    )
    rendered = strip_inline_markdown_links(rendered)
    rendered = strip_markdown_reference_images(rendered, reference_definitions)
    rendered = strip_html_metadata(rendered)
    return rendered


def alias_patterns(alias: str) -> list[str]:
    """Build field-label spellings with any punctuation/separator between tokens."""
    words = re.findall(r"[a-z0-9]+", alias.casefold())
    if not words:
        return []
    separator = r"(?:[\W_])*"
    patterns = [separator.join(re.escape(word) for word in words)]
    if len(words) == 1 and 1 < len(words[0]) <= 5:
        acronym = separator.join(re.escape(character) for character in words[0]) + separator
        if acronym not in patterns:
            patterns.append(acronym)
    return patterns


def leaked_authoring_labels(text: str) -> list[str]:
    """Find serialized labels or prose explanations of internal authoring fields."""
    folded = unicodedata.normalize("NFKC", unescape(text)).casefold()
    folded = "".join(
        character
        for character in folded
        if not is_default_ignorable(character)
    )
    folded = re.sub(
        r"!?\[((?:\\[^\r\n]|[^\]\\\r\n])*)\]"
        r"(?:\[(?:\\[^\r\n]|[^\]\\\r\n])*\])?",
        lambda match: match.group(1),
        folded,
    )
    folded = re.sub(r"\\([\\`*_{}\[\]()#+.!|>~-])", r"\1", folded)
    folded = re.sub(r"[`*_~]+", "", folded)
    folded = "".join(
        "→" if "ARROW" in unicodedata.name(character, "") else character
        for character in folded
    )
    leaked: list[str] = []
    line_boundary = r"[\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029]"
    list_marker = r"(?:[#>*+-]+|[0-9]{1,9}[.)])"
    label_boundary = (
        rf"(?:(?:^|{line_boundary}+)[ \t]*(?:{list_marker}[ \t]+)?|[.!?;][ \t]+)"
    )
    arrow = r"(?:->|=>|[\u2190-\u21ff\u2794-\u27ff\u2900-\u297f])"
    for field, aliases in AUTHORING_LABEL_ALIASES.items():
        serialized = "_" in field and field in folded
        explanatory = False
        for alias in aliases:
            alias_words = re.findall(r"[a-z0-9]+", alias.casefold())
            unambiguous_prose_label = len(alias_words) > 1 or alias.casefold() == "pov"
            article_prefix = r"(?:the[ \t]+)?" if unambiguous_prose_label else ""
            explanation_boundary = (
                r"(?<![a-z0-9])" if unambiguous_prose_label else label_boundary
            )
            for flexible_alias in alias_patterns(alias):
                assignment_boundary = (
                    r"(?<![a-z0-9])" if unambiguous_prose_label else label_boundary
                )
                assignment_label = (
                    rf"{assignment_boundary}{flexible_alias}[ \t]*(?::|=)"
                )
                structural_label = (
                    rf"{label_boundary}{flexible_alias}[ \t]*"
                    rf"(?:;|\||[-\u2010-\u2015]{{1,2}}|{arrow}|\(|\[|\x7b)"
                )
                sentence_label = rf"{label_boundary}{flexible_alias}[ \t]+is\b"
                prose_explanation = (
                    rf"{explanation_boundary}{article_prefix}{flexible_alias}[ \t]+"
                    rf"(?:is|means|describes|records|captures|refers[ \t]+to)\b"
                )
                bare_label = rf"{label_boundary}{flexible_alias}[ \t]*\Z"
                heading_label = (
                    rf"{label_boundary}{flexible_alias}[ \t]*"
                    rf"(?::|=|;|\||[-\u2010-\u2015]{{1,2}}|{arrow})?[ \t]*"
                    rf"(?=\Z|{line_boundary})"
                )
                table_label = (
                    rf"{label_boundary}\|[ \t]*{flexible_alias}[ \t]*"
                    rf"(?:\||:|=|;|[-\u2010-\u2015]{{1,2}}|{arrow})"
                )
                any_table_cell_label = rf"\|[ \t]*{flexible_alias}[ \t]*\|"
                if (
                    re.search(assignment_label, folded)
                    or re.search(structural_label, folded)
                    or re.search(sentence_label, folded)
                    or re.search(prose_explanation, folded)
                    or re.search(bare_label, folded)
                    or re.search(heading_label, folded)
                    or re.search(table_label, folded)
                    or re.search(any_table_cell_label, folded)
                ):
                    explanatory = True
                    break
            if explanatory:
                break
        if serialized or explanatory:
            leaked.append(field)
    return sorted(leaked)


def expected_authoring_fields(lane: str | None, state: dict | None = None) -> set[str] | None:
    if lane == "narrative":
        return NARRATIVE_AUTHORING_FIELDS
    if lane == "non_narrative":
        return NON_NARRATIVE_AUTHORING_FIELDS
    if isinstance(state, dict):
        fields = set(state)
        if fields <= NARRATIVE_AUTHORING_FIELDS:
            return NARRATIVE_AUTHORING_FIELDS
        if fields <= NON_NARRATIVE_AUTHORING_FIELDS:
            return NON_NARRATIVE_AUTHORING_FIELDS
    return None


def check_authoring_state(
    state: object,
    label: str,
    errors: list[str],
    *,
    required: bool,
    lane: str | None = None,
    source_references: set[str] | None = None,
) -> None:
    """Validate the deterministic shell around an inherently qualitative record.

    This can prove presence, shape, one-line handoff safety, and concrete-carrier
    separation. It cannot prove that the dramatic choices are original or that a
    generation model will enact them; that remains a take-review responsibility.
    """
    if state is None:
        if required:
            errors.append(f"{label}: missing authoring_state")
        return
    if not isinstance(state, dict):
        errors.append(f"{label}: authoring_state must be an object")
        return

    expected = expected_authoring_fields(lane, state)
    if expected is None:
        errors.append(f"{label}: authoring_state does not match a canonical lane record")
        return
    missing = sorted(expected - set(state))
    extra = sorted(set(state) - expected)
    if missing:
        errors.append(f"{label}: authoring_state missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"{label}: authoring_state has unknown fields: {', '.join(extra)}")

    for field in sorted(AUTHORING_TEXT_FIELDS & set(state)):
        value = state[field]
        if not has_visible_text(value) or not is_one_line_text(value):
            errors.append(f"{label}: authoring_state.{field} must be a non-empty one-line string")

    if expected == NON_NARRATIVE_AUTHORING_FIELDS:
        utility_intent = state.get("utility_intent")
        if isinstance(utility_intent, str):
            errors.extend(
                utility_prompt_relevance_errors(
                    utility_intent,
                    utility_intent,
                    label=label,
                )
            )
        return

    provenance = state.get("non_transferable_detail_provenance")
    if not is_string_enum(provenance, NON_TRANSFERABLE_PROVENANCE):
        errors.append(
            f"{label}: authoring_state.non_transferable_detail_provenance must be "
            "source_bound or authored_choice"
        )
    source = state.get("non_transferable_detail_source")
    if provenance == "source_bound":
        if (
            not isinstance(source, str)
            or not has_visible_text(source)
            or not is_one_line_text(source)
            or SOURCE_EVIDENCE_RE.fullmatch(source.strip()) is None
            or not source_evidence_has_visible_payload(source)
        ):
            errors.append(
                f"{label}: source_bound non-transferable detail requires an exact "
                "reference tag, URL, file:, ref:, or evidence: locator"
            )
        elif source_references is not None and source.strip() not in source_references:
            errors.append(
                f"{label}: source_bound non-transferable detail source {source.strip()!r} "
                "is not present in reference_registry"
            )
    elif provenance == "authored_choice" and source is not None:
        errors.append(
            f"{label}: authored_choice non-transferable detail source must be null"
        )
    before = state.get("value_before")
    after = state.get("value_after")
    if isinstance(before, str) and isinstance(after, str):
        if normalized_dramatic_value(before) == normalized_dramatic_value(after):
            errors.append(f"{label}: authoring_state.value_after must change value_before")

    carriers = state.get("prompt_carriers")
    if not isinstance(carriers, list) or not carriers:
        errors.append(f"{label}: authoring_state.prompt_carriers must be a non-empty array")
        return
    normalized: list[str] = []
    for index, carrier in enumerate(carriers):
        if not has_visible_text(carrier) or not is_one_line_text(carrier):
            errors.append(
                f"{label}: authoring_state.prompt_carriers[{index}] must be a non-empty one-line string"
            )
            continue
        folded = " ".join(
            "".join(
                character
                for character in unicodedata.normalize("NFKC", carrier).casefold()
                if not is_default_ignorable(character)
            ).split()
        )
        normalized.append(folded)
        leaked = leaked_authoring_labels(folded)
        if leaked:
            errors.append(
                f"{label}: authoring_state.prompt_carriers[{index}] leaks internal labels: {', '.join(leaked)}"
            )
    if len(normalized) != len(set(normalized)):
        errors.append(f"{label}: authoring_state.prompt_carriers must not contain duplicates")
    creative_fields = {
        field: state[field]
        for field in sorted(
            NARRATIVE_AUTHORING_FIELDS
            - {
                "non_transferable_detail_provenance",
                "non_transferable_detail_source",
                "prompt_carriers",
            }
        )
        if isinstance(state.get(field), str)
    }
    errors.extend(
        creative_specificity_errors(
            creative_fields,
            carriers if isinstance(carriers, list) else [],
            label=f"{label}: authoring_state",
            carrier_fields=(
                "visible_suppressed_behavior",
                "non_transferable_detail",
            ),
        )
    )


def compiled_prompt_errors(
    prompt: str,
    state: object,
    label: str = "prompt",
    *,
    lane: str | None = None,
) -> list[str]:
    """Check the deterministic authoring-state-to-prompt boundary.

    Exact carriers are intentionally auditable. This is not a model-quality score.
    """
    errors: list[str] = []
    local: list[str] = []
    check_authoring_state(state, label, local, required=True, lane=lane)
    if local:
        return local
    assert isinstance(state, dict)
    rendered_prompt = strip_non_rendered_markdown(prompt)
    leaked_fields = set(leaked_authoring_labels(prompt))
    leaked_fields.update(leaked_authoring_labels(strip_html_tags_keep_data(prompt)))
    for field in sorted(leaked_fields):
        errors.append(f"{label}: generation prompt leaks internal authoring label {field}")
    for carrier in state.get("prompt_carriers", []):
        if carrier not in rendered_prompt:
            errors.append(f"{label}: generation prompt missing exact prompt carrier: {carrier}")
    if lane == "non_narrative":
        utility_intent = state.get("utility_intent")
        if isinstance(utility_intent, str):
            errors.extend(
                utility_prompt_relevance_errors(
                    utility_intent,
                    rendered_prompt,
                    label=label,
                )
            )
    return errors


def check_authoring_state_provenance(
    obj: dict,
    label: str,
    errors: list[str],
    *,
    required: bool,
    current_project_version: tuple[int, int] | None,
) -> None:
    provenance = obj.get("authoring_state_provenance")
    if provenance is None:
        if required:
            errors.append(f"{label}: missing authoring_state_provenance")
        return
    if not isinstance(provenance, dict):
        errors.append(f"{label}: authoring_state_provenance must be an object")
        return

    missing = sorted(AUTHORING_STATE_PROVENANCE_FIELDS - set(provenance))
    extra = sorted(set(provenance) - AUTHORING_STATE_PROVENANCE_FIELDS)
    if missing:
        errors.append(
            f"{label}: authoring_state_provenance missing fields: {', '.join(missing)}"
        )
    if extra:
        errors.append(
            f"{label}: authoring_state_provenance has unknown fields: {', '.join(extra)}"
        )

    if provenance.get("project_id") != obj.get("project_id"):
        errors.append(f"{label}: authoring_state_provenance project_id does not match contract")
    if provenance.get("clip_id") != obj.get("clip_id"):
        errors.append(f"{label}: authoring_state_provenance clip_id does not match contract")
    revision = (provenance.get("canon_revision"), provenance.get("state_revision"))
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 1
        for value in revision
    ):
        errors.append(
            f"{label}: authoring_state_provenance revisions must be integers >= 1"
        )

    digest = provenance.get("authoring_state_sha256")
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        errors.append(
            f"{label}: authoring_state_provenance authoring_state_sha256 must be 64 lowercase hex characters"
        )
    state = obj.get("authoring_state")
    if isinstance(state, dict) and isinstance(digest, str):
        expected_digest = authoring_state_digest(state)
        if digest != expected_digest:
            errors.append(
                f"{label}: authoring_state does not match its immutable provenance digest"
            )

    if (
        current_project_version is not None
        and all(isinstance(value, int) and not isinstance(value, bool) for value in revision)
    ):
        if is_string_enum(obj.get("status"), CURRENT_CONTRACT_STATUSES):
            if revision != current_project_version:
                errors.append(
                    f"{label}: current authoring_state provenance revision {revision} does not "
                    f"match current project revision {current_project_version}"
                )
        elif is_string_enum(obj.get("status"), HISTORICAL_CONTRACT_STATUSES):
            if any(value > current for value, current in zip(revision, current_project_version)):
                errors.append(
                    f"{label}: historical authoring_state provenance revision {revision} is "
                    f"newer than current project revision {current_project_version}"
                )


def check_authoring_state_snapshots(
    value: object,
    label: str,
    errors: list[str],
    *,
    project_id: object,
    clip_id: object,
) -> None:
    """Validate immutable contract coordinates stored on a project clip."""

    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"{label}: contract_authoring_state_snapshots must be an array")
        return
    for index, snapshot in enumerate(value):
        item_label = f"{label}: contract_authoring_state_snapshots[{index}]"
        if not isinstance(snapshot, dict):
            errors.append(f"{item_label} must be an object")
            continue
        missing = sorted(AUTHORING_STATE_PROVENANCE_FIELDS - set(snapshot))
        extra = sorted(set(snapshot) - AUTHORING_STATE_PROVENANCE_FIELDS)
        if missing:
            errors.append(f"{item_label} missing fields: {', '.join(missing)}")
        if extra:
            errors.append(f"{item_label} unknown fields: {', '.join(extra)}")
        if snapshot.get("project_id") != project_id:
            errors.append(f"{item_label} project_id does not match project")
        if snapshot.get("clip_id") != clip_id:
            errors.append(f"{item_label} clip_id does not match clip")
        for field in ("canon_revision", "state_revision"):
            revision = snapshot.get(field)
            if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
                errors.append(f"{item_label} {field} must be an integer >= 1")
        digest = snapshot.get("authoring_state_sha256")
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            errors.append(
                f"{item_label} authoring_state_sha256 must be 64 lowercase hex characters"
            )
        if snapshot in value[:index]:
            errors.append(f"{item_label} duplicates an earlier snapshot")


def looks_like_project_state(path: Path, obj: object | None = None) -> bool:
    """Recognize project snapshots by canonical name or distinctive object shape."""
    if "project-state" in path.name.casefold():
        return True
    if not isinstance(obj, dict) or "project_id" not in obj or "clip_id" in obj:
        return False
    return any(
        key in obj
        for key in ("project_mode", "clips", "scenes", "beats", "canon_revision", "state_revision")
    )


def looks_like_take_review(path: Path, obj: object | None = None) -> bool:
    """Recognize take reviews without trusting a filename convention alone."""
    if "take-review" in path.name.casefold():
        return True
    return isinstance(obj, dict) and "take_id" in obj and any(
        key in obj for key in ("source_status", "verdict", "accepted_deviations")
    )


def looks_like_clip_contract(path: Path, obj: object | None = None) -> bool:
    """Recognize standalone clip contracts even after an accidental rename."""
    if "contract" in path.name.casefold():
        return True
    if not isinstance(obj, dict) or looks_like_take_review(path, obj):
        return False
    if "project_id" not in obj or "clip_id" not in obj:
        return False
    return any(
        key in obj
        for key in (
            "generation_mode",
            "shot_structure",
            "directors_read_lane",
            "authoring_state",
            "planned_start_state",
            "planned_end_state",
        )
    )


def sequence_paths(root: Path) -> list[Path]:
    examples = root / "examples"
    if not os.path.lexists(examples):
        return []
    examples = validate_repo_input_path(root, examples)
    paths = []
    for path in examples.rglob("*.json"):
        path = validate_repo_input_path(root, path)
        if is_take_review_path(path):
            # Review candidates are loaded once, after project discovery, by
            # the bounded shared review index.  Generic discovery must not
            # pre-read bytes that the authority reader may reject by size or
            # file identity.
            continue
        try:
            obj = load_json(path, root=root)
        except Exception:
            obj = None
        if looks_like_project_state(path, obj):
            paths.append(path)
    return sorted(paths)


def needs_authoring_record(clip: dict, *, strict: bool) -> bool:
    """Any explicit lane carries its complete record; strict adds lane presence."""
    return is_string_enum(clip.get("directors_read_lane"), DIRECTORS_READ_LANES)


def nearest_narrative_ancestor(clip: dict, clips: dict[str, dict]) -> dict | None:
    """Walk through utility inserts without dropping the dramatic lineage."""
    parent_id = clip.get("parent_clip_id")
    visited: set[str] = set()
    while isinstance(parent_id, str) and parent_id in clips and parent_id not in visited:
        visited.add(parent_id)
        parent = clips[parent_id]
        if parent.get("directors_read_lane") == "narrative":
            return parent
        parent_id = parent.get("parent_clip_id")
    return None


def validate_project(
    path: Path,
    root: Path,
    review_index: TakeReviewIndex | None = None,
    *,
    strict: bool = False,
) -> list[str]:
    data, rel, errors = load_project_document(path, root)
    if data is None:
        return bound_validation_diagnostics(errors, rel)

    lineage = analyze_lineage(data.get("clips"), rel)
    errors.extend(lineage.errors)
    check_required(data, REQUIRED_PROJECT_FIELDS, rel, errors)
    missing_project_fields = REQUIRED_PROJECT_FIELDS - set(data)
    if missing_project_fields:
        return bound_validation_diagnostics(errors, rel)

    clips = lineage.clips
    clips_by_id = lineage.clips_by_id
    clip_ids = set(clips_by_id)
    if review_index is None:
        review_index = build_take_review_indexes([path])[path.resolve().parent]
    errors.extend(validate_take_reconciliation(data, clips_by_id, rel, review_index))

    if not is_string_enum(data["project_mode"], {"standalone_clip", "sequence_project"}):
        errors.append(f"{rel}: invalid project_mode {data['project_mode']}")
    story = data["story"]
    if not isinstance(story, dict):
        errors.append(f"{rel}: story must be an object")
        story = {}
    if data["project_mode"] == "sequence_project" and not story.get("final_outcome"):
        errors.append(f"{rel}: sequence project missing final_outcome")
    check_required(story, REQUIRED_STORY_FIELDS, f"{rel}: story", errors)
    references = data.get("reference_registry")
    if not isinstance(references, list):
        errors.append(f"{rel}: reference_registry must be an array of reference objects")
        references = []
    valid_references: list[dict] = []
    source_references: set[str] = set()
    for index, reference in enumerate(references):
        if not isinstance(reference, dict):
            errors.append(f"{rel}: reference_registry[{index}] must be an object")
            continue
        valid_references.append(reference)
        tag = reference.get("tag")
        if isinstance(tag, str):
            source_references.add(tag)

    accepted_ids: set[str] = set()
    scene_ids = set()
    scene_depth_caps = {}
    scene_indexes = set()
    scene_order = {}
    scene_assigned = {}
    clip_scene = {}
    clip_positions = {}
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list):
        errors.append(f"{rel}: scenes must be an array of scene objects")
        scenes = []
    for scene_index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            errors.append(f"{rel}: scenes[{scene_index}] must be an object")
            continue
        check_required(scene, REQUIRED_SCENE_FIELDS, f"{rel}: scene", errors)
        sid = scene.get("scene_id")
        valid_sid = isinstance(sid, str) and bool(sid.strip())
        if not valid_sid:
            errors.append(f"{rel}: scene[{scene_index}] scene_id must be a non-empty string")
        elif sid in scene_ids:
            errors.append(f"{rel}: duplicate scene_id {sid}")
        else:
            scene_ids.add(sid)
        idx = scene.get("scene_index")
        if not isinstance(idx, int) or isinstance(idx, bool) or idx < 1:
            errors.append(f"{rel}: scene {sid} scene_index must be an integer >= 1")
        elif idx in scene_indexes:
            errors.append(f"{rel}: duplicate scene_index {idx}")
        else:
            scene_indexes.add(idx)
            if valid_sid:
                scene_order[sid] = idx
        if not is_string_enum(scene.get("status"), SCENE_STATUSES):
            errors.append(f"{rel}: scene {sid} invalid status {scene.get('status')}")
        if not is_string_enum(scene.get("arc_position"), ARC_POSITIONS):
            errors.append(f"{rel}: scene {sid} invalid arc_position {scene.get('arc_position')}")
        depth_cap = scene.get("max_chain_depth")
        if not isinstance(depth_cap, int) or isinstance(depth_cap, bool) or depth_cap < 0 or depth_cap > MAX_CHAIN_DEPTH_CEILING:
            errors.append(f"{rel}: scene {sid} max_chain_depth must be an integer between 0 and {MAX_CHAIN_DEPTH_CEILING}")
        else:
            if valid_sid:
                scene_depth_caps[sid] = depth_cap
        assigned_list = scene.get("assigned_clip_ids")
        seen_assigned = checked_string_array(
            assigned_list,
            f"{rel}: scene {sid} assigned_clip_ids",
            errors,
        )
        if isinstance(assigned_list, list):
            seen_once: set[str] = set()
            for assigned in assigned_list:
                if not isinstance(assigned, str) or not assigned.strip():
                    continue
                if assigned in seen_once:
                    errors.append(f"{rel}: scene {sid} lists clip {assigned} more than once")
                seen_once.add(assigned)
        if valid_sid:
            scene_assigned[sid] = seen_assigned
    for clip in clips:
        check_required(clip, REQUIRED_CLIP_FIELDS, f"{rel}: clip", errors)
        cid = clip.get("clip_id")
        if (
            not isinstance(cid, str)
            or not cid.strip()
            or clips_by_id.get(cid) is not clip
        ):
            continue
        sid = clip.get("scene_id")
        valid_sid = isinstance(sid, str) and bool(sid.strip())
        if not valid_sid:
            errors.append(f"{rel}: clip {cid} scene_id must be a non-empty string")
        clip_scene[cid] = sid if valid_sid else None
        sequence_index = clip.get("sequence_index")
        normalized_sequence_index = json_integer(sequence_index)
        if normalized_sequence_index is None or normalized_sequence_index < 1:
            errors.append(f"{rel}: clip {cid} sequence_index must be an integer >= 1")
        elif isinstance(sid, str):
            position = (sid, normalized_sequence_index)
            if position in clip_positions:
                errors.append(
                    f"{rel}: duplicate sequence_index {sequence_index} in scene {sid} "
                    f"for clips {clip_positions[position]} and {cid}"
                )
            else:
                clip_positions[position] = cid
        depth = clip.get("extension_depth")
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
            errors.append(f"{rel}: clip {cid} extension_depth must be a non-negative integer")
            depth = None
        felt = clip.get("felt_intent")
        if "felt_intent" in clip and (
            not has_visible_text(felt) or not is_one_line_text(felt)
        ):
            errors.append(f"{rel}: clip {cid} felt_intent must be a non-empty one-line string")
        lane = clip.get("directors_read_lane")
        lane_present = "directors_read_lane" in clip
        authoring_key_present = any(
            field in clip
            for field in (
                "directors_read_lane",
                "authoring_state",
                "authoring_state_provenance",
                "contract_authoring_state_snapshots",
            )
        )
        strict_sequence = strict and data["project_mode"] == "sequence_project"
        if (
            not is_string_enum(lane, DIRECTORS_READ_LANES)
            and (
                lane_present
                or authoring_key_present
                or strict_sequence
            )
        ):
            errors.append(
                f"{rel}: clip {cid} authoring metadata requires directors_read_lane "
                "narrative or non_narrative"
            )
        check_authoring_state(
            clip.get("authoring_state"),
            f"{rel}: clip {cid}",
            errors,
            required=(
                authoring_key_present
                or strict_sequence
            ),
            lane=lane if is_string_enum(lane, DIRECTORS_READ_LANES) else None,
            source_references=source_references,
        )
        check_authoring_state_snapshots(
            clip.get("contract_authoring_state_snapshots"),
            f"{rel}: clip {cid}",
            errors,
            project_id=data.get("project_id"),
            clip_id=cid,
        )
        if not valid_sid or sid not in scene_ids:
            errors.append(f"{rel}: clip {cid} scene {sid} is missing")
        elif sid in scene_depth_caps and depth is not None and depth > scene_depth_caps[sid]:
            errors.append(
                f"{rel}: clip {cid} extension_depth {depth} exceeds "
                f"scene {sid} max_chain_depth {scene_depth_caps[sid]}; open from canonical references instead"
            )
        if is_string_enum(clip.get("status"), ACCEPTED):
            accepted_ids.add(cid)
            if not clip.get("observed_end_state"):
                errors.append(f"{rel}: accepted clip {cid} missing observed_end_state")
        if clip.get("status") == "rejected" and clip.get("observed_end_state"):
            errors.append(f"{rel}: rejected clip {cid} must not publish observed_end_state as canon")

    for clip in clips:
        cid = clip.get("clip_id")
        if (
            not isinstance(cid, str)
            or not cid.strip()
            or clips_by_id.get(cid) is not clip
        ):
            continue
        parent_kind, parent = classify_parent_id(clip)
        sequence_index = clip.get("sequence_index")
        depth = clip.get("extension_depth")
        if parent_kind == "root":
            if isinstance(depth, int) and not isinstance(depth, bool) and depth != 0:
                errors.append(
                    f"{rel}: root clip {cid} extension_depth must be 0, got {depth}"
                )
        elif (
            parent_kind == "parent"
            and parent != cid
            and parent in clips_by_id
        ):
            parent_clip = clips_by_id.get(parent)
            parent_index = parent_clip.get("sequence_index") if parent_clip else None
            child_scene = clip.get("scene_id")
            parent_scene = parent_clip.get("scene_id") if parent_clip else None
            if child_scene == parent_scene:
                if (
                    isinstance(sequence_index, int)
                    and not isinstance(sequence_index, bool)
                    and isinstance(parent_index, int)
                    and not isinstance(parent_index, bool)
                    and parent_index >= sequence_index
                ):
                    errors.append(
                        f"{rel}: clip {cid} sequence_index {sequence_index} must be greater than "
                        f"parent {parent} sequence_index {parent_index} in scene {child_scene}"
                    )
            else:
                child_scene_index = (
                    scene_order.get(child_scene) if isinstance(child_scene, str) else None
                )
                parent_scene_index = (
                    scene_order.get(parent_scene) if isinstance(parent_scene, str) else None
                )
                if (
                    isinstance(child_scene_index, int)
                    and isinstance(parent_scene_index, int)
                    and parent_scene_index >= child_scene_index
                ):
                    errors.append(
                        f"{rel}: clip {cid} scene {child_scene} must follow parent {parent} "
                        f"scene {parent_scene}"
                    )

            parent_depth = parent_clip.get("extension_depth") if parent_clip else None
            if (
                isinstance(depth, int)
                and not isinstance(depth, bool)
                and isinstance(parent_depth, int)
                and not isinstance(parent_depth, bool)
            ):
                expected_depth = parent_depth + 1 if child_scene == parent_scene else 0
                if depth != expected_depth:
                    errors.append(
                        f"{rel}: clip {cid} extension_depth {depth} must be {expected_depth} "
                        f"from parent {parent}"
                    )
            if clip.get("status") != "planned" and parent not in accepted_ids:
                errors.append(f"{rel}: later clip {cid} parent {parent} is not accepted")
        already_happened = checked_string_array(
            clip.get("already_happened"),
            f"{rel}: clip {cid} already_happened",
            errors,
        )
        this_clip_only = checked_string_array(
            clip.get("this_clip_only"),
            f"{rel}: clip {cid} this_clip_only",
            errors,
        )
        reserved_for_later = checked_string_array(
            clip.get("reserved_for_later"),
            f"{rel}: clip {cid} reserved_for_later",
            errors,
        )
        overlap_current_future = this_clip_only & reserved_for_later
        if overlap_current_future:
            errors.append(f"{rel}: clip {cid} overlaps current and reserved beats: {sorted(overlap_current_future)}")
        overlap_done_current = already_happened & this_clip_only
        if overlap_done_current:
            errors.append(f"{rel}: clip {cid} replays completed beats: {sorted(overlap_done_current)}")
        if strict and clip.get("directors_read_lane") == "narrative":
            parent_clip = nearest_narrative_ancestor(clip, clips_by_id)
            child_authoring = clip.get("authoring_state")
            if parent_clip is not None and isinstance(child_authoring, dict):
                parent_authoring = parent_clip.get("authoring_state")
            else:
                parent_authoring = None
            if isinstance(parent_authoring, dict) and isinstance(child_authoring, dict):
                parent_after = parent_authoring.get("value_after")
                child_before = child_authoring.get("value_before")
                if parent_after != child_before:
                    errors.append(
                        f"{rel}: clip {cid} authoring_state.value_before must equal "
                        f"nearest narrative ancestor {parent_clip.get('clip_id')} "
                        "authoring_state.value_after"
                    )

    beats = data["beats"]
    if not isinstance(beats, list):
        errors.append(f"{rel}: beats must be an array of beat objects")
        beats = []
    for beat_index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            errors.append(f"{rel}: beats[{beat_index}] must be an object")
            continue
        check_required(beat, REQUIRED_BEAT_FIELDS, f"{rel}: beat", errors)
        beat_id = beat.get("beat_id")
        if not isinstance(beat_id, str) or not beat_id.strip():
            errors.append(f"{rel}: beat[{beat_index}] beat_id must be a non-empty string")
        assigned = beat.get("assigned_clip_id")
        if assigned is not None and (
            not isinstance(assigned, str) or not assigned.strip()
        ):
            errors.append(
                f"{rel}: beat {beat.get('beat_id')} assigned_clip_id must be null or a non-empty string"
            )
        elif assigned is not None and assigned not in clip_ids:
            errors.append(f"{rel}: beat {beat.get('beat_id')} assigned to missing clip {assigned}")
        checked_string_array(
            beat.get("dependencies"),
            f"{rel}: beat {beat.get('beat_id')} dependencies",
            errors,
        )

    assignment_owners = {}
    for sid, assigned_set in scene_assigned.items():
        for assigned in assigned_set:
            if assigned not in clip_ids:
                errors.append(f"{rel}: scene {sid} assigned to missing clip {assigned}")
            assignment_owners.setdefault(assigned, []).append(sid)
    for cid, owners in assignment_owners.items():
        if len(owners) > 1:
            errors.append(f"{rel}: clip {cid} is assigned to multiple scenes: {sorted(owners)}")
    for cid, sid in clip_scene.items():
        if sid in scene_assigned and cid not in scene_assigned[sid]:
            errors.append(f"{rel}: clip {cid} carries scene_id {sid} but scene {sid} does not list it in assigned_clip_ids")
        owners = assignment_owners.get(cid, [])
        if owners and sid not in owners:
            errors.append(f"{rel}: clip {cid} carries scene_id {sid} but is listed under scene {owners[0]}")

    for ref in valid_references:
        tag = ref.get("tag")
        if not isinstance(tag, str) or not tag.strip():
            errors.append(f"{rel}: reference tag must be a non-empty string")
        if ref.get("preserve_exact_tag") is not True:
            errors.append(f"{rel}: reference {ref.get('tag')} must set preserve_exact_tag true")

    current_clip_id = data["current_clip_id"]
    if not isinstance(current_clip_id, str) or current_clip_id not in clip_ids:
        errors.append(f"{rel}: current_clip_id missing from clips")
    return bound_validation_diagnostics(errors, rel)


def validate_contract(
    obj: dict,
    label: str,
    errors: list[str],
    *,
    strict: bool,
    current_clip: dict | None,
    prompt: str | None,
    current_project_version: tuple[int, int] | None = None,
    source_references: set[str] | None = None,
    historical_ledger: dict[tuple[str, str, int, int], dict] | None = None,
    consumed_historical_keys: set[tuple[str, str, int, int]] | None = None,
) -> None:
    """Validate a clip contract against the current project snapshot and its prompt."""
    check_required(obj, REQUIRED_CLIP_CONTRACT_FIELDS, label, errors)
    felt = obj.get("felt_intent")
    if "felt_intent" in obj and (
        not has_visible_text(felt) or not is_one_line_text(felt)
    ):
        errors.append(f"{label}: felt_intent must be a non-empty one-line string")
    current_beats = checked_string_array(
        obj.get("this_clip_only"),
        f"{label}: this_clip_only",
        errors,
    )
    reserved_beats = checked_string_array(
        obj.get("reserved_for_later"),
        f"{label}: reserved_for_later",
        errors,
    )
    if current_beats & reserved_beats:
        errors.append(f"{label}: current and reserved beats overlap")

    lane = obj.get("directors_read_lane")
    authoring_key_present = any(
        field in obj
        for field in (
            "directors_read_lane",
            "authoring_state",
            "authoring_state_provenance",
        )
    )
    authoring_required = strict or authoring_key_present
    if not is_string_enum(lane, DIRECTORS_READ_LANES) and authoring_required:
        errors.append(
            f"{label}: authoring metadata requires directors_read_lane "
            "narrative or non_narrative"
        )
    check_authoring_state(
        obj.get("authoring_state"),
        label,
        errors,
        required=authoring_required,
        lane=lane if is_string_enum(lane, DIRECTORS_READ_LANES) else None,
        source_references=source_references,
    )
    provenance_required = authoring_required
    check_authoring_state_provenance(
        obj,
        label,
        errors,
        required=provenance_required,
        current_project_version=current_project_version,
    )
    if provenance_required and current_clip is not None:
        snapshots = current_clip.get("contract_authoring_state_snapshots")
        if (
            not isinstance(snapshots, list)
            or obj.get("authoring_state_provenance") not in snapshots
        ):
            errors.append(
                f"{label}: authoring_state_provenance is not bound to an exact "
                "planned snapshot in current project state"
            )
    if provenance_required and is_string_enum(
        obj.get("status"), HISTORICAL_CONTRACT_STATUSES
    ):
        provenance = obj.get("authoring_state_provenance")
        if not isinstance(provenance, dict):
            errors.append(f"{label}: historical contract lacks protected provenance coordinates")
        elif historical_ledger is None:
            errors.append(f"{label}: protected historical provenance ledger is unavailable")
        else:
            key = (
                obj.get("project_id"),
                obj.get("clip_id"),
                provenance.get("canon_revision"),
                provenance.get("state_revision"),
            )
            coordinates_valid = (
                isinstance(key[0], str)
                and isinstance(key[1], str)
                and isinstance(key[2], int)
                and not isinstance(key[2], bool)
                and isinstance(key[3], int)
                and not isinstance(key[3], bool)
            )
            entry = historical_ledger.get(key) if coordinates_valid else None
            if entry is None:
                errors.append(
                    f"{label}: no protected historical provenance ledger entry for {key}"
                )
            else:
                expected = {
                    "contract_status": obj.get("status"),
                    "authoring_state_sha256": provenance.get("authoring_state_sha256"),
                    "contract_sha256": canonical_json_digest(obj),
                    "prompt_sha256": prompt_digest(prompt) if prompt is not None else None,
                }
                exact_match = True
                for field, actual in expected.items():
                    if entry.get(field) != actual:
                        exact_match = False
                        errors.append(
                            f"{label}: {field} does not match protected historical "
                            "provenance ledger"
                        )
                if exact_match and consumed_historical_keys is not None:
                    if key in consumed_historical_keys:
                        errors.append(
                            f"{label}: protected historical provenance ledger entry {key} "
                            "is consumed by more than one terminal contract artifact"
                        )
                    else:
                        consumed_historical_keys.add(key)
    if not is_string_enum(obj.get("status"), CONTRACT_STATUSES):
        errors.append(f"{label}: invalid contract status {obj.get('status')!r}")

    if current_clip is None:
        if strict:
            errors.append(f"{label}: no current project clip matches this contract")
    else:
        expected_lane = current_clip.get("directors_read_lane")
        if lane != expected_lane:
            errors.append(
                f"{label}: directors_read_lane {lane!r} does not match current project clip "
                f"{expected_lane!r}"
            )
        if (
            is_string_enum(obj.get("status"), CURRENT_CONTRACT_STATUSES)
            and obj.get("status") != current_clip.get("status")
        ):
            errors.append(
                f"{label}: status {obj.get('status')!r} does not match current project clip "
                f"{current_clip.get('status')!r}"
            )
        for field in (
            "parent_clip_id", "scene_id", "sequence_index", "narrative_job", "felt_intent",
            "generation_mode", "already_happened", "this_clip_only", "reserved_for_later",
        ):
            if obj.get(field) != current_clip.get(field):
                errors.append(f"{label}: {field} does not match current project clip")
        if is_string_enum(obj.get("status"), CURRENT_CONTRACT_STATUSES):
            if obj.get("authoring_state") != current_clip.get("authoring_state"):
                errors.append(f"{label}: current authoring_state is stale against project state")

    if prompt is None:
        if strict:
            errors.append(f"{label}: matching generation prompt is missing")
    elif (
        isinstance(obj.get("authoring_state"), dict)
        or is_string_enum(lane, DIRECTORS_READ_LANES)
    ):
        errors.extend(
            compiled_prompt_errors(
                prompt,
                obj.get("authoring_state"),
                f"{label}: generation prompt",
                lane=lane if is_string_enum(lane, DIRECTORS_READ_LANES) else None,
            )
        )


def project_version(project: dict, path: Path | None = None) -> tuple[int, int]:
    canon = project.get("canon_revision")
    state = project.get("state_revision")
    return (
        canon if isinstance(canon, int) and not isinstance(canon, bool) else 0,
        state if isinstance(state, int) and not isinstance(state, bool) else 0,
    )


def check_provenance_ledger_consumption(
    historical_ledger: dict[tuple[str, str, int, int], dict] | None,
    consumed_historical_keys: set[tuple[str, str, int, int]],
    errors: list[str],
) -> None:
    """Reject protected entries no exact terminal contract artifact consumed."""
    if historical_ledger is None:
        return
    for key in historical_ledger:
        if key not in consumed_historical_keys:
            errors.append(
                "validation/authoring-state-provenance-ledger.json: protected "
                f"historical provenance entry {key} is orphaned; no exact terminal "
                "contract and prompt consume it"
            )


def select_current_projects(
    snapshots: list[tuple[Path, dict]],
    root: Path,
    errors: list[str],
) -> dict[str, tuple[tuple[int, int], Path, dict]]:
    """Select only a uniquely newest snapshot for each project.

    Revision coordinates are a partial order. Equal coordinates are duplicate
    identities, and crossed coordinates are incomparable; neither case may be
    resolved by filesystem ordering.
    """
    def label(path: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return path.as_posix()

    grouped: dict[str, list[tuple[tuple[int, int], Path, dict]]] = {}
    for path, project in snapshots:
        project_id = project.get("project_id")
        if not isinstance(project_id, str):
            continue
        grouped.setdefault(project_id, []).append(
            (project_version(project, path), path, project)
        )

    selected: dict[str, tuple[tuple[int, int], Path, dict]] = {}
    for project_id in sorted(grouped):
        records = sorted(grouped[project_id], key=lambda item: label(item[1]))
        ambiguous = False
        for left_index, (left_version, left_path, _) in enumerate(records):
            for right_version, right_path, _ in records[left_index + 1 :]:
                if left_version == right_version:
                    errors.append(
                        f"duplicate project snapshot revision for {project_id}: "
                        f"canon_revision={left_version[0]}, "
                        f"state_revision={left_version[1]} in "
                        f"{label(left_path)} and {label(right_path)}"
                    )
                    ambiguous = True
                    continue
                left_dominates = all(
                    left >= right
                    for left, right in zip(left_version, right_version)
                )
                right_dominates = all(
                    right >= left
                    for left, right in zip(left_version, right_version)
                )
                if not left_dominates and not right_dominates:
                    errors.append(
                        f"incomparable project snapshot revisions for {project_id}: "
                        f"{label(left_path)} has {left_version}, "
                        f"{label(right_path)} has {right_version}"
                    )
                    ambiguous = True
        if ambiguous:
            continue
        selected[project_id] = next(
            record
            for record in records
            if all(
                all(current >= other for current, other in zip(record[0], candidate[0]))
                for candidate in records
            )
        )
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "require complete authoring state, current-project binding, and matching "
            "generation prompts"
        ),
    )
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    errors: list[str] = []
    ledger_path = root / PROVENANCE_LEDGER_RELATIVE_PATH
    historical_ledger = (
        load_protected_provenance_ledger(root, errors)
        if ledger_path.exists()
        else {}
    )
    try:
        paths = sequence_paths(root)
    except (OSError, ValueError) as exc:
        errors.append(f"examples: invalid repository input: {diagnostic_text(exc)}")
        paths = []
    if not paths:
        errors.append("missing project-state examples")
    review_indexes = build_take_review_indexes(paths)
    snapshots: list[tuple[Path, dict]] = []
    for path in paths:
        errors.extend(
            validate_project(
                path,
                root,
                review_indexes[path.resolve().parent],
                strict=args.strict,
            )
        )
        try:
            project = load_json(path, root=root)
        except Exception:
            continue
        if isinstance(project, dict) and isinstance(project.get("project_id"), str):
            snapshots.append((path, project))

    current_projects = select_current_projects(snapshots, root, errors)

    current_clips: dict[tuple[str, str], dict] = {}
    current_project_versions: dict[str, tuple[int, int]] = {}
    current_project_references: dict[str, set[str]] = {}
    for project_id, (version, _, project) in current_projects.items():
        current_project_versions[project_id] = version
        references = project.get("reference_registry", [])
        if not isinstance(references, list):
            references = []
        current_project_references[project_id] = {
            reference.get("tag")
            for reference in references
            if isinstance(reference, dict) and isinstance(reference.get("tag"), str)
        }
        clips = project.get("clips", [])
        for clip in clips if isinstance(clips, list) else []:
            if isinstance(clip, dict) and isinstance(clip.get("clip_id"), str):
                current_clips[(project_id, clip["clip_id"])] = clip

    consumed_historical_keys: set[tuple[str, str, int, int]] = set()
    for path in sorted((root / "examples").rglob("*.json")) if (root / "examples").exists() else []:
        rel = path.relative_to(root).as_posix()
        is_take_review = is_take_review_path(path)
        if is_take_review and path.parent.resolve() in review_indexes:
            # The directory index already loaded and validated this candidate
            # through the stable, bounded authority reader. Invalid, excluded,
            # oversized, and over-budget candidates are represented by its
            # diagnostics and must never be re-read by the generic JSON path.
            continue
        try:
            obj = (
                load_bounded_take_review(path)
                if is_take_review
                else load_json(path, root=root)
            )
        except Exception as exc:
            errors.append(f"{rel}: invalid JSON: {exc}")
            continue
        if not isinstance(obj, dict):
            errors.append(f"{rel}: JSON example must be an object")
            continue
        is_take_review = looks_like_take_review(path, obj)
        if looks_like_clip_contract(path, obj):
            parent_kind, _ = classify_parent_id(obj)
            if parent_kind == "invalid":
                errors.append(f"{rel}: parent_clip_id must be null or a non-empty string")
            sequence_index = json_integer(obj.get("sequence_index"))
            if parent_kind == "root" and sequence_index is not None and sequence_index > 1:
                errors.append(
                    f"{rel}: later clip sequence_index {obj.get('sequence_index')} "
                    "must declare a non-empty parent_clip_id"
                )
            if parent_kind == "parent" and sequence_index == 1:
                errors.append(
                    f"{rel}: first clip sequence_index {obj.get('sequence_index')} "
                    "must not declare parent_clip_id"
                )
            status = obj.get("status")
            clip_id = obj.get("clip_id")
            if (
                isinstance(status, str)
                and status in ACCEPTED_PARENT_STATUSES
                and not has_usable_observed_end_state(obj)
            ):
                errors.append(
                    f"{rel}: accepted clip {clip_id} observed_end_state "
                    "must be a non-empty object"
                )
            elif status == "rejected" and (
                "observed_end_state" not in obj
                or obj["observed_end_state"] is not None
            ):
                errors.append(
                    f"{rel}: rejected clip {clip_id} observed_end_state must be null"
                )
            felt = obj.get("felt_intent")
            if "felt_intent" in obj and (not isinstance(felt, str) or not felt.strip()):
                errors.append(f"{rel}: felt_intent must be a non-empty one-line string")
            if set(obj.get("this_clip_only", [])) & set(obj.get("reserved_for_later", [])):
                errors.append(f"{rel}: current and reserved beats overlap")
            prompt_path = path.parent / f"{str(obj.get('clip_id', '')).replace('_', '-')}-prompt.md"
            prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else None
            project_id = obj.get("project_id")
            clip_id = obj.get("clip_id")
            lookup_key = (
                (project_id, clip_id)
                if isinstance(project_id, str) and isinstance(clip_id, str)
                else None
            )
            validate_contract(
                obj,
                rel,
                errors,
                strict=args.strict,
                current_clip=current_clips.get(lookup_key) if lookup_key is not None else None,
                prompt=prompt,
                current_project_version=(
                    current_project_versions.get(project_id)
                    if isinstance(project_id, str)
                    else None
                ),
                source_references=(
                    current_project_references.get(project_id)
                    if isinstance(project_id, str)
                    else None
                ),
                historical_ledger=historical_ledger,
                consumed_historical_keys=consumed_historical_keys,
            )
        if is_take_review:
            errors.extend(validate_take_review_record(obj, rel))

    check_provenance_ledger_consumption(
        historical_ledger,
        consumed_historical_keys,
        errors,
    )

    for schema in (root / "schemas").glob("*.schema.json") if (root / "schemas").exists() else []:
        try:
            load_json(schema, root=root)
        except Exception as exc:
            errors.append(f"{schema.relative_to(root).as_posix()}: invalid JSON: {exc}")

    errors = bound_diagnostics(errors, "additional project-state diagnostics omitted")
    if errors:
        print("Project state errors:")
        for error in errors:
            print(diagnostic_text(f"- {error}"))
        return 1
    print(diagnostic_text(f"Project state check passed: {len(paths)} project states."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

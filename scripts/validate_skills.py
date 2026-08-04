#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

if __package__:
    from .strict_json import (
        diagnostic_path,
        diagnostic_text,
        load_json,
        load_jsonl,
        read_repo_text,
        validate_repo_input_path,
    )
else:
    from strict_json import (
        diagnostic_path,
        diagnostic_text,
        load_json,
        load_jsonl,
        read_repo_text,
        validate_repo_input_path,
    )

EXPECTED_SKILLS = [
    "seedance-antislop", "seedance-audio", "seedance-camera", "seedance-characters", "seedance-continuation",
    "seedance-copyright", "seedance-examples-ja", "seedance-examples-ko", "seedance-examples-zh", "seedance-filter", "seedance-interview",
    "seedance-interview-short", "seedance-lighting", "seedance-motion", "seedance-pipeline",
    "seedance-prompt", "seedance-prompt-short", "seedance-recipes", "seedance-style",
    "seedance-sequence", "seedance-troubleshoot", "seedance-vfx", "seedance-vocab-en", "seedance-vocab-es", "seedance-vocab-ja",
    "seedance-vocab-ko", "seedance-vocab-ru", "seedance-vocab-zh",
]

EXPECTED_VERSION = "6.7.0"

REQUIRED_REFERENCES = [
    "references/api-status.md",
    "references/source-registry.md",
    "references/research-2026-05-30.md",
    "references/agent-compatibility.md",
    "references/api-workflow.md",
    "references/capability-map.md",
    "references/directors-read.md",
    "references/directing-engine.md",
    "references/directing-engine-genre-library.md",
    "references/model-mechanics.md",
    "references/retake-protocol.md",
    "references/allocation-model.md",
    "references/multishot-grammar.md",
    "references/2d-anime-grammar.md",
    "references/pro-filmmaking-standards.md",
    "references/cinematography-shot-language.md",
    "references/shot-list-continuity.md",
    "references/color-pipeline-aces.md",
    "references/aspect-ratio-delivery.md",
    "references/subtitles-localization.md",
    "references/audio-post-delivery.md",
    "references/delivery-qc.md",
    "references/examples-by-mode.md",
    "references/multilingual-community-examples.md",
    "references/multilingual-native-review.md",
    "references/platform-surface-matrix.md",
    "references/model-name-map.md",
    "references/first-last-frame-guide.md",
    "references/field-observed-tips.md",
    "references/community-source-methodology.md",
    "references/platform-constraints.md",
    "references/quick-ref.md",
    "references/audio-guide.md",
    "references/anti-slop-lexicon.md",
    "references/filter-vocab.md",
    "references/frontend-design-system.md",
    "references/json-schema.md",
    "references/reference-workflow.md",
    "references/i2v-guide.md",
    "references/genre-guides.md",
    "references/storytelling-framework.md",
    "references/intent-vs-precision.md",
    "references/eval-rubric.md",
    "references/progressive-disclosure.md",
    "references/prompt-examples.md",
    "references/sequence-project-state.md",
    "references/continuation-handoff.md",
    "references/prompt-compiler.md",
    "references/reference-transfer-contract.md",
    "references/dense-storyboard-mode.md",
    "references/surface-prompt-profiles.md",
    "references/event-density.md",
    "references/continuity-qc.md",
    "references/failure-atlas.md",
    "references/sequence-worked-trace.md",
    "references/vocab/en.md",
    "references/vocab/zh.md",
    "references/vocab/ja.md",
    "references/vocab/ko.md",
    "references/vocab/es.md",
    "references/vocab/ru.md",
]

REQUIRED_FILES = [
    "README.md",
    "SKILL.md",
    "CHANGELOG.md",
    "requirements-masthead.lock",
    "V6_SEQUENCE_PROMPT_COMPILER_MANIFEST.md",
    "scripts/validate_repo.py",
    "scripts/validate_skills.py",
    "scripts/content_audit.py",
    "scripts/eval_schema_check.py",
    "scripts/eval_run.py",
    "scripts/design_audit.py",
    "scripts/install_codex_skill.py",
    "scripts/source_registry_check.py",
    "scripts/vocab_schema_check.py",
    "scripts/prompt_lint.py",
    "scripts/strict_json.py",
    "scripts/lineage_contract.py",
    "scripts/project_state_check.py",
    "scripts/continuity_chain_check.py",
    "scripts/behavior_contract_check.py",
    "scripts/sequence_eval_check.py",
    "scripts/generation_run_check.py",
    "scripts/extract_last_frame.py",
    "validation/install-payload.txt",
    "tests/test_authoring_state.py",
    ".github/workflows/validate-skills.yml",
    "agents/openai.yaml",
    "evals/evals.json",
    "evals/generation-benchmark.json",
    "evals/multilingual-native-review.json",
    "evals/multilingual-native-review-evidence.json",
    "tests/test_multilingual_native_review.py",
    "data/sources.seedance-2026-05-30.json",
    "data/community-patterns.seedance-2026-05-30.json",
    "data/generation-runs.example.jsonl",
    "schemas/project-state.schema.json",
    "schemas/clip-contract.schema.json",
    "schemas/take-review.schema.json",
    "schemas/prompt-spec.schema.json",
    "schemas/generation-run.schema.json",
    "validation/authoring-state-provenance-ledger.json",
    "validation/fixtures/directors-read-cases.json",
    "examples/sequence-airport-arrival/project-state.json",
    "examples/sequence-airport-arrival/sequence-plan.md",
    "examples/sequence-airport-arrival/clip-01-contract.json",
    "examples/sequence-airport-arrival/clip-01-prompt.md",
    "examples/sequence-airport-arrival/clip-01-take-review.json",
    "examples/sequence-airport-arrival/clip-02-continuation-contract.json",
    "examples/sequence-airport-arrival/clip-02-prompt.md",
    "examples/sequence-observed-deviation/project-state-before.json",
    "examples/sequence-observed-deviation/take-review.json",
    "examples/sequence-observed-deviation/project-state-after.json",
    "examples/sequence-mixed-lane/project-state.json",
    "examples/standalone-clip/project-state.json",
    "examples/standalone-clip/prompt.md",
    "examples/golden-prompts/compact-i2v.md",
    "examples/golden-prompts/r2v-role-isolation.md",
    "examples/golden-prompts/phased-single-take.md",
    "examples/golden-prompts/dense-2d-storyboard.md",
    "examples/golden-prompts/sequence-continuation.md",
    "examples/golden-prompts/continuation-observed-deviation.md",
    "examples/golden-prompts/first-last-frame-transition.md",
    "examples/golden-prompts/video-edit-one-layer.md",
    "assets/hero-command-center.png",
    "assets/hero-global-filmmaker-mode.png",
    "assets/infographic-skill-capabilities.png",
    "assets/infographic-cdn-delivery-map.png",
    "assets/infographic-reference-role-map.png",
    "assets/infographic-production-delivery.png",
    "assets/infographic-professional-qc-stack.png",
    "assets/hero-cinematic.png",
    "assets/skill-os-infographic.png",
    "assets/skill-map-cinematic.png",
    "assets/hero-dark.svg",
    "assets/hero-light.svg",
    "assets/skill-map.svg",
    "docs/frontend-redesign.md",
    "docs/v6-release-readiness.md",
    "docs/README.zh.md",
    "docs/README.ja.md",
    "docs/README.ko.md",
]

REQUIRED_FIELDS = ["name", "description", "license", "user-invocable", "tags", "metadata"]

OPAQUE_ROUTE_RE = re.compile(
    r"\[(?P<kind>skill|ref):(?P<name>[^\]\r\n]+)\]",
    re.IGNORECASE,
)
MARKDOWN_LINK_RE = re.compile(
    r"(?<!!)\[[^\]\r\n]+\]\((?P<target><[^>\r\n]+>|[^)\r\n]+)\)"
)
UNLINKED_ROUTE_RE = re.compile(
    r"`(?P<target>(?:\.{0,2}/)*(?:(?:skills|references)[\\/])?"
    r"[A-Za-z0-9][A-Za-z0-9_./\\-]*\.md(?:#[A-Za-z0-9_-]+)?)`",
    re.IGNORECASE,
)
UNLINKED_ROUTE_DIRECTIVE_RE = re.compile(
    r"\b(?:load|read|open|consult|follow|see|use|check|review|route\s+to)\b",
    re.IGNORECASE,
)
MUTATION_ROUTE_VERBS = r"(?:record|write|append|save|store|log|update|edit|add)"
UNLINKED_ROUTE_MUTATION_DIRECTIVE_RE = re.compile(
    r"(?P<directive>"
    r"^[ \t]*(?:>[ \t]*)*(?:#{1,6}[ \t]+)?"
    r"(?:(?:[-*+]|\d+[.)])[ \t]+)?(?:\[[ xX]\][ \t]+)?"
    r"(?:\*{1,2}|_{1,2})?"
    r"(?:(?:please|always|never|carefully|immediately|securely|promptly|finally|"
    r"next|afterward|afterwards)[ \t]+)?"
    r"(?:\*{1,2}|_{1,2})?"
    rf"(?P<line_verb>{MUTATION_ROUTE_VERBS})(?:\*{{1,2}}|_{{1,2}})?(?!\w)|"
    r"\b(?:you\s+need\s+to|you\s+are\s+required\s+to|be\s+sure\s+to|"
    r"remember\s+to|do\s+not|please|then|must|should|shall|carefully|"
    r"immediately|securely|promptly|finally|next|afterward|afterwards)[ \t]+"
    r"(?:\*{1,2}|_{1,2})?"
    rf"(?P<modal_verb>{MUTATION_ROUTE_VERBS})(?:\*{{1,2}}|_{{1,2}})?(?!\w)|"
    rf"[,;:][ \t]*(?:\*{{1,2}}|_{{1,2}})?"
    rf"(?P<punct_verb>{MUTATION_ROUTE_VERBS})(?:\*{{1,2}}|_{{1,2}})?(?!\w)"
    r")",
    re.IGNORECASE | re.MULTILINE,
)
MUTATION_NOUN_PREDICATE_RE = re.compile(
    r"^[ \t]+(?:is|are|was|were|means?|refers?|denotes?|names?|appears?|"
    r"occurs?|exists?|serves?|contains?|includes?|lists?|shows?|stores?|defines?)\b",
    re.IGNORECASE,
)
MUTATION_NOUN_TAIL_RE = re.compile(
    r"(?:^[ \t]*(?:type|count|format|field|class|name|label|schema|entry|"
    r"example|term|word|noun)s?\b(?:[ \t]*:|[^.!?;:\r\n]{0,100}\b"
    r"(?:is|are|was|were|means?|refers?|denotes?|names?|contains?|includes?|"
    r"lists?|shows?|stores?|defines?)\b)|"
    r"\b(?:is|are|was|were)\s+(?:stored|listed|defined|shown|documented|named)\b)",
    re.IGNORECASE,
)
RECORD_NOMINAL_TAIL_RE = re.compile(
    r"^[ \t]+(?:keeping|management|formatting|layout|schema|structure|syntax)\b",
    re.IGNORECASE,
)
ROUTE_SEGMENT_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")
ROUTE_ANCHOR_RE = re.compile(r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?")
INSTALL_PAYLOAD_MANIFEST = PurePosixPath("validation/install-payload.txt")


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _heading_anchors(path: Path, root: Path) -> set[str]:
    """Return the deterministic Markdown heading anchors this validator supports."""

    anchors: set[str] = set()
    seen: dict[str, int] = {}
    for line in read_repo_text(root=root, path=path).splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        heading = re.sub(r"[`*_~]", "", match.group(1)).strip().lower()
        base = re.sub(r"[^\w\- ]", "", heading, flags=re.UNICODE)
        base = re.sub(r"\s+", "-", base).strip("-")
        if not base:
            continue
        duplicate = seen.get(base, 0)
        seen[base] = duplicate + 1
        anchors.add(base if duplicate == 0 else f"{base}-{duplicate}")
    return anchors


def _find_exact_case_path(root: Path, parts: tuple[str, ...]) -> tuple[Path | None, str | None]:
    """Walk by directory entries so Windows cannot hide a route's case mismatch."""

    current = root
    for part in parts:
        try:
            names = {entry.name: entry for entry in current.iterdir()}
        except OSError:
            return None, None
        if part in names:
            current = names[part]
            continue
        folded = sorted(name for name in names if name.casefold() == part.casefold())
        return None, folded[0] if folded else None
    return current, None


def active_runtime_markdown_paths(root: Path) -> tuple[Path, ...]:
    """Return manifest-shipped Markdown that can participate in runtime routing.

    Release notes, examples, and the preserved ``references/migrated`` tree ship
    for readers, but they are not active agent guidance. Keeping the scope tied
    to the install manifest prevents a repository-only document from silently
    becoming part of the installed routing contract.
    """

    manifest = root / INSTALL_PAYLOAD_MANIFEST
    if not os.path.lexists(manifest):
        return ()
    manifest = validate_repo_input_path(root, manifest)

    active: list[Path] = []
    for raw_line in read_repo_text(root=root, path=manifest).splitlines():
        relative = raw_line.strip()
        if not relative or relative.startswith("#"):
            continue
        portable = PurePosixPath(relative)
        if portable.suffix != ".md":
            continue
        parts = portable.parts
        is_root = parts == ("SKILL.md",)
        is_skill = bool(parts) and parts[0] == "skills"
        is_reference = (
            bool(parts)
            and parts[0] == "references"
            and not (len(parts) >= 2 and parts[1] == "migrated")
        )
        if is_root or is_skill or is_reference:
            active.append(root.joinpath(*parts))
    return tuple(active)


def _lexical_route_target(
    source_parent_parts: tuple[str, ...],
    raw_parts: list[str],
) -> tuple[tuple[str, ...], bool]:
    """Resolve POSIX path parts lexically and report root escape attempts."""

    target_parts = list(source_parent_parts)
    escaped = False
    for part in raw_parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if target_parts:
                target_parts.pop()
            else:
                escaped = True
            continue
        target_parts.append(part)
    return tuple(target_parts), escaped


def _canonical_relative_route(
    source_parent_parts: tuple[str, ...],
    target_parts: tuple[str, ...],
) -> str:
    """Return the shortest portable path from a runtime file to its target."""

    common = 0
    for source_part, target_part in zip(source_parent_parts, target_parts):
        if source_part != target_part:
            break
        common += 1
    parts = ("..",) * (len(source_parent_parts) - common) + target_parts[common:]
    return "/".join(parts) or "."


def _unlinked_route_instructions(
    text: str,
    path: Path,
    root: Path,
) -> tuple[re.Match[str], ...]:
    """Return actionable code-form routes while ignoring descriptive prose.

    A backticked Markdown filename is not automatically a route: runtime docs
    also describe package layouts, filenames, and generated artifacts. Treat it
    as an unlinked route only when the same sentence directs the agent to load,
    read, open, consult, follow, see, use, check, review, or route to that file,
    or when a bounded imperative tells the agent to record, write, append, save,
    store, log, update, edit, or add material at that path.
    Root-qualified ``skills/`` and ``references/`` paths are always route-shaped;
    a short filename is route-shaped only when it resolves inside those active
    runtime trees. Code-form labels that are already inside Markdown links are
    excluded.
    """

    root = root.resolve()
    source_parent_parts = path.parent.resolve().relative_to(root).parts
    active_by_name: dict[str, list[Path]] = {}
    for active_path in active_runtime_markdown_paths(root):
        active_by_name.setdefault(active_path.name.casefold(), []).append(active_path)
    matches: list[re.Match[str]] = []
    for match in UNLINKED_ROUTE_RE.finditer(text):
        # ``[`label.md`](target.md)`` is already a real Markdown link.
        if (
            match.start() > 0
            and text[match.start() - 1] == "["
            and text[match.end() :].startswith("](")
        ):
            continue

        raw_target = match.group("target").replace("\\", "/")
        route_path = raw_target.partition("#")[0]
        raw_parts = route_path.split("/")
        explicit_root = bool(raw_parts) and raw_parts[0].casefold() in {
            "skills",
            "references",
        }
        if explicit_root:
            route_shaped = True
        else:
            target_parts, escaped = _lexical_route_target(source_parent_parts, raw_parts)
            basename_matches = active_by_name.get(PurePosixPath(route_path).name.casefold(), [])
            route_shaped = (
                not escaped
                and bool(target_parts)
                and target_parts[0].casefold() in {"skills", "references"}
                and root.joinpath(*target_parts).is_file()
            ) or len(basename_matches) == 1
        if not route_shaped:
            continue

        sentence_start = 0
        for boundary in re.finditer(
            r"(?:\n|[.!?;](?=\s|$))",
            text[: match.start()],
        ):
            sentence_start = boundary.end()
        directive_prefix = text[sentence_start : match.start()]
        # A write-back target may be placed on the next Markdown list line, for
        # example ``Record the result in:\n- `references/...` ``.  Keep this
        # grammar separate from read/load routing: widening the ordinary
        # sentence window would turn unrelated filenames in later prose into
        # routes.  The tail must bind the verb directly to the target, either
        # immediately or through an explicit destination preposition/colon.
        paragraph_break = text.rfind("\n\n", 0, match.start())
        paragraph_start = paragraph_break + 2 if paragraph_break >= 0 else 0
        record_context_start = max(paragraph_start, match.start() - 512)
        record_prefix = text[record_context_start : match.start()]
        mutation_directive = False
        for mutation_match in UNLINKED_ROUTE_MUTATION_DIRECTIVE_RE.finditer(record_prefix):
            tail = record_prefix[mutation_match.end() :]
            boundary_tail = re.sub(
                r"(?m)^[ \t]*\d+[.)][ \t]+", "", tail
            )
            if (
                len(tail) > 240
                or re.search(r"[.!?;]", boundary_tail)
                or re.search(r"\r?\n[ \t]*\r?\n", tail)
            ):
                continue
            if MUTATION_NOUN_TAIL_RE.search(tail):
                continue
            mutation_verb = next(
                (
                    mutation_match.group(name)
                    for name in ("line_verb", "modal_verb", "punct_verb")
                    if mutation_match.group(name) is not None
                ),
                "",
            )
            if mutation_verb.casefold() == "record" and RECORD_NOMINAL_TAIL_RE.match(tail):
                continue
            # ``Record `path` is a noun ...`` starts with the same spelling as
            # the imperative.  A direct target followed by a copular or
            # definitional predicate is descriptive prose, not a write action.
            direct_target = tail.strip() == ""
            target_suffix = text[match.end() :]
            if direct_target and MUTATION_NOUN_PREDICATE_RE.match(target_suffix):
                continue
            mutation_directive = True
            break
        if (
            UNLINKED_ROUTE_DIRECTIVE_RE.search(directive_prefix)
            or mutation_directive
        ):
            matches.append(match)
    return tuple(matches)


def validate_portable_routes(
    path: Path,
    root: Path,
    errors: list[str],
    *,
    require_routes: bool = True,
) -> None:
    """Validate explicit Markdown routes without claiming client auto-loading.

    Nested runtime files may legitimately climb to a sibling directory, so a
    route is resolved relative to the file that contains it and then checked
    against the canonical repository-relative target.
    """

    path = validate_repo_input_path(root, path)
    text = read_repo_text(root=root, path=path)
    root = root.resolve()
    rel = path.relative_to(root).as_posix()

    for match in OPAQUE_ROUTE_RE.finditer(text):
        kind = match.group("kind")
        name = match.group("name")
        line = _line_number(text, match.start())
        label = f"[{kind}:{name}]"
        errors.append(
            f"{rel}:{line}: opaque route `{label}` has no portable relative path; "
            "use an ordinary relative Markdown link"
        )

    for match in _unlinked_route_instructions(text, path, root):
        line = _line_number(text, match.start())
        errors.append(
            f"{rel}:{line}: route `{match.group('target')}` is code text, not a Markdown link"
        )

    routes: list[tuple[re.Match[str], str]] = []
    source_parent_parts = path.parent.resolve().relative_to(root).parts
    for match in MARKDOWN_LINK_RE.finditer(text):
        destination = match.group("target").strip()
        if destination.startswith("<") and destination.endswith(">"):
            destination = destination[1:-1]
        parsed_hint = urlsplit(destination)
        if parsed_hint.scheme.casefold() in {"http", "https", "mailto"}:
            continue
        hinted_target = unquote(parsed_hint.path).replace("\\", "/")
        path_parts = hinted_target.split("/")
        target_parts, _ = _lexical_route_target(source_parent_parts, path_parts)
        names_a_route_root = any(
            part.casefold() in {"skills", "references"} for part in path_parts
        )
        resolves_to_runtime_markdown = (
            hinted_target.casefold().endswith(".md")
            and bool(target_parts)
            and target_parts[0].casefold() in {"skills", "references"}
        )
        if names_a_route_root or resolves_to_runtime_markdown:
            routes.append((match, destination))

    if require_routes and not routes:
        errors.append(f"{rel}: no portable root route links found")

    for match, destination in routes:
        line = _line_number(text, match.start())
        parsed = urlsplit(destination)
        target = unquote(parsed.path)
        fragment = unquote(parsed.fragment)

        if (
            parsed.scheme
            or parsed.netloc
            or target.startswith("/")
            or re.match(r"^[A-Za-z]:", destination)
        ):
            errors.append(f"{rel}:{line}: route path must be relative: {destination}")
            continue
        if parsed.query:
            errors.append(f"{rel}:{line}: route path must not contain a query: {destination}")
            continue
        if target != parsed.path or fragment != parsed.fragment:
            errors.append(
                f"{rel}:{line}: route must not hide path or anchor characters with percent encoding: "
                f"{destination}"
            )
            continue
        if "\\" in target:
            errors.append(f"{rel}:{line}: route path must use forward slashes: {destination}")
            continue
        if any(character.isspace() for character in target):
            errors.append(f"{rel}:{line}: route path must not contain whitespace: {destination}")
            continue
        if destination.endswith("#"):
            errors.append(f"{rel}:{line}: route fragment must not be empty: {destination}")
            continue
        if fragment and ROUTE_ANCHOR_RE.fullmatch(fragment) is None:
            errors.append(
                f"{rel}:{line}: route fragment must be a lowercase Markdown anchor: {fragment}"
            )
            continue
        raw_parts = target.split("/")
        if any(part == "" for part in raw_parts):
            errors.append(f"{rel}:{line}: route path must not contain empty segments: {destination}")
            continue

        target_parts, escaped = _lexical_route_target(source_parent_parts, raw_parts)
        if escaped:
            errors.append(
                f"{rel}:{line}: route path must not traverse outside the skill root: {destination}"
            )
            continue
        canonical = _canonical_relative_route(source_parent_parts, target_parts)
        if target != canonical:
            errors.append(
                f"{rel}:{line}: route path must not traverse redundantly; "
                f"use canonical relative path `{canonical}`: {destination}"
            )
            continue

        if not target_parts:
            errors.append(f"{rel}:{line}: route target is not a file: {target}")
            continue
        route_root = target_parts[0]
        if route_root.casefold() == "skills" and route_root != "skills":
            errors.append(f"{rel}:{line}: route path must use exact lowercase `skills/`: {target}")
            continue
        if route_root.casefold() == "references" and route_root != "references":
            errors.append(f"{rel}:{line}: route path must use exact lowercase `references/`: {target}")
            continue

        if route_root == "skills":
            parts = target_parts
            valid = (
                len(parts) == 3
                and ROUTE_SEGMENT_RE.fullmatch(parts[1]) is not None
                and parts[2] == "SKILL.md"
            )
            expected_shape = "skills/<skill-name>/SKILL.md"
        else:
            parts = target_parts
            stem_parts = parts[1:-1] + (PurePosixPath(parts[-1]).stem,)
            valid = (
                route_root == "references"
                and len(parts) >= 2
                and parts[-1].endswith(".md")
                and all(ROUTE_SEGMENT_RE.fullmatch(part) for part in stem_parts)
            )
            expected_shape = "references/<reference-name>.md"
        if not valid:
            errors.append(f"{rel}:{line}: route path must match `{expected_shape}`: {target}")
            continue

        exact_path, case_match = _find_exact_case_path(root, target_parts)
        if exact_path is None:
            if case_match is not None:
                errors.append(
                    f"{rel}:{line}: route path case mismatch at `{case_match}`: {target}"
                )
            else:
                errors.append(f"{rel}:{line}: route target is not a file: {target}")
            continue
        try:
            resolved = exact_path.resolve(strict=True)
        except OSError:
            errors.append(f"{rel}:{line}: route target is not a file: {target}")
            continue
        if resolved != root and root not in resolved.parents:
            errors.append(f"{rel}:{line}: route resolves outside the skill root: {target}")
            continue
        if not exact_path.is_file():
            errors.append(f"{rel}:{line}: route target is not a file: {target}")
            continue
        if fragment and fragment not in _heading_anchors(exact_path, root):
            errors.append(
                f"{rel}:{line}: route fragment does not resolve in {target}: #{fragment}"
            )


def tracked_files(root: Path) -> set[str] | None:
    """Repository-relative paths git tracks, or None outside a git checkout.

    None means the question "is this committed?" has no answer here - an
    unpacked ZIP has no index - so callers treat nothing as committed.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return {part.decode("utf-8", "replace") for part in proc.stdout.split(b"\0") if part}


def split_frontmatter(text: str) -> tuple[str, str]:
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter must start with a standalone --- line")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("frontmatter must end with a standalone --- line") from exc
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1:])


def top_keys(frontmatter: str) -> list[str]:
    keys = []
    for line in frontmatter.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            keys.append(line.split(":", 1)[0].strip())
    return keys


def value_for(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.*)$", frontmatter, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] in {'\"', "'"} and value[-1] == value[0]:
        value = value[1:-1]
    return value


def metadata_value(frontmatter: str, key: str) -> str | None:
    in_metadata = False
    for line in frontmatter.splitlines():
        if line.startswith("metadata:"):
            in_metadata = True
            continue
        if in_metadata and line and not line.startswith(" "):
            break
        if in_metadata:
            match = re.match(rf"^\s+{re.escape(key)}:\s*(.*)$", line)
            if match:
                value = match.group(1).strip()
                if len(value) >= 2 and value[0] in {'\"', "'"} and value[-1] == value[0]:
                    value = value[1:-1]
                return value
    return None


def validate_skill(path: Path, root: Path, errors: list[str], warnings: list[str]) -> None:
    rel = path.relative_to(root).as_posix()
    try:
        path = validate_repo_input_path(root, path)
        text = read_repo_text(root=root, path=path)
    except (OSError, ValueError) as exc:
        errors.append(f"{rel}: {diagnostic_text(exc)}")
        return
    try:
        frontmatter, body = split_frontmatter(text)
    except Exception as exc:
        errors.append(f"{rel}: {exc}")
        return

    keys = top_keys(frontmatter)
    for field in REQUIRED_FIELDS:
        if field not in keys:
            errors.append(f"{rel}: missing top-level field `{field}`")

    if "parent" in keys:
        errors.append(f"{rel}: illegal top-level `parent`; use metadata.parent")

    name = value_for(frontmatter, "name")
    if path != root / "SKILL.md" and path.name == "SKILL.md" and path.parent.name.startswith("seedance-") and name != path.parent.name:
        errors.append(f"{rel}: name `{name}` does not match folder `{path.parent.name}`")

    if path != root / "SKILL.md":
        if metadata_value(frontmatter, "parent") != "seedance-20":
            errors.append(f"{rel}: missing metadata.parent: seedance-20")

    if metadata_value(frontmatter, "version") != EXPECTED_VERSION:
        errors.append(f"{rel}: metadata.version must be {EXPECTED_VERSION}")

    if path != root / "SKILL.md" and "## Intent" not in body:
        errors.append(f"{rel}: sub-skill missing a `## Intent` section")

    description = value_for(frontmatter, "description") or ""
    if not description.startswith("This skill should be used when"):
        errors.append(f"{rel}: description must use third-person activation wording")

    if len(body.strip()) < 200:
        warnings.append(f"{rel}: body is very short")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    valid_required_paths: set[str] = set()
    for rel in REQUIRED_FILES + REQUIRED_REFERENCES:
        path = root / rel
        if not os.path.lexists(path):
            errors.append(f"missing required file: {rel}")
            continue
        try:
            validate_repo_input_path(root, path)
        except (OSError, ValueError) as exc:
            errors.append(f"{diagnostic_path(rel)}: {diagnostic_text(exc)}")
            continue
        valid_required_paths.add(rel)

    structured_inputs: dict[str, object] = {}
    for rel in REQUIRED_FILES:
        if rel not in valid_required_paths:
            continue
        path = root / rel
        try:
            if path.suffix == ".json":
                structured_inputs[rel] = load_json(path, root=root)
            elif path.suffix == ".jsonl":
                structured_inputs[rel] = load_jsonl(
                    path,
                    expected_type=dict,
                    root=root,
                )
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(
                f"{diagnostic_path(rel)} parse error: {diagnostic_text(exc)}"
            )

    skill_root = root / "skills"
    dirs = sorted(path.name for path in skill_root.glob("seedance-*") if path.is_dir()) if skill_root.exists() else []
    missing = sorted(set(EXPECTED_SKILLS) - set(dirs))
    extra = sorted(set(dirs) - set(EXPECTED_SKILLS))
    if missing:
        errors.append("missing expected skill dirs: " + ", ".join(missing))
    if extra:
        warnings.append("extra skill dirs: " + ", ".join(extra))

    if "SKILL.md" in valid_required_paths:
        validate_skill(root / "SKILL.md", root, errors, warnings)
    for name in EXPECTED_SKILLS:
        path = root / "skills" / name / "SKILL.md"
        if os.path.lexists(path):
            validate_skill(path, root, errors, warnings)

    for path in active_runtime_markdown_paths(root):
        if not path.is_file():
            errors.append(
                "active runtime Markdown declared by the install manifest is missing: "
                + path.relative_to(root).as_posix()
            )
            continue
        is_root_skill = path == root / "SKILL.md"
        validate_portable_routes(
            path,
            root,
            errors,
            require_routes=is_root_skill,
        )


    # Only bytecode git actually tracks is a finding. Importing any module here
    # writes __pycache__, so flagging it on sight failed for anyone who ran the
    # tests before the validators - the files are gitignored and were never
    # committed, but the error said they were. CI never saw it because the
    # workflow sets PYTHONDONTWRITEBYTECODE.
    tracked = tracked_files(root)

    def is_committed(rel: str) -> bool:
        return rel in tracked if tracked is not None else False

    pycache = root / "scripts" / "__pycache__"
    if pycache.exists() and any(
        is_committed(item.relative_to(root).as_posix())
        for item in pycache.rglob("*")
        if item.is_file()
    ):
        errors.append("scripts/__pycache__ must not be committed")
    for pyc in root.rglob("*.pyc"):
        rel = pyc.relative_to(root).as_posix()
        if not rel.startswith(".seedance_backups/") and is_committed(rel):
            errors.append(f"compiled Python cache must not be committed: {rel}")

    data = structured_inputs.get("evals/evals.json")
    if isinstance(data, dict):
        cases = data.get("cases", [])
        if not isinstance(cases, list) or len(cases) < 16:
            errors.append("evals/evals.json must contain at least 16 cases")

    for rel in [
        "scripts/validate_repo.py",
        "scripts/validate_skills.py",
        "scripts/content_audit.py",
        "scripts/eval_schema_check.py",
        "scripts/design_audit.py",
        "scripts/install_codex_skill.py",
        "scripts/source_registry_check.py",
        "scripts/vocab_schema_check.py",
        "scripts/prompt_lint.py",
        "scripts/strict_json.py",
        "scripts/lineage_contract.py",
        "scripts/project_state_check.py",
        "scripts/continuity_chain_check.py",
        "scripts/behavior_contract_check.py",
        "scripts/sequence_eval_check.py",
        "scripts/generation_run_check.py",
    "scripts/extract_last_frame.py",
    ]:
        path = root / rel
        if os.path.lexists(path):
            try:
                line_count = len(read_repo_text(root=root, path=path).splitlines())
            except (OSError, ValueError) as exc:
                errors.append(f"{rel}: {diagnostic_text(exc)}")
                continue
            if line_count < 20:
                errors.append(f"{rel}: script appears collapsed or incomplete ({line_count} lines)")

    installer = root / "scripts" / "install_codex_skill.py"
    if os.path.lexists(installer):
        installer_text = read_repo_text(root=root, path=installer)
        if re.search(r"IGNORE_NAMES\s*=\s*{[^}]*[\"']docs[\"']", installer_text, re.S):
            errors.append("scripts/install_codex_skill.py must include docs/ because README links native zh/ja/ko guides")

    openai_yaml = root / "agents" / "openai.yaml"
    if os.path.lexists(openai_yaml):
        yaml_text = read_repo_text(root=root, path=openai_yaml)
        for required in [
            'display_name: "Seedance 2.0 Skill OS"',
            'short_description: "Professional Seedance video prompting"',
            'default_prompt: "Use $seedance-20',
            "allow_implicit_invocation: true",
        ]:
            if required not in yaml_text:
                errors.append(f"agents/openai.yaml missing `{required}`")

    disclosure = root / "references" / "progressive-disclosure.md"
    if os.path.lexists(disclosure):
        disclosure_text = read_repo_text(root=root, path=disclosure)
        for needed in ("directing-engine.md", "directing-engine-genre-library.md"):
            if needed not in disclosure_text:
                errors.append(f"progressive-disclosure.md must document the heavy reference {needed}")

    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(diagnostic_text(f"- {warning}"))
        print()

    if errors:
        print("ERRORS:")
        for error in errors:
            print(diagnostic_text(f"- {error}"))
        return 1

    print(
        diagnostic_text(
            f"Validated root plus {len(EXPECTED_SKILLS)} sub-skills and "
            f"required v{EXPECTED_VERSION} files."
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

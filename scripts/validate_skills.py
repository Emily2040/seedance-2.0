#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath

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
    "V6_SEQUENCE_PROMPT_COMPILER_MANIFEST.md",
    "scripts/validate_skills.py",
    "scripts/__init__.py",
    "scripts/strict_json.py",
    "scripts/content_audit.py",
    "scripts/eval_schema_check.py",
    "scripts/eval_run.py",
    "scripts/design_audit.py",
    "scripts/install_codex_skill.py",
    "scripts/source_registry_check.py",
    "scripts/vocab_schema_check.py",
    "scripts/prompt_lint.py",
    "scripts/project_state_check.py",
    "scripts/continuity_chain_check.py",
    "scripts/behavior_contract_check.py",
    "scripts/sequence_eval_check.py",
    "scripts/generation_run_check.py",
    "scripts/extract_last_frame.py",
    ".github/workflows/validate-skills.yml",
    "agents/openai.yaml",
    "evals/evals.json",
    "evals/generation-benchmark.json",
    "data/sources.seedance-2026-05-30.json",
    "data/community-patterns.seedance-2026-05-30.json",
    "data/generation-runs.example.jsonl",
    "schemas/project-state.schema.json",
    "schemas/clip-contract.schema.json",
    "schemas/take-review.schema.json",
    "schemas/prompt-spec.schema.json",
    "schemas/generation-run.schema.json",
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
    rel = diagnostic_path(path.relative_to(root))
    try:
        path = validate_repo_input_path(root, path)
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("skill input is not a regular file")
        text = read_repo_text(root=root, path=path)
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"{rel}: cannot read skill: {diagnostic_text(exc)}")
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
        errors.append(
            f"{rel}: name `{diagnostic_text(name)}` does not match folder "
            f"`{diagnostic_text(path.parent.name)}`"
        )

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
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    def read_required_text(rel: str, label: str) -> str | None:
        """Read only a previously validated in-repository regular path."""

        path = root / rel
        try:
            path = validate_repo_input_path(root, path)
            if not stat.S_ISREG(path.stat().st_mode):
                raise ValueError("required input is not a regular file")
            return read_repo_text(root=root, path=path)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(
                f"{diagnostic_path(rel)}: cannot inspect {label}: "
                f"{diagnostic_text(exc)}"
            )
            return None

    valid_required_paths: set[str] = set()
    for rel in REQUIRED_FILES + REQUIRED_REFERENCES:
        path = root / rel
        if not os.path.lexists(path):
            errors.append(f"missing required file: {diagnostic_path(rel)}")
            continue
        try:
            validated = validate_repo_input_path(root, path)
            if not stat.S_ISREG(validated.stat().st_mode):
                raise ValueError("required input is not a regular file")
        except (OSError, ValueError) as exc:
            errors.append(f"{diagnostic_path(rel)}: {diagnostic_text(exc)}")
            continue
        valid_required_paths.add(rel)

    structured_inputs: dict[str, object] = {}
    for rel in REQUIRED_FILES:
        path = root / rel
        if rel not in valid_required_paths:
            continue
        try:
            if path.suffix == ".json":
                structured_inputs[rel] = load_json(path, expected_type=dict, root=root)
            elif path.suffix == ".jsonl":
                structured_inputs[rel] = load_jsonl(path, expected_type=dict, root=root)
        except (OSError, ValueError) as exc:
            errors.append(
                f"{diagnostic_path(rel)} parse error: {diagnostic_text(exc)}"
            )

    skill_root = root / "skills"
    dirs: list[str] = []
    if os.path.lexists(skill_root):
        try:
            validate_repo_input_path(root, skill_root)
            for path in skill_root.glob("seedance-*"):
                try:
                    validated = validate_repo_input_path(root, path)
                except (OSError, ValueError) as exc:
                    errors.append(
                        f"{diagnostic_path(path.relative_to(root))}: "
                        f"{diagnostic_text(exc)}"
                    )
                    continue
                if stat.S_ISDIR(validated.stat().st_mode):
                    dirs.append(path.name)
            dirs.sort()
        except (OSError, ValueError) as exc:
            errors.append(f"skills: {diagnostic_text(exc)}")
    missing = sorted(set(EXPECTED_SKILLS) - set(dirs))
    extra = sorted(set(dirs) - set(EXPECTED_SKILLS))
    if missing:
        errors.append(
            "missing expected skill dirs: "
            + ", ".join(diagnostic_text(name) for name in missing)
        )
    if extra:
        warnings.append(
            "extra skill dirs: "
            + ", ".join(diagnostic_text(name) for name in extra)
        )

    if "SKILL.md" in valid_required_paths:
        validate_skill(root / "SKILL.md", root, errors, warnings)
    for name in EXPECTED_SKILLS:
        path = root / "skills" / name / "SKILL.md"
        if os.path.lexists(path):
            validate_skill(path, root, errors, warnings)

    # Only bytecode git actually tracks is a finding. Importing any module here
    # writes __pycache__, so flagging it on sight failed for anyone who ran the
    # tests before the validators - the files are gitignored and were never
    # committed, but the error said they were. CI never saw it because the
    # workflow sets PYTHONDONTWRITEBYTECODE.
    tracked = tracked_files(root)

    # Inspect the index instead of walking the checkout: a repository must not
    # be able to redirect this validator through an untrusted directory link.
    for raw_rel in sorted(tracked or ()):
        pure = PurePosixPath(raw_rel)
        if raw_rel.startswith(".seedance_backups/"):
            continue
        if pure.suffix == ".pyc":
            errors.append(
                "compiled Python cache must not be committed: "
                f"{diagnostic_path(raw_rel)}"
            )

    data = structured_inputs.get("evals/evals.json")
    if isinstance(data, dict):
        cases = data.get("cases", [])
        if not isinstance(cases, list) or len(cases) < 16:
            errors.append("evals/evals.json must contain at least 16 cases")

    for rel in [
        "scripts/validate_skills.py",
        "scripts/content_audit.py",
        "scripts/eval_schema_check.py",
        "scripts/design_audit.py",
        "scripts/install_codex_skill.py",
        "scripts/source_registry_check.py",
        "scripts/vocab_schema_check.py",
        "scripts/prompt_lint.py",
        "scripts/project_state_check.py",
        "scripts/continuity_chain_check.py",
        "scripts/behavior_contract_check.py",
        "scripts/sequence_eval_check.py",
        "scripts/generation_run_check.py",
        "scripts/extract_last_frame.py",
    ]:
        if rel in valid_required_paths:
            script_text = read_required_text(rel, "script")
            if script_text is None:
                continue
            line_count = len(script_text.splitlines())
            if line_count < 20:
                errors.append(
                    f"{diagnostic_path(rel)}: script appears collapsed or incomplete "
                    f"({line_count} lines)"
                )

    if "scripts/install_codex_skill.py" in valid_required_paths:
        installer_text = read_required_text(
            "scripts/install_codex_skill.py", "installer"
        )
        if installer_text is not None and re.search(
            r"IGNORE_NAMES\s*=\s*{[^}]*[\"']docs[\"']", installer_text, re.S
        ):
            errors.append("scripts/install_codex_skill.py must include docs/ because README links native zh/ja/ko guides")

    if "agents/openai.yaml" in valid_required_paths:
        yaml_text = read_required_text("agents/openai.yaml", "agent manifest")
        if yaml_text is not None:
            for required in [
                'display_name: "Seedance 2.0 Skill OS"',
                'short_description: "Professional Seedance video prompting"',
                'default_prompt: "Use $seedance-20',
                "allow_implicit_invocation: true",
            ]:
                if required not in yaml_text:
                    errors.append(f"agents/openai.yaml missing `{required}`")

    if "references/progressive-disclosure.md" in valid_required_paths:
        disclosure_text = read_required_text(
            "references/progressive-disclosure.md", "disclosure guide"
        )
        if disclosure_text is not None:
            for needed in (
                "directing-engine.md",
                "directing-engine-genre-library.md",
            ):
                if needed not in disclosure_text:
                    errors.append(
                        "progressive-disclosure.md must document the heavy "
                        f"reference {needed}"
                    )

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

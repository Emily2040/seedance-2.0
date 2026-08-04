#!/usr/bin/env python3
"""Run the canonical repository checks without requiring Git metadata.

The runner anchors child processes to the repository containing this file, so
it also works from an extracted archive, a nested caller directory, and paths
containing spaces. Git working-tree hygiene remains a separate checkout-only
check.
"""
from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SOURCE_DIRECTORIES = ("scripts", "tests")
MAX_PYTHON_SOURCE_FILES = 512
MAX_PYTHON_SOURCE_FILE_BYTES = 1 * 1024 * 1024
MAX_PYTHON_SOURCE_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class Check:
    name: str
    arguments: tuple[str, ...]

    @property
    def command(self) -> tuple[str, ...]:
        return (sys.executable, *self.arguments)

    def display_command(self) -> str:
        return " ".join(("python", *self.arguments))


def validation_plan(*, release: bool) -> tuple[Check, ...]:
    source_arguments = ["scripts/source_registry_check.py"]
    if release:
        source_arguments.append("--enforce-freshness")

    return (
        Check("Validate skill metadata and required files", ("scripts/validate_skills.py",)),
        Check("Audit stale and risky active wording", ("scripts/content_audit.py",)),
        Check("Validate eval schema", ("scripts/eval_schema_check.py",)),
        Check("Execute JSON Schemas", ("scripts/schema_check.py",)),
        Check("Audit README and SVG assets", ("scripts/design_audit.py",)),
        Check("Check the masthead generator", ("-I", "-S", "-B", "scripts/build_hero.py", "--check")),
        Check("Validate source freshness and claim labels", tuple(source_arguments)),
        Check("Validate multilingual vocabulary schema", ("scripts/vocab_schema_check.py", "--strict")),
        Check("Validate sequence project state", ("scripts/project_state_check.py", "--strict")),
        Check("Validate continuity chains", ("scripts/continuity_chain_check.py", "--strict")),
        Check("Validate behavior contracts", ("scripts/behavior_contract_check.py",)),
        Check("Validate sequence evals", ("scripts/sequence_eval_check.py",)),
        Check("Validate generation-run fixtures", ("scripts/generation_run_check.py",)),
        Check("Lint compiled prompts", ("scripts/prompt_lint.py", "--self-test", "--strict")),
        Check("Stress-test prompt architecture", ("scripts/prompt_architecture_stress.py", "--strict")),
        Check("Check eval harness wiring", ("scripts/eval_run.py", "--self-test")),
        Check("Check frame-extraction wiring", ("scripts/extract_last_frame.py", "--self-test")),
        Check("Run unit tests", ("-m", "unittest", "discover", "-s", "tests", "-v")),
        Check("Compile Python sources in memory", ("scripts/validate_repo.py", "--compile-sources")),
    )


RunFunction = Callable[..., subprocess.CompletedProcess[object]]


def compile_python_sources(root: Path) -> int:
    """Compile a bounded source set without writing bytecode."""
    root = root.resolve()
    sources: list[Path] = []
    for relative in PYTHON_SOURCE_DIRECTORIES:
        directory = root / relative
        if not directory.is_dir():
            print(f"FAILED: missing Python source directory: {relative}", file=sys.stderr)
            return 2
        for path in directory.rglob("*.py"):
            sources.append(path)
            if len(sources) > MAX_PYTHON_SOURCE_FILES:
                print(
                    f"FAILED: Python source file count exceeds {MAX_PYTHON_SOURCE_FILES}",
                    file=sys.stderr,
                )
                return 2

    total_bytes = 0
    for path in sorted(sources):
        relative = path.relative_to(root).as_posix()
        try:
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                print(f"FAILED: Python source is not a regular file: {relative}", file=sys.stderr)
                return 2
            if metadata.st_size > MAX_PYTHON_SOURCE_FILE_BYTES:
                print(
                    f"FAILED: Python source exceeds {MAX_PYTHON_SOURCE_FILE_BYTES} bytes: {relative}",
                    file=sys.stderr,
                )
                return 2
            source = path.read_bytes()
        except OSError as exc:
            print(f"FAILED: could not read Python source {relative}: {exc}", file=sys.stderr)
            return 2

        total_bytes += len(source)
        if total_bytes > MAX_PYTHON_SOURCE_BYTES:
            print(
                f"FAILED: total Python source size exceeds {MAX_PYTHON_SOURCE_BYTES} bytes",
                file=sys.stderr,
            )
            return 2
        try:
            compile(source, relative, "exec", dont_inherit=True)
        except SyntaxError as exc:
            print(
                f"FAILED: {relative}:{exc.lineno or 1}:{exc.offset or 1}: {exc.msg}",
                file=sys.stderr,
            )
            return 1
        except (MemoryError, OverflowError, ValueError) as exc:
            print(
                f"FAILED: could not compile Python source {relative}: {type(exc).__name__}",
                file=sys.stderr,
            )
            return 2

    if not sources:
        print("FAILED: no Python sources found", file=sys.stderr)
        return 2
    print(
        f"In-memory compilation passed: {len(sources)} files, "
        f"{total_bytes} bytes; no bytecode written."
    )
    return 0


def run_validation(
    root: Path,
    *,
    release: bool,
    runner: RunFunction = subprocess.run,
) -> int:
    root = root.resolve()
    plan = validation_plan(release=release)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"

    mode = "release" if release else "pull-request"
    print(f"Validation root: {root}")
    print(f"Mode: archive-safe {mode}; Git is not required")

    with tempfile.TemporaryDirectory(prefix="seedance-validation-pycache-") as cache_dir:
        environment["PYTHONPYCACHEPREFIX"] = cache_dir
        for index, check in enumerate(plan, start=1):
            print(f"[{index}/{len(plan)}] {check.name}", flush=True)
            try:
                result = runner(check.command, cwd=root, env=environment)
            except OSError as exc:
                print(f"FAILED: could not start {check.display_command()}: {exc}", file=sys.stderr)
                return 2
            if result.returncode != 0:
                print(f"FAILED: {check.name} (exit {result.returncode})", file=sys.stderr)
                return result.returncode if result.returncode > 0 else 1

    print(f"PASS: all {len(plan)} archive-safe checks completed")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release",
        action="store_true",
        help="also fail when the checked-in source registry is stale",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the archive-safe command plan without running it",
    )
    parser.add_argument("--compile-sources", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.compile_sources:
        if args.release or args.list:
            parser.error("--compile-sources cannot be combined with another mode")
        return compile_python_sources(REPO_ROOT)
    if args.list:
        for check in validation_plan(release=args.release):
            print(check.display_command())
        return 0
    return run_validation(REPO_ROOT, release=args.release)


if __name__ == "__main__":
    raise SystemExit(main())

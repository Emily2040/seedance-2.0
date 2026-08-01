#!/usr/bin/env python3
"""Run the repository's canonical validation suite without requiring Git.

The runner anchors every child process to the repository containing this file,
so an extracted archive may live under a nested path or a path containing
spaces. Git working-tree hygiene is intentionally not part of this suite.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]


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
    source_arguments = ["scripts/source_registry_check.py", "--strict"]
    if release:
        source_arguments.append("--enforce-freshness")

    return (
        Check("Validate skill metadata and required files", ("scripts/validate_skills.py", "--strict")),
        Check("Audit stale and risky active wording", ("scripts/content_audit.py", "--strict")),
        Check("Validate eval schema", ("scripts/eval_schema_check.py", "--strict")),
        Check("Execute JSON Schemas against declared instances", ("scripts/schema_check.py", "--strict")),
        Check("Audit frontend README and SVG assets", ("scripts/design_audit.py", "--strict")),
        Check("Check the masthead matches its generator", ("scripts/build_hero.py", "--check")),
        Check("Validate source freshness and claim labels", tuple(source_arguments)),
        Check("Validate multilingual vocabulary schema", ("scripts/vocab_schema_check.py", "--strict")),
        Check("Validate sequence project state", ("scripts/project_state_check.py", "--strict")),
        Check("Validate continuity chains", ("scripts/continuity_chain_check.py", "--strict")),
        Check("Validate behavior contracts", ("scripts/behavior_contract_check.py", "--strict")),
        Check("Validate sequence evals", ("scripts/sequence_eval_check.py", "--strict")),
        Check("Validate generation-run fixtures", ("scripts/generation_run_check.py", "--strict")),
        Check("Lint compiled prompts", ("scripts/prompt_lint.py", "--self-test", "--strict")),
        Check("Stress-test the prompt architecture", ("scripts/prompt_architecture_stress.py", "--strict")),
        Check("Check eval harness wiring (offline)", ("scripts/eval_run.py", "--self-test", "--strict")),
        Check(
            "Check frame-extraction tool wiring (offline)",
            ("scripts/extract_last_frame.py", "--self-test", "--strict"),
        ),
        Check("Run unit tests", ("-m", "unittest", "discover", "-s", "tests", "-v")),
        Check("Compile Python files", ("-m", "compileall", "-q", "scripts", "tests")),
    )


RunFunction = Callable[..., subprocess.CompletedProcess[object]]


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
                print(
                    f"FAILED: {check.name} (exit {result.returncode})",
                    file=sys.stderr,
                )
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
    args = parser.parse_args(argv)

    if args.list:
        for check in validation_plan(release=args.release):
            print(check.display_command())
        return 0

    return run_validation(REPO_ROOT, release=args.release)


if __name__ == "__main__":
    raise SystemExit(main())

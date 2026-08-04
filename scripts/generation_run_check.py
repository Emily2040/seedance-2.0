#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

if __package__:
    from .strict_json import StrictJSONError, diagnostic_text, load_json, load_jsonl
else:
    from strict_json import StrictJSONError, diagnostic_text, load_json, load_jsonl


REQUIRED_RUN_FIELDS = {
    "run_id", "project_id", "clip_id", "surface", "prompt_version",
    "input_mode", "reference_tags", "prompt", "result_status", "is_synthetic_fixture",
}
REQUIRED_BENCHMARK_FIELDS = {
    "benchmark_version", "updated", "cases",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    errors: list[str] = []

    benchmark = root / "evals" / "generation-benchmark.json"
    if not benchmark.exists():
        errors.append("missing evals/generation-benchmark.json")
    else:
        try:
            data = load_json(benchmark, expected_type=dict, root=root)
        except Exception as exc:
            errors.append(f"evals/generation-benchmark.json invalid JSON: {exc}")
        else:
            missing = REQUIRED_BENCHMARK_FIELDS - set(data)
            if missing:
                errors.append("generation benchmark missing: " + ", ".join(sorted(missing)))
            if len(data.get("cases", [])) < 3:
                errors.append("generation benchmark needs at least three cases")

    runs = root / "data" / "generation-runs.example.jsonl"
    if not runs.exists():
        errors.append("missing data/generation-runs.example.jsonl")
    else:
        try:
            records = load_jsonl(runs, expected_type=dict, root=root)
        except StrictJSONError as exc:
            location = f":{exc.line}" if exc.line is not None else ""
            detail = exc.message
            if exc.column is not None:
                detail += f" at column {exc.column}"
            errors.append(
                f"generation-runs.example.jsonl{location}: invalid JSONL: {detail}"
            )
        except OSError as exc:
            errors.append(f"generation-runs.example.jsonl: invalid JSONL: {exc}")
        else:
            for lineno, record in records:
                missing = REQUIRED_RUN_FIELDS - set(record)
                if missing:
                    errors.append(f"generation-runs.example.jsonl:{lineno}: missing {', '.join(sorted(missing))}")
                if record.get("result_status") != "not_run_fixture" and record.get("is_synthetic_fixture") is True:
                    errors.append(f"generation-runs.example.jsonl:{lineno}: fixture must not pretend to be production result")
            if len(records) < 2:
                errors.append("generation-runs.example.jsonl needs at least two records")

    if errors:
        print("Generation run errors:")
        for error in errors:
            print(diagnostic_text(f"- {error}"))
        return 1
    print("Generation run check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

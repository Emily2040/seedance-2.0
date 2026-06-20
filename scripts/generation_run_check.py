#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_RUN_FIELDS = {
    "run_id", "project_id", "clip_id", "surface", "prompt_version",
    "input_mode", "reference_tags", "prompt", "result_status", "is_synthetic_fixture",
}
REQUIRED_BENCHMARK_FIELDS = {
    "benchmark_version", "updated", "cases",
}


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    errors: list[str] = []

    benchmark = root / "evals" / "generation-benchmark.json"
    if not benchmark.exists():
        errors.append("missing evals/generation-benchmark.json")
    else:
        try:
            data = load_json(benchmark)
        except Exception as exc:
            errors.append(f"evals/generation-benchmark.json invalid JSON: {exc}")
        else:
            if not isinstance(data, dict):
                errors.append("generation benchmark must be object")
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
        count = 0
        for lineno, line in enumerate(runs.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            count += 1
            try:
                record = json.loads(line)
            except Exception as exc:
                errors.append(f"generation-runs.example.jsonl:{lineno}: invalid JSONL: {exc}")
                continue
            missing = REQUIRED_RUN_FIELDS - set(record)
            if missing:
                errors.append(f"generation-runs.example.jsonl:{lineno}: missing {', '.join(sorted(missing))}")
            if record.get("result_status") != "not_run_fixture" and record.get("is_synthetic_fixture") is True:
                errors.append(f"generation-runs.example.jsonl:{lineno}: fixture must not pretend to be production result")
        if count < 2:
            errors.append("generation-runs.example.jsonl needs at least two records")

    if errors:
        print("Generation run errors:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Generation run check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

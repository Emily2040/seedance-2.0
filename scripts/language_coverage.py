"""Offline availability and conservative source-drift checks, not fluency review."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

if __package__:
    from .strict_json import load_json, read_repo_text
else:
    from strict_json import load_json, read_repo_text

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = {"en", "zh", "ja", "ko", "es", "ru"}
SOURCES = {"SKILL.md", "skills/seedance-prompt/SKILL.md", "skills/seedance-interview/SKILL.md",
           "skills/seedance-audio/SKILL.md"}


def digest(root: Path, relative: str) -> str:
    return hashlib.sha256(read_repo_text(root, root / relative).replace("\r\n", "\n").encode("utf-8")).hexdigest()


def check(root: Path, contract: dict) -> dict:
    if not isinstance(contract, dict) or set(contract) != {"version", "source_revision", "sources", "languages"}:
        raise ValueError("coverage contract fields differ from the schema")
    if type(contract["version"]) is not int or contract["version"] != 1:
        raise ValueError("coverage version must be 1")
    if not isinstance(contract["source_revision"], str) or not re.fullmatch(r"[0-9a-f]{40}", contract["source_revision"]):
        raise ValueError("source revision must be a full Git commit ID")
    sources = contract["sources"]
    if not isinstance(sources, dict) or set(sources) != SOURCES:
        raise ValueError("all declared source concepts must retain their source files")
    languages = contract["languages"]
    if not isinstance(languages, dict) or set(languages) != LANGUAGES:
        raise ValueError("coverage must include exactly six languages")
    def changed(entries):
        if not isinstance(entries, dict) or not entries:
            raise ValueError("source snapshots must be nonempty maps")
        result = []
        for path, expected in entries.items():
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError("snapshot hashes must be SHA-256")
            if digest(root, path) != expected:
                result.append(path)
        return result
    source_changes = changed(sources)
    report = {}
    for language, item in languages.items():
        if not isinstance(item, dict) or set(item) != {"quickstart", "vocabulary", "readme", "snapshots", "native_review", "rendered_review"}:
            raise ValueError("language fields differ from the schema")
        suffix = "" if language == "en" else f".{language}"
        readme = "README.md" if language == "en" else f"docs/README.{language}.md" if language in {"zh", "ja", "ko"} else None
        if (item["quickstart"] != f"docs/QUICKSTART{suffix}.md"
                or item["vocabulary"] != f"references/vocab/{language}.md" or item["readme"] != readme):
            raise ValueError("language availability paths differ from the declared scope")
        # README content evolves independently; it is availability-only, not a
        # claim of semantic parity. Scope tracked here is quickstart + vocabulary.
        expected_paths = {item["quickstart"], item["vocabulary"]}
        if not isinstance(item["snapshots"], dict) or set(item["snapshots"]) != expected_paths:
            raise ValueError("snapshot scope must retain quickstart and vocabulary")
        if item["native_review"] != "pending" or item["rendered_review"] != "pending":
            raise ValueError("this availability contract cannot certify review completion")
        if readme:
            read_repo_text(root, root / readme)
        target_changes = changed(item["snapshots"])
        report[language] = {"status": "stale_review_required" if source_changes or target_changes else "unchanged_unreviewed",
                            "source_changes": source_changes, "target_changes": target_changes,
                            "native_review": "pending", "rendered_review": "pending"}
    return report


if __name__ == "__main__":
    contract = load_json(ROOT / "evals/language-coverage.json", root=ROOT)
    print(json.dumps(check(ROOT, contract), ensure_ascii=True, indent=2))

#!/usr/bin/env python3
"""Read-only comparison of one installed skill with this source checkout."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from pathlib import Path

sys.dont_write_bytecode = True

if __package__:
    from . import install_codex_skill as installer
else:
    import install_codex_skill as installer


NEXT_STEPS = {
    "missing": "Run the installer from the reviewed source checkout when ready.",
    "current": "No replacement is needed for the checked payload.",
    "different_payload": "Review source differences and back up this directory before choosing an upgrade.",
    "modified": "Back up this directory and review local edits before choosing any replacement.",
    "unmanaged": "Back up this directory and review its origin before choosing any replacement.",
    "unsafe": "Stop and inspect the selected path or marker manually; no repair was attempted.",
}


def _version(raw: bytes) -> str | None:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None
    frontmatter = text.split("---", 2)[1]
    match = re.search(r'^\s*version:\s*["\']?(\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?)["\']?\s*$', frontmatter, re.M)
    return match.group(1) if match and len(match.group(1)) <= 64 else None


def _normalized(raw: bytes) -> bytes:
    """Normalize only UTF-8 newline spelling, never whitespace or file content."""
    try:
        return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    except UnicodeDecodeError:
        return raw


def _read(root: Path, relative: str, limit: int = installer.MAX_INSTALL_FILE_BYTES) -> bytes:
    return installer._read_stable_regular_bytes(
        root, relative, label="doctor input", max_bytes=limit,
    )[1]


def inspect_install(repo_root: Path, destination: Path) -> dict:
    """Do not enumerate target contents, recover transactions, lock or write."""
    result = {
        "format_version": 1, "status": "unsafe", "managed": False,
        "installed_version": None, "source_version": None,
        "installed_commit": None, "source_contract_sha256": None,
        "checked_files": 0, "missing": [], "changed": [],
        "newline_only": [], "modified_since_install": [],
        "recorded_paths_not_checked": 0,
        "scope": "Only current source-declared paths and the completion marker are read; extra files are not scanned.",
    }
    try:
        contract = installer.load_payload_contract(repo_root)
        plan = installer.build_install_payload_plan(repo_root, contract)
        expected = plan.installed_contract.file_manifest()
        source = contract.file_manifest()
        result["source_contract_sha256"] = plan.installed_contract.contract_sha256
        result["source_version"] = _version(_read(repo_root, "SKILL.md"))
        try:
            initial = destination.lstat()
        except FileNotFoundError:
            result["status"] = "missing"
            return result
        if installer._is_reparse_stat(initial) or not stat.S_ISDIR(initial.st_mode):
            raise ValueError("unsafe target")
        # The installer reader refuses symlinks/reparse parents, hard links,
        # special files, oversized inputs and file identity changes.
        try:
            marker_before = _read(destination, installer.COMPLETION_MARKER, installer.MAX_RECORD_BYTES)
        except FileNotFoundError:
            marker_before = None
        record = None
        if marker_before is not None:
            record, checked_marker = installer._completion_metadata(destination)
            if marker_before != checked_marker:
                raise ValueError("marker changed")
            result["managed"] = True
            result["recorded_paths_not_checked"] = len(set(record["files"]) - set(expected))

        total = 0
        for relative, metadata in sorted(expected.items()):
            try:
                raw = _read(destination, relative)
            except FileNotFoundError:
                result["missing"].append(relative)
                if record and relative in record["files"]:
                    result["modified_since_install"].append(relative)
                continue
            total += len(raw)
            if total > installer.MAX_INSTALL_PAYLOAD_BYTES:
                raise ValueError("target budget exceeded")
            result["checked_files"] += 1
            actual = {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            if relative == "SKILL.md":
                result["installed_version"] = _version(raw)
            if record and relative in record["files"] and actual != record["files"][relative]:
                result["modified_since_install"].append(relative)
            if actual != metadata:
                source_raw = _read(repo_root, relative)
                if {"size": len(source_raw), "sha256": hashlib.sha256(source_raw).hexdigest()} != source[relative]:
                    raise ValueError("source changed")
                expected_raw = (installer._installed_readme_bytes(source_raw)
                                if relative == installer.INSTALLED_README_PATH else source_raw)
                field = "newline_only" if _normalized(raw) == _normalized(expected_raw) else "changed"
                result[field].append(relative)
        final = destination.lstat()
        if installer._stat_identity(initial) != installer._stat_identity(final):
            raise ValueError("target changed")
        try:
            marker_after = _read(destination, installer.COMPLETION_MARKER, installer.MAX_RECORD_BYTES)
        except FileNotFoundError:
            marker_after = None
        if marker_before != marker_after:
            raise ValueError("marker changed")
        if not record:
            result["status"] = "unmanaged"
        elif result["modified_since_install"]:
            result["status"] = "modified"
        elif (result["missing"] or result["changed"] or result["newline_only"]
              or record["contract_sha256"] != plan.installed_contract.contract_sha256):
            result["status"] = "different_payload"
        else:
            result["status"] = "current"
    except (OSError, ValueError, RuntimeError):
        # Exceptions and untrusted marker values may contain private data.
        result["status"] = "unsafe"
        result["reason"] = "Inspection could not complete safely; no files were changed."
    finally:
        result["next_step"] = NEXT_STEPS[result["status"]]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    installer.add_destination_arguments(parser)
    parser.add_argument("--json", action="store_true", help="Print the complete machine-readable report.")
    args = parser.parse_args()
    destination = installer.skills_dir_from_args(parser, args) / installer.SKILL_NAME
    report = inspect_install(Path(__file__).resolve().parents[1], destination)
    report["destination"] = str(destination.absolute())
    if args.json:
        print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    else:
        installer.safe_print("Target: " + installer._bounded_diagnostic(report["destination"], 280))
        print(f"Installation: {report['status']}")
        print(f"Version: installed {report['installed_version'] or 'unknown'}; source {report['source_version'] or 'unknown'}")
        print(f"Checked {report['checked_files']} source-declared files; extra files were not scanned.")
        for field in ("missing", "changed", "newline_only", "modified_since_install"):
            if report[field]:
                print(f"{field}: {len(report[field])}")
                for relative in report[field][:20]:
                    installer.safe_print("  " + installer._bounded_diagnostic(relative, 180))
        print(report["next_step"])
    return 0 if report["status"] == "current" else 2 if report["status"] == "unsafe" else 1


if __name__ == "__main__":
    raise SystemExit(main())

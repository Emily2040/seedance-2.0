"""Read-only diagnostics must not become a replacement or secret scanner."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts import install_doctor as doctor
from scripts import install_codex_skill as installer


class InstallDoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.target = Path(self.temp.name) / "skills" / "seedance-20"
        self.root.mkdir()
        files = {
            "SKILL.md": "---\nname: seedance-20\nmetadata:\n  version: 6.7.0\n---\nA skill.\n",
            "README.md": "# Source\n<!-- installed-readme-gallery:start -->\nOld gallery\n<!-- installed-readme-gallery:end -->\n<!-- installed-readme-validation:start -->\nDev checks\n<!-- installed-readme-validation:end -->\n",
            "scripts/install_codex_skill.py": "# fixture, not executable installation\n",
            "references/example.md": "# Example\nOriginal direction.\n",
        }
        paths = sorted([*files, "validation/install-payload.txt"])
        files["validation/install-payload.txt"] = "\n".join(paths) + "\n"
        for name, content in files.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8", newline="\n")
        self.install()

    def install(self):
        shutil.copytree(self.root, self.target, dirs_exist_ok=True)
        contract = installer.load_payload_contract(self.root)
        plan = installer.build_install_payload_plan(self.root, contract)
        readme = self.target / "README.md"
        readme.write_bytes(installer._installed_readme_bytes(readme.read_bytes()))
        installer.write_completion_marker(self.target, plan.installed_contract)

    def inspect(self):
        return doctor.inspect_install(self.root, self.target)

    def snapshot(self):
        return {p.relative_to(self.target).as_posix():
                (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode)
                for p in self.target.rglob("*") if p.is_file()}

    def test_current_install_preserves_every_byte_mode_and_mtime(self):
        (self.target / "private.env").write_text("SECRET=do-not-read", encoding="utf-8")
        before = self.snapshot()
        original = doctor._read
        seen = []
        def track(root, relative, *args):
            seen.append(relative)
            return original(root, relative, *args)
        with patch.object(doctor, "_read", side_effect=track):
            report = self.inspect()
        self.assertEqual(report["status"], "current")
        self.assertEqual(report["installed_version"], "6.7.0")
        self.assertIsNone(report["installed_commit"])
        self.assertNotIn("private.env", seen)
        self.assertNotIn("SECRET", json.dumps(report))
        self.assertEqual(before, self.snapshot())
        self.assertEqual(sorted(p.name for p in self.target.parent.iterdir()), ["seedance-20"])

    def test_missing_directory_is_not_created(self):
        shutil.rmtree(self.target.parent)
        self.assertEqual(self.inspect()["status"], "missing")
        self.assertFalse(self.target.parent.exists())

    def test_installed_readme_is_compared_with_transformed_source(self):
        self.assertNotEqual((self.root / "README.md").read_bytes(), (self.target / "README.md").read_bytes())
        self.assertEqual(self.inspect()["changed"], [])
        p = self.target / "README.md"
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(self.inspect()["newline_only"], ["README.md"])

    def test_unmarked_matching_files_remain_unmanaged(self):
        (self.target / installer.COMPLETION_MARKER).unlink()
        self.assertEqual(self.inspect()["status"], "unmanaged")

    def test_older_managed_payload_is_different_not_corrupt(self):
        (self.root / "references/example.md").write_text("# New source\n", encoding="utf-8")
        report = self.inspect()
        self.assertEqual(report["status"], "different_payload")
        self.assertEqual(report["changed"], ["references/example.md"])
        self.assertEqual(report["modified_since_install"], [])

    def test_local_edits_and_missing_managed_files_are_modified(self):
        (self.target / "references/example.md").write_text("Local edit\n", encoding="utf-8")
        (self.target / "SKILL.md").unlink()
        report = self.inspect()
        self.assertEqual(report["status"], "modified")
        self.assertIn("SKILL.md", report["missing"])
        self.assertEqual(report["modified_since_install"], ["SKILL.md", "references/example.md"])

    def test_newline_only_change_does_not_bypass_managed_hash_check(self):
        p = self.target / "references/example.md"
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        report = self.inspect()
        self.assertEqual(report["newline_only"], ["references/example.md"])
        self.assertEqual(report["changed"], [])
        self.assertEqual(report["status"], "modified")

    def test_malformed_marker_does_not_echo_private_content(self):
        (self.target / installer.COMPLETION_MARKER).write_text('SECRET-private-value', encoding="utf-8")
        report = self.inspect()
        self.assertEqual(report["status"], "unsafe")
        self.assertNotIn("SECRET", json.dumps(report))

    def test_old_only_files_are_counted_without_opening_them(self):
        record_path = self.target / installer.COMPLETION_MARKER
        record_path.unlink()
        old = self.target / "old-private-note.txt"
        old.write_text("PRIVATE", encoding="utf-8")
        manifest = self.target / "validation/install-payload.txt"
        paths = sorted(manifest.read_text(encoding="utf-8").splitlines() + [old.name])
        manifest.write_text("\n".join(paths) + "\n", encoding="utf-8", newline="\n")
        files = {name: {"size": len((self.target/name).read_bytes()),
                        "sha256": hashlib.sha256((self.target/name).read_bytes()).hexdigest()}
                 for name in paths}
        record_path.write_text(json.dumps(installer._completion_marker_record(files)), encoding="utf-8")
        original = doctor._read
        def guard(root, relative, *args):
            self.assertNotEqual(relative, old.name)
            return original(root, relative, *args)
        with patch.object(doctor, "_read", side_effect=guard):
            report = self.inspect()
        self.assertEqual(report["recorded_paths_not_checked"], 1)
        self.assertEqual(report["status"], "different_payload")

    def test_hard_linked_payload_is_unsafe(self):
        p = self.target / "references/example.md"
        try:
            os.link(p, self.target.parent / "alias")
        except OSError as exc:
            self.skipTest(str(exc))
        self.assertEqual(self.inspect()["status"], "unsafe")

    def test_symlink_payload_is_not_followed(self):
        p = self.target / "references/example.md"
        p.unlink()
        try:
            p.symlink_to(self.root / "references/example.md")
        except OSError as exc:
            self.skipTest(str(exc))
        self.assertEqual(self.inspect()["status"], "unsafe")

    def test_marker_change_mid_inspection_is_unsafe(self):
        original = doctor._read
        def mutate(root, relative, *args):
            raw = original(root, relative, *args)
            if root == self.target and relative == "SKILL.md":
                (self.target / installer.COMPLETION_MARKER).write_text("{}", encoding="utf-8")
            return raw
        with patch.object(doctor, "_read", side_effect=mutate):
            self.assertEqual(self.inspect()["status"], "unsafe")

    def test_budget_failure_is_unsafe(self):
        with patch.object(installer, "MAX_INSTALL_PAYLOAD_BYTES", 1):
            self.assertEqual(self.inspect()["status"], "unsafe")

    def test_version_labels_are_bounded(self):
        self.assertIsNone(doctor._version(b"---\nversion: " + b"9" * 1000 + b".0.0\n---\n"))
        self.assertEqual(doctor._version(b'---\nversion: "6.7.0-beta.1"\n---\n'), "6.7.0-beta.1")

    def test_modified_or_deleted_payload_allowlist_is_a_managed_edit(self):
        path = self.target / installer.PAYLOAD_MANIFEST
        original = path.read_bytes()
        for replacement in (b"# a local edit\n", None):
            with self.subTest(replacement=replacement):
                if replacement is None:
                    path.unlink()
                else:
                    path.write_bytes(replacement)
                report = self.inspect()
                self.assertEqual(report["status"], "modified")
                self.assertTrue(report["managed"])
                self.assertIn(installer.PAYLOAD_MANIFEST.as_posix(), report["modified_since_install"])
                # Diagnostic classification must not weaken installer acceptance.
                self.assertFalse(installer.validate_completed_install(self.target)[0])
                path.write_bytes(original)

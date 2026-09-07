"""Destination choices must not redirect existing installs or bypass guards."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import install_codex_skill as installer
from scripts import install_doctor as doctor


class InstallScopeTests(unittest.TestCase):
    def select(self, argv):
        parser = argparse.ArgumentParser()
        installer.add_destination_arguments(parser)
        return installer.skills_dir_from_args(parser, parser.parse_args(argv))

    def test_legacy_default_preserves_environment_and_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with patch.object(Path, "home", return_value=home):
                with patch.dict(os.environ, {"CODEX_HOME": ""}):
                    self.assertEqual(self.select([]), home / ".codex/skills")
                with patch.dict(os.environ, {"CODEX_HOME": str(home / "custom")}):
                    self.assertEqual(self.select([]), home / "custom/skills")
                    self.assertEqual(self.select(["--client", "codex", "--scope", "user"]),
                                     home / ".agents/skills")
                    self.assertEqual(self.select(["--dest", str(home / "chosen")]), home / "chosen")
            self.assertEqual(list(home.iterdir()), [])

    def test_invalid_combinations_stop_both_commands_before_payload_access(self):
        cases = [
            ["--client", "codex"], ["--scope", "user"],
            ["--project-root", "."], ["--dest", "x", "--client", "codex"],
            ["--dest", "x", "--scope", "project"],
            ["--dest", "x", "--project-root", "."],
            ["--client", "codex", "--scope", "project"],
            ["--client", "codex", "--scope", "user", "--project-root", "."],
            ["--client", "unknown", "--scope", "user"],
            ["--client", "codex", "--scope", "unknown"],
        ]
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"
            ordinary_file = Path(tmp) / "file"
            ordinary_file.write_text("unchanged", encoding="utf-8")
            for root in (missing, ordinary_file):
                cases.append(["--client", "codex", "--scope", "project", "--project-root", str(root)])
            with patch.object(installer, "_load_payload_contract_once") as install_read, \
                 patch.object(doctor, "inspect_install") as doctor_read:
                for module in (installer, doctor):
                    for argv in cases:
                        with self.subTest(command=module.__name__, argv=argv), \
                             patch("sys.argv", ["command", *argv]), \
                             contextlib.redirect_stderr(io.StringIO()):
                            with self.assertRaises(SystemExit) as exc:
                                module.main()
                            self.assertEqual(exc.exception.code, 2)
                install_read.assert_not_called()
                doctor_read.assert_not_called()
            self.assertFalse(missing.exists())
            self.assertEqual(ordinary_file.read_text(encoding="utf-8"), "unchanged")

    def test_real_installs_and_doctor_agree_for_all_four_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            project = Path(tmp) / "My Film"
            home.mkdir()
            project.mkdir()
            legacy = home / ".codex/skills/seedance-20/SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"existing private local edits")
            before = (legacy.read_bytes(), legacy.stat().st_mtime_ns)
            with patch.object(Path, "home", return_value=home):
                for client, folder in (("codex", ".agents"), ("claude-code", ".claude")):
                    for scope, parent in (("user", home), ("project", project)):
                        argv = ["--client", client, "--scope", scope]
                        if scope == "project":
                            argv += ["--project-root", str(project)]
                        target = parent / folder / "skills/seedance-20"
                        with self.subTest(client=client, scope=scope):
                            with patch("sys.argv", ["installer", *argv]), contextlib.redirect_stdout(io.StringIO()):
                                self.assertEqual(installer.main(), 0)
                                # Fresh-install choice never authorizes replacement.
                                self.assertEqual(installer.main(), 1)
                            output = io.StringIO()
                            with patch("sys.argv", ["doctor", *argv, "--json"]), contextlib.redirect_stdout(output):
                                self.assertEqual(doctor.main(), 0)
                            report = json.loads(output.getvalue())
                            self.assertEqual(report["destination"], str(target.absolute()))
                            self.assertEqual(report["status"], "current")
                            self.assertEqual(report["missing"], [])
                            self.assertEqual(report["changed"], [])
                            self.assertFalse((target / "scripts/eval_run.py").exists())
            self.assertEqual(before, (legacy.read_bytes(), legacy.stat().st_mtime_ns))

    def test_source_checkout_project_target_is_still_refused(self):
        source = Path(installer.__file__).resolve().parents[1]
        for client in ("codex", "claude-code"):
            with self.subTest(client=client), \
                 patch("sys.argv", ["installer", "--client", client, "--scope", "project", "--project-root", str(source)]), \
                 patch.object(installer, "exclusive_install_lock") as lock, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(), 1)
                lock.assert_not_called()


if __name__ == "__main__":
    unittest.main()

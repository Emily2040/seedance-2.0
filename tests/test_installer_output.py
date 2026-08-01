"""Regression tests for installer messages on restricted text encodings."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_codex_skill.py"

sys.path.insert(0, str(ROOT / "scripts"))
import install_codex_skill as installer  # noqa: E402


class EncodingCheckedStream:
    """A strict text stream with no .buffer, like many test/redirect wrappers."""

    def __init__(self, advertised_encoding: str, actual_encoding: str | None = None) -> None:
        self.encoding = advertised_encoding
        self.actual_encoding = actual_encoding or advertised_encoding
        self.parts: list[str] = []

    def write(self, value: str) -> int:
        value.encode(self.actual_encoding, errors="strict")
        self.parts.append(value)
        return len(value)

    def getvalue(self) -> str:
        return "".join(self.parts)


class FailingStream:
    encoding = "utf-8"

    def write(self, _value: str) -> int:
        raise OSError("injected output failure")


class UnicodeConsoleSubprocessTests(unittest.TestCase):
    def run_installer(
        self, codex_home: Path, encoding: str, *arguments: str
    ) -> subprocess.CompletedProcess[bytes]:
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(codex_home)
        environment["PYTHONIOENCODING"] = f"{encoding}:strict"
        return subprocess.run(
            [sys.executable, str(INSTALLER), *arguments],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=90,
        )

    def test_cp1252_console_does_not_turn_a_valid_install_into_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "Codex-技能-🚀"
            result = self.run_installer(codex_home, "cp1252")

            destination = codex_home / "skills" / "seedance-20"
            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertTrue((destination / "references" / "quick-ref.md").is_file())
            self.assertEqual(
                result.returncode,
                0,
                result.stdout.decode("cp1252") + result.stderr.decode("cp1252"),
            )
            stdout = result.stdout.decode("cp1252")
            self.assertIn("Installed seedance-20 to", stdout)
            self.assertIn(r"\u6280\u80fd", stdout)
            self.assertIn(r"\U0001f680", stdout)
            self.assertEqual(result.stderr, b"")

    def test_later_cp1252_already_installed_message_keeps_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "Codex-技能-🚀"
            first = self.run_installer(codex_home, "cp1252")
            self.assertEqual(first.returncode, 0)

            later = self.run_installer(codex_home, "cp1252")

            self.assertEqual(later.returncode, 1)
            stdout = later.stdout.decode("cp1252")
            self.assertIn("seedance-20 is already installed at", stdout)
            self.assertIn(r"\u6280\u80fd", stdout)
            self.assertIn("Run again with --force to replace it.", stdout)
            self.assertEqual(later.stderr, b"")

    def test_utf8_console_preserves_the_real_unicode_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "Codex-技能-🚀"
            result = self.run_installer(codex_home, "utf-8")

            self.assertEqual(
                result.returncode,
                0,
                result.stdout.decode("utf-8") + result.stderr.decode("utf-8"),
            )
            stdout = result.stdout.decode("utf-8")
            destination = codex_home / "skills" / "seedance-20"
            self.assertIn(str(destination), stdout)
            self.assertIn("技能-🚀", stdout)
            self.assertNotIn(r"\u6280", stdout)
            self.assertEqual(result.stderr, b"")

    def test_cp1252_redirected_stderr_uses_escaped_unicode(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252:strict"
        code = (
            "import sys; "
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r}); "
            "import install_codex_skill as installer; "
            "installer.safe_print('stderr 技能 🚀', stream=sys.stderr)"
        )

        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr.decode("cp1252"))
        self.assertEqual(result.stdout, b"")
        stderr = result.stderr.decode("cp1252")
        self.assertIn(r"\u6280\u80fd", stderr)
        self.assertIn(r"\U0001f680", stderr)


class SafePrintStreamTests(unittest.TestCase):
    def test_strict_cp1252_text_wrapper_escapes_only_unsupported_text(self) -> None:
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict", newline="\n")

        installer.safe_print("café 技能 🚀", stream=stream)
        stream.flush()

        output = raw.getvalue().decode("cp1252")
        self.assertIn("café", output)
        self.assertIn(r"\u6280\u80fd", output)
        self.assertIn(r"\U0001f680", output)

    def test_bufferless_string_stream_preserves_unicode(self) -> None:
        stream = io.StringIO()

        installer.safe_print("技能 🚀", stream=stream)

        self.assertEqual(stream.getvalue(), "技能 🚀\n")

    def test_strict_bufferless_cp1252_stream_gets_ascii_escapes(self) -> None:
        stream = EncodingCheckedStream("cp1252")

        installer.safe_print("技能 🚀", stream=stream)

        self.assertEqual(stream.getvalue(), r"\u6280\u80fd \U0001f680" + "\n")

    def test_stream_that_misreports_its_encoding_gets_a_safe_retry(self) -> None:
        stream = EncodingCheckedStream("utf-8", actual_encoding="cp1252")

        installer.safe_print("技能 🚀", stream=stream)

        self.assertEqual(stream.getvalue(), r"\u6280\u80fd \U0001f680" + "\n")

    def test_unknown_advertised_encoding_falls_back_to_ascii_escapes(self) -> None:
        stream = EncodingCheckedStream("codec-that-does-not-exist", actual_encoding="ascii")

        installer.safe_print("技能 🚀", stream=stream)

        self.assertEqual(stream.getvalue(), r"\u6280\u80fd \U0001f680" + "\n")

    def test_non_encoding_write_errors_are_not_hidden(self) -> None:
        with self.assertRaisesRegex(OSError, "injected output failure"):
            installer.safe_print("ordinary message", stream=FailingStream())


class FilesystemFailureTests(unittest.TestCase):
    def test_copy_failure_still_propagates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_argv = sys.argv
            sys.argv = ["install_codex_skill.py", "--dest", str(Path(tmp) / "skills")]
            try:
                with mock.patch.object(
                    installer.shutil, "copytree", side_effect=OSError("injected copy failure")
                ):
                    with self.assertRaisesRegex(OSError, "injected copy failure"):
                        installer.main()
            finally:
                sys.argv = original_argv


if __name__ == "__main__":
    unittest.main()

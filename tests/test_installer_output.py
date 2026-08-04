"""Regression tests for installer messages on restricted text encodings."""

from __future__ import annotations

import ast
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
UNICODE_COMPONENT = "Codex-\u6280\u80fd-\U0001f680"

sys.path.insert(0, str(ROOT / "scripts"))
import install_codex_skill as installer  # noqa: E402


class EncodingCheckedStream:
    """A strict text stream with no byte buffer, like redirect wrappers."""

    def __init__(self, advertised_encoding: str | None, actual_encoding: str) -> None:
        self.encoding = advertised_encoding
        self.actual_encoding = actual_encoding
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


class ShortWriteStream:
    encoding = "utf-8"

    def write(self, value: str) -> int:
        return max(0, len(value) - 1)


class UnicodeConsoleSubprocessTests(unittest.TestCase):
    def run_installer(
        self,
        codex_home: Path,
        encoding: str,
        *arguments: str,
    ) -> subprocess.CompletedProcess[bytes]:
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(codex_home)
        environment["PYTHONIOENCODING"] = f"{encoding}:strict"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", str(INSTALLER), *arguments],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=120,
        )

    def test_cp1252_console_does_not_turn_a_valid_install_into_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / UNICODE_COMPONENT
            result = self.run_installer(codex_home, "cp1252")
            destination = codex_home / "skills" / installer.SKILL_NAME

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

    def test_cp1252_already_installed_refusal_keeps_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / UNICODE_COMPONENT
            first = self.run_installer(codex_home, "cp1252")
            self.assertEqual(first.returncode, 0, first.stderr.decode("cp1252"))

            later = self.run_installer(codex_home, "cp1252")

            self.assertEqual(later.returncode, 1)
            stdout = later.stdout.decode("cp1252")
            self.assertIn("seedance-20 is already installed at", stdout)
            self.assertIn(r"\u6280\u80fd", stdout)
            self.assertIn("Run again with --force to replace it.", stdout)
            self.assertEqual(later.stderr, b"")

    def test_utf8_console_preserves_the_real_unicode_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / UNICODE_COMPONENT
            result = self.run_installer(codex_home, "utf-8")
            destination = codex_home / "skills" / installer.SKILL_NAME

            self.assertEqual(
                result.returncode,
                0,
                result.stdout.decode("utf-8") + result.stderr.decode("utf-8"),
            )
            stdout = result.stdout.decode("utf-8")
            self.assertIn(str(destination), stdout)
            self.assertIn("\u6280\u80fd-\U0001f680", stdout)
            self.assertNotIn(r"\u6280", stdout)
            self.assertEqual(result.stderr, b"")

    def test_cp1252_redirected_stderr_uses_escaped_unicode(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252:strict"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        code = (
            "import sys; "
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r}); "
            "import install_codex_skill as installer; "
            "installer.safe_print('stderr \\u6280\\u80fd \\U0001f680', stream=sys.stderr)"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-c", code],
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
    def test_absent_stdout_is_a_noop(self) -> None:
        with mock.patch.object(installer.sys, "stdout", None):
            installer.safe_print("message with no console")

    def test_absent_stderr_and_stdout_are_a_noop(self) -> None:
        with (
            mock.patch.object(installer.sys, "stdout", None),
            mock.patch.object(installer.sys, "stderr", None),
        ):
            installer.safe_print("error with no console", stream=installer.sys.stderr)

    def test_absent_stderr_falls_back_to_available_stdout(self) -> None:
        fallback = io.StringIO()
        with (
            mock.patch.object(installer.sys, "stdout", fallback),
            mock.patch.object(installer.sys, "stderr", None),
        ):
            installer.safe_print("fallback error", stream=installer.sys.stderr)
        self.assertEqual(fallback.getvalue(), "fallback error\n")

    def test_strict_cp1252_text_wrapper_escapes_only_unsupported_text(self) -> None:
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict", newline="\n")

        installer.safe_print("caf\u00e9 \u6280\u80fd \U0001f680", stream=stream)
        stream.flush()

        output = raw.getvalue().decode("cp1252")
        self.assertIn("caf\u00e9", output)
        self.assertIn(r"\u6280\u80fd", output)
        self.assertIn(r"\U0001f680", output)

    def test_bufferless_string_stream_preserves_unicode(self) -> None:
        stream = io.StringIO()
        installer.safe_print("\u6280\u80fd \U0001f680", stream=stream)
        self.assertEqual(stream.getvalue(), "\u6280\u80fd \U0001f680\n")

    def test_strict_bufferless_cp1252_stream_gets_ascii_escapes(self) -> None:
        stream = EncodingCheckedStream("cp1252", "cp1252")
        installer.safe_print("\u6280\u80fd \U0001f680", stream=stream)
        self.assertEqual(stream.getvalue(), r"\u6280\u80fd \U0001f680" + "\n")

    def test_stream_that_misreports_its_encoding_gets_a_safe_retry(self) -> None:
        stream = EncodingCheckedStream("utf-8", "cp1252")
        installer.safe_print("\u6280\u80fd \U0001f680", stream=stream)
        self.assertEqual(stream.getvalue(), r"\u6280\u80fd \U0001f680" + "\n")

    def test_stream_without_an_encoding_gets_a_safe_retry(self) -> None:
        stream = EncodingCheckedStream(None, "cp1252")
        installer.safe_print("\u6280\u80fd \U0001f680", stream=stream)
        self.assertEqual(stream.getvalue(), r"\u6280\u80fd \U0001f680" + "\n")

    def test_unknown_advertised_encoding_falls_back_to_ascii_escapes(self) -> None:
        stream = EncodingCheckedStream("codec-that-does-not-exist", "ascii")
        installer.safe_print("\u6280\u80fd \U0001f680", stream=stream)
        self.assertEqual(stream.getvalue(), r"\u6280\u80fd \U0001f680" + "\n")

    def test_unpaired_surrogate_is_escaped(self) -> None:
        stream = EncodingCheckedStream("utf-8", "utf-8")
        installer.safe_print("bad-\ud800", stream=stream)
        self.assertEqual(stream.getvalue(), "bad-" + r"\ud800" + "\n")

    def test_non_encoding_write_errors_are_not_hidden(self) -> None:
        with self.assertRaisesRegex(OSError, "injected output failure"):
            installer.safe_print("ordinary message", stream=FailingStream())

    def test_short_writes_are_not_silently_accepted(self) -> None:
        with self.assertRaisesRegex(OSError, "short console write"):
            installer.safe_print("ordinary message", stream=ShortWriteStream())

    def test_installer_has_no_raw_print_call_that_can_bypass_the_guard(self) -> None:
        tree = ast.parse(INSTALLER.read_text(encoding="utf-8"), filename=str(INSTALLER))
        raw_prints = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ]
        self.assertEqual(raw_prints, [])


class InstallerFailureOutputTests(unittest.TestCase):
    def test_unicode_failure_diagnostic_uses_safe_stderr_and_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / UNICODE_COMPONENT / "skills"
            stream = EncodingCheckedStream("cp1252", "cp1252")
            original_argv = sys.argv
            sys.argv = ["install_codex_skill.py", "--dest", str(skills_dir)]
            try:
                with (
                    mock.patch.object(
                        installer,
                        "stage_validated_install",
                        side_effect=OSError("injected-\u6280\u80fd-\U0001f680"),
                    ),
                    mock.patch.object(installer.sys, "stderr", stream),
                ):
                    result = installer.main()
            finally:
                sys.argv = original_argv

            self.assertEqual(result, 1)
            self.assertIn(r"\u6280\u80fd", stream.getvalue())
            self.assertIn(r"\U0001f680", stream.getvalue())
            self.assertNotIn("Traceback", stream.getvalue())


if __name__ == "__main__":
    unittest.main()

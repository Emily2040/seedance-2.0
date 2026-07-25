"""Nothing network-capable may reach an installed skill.

SECURITY.md promises that installing this package cannot cause a network call
or read a credential. That promise is about the *installed payload*, not the
repository, so it has to be checked against what the installer actually copies
rather than against what the repository happens to contain.
"""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import install_codex_skill as installer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# Modules that can open a socket. Matched by parsing imports rather than by
# searching text: a substring scan flags the word in a comment or docstring,
# which is how the first version of this test failed on its own prose.
NETWORK_MODULES = {
    "urllib.request", "urllib.error", "http.client", "socket",
    "ssl", "ftplib", "smtplib", "telnetlib", "requests", "httpx", "aiohttp",
}
CREDENTIAL_HINTS = ("API_KEY", "APIKEY", "TOKEN", "SECRET", "PASSWORD")


def imported_modules(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def credential_env_reads(tree: ast.AST) -> set[str]:
    """Literal environment names that look like credentials, read at runtime."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            upper = node.value.upper()
            if any(hint in upper for hint in CREDENTIAL_HINTS) and node.value.isupper():
                found.add(node.value)
    return found


class InstallPayloadTests(unittest.TestCase):
    def install(self, dest: Path) -> Path:
        argv = sys.argv
        sys.argv = ["install_codex_skill.py", "--dest", str(dest)]
        try:
            self.assertEqual(installer.main(), 0)
        finally:
            sys.argv = argv
        return dest / installer.SKILL_NAME

    def test_development_only_tools_are_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            for name in installer.DEV_ONLY_NAMES:
                matches = list(payload.rglob(name))
                self.assertEqual(matches, [], f"{name} must not reach an installed skill")

    def test_no_installed_script_imports_a_network_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            offenders = []
            for script in sorted(payload.rglob("*.py")):
                tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
                hits = sorted(imported_modules(tree) & NETWORK_MODULES)
                if hits:
                    offenders.append(f"{script.relative_to(payload)}: {hits}")
            self.assertEqual(offenders, [], "installed payload must not be able to open a socket")

    def test_no_installed_script_reads_a_credential(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            offenders = []
            for script in sorted(payload.rglob("*.py")):
                tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
                hits = sorted(credential_env_reads(tree))
                if hits:
                    offenders.append(f"{script.relative_to(payload)}: {hits}")
            self.assertEqual(offenders, [], "installed payload must not read credentials")

    def test_the_check_would_catch_the_evaluator(self) -> None:
        """Guard against the scan passing because it detects nothing at all."""
        tree = ast.parse((ROOT / "scripts/eval_run.py").read_text(encoding="utf-8"))
        self.assertTrue(imported_modules(tree) & NETWORK_MODULES)
        self.assertIn("ANTHROPIC_API_KEY", credential_env_reads(tree))

    def test_the_skill_itself_is_still_installed(self) -> None:
        """Guard against the exclusion list quietly gutting the install."""
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            self.assertTrue((payload / "SKILL.md").exists())
            self.assertTrue((payload / "references").is_dir())
            self.assertTrue((payload / "skills").is_dir())
            self.assertGreater(len(list((payload / "scripts").glob("*.py"))), 5)

    def test_repository_still_ships_the_evaluator(self) -> None:
        """Excluded from installs, not deleted from the project."""
        self.assertTrue((ROOT / "scripts/eval_run.py").exists())


if __name__ == "__main__":
    unittest.main()

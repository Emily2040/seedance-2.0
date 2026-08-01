"""Nothing network-capable may reach an installed skill.

SECURITY.md promises that installing this package cannot cause a network call
or read a credential. That promise is about the *installed payload*, not the
repository, so it has to be checked against what the installer actually copies
rather than against what the repository happens to contain.
"""

from __future__ import annotations

import ast
import errno
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import install_codex_skill as installer  # noqa: E402
import validate_skills  # noqa: E402

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

    def test_installed_files_exactly_match_the_payload_manifest(self) -> None:
        declared = set(installer.load_payload_manifest(ROOT))
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            installed = {
                path.relative_to(payload).as_posix()
                for path in payload.rglob("*")
                if path.is_file()
            }
        self.assertEqual(installed, declared)

    def test_payload_manifest_preserves_required_runtime_content(self) -> None:
        declared = set(installer.load_payload_manifest(ROOT))
        required = {
            "README.md",
            "SECURITY.md",
            "SKILL.md",
            "agents/openai.yaml",
            "scripts/install_codex_skill.py",
            installer.PAYLOAD_MANIFEST.as_posix(),
            *validate_skills.REQUIRED_REFERENCES,
            *(
                f"skills/{name}/SKILL.md"
                for name in validate_skills.EXPECTED_SKILLS
            ),
        }
        self.assertEqual(
            sorted(required - declared),
            [],
            "mandatory runtime files must remain in the explicit payload contract",
        )

    def test_only_declared_files_are_installed_from_source_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            copied_installer = source / "scripts" / "install_codex_skill.py"
            copied_installer.parent.mkdir(parents=True)
            shutil.copy2(ROOT / "scripts/install_codex_skill.py", copied_installer)

            declared = [
                "SKILL.md",
                "references/nested/runtime-note.md",
                "scripts/install_codex_skill.py",
                "validation/install-payload.txt",
            ]
            fixture_files = {
                "SKILL.md": "---\nname: fixture\n---\n",
                "references/nested/runtime-note.md": "declared runtime content\n",
                "validation/install-payload.txt": "\n".join(declared) + "\n",
                ".env": "API_KEY=must-not-ship\n",
                "private.txt": "must not ship\n",
                "secret.json": '{"secret": true}\n',
                "clip.mp4": "not really media, but still undeclared\n",
                "references/nested/undeclared-note.md": "safe-looking but undeclared\n",
            }
            for relative, content in fixture_files.items():
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            destination = root / "installed-skills"
            result = subprocess.run(
                [sys.executable, str(copied_installer), "--dest", str(destination)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            payload = destination / installer.SKILL_NAME
            self.assertTrue((payload / "references/nested/runtime-note.md").is_file())
            for relative in (
                ".env",
                "private.txt",
                "secret.json",
                "clip.mp4",
                "references/nested/undeclared-note.md",
            ):
                self.assertFalse(
                    (payload / relative).exists(),
                    f"undeclared source file reached payload: {relative}",
                )

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
        """Guard against the payload contract quietly gutting the install."""
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            self.assertTrue((payload / "SKILL.md").exists())
            self.assertTrue((payload / "references").is_dir())
            self.assertTrue((payload / "skills").is_dir())
            self.assertGreater(len(list((payload / "scripts").glob("*.py"))), 5)

    def test_repository_still_ships_the_evaluator(self) -> None:
        """Excluded from installs, not deleted from the project."""
        self.assertTrue((ROOT / "scripts/eval_run.py").exists())


class PayloadManifestTests(unittest.TestCase):
    def minimal_repo(self, root: Path, extra_entries: list[str]) -> Path:
        entries = [
            "SKILL.md",
            "scripts/install_codex_skill.py",
            "validation/install-payload.txt",
            *extra_entries,
        ]
        for relative in ("SKILL.md", "scripts/install_codex_skill.py"):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        manifest = root / installer.PAYLOAD_MANIFEST.as_posix()
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("\n".join(entries) + "\n", encoding="utf-8")
        return root

    def symlink_or_skip(
        self,
        link: Path,
        target: Path,
        *,
        target_is_directory: bool = False,
    ) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target, target_is_directory=target_is_directory)
        except (NotImplementedError, OSError) as exc:
            unavailable_errors = {
                errno.EACCES,
                errno.ENOSYS,
                errno.EPERM,
            }
            unavailable_errors.update(
                value
                for name in ("ENOTSUP", "EOPNOTSUPP")
                if (value := getattr(errno, name, None))
            )
            if isinstance(exc, NotImplementedError) or (
                exc.errno in unavailable_errors or getattr(exc, "winerror", None) == 1314
            ):
                self.skipTest(f"filesystem symlinks are unavailable: {exc}")
            raise

    def junction_or_skip(self, link: Path, target: Path) -> None:
        if os.name != "nt":
            self.skipTest("Windows directory junctions are unavailable on this platform")
        link.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.skipTest(f"Windows directory junctions are unavailable: {result.stderr.strip()}")

    def test_manifest_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), ["../outside.txt"])
            with self.assertRaisesRegex(ValueError, "normalized POSIX relative path"):
                installer.load_payload_manifest(root)

    def test_manifest_rejects_duplicate_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), ["SKILL.md"])
            with self.assertRaisesRegex(ValueError, "duplicate payload path"):
                installer.load_payload_manifest(root)

    def test_manifest_rejects_missing_declared_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), ["references/missing.md"])
            with self.assertRaisesRegex(FileNotFoundError, "declared payload file missing"):
                installer.load_payload_manifest(root)

    def test_manifest_rejects_declared_file_symlink_to_internal_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), ["references/linked.md"])
            (root / "runtime.md").write_text("runtime\n", encoding="utf-8")
            self.symlink_or_skip(root / "references/linked.md", Path("../runtime.md"))

            with self.assertRaisesRegex(ValueError, "linked or reparse component") as raised:
                installer.load_payload_manifest(root)
            self.assertIn("component: references/linked.md", str(raised.exception))

    def test_manifest_rejects_declared_file_symlink_to_external_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            root = self.minimal_repo(sandbox / "repo", ["references/linked.md"])
            external = sandbox / "external.md"
            external.write_text("external\n", encoding="utf-8")
            self.symlink_or_skip(root / "references/linked.md", external)

            with self.assertRaisesRegex(ValueError, "linked or reparse component") as raised:
                installer.load_payload_manifest(root)
            self.assertIn("component: references/linked.md", str(raised.exception))

    def test_manifest_rejects_directory_symlink_to_internal_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), ["references/linked/runtime.md"])
            target = root / "runtime"
            target.mkdir()
            (target / "runtime.md").write_text("runtime\n", encoding="utf-8")
            self.symlink_or_skip(
                root / "references/linked",
                Path("../runtime"),
                target_is_directory=True,
            )

            with self.assertRaisesRegex(ValueError, "linked or reparse component") as raised:
                installer.load_payload_manifest(root)
            self.assertIn("component: references/linked", str(raised.exception))

    def test_manifest_rejects_directory_symlink_to_external_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            root = self.minimal_repo(sandbox / "repo", ["references/linked/runtime.md"])
            external = sandbox / "external"
            external.mkdir()
            (external / "runtime.md").write_text("external\n", encoding="utf-8")
            self.symlink_or_skip(
                root / "references/linked",
                external,
                target_is_directory=True,
            )

            with self.assertRaisesRegex(ValueError, "linked or reparse component") as raised:
                installer.load_payload_manifest(root)
            self.assertIn("component: references/linked", str(raised.exception))

    def test_manifest_rejects_internal_windows_junction_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), ["references/linked/runtime.md"])
            target = root / "runtime"
            target.mkdir()
            (target / "runtime.md").write_text("runtime\n", encoding="utf-8")
            self.junction_or_skip(root / "references/linked", target)

            with self.assertRaisesRegex(ValueError, "linked or reparse component") as raised:
                installer.load_payload_manifest(root)
            self.assertIn("component: references/linked", str(raised.exception))

    def test_manifest_rejects_external_windows_junction_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            root = self.minimal_repo(sandbox / "repo", ["references/linked/runtime.md"])
            external = sandbox / "external"
            external.mkdir()
            (external / "runtime.md").write_text("external\n", encoding="utf-8")
            self.junction_or_skip(root / "references/linked", external)

            with self.assertRaisesRegex(ValueError, "linked or reparse component") as raised:
                installer.load_payload_manifest(root)
            self.assertIn("component: references/linked", str(raised.exception))

    def test_manifest_rejects_linked_manifest_before_reading_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), [])
            manifest = root / installer.PAYLOAD_MANIFEST.as_posix()
            target = root / "real-manifest.txt"
            manifest.replace(target)
            self.symlink_or_skip(manifest, Path("../real-manifest.txt"))

            with self.assertRaisesRegex(
                ValueError,
                "install payload manifest contains linked or reparse component",
            ):
                installer.load_payload_manifest(root)

    def test_manifest_rejects_windows_junction_before_reading_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            root = self.minimal_repo(sandbox / "repo", [])
            validation = root / "validation"
            target = sandbox / "manifest-directory"
            validation.replace(target)
            self.junction_or_skip(validation, target)

            with self.assertRaisesRegex(
                ValueError,
                "install payload manifest contains linked or reparse component",
            ):
                installer.load_payload_manifest(root)


class InTreeDestinationTests(unittest.TestCase):
    """copytree walks the source, so an in-tree destination copies itself.

    `--dest .claude/skills` from the repository root produced
    .claude/skills/seedance-20/.claude/skills/seedance-20/... - 757 directories
    and a 4105-character path before it died on ENAMETOOLONG.
    """

    def test_destination_inside_the_repository_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            installer.assert_destination_outside_source(
                ROOT / ".claude" / "skills" / installer.SKILL_NAME, ROOT
            )

    def test_the_repository_root_itself_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            installer.assert_destination_outside_source(ROOT, ROOT)

    def test_a_destination_outside_the_repository_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            installer.assert_destination_outside_source(
                Path(tmp) / "skills" / installer.SKILL_NAME, ROOT
            )

    def test_the_cli_refuses_without_a_traceback_and_writes_nothing(self) -> None:
        # A contributor may legitimately have .claude/ in their working copy
        # (running Claude Code in this repository creates it), so the assertion
        # is "nothing new appeared", never "the directory does not exist".
        target = ROOT / ".claude" / "skills" / installer.SKILL_NAME
        dot_claude_existed_before = (ROOT / ".claude").exists()
        argv = sys.argv
        sys.argv = ["install_codex_skill.py", "--dest", str(ROOT / ".claude" / "skills")]
        try:
            self.assertEqual(installer.main(), 1)
        finally:
            sys.argv = argv
        self.assertFalse(target.exists(), "refused install must create nothing")
        if not dot_claude_existed_before:
            self.assertFalse((ROOT / ".claude").exists(),
                             "refusal must not create the destination's parents either")


if __name__ == "__main__":
    unittest.main()

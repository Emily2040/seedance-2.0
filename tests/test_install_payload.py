"""Nothing network-capable may reach an installed skill.

SECURITY.md promises that installing this package cannot cause a network call
or read a credential. That promise is about the *installed payload*, not the
repository, so it has to be checked against what the installer actually copies
rather than against what the repository happens to contain.
"""

from __future__ import annotations

import ast
import contextlib
import errno
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def run_installer(self, dest: Path, *args: str) -> tuple[int, str]:
        argv = sys.argv
        output = io.StringIO()
        sys.argv = ["install_codex_skill.py", "--dest", str(dest), *args]
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = installer.main()
        finally:
            sys.argv = argv
        return result, output.getvalue()

    def fixture_source(self, root: Path) -> Path:
        source = root / "source"
        declared = [
            "SKILL.md",
            "scripts/install_codex_skill.py",
            installer.PAYLOAD_MANIFEST.as_posix(),
        ]
        fixture_files = {
            "SKILL.md": "stable payload A\n",
            "scripts/install_codex_skill.py": "# fixture installer\n",
            installer.PAYLOAD_MANIFEST.as_posix(): "\n".join(declared) + "\n",
        }
        for relative, content in fixture_files.items():
            path = source.joinpath(*relative.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return source

    def directory_link_or_skip(self, link: Path, target: Path) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.skipTest(f"Windows directory junctions are unavailable: {result.stderr}")
            return
        try:
            link.symlink_to(target, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            unavailable = {errno.EACCES, errno.ENOSYS, errno.EPERM}
            if isinstance(exc, NotImplementedError) or exc.errno in unavailable:
                self.skipTest(f"directory links are unavailable: {exc}")
            raise

    def remove_directory_link(self, link: Path) -> None:
        if os.name == "nt":
            os.rmdir(link)
        else:
            link.unlink()

    def test_development_only_tools_are_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            for name in installer.DEV_ONLY_NAMES:
                matches = list(payload.rglob(name))
                self.assertEqual(matches, [], f"{name} must not reach an installed skill")

    def test_installed_files_match_payload_plus_completion_marker(self) -> None:
        declared = set(installer.load_payload_manifest(ROOT))
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            installed = {
                path.relative_to(payload).as_posix()
                for path in payload.rglob("*")
                if path.is_file()
            }
            marker = json.loads(
                (payload / installer.COMPLETION_MARKER).read_text(encoding="utf-8")
            )
        self.assertEqual(
            installed,
            declared | {installer.COMPLETION_MARKER, installer.PROVENANCE_MARKER},
        )
        self.assertEqual(set(marker["files"]), declared)
        self.assertEqual(marker["declared_paths"], sorted(declared))
        self.assertEqual(marker["payload_manifest_path"], installer.PAYLOAD_MANIFEST.as_posix())
        self.assertEqual(
            marker["payload_manifest_sha256"],
            marker["files"][installer.PAYLOAD_MANIFEST.as_posix()]["sha256"],
        )
        self.assertTrue(installer._is_sha256(marker["contract_sha256"]))

    def test_undeclared_files_never_enter_stage_or_live_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            skills_dir = root / "skills"
            skills_dir.mkdir()
            declared = frozenset(
                {
                    "SKILL.md",
                    "scripts/install_codex_skill.py",
                    installer.PAYLOAD_MANIFEST.as_posix(),
                }
            )
            fixture_files = {
                "SKILL.md": "runtime skill\n",
                "scripts/install_codex_skill.py": "# fixture installer\n",
                installer.PAYLOAD_MANIFEST.as_posix(): "\n".join(sorted(declared)) + "\n",
                "secret.txt": "must never be staged\n",
                "references/undeclared.md": "also excluded\n",
            }
            for relative, content in fixture_files.items():
                path = source.joinpath(*relative.split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            contract = installer.load_payload_contract(source)
            stage = installer.stage_validated_install(source, skills_dir, contract)
            self.assertFalse((stage / "secret.txt").exists())
            self.assertFalse((stage / "references" / "undeclared.md").exists())
            self.assertEqual(installer.payload_manifest(stage), contract.file_manifest())
            marker = json.loads(
                (stage / installer.COMPLETION_MARKER).read_text(encoding="utf-8")
            )
            self.assertEqual(set(marker["files"]), set(declared))

            destination = skills_dir / installer.SKILL_NAME
            installer.promote_staged_install(stage, destination, skills_dir, contract)
            self.assertFalse((destination / "secret.txt").exists())
            self.assertFalse((destination / "references" / "undeclared.md").exists())
            self.assertTrue(installer.validate_completed_install(destination)[0])

    def test_declared_source_mutation_aborts_and_preserves_live_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(source)
            initial_stage = installer.stage_validated_install(source, skills_dir, contract)
            destination = skills_dir / installer.SKILL_NAME
            installer.promote_staged_install(
                initial_stage,
                destination,
                skills_dir,
                contract,
            )
            sentinel = destination / "local-sentinel.txt"
            sentinel.write_text("old live install survives\n", encoding="utf-8")

            original_load_contract = installer._load_payload_contract_once
            mutated = False

            def mutate_before_post_copy_snapshot(repo_root: Path):
                nonlocal mutated
                if not mutated:
                    (source / "SKILL.md").write_text(
                        "changed payload B\n",
                        encoding="utf-8",
                    )
                    mutated = True
                return original_load_contract(repo_root)

            with mock.patch.object(
                installer,
                "_load_payload_contract_once",
                mutate_before_post_copy_snapshot,
            ):
                with self.assertRaisesRegex(RuntimeError, "source payload changed"):
                    installer.stage_validated_install(source, skills_dir, contract)

            self.assertTrue(mutated, "the regression must mutate a declared source file")
            self.assertTrue(installer.validate_completed_install(destination)[0])
            self.assertEqual(
                sentinel.read_text(encoding="utf-8"),
                "old live install survives\n",
            )
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_atomic_manifest_replacement_during_capture_preserves_live_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(source)
            stage = installer.stage_validated_install(source, skills_dir, contract)
            destination = skills_dir / installer.SKILL_NAME
            installer.promote_staged_install(stage, destination, skills_dir, contract)
            sentinel = destination / "local-sentinel.txt"
            sentinel.write_text("live install must survive\n", encoding="utf-8")

            manifest = source / installer.PAYLOAD_MANIFEST.as_posix()
            replacement = manifest.with_name("replacement-manifest.tmp")
            replacement.write_text(
                manifest.read_text(encoding="utf-8") + "references/new-runtime.md\n",
                encoding="utf-8",
            )
            new_runtime = source / "references" / "new-runtime.md"
            new_runtime.parent.mkdir(parents=True)
            new_runtime.write_text("new content\n", encoding="utf-8")

            original_parse = installer._parse_payload_manifest_bytes
            replaced = False

            def replace_after_parse(path: Path, data: bytes):
                nonlocal replaced
                parsed = original_parse(path, data)
                if not replaced:
                    os.replace(replacement, manifest)
                    replaced = True
                return parsed

            with mock.patch.object(
                installer,
                "_parse_payload_manifest_bytes",
                replace_after_parse,
            ):
                with self.assertRaisesRegex(RuntimeError, "source payload changed"):
                    installer.load_payload_contract(source)

            self.assertTrue(replaced)
            self.assertTrue(installer.validate_completed_install(destination)[0])
            self.assertEqual(
                sentinel.read_text(encoding="utf-8"),
                "live install must survive\n",
            )
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_malformed_marker_never_authorizes_no_force_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            payload = self.install(skills_dir)
            sentinel = payload / "local-sentinel.txt"
            sentinel.write_text("must remain\n", encoding="utf-8")
            marker = payload / installer.COMPLETION_MARKER
            marker.write_text('{"files": {"victim": ', encoding="utf-8")

            result, output = self.run_installer(skills_dir)

            self.assertEqual(result, 1, output)
            self.assertIn("completion marker is untrusted", output)
            self.assertNotIn("Traceback", output)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must remain\n")
            self.assertEqual(marker.read_text(encoding="utf-8"), '{"files": {"victim": ')

    def test_forged_marker_contract_never_authorizes_no_force_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            payload = self.install(skills_dir)
            sentinel = payload / "local-sentinel.txt"
            sentinel.write_text("must remain\n", encoding="utf-8")
            skill = payload / "SKILL.md"
            skill.write_text("damaged\n", encoding="utf-8")
            marker = payload / installer.COMPLETION_MARKER
            record = json.loads(marker.read_text(encoding="utf-8"))
            record["contract_sha256"] = "0" * 64
            marker.write_text(json.dumps(record), encoding="utf-8")

            result, output = self.run_installer(skills_dir)

            self.assertEqual(result, 1, output)
            self.assertIn("completion marker is untrusted", output)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must remain\n")
            self.assertEqual(skill.read_text(encoding="utf-8"), "damaged\n")

    def test_semantically_equivalent_manifest_byte_change_breaks_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            payload = self.install(skills_dir)
            manifest = payload / installer.PAYLOAD_MANIFEST.as_posix()
            original = manifest.read_bytes()
            manifest.write_bytes(original + b"# semantically empty change\n")
            sentinel = payload / "local-sentinel.txt"
            sentinel.write_text("must remain\n", encoding="utf-8")

            result, output = self.run_installer(skills_dir)

            self.assertEqual(result, 1, output)
            self.assertIn("payload manifest digest does not match", output)
            self.assertEqual(manifest.read_bytes(), original + b"# semantically empty change\n")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must remain\n")

    def test_completed_install_must_match_the_current_source_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            original_contract = installer.load_payload_contract(source)
            stage = installer.stage_validated_install(
                source,
                skills_dir,
                original_contract,
            )
            destination = skills_dir / installer.SKILL_NAME
            installer.promote_staged_install(
                stage,
                destination,
                skills_dir,
                original_contract,
            )

            manifest = source / installer.PAYLOAD_MANIFEST.as_posix()
            manifest.write_bytes(manifest.read_bytes() + b"# new source contract\n")
            current_contract = installer.load_payload_contract(source)

            state, reason = installer.classify_existing_install(
                destination,
                current_contract,
            )
            self.assertEqual(state, "unknown")
            self.assertIn("different source payload contract", reason)

    def test_damaged_managed_install_with_unowned_file_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            payload = self.install(skills_dir)
            sentinel = payload / "local-sentinel.txt"
            sentinel.write_text("user-owned\n", encoding="utf-8")
            skill = payload / "SKILL.md"
            skill.write_text("damaged\n", encoding="utf-8")

            refused, refusal_output = self.run_installer(skills_dir)

            self.assertEqual(refused, 1, refusal_output)
            self.assertIn("unowned entries", refusal_output)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "user-owned\n")
            self.assertEqual(skill.read_text(encoding="utf-8"), "damaged\n")

            forced, force_output = self.run_installer(skills_dir, "--force")
            self.assertEqual(forced, 0, force_output)
            self.assertFalse(sentinel.exists())
            self.assertTrue(installer.validate_completed_install(payload)[0])

    def test_unowned_file_added_after_classification_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(source)
            initial = installer.stage_validated_install(source, skills_dir, contract)
            destination = skills_dir / installer.SKILL_NAME
            installer.promote_staged_install(initial, destination, skills_dir, contract)
            (destination / "SKILL.md").write_text("damaged\n", encoding="utf-8")
            state, _ = installer.classify_existing_install(destination, contract)
            self.assertEqual(state, "incomplete")

            replacement = installer.stage_validated_install(source, skills_dir, contract)
            sentinel = destination / "late-unowned.txt"
            sentinel.write_text("must survive\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "changed after transaction"):
                installer.promote_staged_install(
                    replacement,
                    destination,
                    skills_dir,
                    contract,
                    replacement_state=state,
                )
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must survive\n")
            self.assertEqual(
                (destination / "SKILL.md").read_text(encoding="utf-8"),
                "damaged\n",
            )
            self.assertTrue(replacement.is_dir(), "owned stage is preserved after refusal")
            self.assertTrue((skills_dir / installer.TRANSACTION_NAME).is_file())

    def test_interrupted_recovery_preserves_untrusted_live_tree_and_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            payload = self.install(skills_dir)
            backup = skills_dir / installer.BACKUP_NAME
            installer._rename_directory(payload, backup)
            payload.mkdir()
            sentinel = payload / "unowned.txt"
            sentinel.write_text("do not delete\n", encoding="utf-8")
            (payload / installer.COMPLETION_MARKER).write_text("{", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "preserv"):
                installer.recover_interrupted_transaction(skills_dir, payload)

            self.assertTrue(backup.is_dir())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not delete\n")

    def test_source_self_junction_is_rejected_before_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            manifest = source / installer.PAYLOAD_MANIFEST.as_posix()
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + "loop/SKILL.md\n",
                encoding="utf-8",
            )
            loop = source / "loop"
            self.directory_link_or_skip(loop, source)
            try:
                with self.assertRaisesRegex(ValueError, "linked or reparse component"):
                    installer.load_payload_contract(source)
            finally:
                self.remove_directory_link(loop)

    def test_manifest_directory_junction_is_rejected_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            validation = source / "validation"
            external = root / "external-validation"
            validation.replace(external)
            self.directory_link_or_skip(validation, external)
            try:
                with self.assertRaisesRegex(ValueError, "linked or reparse component"):
                    installer.load_payload_contract(source)
            finally:
                self.remove_directory_link(validation)

    def test_stage_junction_is_rejected_before_manifest_traversal_or_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(source)
            initial = installer.stage_validated_install(source, skills_dir, contract)
            destination = skills_dir / installer.SKILL_NAME
            installer.promote_staged_install(initial, destination, skills_dir, contract)
            sentinel = destination / "local-sentinel.txt"
            sentinel.write_text("old live tree\n", encoding="utf-8")

            original_capture = installer._capture_path_snapshot
            hostile_link: Path | None = None
            injected = False

            def inject_stage_junction(tree_root: Path):
                nonlocal hostile_link, injected
                if not injected and Path(tree_root).name.startswith(installer.STAGE_PREFIX):
                    hostile_link = Path(tree_root) / "self-loop"
                    self.directory_link_or_skip(hostile_link, Path(tree_root))
                    injected = True
                return original_capture(tree_root)

            try:
                with mock.patch.object(
                    installer,
                    "_capture_path_snapshot",
                    inject_stage_junction,
                ):
                    with self.assertRaisesRegex(RuntimeError, "staging recovery refused"):
                        installer.stage_validated_install(source, skills_dir, contract)
                self.assertTrue(installer.validate_completed_install(destination)[0])
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "old live tree\n")
            finally:
                if hostile_link is not None and installer._path_exists(hostile_link):
                    self.remove_directory_link(hostile_link)
                installer.recover_interrupted_transaction(skills_dir, destination)
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_linked_promotion_target_is_rejected_even_with_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            external = root / "external"
            external.mkdir()
            sentinel = external / "sentinel.txt"
            sentinel.write_text("outside\n", encoding="utf-8")
            destination = skills_dir / installer.SKILL_NAME
            self.directory_link_or_skip(destination, external)
            try:
                result, output = self.run_installer(skills_dir, "--force")
                self.assertEqual(result, 1, output)
                self.assertIn("linked or reparse", output)
                self.assertNotIn("Traceback", output)
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside\n")
            finally:
                self.remove_directory_link(destination)

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
                "references/nested/undeclared-note.md": (
                    "undeclared content with [ref:also-undeclared]\n"
                ),
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

    def test_every_installed_runtime_dependency_resolves_in_the_payload(self) -> None:
        tag_pattern = re.compile(rb"\[(ref|skill):([^\]\r\n]*)\]")
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            unresolved: list[str] = []
            dependency_count = 0
            for source in sorted(path for path in payload.rglob("*") if path.is_file()):
                data = source.read_bytes()
                for match in tag_pattern.finditer(data):
                    dependency_count += 1
                    kind = match.group(1).decode("ascii")
                    name = match.group(2).decode("utf-8")
                    target = (
                        payload / "references" / f"{name}.md"
                        if kind == "ref"
                        else payload / "skills" / name / "SKILL.md"
                    )
                    if not target.is_file():
                        unresolved.append(
                            f"{source.relative_to(payload).as_posix()}:"
                            f"[{kind}:{name}] -> {target.relative_to(payload).as_posix()}"
                        )
            self.assertGreater(dependency_count, 0, "fixture must exercise runtime tags")
            self.assertEqual(unresolved, [])

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

    def test_manifest_rejects_non_nfc_and_control_character_paths(self) -> None:
        for hostile in ("references/e\u0301.md", "references/a\tb.md"):
            with self.subTest(hostile=hostile), tempfile.TemporaryDirectory() as tmp:
                root = self.minimal_repo(Path(tmp), [hostile])
                with self.assertRaisesRegex(ValueError, "normalized POSIX relative path"):
                    installer.load_payload_manifest(root)

    def test_manifest_reader_rejects_same_tick_rewrite_with_restored_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), [])
            relative = installer.PAYLOAD_MANIFEST.as_posix()
            manifest = root / relative
            original = manifest.read_bytes()
            alternate = original.replace(b"SKILL.md", b"EVILL.md", 1)
            self.assertEqual(len(alternate), len(original))
            original_read = installer.os.read
            reads = 0

            def rewrite_then_read(descriptor: int, count: int) -> bytes:
                nonlocal reads
                reads += 1
                # A portable same-tick simulation: Windows prevents a real
                # writer from modifying a shared LockFileEx range.  Keep all
                # metadata unchanged and alter only the second descriptor
                # capture, which is exactly the coarse/no-ctime threat.
                if reads == 3:
                    return alternate
                if reads == 4:
                    return b""
                return original_read(descriptor, count)

            with mock.patch.object(installer.os, "read", side_effect=rewrite_then_read):
                with self.assertRaisesRegex(RuntimeError, "content changed"):
                    installer._read_stable_regular_bytes(
                        root,
                        relative,
                        label="install payload manifest",
                        max_bytes=installer.MAX_PAYLOAD_MANIFEST_BYTES,
                    )
            self.assertEqual(reads, 4)

    def test_source_metadata_rejects_same_tick_rewrite_with_restored_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), [])
            source = root / "SKILL.md"
            original = source.read_bytes()
            alternate = b"x" * len(original)
            original_read = installer.os.read
            reads = 0

            def rewrite_then_read(descriptor: int, count: int) -> bytes:
                nonlocal reads
                reads += 1
                if reads == 3:
                    return alternate
                if reads == 4:
                    return b""
                return original_read(descriptor, count)

            with mock.patch.object(installer.os, "read", side_effect=rewrite_then_read):
                with self.assertRaisesRegex(RuntimeError, "content changed"):
                    installer._regular_file_metadata(source)
            self.assertEqual(reads, 4)

    def test_declared_payload_file_cannot_be_hard_linked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = self.minimal_repo(base / "source", [])
            declared = root / "SKILL.md"
            victim = base / "outside-user-file.md"
            victim.write_text("fixture\n", encoding="utf-8")
            declared.unlink()
            os.link(victim, declared)

            with self.assertRaisesRegex(RuntimeError, "hard-linked"):
                installer.load_payload_contract(root)

    def test_manifest_rejects_missing_declared_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), ["references/missing.md"])
            with self.assertRaisesRegex(FileNotFoundError, "declared payload path file is missing"):
                installer.load_payload_manifest(root)

    def test_runtime_dependency_target_must_be_declared_with_actionable_error(self) -> None:
        cases = (
            ("ref", "missing-reference", "references/missing-reference.md"),
            ("skill", "missing-skill", "skills/missing-skill/SKILL.md"),
        )
        for kind, name, target_relative in cases:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = self.minimal_repo(Path(tmp), ["references/caller.md"])
                caller = root / "references" / "caller.md"
                caller.parent.mkdir(parents=True, exist_ok=True)
                caller.write_text(f"[{kind}:{name}]\n", encoding="utf-8")
                target = root / target_relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("present but undeclared\n", encoding="utf-8")

                with self.assertRaises(ValueError) as raised:
                    installer.load_payload_contract(root)

                message = str(raised.exception)
                self.assertIn(f"references/caller.md:1", message)
                self.assertIn(f"[{kind}:{name}]", message)
                self.assertIn(target_relative, message)
                self.assertIn("absent from validation/install-payload.txt", message)
                self.assertIn("add it to validation/install-payload.txt", message)

    def test_runtime_dependency_parser_spans_read_chunks(self) -> None:
        declared = frozenset({"references/present.md"})
        scanner = installer._RuntimeDependencyClosureScanner("SKILL.md", declared)
        for chunk in (b"first line\r\n[re", b"f:pre", b"sent] trailing"):
            scanner.feed(chunk)
        scanner.raise_for_error()

        missing = installer._RuntimeDependencyClosureScanner("SKILL.md", declared)
        for chunk in (b"first line\r\n[sk", b"ill:miss", b"ing]"):
            missing.feed(chunk)
        with self.assertRaises(ValueError) as raised:
            missing.raise_for_error()
        self.assertIn("SKILL.md:2", str(raised.exception))
        self.assertIn("skills/missing/SKILL.md", str(raised.exception))

    def test_cli_bounds_preflight_manifest_errors_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            copied_installer = source / "scripts" / "install_codex_skill.py"
            copied_installer.parent.mkdir(parents=True)
            shutil.copy2(ROOT / "scripts" / "install_codex_skill.py", copied_installer)
            (source / "SKILL.md").write_text("fixture\n", encoding="utf-8")
            manifest = source / installer.PAYLOAD_MANIFEST.as_posix()
            manifest.parent.mkdir(parents=True)
            manifest.write_bytes(b"x" * (installer.MAX_PAYLOAD_MANIFEST_BYTES + 1))
            destination = root / "skills"

            result = subprocess.run(
                [sys.executable, str(copied_installer), "--dest", str(destination)],
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 1, output)
            self.assertIn("Refusing to install:", output)
            self.assertIn("exceeds", output)
            self.assertNotIn("Traceback", output)
            self.assertLessEqual(len(output), installer.MAX_DIAGNOSTIC_CHARS + 40)
            self.assertFalse(destination.exists())


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

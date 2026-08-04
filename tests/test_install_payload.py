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
import stat
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

    def assert_owner_writable_directories(self, root: Path) -> None:
        directories = [root, *(path for path in root.rglob("*") if path.is_dir())]
        for directory in directories:
            mode = stat.S_IMODE(directory.lstat().st_mode)
            self.assertEqual(
                mode & installer._OWNER_DIRECTORY_ACCESS,
                installer._OWNER_DIRECTORY_ACCESS,
                directory,
            )

    def test_public_staging_api_recomputes_policy_and_refuses_unknown_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            destination = skills_dir / installer.SKILL_NAME
            destination.mkdir(parents=True)
            sentinel = destination / "user-data.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")
            contract = installer.load_payload_contract(source)

            with self.assertRaisesRegex(RuntimeError, "requires an explicit force"):
                installer.stage_validated_install(source, skills_dir, contract)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_transaction_persists_the_recomputed_replacement_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(source)

            stage = installer.stage_validated_install(source, skills_dir, contract)
            record, _ = installer._load_transaction(skills_dir)

            self.assertEqual(record["replacement_state"], "missing")
            self.assertIs(record["force"], False)
            installer.promote_staged_install(
                stage, skills_dir / installer.SKILL_NAME, skills_dir, contract
            )

    def test_staging_is_bound_to_the_authorized_destination_classification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            destination = skills_dir / installer.SKILL_NAME
            contract = installer.load_payload_contract(source)
            authorized = installer._classify_existing_install_bound(
                destination, contract
            )
            destination.mkdir()
            sentinel = destination / "user-data.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "destination changed"):
                installer.stage_validated_install(
                    source,
                    skills_dir,
                    contract,
                    authorized_destination=authorized,
                )

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_public_transaction_entrypoints_reject_redirected_destinations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            other_skills = root / "other-skills"
            other_skills.mkdir()
            redirected = other_skills / installer.SKILL_NAME
            contract = installer.load_payload_contract(source)
            stage = installer.stage_validated_install(source, skills_dir, contract)

            with self.assertRaisesRegex(ValueError, "inside the skills directory"):
                installer.promote_staged_install(
                    stage,
                    redirected,
                    skills_dir,
                    contract,
                )
            with self.assertRaisesRegex(ValueError, "inside the skills directory"):
                installer.recover_interrupted_transaction(skills_dir, redirected)

            self.assertTrue(stage.is_dir())
            self.assertTrue((skills_dir / installer.TRANSACTION_NAME).is_file())
            self.assertFalse(redirected.exists())
            installer.recover_interrupted_transaction(
                skills_dir,
                skills_dir / installer.SKILL_NAME,
            )

    @unittest.skipIf(os.name == "nt", "POSIX portable-mode contract")
    def test_source_permission_drift_is_normalized_not_propagated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(source)
            for directory in [source, *(path for path in source.rglob("*") if path.is_dir())]:
                directory.chmod(0o777)
            for file_path in (path for path in source.rglob("*") if path.is_file()):
                file_path.chmod(0o777)
            source_modes = {
                path.relative_to(source).as_posix(): stat.S_IMODE(path.lstat().st_mode)
                for path in [source, *source.rglob("*")]
            }

            stage = installer.stage_validated_install(source, skills_dir, contract)
            self.assertEqual(
                stat.S_IMODE(stage.lstat().st_mode),
                installer.PORTABLE_DIRECTORY_MODE,
            )
            for candidate in stage.rglob("*"):
                expected = (
                    installer.PORTABLE_DIRECTORY_MODE
                    if candidate.is_dir()
                    else (
                        installer.PORTABLE_FILE_MODE
                        if candidate.name
                        in {installer.PROVENANCE_MARKER, installer.COMPLETION_MARKER}
                        else installer.INSTALLED_PAYLOAD_FILE_MODE
                    )
                )
                self.assertEqual(stat.S_IMODE(candidate.lstat().st_mode), expected)
            self.assertEqual(
                {
                    path.relative_to(source).as_posix(): stat.S_IMODE(
                        path.lstat().st_mode
                    )
                    for path in [source, *source.rglob("*")]
                },
                source_modes,
            )

            destination = skills_dir / installer.SKILL_NAME
            installer.promote_staged_install(stage, destination, skills_dir, contract)
            for candidate in [destination, *destination.rglob("*")]:
                expected = (
                    installer.INSTALLED_PAYLOAD_DIRECTORY_MODE
                    if candidate.is_dir()
                    else (
                        installer.PORTABLE_FILE_MODE
                        if candidate.name
                        in {installer.PROVENANCE_MARKER, installer.COMPLETION_MARKER}
                        else installer.INSTALLED_PAYLOAD_FILE_MODE
                    )
                )
                self.assertEqual(stat.S_IMODE(candidate.lstat().st_mode), expected)
            self.assertEqual(
                {
                    path.relative_to(source).as_posix(): stat.S_IMODE(
                        path.lstat().st_mode
                    )
                    for path in [source, *source.rglob("*")]
                },
                source_modes,
            )

    @unittest.skipUnless(
        os.name != "nt" and hasattr(os, "setxattr"),
        "POSIX extended-attribute policy",
    )
    def test_source_root_directory_and_file_xattrs_fail_before_transaction(self) -> None:
        for target_kind in ("root", "directory", "file"):
            with self.subTest(target_kind=target_kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = self.fixture_source(root)
                skills_dir = root / "skills"
                skills_dir.mkdir()
                target = {
                    "root": source,
                    "directory": source / "scripts",
                    "file": source / "SKILL.md",
                }[target_kind]
                try:
                    os.setxattr(target, "user.seedance-source-test", b"unsupported")
                except OSError as exc:
                    self.skipTest(f"temporary filesystem does not support xattrs: {exc}")

                with self.assertRaisesRegex(RuntimeError, "not representable"):
                    contract = installer.load_payload_contract(source)
                    installer.stage_validated_install(source, skills_dir, contract)

                self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
                self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    @unittest.skipUnless(os.name == "nt", "Windows named-stream policy")
    def test_source_directory_and_file_streams_fail_before_transaction(self) -> None:
        for target_kind in ("root", "directory", "file"):
            with self.subTest(target_kind=target_kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = self.fixture_source(root)
                skills_dir = root / "skills"
                skills_dir.mkdir()
                target = {
                    "root": source,
                    "directory": source / "scripts",
                    "file": source / "SKILL.md",
                }[target_kind]
                Path(f"{target}:seedance-source-test").write_bytes(b"unsupported")

                with self.assertRaisesRegex(RuntimeError, "not representable"):
                    contract = installer.load_payload_contract(source)
                    installer.stage_validated_install(source, skills_dir, contract)

                self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
                self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_transaction_validator_rejects_no_force_unknown_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            destination = skills_dir / installer.SKILL_NAME
            destination.mkdir(parents=True)
            sentinel = destination / "user-data.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")
            contract = installer.load_payload_contract(source)
            snapshot = installer._capture_path_snapshot(destination)
            transaction_id = "a" * 32
            record = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                contract.file_manifest(),
                snapshot,
                "unknown",
                False,
            )

            with self.assertRaisesRegex(ValueError, "does not authorize"):
                installer._validate_transaction_before_publication(record)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

    @unittest.skipUnless(os.name == "nt", "Windows legal-name round-trip")
    def test_unserializable_windows_live_name_is_refused_before_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            destination = skills_dir / installer.SKILL_NAME
            destination.mkdir(parents=True)
            sentinel = destination / "keep\u200b.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")
            contract = installer.load_payload_contract(source)

            with self.assertRaisesRegex(ValueError, "unsafe path"):
                installer.stage_validated_install(
                    source, skills_dir, contract, force=True
                )

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    @unittest.skipIf(os.name == "nt", "POSIX filename round-trip cases")
    def test_unserializable_posix_live_names_are_refused_before_artifacts(self) -> None:
        cases = (
            ("casefold", ("Case.txt", "case.txt")),
            ("nfd", ("e\u0301.txt",)),
            ("colon", ("keep:note.txt",)),
            ("control", ("keep\x01note.txt",)),
        )
        for label, names in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = self.fixture_source(root)
                skills_dir = root / "skills"
                destination = skills_dir / installer.SKILL_NAME
                destination.mkdir(parents=True)
                sentinels = [destination / name for name in names]
                for sentinel in sentinels:
                    sentinel.write_text("preserve\n", encoding="utf-8")
                contract = installer.load_payload_contract(source)

                with self.assertRaisesRegex(ValueError, "unsafe|case-ambiguous"):
                    installer.stage_validated_install(
                        source, skills_dir, contract, force=True
                    )

                for sentinel in sentinels:
                    self.assertEqual(
                        sentinel.read_text(encoding="utf-8"), "preserve\n"
                    )
                self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
                self.assertEqual(
                    list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), []
                )

    @unittest.skipIf(os.name == "nt", "POSIX directory mode contract")
    def test_read_only_source_directories_are_writable_in_stage_and_live(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(source)
            source_directories = [
                source,
                *(path for path in source.rglob("*") if path.is_dir()),
            ]
            for directory in sorted(
                source_directories, key=lambda path: len(path.parts), reverse=True
            ):
                directory.chmod(0o555)
            try:
                stage = installer.stage_validated_install(
                    source, skills_dir, contract
                )
                self.assert_owner_writable_directories(stage)
                destination = skills_dir / installer.SKILL_NAME
                installer.promote_staged_install(
                    stage, destination, skills_dir, contract
                )
                self.assert_owner_writable_directories(destination)
            finally:
                for directory in sorted(
                    source_directories, key=lambda path: len(path.parts)
                ):
                    if directory.exists():
                        directory.chmod(0o755)

    @unittest.skipIf(os.name == "nt", "POSIX directory mode contract")
    def test_read_only_live_tree_can_be_force_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(source)
            initial = installer.stage_validated_install(source, skills_dir, contract)
            destination = skills_dir / installer.SKILL_NAME
            installer.promote_staged_install(
                initial, destination, skills_dir, contract
            )
            live_directories = [
                destination,
                *(path for path in destination.rglob("*") if path.is_dir()),
            ]
            for directory in sorted(
                live_directories, key=lambda path: len(path.parts), reverse=True
            ):
                directory.chmod(0o555)
            try:
                replacement = installer.stage_validated_install(
                    source, skills_dir, contract, force=True
                )
                installer.promote_staged_install(
                    replacement,
                    destination,
                    skills_dir,
                    contract,
                )

                self.assertTrue(installer.validate_completed_install(destination)[0])
                self.assert_owner_writable_directories(destination)
                self.assertFalse((skills_dir / installer.BACKUP_NAME).exists())
                self.assertEqual(
                    list(skills_dir.glob(f"{installer.QUARANTINE_PREFIX}*")), []
                )
                self.assertEqual(
                    list(skills_dir.glob(f"{installer.PRIVATE_DELETE_PREFIX}*")), []
                )
            finally:
                current_directories = [
                    skills_dir,
                    *(path for path in skills_dir.rglob("*") if path.is_dir()),
                ]
                for directory in sorted(
                    current_directories, key=lambda path: len(path.parts)
                ):
                    directory.chmod(0o755)

    @unittest.skipIf(os.name == "nt", "POSIX directory mode contract")
    def test_read_only_interrupted_stage_is_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(source)
            stage = installer.stage_validated_install(source, skills_dir, contract)
            stage_directories = [
                stage,
                *(path for path in stage.rglob("*") if path.is_dir()),
            ]
            for directory in sorted(
                stage_directories, key=lambda path: len(path.parts), reverse=True
            ):
                directory.chmod(0o555)
            try:
                installer.recover_interrupted_transaction(
                    skills_dir, skills_dir / installer.SKILL_NAME
                )
                self.assertFalse(stage.exists())
                self.assertFalse(
                    (skills_dir / installer.TRANSACTION_NAME).exists()
                )
            finally:
                current_directories = [
                    skills_dir,
                    *(path for path in skills_dir.rglob("*") if path.is_dir()),
                ]
                for directory in sorted(
                    current_directories, key=lambda path: len(path.parts)
                ):
                    directory.chmod(0o755)

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

    def test_public_staging_rejects_a_linked_skills_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            contract = installer.load_payload_contract(source)
            real_skills = root / "real-skills"
            real_skills.mkdir()
            linked_skills = root / "linked-skills"
            self.directory_link_or_skip(linked_skills, real_skills)
            try:
                with self.assertRaisesRegex(ValueError, "linked or reparse"):
                    installer.stage_validated_install(
                        source,
                        linked_skills,
                        contract,
                    )
            finally:
                self.remove_directory_link(linked_skills)

            self.assertEqual(list(real_skills.iterdir()), [])

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
            contract_loads = 0

            def mutate_before_post_copy_snapshot(repo_root: Path):
                nonlocal contract_loads, mutated
                contract_loads += 1
                if contract_loads == 2:
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
                    installer.stage_validated_install(
                        source, skills_dir, contract, force=True
                    )

            self.assertTrue(mutated, "the regression must mutate a declared source file")
            self.assertTrue(installer.validate_completed_install(destination)[0])
            self.assertEqual(
                sentinel.read_text(encoding="utf-8"),
                "old live install survives\n",
            )
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_late_source_directory_fork_aborts_without_stranding_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(source)
            original_copy = installer._copy_payload_file_atomic
            injected = False

            def copy_then_inject(source_path: str, destination_path: str, **kwargs):
                nonlocal injected
                result = original_copy(source_path, destination_path, **kwargs)
                if not injected:
                    target = source / "scripts"
                    if os.name == "nt":
                        Path(f"{target}:late-source-policy").write_bytes(b"unsupported")
                    elif hasattr(os, "setxattr"):
                        try:
                            os.setxattr(
                                target,
                                "user.seedance-late-source-policy",
                                b"unsupported",
                            )
                        except OSError as exc:
                            self.skipTest(
                                f"temporary filesystem does not support xattrs: {exc}"
                            )
                    else:
                        self.skipTest("source metadata forks are unavailable")
                    injected = True
                return result

            with mock.patch.object(
                installer,
                "_copy_payload_file_atomic",
                copy_then_inject,
            ):
                with self.assertRaisesRegex(RuntimeError, "not representable"):
                    installer.stage_validated_install(source, skills_dir, contract)

            self.assertTrue(injected)
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])
            self.assertFalse((skills_dir / installer.SKILL_NAME).exists())

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
            self.assertIn("different source payload", reason)

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
                        installer.stage_validated_install(
                            source, skills_dir, contract, force=True
                        )
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
            "scripts/lineage_contract.py",
            "scripts/strict_json.py",
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
        self.assertEqual(
            credential_env_reads(tree),
            {"ANTHROPIC_API_KEY", "MINIMAX_API_KEY"},
        )

    def test_the_skill_itself_is_still_installed(self) -> None:
        """Guard against the payload contract quietly gutting the install."""
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            self.assertTrue((payload / "SKILL.md").exists())
            self.assertTrue((payload / "references").is_dir())
            self.assertTrue((payload / "references" / "directors-read.md").exists())
            self.assertTrue((payload / "skills").is_dir())
            self.assertTrue((payload / "validation" / "fixtures" / "directors-read-cases.json").exists())
            self.assertTrue(
                (payload / "validation" / "authoring-state-provenance-ledger.json").exists()
            )
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

    def set_windows_mount_point(self, source: Path, target: Path) -> None:
        import ctypes
        import struct
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        create_file.restype = wintypes.HANDLE
        device_io_control = kernel32.DeviceIoControl
        device_io_control.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        device_io_control.restype = wintypes.BOOL
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL

        handle = create_file(
            str(source),
            0x00000100,  # FILE_WRITE_ATTRIBUTES is sufficient for this ioctl
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,  # OPEN_EXISTING
            0x02000000 | 0x00200000,
            None,
        )
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            substitute = f"\\??\\{target}".encode("utf-16-le")
            printable = str(target).encode("utf-16-le")
            paths = substitute + b"\x00\x00" + printable + b"\x00\x00"
            payload = struct.pack(
                "<LHHHHHH",
                0xA0000003,  # IO_REPARSE_TAG_MOUNT_POINT
                8 + len(paths),
                0,
                0,
                len(substitute),
                len(substitute) + 2,
                len(printable),
            ) + paths
            buffer = ctypes.create_string_buffer(payload)
            returned = wintypes.DWORD()
            if not device_io_control(
                handle,
                0x000900A4,  # FSCTL_SET_REPARSE_POINT
                buffer,
                len(payload),
                None,
                0,
                ctypes.byref(returned),
                None,
            ):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            close_handle(handle)

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

    def test_manifest_rejects_archive_only_paths(self) -> None:
        for relative in (
            "references/migrated/README.md",
            "REFERENCES/MIGRATED/README.md",
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                root = self.minimal_repo(Path(tmp), [relative])
                with self.assertRaisesRegex(
                    ValueError,
                    "archive-only path cannot be installed",
                ):
                    installer.load_payload_manifest(root)

    def test_payload_contract_bounds_individual_and_total_source_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), [])
            files = [path for path in root.rglob("*") if path.is_file()]
            largest = max(path.stat().st_size for path in files)
            total = sum(path.stat().st_size for path in files)

            with mock.patch.object(installer, "MAX_INSTALL_FILE_BYTES", largest - 1):
                with self.assertRaisesRegex(ValueError, "payload file exceeds"):
                    installer.load_payload_contract(root)

            with (
                mock.patch.object(installer, "MAX_INSTALL_FILE_BYTES", largest),
                mock.patch.object(installer, "MAX_INSTALL_PAYLOAD_BYTES", total - 1),
            ):
                with self.assertRaisesRegex(ValueError, "payload exceeds"):
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
                self.assertIn("references/caller.md:1", message)
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

    def test_source_snapshot_scans_only_the_first_repeated_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), [])
            expected = (root / "SKILL.md").read_bytes()
            consumed: list[bytes] = []

            snapshot = installer._source_file_snapshot(
                root,
                "SKILL.md",
                chunk_consumer=consumed.append,
            )

            self.assertEqual(b"".join(consumed), expected)
            self.assertEqual(snapshot.size, len(expected))

    def test_intermediate_component_swap_before_bound_open_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            relative = "references/linked/runtime.md"
            root = self.minimal_repo(sandbox / "repo", [relative])
            linked = root / "references" / "linked"
            linked.mkdir(parents=True)
            (linked / "runtime.md").write_text("declared\n", encoding="utf-8")
            external = sandbox / "external"
            external.mkdir()
            (external / "runtime.md").write_text("external\n", encoding="utf-8")
            displaced = root / "references" / "displaced"
            attacked = False

            if os.name == "nt":
                original_open = installer._win32_open_relative_directory_component

                def attack(
                    parent_handle: int,
                    name: str,
                    path: Path,
                    label: str,
                    diagnostic: str,
                ) -> int:
                    nonlocal attacked
                    if path == linked and not attacked:
                        attacked = True
                        linked.rename(displaced)
                        self.junction_or_skip(linked, external)
                    return original_open(
                        parent_handle,
                        name,
                        path,
                        label,
                        diagnostic,
                    )

                patch = mock.patch.object(
                    installer,
                    "_win32_open_relative_directory_component",
                    side_effect=attack,
                )
                rejection = self.assertRaises((OSError, ValueError))
            else:
                original_open = installer.os.open

                def attack(
                    path: str | os.PathLike[str],
                    flags: int,
                    mode: int = 0o777,
                    *,
                    dir_fd: int | None = None,
                ) -> int:
                    nonlocal attacked
                    if os.fspath(path) == "linked" and dir_fd is not None and not attacked:
                        attacked = True
                        linked.rename(displaced)
                        self.symlink_or_skip(
                            linked,
                            external,
                            target_is_directory=True,
                        )
                    return original_open(path, flags, mode, dir_fd=dir_fd)

                patch = mock.patch.object(installer.os, "open", side_effect=attack)
                rejection = self.assertRaisesRegex(
                    ValueError,
                    "linked or reparse component",
                )

            with patch, rejection:
                installer._read_stable_regular_bytes(
                    root,
                    relative,
                    label="declared payload path",
                    max_bytes=1024,
                )
            self.assertTrue(attacked)

    @unittest.skipUnless(os.name == "nt", "Windows sharing semantics only")
    def test_bound_parent_rejects_child_open_after_in_place_reparse_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            relative = "references/linked/runtime.md"
            root = self.minimal_repo(sandbox / "repo", [relative])
            references = root / "references"
            references.mkdir()
            linked = root / "references" / "linked"
            external = sandbox / "external"
            (external / "linked").mkdir(parents=True)
            (external / "linked" / "runtime.md").write_bytes(b"external")

            probe = sandbox / "probe"
            probe.mkdir()
            try:
                self.set_windows_mount_point(probe, external)
            except OSError as exc:
                self.skipTest(f"Windows mount points are unavailable: {exc}")
            probe.rmdir()

            original_open = installer._win32_open_relative_directory_component
            attacked = False

            def attack(
                parent_handle: int,
                name: str,
                path: Path,
                label: str,
                diagnostic: str,
            ) -> int:
                nonlocal attacked
                if path == linked and not attacked:
                    attacked = True
                    self.set_windows_mount_point(references, external)
                return original_open(
                    parent_handle,
                    name,
                    path,
                    label,
                    diagnostic,
                )

            with (
                mock.patch.object(
                    installer,
                    "_win32_open_relative_directory_component",
                    side_effect=attack,
                ),
                self.assertRaises((OSError, ValueError)),
            ):
                installer._read_stable_regular_bytes(
                    root,
                    relative,
                    label="declared payload path",
                    max_bytes=1024,
                )
            self.assertTrue(attacked)
            self.assertTrue(installer._is_reparse_stat(references.lstat()))

    @unittest.skipUnless(os.name == "nt", "Windows sharing semantics only")
    def test_bound_leaf_blocks_rewrite_before_record_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            relative = "references/runtime.md"
            root = self.minimal_repo(Path(tmp) / "repo", [relative])
            leaf = root / relative
            leaf.parent.mkdir(parents=True)
            leaf.write_bytes(b"declared")
            original_lock = installer._locked_record_descriptor
            attacked = False

            @contextlib.contextmanager
            def attack(
                descriptor: int,
                range_length: int = installer.MAX_RECORD_BYTES + 1,
                *,
                exclusive: bool = True,
            ):
                nonlocal attacked
                if not attacked:
                    attacked = True
                    with self.assertRaises(OSError):
                        leaf.write_bytes(b"external")
                with original_lock(
                    descriptor,
                    range_length,
                    exclusive=exclusive,
                ):
                    yield

            with mock.patch.object(
                installer,
                "_locked_record_descriptor",
                side_effect=attack,
            ):
                _snapshot, raw = installer._read_stable_regular_bytes(
                    root,
                    relative,
                    label="declared payload path",
                    max_bytes=1024,
                )
            self.assertTrue(attacked)
            self.assertEqual(raw, b"declared")

    @unittest.skipUnless(os.name == "nt", "Windows handle-relative semantics only")
    def test_bound_read_does_not_reresolve_full_windows_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            relative = "references/runtime.md"
            root = self.minimal_repo(Path(tmp) / "repo", [relative])
            leaf = root / relative
            leaf.parent.mkdir(parents=True)
            leaf.write_bytes(b"declared")

            with mock.patch.object(
                Path,
                "lstat",
                side_effect=AssertionError("full path was re-resolved"),
            ):
                _snapshot, raw = installer._read_stable_regular_bytes(
                    root,
                    relative,
                    label="declared payload path",
                    max_bytes=1024,
                )
            self.assertEqual(raw, b"declared")

    @unittest.skipIf(os.name == "nt", "POSIX dir_fd semantics only")
    def test_leaf_swap_between_stat_and_open_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            relative = "references/runtime.md"
            root = self.minimal_repo(sandbox / "repo", [relative])
            leaf = root / relative
            leaf.parent.mkdir(parents=True)
            leaf.write_bytes(b"declared")
            displaced = sandbox / "displaced.md"
            replacement = sandbox / "replacement.md"
            replacement.write_bytes(b"external")
            original_open = installer.os.open
            attacked = False

            def attack(
                path: str | os.PathLike[str],
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                nonlocal attacked
                if os.fspath(path) == leaf.name and dir_fd is not None and not attacked:
                    attacked = True
                    leaf.rename(displaced)
                    replacement.rename(leaf)
                return original_open(path, flags, mode, dir_fd=dir_fd)

            with (
                mock.patch.object(installer.os, "open", side_effect=attack),
                self.assertRaisesRegex(RuntimeError, "changed while it was being opened"),
            ):
                installer._read_stable_regular_bytes(
                    root,
                    relative,
                    label="declared payload path",
                    max_bytes=1024,
                )
            self.assertTrue(attacked)

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

    def test_manifest_rejects_declared_file_symlink_to_internal_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), ["references/linked.md"])
            (root / "runtime.md").write_text("runtime\n", encoding="utf-8")
            self.symlink_or_skip(root / "references/linked.md", Path("../runtime.md"))

            with self.assertRaisesRegex(ValueError, "linked or reparse component") as raised:
                installer.load_payload_manifest(root)
            self.assertIn("references/linked.md", str(raised.exception))

    def test_manifest_rejects_declared_file_symlink_to_external_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            root = self.minimal_repo(sandbox / "repo", ["references/linked.md"])
            external = sandbox / "external.md"
            external.write_text("external\n", encoding="utf-8")
            self.symlink_or_skip(root / "references/linked.md", external)

            with self.assertRaisesRegex(ValueError, "linked or reparse component") as raised:
                installer.load_payload_manifest(root)
            self.assertIn("references/linked.md", str(raised.exception))

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
            self.assertIn("references/linked/runtime.md", str(raised.exception))

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
            self.assertIn("references/linked/runtime.md", str(raised.exception))

    def test_manifest_rejects_internal_windows_junction_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), ["references/linked/runtime.md"])
            target = root / "runtime"
            target.mkdir()
            (target / "runtime.md").write_text("runtime\n", encoding="utf-8")
            self.junction_or_skip(root / "references/linked", target)

            with self.assertRaisesRegex(ValueError, "linked or reparse component") as raised:
                installer.load_payload_manifest(root)
            self.assertIn("references/linked/runtime.md", str(raised.exception))

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
            self.assertIn("references/linked/runtime.md", str(raised.exception))

    def test_manifest_rejects_linked_manifest_before_reading_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.minimal_repo(Path(tmp), [])
            manifest = root / installer.PAYLOAD_MANIFEST.as_posix()
            target = root / "real-manifest.txt"
            manifest.replace(target)
            self.symlink_or_skip(manifest, Path("../real-manifest.txt"))

            with self.assertRaisesRegex(
                ValueError,
                "install payload manifest contains a linked or reparse component",
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
                "install payload manifest contains a linked or reparse component",
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

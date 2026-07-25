"""The shipped schemas must actually accept the shipped examples.

Other checkers re-declare required fields in Python, so a schema and its
examples can drift apart while both still pass. These tests pin the executable
relationship: every schema is declared with at least one instance, the
instances validate, and the checker fails rather than passing quietly when
something breaks.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import schema_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HAVE_JSONSCHEMA = schema_check.Draft202012Validator is not None


class ManifestTests(unittest.TestCase):
    def test_every_schema_is_declared_with_an_instance(self) -> None:
        manifest = json.loads((ROOT / "validation/schema-instances.json").read_text("utf-8"))
        declared = manifest["instances"]
        on_disk = {p.name for p in (ROOT / "schemas").glob("*.schema.json")}
        self.assertEqual(
            on_disk,
            set(declared),
            "every schema needs an entry in validation/schema-instances.json",
        )
        for name, instances in declared.items():
            with self.subTest(schema=name):
                self.assertTrue(instances, f"{name} must declare at least one instance")
                for relative in instances:
                    self.assertTrue((ROOT / relative).exists(), f"missing instance {relative}")

    def test_duplicate_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dup.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate object key"):
                schema_check.load_json(path)


@unittest.skipUnless(HAVE_JSONSCHEMA, "jsonschema not installed")
class ExecutionTests(unittest.TestCase):
    def test_repository_passes(self) -> None:
        self.assertEqual(schema_check.check(ROOT), [])

    def _copy_repo(self, tmp: str) -> Path:
        dest = Path(tmp) / "repo"
        for part in ("schemas", "examples", "validation"):
            shutil.copytree(ROOT / part, dest / part)
        return dest

    def test_example_violating_its_schema_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            target = repo / "examples/standalone-clip/project-state.json"
            data = json.loads(target.read_text("utf-8"))
            data["schema_version"] = 1  # declared as a string
            target.write_text(json.dumps(data), encoding="utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(any("schema_version" in e for e in errors), errors)

    def test_schema_requiring_a_field_no_example_has_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            target = repo / "schemas/take-review.schema.json"
            schema = json.loads(target.read_text("utf-8"))
            schema["required"] = list(schema["required"]) + ["field_no_example_has"]
            target.write_text(json.dumps(schema), encoding="utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(any("field_no_example_has" in e for e in errors), errors)

    def test_undeclared_schema_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            manifest = repo / "validation/schema-instances.json"
            data = json.loads(manifest.read_text("utf-8"))
            del data["instances"]["take-review.schema.json"]
            manifest.write_text(json.dumps(data), encoding="utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(any("has no entry" in e for e in errors), errors)

    def test_declared_schema_that_does_not_exist_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            manifest = repo / "validation/schema-instances.json"
            data = json.loads(manifest.read_text("utf-8"))
            data["instances"]["ghost.schema.json"] = ["examples/standalone-clip/project-state.json"]
            manifest.write_text(json.dumps(data), encoding="utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(any("ghost.schema.json" in e for e in errors), errors)


class DependencyTests(unittest.TestCase):
    def test_missing_dependency_fails_rather_than_skipping(self) -> None:
        """A silent skip would let CI report success while validating nothing."""
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/schema_check.py"), str(ROOT)],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn(result.returncode, (0, 2), result.stdout + result.stderr)
        if result.returncode == 2:
            self.assertIn("requires jsonschema", result.stderr)


if __name__ == "__main__":
    unittest.main()

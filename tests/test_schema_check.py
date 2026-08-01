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

    def test_project_state_rejects_empty_or_whitespace_parent_ids(self) -> None:
        for invalid in ("", "   "):
            with self.subTest(parent_clip_id=invalid), tempfile.TemporaryDirectory() as tmp:
                repo = self._copy_repo(tmp)
                target = repo / "examples/standalone-clip/project-state.json"
                data = json.loads(target.read_text("utf-8"))
                data["clips"][0]["parent_clip_id"] = invalid
                target.write_text(json.dumps(data), encoding="utf-8")
                errors = schema_check.check(repo)
                self.assertTrue(
                    any(
                        "project-state.json against schemas/project-state.schema.json" in error
                        and "parent_clip_id" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_clip_contract_rejects_empty_or_whitespace_parent_ids(self) -> None:
        for invalid in ("", "   "):
            with self.subTest(parent_clip_id=invalid), tempfile.TemporaryDirectory() as tmp:
                repo = self._copy_repo(tmp)
                target = repo / "examples/sequence-airport-arrival/clip-01-contract.json"
                data = json.loads(target.read_text("utf-8"))
                data["parent_clip_id"] = invalid
                target.write_text(json.dumps(data), encoding="utf-8")
                errors = schema_check.check(repo)
                self.assertTrue(
                    any(
                        "clip-01-contract.json against schemas/clip-contract.schema.json" in error
                        and "parent_clip_id" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_null_root_parent_remains_schema_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            project = repo / "examples/standalone-clip/project-state.json"
            contract = repo / "examples/sequence-airport-arrival/clip-01-contract.json"
            self.assertIsNone(json.loads(project.read_text("utf-8"))["clips"][0]["parent_clip_id"])
            self.assertIsNone(json.loads(contract.read_text("utf-8"))["parent_clip_id"])
            self.assertEqual(schema_check.check(repo), [])

    def test_project_schema_enforces_root_and_later_parent_policy(self) -> None:
        schema = schema_check.load_json(ROOT / "schemas/project-state.schema.json")
        validator = schema_check.Draft202012Validator(schema)
        base = json.loads(
            (ROOT / "examples/sequence-observed-deviation/project-state-before.json").read_text(
                "utf-8"
            )
        )

        for mode in ("missing", "null"):
            with self.subTest(later_parent=mode):
                data = json.loads(json.dumps(base))
                later = data["clips"][1]
                if mode == "missing":
                    later.pop("parent_clip_id")
                else:
                    later["parent_clip_id"] = None
                self.assertTrue(list(validator.iter_errors(data)))

        first_with_parent = json.loads(json.dumps(base))
        first_with_parent["clips"][0]["parent_clip_id"] = "external_parent"
        self.assertTrue(list(validator.iter_errors(first_with_parent)))

        first_without_parent = json.loads(json.dumps(base))
        first_without_parent["clips"][0].pop("parent_clip_id")
        self.assertEqual(list(validator.iter_errors(first_without_parent)), [])

    def test_clip_contract_schema_enforces_root_and_later_parent_policy(self) -> None:
        schema = schema_check.load_json(ROOT / "schemas/clip-contract.schema.json")
        validator = schema_check.Draft202012Validator(schema)
        base = json.loads(
            (ROOT / "examples/sequence-airport-arrival/clip-01-contract.json").read_text(
                "utf-8"
            )
        )

        for mode in ("missing", "null"):
            with self.subTest(later_parent=mode):
                data = json.loads(json.dumps(base))
                data["sequence_index"] = 2
                if mode == "missing":
                    data.pop("parent_clip_id")
                else:
                    data["parent_clip_id"] = None
                self.assertTrue(list(validator.iter_errors(data)))

        first_without_parent = json.loads(json.dumps(base))
        first_without_parent.pop("parent_clip_id")
        self.assertEqual(list(validator.iter_errors(first_without_parent)), [])

        later_with_parent = json.loads(json.dumps(base))
        later_with_parent["sequence_index"] = 2
        later_with_parent["parent_clip_id"] = "clip_01"
        self.assertEqual(list(validator.iter_errors(later_with_parent)), [])

    def test_schemas_accept_finite_integral_json_numbers_only(self) -> None:
        project_schema = schema_check.load_json(ROOT / "schemas/project-state.schema.json")
        project_validator = schema_check.Draft202012Validator(project_schema)
        project = json.loads(
            (ROOT / "examples/sequence-observed-deviation/project-state-before.json").read_text(
                "utf-8"
            )
        )
        for index, clip in enumerate(project["clips"], start=1):
            clip["sequence_index"] = float(index)
        self.assertEqual(list(project_validator.iter_errors(project)), [])

        contract_schema = schema_check.load_json(ROOT / "schemas/clip-contract.schema.json")
        contract_validator = schema_check.Draft202012Validator(contract_schema)
        contract = json.loads(
            (ROOT / "examples/sequence-airport-arrival/clip-01-contract.json").read_text(
                "utf-8"
            )
        )
        contract["sequence_index"] = 1.0
        self.assertEqual(list(contract_validator.iter_errors(contract)), [])

        for invalid in (1.5, True, False):
            with self.subTest(sequence_index=invalid):
                invalid_project = json.loads(json.dumps(project))
                invalid_project["clips"][1]["sequence_index"] = invalid
                self.assertTrue(list(project_validator.iter_errors(invalid_project)))

                invalid_contract = json.loads(json.dumps(contract))
                invalid_contract["sequence_index"] = invalid
                self.assertTrue(list(contract_validator.iter_errors(invalid_contract)))

    def test_raw_decimal_tokens_keep_exact_integer_semantics(self) -> None:
        for token, should_pass in (("1.0", True), ("1.0000000000000001", False)):
            with self.subTest(token=token), tempfile.TemporaryDirectory() as tmp:
                repo = self._copy_repo(tmp)
                target = repo / "examples/sequence-observed-deviation/project-state-before.json"
                raw = target.read_text("utf-8")
                original = '"sequence_index": 1'
                self.assertIn(original, raw)
                target.write_text(raw.replace(original, f'"sequence_index": {token}', 1), "utf-8")
                errors = schema_check.check(repo)
                if should_pass:
                    self.assertEqual(errors, [])
                else:
                    self.assertTrue(
                        any("sequence_index" in error and "integer" in error for error in errors),
                        errors,
                    )

    def test_duplicate_parent_key_is_rejected_before_schema_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            target = repo / "examples/sequence-observed-deviation/project-state-before.json"
            raw = target.read_text("utf-8")
            original = '"parent_clip_id": null'
            replacement = '"parent_clip_id": null, "parent_clip_id": "laundered"'
            self.assertIn(original, raw)
            target.write_text(raw.replace(original, replacement, 1), "utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(
                any("duplicate object key: 'parent_clip_id'" in error for error in errors),
                errors,
            )

    def test_project_schema_rejects_invalid_status_and_terminal_endpoint_shapes(self) -> None:
        schema = schema_check.load_json(ROOT / "schemas/project-state.schema.json")
        validator = schema_check.Draft202012Validator(schema)
        base = json.loads(
            (ROOT / "examples/sequence-observed-deviation/project-state-before.json").read_text(
                "utf-8"
            )
        )

        for invalid_status in ([], {}, "Accepted", " accepted", "accepted "):
            with self.subTest(status=invalid_status):
                data = json.loads(json.dumps(base))
                data["clips"][2]["status"] = invalid_status
                self.assertTrue(list(validator.iter_errors(data)))

        for endpoint in (None, {}):
            with self.subTest(accepted_endpoint=endpoint):
                data = json.loads(json.dumps(base))
                terminal = data["clips"][2]
                terminal["status"] = "accepted"
                terminal["observed_end_state"] = endpoint
                self.assertTrue(list(validator.iter_errors(data)))

        rejected_with_object = json.loads(json.dumps(base))
        rejected_with_object["clips"][2]["status"] = "rejected"
        rejected_with_object["clips"][2]["observed_end_state"] = {}
        self.assertTrue(list(validator.iter_errors(rejected_with_object)))

    def test_clip_contract_schema_enforces_local_status_and_endpoint_invariants(self) -> None:
        schema = schema_check.load_json(ROOT / "schemas/clip-contract.schema.json")
        self.assertIn("Structural and record-local", schema["description"])
        validator = schema_check.Draft202012Validator(schema)
        base = json.loads(
            (ROOT / "examples/sequence-airport-arrival/clip-01-contract.json").read_text(
                "utf-8"
            )
        )

        accepted_without_endpoint = json.loads(json.dumps(base))
        accepted_without_endpoint["status"] = "accepted"
        self.assertTrue(list(validator.iter_errors(accepted_without_endpoint)))

        accepted_with_endpoint = json.loads(json.dumps(accepted_without_endpoint))
        accepted_with_endpoint["observed_end_state"] = {"pose": "held"}
        self.assertEqual(list(validator.iter_errors(accepted_with_endpoint)), [])

        rejected_without_endpoint = json.loads(json.dumps(base))
        rejected_without_endpoint["status"] = "rejected"
        self.assertTrue(list(validator.iter_errors(rejected_without_endpoint)))

        rejected_with_null_endpoint = json.loads(json.dumps(rejected_without_endpoint))
        rejected_with_null_endpoint["observed_end_state"] = None
        self.assertEqual(list(validator.iter_errors(rejected_with_null_endpoint)), [])

        for invalid_status in ([], {}, "Accepted", "accepted "):
            with self.subTest(status=invalid_status):
                data = json.loads(json.dumps(base))
                data["status"] = invalid_status
                self.assertTrue(list(validator.iter_errors(data)))

        later_with_unknown_parent = json.loads(json.dumps(base))
        later_with_unknown_parent["sequence_index"] = 2
        later_with_unknown_parent["parent_clip_id"] = "not_visible_to_single_record_schema"
        self.assertEqual(list(validator.iter_errors(later_with_unknown_parent)), [])

    def test_schemas_bound_clip_and_parent_identifiers(self) -> None:
        huge_id = "x" * 257
        project_schema = schema_check.load_json(ROOT / "schemas/project-state.schema.json")
        project_validator = schema_check.Draft202012Validator(project_schema)
        project = json.loads(
            (ROOT / "examples/sequence-observed-deviation/project-state-before.json").read_text(
                "utf-8"
            )
        )
        project["clips"][2]["clip_id"] = huge_id
        self.assertTrue(list(project_validator.iter_errors(project)))

        contract_schema = schema_check.load_json(ROOT / "schemas/clip-contract.schema.json")
        contract_validator = schema_check.Draft202012Validator(contract_schema)
        contract = json.loads(
            (ROOT / "examples/sequence-airport-arrival/clip-02-continuation-contract.json").read_text(
                "utf-8"
            )
        )
        contract["parent_clip_id"] = huge_id
        self.assertTrue(list(contract_validator.iter_errors(contract)))

    def test_schema_checker_bounds_huge_identifier_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            target = repo / "examples/sequence-observed-deviation/project-state-before.json"
            data = json.loads(target.read_text("utf-8"))
            data["clips"][2]["clip_id"] = "x" * 1_000_000
            target.write_text(json.dumps(data), encoding="utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(errors)
            self.assertLessEqual(max(map(len, errors)), 1024)
            self.assertLessEqual(sum(map(len, errors)), 16384)

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

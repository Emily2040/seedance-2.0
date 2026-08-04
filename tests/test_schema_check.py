"""The shipped schemas must actually accept the shipped examples.

Other checkers re-declare required fields in Python, so a schema and its
examples can drift apart while both still pass. These tests pin the executable
relationship: every schema is declared with at least one instance, the
instances validate, and the checker fails rather than passing quietly when
something breaks.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def _probe_errors(self, schema: object, instance: object) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "schemas").mkdir()
            (repo / "examples").mkdir()
            (repo / "validation").mkdir()
            (repo / "schemas/probe.schema.json").write_text(
                json.dumps(schema), encoding="utf-8"
            )
            (repo / "examples/probe.json").write_text(
                json.dumps(instance), encoding="utf-8"
            )
            (repo / "validation/schema-instances.json").write_text(
                json.dumps(
                    {"instances": {"probe.schema.json": ["examples/probe.json"]}}
                ),
                encoding="utf-8",
            )
            return schema_check.check(repo)

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

    def test_project_schema_strictly_bounds_take_history_items(self) -> None:
        schema = schema_check.load_json(ROOT / "schemas/project-state.schema.json")
        validator = schema_check.Draft202012Validator(schema)
        base = json.loads(
            (ROOT / "examples/sequence-airport-arrival/project-state.json").read_text(
                "utf-8"
            )
        )

        for verdict in ("accept", "accept_with_deviation", "repair", "reject"):
            with self.subTest(valid_verdict=verdict):
                data = json.loads(json.dumps(base))
                data["take_history"][0]["verdict"] = verdict
                self.assertEqual(list(validator.iter_errors(data)), [])

        attacks = {
            "missing verdict": lambda item: item.pop("verdict"),
            "array verdict": lambda item: item.update(verdict=[]),
            "unknown verdict": lambda item: item.update(verdict="Accept"),
            "blank take id": lambda item: item.update(take_id="   "),
            "overlong take id": lambda item: item.update(take_id="x" * 257),
            "blank clip id": lambda item: item.update(clip_id=""),
            "overlong clip id": lambda item: item.update(clip_id="x" * 257),
            "non-string evidence": lambda item: item.update(evidence=[]),
            "overlong evidence": lambda item: item.update(evidence="x" * 4097),
            "unexpected field": lambda item: item.update(authority="claimed"),
        }
        for label, mutate in attacks.items():
            with self.subTest(attack=label):
                data = json.loads(json.dumps(base))
                mutate(data["take_history"][0])
                self.assertTrue(list(validator.iter_errors(data)), label)

        too_many = json.loads(json.dumps(base))
        too_many["take_history"] = [
            {
                "take_id": f"take_{index}",
                "clip_id": "clip_01",
                "verdict": "accept",
            }
            for index in range(4097)
        ]
        self.assertTrue(list(validator.iter_errors(too_many)))

    def test_authority_identifiers_and_take_review_shape_are_strictly_bounded(self) -> None:
        project_schema = schema_check.load_json(ROOT / "schemas/project-state.schema.json")
        project_validator = schema_check.Draft202012Validator(project_schema)
        project = json.loads(
            (ROOT / "examples/sequence-airport-arrival/project-state.json").read_text(
                "utf-8"
            )
        )
        for invalid in ("   ", "x" * 257):
            with self.subTest(document="project-state", invalid_length=len(invalid)):
                data = json.loads(json.dumps(project))
                data["project_id"] = invalid
                self.assertTrue(list(project_validator.iter_errors(data)))

        review_schema = schema_check.load_json(ROOT / "schemas/take-review.schema.json")
        review_validator = schema_check.Draft202012Validator(review_schema)
        review = json.loads(
            (ROOT / "examples/sequence-airport-arrival/clip-01-take-review.json").read_text(
                "utf-8"
            )
        )
        self.assertEqual(list(review_validator.iter_errors(review)), [])

        for field in ("project_id", "clip_id", "take_id"):
            for invalid in ("   ", "x" * 257):
                with self.subTest(field=field, invalid_length=len(invalid)):
                    data = json.loads(json.dumps(review))
                    data[field] = invalid
                    self.assertTrue(list(review_validator.iter_errors(data)))

        attacks = {
            "observed start array": lambda item: item.update(observed_start_state=[]),
            "observed end null": lambda item: item.update(observed_end_state=None),
            "completed beats string": lambda item: item.update(completed_beats="claimed"),
            "completed beats item": lambda item: item.update(completed_beats=[1]),
            "incomplete beats object": lambda item: item.update(incomplete_beats={}),
            "unexpected beats null": lambda item: item.update(
                unexpected_completed_beats=None
            ),
            "continuity breaks string": lambda item: item.update(
                continuity_breaks="none"
            ),
            "accepted deviations object": lambda item: item.update(
                accepted_deviations={}
            ),
            "confidence array": lambda item: item.update(observation_confidence=[]),
            "unknown confidence": lambda item: item.update(
                observation_confidence="extreme"
            ),
            "uncertainties string": lambda item: item.update(uncertainties="none"),
            "uncertainty item": lambda item: item.update(uncertainties=[1]),
            "confirmation string": lambda item: item.update(
                requires_user_confirmation="yes"
            ),
            "unexpected field": lambda item: item.update(authority="claimed"),
        }
        for label, mutate in attacks.items():
            with self.subTest(attack=label):
                data = json.loads(json.dumps(review))
                mutate(data)
                self.assertTrue(list(review_validator.iter_errors(data)), label)

        rejected_with_deviation = json.loads(json.dumps(review))
        rejected_with_deviation["verdict"] = "reject"
        rejected_with_deviation["accepted_deviations"] = ["claimed exception"]
        self.assertTrue(list(review_validator.iter_errors(rejected_with_deviation)))

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
        accepted_without_endpoint.pop("observed_end_state", None)
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

    def test_text_waiver_arrays_reject_non_string_items(self) -> None:
        cases = (
            (
                "examples/standalone-clip/project-state.json",
                "allowed_changes",
                True,
            ),
            (
                "examples/standalone-clip/project-state.json",
                "continuity_breaks",
                True,
            ),
            (
                "examples/standalone-clip/project-state.json",
                "accepted_deviations",
                True,
            ),
            (
                "examples/sequence-airport-arrival/clip-01-contract.json",
                "allowed_changes",
                False,
            ),
            (
                "examples/sequence-airport-arrival/clip-01-take-review.json",
                "continuity_breaks",
                False,
            ),
            (
                "examples/sequence-airport-arrival/clip-01-take-review.json",
                "accepted_deviations",
                False,
            ),
        )
        for relative, field, nested_clip in cases:
            with self.subTest(instance=relative, field=field), tempfile.TemporaryDirectory() as tmp:
                repo = self._copy_repo(tmp)
                target = repo / relative
                data = json.loads(target.read_text("utf-8"))
                owner = data["clips"][0] if nested_clip else data
                owner[field] = [{"not": "text"}]
                target.write_text(json.dumps(data), encoding="utf-8")

                errors = schema_check.check(repo)

                self.assertTrue(any(field in error for error in errors), errors)

    def test_schema_requiring_a_field_no_example_has_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            target = repo / "schemas/take-review.schema.json"
            schema = json.loads(target.read_text("utf-8"))
            schema["required"] = list(schema["required"]) + ["field_no_example_has"]
            target.write_text(json.dumps(schema), encoding="utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(any("field_no_example_has" in e for e in errors), errors)

    def test_boolean_schema_and_non_object_instance_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            schema_name = "accept-anything.schema.json"
            instance_name = "examples/standalone-clip/array-instance.json"
            (repo / "schemas" / schema_name).write_text("true", encoding="utf-8")
            (repo / instance_name).write_text("[1, 2, 3]", encoding="utf-8")

            manifest_path = repo / "validation/schema-instances.json"
            manifest = json.loads(manifest_path.read_text("utf-8"))
            manifest["instances"][schema_name] = [instance_name]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            self.assertEqual(schema_check.check(repo), [])

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

    def test_external_schema_references_fail_without_opening_the_network(self) -> None:
        for keyword in ("$ref", "$dynamicRef"):
            with self.subTest(keyword=keyword), tempfile.TemporaryDirectory() as tmp:
                repo = self._copy_repo(tmp)
                target = repo / "schemas/take-review.schema.json"
                schema = json.loads(target.read_text("utf-8"))
                schema.setdefault("properties", {})["network_probe"] = {
                    keyword: "https://example.invalid/remote.schema.json"
                }
                target.write_text(json.dumps(schema), encoding="utf-8")
                with mock.patch("urllib.request.urlopen") as urlopen:
                    errors = schema_check.check(repo)
                self.assertTrue(
                    any("external or unresolved $ref/$dynamicRef" in e for e in errors),
                    errors,
                )
                urlopen.assert_not_called()

    def test_local_fragment_references_remain_supported(self) -> None:
        self.assertEqual(
            schema_check.external_reference_paths(
                {"$defs": {"value": {"type": "string"}}, "$ref": "#/$defs/value"}
            ),
            [],
        )

    def test_opaque_local_target_must_pass_the_metaschema_before_activation(self) -> None:
        schema = {
            "type": "object",
            "properties": {"optional": {"$ref": "#/opaque/target"}},
            "opaque": {"target": {"type": 7}},
        }
        self.assertEqual(schema_check.external_reference_paths(schema), [])
        invalid_targets = schema_check.invalid_local_reference_targets(schema)
        self.assertEqual(len(invalid_targets), 1)
        self.assertIn("$/properties/optional/$ref", invalid_targets[0])
        self.assertIn("$/opaque/target", invalid_targets[0])

        # The root metaschema ignores the unknown `opaque` container, and the
        # fixture can omit the optional branch. The static reference audit must
        # still reject the invalid runtime target.
        schema_check.Draft202012Validator.check_schema(schema)
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors({})), [])
        with self.assertRaises(Exception):
            list(validator.iter_errors({"optional": "activated"}))
        errors = self._probe_errors(schema, {})
        self.assertTrue(any("local $ref/$dynamicRef target" in error for error in errors))

    def test_opaque_local_target_rejects_primitives_and_lists_but_accepts_booleans(self) -> None:
        for target in (7, ["not", "a", "schema"]):
            schema = {
                "type": "object",
                "properties": {"optional": {"$ref": "#/opaque/target"}},
                "opaque": {"target": target},
            }
            with self.subTest(target=target):
                findings = schema_check.invalid_local_reference_targets(schema)
                self.assertEqual(len(findings), 1)
                self.assertIn("not an object or boolean schema", findings[0])
                self.assertTrue(
                    any(
                        "local $ref/$dynamicRef target" in error
                        for error in self._probe_errors(schema, {})
                    )
                )

        for target in (True, False):
            schema = {
                "type": "object",
                "properties": {"optional": {"$ref": "#/opaque/target"}},
                "opaque": {"target": target},
            }
            with self.subTest(target=target):
                self.assertEqual(schema_check.invalid_local_reference_targets(schema), [])
                self.assertEqual(self._probe_errors(schema, {}), [])
                validator = schema_check.Draft202012Validator(
                    schema,
                    registry=schema_check.Registry(
                        retrieve=schema_check.refuse_schema_retrieval
                    ),
                )
                activated_errors = list(
                    validator.iter_errors({"optional": "activated"})
                )
                self.assertEqual(len(activated_errors), 0 if target else 1)

    def test_opaque_invalid_target_is_checked_within_a_nested_id_resource(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "optional": {
                    "$id": "https://nested.invalid/resource",
                    "$ref": "#/opaque/target",
                    "opaque": {"target": {"type": 7}},
                }
            },
        }
        invalid_targets = schema_check.invalid_local_reference_targets(schema)
        self.assertEqual(len(invalid_targets), 1)
        self.assertIn("$/properties/optional/opaque/target", invalid_targets[0])
        self.assertTrue(
            any(
                "local $ref/$dynamicRef target" in error
                for error in self._probe_errors(schema, {})
            )
        )

    def test_every_nonlocal_reference_form_is_rejected_in_schema_positions(self) -> None:
        references = (
            "https://example.invalid/schema",
            "http://example.invalid/schema",
            "//example.invalid/schema",
            "?alternate-schema",
            "file:///tmp/schema.json",
            "urn:example:remote-schema",
            "relative/schema.json",
        )
        for keyword in ("$ref", "$dynamicRef"):
            for reference in references:
                with self.subTest(keyword=keyword, reference=reference):
                    self.assertEqual(
                        schema_check.external_reference_paths(
                            {"properties": {"value": {keyword: reference}}}
                        ),
                        [f"$/properties/value/{keyword}"],
                    )

    def test_invalid_reference_types_are_left_to_the_schema_metaschema(self) -> None:
        from jsonschema.exceptions import SchemaError

        for keyword in ("$ref", "$dynamicRef"):
            for invalid in (7, [], {}):
                schema = {"properties": {"value": {keyword: invalid}}}
                with self.subTest(keyword=keyword, invalid=invalid):
                    self.assertEqual(schema_check.external_reference_paths(schema), [])
                    with self.assertRaises(SchemaError):
                        schema_check.Draft202012Validator.check_schema(schema)

    def test_empty_reference_is_same_resource_and_recursive(self) -> None:
        schema = {
            "type": "object",
            "properties": {"child": {"$ref": ""}},
        }
        self.assertEqual(schema_check.external_reference_paths(schema), [])
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors({"child": {"child": {}}})), [])

    def test_local_dynamic_anchor_recursion_remains_supported(self) -> None:
        schema = {
            "$dynamicAnchor": "node",
            "type": "object",
            "properties": {"child": {"$dynamicRef": "#node"}},
        }
        self.assertEqual(schema_check.external_reference_paths(schema), [])
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors({"child": {"child": {}}})), [])

    def test_local_plain_anchor_resolution_remains_supported(self) -> None:
        schema = {
            "$defs": {
                "value": {
                    "$anchor": "value",
                    "type": "integer",
                }
            },
            "$ref": "#value",
        }
        self.assertEqual(schema_check.external_reference_paths(schema), [])
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors(1)), [])

    def test_unresolved_optional_local_pointer_fails_static_audit(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "optional": {"$ref": "#/$defs/missing"},
            },
            "$defs": {},
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/properties/optional/$ref"],
        )
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors({})), [])
        with self.assertRaises(Exception) as unresolved:
            list(validator.iter_errors({"optional": 1}))
        self.assertIn("missing", str(unresolved.exception))

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "schemas").mkdir()
            (repo / "examples").mkdir()
            (repo / "validation").mkdir()
            (repo / "schemas/probe.schema.json").write_text(
                json.dumps(schema), encoding="utf-8"
            )
            (repo / "examples/omitted.json").write_text("{}", encoding="utf-8")
            (repo / "validation/schema-instances.json").write_text(
                json.dumps(
                    {
                        "instances": {
                            "probe.schema.json": ["examples/omitted.json"]
                        }
                    }
                ),
                encoding="utf-8",
            )
            errors = schema_check.check(repo)
        self.assertTrue(
            any("external or unresolved $ref/$dynamicRef" in error for error in errors),
            errors,
        )

    def test_unresolved_plain_anchor_is_a_finding(self) -> None:
        schema = {
            "type": "object",
            "properties": {"optional": {"$dynamicRef": "#missing"}},
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/properties/optional/$dynamicRef"],
        )

    def test_reference_shaped_literal_data_is_not_treated_as_a_subschema(self) -> None:
        literal = {
            "$ref": "https://example.invalid/literal-ref",
            "$dynamicRef": "relative-literal-ref",
        }
        schema = {
            "const": literal,
            "enum": [literal],
            "default": literal,
            "examples": [literal],
        }
        self.assertEqual(schema_check.external_reference_paths(schema), [])
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors(literal)), [])

    def test_local_pointer_into_opaque_data_makes_that_target_an_active_schema(self) -> None:
        schema = {
            "$ref": "#/%63onst",
            "const": {"$ref": "https://example.invalid/active-via-pointer"},
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/const/$ref"],
        )

    def test_nested_id_pointer_uses_the_embedded_resource_root(self) -> None:
        """An optional property must not hide retrieval behind a nested resource scope."""
        schema = {
            "type": "object",
            "properties": {
                "optional": {
                    "$id": "https://example.invalid/embedded",
                    "$ref": "#/const",
                    "const": {"$ref": "https://example.invalid/remote"},
                }
            },
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/properties/optional/const/$ref"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "schemas").mkdir()
            (repo / "examples").mkdir()
            (repo / "validation").mkdir()
            (repo / "schemas/probe.schema.json").write_text(
                json.dumps(schema), encoding="utf-8"
            )
            # The property is deliberately absent: fixture execution alone
            # would never resolve the external reference.
            (repo / "examples/omitted.json").write_text("{}", encoding="utf-8")
            (repo / "validation/schema-instances.json").write_text(
                json.dumps(
                    {
                        "instances": {
                            "probe.schema.json": ["examples/omitted.json"]
                        }
                    }
                ),
                encoding="utf-8",
            )
            errors = schema_check.check(repo)
        self.assertTrue(
            any("external or unresolved $ref/$dynamicRef" in error for error in errors),
            errors,
        )

    def test_outer_pointer_into_nested_resource_keeps_nested_scope(self) -> None:
        """Crossing a nested `$id` must rebase refs in an activated opaque value."""
        schema = {
            "$id": "https://outer.invalid/root",
            "type": "object",
            "properties": {
                "optional": {"$ref": "#/$defs/embedded/const"}
            },
            "$defs": {
                "embedded": {
                    "$id": "https://embedded.invalid/res",
                    "const": {
                        "$ref": "#/const/hidden",
                        "hidden": {"$ref": "https://remote.invalid/x"},
                    },
                }
            },
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/$defs/embedded/const/hidden/$ref"],
        )

        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors({})), [])
        with self.assertRaises(Exception) as retrieval:
            list(validator.iter_errors({"optional": 1}))
        self.assertIn("remote.invalid", str(retrieval.exception))

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "schemas").mkdir()
            (repo / "examples").mkdir()
            (repo / "validation").mkdir()
            (repo / "schemas/probe.schema.json").write_text(
                json.dumps(schema), encoding="utf-8"
            )
            (repo / "examples/omitted.json").write_text("{}", encoding="utf-8")
            (repo / "validation/schema-instances.json").write_text(
                json.dumps(
                    {
                        "instances": {
                            "probe.schema.json": ["examples/omitted.json"]
                        }
                    }
                ),
                encoding="utf-8",
            )
            errors = schema_check.check(repo)
        self.assertTrue(
            any("external or unresolved $ref/$dynamicRef" in error for error in errors),
            errors,
        )

    def test_literal_id_on_pointer_path_is_not_a_resource_boundary(self) -> None:
        """A `$id` inside opaque instance data must not rebase an active schema."""
        schema = {
            "$id": "https://outer.invalid/root",
            "$ref": "#/const/target",
            "const": {
                "$id": "https://literal.invalid/not-a-schema-resource",
                "target": {"$ref": "#/default/hidden"},
            },
            "default": {
                "hidden": {"$ref": "https://remote.invalid/inverse"}
            },
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/default/hidden/$ref"],
        )

    def test_registry_retrieval_callback_always_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "external schema retrieval is disabled"):
            schema_check.refuse_schema_retrieval("https://example.invalid/schema")


class DependencyTests(unittest.TestCase):
    def test_missing_dependency_fails_rather_than_skipping(self) -> None:
        """A silent skip would let CI report success while validating nothing."""
        environment = {
            "PYTHONPATH": "",
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        # CPython on Windows needs the OS root to initialize its secure random
        # provider; removing it tests process startup rather than dependency
        # handling (Fatal _Py_HashRandomization_Init, exit 1).
        if os.name == "nt":
            environment["PATH"] = str(Path(sys.executable).parent)
            for name in ("SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP"):
                if name in os.environ:
                    environment[name] = os.environ[name]
        result = subprocess.run(
            [
                sys.executable,
                "-S",
                str(ROOT / "scripts/schema_check.py"),
                str(ROOT),
            ],
            capture_output=True,
            text=True,
            env=environment,
        )
        expected = (
            "schema check requires jsonschema.\n"
            "  python -m pip install --require-hashes --requirement "
            "requirements-validation.lock\n"
            "The lock covers CPython 3.11-3.13 on Linux, macOS, and Windows. "
            "On a platform\n"
            "it does not cover, install jsonschema>=4.26 by any means you trust "
            "and re-run;\n"
            "this checker needs the library, not that particular lock file.\n"
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, expected)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PROJECT_STATE = (
    ROOT / "examples" / "sequence-observed-deviation" / "project-state-before.json"
)

sys.path.insert(0, str(ROOT / "scripts"))

import continuity_chain_check  # noqa: E402
import project_state_check  # noqa: E402
import schema_check  # noqa: E402
from lineage_contract import (  # noqa: E402
    MAX_ERROR_CHARS,
    MAX_IDENTIFIER_CHARS,
    MAX_LINEAGE_ERRORS,
    MAX_TOTAL_DIAGNOSTIC_CHARS,
    analyze_lineage,
    json_integer,
)
from strict_json import MAX_JSON_BYTES  # noqa: E402


class LineageConsumerParityTests(unittest.TestCase):
    @staticmethod
    def clip(data: dict, clip_id: str) -> dict:
        return next(clip for clip in data["clips"] if clip["clip_id"] == clip_id)

    def validate_data(self, data: object) -> tuple[list[str], list[str]]:
        return self.validate_raw(json.dumps(data))

    def validate_raw(self, raw: str) -> tuple[list[str], list[str]]:
        with tempfile.TemporaryDirectory(prefix="lineage-parity-") as temp_dir:
            fixture = Path(temp_dir) / "project-state.json"
            fixture.write_text(raw, encoding="utf-8")
            project_errors = project_state_check.validate_project(fixture, ROOT)
            continuity_errors, _ = continuity_chain_check.validate(fixture, ROOT)
            return project_errors, continuity_errors

    def mutate_and_validate(self, mutate) -> tuple[list[str], list[str]]:
        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        mutate(data)
        return self.validate_data(data)

    def assert_both_reject(self, mutate, expected: str) -> None:
        project_errors, continuity_errors = self.mutate_and_validate(mutate)
        for consumer, errors in (
            ("project_state_check", project_errors),
            ("continuity_chain_check", continuity_errors),
        ):
            self.assertTrue(
                any(expected in error for error in errors),
                f"{consumer} did not report {expected!r}: {errors}",
            )

    def test_duplicate_ids_are_rejected_by_both_consumers(self) -> None:
        self.assert_both_reject(
            lambda data: self.clip(data, "clip_03").update(clip_id="clip_02"),
            "duplicate clip_id clip_02",
        )

    def test_self_parent_is_rejected_by_both_consumers(self) -> None:
        self.assert_both_reject(
            lambda data: self.clip(data, "clip_02").update(parent_clip_id="clip_02"),
            "clip clip_02 cannot parent itself",
        )

    def test_equal_parent_child_order_is_rejected_by_both_consumers(self) -> None:
        self.assert_both_reject(
            lambda data: self.clip(data, "clip_02").update(sequence_index=1),
            "clip clip_02 sequence_index 1 must be greater than parent clip_01 sequence_index 1",
        )

    def test_reversed_parent_child_order_is_rejected_by_both_consumers(self) -> None:
        def reverse_order(data: dict) -> None:
            self.clip(data, "clip_01")["sequence_index"] = 2
            self.clip(data, "clip_02")["sequence_index"] = 1

        self.assert_both_reject(
            reverse_order,
            "clip clip_02 sequence_index 1 must be greater than parent clip_01 sequence_index 2",
        )

    def test_three_node_cycle_is_rejected_by_both_consumers(self) -> None:
        self.assert_both_reject(
            lambda data: self.clip(data, "clip_01").update(parent_clip_id="clip_03"),
            "clip lineage cycle:",
        )

    def test_integral_float_order_is_compared_by_both_consumers(self) -> None:
        def reverse_integral_float_order(data: dict) -> None:
            self.clip(data, "clip_01")["sequence_index"] = 2.0
            self.clip(data, "clip_02")["sequence_index"] = 1.0

        self.assert_both_reject(
            reverse_integral_float_order,
            "clip clip_02 sequence_index 1.0 must be greater than parent clip_01 sequence_index 2.0",
        )

    def test_later_missing_or_null_parent_is_rejected_by_both_consumers(self) -> None:
        def remove_parent(data: dict) -> None:
            self.clip(data, "clip_02").pop("parent_clip_id")

        self.assert_both_reject(
            remove_parent,
            "later clip clip_02 sequence_index 2 must declare a non-empty parent_clip_id",
        )
        self.assert_both_reject(
            lambda data: self.clip(data, "clip_02").update(parent_clip_id=None),
            "later clip clip_02 sequence_index 2 must declare a non-empty parent_clip_id",
        )

    def test_malformed_document_shapes_return_shared_diagnostics(self) -> None:
        malformed = (
            ("{", "invalid JSON:"),
            ("[]", "project state must be an object"),
            ('{"clips":[{"sequence_index":NaN}]}', "non-finite number is not permitted: NaN"),
            (
                '{"clips":' + "[" * 1100 + "0" + "]" * 1100 + "}",
                "maximum JSON nesting depth",
            ),
        )
        for raw, expected in malformed:
            with self.subTest(raw=raw):
                project_errors, continuity_errors = self.validate_raw(raw)
                self.assertEqual(project_errors, continuity_errors)
                self.assertEqual(len(project_errors), 1)
                self.assertIn(expected, project_errors[0])

        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        data["clips"] = None
        project_errors, continuity_errors = self.validate_data(data)
        expected = "clips must be an array of clip objects"
        self.assertTrue(any(expected in error for error in project_errors), project_errors)
        self.assertTrue(any(expected in error for error in continuity_errors), continuity_errors)

    def test_duplicate_json_keys_are_rejected_before_laundering(self) -> None:
        for raw in ('{"clips":[],"clips":null}', self.raw_with_duplicate_parent_key()):
            with self.subTest(raw_length=len(raw)):
                project_errors, continuity_errors = self.validate_raw(raw)
                self.assertEqual(project_errors, continuity_errors)
                self.assertEqual(len(project_errors), 1)
                self.assertIn("duplicate object key:", project_errors[0])

    def raw_with_duplicate_parent_key(self) -> str:
        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        raw = json.dumps(data)
        original = '"parent_clip_id": null'
        replacement = '"parent_clip_id": null, "parent_clip_id": "laundered"'
        self.assertIn(original, raw)
        return raw.replace(original, replacement, 1)

    def test_raw_fractional_token_does_not_round_into_an_integer(self) -> None:
        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        raw = json.dumps(data)
        original = '"sequence_index": 1'
        replacement = '"sequence_index": 1.0000000000000001'
        self.assertIn(original, raw)
        project_errors, continuity_errors = self.validate_raw(
            raw.replace(original, replacement, 1)
        )
        expected = "clip clip_01 sequence_index must be a JSON integer >= 1"
        self.assertTrue(any(expected in error for error in project_errors), project_errors)
        self.assertTrue(any(expected in error for error in continuity_errors), continuity_errors)

    def test_array_or_object_status_is_bounded_and_rejected_by_both_consumers(self) -> None:
        for invalid in ([], {}):
            with self.subTest(status=invalid):
                self.assert_both_reject(
                    lambda data, value=invalid: self.clip(data, "clip_01").update(
                        status=value
                    ),
                    f"clip clip_01 status <{type(invalid).__name__}> is invalid",
                )

    def test_terminal_wrong_case_or_whitespace_status_is_rejected(self) -> None:
        for invalid in ("Accepted", " accepted", "accepted ", "ACCEPTED"):
            with self.subTest(status=invalid):
                self.assert_both_reject(
                    lambda data, value=invalid: self.clip(data, "clip_03").update(
                        status=value
                    ),
                    f"clip clip_03 status {invalid!r} is invalid",
                )

    def test_terminal_accepted_clip_requires_a_nonempty_observed_endpoint(self) -> None:
        for invalid_endpoint in (None, {}):
            with self.subTest(observed_end_state=invalid_endpoint):
                self.assert_both_reject(
                    lambda data, endpoint=invalid_endpoint: self.clip(data, "clip_03").update(
                        status="accepted",
                        observed_end_state=endpoint,
                    ),
                    "accepted clip clip_03 observed_end_state must be a non-empty object",
                )

    def test_rejected_clip_requires_an_explicit_null_observed_endpoint(self) -> None:
        def remove_endpoint(data: dict) -> None:
            clip = self.clip(data, "clip_03")
            clip["status"] = "rejected"
            clip.pop("observed_end_state")

        self.assert_both_reject(
            remove_endpoint,
            "rejected clip clip_03 observed_end_state must be null",
        )
        self.assert_both_reject(
            lambda data: self.clip(data, "clip_03").update(
                status="rejected",
                observed_end_state={},
            ),
            "rejected clip clip_03 observed_end_state must be null",
        )

    def test_first_root_may_be_absent_or_null(self) -> None:
        for root_value in ("absent", None):
            with self.subTest(root_value=root_value):
                def set_root(data: dict, value=root_value) -> None:
                    root = self.clip(data, "clip_01")
                    if value == "absent":
                        root.pop("parent_clip_id")
                    else:
                        root["parent_clip_id"] = value

                project_errors, continuity_errors = self.mutate_and_validate(set_root)
                self.assertEqual(project_errors, [])
                self.assertEqual(continuity_errors, [])

    def test_ordered_integral_float_sequence_indexes_are_valid(self) -> None:
        def use_integral_floats(data: dict) -> None:
            for index, clip in enumerate(data["clips"], start=1):
                clip["sequence_index"] = float(index)

        project_errors, continuity_errors = self.mutate_and_validate(use_integral_floats)
        self.assertEqual(project_errors, [])
        self.assertEqual(continuity_errors, [])

    def test_fractional_and_boolean_sequence_indexes_are_rejected(self) -> None:
        for invalid in (1.5, True, False):
            with self.subTest(sequence_index=invalid):
                self.assert_both_reject(
                    lambda data, value=invalid: self.clip(data, "clip_02").update(
                        sequence_index=value
                    ),
                    "clip clip_02 sequence_index must be a JSON integer >= 1",
                )

    def test_json_integer_accepts_only_finite_integral_non_boolean_numbers(self) -> None:
        self.assertEqual(json_integer(2), 2)
        self.assertEqual(json_integer(2.0), 2.0)
        for invalid in (2.5, True, False, float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=invalid):
                self.assertIsNone(json_integer(invalid))

    def test_lineage_diagnostics_are_bounded(self) -> None:
        analysis = analyze_lineage([{} for _ in range(200)], "fixture.json")
        self.assertEqual(len(analysis.errors), MAX_LINEAGE_ERRORS)
        self.assertEqual(
            analysis.errors[-1],
            "fixture.json: additional lineage errors omitted",
        )
        self.assertLessEqual(max(map(len, analysis.errors)), MAX_ERROR_CHARS)
        self.assertLessEqual(
            sum(map(len, analysis.errors)),
            MAX_TOTAL_DIAGNOSTIC_CHARS,
        )

    def test_long_lineage_does_not_depend_on_python_recursion_depth(self) -> None:
        clips = []
        for index in range(1, 1501):
            clip = {
                "clip_id": f"clip_{index:04d}",
                "sequence_index": index,
                "status": "planned",
            }
            clip["parent_clip_id"] = None if index == 1 else f"clip_{index - 1:04d}"
            clips.append(clip)
        self.assertEqual(analyze_lineage(clips, "fixture.json").errors, [])

    def test_fifty_thousand_node_cycle_has_a_bounded_summary(self) -> None:
        count = 50_000
        clips = []
        for index in range(count):
            clips.append(
                {
                    "clip_id": f"clip_{index}",
                    "parent_clip_id": f"clip_{index - 1}" if index else f"clip_{count - 1}",
                    "sequence_index": index + 1,
                    "status": "planned",
                }
            )
        errors = analyze_lineage(clips, "fixture.json").errors
        cycle_errors = [error for error in errors if "clip lineage cycle:" in error]
        self.assertEqual(len(cycle_errors), 1, errors)
        self.assertIn("50000 nodes", cycle_errors[0])
        self.assertLessEqual(max(map(len, errors)), MAX_ERROR_CHARS)
        self.assertLessEqual(sum(map(len, errors)), MAX_TOTAL_DIAGNOSTIC_CHARS)

        consumer_count = 10_000
        consumer_clips = []
        for index in range(consumer_count):
            consumer_clips.append(
                {
                    "clip_id": f"clip_{index}",
                    "parent_clip_id": (
                        f"clip_{index - 1}"
                        if index
                        else f"clip_{consumer_count - 1}"
                    ),
                    "sequence_index": index + 1,
                    "status": "planned",
                }
            )
        consumer_data = {"clips": consumer_clips}
        self.assertLess(
            len(json.dumps(consumer_data).encode("utf-8")),
            MAX_JSON_BYTES,
        )
        project_errors, continuity_errors = self.validate_data(consumer_data)
        for consumer_errors in (project_errors, continuity_errors):
            self.assertTrue(
                any("clip lineage cycle:" in error for error in consumer_errors),
                consumer_errors,
            )
            self.assertLessEqual(max(map(len, consumer_errors)), MAX_ERROR_CHARS)
            self.assertLessEqual(
                sum(map(len, consumer_errors)),
                MAX_TOTAL_DIAGNOSTIC_CHARS,
            )

    def test_one_million_character_identifier_cannot_expand_diagnostics(self) -> None:
        huge_id = "x" * 1_000_000
        analysis = analyze_lineage(
            [
                {
                    "clip_id": huge_id,
                    "parent_clip_id": None,
                    "sequence_index": 2,
                    "status": "planned",
                }
            ],
            "fixture.json",
        )
        self.assertTrue(analysis.errors)
        self.assertTrue(any(str(MAX_IDENTIFIER_CHARS) in error for error in analysis.errors))
        self.assertNotIn(huge_id, "\n".join(analysis.errors))
        self.assertLessEqual(max(map(len, analysis.errors)), MAX_ERROR_CHARS)
        self.assertLessEqual(
            sum(map(len, analysis.errors)),
            MAX_TOTAL_DIAGNOSTIC_CHARS,
        )

        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        self.clip(data, "clip_03")["clip_id"] = huge_id
        project_errors, continuity_errors = self.validate_data(data)
        for consumer_errors in (project_errors, continuity_errors):
            self.assertTrue(consumer_errors)
            self.assertNotIn(huge_id, "\n".join(consumer_errors))
            self.assertLessEqual(max(map(len, consumer_errors)), MAX_ERROR_CHARS)
            self.assertLessEqual(
                sum(map(len, consumer_errors)),
                MAX_TOTAL_DIAGNOSTIC_CHARS,
            )

    def test_identifier_diagnostics_escape_control_characters(self) -> None:
        hostile_id = ("\x1b[31m\n" * 40) + "tail"
        errors = analyze_lineage(
            [
                {
                    "clip_id": hostile_id,
                    "sequence_index": 2,
                    "status": "planned",
                }
            ],
            "fixture.json",
        ).errors
        rendered = "\n".join(errors)
        self.assertNotIn("\x1b", rendered)
        self.assertNotIn("[31m\n", rendered)
        self.assertIn("\\x1b", rendered)

    @unittest.skipUnless(schema_check.Draft202012Validator is not None, "jsonschema not installed")
    def test_schema_is_explicitly_structural_for_graph_wide_invariants(self) -> None:
        schema = schema_check.load_json(ROOT / "schemas/project-state.schema.json")
        self.assertIn("Structural and record-local", schema["description"])
        validator = schema_check.Draft202012Validator(schema)
        attacks = {
            "duplicate clip id": lambda data: self.clip(data, "clip_03").update(
                clip_id="clip_02"
            ),
            "missing parent": lambda data: self.clip(data, "clip_02").update(
                parent_clip_id="ghost"
            ),
            "self parent": lambda data: self.clip(data, "clip_02").update(
                parent_clip_id="clip_02"
            ),
            "two node cycle": lambda data: (
                self.clip(data, "clip_02").update(parent_clip_id="clip_03"),
                self.clip(data, "clip_03").update(parent_clip_id="clip_02"),
            ),
            "unusable parent status": lambda data: self.clip(data, "clip_01").update(
                status="generated"
            ),
        }
        for label, mutate in attacks.items():
            with self.subTest(attack=label):
                data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
                mutate(data)
                self.assertEqual(list(validator.iter_errors(data)), [], label)
                project_errors, continuity_errors = self.validate_data(data)
                self.assertTrue(project_errors, label)
                self.assertTrue(continuity_errors, label)


if __name__ == "__main__":
    unittest.main()

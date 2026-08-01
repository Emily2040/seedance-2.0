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
from lineage_contract import MAX_LINEAGE_ERRORS, analyze_lineage, json_integer  # noqa: E402


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
            ('{"clips":[{"sequence_index":NaN}]}', "non-JSON numeric constant 'NaN'"),
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


if __name__ == "__main__":
    unittest.main()

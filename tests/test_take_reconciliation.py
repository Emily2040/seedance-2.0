from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PROJECT_FIXTURE = ROOT / "examples" / "sequence-airport-arrival" / "project-state.json"
REVIEW_FIXTURE = ROOT / "examples" / "sequence-airport-arrival" / "clip-01-take-review.json"

sys.path.insert(0, str(ROOT / "scripts"))

import continuity_chain_check  # noqa: E402
import lineage_contract  # noqa: E402
import project_state_check  # noqa: E402
from strict_json import (  # noqa: E402
    MAX_DIAGNOSTIC_CHARS,
    MAX_DIAGNOSTIC_COUNT,
    MAX_DIAGNOSTIC_TOTAL_CHARS,
)


class TakeReconciliationTests(unittest.TestCase):
    def project(self) -> dict:
        return json.loads(PROJECT_FIXTURE.read_text(encoding="utf-8"))

    def review(self) -> dict:
        return json.loads(REVIEW_FIXTURE.read_text(encoding="utf-8"))

    def validate(
        self,
        project: dict,
        reviews: list[dict] | None = None,
        *,
        project_name: str = "project-state.json",
    ) -> tuple[list[str], list[str]]:
        with tempfile.TemporaryDirectory(prefix="take-authority-") as temp_dir:
            directory = Path(temp_dir)
            project_path = directory / project_name
            project_path.write_text(json.dumps(project), encoding="utf-8")
            for index, review in enumerate(reviews or []):
                (directory / f"clip-{index}-take-review.json").write_text(
                    json.dumps(review), encoding="utf-8"
                )
            index = lineage_contract.build_take_review_indexes([project_path])[
                project_path.resolve().parent
            ]
            project_errors = project_state_check.validate_project(
                project_path,
                directory,
                index,
            )
            continuity_errors, _ = continuity_chain_check.validate(
                project_path,
                directory,
                index,
            )
            return project_errors, continuity_errors

    def assert_both_contain(
        self,
        project: dict,
        reviews: list[dict] | None,
        expected: str,
        *,
        project_name: str = "project-state.json",
    ) -> None:
        project_errors, continuity_errors = self.validate(
            project,
            reviews,
            project_name=project_name,
        )
        for consumer, errors in (
            ("project_state_check", project_errors),
            ("continuity_chain_check", continuity_errors),
        ):
            self.assertTrue(
                any(expected in error for error in errors),
                f"{consumer} did not report {expected!r}: {errors}",
            )

    def test_every_post_review_status_requires_current_history_and_review(self) -> None:
        endpoint = self.project()["clips"][0]["observed_end_state"]
        for status in ("accepted", "accepted_with_deviation", "repair", "rejected"):
            with self.subTest(status=status):
                project = self.project()
                project["clips"][0]["status"] = status
                project["clips"][0]["observed_end_state"] = (
                    None if status == "rejected" else copy.deepcopy(endpoint)
                )
                project["take_history"] = []
                self.assert_both_contain(
                    project,
                    [],
                    f"clip clip_01 status {status} requires a current take_history entry",
                )

    def test_malformed_history_verdict_types_fail_cleanly_in_both_consumers(self) -> None:
        for verdict in ([], {}, None, True, 1):
            with self.subTest(verdict=verdict):
                project = self.project()
                project["take_history"][-1]["verdict"] = verdict
                self.assert_both_contain(project, [self.review()], "has invalid verdict")

    def test_malformed_review_verdict_types_fail_cleanly_in_both_consumers(self) -> None:
        for verdict in ([], {}, None, True, 1):
            with self.subTest(verdict=verdict):
                review = self.review()
                review["verdict"] = verdict
                self.assert_both_contain(
                    self.project(),
                    [review],
                    "sibling take-review for take take_clip01_a has invalid verdict",
                )

    def test_project_state_cannot_witness_itself_as_a_take_review(self) -> None:
        for project_name in ("take-review.json", "project-state-take-review.json"):
            with self.subTest(project_name=project_name):
                project = self.project()
                review = self.review()
                for field, value in review.items():
                    project.setdefault(field, value)
                self.assert_both_contain(
                    project,
                    [],
                    "is missing its sibling take-review record",
                    project_name=project_name,
                )

    def test_hard_link_to_project_state_cannot_witness_as_review(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-hardlink-") as temp_dir:
            directory = Path(temp_dir)
            project = self.project()
            review = self.review()
            for field, value in review.items():
                project.setdefault(field, value)
            project_path = directory / "project-state.json"
            project_path.write_text(json.dumps(project), encoding="utf-8")
            try:
                (directory / "clip-0-take-review.json").hardlink_to(project_path)
            except OSError as exc:
                self.skipTest(f"hard links unavailable: {exc}")

            review_index = lineage_contract.build_take_review_indexes([project_path])[
                project_path.resolve().parent
            ]
            for errors in (
                project_state_check.validate_project(project_path, directory, review_index),
                continuity_chain_check.validate(project_path, directory, review_index)[0],
            ):
                self.assertTrue(
                    any("is missing its sibling take-review record" in error for error in errors),
                    errors,
                )

    def test_review_verdict_mismatch_is_rejected_by_both_consumers(self) -> None:
        review = self.review()
        review["verdict"] = "reject"
        review["accepted_deviations"] = []
        self.assert_both_contain(
            self.project(),
            [review],
            "does not match sibling take-review verdict reject",
        )

    def test_duplicate_current_reviews_are_not_authoritative(self) -> None:
        review = self.review()
        self.assert_both_contain(
            self.project(),
            [review, copy.deepcopy(review)],
            "has multiple sibling take-review records",
        )

    def test_only_current_history_entry_requires_a_sibling_review(self) -> None:
        project = self.project()
        project["take_history"].insert(
            0,
            {
                "take_id": "take_clip01_rejected",
                "clip_id": "clip_01",
                "verdict": "reject",
            },
        )
        project_errors, continuity_errors = self.validate(project, [self.review()])
        self.assertEqual(project_errors, [])
        self.assertEqual(continuity_errors, [])

    def test_incomplete_review_record_cannot_be_authoritative(self) -> None:
        review = {
            "project_id": "seq_airport_arrival",
            "clip_id": "clip_01",
            "take_id": "take_clip01_a",
            "source_status": "reviewed",
            "verdict": "accept_with_deviation",
        }
        self.assert_both_contain(
            self.project(),
            [review],
            "is not authoritative; missing fields:",
        )

    def test_review_index_is_loaded_once_and_shared_by_both_consumers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-index-once-") as temp_dir:
            directory = Path(temp_dir)
            project_paths: list[Path] = []
            for suffix in ("a", "b"):
                project = self.project()
                review = self.review()
                project["project_id"] = f"project_{suffix}"
                review["project_id"] = f"project_{suffix}"
                project_path = directory / f"project-state-{suffix}.json"
                review_path = directory / f"clip-{suffix}-take-review.json"
                project_path.write_text(json.dumps(project), encoding="utf-8")
                review_path.write_text(json.dumps(review), encoding="utf-8")
                project_paths.append(project_path)

            original_load = lineage_contract.load_strict_json
            loaded_review_paths: list[Path] = []

            def counted_load(path: Path):
                if path.name.endswith("-take-review.json"):
                    loaded_review_paths.append(path)
                return original_load(path)

            with mock.patch.object(
                lineage_contract,
                "load_strict_json",
                side_effect=counted_load,
            ):
                indexes = lineage_contract.build_take_review_indexes(project_paths)
                for project_path in project_paths:
                    index = indexes[project_path.resolve().parent]
                    self.assertEqual(
                        project_state_check.validate_project(project_path, directory, index),
                        [],
                    )
                    self.assertEqual(
                        continuity_chain_check.validate(project_path, directory, index),
                        ([], []),
                    )

            self.assertCountEqual(
                [path.name for path in loaded_review_paths],
                ["clip-a-take-review.json", "clip-b-take-review.json"],
            )

    def test_history_attack_diagnostics_are_bounded(self) -> None:
        project = self.project()
        project["take_history"] = [
            {"clip_id": [], "take_id": {}, "verdict": ["x" * 10000]}
            for _ in range(lineage_contract.MAX_TAKE_HISTORY_ITEMS + 100)
        ]
        project_errors, continuity_errors = self.validate(project, [])
        for errors in (project_errors, continuity_errors):
            self.assertTrue(errors)
            self.assertLessEqual(len(errors), MAX_DIAGNOSTIC_COUNT)
            self.assertLessEqual(max(map(len, errors)), MAX_DIAGNOSTIC_CHARS)
            self.assertLessEqual(sum(map(len, errors)), MAX_DIAGNOSTIC_TOTAL_CHARS)
            self.assertTrue(
                any("diagnostics omitted" in error for error in errors),
                errors,
            )

    def test_review_file_scan_cap_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-index-cap-") as temp_dir:
            directory = Path(temp_dir)
            project = self.project()
            project_path = directory / "project-state.json"
            project_path.write_text(json.dumps(project), encoding="utf-8")
            for index in range(3):
                review = self.review()
                review["take_id"] = f"take_{index}"
                (directory / f"clip-{index}-take-review.json").write_text(
                    json.dumps(review), encoding="utf-8"
                )
            with mock.patch.object(
                lineage_contract,
                "MAX_TAKE_REVIEW_FILES_PER_DIRECTORY",
                2,
            ):
                review_index = lineage_contract.build_take_review_indexes([project_path])[
                    project_path.resolve().parent
                ]
            self.assertTrue(
                any("file count exceeds 2" in error for error in review_index.diagnostics),
                review_index.diagnostics,
            )


if __name__ == "__main__":
    unittest.main()

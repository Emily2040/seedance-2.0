from __future__ import annotations

import contextlib
import copy
import io
import json
import os
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
    MAX_JSON_BYTES,
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

    def test_in_progress_retry_can_retain_prior_reviewed_take_history(self) -> None:
        for status in ("generated", "reviewed"):
            with self.subTest(status=status):
                project = self.project()
                project["clips"] = project["clips"][:1]
                project["scenes"][0]["assigned_clip_ids"] = ["clip_01"]
                project["beats"] = [
                    beat
                    for beat in project["beats"]
                    if beat.get("assigned_clip_id") == "clip_01"
                ]
                project["current_clip_id"] = "clip_01"
                project["clips"][0]["status"] = status
                project_errors, continuity_errors = self.validate(project, [])
                self.assertEqual(project_errors, [])
                self.assertEqual(continuity_errors, [])

    def test_project_state_main_never_rereads_oversized_indexed_review(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-main-size-cap-") as temp_dir:
            root = Path(temp_dir)
            directory = root / "examples" / "sequence"
            directory.mkdir(parents=True)
            project_path = directory / "project-state.json"
            review_path = directory / "clip-0-take-review.json"
            project_path.write_text(json.dumps(self.project()), encoding="utf-8")
            review_path.write_bytes(b"x" * 65)

            loaded_paths: list[Path] = []
            original_load = project_state_check.load_json

            def tracked_generic_load(path: Path) -> object:
                loaded_paths.append(path)
                return original_load(path)

            with mock.patch.object(
                lineage_contract, "MAX_TAKE_REVIEW_BYTES", 64
            ), mock.patch.object(
                project_state_check, "load_json", side_effect=tracked_generic_load
            ), mock.patch.object(
                sys, "argv", ["project_state_check.py", str(root), "--strict"]
            ), contextlib.redirect_stdout(io.StringIO()):
                result = project_state_check.main()

            self.assertEqual(result, 1)
            self.assertNotIn(review_path, loaded_paths)

    def test_review_like_backup_name_still_uses_generic_json_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-backup-name-") as temp_dir:
            root = Path(temp_dir)
            directory = root / "examples" / "sequence"
            directory.mkdir(parents=True)
            (directory / "project-state.json").write_text(
                json.dumps(self.project()), encoding="utf-8"
            )
            (directory / "clip-0-take-review.json").write_text(
                json.dumps(self.review()), encoding="utf-8"
            )
            backup = directory / "clip-take-review-backup.json"
            backup.write_text("{", encoding="utf-8")
            output = io.StringIO()

            with mock.patch.object(
                sys, "argv", ["project_state_check.py", str(root), "--strict"]
            ), contextlib.redirect_stdout(output):
                result = project_state_check.main()

            self.assertEqual(result, 1)
            self.assertIn(
                "clip-take-review-backup.json: invalid JSON", output.getvalue()
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
                    "invalid verdict",
                )

    def test_every_take_review_field_is_validated_before_authority_indexing(self) -> None:
        attacks = (
            ("observed_start_state", [], "observed_start_state must be an object"),
            ("observed_end_state", None, "observed_end_state must be an object"),
            ("completed_beats", "claimed", "completed_beats must be an array of strings"),
            ("completed_beats", [1], "completed_beats[0] must be a string"),
            ("incomplete_beats", {}, "incomplete_beats must be an array of strings"),
            (
                "unexpected_completed_beats",
                None,
                "unexpected_completed_beats must be an array of strings",
            ),
            ("continuity_breaks", "none", "continuity_breaks must be an array"),
            ("accepted_deviations", {}, "accepted_deviations must be an array"),
            (
                "observation_confidence",
                [],
                "invalid observation_confidence",
            ),
            (
                "observation_confidence",
                "extreme",
                "invalid observation_confidence",
            ),
            ("uncertainties", "none", "uncertainties must be an array of strings"),
            ("uncertainties", [1], "uncertainties[0] must be a string"),
            (
                "requires_user_confirmation",
                "yes",
                "requires_user_confirmation must be a boolean",
            ),
        )
        for field, value, expected in attacks:
            with self.subTest(field=field, value=value):
                review = self.review()
                review[field] = value
                self.assert_both_contain(self.project(), [review], expected)

        review = self.review()
        review["authority"] = "claimed"
        self.assert_both_contain(self.project(), [review], "unexpected fields: 'authority'")

        review = self.review()
        review["verdict"] = "reject"
        review["accepted_deviations"] = ["claimed exception"]
        self.assert_both_contain(
            self.project(),
            [review],
            "rejected take must not accept deviations",
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

    def test_symbolic_link_cannot_become_review_authority(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-symlink-") as temp_dir:
            directory = Path(temp_dir)
            project_path = directory / "project-state.json"
            target_path = directory / "review-target.json"
            review_path = directory / "clip-0-take-review.json"
            project_path.write_text(json.dumps(self.project()), encoding="utf-8")
            target_path.write_text(json.dumps(self.review()), encoding="utf-8")
            try:
                review_path.symlink_to(target_path.name)
            except OSError as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")

            with mock.patch.object(
                lineage_contract.os,
                "open",
                side_effect=AssertionError("symlink candidate must not be opened"),
            ):
                review_index = lineage_contract.build_take_review_indexes([project_path])[
                    project_path.resolve().parent
                ]

            self.assertTrue(
                any(
                    "must be a regular non-link file" in error
                    for error in review_index.diagnostics
                ),
                review_index.diagnostics,
            )
            for errors in (
                project_state_check.validate_project(project_path, directory, review_index),
                continuity_chain_check.validate(project_path, directory, review_index)[0],
            ):
                self.assertTrue(
                    any("is missing its sibling take-review record" in error for error in errors),
                    errors,
                )

    def test_windows_reparse_attribute_is_never_regular_authority(self) -> None:
        info = mock.Mock(
            st_mode=lineage_contract.stat.S_IFREG,
            st_file_attributes=0x0400,
        )
        with mock.patch.object(
            lineage_contract.stat,
            "FILE_ATTRIBUTE_REPARSE_POINT",
            0x0400,
            create=True,
        ):
            self.assertFalse(lineage_contract._is_regular_non_link(info))
            info.st_file_attributes = 0
            self.assertTrue(lineage_contract._is_regular_non_link(info))

    def test_safe_open_requests_no_follow_when_platform_supports_it(self) -> None:
        no_follow = getattr(os, "O_NOFOLLOW", 0)
        if not no_follow:
            self.skipTest("O_NOFOLLOW is unavailable")
        with tempfile.TemporaryDirectory(prefix="take-no-follow-") as temp_dir:
            review_path = Path(temp_dir) / "clip-0-take-review.json"
            review_path.write_text(json.dumps(self.review()), encoding="utf-8")
            original_open = lineage_contract.os.open

            def checked_open(path: Path, flags: int) -> int:
                self.assertTrue(flags & no_follow)
                return original_open(path, flags)

            with mock.patch.object(
                lineage_contract.os,
                "open",
                side_effect=checked_open,
            ):
                status, payload, captured_bytes = (
                    lineage_contract._load_checked_take_review(review_path, set())
                )

            self.assertEqual(status, "loaded")
            self.assertEqual(payload, self.review())
            self.assertEqual(captured_bytes, review_path.stat().st_size)

    def test_non_regular_review_candidate_is_rejected_without_opening(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("named pipes are unavailable")
        with tempfile.TemporaryDirectory(prefix="take-fifo-") as temp_dir:
            directory = Path(temp_dir)
            project_path = directory / "project-state.json"
            review_path = directory / "clip-0-take-review.json"
            project_path.write_text(json.dumps(self.project()), encoding="utf-8")
            os.mkfifo(review_path)

            with mock.patch.object(
                lineage_contract.os,
                "open",
                side_effect=AssertionError("non-regular candidate must not be opened"),
            ):
                review_index = lineage_contract.build_take_review_indexes([project_path])[
                    project_path.resolve().parent
                ]

            self.assertTrue(
                any(
                    "must be a regular non-link file" in error
                    for error in review_index.diagnostics
                ),
                review_index.diagnostics,
            )

    def test_oversized_schema_valid_review_is_rejected_before_reading(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-size-cap-") as temp_dir:
            directory = Path(temp_dir)
            project_path = directory / "project-state.json"
            review_path = directory / "clip-0-take-review.json"
            project_path.write_text(json.dumps(self.project()), encoding="utf-8")
            review = self.review()
            review["continuity_breaks"] = ["x" * 2048]
            review_path.write_text(json.dumps(review), encoding="utf-8")

            with (
                mock.patch.object(lineage_contract, "MAX_TAKE_REVIEW_BYTES", 1024),
                mock.patch.object(
                    lineage_contract.os,
                    "read",
                    side_effect=AssertionError("oversized candidate must not be read"),
                ),
            ):
                review_index = lineage_contract.build_take_review_indexes([project_path])[
                    project_path.resolve().parent
                ]

            self.assertTrue(
                any(
                    "exceeds the 1024-byte take-review limit" in error
                    for error in review_index.diagnostics
                ),
                review_index.diagnostics,
            )
            for errors in (
                project_state_check.validate_project(project_path, directory, review_index),
                continuity_chain_check.validate(project_path, directory, review_index)[0],
            ):
                self.assertTrue(
                    any("exceeds the 1024-byte take-review limit" in error for error in errors),
                    errors,
                )

    def test_review_snapshot_must_match_across_two_bounded_captures(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-rewrite-") as temp_dir:
            directory = Path(temp_dir)
            review_path = directory / "clip-0-take-review.json"
            review_path.write_text(json.dumps(self.review()), encoding="utf-8")
            original = review_path.read_bytes()
            changed = b"[" + original[1:]

            with mock.patch.object(
                lineage_contract,
                "_read_bounded_take_review_bytes",
                side_effect=(original, changed),
            ) as capture:
                status, detail, captured_bytes = lineage_contract._load_checked_take_review(
                    review_path,
                    set(),
                )

            self.assertEqual(status, "error")
            self.assertEqual(detail, "changed contents while being read")
            self.assertEqual(captured_bytes, len(original))
            self.assertEqual(capture.call_count, 2)
            self.assertEqual(
                capture.call_args_list[0].args,
                capture.call_args_list[1].args,
            )

    def test_path_swap_to_project_state_cannot_witness_as_review(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-path-swap-") as temp_dir:
            directory = Path(temp_dir)
            project = self.project()
            review = self.review()
            for field, value in review.items():
                project.setdefault(field, value)
            project_path = directory / "project-state.json"
            review_path = directory / "clip-0-take-review.json"
            project_path.write_text(json.dumps(project), encoding="utf-8")
            review_path.write_text("{}", encoding="utf-8")

            original_load = lineage_contract._load_checked_take_review
            swapped = False

            def swap_then_load(path: Path, excluded_file_ids: set[tuple[int, int]]):
                nonlocal swapped
                if path == review_path and not swapped:
                    path.unlink()
                    path.hardlink_to(project_path)
                    swapped = True
                return original_load(path, excluded_file_ids)

            try:
                with mock.patch.object(
                    lineage_contract,
                    "_load_checked_take_review",
                    side_effect=swap_then_load,
                ):
                    review_index = lineage_contract.build_take_review_indexes([project_path])[
                        project_path.resolve().parent
                    ]
            except OSError as exc:
                self.skipTest(f"hard links unavailable: {exc}")

            self.assertTrue(swapped)
            self.assertTrue(review_path.samefile(project_path))
            for errors in (
                project_state_check.validate_project(project_path, directory, review_index),
                continuity_chain_check.validate(project_path, directory, review_index)[0],
            ):
                self.assertTrue(
                    any("is missing its sibling take-review record" in error for error in errors),
                    errors,
                )

    def test_oversized_project_alias_is_excluded_before_review_size_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-large-project-") as temp_dir:
            directory = Path(temp_dir)
            project = self.project()
            for field, value in self.review().items():
                project.setdefault(field, value)
            project_path = directory / "take-review.json"
            project_path.write_text(json.dumps(project), encoding="utf-8")

            with mock.patch.object(lineage_contract, "MAX_TAKE_REVIEW_BYTES", 1):
                review_index = lineage_contract.build_take_review_indexes([project_path])[
                    project_path.resolve().parent
                ]

            self.assertEqual(review_index.diagnostics, ())
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
            "missing fields:",
        )

    def test_take_review_identifiers_are_bounded_before_authority_indexing(self) -> None:
        for field in ("project_id", "clip_id", "take_id"):
            for invalid in ("   ", "x" * 257):
                with self.subTest(field=field, invalid_length=len(invalid)):
                    review = self.review()
                    review[field] = invalid
                    self.assert_both_contain(
                        self.project(),
                        [review],
                        f"{field} must be a non-empty string of at most 256 characters",
                    )

    def test_project_identifier_is_bounded_in_both_consumers(self) -> None:
        for invalid in ("   ", "x" * 257):
            with self.subTest(invalid_length=len(invalid)):
                project = self.project()
                project["project_id"] = invalid
                self.assert_both_contain(
                    project,
                    [self.review()],
                    "project_id must be a non-empty string of at most 256 characters",
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
                for clip in project["clips"]:
                    for snapshot in clip.get(
                        "contract_authoring_state_snapshots", []
                    ):
                        snapshot["project_id"] = project["project_id"]
                project_path = directory / f"project-state-{suffix}.json"
                review_path = directory / f"clip-{suffix}-take-review.json"
                project_path.write_text(json.dumps(project), encoding="utf-8")
                review_path.write_text(json.dumps(review), encoding="utf-8")
                project_paths.append(project_path)

            original_load = lineage_contract._load_checked_take_review
            loaded_review_paths: list[Path] = []

            def counted_load(path: Path, excluded_file_ids: set[tuple[int, int]]):
                loaded_review_paths.append(path)
                return original_load(path, excluded_file_ids)

            with mock.patch.object(
                lineage_contract,
                "_load_checked_take_review",
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
            {"clip_id": [], "take_id": {}, "verdict": ["x" * 256]}
            for _ in range(lineage_contract.MAX_TAKE_HISTORY_ITEMS + 100)
        ]
        self.assertLess(len(json.dumps(project).encode("utf-8")), MAX_JSON_BYTES)
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

    def test_review_directory_byte_budget_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="take-byte-cap-") as temp_dir:
            directory = Path(temp_dir)
            project_path = directory / "project-state.json"
            project_path.write_text(json.dumps(self.project()), encoding="utf-8")
            encoded_review = json.dumps(self.review())
            for index in range(2):
                (directory / f"clip-{index}-take-review.json").write_text(
                    encoded_review,
                    encoding="utf-8",
                )

            with mock.patch.object(
                lineage_contract,
                "MAX_TAKE_REVIEW_BYTES_PER_DIRECTORY",
                len(encoded_review.encode("utf-8")) + 1,
            ):
                review_index = lineage_contract.build_take_review_indexes([project_path])[
                    project_path.resolve().parent
                ]

            self.assertTrue(
                any(
                    "take-review bytes exceed" in error
                    and "directory limit" in error
                    for error in review_index.diagnostics
                ),
                review_index.diagnostics,
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PROJECT_STATE = ROOT / "examples" / "sequence-observed-deviation" / "project-state-before.json"
REVIEWED_PROJECT_STATE = ROOT / "examples" / "sequence-airport-arrival" / "project-state.json"
REVIEWED_TAKE = ROOT / "examples" / "sequence-airport-arrival" / "clip-01-take-review.json"


class ProjectStateTests(unittest.TestCase):
    @staticmethod
    def review_for(project_id: str, clip_id: str, take_id: str, verdict: str) -> dict:
        return {
            "project_id": project_id,
            "clip_id": clip_id,
            "take_id": take_id,
            "source_status": "reviewed",
            "verdict": verdict,
            "observed_start_state": {},
            "observed_end_state": {},
            "completed_beats": [],
            "incomplete_beats": [],
            "unexpected_completed_beats": [],
            "continuity_breaks": [],
            "accepted_deviations": [],
            "observation_confidence": "high",
            "uncertainties": [],
            "requires_user_confirmation": False,
        }

    def reviews_for_history(self, data: dict) -> list[dict]:
        return [
            self.review_for(
                data["project_id"],
                entry["clip_id"],
                entry["take_id"],
                entry["verdict"],
            )
            for entry in data["take_history"]
        ]

    def run_mutated_project(
        self,
        mutate,
        review_builder=None,
    ) -> subprocess.CompletedProcess[str]:
        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        mutate(data)
        reviews = review_builder(data) if review_builder is not None else []
        with tempfile.TemporaryDirectory(prefix="lineage-test-") as temp_dir:
            repo = Path(temp_dir)
            fixture = repo / "examples" / "lineage" / "project-state.json"
            fixture.parent.mkdir(parents=True)
            fixture.write_text(json.dumps(data), encoding="utf-8")
            for index, review in enumerate(reviews):
                (fixture.parent / f"clip-{index}-take-review.json").write_text(
                    json.dumps(review), encoding="utf-8"
                )
            return subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "project_state_check.py"), str(repo), "--strict"],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

    def run_mutated_reviewed_project(self, project_mutate, review_mutate) -> subprocess.CompletedProcess[str]:
        project = json.loads(REVIEWED_PROJECT_STATE.read_text(encoding="utf-8"))
        review = json.loads(REVIEWED_TAKE.read_text(encoding="utf-8"))
        project_mutate(project)
        review_mutate(review)
        with tempfile.TemporaryDirectory(prefix="take-reconcile-test-") as temp_dir:
            repo = Path(temp_dir)
            fixture_dir = repo / "examples" / "sequence"
            fixture_dir.mkdir(parents=True)
            (fixture_dir / "project-state.json").write_text(
                json.dumps(project), encoding="utf-8"
            )
            (fixture_dir / "clip-01-take-review.json").write_text(
                json.dumps(review), encoding="utf-8"
            )
            return subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "project_state_check.py"), str(repo), "--strict"],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

    @staticmethod
    def clip(data: dict, clip_id: str) -> dict:
        return next(clip for clip in data["clips"] if clip["clip_id"] == clip_id)

    def test_project_state_examples_validate(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/project_state_check.py", "--strict"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_later_standalone_contract_requires_parent(self) -> None:
        contract_path = (
            ROOT
            / "examples"
            / "sequence-airport-arrival"
            / "clip-02-continuation-contract.json"
        )
        for mode in ("missing", "null"):
            with self.subTest(parent=mode), tempfile.TemporaryDirectory(
                prefix="contract-parent-test-"
            ) as temp_dir:
                repo = Path(temp_dir)
                fixture_dir = repo / "examples" / "sequence"
                fixture_dir.mkdir(parents=True)
                (fixture_dir / "project-state.json").write_text(
                    BASE_PROJECT_STATE.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                if mode == "missing":
                    contract.pop("parent_clip_id")
                else:
                    contract["parent_clip_id"] = None
                (fixture_dir / "clip-02-continuation-contract.json").write_text(
                    json.dumps(contract), encoding="utf-8"
                )
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "project_state_check.py"),
                        str(repo),
                        "--strict",
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(
                    "later clip sequence_index 2 must declare a non-empty parent_clip_id",
                    result.stdout,
                )

    def test_first_standalone_contract_must_not_declare_parent(self) -> None:
        contract_path = (
            ROOT / "examples" / "sequence-airport-arrival" / "clip-01-contract.json"
        )
        with tempfile.TemporaryDirectory(prefix="contract-root-test-") as temp_dir:
            repo = Path(temp_dir)
            fixture_dir = repo / "examples" / "sequence"
            fixture_dir.mkdir(parents=True)
            (fixture_dir / "project-state.json").write_text(
                BASE_PROJECT_STATE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["parent_clip_id"] = "external_parent"
            (fixture_dir / "clip-01-contract.json").write_text(
                json.dumps(contract), encoding="utf-8"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "project_state_check.py"),
                    str(repo),
                    "--strict",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "first clip sequence_index 1 must not declare parent_clip_id",
            result.stdout,
        )

    def test_standalone_terminal_contract_enforces_observed_endpoint(self) -> None:
        contract_path = (
            ROOT / "examples" / "sequence-airport-arrival" / "clip-01-contract.json"
        )
        cases = (
            ("accepted", "missing", None, "accepted clip clip_01 observed_end_state must be a non-empty object"),
            ("accepted", "empty", {}, "accepted clip clip_01 observed_end_state must be a non-empty object"),
            ("accepted_with_deviation", "null", None, "accepted clip clip_01 observed_end_state must be a non-empty object"),
            ("rejected", "missing", None, "rejected clip clip_01 observed_end_state must be null"),
            ("rejected", "object", {"summary": "must not publish"}, "rejected clip clip_01 observed_end_state must be null"),
        )
        for status, endpoint_mode, endpoint, expected in cases:
            with (
                self.subTest(status=status, endpoint=endpoint_mode),
                tempfile.TemporaryDirectory(prefix="contract-endpoint-test-") as temp_dir,
            ):
                repo = Path(temp_dir)
                fixture_dir = repo / "examples" / "sequence"
                fixture_dir.mkdir(parents=True)
                (fixture_dir / "project-state.json").write_text(
                    BASE_PROJECT_STATE.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                contract["status"] = status
                if endpoint_mode == "missing":
                    contract.pop("observed_end_state", None)
                else:
                    contract["observed_end_state"] = endpoint
                (fixture_dir / "clip-01-contract.json").write_text(
                    json.dumps(contract),
                    encoding="utf-8",
                )

                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "project_state_check.py"),
                        str(repo),
                        "--strict",
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                )

                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(expected, result.stdout)

    def test_standalone_terminal_contract_accepts_status_consistent_endpoint(self) -> None:
        contract_path = (
            ROOT / "examples" / "sequence-airport-arrival" / "clip-01-contract.json"
        )
        for status, endpoint in (
            ("accepted", {"summary": "usable endpoint"}),
            ("accepted_with_deviation", {"summary": "usable endpoint"}),
            ("rejected", None),
        ):
            with (
                self.subTest(status=status),
                tempfile.TemporaryDirectory(prefix="contract-endpoint-control-") as temp_dir,
            ):
                repo = Path(temp_dir)
                fixture_dir = repo / "examples" / "sequence"
                fixture_dir.mkdir(parents=True)
                (fixture_dir / "project-state.json").write_text(
                    BASE_PROJECT_STATE.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                contract["status"] = status
                contract["observed_end_state"] = endpoint
                # This fixture exercises the legacy/default standalone endpoint
                # contract. Lane-bound strict contracts require their matching
                # project snapshot, prompt, and protected provenance ledger.
                for field in (
                    "directors_read_lane",
                    "authoring_state",
                    "authoring_state_provenance",
                ):
                    contract.pop(field, None)
                (fixture_dir / "clip-01-contract.json").write_text(
                    json.dumps(contract),
                    encoding="utf-8",
                )

                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "project_state_check.py"),
                        str(repo),
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                )

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejected_canonical_take_cannot_leave_clip_accepted(self) -> None:
        def reject_history(project: dict) -> None:
            project["take_history"][-1]["verdict"] = "reject"

        result = self.run_mutated_reviewed_project(
            reject_history,
            lambda review: review.update(verdict="reject", accepted_deviations=[]),
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "latest take take_clip01_a for clip clip_01 has verdict reject; "
            "clip status must be rejected, not accepted_with_deviation",
            result.stdout,
        )

    def test_sibling_review_verdict_must_match_take_history(self) -> None:
        result = self.run_mutated_reviewed_project(
            lambda project: None,
            lambda review: review.update(verdict="reject", accepted_deviations=[]),
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "take_history verdict accept_with_deviation for take take_clip01_a "
            "does not match sibling take-review verdict reject",
            result.stdout,
        )

    def test_latest_take_history_entry_requires_its_review_record(self) -> None:
        project = json.loads(REVIEWED_PROJECT_STATE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="take-reconcile-test-") as temp_dir:
            repo = Path(temp_dir)
            fixture_dir = repo / "examples" / "sequence"
            fixture_dir.mkdir(parents=True)
            (fixture_dir / "project-state.json").write_text(
                json.dumps(project), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "project_state_check.py"), str(repo), "--strict"],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("latest take take_clip01_a for clip clip_01 is missing", result.stdout)

    def test_earlier_rejected_take_does_not_override_latest_accepted_take(self) -> None:
        def prepend_rejection(project: dict) -> None:
            project["take_history"].insert(
                0,
                {"take_id": "take_clip01_rejected", "clip_id": "clip_01", "verdict": "reject"},
            )

        result = self.run_mutated_reviewed_project(prepend_rejection, lambda review: None)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_self_parenting(self) -> None:
        result = self.run_mutated_project(
            lambda data: self.clip(data, "clip_02").update(parent_clip_id="clip_02")
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("clip clip_02 cannot parent itself", result.stdout)

    def test_rejects_declared_missing_parent_even_at_first_index(self) -> None:
        result = self.run_mutated_project(
            lambda data: self.clip(data, "clip_01").update(parent_clip_id="missing_clip")
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("clip clip_01 parent missing_clip is missing", result.stdout)

    def test_rejects_empty_parent_id_even_at_first_index(self) -> None:
        result = self.run_mutated_project(
            lambda data: self.clip(data, "clip_01").update(parent_clip_id="")
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("parent_clip_id must be null or a non-empty string", result.stdout)

    def test_rejects_whitespace_only_or_non_string_parent_ids(self) -> None:
        for invalid in ("   ", False, 0, []):
            with self.subTest(parent_clip_id=invalid):
                result = self.run_mutated_project(
                    lambda data, value=invalid: self.clip(data, "clip_01").update(
                        parent_clip_id=value
                    )
                )
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("parent_clip_id must be null or a non-empty string", result.stdout)

    def test_rejects_non_monotonic_parent_order(self) -> None:
        result = self.run_mutated_project(
            lambda data: self.clip(data, "clip_02").update(sequence_index=1)
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "clip clip_02 sequence_index 1 must be greater than parent clip_01 sequence_index 1",
            result.stdout,
        )

    def test_rejects_cycle_longer_than_two_nodes(self) -> None:
        result = self.run_mutated_project(
            lambda data: self.clip(data, "clip_01").update(parent_clip_id="clip_03")
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("clip lineage cycle:", result.stdout)

    def test_preserves_valid_provisional_planned_chain(self) -> None:
        result = self.run_mutated_project(lambda data: None)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_unusable_parent_even_for_a_planned_child(self) -> None:
        for status in ("generated", "reviewed", "repair", "rejected"):
            with self.subTest(parent_status=status):
                def make_parent_unusable(data: dict, parent_status: str = status) -> None:
                    parent = self.clip(data, "clip_01")
                    parent["status"] = parent_status
                    parent["observed_end_state"] = None
                    self.clip(data, "clip_02")["status"] = "planned"

                result = self.run_mutated_project(make_parent_unusable)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"status '{status}' is not usable", result.stdout)

    def test_ready_child_requires_an_accepted_parent(self) -> None:
        result = self.run_mutated_project(
            lambda data: self.clip(data, "clip_02").update(status="ready")
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("parent clip_01 status 'ready' is not usable", result.stdout)

    def test_rejects_accepted_parent_without_observed_end_state(self) -> None:
        for invalid_endpoint in (None, {}, [], "claimed endpoint", 1):
            with self.subTest(observed_end_state=invalid_endpoint):
                def remove_parent_endpoint(data: dict, endpoint=invalid_endpoint) -> None:
                    parent = self.clip(data, "clip_01")
                    parent["status"] = "accepted"
                    parent["observed_end_state"] = endpoint

                result = self.run_mutated_project(remove_parent_endpoint)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(
                    "parent clip_01 is accepted but missing a usable observed_end_state",
                    result.stdout,
                )

    def test_preserves_explicit_null_root(self) -> None:
        def keep_only_root(data: dict) -> None:
            root = self.clip(data, "clip_01")
            root["parent_clip_id"] = None
            data["clips"] = [root]
            data["beats"] = [
                beat for beat in data["beats"] if beat.get("assigned_clip_id") == "clip_01"
            ]
            data["scenes"][0]["assigned_clip_ids"] = ["clip_01"]
            data["current_clip_id"] = "clip_01"

        result = self.run_mutated_project(keep_only_root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_preserves_valid_accepted_chain_with_planned_leaf(self) -> None:
        def accept_predecessors(data: dict) -> None:
            data["take_history"] = []
            for clip_id in ("clip_01", "clip_02"):
                clip = self.clip(data, clip_id)
                clip["status"] = "accepted"
                clip["observed_end_state"] = copy.deepcopy(clip["planned_end_state"])
                data["take_history"].append(
                    {
                        "take_id": f"take_{clip_id}_accepted",
                        "clip_id": clip_id,
                        "verdict": "accept",
                    }
                )

        result = self.run_mutated_project(
            accept_predecessors,
            self.reviews_for_history,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_preserves_rejected_leaf_with_accepted_parent(self) -> None:
        def reject_leaf(data: dict) -> None:
            root = self.clip(data, "clip_01")
            root["status"] = "accepted"
            root["observed_end_state"] = copy.deepcopy(root["planned_end_state"])
            leaf = self.clip(data, "clip_02")
            leaf["status"] = "rejected"
            leaf["observed_end_state"] = None
            data["take_history"] = [
                {
                    "take_id": "take_clip_01_accepted",
                    "clip_id": "clip_01",
                    "verdict": "accept",
                },
                {
                    "take_id": "take_clip_02_rejected",
                    "clip_id": "clip_02",
                    "verdict": "reject",
                },
            ]
            data["clips"] = [root, leaf]
            data["beats"] = [
                beat for beat in data["beats"] if beat.get("assigned_clip_id") != "clip_03"
            ]
            data["scenes"][0]["assigned_clip_ids"] = ["clip_01", "clip_02"]
            data["current_clip_id"] = "clip_02"

        result = self.run_mutated_project(
            reject_leaf,
            self.reviews_for_history,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_preserves_disconnected_valid_lineage_components(self) -> None:
        def add_component(data: dict) -> None:
            scene = copy.deepcopy(data["scenes"][0])
            scene["scene_id"] = "scene_02"
            scene["scene_index"] = 2
            scene["assigned_clip_ids"] = ["clip_alt_01"]
            scene["status"] = "planned"
            data["scenes"].append(scene)

            clip = copy.deepcopy(self.clip(data, "clip_01"))
            clip["clip_id"] = "clip_alt_01"
            clip["parent_clip_id"] = None
            clip["scene_id"] = "scene_02"
            clip["sequence_index"] = 1
            clip["status"] = "planned"
            clip["observed_start_state"] = None
            clip["observed_end_state"] = None
            data["clips"].append(clip)

        result = self.run_mutated_project(add_component)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

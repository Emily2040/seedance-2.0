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


class ProjectStateTests(unittest.TestCase):
    def run_mutated_project(self, mutate) -> subprocess.CompletedProcess[str]:
        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        mutate(data)
        with tempfile.TemporaryDirectory(prefix="lineage-test-", dir=ROOT) as temp_dir:
            repo = Path(temp_dir)
            fixture = repo / "examples" / "lineage" / "project-state.json"
            fixture.parent.mkdir(parents=True)
            fixture.write_text(json.dumps(data), encoding="utf-8")
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

    def test_preserves_valid_accepted_chain_with_planned_leaf(self) -> None:
        def accept_predecessors(data: dict) -> None:
            for clip_id in ("clip_01", "clip_02"):
                clip = self.clip(data, clip_id)
                clip["status"] = "accepted"
                clip["observed_end_state"] = copy.deepcopy(clip["planned_end_state"])

        result = self.run_mutated_project(accept_predecessors)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_preserves_rejected_leaf_with_accepted_parent(self) -> None:
        def reject_leaf(data: dict) -> None:
            root = self.clip(data, "clip_01")
            root["status"] = "accepted"
            root["observed_end_state"] = copy.deepcopy(root["planned_end_state"])
            leaf = self.clip(data, "clip_02")
            leaf["status"] = "rejected"
            leaf["observed_end_state"] = None
            data["clips"] = [root, leaf]
            data["beats"] = [
                beat for beat in data["beats"] if beat.get("assigned_clip_id") != "clip_03"
            ]
            data["scenes"][0]["assigned_clip_ids"] = ["clip_01", "clip_02"]
            data["current_clip_id"] = "clip_02"

        result = self.run_mutated_project(reject_leaf)
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

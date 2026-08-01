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

sys.path.insert(0, str(ROOT / "scripts"))

import continuity_chain_check  # noqa: E402
import project_state_check  # noqa: E402


class ContinuityChainTests(unittest.TestCase):
    def validate_mutated_project(self, mutate) -> tuple[list[str], list[str]]:
        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        mutate(data)
        with tempfile.TemporaryDirectory(prefix="continuity-lineage-", dir=ROOT) as temp_dir:
            fixture = Path(temp_dir) / "project-state.json"
            fixture.write_text(json.dumps(data), encoding="utf-8")
            return continuity_chain_check.validate(fixture, ROOT)

    def validate_mutated_project_with_both(self, mutate) -> tuple[list[str], list[str]]:
        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        mutate(data)
        with tempfile.TemporaryDirectory(prefix="lineage-agreement-", dir=ROOT) as temp_dir:
            fixture = Path(temp_dir) / "project-state.json"
            fixture.write_text(json.dumps(data), encoding="utf-8")
            project_errors = project_state_check.validate_project(fixture, ROOT)
            continuity_errors, _ = continuity_chain_check.validate(fixture, ROOT)
            return project_errors, continuity_errors

    @staticmethod
    def clip(data: dict, clip_id: str) -> dict:
        return next(clip for clip in data["clips"] if clip["clip_id"] == clip_id)

    def test_continuity_chain_examples_validate(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/continuity_chain_check.py", "--strict"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_empty_parent_id_is_not_treated_as_a_root(self) -> None:
        errors, _ = self.validate_mutated_project(
            lambda data: self.clip(data, "clip_01").update(parent_clip_id="")
        )
        self.assertTrue(
            any("parent_clip_id must be null or a non-empty string" in error for error in errors),
            errors,
        )

    def test_unusable_parent_is_rejected_even_for_a_planned_child(self) -> None:
        for status in ("generated", "reviewed", "repair", "rejected"):
            with self.subTest(parent_status=status):
                def make_parent_unusable(data: dict, parent_status: str = status) -> None:
                    parent = self.clip(data, "clip_01")
                    parent["status"] = parent_status
                    parent["observed_end_state"] = None
                    self.clip(data, "clip_02")["status"] = "planned"

                errors, _ = self.validate_mutated_project(make_parent_unusable)
                self.assertTrue(
                    any(f"status '{status}' is not usable" in error for error in errors),
                    errors,
                )

    def test_accepted_parent_without_observed_endpoint_is_rejected(self) -> None:
        for invalid_endpoint in (None, {}, [], "claimed endpoint", 1):
            with self.subTest(observed_end_state=invalid_endpoint):
                def remove_parent_endpoint(data: dict, endpoint=invalid_endpoint) -> None:
                    parent = self.clip(data, "clip_01")
                    parent["status"] = "accepted"
                    parent["observed_end_state"] = endpoint

                errors, _ = self.validate_mutated_project(remove_parent_endpoint)
                self.assertTrue(
                    any("missing a usable observed_end_state" in error for error in errors),
                    errors,
                )

    def test_explicit_null_root_remains_valid(self) -> None:
        errors, _ = self.validate_mutated_project(
            lambda data: self.clip(data, "clip_01").update(parent_clip_id=None)
        )
        self.assertEqual(errors, [])

    def test_accepted_parent_with_observed_endpoint_remains_valid(self) -> None:
        def accept_parent(data: dict) -> None:
            parent = self.clip(data, "clip_01")
            child = self.clip(data, "clip_02")
            parent["status"] = "accepted"
            parent["observed_end_state"] = copy.deepcopy(child["planned_start_state"])
            child["status"] = "ready"

        errors, warnings = self.validate_mutated_project(accept_parent)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_project_and_continuity_consumers_agree_on_parent_attacks(self) -> None:
        attacks = {
            "empty parent": lambda data: self.clip(data, "clip_01").update(parent_clip_id=""),
            "rejected parent": lambda data: self.clip(data, "clip_01").update(
                status="rejected", observed_end_state=None
            ),
            "ready child with unaccepted parent": lambda data: self.clip(data, "clip_02").update(
                status="ready"
            ),
            "accepted without endpoint": lambda data: self.clip(data, "clip_01").update(
                status="accepted", observed_end_state={}
            ),
        }
        for label, mutate in attacks.items():
            with self.subTest(attack=label):
                project_errors, continuity_errors = self.validate_mutated_project_with_both(mutate)
                self.assertTrue(project_errors, label)
                self.assertTrue(continuity_errors, label)


if __name__ == "__main__":
    unittest.main()

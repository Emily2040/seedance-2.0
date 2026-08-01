from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import continuity_chain_check


ROOT = Path(__file__).resolve().parents[1]
BASE_PROJECT_STATE = ROOT / "examples" / "sequence-observed-deviation" / "project-state-before.json"

sys.path.insert(0, str(ROOT / "scripts"))

import continuity_chain_check  # noqa: E402
import project_state_check  # noqa: E402


class ContinuityChainTests(unittest.TestCase):
    @staticmethod
    def review_for(data: dict, clip_id: str, take_id: str, verdict: str) -> dict:
        return {
            "project_id": data["project_id"],
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

    def validate_mutated_project(
        self,
        mutate,
        with_reviews: bool = False,
    ) -> tuple[list[str], list[str]]:
        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        mutate(data)
        with tempfile.TemporaryDirectory(prefix="continuity-lineage-") as temp_dir:
            fixture = Path(temp_dir) / "project-state.json"
            fixture.write_text(json.dumps(data), encoding="utf-8")
            if with_reviews:
                for index, entry in enumerate(data["take_history"]):
                    review = self.review_for(
                        data,
                        entry["clip_id"],
                        entry["take_id"],
                        entry["verdict"],
                    )
                    (fixture.parent / f"clip-{index}-take-review.json").write_text(
                        json.dumps(review), encoding="utf-8"
                    )
            return continuity_chain_check.validate(fixture, ROOT)

    def validate_mutated_project_with_both(self, mutate) -> tuple[list[str], list[str]]:
        data = json.loads(BASE_PROJECT_STATE.read_text(encoding="utf-8"))
        mutate(data)
        with tempfile.TemporaryDirectory(prefix="lineage-agreement-") as temp_dir:
            fixture = Path(temp_dir) / "project-state.json"
            fixture.write_text(json.dumps(data), encoding="utf-8")
            project_errors = project_state_check.validate_project(fixture, ROOT)
            continuity_errors, _ = continuity_chain_check.validate(fixture, ROOT)
            return project_errors, continuity_errors

    @staticmethod
    def clip(data: dict, clip_id: str) -> dict:
        return next(clip for clip in data["clips"] if clip["clip_id"] == clip_id)

    def validate_states(
        self,
        observed_end_state: dict,
        planned_start_state: dict,
        *,
        transition_in: str = "next shot",
        allowed_changes: list[str] | None = None,
        accepted_deviations: list[str] | None = None,
        continuity_breaks: list[str] | None = None,
    ) -> tuple[list[str], list[str]]:
        data = {
            "clips": [
                {
                    "clip_id": "clip_01",
                    "parent_clip_id": None,
                    "status": "accepted",
                    "observed_end_state": observed_end_state,
                },
                {
                    "clip_id": "clip_02",
                    "parent_clip_id": "clip_01",
                    "status": "ready",
                    "planned_start_state": planned_start_state,
                    "transition_in": transition_in,
                    "allowed_changes": allowed_changes or [],
                    "accepted_deviations": accepted_deviations or [],
                    "continuity_breaks": continuity_breaks or [],
                },
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "project-state.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return continuity_chain_check.validate(path, root)

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
            data["take_history"] = [
                {
                    "take_id": "take_clip_01_accepted",
                    "clip_id": "clip_01",
                    "verdict": "accept",
                }
            ]

        errors, warnings = self.validate_mutated_project(accept_parent, with_reviews=True)
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

    def test_generic_intentional_transition_does_not_waive_immutable_fields(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {
                    "canonical_identity_id": "hero-a",
                    "wardrobe": "red coat",
                },
                "product": {
                    "product_identity": "watch-a",
                    "prop_owner": "hero",
                },
                "environment": {"location": "studio-a"},
            },
            {
                "character": {
                    "canonical_identity_id": "hero-b",
                    "wardrobe": "blue coat",
                },
                "product": {
                    "product_identity": "watch-b",
                    "prop_owner": "guide",
                },
                "environment": {"location": "studio-b"},
            },
            transition_in="intentional next shot",
        )

        for field in (
            "canonical_identity_id",
            "wardrobe",
            "product_identity",
            "prop_owner",
            "location",
        ):
            self.assertTrue(any(field in error for error in errors), errors)

    def test_generic_intentional_allowance_does_not_waive_wardrobe(self) -> None:
        errors, _ = self.validate_states(
            {"character": {"wardrobe": "red coat"}},
            {"character": {"wardrobe": "blue coat"}},
            allowed_changes=["intentional"],
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_explicit_wardrobe_transition_waives_only_wardrobe(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {"wardrobe": "red coat"},
                "environment": {"location": "studio-a"},
            },
            {
                "character": {"wardrobe": "blue coat"},
                "environment": {"location": "studio-b"},
            },
            allowed_changes=["intentional wardrobe change after the time jump"],
        )

        self.assertFalse(any("wardrobe" in error for error in errors), errors)
        self.assertTrue(any("location" in error for error in errors), errors)

    def test_explicit_transition_in_can_waive_its_named_field(self) -> None:
        errors, warnings = self.validate_states(
            {"character": {"wardrobe": "red coat"}},
            {"character": {"wardrobe": "blue coat"}},
            transition_in="intentional wardrobe change after the time jump",
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_explicit_transition_in_recognizes_a_named_field_swap(self) -> None:
        errors, warnings = self.validate_states(
            {"character": {"wardrobe": "red coat"}},
            {"character": {"wardrobe": "blue coat"}},
            transition_in="wardrobe swap after the time jump",
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_product_identity_allowance_does_not_waive_character_identity(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {"canonical_identity_id": "hero-a"},
                "product": {"product_identity": "watch-a"},
            },
            {
                "character": {"canonical_identity_id": "hero-b"},
                "product": {"product_identity": "watch-b"},
            },
            allowed_changes=["product identity changes to the approved replacement"],
        )

        self.assertTrue(any("canonical_identity_id" in error for error in errors), errors)
        self.assertFalse(any("product_identity" in error for error in errors), errors)

    def test_axis_reset_waives_travel_direction_only(self) -> None:
        errors, warnings = self.validate_states(
            {
                "character": {"travel_direction": "left-to-right"},
                "environment": {"location": "studio-a"},
            },
            {
                "character": {"travel_direction": "right-to-left"},
                "environment": {"location": "studio-b"},
            },
            transition_in="intentional axis reset for the reverse angle",
        )

        self.assertTrue(any("location" in error for error in errors), errors)
        self.assertFalse(any("travel_direction" in warning for warning in warnings), warnings)

    def test_axis_reset_in_allowance_list_is_scoped_to_travel_direction(self) -> None:
        errors, warnings = self.validate_states(
            {
                "character": {"travel_direction": "left-to-right"},
                "environment": {"location": "studio-a"},
            },
            {
                "character": {"travel_direction": "right-to-left"},
                "environment": {"location": "studio-b"},
            },
            allowed_changes=["axis reset"],
        )

        self.assertTrue(any("location" in error for error in errors), errors)
        self.assertFalse(any("travel_direction" in warning for warning in warnings), warnings)

    def test_null_state_values_remain_not_comparable(self) -> None:
        errors, warnings = self.validate_states(
            {"character": {"wardrobe": None}},
            {"character": {"wardrobe": "blue coat"}},
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_all_nested_characters_are_compared_by_character_id(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide-a",
                        "wardrobe": "blue coat",
                    },
                }
            },
            {
                "characters": {
                    "guide": {
                        "canonical_identity_id": "guide-a",
                        "wardrobe": "green coat",
                    },
                    "hero": {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "red coat",
                    },
                }
            },
        )

        self.assertTrue(
            any("characters.guide.wardrobe" in error for error in errors),
            errors,
        )
        self.assertFalse(
            any("characters.hero.wardrobe" in error for error in errors),
            errors,
        )

    def test_reordered_character_list_matches_canonical_identity_ids(self) -> None:
        errors, warnings = self.validate_states(
            {
                "characters": [
                    {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "red coat",
                    },
                    {
                        "canonical_identity_id": "guide-a",
                        "wardrobe": "blue coat",
                    },
                ]
            },
            {
                "characters": [
                    {
                        "canonical_identity_id": "guide-a",
                        "wardrobe": "blue coat",
                    },
                    {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "red coat",
                    },
                ]
            },
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_reordered_character_list_reports_change_for_the_canonical_identity(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "red coat",
                    },
                    {
                        "canonical_identity_id": "guide-a",
                        "wardrobe": "blue coat",
                    },
                ]
            },
            {
                "characters": [
                    {
                        "canonical_identity_id": "guide-a",
                        "wardrobe": "green coat",
                    },
                    {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "red coat",
                    },
                ]
            },
        )

        self.assertTrue(
            any("characters.guide-a.wardrobe" in error for error in errors),
            errors,
        )
        self.assertFalse(any("canonical_identity_id" in error for error in errors), errors)
        self.assertFalse(any("characters.hero-a.wardrobe" in error for error in errors), errors)

    def test_character_list_still_reports_a_canonical_identity_replacement(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"canonical_identity_id": "hero-a", "wardrobe": "red coat"},
                    {"canonical_identity_id": "guide-a", "wardrobe": "blue coat"},
                ]
            },
            {
                "characters": [
                    {"canonical_identity_id": "hero-b", "wardrobe": "red coat"},
                    {"canonical_identity_id": "guide-a", "wardrobe": "blue coat"},
                ]
            },
        )

        self.assertTrue(any("canonical_identity_id" in error for error in errors), errors)

    def test_singleton_fields_on_different_named_entities_are_not_compared(self) -> None:
        errors, warnings = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "red coat",
                    }
                }
            },
            {
                "characters": {
                    "guide": {
                        "canonical_identity_id": "guide-a",
                        "wardrobe": "blue coat",
                    }
                }
            },
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_singleton_fields_on_the_same_named_entity_are_still_compared(self) -> None:
        errors, _ = self.validate_states(
            {"characters": {"hero": {"wardrobe": "red coat"}}},
            {"characters": {"hero": {"wardrobe": "blue coat"}}},
        )

        self.assertTrue(any("characters.hero.wardrobe" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()

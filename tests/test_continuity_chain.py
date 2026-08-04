from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
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
            "project_id": "continuity-test",
            "clips": [
                {
                    "clip_id": "clip_01",
                    "parent_clip_id": None,
                    "sequence_index": 1,
                    "status": "accepted",
                    "observed_end_state": observed_end_state,
                },
                {
                    "clip_id": "clip_02",
                    "parent_clip_id": "clip_01",
                    "sequence_index": 2,
                    "status": "ready",
                    "planned_start_state": planned_start_state,
                    "transition_in": transition_in,
                    "allowed_changes": allowed_changes or [],
                    "accepted_deviations": accepted_deviations or [],
                    "continuity_breaks": continuity_breaks or [],
                },
            ],
            "take_history": [
                {
                    "take_id": "take_clip_01_accepted",
                    "clip_id": "clip_01",
                    "verdict": "accept",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "project-state.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            review = self.review_for(
                data,
                "clip_01",
                "take_clip_01_accepted",
                "accept",
            )
            (root / "clip-01-take-review.json").write_text(
                json.dumps(review),
                encoding="utf-8",
            )
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
    def test_malformed_public_inputs_return_diagnostics_instead_of_crashing(self) -> None:
        malformed_documents = (
            [],
            {"clips": {}},
            {"clips": ["not-an-object"]},
            {"clips": [{"clip_id": []}]},
            {
                "clips": [
                    {"clip_id": "parent", "status": "accepted"},
                    {
                        "clip_id": "child",
                        "parent_clip_id": [],
                        "status": "ready",
                    },
                ]
            },
            {
                "clips": [
                    {
                        "clip_id": "parent",
                        "status": "accepted",
                        "observed_end_state": [],
                    },
                    {
                        "clip_id": "child",
                        "parent_clip_id": "parent",
                        "status": "ready",
                        "planned_start_state": [],
                    },
                ]
            },
        )
        for document in malformed_documents:
            with self.subTest(document=document), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path = root / "project-state.json"
                path.write_text(json.dumps(document), encoding="utf-8")
                errors, warnings = continuity_chain_check.validate(path, root)
                self.assertTrue(errors)
                self.assertEqual(warnings, [])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "project-state.json"
            path.write_text('{"clips": [', encoding="utf-8")
            errors, warnings = continuity_chain_check.validate(path, root)
            self.assertTrue(any("invalid JSON" in error for error in errors), errors)
            self.assertEqual(warnings, [])

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

    def test_negated_allowed_change_does_not_waive_wardrobe(self) -> None:
        errors, _ = self.validate_states(
            {"character": {"wardrobe": "red coat"}},
            {"character": {"wardrobe": "blue coat"}},
            allowed_changes=["do not change wardrobe"],
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_unchanged_deviation_does_not_waive_wardrobe(self) -> None:
        errors, _ = self.validate_states(
            {"character": {"wardrobe": "red coat"}},
            {"character": {"wardrobe": "blue coat"}},
            accepted_deviations=["wardrobe remains unchanged"],
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_negated_transition_does_not_waive_wardrobe(self) -> None:
        errors, _ = self.validate_states(
            {"character": {"wardrobe": "red coat"}},
            {"character": {"wardrobe": "blue coat"}},
            transition_in="wardrobe doesn't change in this transition",
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_positive_clause_after_negated_clause_still_waives_wardrobe(self) -> None:
        errors, warnings = self.validate_states(
            {
                "character": {"wardrobe": "red coat"},
                "environment": {"location": "studio-a"},
            },
            {
                "character": {"wardrobe": "blue coat"},
                "environment": {"location": "studio-b"},
            },
            allowed_changes=["location must not change; wardrobe may change"],
        )

        self.assertFalse(any("wardrobe" in error for error in errors), errors)
        self.assertTrue(any("location" in error for error in errors), errors)
        self.assertEqual(warnings, [])

    def test_denial_for_another_field_does_not_cancel_wardrobe_waiver(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {
                    "canonical_identity_id": "hero-a",
                    "wardrobe": "red coat",
                }
            },
            {
                "character": {
                    "canonical_identity_id": "hero-b",
                    "wardrobe": "blue coat",
                }
            },
            allowed_changes=["wardrobe may change without altering canonical identity"],
        )

        self.assertFalse(any("wardrobe" in error for error in errors), errors)
        self.assertTrue(any("canonical_identity_id" in error for error in errors), errors)

    def test_without_binds_forward_across_subordinate_modifiers(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {
                    "canonical_identity_id": "hero-a",
                    "wardrobe": "red coat",
                }
            },
            {
                "character": {
                    "canonical_identity_id": "hero-b",
                    "wardrobe": "blue coat",
                }
            },
            allowed_changes=[
                "wardrobe may change without deliberately or indirectly altering canonical identity"
            ],
        )

        self.assertFalse(any("wardrobe" in error for error in errors), errors)
        self.assertTrue(any("canonical_identity_id" in error for error in errors), errors)

    def test_without_non_field_restriction_does_not_negate_waiver(self) -> None:
        errors, warnings = self.validate_states(
            {"character": {"wardrobe": "red coat"}},
            {"character": {"wardrobe": "blue coat"}},
            allowed_changes=["wardrobe may change without restriction"],
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_postpositive_denial_targets_only_its_named_field(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {
                    "wardrobe": "red coat",
                    "product_identity": "watch-a",
                }
            },
            {
                "character": {
                    "wardrobe": "blue coat",
                    "product_identity": "watch-b",
                }
            },
            allowed_changes=["wardrobe may change while product identity must not change"],
        )

        self.assertFalse(any("wardrobe" in error for error in errors), errors)
        self.assertTrue(any("product_identity" in error for error in errors), errors)

    def test_denial_of_coordinated_fields_does_not_create_a_partial_waiver(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {"wardrobe": "red coat"},
                "product": {"product_identity": "watch-a"},
            },
            {
                "character": {"wardrobe": "blue coat"},
                "product": {"product_identity": "watch-b"},
            },
            allowed_changes=["wardrobe and product identity must not change"],
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)
        self.assertTrue(any("product_identity" in error for error in errors), errors)

    def test_mixed_field_clauses_keep_positive_and_negative_scope_separate(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {
                    "canonical_identity_id": "hero-a",
                    "wardrobe": "red coat",
                },
                "environment": {"location": "studio-a"},
            },
            {
                "character": {
                    "canonical_identity_id": "hero-b",
                    "wardrobe": "blue coat",
                },
                "environment": {"location": "studio-b"},
            },
            allowed_changes=[
                "wardrobe may change without altering canonical identity, location may change"
            ],
        )

        self.assertFalse(any("wardrobe" in error for error in errors), errors)
        self.assertFalse(any("location" in error for error in errors), errors)
        self.assertTrue(any("canonical_identity_id" in error for error in errors), errors)

    def test_change_verbs_are_bound_to_their_local_field_clause(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {"wardrobe": "red coat"},
                "environment": {"location": "studio-a"},
            },
            {
                "character": {"wardrobe": "blue coat"},
                "environment": {"location": "studio-b"},
            },
            allowed_changes=["wardrobe continuity while location may change"],
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)
        self.assertFalse(any("location" in error for error in errors), errors)

    def test_bare_field_fragments_from_mixed_entries_are_not_waivers(self) -> None:
        for allowance in (
            "wardrobe while location may change",
            "wardrobe, location may change",
        ):
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {
                        "character": {"wardrobe": "red coat"},
                        "environment": {"location": "studio-a"},
                    },
                    {
                        "character": {"wardrobe": "blue coat"},
                        "environment": {"location": "studio-b"},
                    },
                    allowed_changes=[allowance],
                )

                self.assertTrue(any("wardrobe" in error for error in errors), errors)
                self.assertFalse(any("location" in error for error in errors), errors)

    def test_mixed_denial_and_permission_clauses_remain_asymmetric(self) -> None:
        for allowance in (
            "wardrobe must not change while product identity may change",
            "wardrobe change is not permitted while product identity may change",
        ):
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {
                        "character": {
                            "wardrobe": "red coat",
                            "product_identity": "watch-a",
                        }
                    },
                    {
                        "character": {
                            "wardrobe": "blue coat",
                            "product_identity": "watch-b",
                        }
                    },
                    allowed_changes=[allowance],
                )

                self.assertTrue(any("wardrobe" in error for error in errors), errors)
                self.assertFalse(any("product_identity" in error for error in errors), errors)

    def test_preservation_clause_does_not_negate_following_identity_waiver(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {
                    "canonical_identity_id": "hero-a",
                    "wardrobe": "red coat",
                }
            },
            {
                "character": {
                    "canonical_identity_id": "hero-b",
                    "wardrobe": "blue coat",
                }
            },
            allowed_changes=["wardrobe is fixed and canonical identity may change"],
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)
        self.assertFalse(any("canonical_identity_id" in error for error in errors), errors)

    def test_coordinated_positive_fields_share_the_local_permission(self) -> None:
        errors, warnings = self.validate_states(
            {
                "character": {
                    "wardrobe": "red coat",
                    "product_identity": "watch-a",
                }
            },
            {
                "character": {
                    "wardrobe": "blue coat",
                    "product_identity": "watch-b",
                }
            },
            allowed_changes=["wardrobe and product identity may change"],
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_ordinary_but_still_separates_independent_field_clauses(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {"wardrobe": "red coat"},
                "environment": {"location": "studio-a"},
            },
            {
                "character": {"wardrobe": "blue coat"},
                "environment": {"location": "studio-b"},
            },
            allowed_changes=["wardrobe must not change but location may change"],
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)
        self.assertFalse(any("location" in error for error in errors), errors)

    def test_negated_mapping_value_does_not_turn_its_key_into_a_waiver(self) -> None:
        errors, _ = self.validate_states(
            {"character": {"wardrobe": "red coat"}},
            {"character": {"wardrobe": "blue coat"}},
            allowed_changes=[{"wardrobe": "must not change"}],
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_bare_field_name_remains_an_explicit_waiver_shorthand(self) -> None:
        errors, warnings = self.validate_states(
            {"character": {"wardrobe": "red coat"}},
            {"character": {"wardrobe": "blue coat"}},
            allowed_changes=["wardrobe"],
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_vague_continuity_mention_does_not_waive_wardrobe(self) -> None:
        errors, _ = self.validate_states(
            {"character": {"wardrobe": "red coat"}},
            {"character": {"wardrobe": "blue coat"}},
            allowed_changes=["wardrobe continuity"],
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_structured_allowance_placeholders_do_not_create_waivers(self) -> None:
        for allowance in (
            {"wardrobe": {}},
            {"wardrobe": []},
            {"wardrobe": None},
            {"wardrobe": {"location": "may change"}},
        ):
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {"character": {"wardrobe": "red coat"}},
                    {"character": {"wardrobe": "blue coat"}},
                    allowed_changes=[allowance],
                )

                self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_additional_denial_language_does_not_create_waivers(self) -> None:
        for allowance in ("wardrobe changes prohibited", "avoid wardrobe change"):
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {"character": {"wardrobe": "red coat"}},
                    {"character": {"wardrobe": "blue coat"}},
                    allowed_changes=[allowance],
                )

                self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_entity_qualified_waiver_only_applies_to_that_entity(self) -> None:
        errors, warnings = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "white coat",
                    },
                }
            },
            allowed_changes=["hero wardrobe may change"],
        )

        self.assertFalse(any("characters.hero.wardrobe" in error for error in errors), errors)
        self.assertTrue(any("characters.guide.wardrobe" in error for error in errors), errors)
        self.assertEqual(warnings, [])

    def test_entity_qualified_waiver_does_not_excuse_collection_replacement(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"canonical_identity_id": "hero", "wardrobe": "red coat"},
                    {"canonical_identity_id": "guide", "wardrobe": "black coat"},
                ]
            },
            {
                "characters": [
                    {"canonical_identity_id": "hero", "wardrobe": "red coat"},
                    {"canonical_identity_id": "newcomer", "wardrobe": "black coat"},
                ]
            },
            allowed_changes=["guide canonical identity may change"],
        )

        self.assertTrue(any("inventory changes" in error for error in errors), errors)

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

    def test_negated_axis_reset_does_not_waive_travel_direction(self) -> None:
        _, warnings = self.validate_states(
            {"character": {"travel_direction": "left-to-right"}},
            {"character": {"travel_direction": "right-to-left"}},
            allowed_changes=["no axis reset"],
        )

        self.assertTrue(any("travel_direction" in warning for warning in warnings), warnings)

    def test_unknown_axis_reset_entity_qualifier_is_not_global(self) -> None:
        _, warnings = self.validate_states(
            {"character": {"travel_direction": "left-to-right"}},
            {"character": {"travel_direction": "right-to-left"}},
            allowed_changes=["axis reset for stranger"],
        )

        self.assertTrue(any("travel_direction" in warning for warning in warnings), warnings)

    def test_null_state_values_remain_not_comparable(self) -> None:
        errors, warnings = self.validate_states(
            {"character": {"wardrobe": None}},
            {"character": {"wardrobe": "blue coat"}},
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_non_null_immutable_field_cannot_disappear(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "red coat",
                }
            },
            {"character": {"canonical_identity_id": "hero"}},
        )

        self.assertTrue(
            any("wardrobe disappears without allowance" in error for error in errors),
            errors,
        )

    def test_non_null_immutable_field_cannot_appear(self) -> None:
        errors, _ = self.validate_states(
            {"character": {"canonical_identity_id": "hero"}},
            {
                "character": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "red coat",
                }
            },
        )

        self.assertTrue(
            any("wardrobe appears without allowance" in error for error in errors),
            errors,
        )

    def test_positional_tracked_collection_cannot_disappear(self) -> None:
        errors, _ = self.validate_states(
            {"characters": [{"wardrobe": "red coat"}]},
            {"characters": []},
        )

        self.assertTrue(
            any("wardrobe disappears without allowance" in error for error in errors),
            errors,
        )

    def test_cjk_entity_qualified_waiver_does_not_become_global(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"canonical_identity_id": "英雄", "wardrobe": "red coat"},
                    {"canonical_identity_id": "向导", "wardrobe": "black coat"},
                ]
            },
            {
                "characters": [
                    {"canonical_identity_id": "英雄", "wardrobe": "blue coat"},
                    {"canonical_identity_id": "向导", "wardrobe": "white coat"},
                ]
            },
            allowed_changes=["英雄 wardrobe may change"],
        )

        self.assertFalse(any("英雄.wardrobe" in error for error in errors), errors)
        self.assertTrue(any(r"\u5411\u5bfc.wardrobe" in error for error in errors), errors)

    def test_whitespace_only_canonical_identity_is_rejected(self) -> None:
        errors, _ = self.validate_states(
            {"character": {"canonical_identity_id": "   ", "wardrobe": "red"}},
            {"character": {"canonical_identity_id": "   ", "wardrobe": "red"}},
        )

        self.assertTrue(any("canonical_identity_id" in error for error in errors), errors)

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

    def test_singleton_canonical_entity_replacement_is_rejected(self) -> None:
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

        self.assertTrue(any("inventory changes" in error for error in errors), errors)
        self.assertEqual(warnings, [])

    def test_singleton_fields_on_the_same_named_entity_are_still_compared(self) -> None:
        errors, _ = self.validate_states(
            {"characters": {"hero": {"wardrobe": "red coat"}}},
            {"characters": {"hero": {"wardrobe": "blue coat"}}},
        )

        self.assertTrue(any("characters.hero.wardrobe" in error for error in errors), errors)

    def test_singleton_fields_on_different_named_entities_are_not_compared(self) -> None:
        errors, warnings = self.validate_states(
            {
                "characters": {
                    "hero": {"wardrobe": "red coat", "pose": "standing"}
                }
            },
            {
                "characters": {
                    "guide": {"wardrobe": "blue coat", "pose": "seated"}
                }
            },
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_duplicate_canonical_identity_cannot_collapse_field_drift(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"canonical_identity_id": "hero", "wardrobe": "red coat"},
                    {"canonical_identity_id": "hero", "wardrobe": "blue coat"},
                ]
            },
            {
                "characters": [
                    {"canonical_identity_id": "hero", "wardrobe": "green coat"},
                    {"canonical_identity_id": "hero", "wardrobe": "blue coat"},
                ]
            },
        )

        self.assertTrue(any("is duplicated" in error for error in errors), errors)

    def test_canonical_identity_matches_across_dictionary_key_rename(self) -> None:
        errors, _ = self.validate_states(
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
                    "lead": {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "blue coat",
                    }
                }
            },
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_canonical_identity_matches_across_list_to_dictionary_reshape(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "red coat",
                    }
                ]
            },
            {
                "characters": {
                    "lead": {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "blue coat",
                    }
                }
            },
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_canonical_field_matches_after_nested_container_move(self) -> None:
        errors, _ = self.validate_states(
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
                    "hero": {
                        "canonical_identity_id": "hero-a",
                        "appearance": {"wardrobe": "blue coat"},
                    }
                }
            },
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_mixed_canonical_and_positional_records_are_rejected(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"canonical_identity_id": "hero-a", "wardrobe": "red coat"},
                    {"wardrobe": "blue coat"},
                ]
            },
            {
                "characters": [
                    {"wardrobe": "green coat"},
                    {"canonical_identity_id": "hero-a", "wardrobe": "red coat"},
                ]
            },
        )

        self.assertTrue(any("mixes canonical-identity" in error for error in errors), errors)

    def test_integer_and_string_canonical_identities_do_not_collide(self) -> None:
        errors, warnings = self.validate_states(
            {
                "characters": [
                    {"canonical_identity_id": 1, "wardrobe": "red coat"},
                    {"canonical_identity_id": "1", "wardrobe": "blue coat"},
                ]
            },
            {
                "characters": [
                    {"canonical_identity_id": "1", "wardrobe": "blue coat"},
                    {"canonical_identity_id": 1, "wardrobe": "red coat"},
                ]
            },
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_repeated_field_within_one_canonical_entity_is_rejected(self) -> None:
        state = {
            "character": {
                "canonical_identity_id": "hero-a",
                "wardrobe": "red coat",
                "appearance": {"wardrobe": "blue coat"},
            }
        }
        errors, _ = self.validate_states(state, state)

        self.assertTrue(any("ambiguous repeated" in error for error in errors), errors)

    def test_duplicate_fallback_list_identity_is_rejected(self) -> None:
        state = {
            "characters": [
                {"id": "hero", "wardrobe": "red coat"},
                {"id": "hero", "wardrobe": "blue coat"},
            ]
        }
        errors, _ = self.validate_states(state, state)

        self.assertTrue(any("duplicate list identities" in error for error in errors), errors)

    def test_canonical_collection_cannot_disappear_into_an_empty_list(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"canonical_identity_id": "hero-a", "wardrobe": "red coat"}
                ]
            },
            {"characters": []},
        )

        self.assertTrue(any("inventory changes" in error for error in errors), errors)

    def test_canonical_collection_cannot_become_positional_records(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"canonical_identity_id": "hero-a", "wardrobe": "red coat"}
                ]
            },
            {"characters": [{"wardrobe": "red coat"}]},
        )

        self.assertTrue(any("inventory changes" in error for error in errors), errors)

    def test_nested_collection_inventory_survives_parent_path_rename(self) -> None:
        errors, _ = self.validate_states(
            {
                "groups": {
                    "primary": {
                        "canonical_identity_id": "team-a",
                        "members": [
                            {"canonical_identity_id": "hero-a", "wardrobe": "red coat"}
                        ],
                    }
                }
            },
            {
                "groups": {
                    "renamed": {
                        "canonical_identity_id": "team-a",
                        "members": [
                            {"canonical_identity_id": "guide-a", "wardrobe": "red coat"}
                        ],
                    }
                }
            },
        )

        self.assertTrue(any("inventory changes" in error for error in errors), errors)

    def test_wrapped_list_records_cannot_hide_reorder_and_replacement(self) -> None:
        errors, _ = self.validate_states(
            {
                "slots": [
                    {
                        "record": {
                            "canonical_identity_id": "hero",
                            "wardrobe": "red coat",
                        }
                    },
                    {
                        "record": {
                            "canonical_identity_id": "guide",
                            "wardrobe": "blue coat",
                        }
                    },
                ]
            },
            {
                "slots": [
                    {
                        "record": {
                            "canonical_identity_id": "guide",
                            "wardrobe": "blue coat",
                        }
                    },
                    {
                        "record": {
                            "canonical_identity_id": "newcomer",
                            "wardrobe": "green coat",
                        }
                    },
                ]
            },
        )

        self.assertTrue(any("inventory changes" in error for error in errors), errors)

    def test_longest_identity_alias_prevents_overlapping_scope_leak(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                    },
                    "super_hero": {
                        "canonical_identity_id": "super hero",
                        "wardrobe": "black coat",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                    },
                    "super_hero": {
                        "canonical_identity_id": "super hero",
                        "wardrobe": "white coat",
                    },
                }
            },
            allowed_changes=["super hero wardrobe may change"],
        )

        self.assertTrue(any("characters.hero.wardrobe" in error for error in errors), errors)
        self.assertFalse(
            any("characters.super_hero.wardrobe" in error for error in errors),
            errors,
        )

    def test_multi_identity_clause_is_not_treated_as_scoped_waiver(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                }
            },
            allowed_changes=["hero wardrobe may change while guide watches"],
        )

        self.assertTrue(any("characters.hero.wardrobe" in error for error in errors), errors)

    def test_dictionary_key_alias_scopes_nonexact_canonical_id(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide-a",
                        "wardrobe": "black coat",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero-a",
                        "wardrobe": "blue coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide-a",
                        "wardrobe": "white coat",
                    },
                }
            },
            allowed_changes=["hero wardrobe may change"],
        )

        self.assertFalse(any("characters.hero.wardrobe" in error for error in errors), errors)
        self.assertTrue(any("characters.guide.wardrobe" in error for error in errors), errors)

    def test_unknown_entity_qualifier_does_not_become_global_waiver(self) -> None:
        errors, _ = self.validate_states(
            {
                "character": {
                    "canonical_identity_id": "hero-a",
                    "wardrobe": "red coat",
                }
            },
            {
                "character": {
                    "canonical_identity_id": "hero-a",
                    "wardrobe": "blue coat",
                }
            },
            allowed_changes=["hero wardrobe may change"],
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_unknown_suffix_entity_qualifier_does_not_become_global_waiver(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "white coat",
                    },
                }
            },
            allowed_changes=["wardrobe may change for stranger"],
        )

        self.assertTrue(any("characters.hero.wardrobe" in error for error in errors), errors)
        self.assertTrue(any("characters.guide.wardrobe" in error for error in errors), errors)

    def test_comma_separated_unknown_qualifier_stays_attached_to_waiver(self) -> None:
        qualifiers = (
            "for stranger",
            "only for stranger",
            "specifically for stranger",
            "exclusively for stranger",
            "only specifically exclusively for stranger",
            "but for stranger",
            "but only for stranger",
            "but specifically for stranger",
            "but exclusively for stranger",
            "but only specifically exclusively for stranger",
        )
        for qualifier in qualifiers:
            allowance = f"wardrobe may change, {qualifier}"
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=[allowance],
                )

                self.assertTrue(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

        for qualifier in qualifiers[5:]:
            allowance = f"wardrobe may change {qualifier}"
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=[allowance],
                )

                self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_unknown_qualifier_cannot_escape_across_other_boundaries(self) -> None:
        for allowance in (
            "wardrobe may change; only for stranger",
            "wardrobe may change. Specifically for stranger",
            "wardrobe may change\nhowever exclusively for stranger",
            "only for stranger, wardrobe may change",
        ):
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {"character": {"wardrobe": "red coat"}},
                    {"character": {"wardrobe": "blue coat"}},
                    allowed_changes=[allowance],
                )

                self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_conflicting_wardrobe_polarity_is_aggregated_across_entry(self) -> None:
        allowances = (
            "wardrobe may change; wardrobe must not change",
            "wardrobe may change, wardrobe remains unchanged",
            "wardrobe may change while wardrobe remains unchanged",
            "wardrobe may change whereas wardrobe remains unchanged",
            "wardrobe may change but wardrobe remains unchanged",
            "wardrobe may change however wardrobe remains unchanged",
            "wardrobe may change; must remain unchanged",
            "wardrobe may change, must remain unchanged",
            "wardrobe may change, but must remain unchanged",
            "wardrobe may change while it must remain unchanged",
            "wardrobe may change whereas it must remain unchanged",
            "wardrobe may change but must remain unchanged",
            "wardrobe may change however must remain unchanged",
        )
        for allowance in allowances:
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {"character": {"wardrobe": "red coat"}},
                    {"character": {"wardrobe": "blue coat"}},
                    allowed_changes=[allowance],
                )

                self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_conflicting_wardrobe_polarity_is_aggregated_across_entries(self) -> None:
        for kwargs in (
            {
                "allowed_changes": [
                    "wardrobe may change",
                    "wardrobe must not change",
                ]
            },
            {
                "allowed_changes": ["wardrobe may change"],
                "accepted_deviations": ["wardrobe remains unchanged"],
            },
            {
                "allowed_changes": ["wardrobe may change"],
                "transition_in": "wardrobe must not change",
            },
        ):
            with self.subTest(kwargs=kwargs):
                errors, _ = self.validate_states(
                    {"character": {"wardrobe": "red coat"}},
                    {"character": {"wardrobe": "blue coat"}},
                    **kwargs,
                )

                self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_other_entity_denial_does_not_cancel_one_entry_waiver(self) -> None:
        errors, warnings = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                }
            },
            allowed_changes=[
                "hero wardrobe may change while guide wardrobe must not change"
            ],
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_other_entity_denial_does_not_cancel_separate_entry_waiver(self) -> None:
        errors, warnings = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                }
            },
            allowed_changes=[
                "hero wardrobe may change",
                "guide wardrobe must not change",
            ],
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_same_entity_or_global_denial_cancels_entity_waiver(self) -> None:
        for allowance in (
            "hero wardrobe may change while hero wardrobe must not change",
            "hero wardrobe may change while wardrobe must not change",
        ):
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    allowed_changes=[allowance],
                )

                self.assertTrue(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )

    def test_entity_denial_filters_global_waiver_only_for_that_entity(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "white coat",
                    },
                }
            },
            allowed_changes=[
                "wardrobe may change",
                "guide wardrobe must not change",
            ],
        )

        self.assertFalse(
            any("characters.hero.wardrobe" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("characters.guide.wardrobe" in error for error in errors),
            errors,
        )

    def test_shared_denial_predicate_binds_every_coordinated_field_group(self) -> None:
        denials = (
            "hero wardrobe and guide location must not change",
            "hero wardrobe or guide location must not change",
            "hero wardrobe, and guide location must not change",
            "hero wardrobe as well as guide location must not change",
            "hero wardrobe, as well as guide location must not change",
        )
        for denial in denials:
            with self.subTest(denial=denial):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                                "location": "stage-a",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                                "location": "hall-a",
                            },
                            "extra": {
                                "canonical_identity_id": "extra",
                                "wardrobe": "white coat",
                                "location": "yard-a",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                                "location": "stage-a",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                                "location": "hall-b",
                            },
                            "extra": {
                                "canonical_identity_id": "extra",
                                "wardrobe": "silver coat",
                                "location": "yard-a",
                            },
                        }
                    },
                    allowed_changes=[
                        "wardrobe may change",
                        "location may change",
                        denial,
                    ],
                )

                self.assertTrue(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.location" in error for error in errors),
                    errors,
                )
                self.assertFalse(
                    any("characters.extra.wardrobe" in error for error in errors),
                    errors,
                )

    def test_three_item_comma_lists_share_predicate_across_every_field(self) -> None:
        before = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "red coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "location": "hall-a",
                },
                "extra": {
                    "canonical_identity_id": "extra",
                    "product_identity": "watch-a",
                },
            }
        }
        after = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "blue coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "location": "hall-b",
                },
                "extra": {
                    "canonical_identity_id": "extra",
                    "product_identity": "watch-b",
                },
            }
        }
        list_forms = (
            "hero wardrobe, guide location, and extra product identity",
            "hero wardrobe, guide location and extra product identity",
            "hero wardrobe， guide location， and extra product identity",
            "hero wardrobe， guide location and extra product identity",
        )
        global_waivers = (
            "wardrobe may change",
            "location may change",
            "product identity may change",
        )

        for field_list in list_forms:
            with self.subTest(field_list=field_list, polarity="denial"):
                errors, _ = self.validate_states(
                    before,
                    after,
                    allowed_changes=[
                        *global_waivers,
                        f"{field_list} must not change",
                    ],
                )
                for path in (
                    "characters.hero.wardrobe",
                    "characters.guide.location",
                    "characters.extra.product_identity",
                ):
                    self.assertTrue(any(path in error for error in errors), errors)

            with self.subTest(field_list=field_list, polarity="positive"):
                errors, warnings = self.validate_states(
                    before,
                    after,
                    allowed_changes=[f"{field_list} may change"],
                )
                self.assertEqual(errors, [])
                self.assertEqual(warnings, [])

        errors, _ = self.validate_states(
            before,
            after,
            allowed_changes=[
                *global_waivers,
                "hero wardrobe may change, guide location and "
                "extra product identity must not change",
            ],
        )
        self.assertFalse(any("characters.hero.wardrobe" in error for error in errors), errors)
        self.assertTrue(any("characters.guide.location" in error for error in errors), errors)
        self.assertTrue(
            any("characters.extra.product_identity" in error for error in errors),
            errors,
        )

    def test_prefix_and_suffix_serial_predicates_cover_every_known_field(self) -> None:
        before = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "red coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "location": "hall-a",
                },
                "extra": {
                    "canonical_identity_id": "extra",
                    "product_identity": "watch-a",
                },
            }
        }
        after = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "blue coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "location": "hall-b",
                },
                "extra": {
                    "canonical_identity_id": "extra",
                    "product_identity": "watch-b",
                },
            }
        }
        paths = (
            "characters.hero.wardrobe",
            "characters.guide.location",
            "characters.extra.product_identity",
        )
        global_waivers = (
            "wardrobe may change",
            "location may change",
            "product identity may change",
        )
        field_list = (
            "hero wardrobe, guide location, and extra product identity"
        )

        denials = (
            f"preserve {field_list}",
            f"keep {field_list}",
            f"do not change {field_list}",
            f"never alter {field_list}",
            f"forbid changes to {field_list}",
            f"{field_list} must not change",
            f"{field_list} must remain unchanged",
        )
        for denial in denials:
            with self.subTest(denial=denial):
                errors, _ = self.validate_states(
                    before,
                    after,
                    allowed_changes=[*global_waivers, denial],
                )
                for path in paths:
                    self.assertTrue(any(path in error for error in errors), errors)

        positives = (
            f"allow changes to {field_list}",
            f"permit changes to {field_list}",
            f"change {field_list}",
            f"{field_list} may change",
        )
        for positive in positives:
            with self.subTest(positive=positive):
                errors, warnings = self.validate_states(
                    before,
                    after,
                    allowed_changes=[positive],
                )
                self.assertEqual(errors, [])
                self.assertEqual(warnings, [])

    def test_serial_lists_fail_closed_with_unknown_items_and_unicode_commas(self) -> None:
        before = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "red coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "location": "hall-a",
                },
                "extra": {
                    "canonical_identity_id": "extra",
                    "product_identity": "watch-a",
                },
            }
        }
        after = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "blue coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "location": "hall-b",
                },
                "extra": {
                    "canonical_identity_id": "extra",
                    "product_identity": "watch-b",
                },
            }
        }
        paths = (
            "characters.hero.wardrobe",
            "characters.guide.location",
            "characters.extra.product_identity",
        )
        global_waivers = (
            "wardrobe may change",
            "location may change",
            "product identity may change",
        )
        unknown_lists = (
            "stranger hairstyle, hero wardrobe, guide location, and extra product identity",
            "hero wardrobe, stranger hairstyle, guide location, and extra product identity",
            "hero wardrobe, guide location, stranger hairstyle, and extra product identity",
            "hero wardrobe, guide location, extra product identity, and stranger hairstyle",
        )
        for field_list in unknown_lists:
            for denial in (
                f"preserve {field_list}",
                f"{field_list} must not change",
            ):
                with self.subTest(field_list=field_list, denial=denial):
                    errors, _ = self.validate_states(
                        before,
                        after,
                        allowed_changes=[*global_waivers, denial],
                    )
                    for path in paths:
                        self.assertTrue(any(path in error for error in errors), errors)

        for comma in (",", "\u060c", "\u3001", "\ufe10", "\ufe50", "\uff0c", "\uff64"):
            field_list = (
                f"hero wardrobe{comma} guide location{comma} "
                "and extra product identity"
            )
            for denial in (
                f"preserve {field_list}",
                f"{field_list} must not change",
            ):
                with self.subTest(comma=comma, denial=denial):
                    errors, _ = self.validate_states(
                        before,
                        after,
                        allowed_changes=[*global_waivers, denial],
                    )
                    for path in paths:
                        self.assertTrue(any(path in error for error in errors), errors)

            for positive in (
                f"allow changes to {field_list}",
                f"{field_list} may change",
            ):
                with self.subTest(comma=comma, positive=positive):
                    errors, warnings = self.validate_states(
                        before,
                        after,
                        allowed_changes=[positive],
                    )
                    self.assertEqual(errors, [])
                    self.assertEqual(warnings, [])

    def test_identity_tokens_never_double_as_waiver_events(self) -> None:
        identity_predicate_words = (
            "May",
            "Can",
            "Allow",
            "Change",
            "Alter",
            "New",
            "Shift",
            "Swap",
        )
        for identity in identity_predicate_words:
            before = {
                "characters": {
                    "subject": {
                        "canonical_identity_id": identity,
                        "wardrobe": "red coat",
                    }
                }
            }
            after = {
                "characters": {
                    "subject": {
                        "canonical_identity_id": identity,
                        "wardrobe": "blue coat",
                    }
                }
            }
            unsafe_allowances = (
                f"{identity} wardrobe",
                f"{identity}'s wardrobe",
                f"wardrobe after {identity} shot",
                f"wardrobe before {identity} sequence",
                f"wardrobe during {identity} scene",
                f"wardrobe following {identity} transition",
            )
            for allowance in unsafe_allowances:
                with self.subTest(identity=identity, allowance=allowance):
                    errors, _ = self.validate_states(
                        before,
                        after,
                        allowed_changes=[allowance],
                    )
                    self.assertTrue(
                        any("characters.subject.wardrobe" in error for error in errors),
                        errors,
                    )

            for allowance in (
                f"replace {identity} wardrobe",
                f"replace {identity}'s wardrobe",
                f"wardrobe replacement after {identity} shot",
            ):
                with self.subTest(identity=identity, explicit=allowance):
                    errors, warnings = self.validate_states(
                        before,
                        after,
                        allowed_changes=[allowance],
                    )
                    self.assertEqual(errors, [])
                    self.assertEqual(warnings, [])

    def test_explicit_multi_identity_denial_applies_to_exact_named_set(self) -> None:
        for denial in (
            "hero and guide wardrobe must not change",
            "hero or guide wardrobe must not change",
            "hero, and guide wardrobe must not change",
            "hero as well as guide wardrobe must not change",
            "hero, as well as guide wardrobe must not change",
        ):
            with self.subTest(denial=denial):
                before = {
                    "characters": {
                        identity: {
                            "canonical_identity_id": identity,
                            "wardrobe": "old coat",
                        }
                        for identity in ("hero", "guide", "extra")
                    }
                }
                after = {
                    "characters": {
                        identity: {
                            "canonical_identity_id": identity,
                            "wardrobe": "new coat",
                        }
                        for identity in ("hero", "guide", "extra")
                    }
                }
                errors, _ = self.validate_states(
                    before,
                    after,
                    allowed_changes=["wardrobe may change", denial],
                )

                self.assertTrue(any("characters.hero.wardrobe" in e for e in errors), errors)
                self.assertTrue(any("characters.guide.wardrobe" in e for e in errors), errors)
                self.assertFalse(any("characters.extra.wardrobe" in e for e in errors), errors)

    def test_ambiguous_attached_identity_denial_fails_closed(self) -> None:
        before = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "name": "captain",
                    "wardrobe": "red coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "name": "captain",
                    "wardrobe": "black coat",
                },
                "extra": {
                    "canonical_identity_id": "extra",
                    "wardrobe": "white coat",
                },
            }
        }
        after = {
            "characters": {
                key: {**value, "wardrobe": "changed coat"}
                for key, value in before["characters"].items()
            }
        }
        errors, _ = self.validate_states(
            before,
            after,
            allowed_changes=[
                "wardrobe may change",
                "captain wardrobe must not change",
            ],
        )

        for identity in ("hero", "guide", "extra"):
            self.assertTrue(
                any(f"characters.{identity}.wardrobe" in error for error in errors),
                errors,
            )

    def test_identity_in_temporal_context_does_not_scope_denial(self) -> None:
        for denial in (
            "wardrobe stays fixed during hero scene",
            "wardrobe stays fixed after hero shot",
            "wardrobe stays fixed before hero sequence",
            "wardrobe stays fixed following hero transition",
        ):
            with self.subTest(denial=denial):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=["wardrobe may change", denial],
                )

                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

    def test_temporal_identity_context_does_not_scope_positive_waiver(self) -> None:
        for allowance in (
            "wardrobe may change during hero scene",
            "wardrobe may change after hero shot",
            "wardrobe may change before hero sequence",
            "wardrobe may change following hero transition",
        ):
            with self.subTest(allowance=allowance):
                errors, warnings = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=[allowance],
                )

                self.assertEqual(errors, [])
                self.assertEqual(warnings, [])

    def test_explicit_suffix_scope_survives_an_earlier_temporal_identity(self) -> None:
        before = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "red coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "wardrobe": "black coat",
                },
            }
        }
        after = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "blue coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "wardrobe": "white coat",
                },
            }
        }
        temporal_phrases = (
            "after hero shot",
            "before hero sequence",
            "during hero scene",
            "following hero transition",
        )
        for temporal_phrase in temporal_phrases:
            with self.subTest(temporal_phrase=temporal_phrase):
                errors, _ = self.validate_states(
                    before,
                    after,
                    allowed_changes=[
                        f"wardrobe may change {temporal_phrase} for guide"
                    ],
                )
                self.assertTrue(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertFalse(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

        for unsafe_allowance in (
            "wardrobe may change after hero shot for stranger",
            "wardrobe may change after hero shot of guide",
            "wardrobe may change after hero shot guide only",
        ):
            with self.subTest(unsafe_allowance=unsafe_allowance):
                errors, _ = self.validate_states(
                    before,
                    after,
                    allowed_changes=[unsafe_allowance],
                )
                self.assertTrue(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

    def test_attached_identity_beats_unattached_temporal_identity(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "white coat",
                    },
                }
            },
            allowed_changes=[
                "wardrobe may change",
                "hero wardrobe stays fixed during guide scene",
            ],
        )

        self.assertTrue(any("characters.hero.wardrobe" in e for e in errors), errors)
        self.assertFalse(any("characters.guide.wardrobe" in e for e in errors), errors)

    def test_possessive_entity_scope_accepts_straight_and_curly_apostrophes(self) -> None:
        possessive_owners = ("hero's", "hero’s")
        for owner in possessive_owners:
            allowance = f"{owner} wardrobe may change"
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=[allowance],
                )

                self.assertFalse(any("characters.hero.wardrobe" in e for e in errors), errors)
                self.assertTrue(any("characters.guide.wardrobe" in e for e in errors), errors)

        for owner in possessive_owners:
            denial = f"{owner} wardrobe must not change"
            with self.subTest(denial=denial):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=["wardrobe may change", denial],
                )

                self.assertTrue(any("characters.hero.wardrobe" in e for e in errors), errors)
                self.assertFalse(any("characters.guide.wardrobe" in e for e in errors), errors)

    def test_colon_and_em_dash_keep_known_scope_and_reject_unknown_scope(self) -> None:
        for boundary in (":", "—"):
            known = f"wardrobe may change {boundary} only for hero"
            errors, _ = self.validate_states(
                {
                    "characters": {
                        "hero": {"canonical_identity_id": "hero", "wardrobe": "red"},
                        "guide": {"canonical_identity_id": "guide", "wardrobe": "black"},
                    }
                },
                {
                    "characters": {
                        "hero": {"canonical_identity_id": "hero", "wardrobe": "blue"},
                        "guide": {"canonical_identity_id": "guide", "wardrobe": "white"},
                    }
                },
                allowed_changes=[known],
            )
            self.assertFalse(any("characters.hero.wardrobe" in e for e in errors), errors)
            self.assertTrue(any("characters.guide.wardrobe" in e for e in errors), errors)

            scoped_errors, scoped_warnings = self.validate_states(
                {
                    "characters": {
                        "hero": {"canonical_identity_id": "hero", "wardrobe": "red"},
                        "guide": {"canonical_identity_id": "guide", "wardrobe": "black"},
                    }
                },
                {
                    "characters": {
                        "hero": {"canonical_identity_id": "hero", "wardrobe": "blue"},
                        "guide": {"canonical_identity_id": "guide", "wardrobe": "black"},
                    }
                },
                allowed_changes=[
                    f"hero wardrobe may change {boundary} "
                    "guide wardrobe must not change"
                ],
            )
            self.assertEqual(scoped_errors, [])
            self.assertEqual(scoped_warnings, [])

            for unsafe in (
                f"wardrobe may change {boundary} stranger only",
                f"stranger only {boundary} wardrobe may change",
                f"wardrobe may change {boundary} wardrobe must not change",
            ):
                with self.subTest(boundary=boundary, unsafe=unsafe):
                    unsafe_errors, _ = self.validate_states(
                        {"character": {"wardrobe": "red coat"}},
                        {"character": {"wardrobe": "blue coat"}},
                        allowed_changes=[unsafe],
                    )
                    self.assertTrue(
                        any("wardrobe" in error for error in unsafe_errors),
                        unsafe_errors,
                    )

    def test_ascii_and_fullwidth_clause_boundaries_share_safe_scope_rules(self) -> None:
        before = {
            "characters": {
                "hero": {"canonical_identity_id": "hero", "wardrobe": "red"},
                "guide": {"canonical_identity_id": "guide", "wardrobe": "black"},
            }
        }
        after = {
            "characters": {
                "hero": {"canonical_identity_id": "hero", "wardrobe": "blue"},
                "guide": {"canonical_identity_id": "guide", "wardrobe": "white"},
            }
        }
        boundaries = ("!", "?", "！", "？", "。", "；", "：", "，", "．")
        for boundary in boundaries:
            with self.subTest(boundary=boundary, case="known-scope"):
                errors, _ = self.validate_states(
                    before,
                    after,
                    allowed_changes=[f"wardrobe may change{boundary} Only for hero"],
                )
                self.assertFalse(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

            for unsafe_tail in ("stranger only", "must not change"):
                with self.subTest(
                    boundary=boundary,
                    case="unsafe-tail",
                    unsafe_tail=unsafe_tail,
                ):
                    errors, _ = self.validate_states(
                        {"character": {"wardrobe": "red coat"}},
                        {"character": {"wardrobe": "blue coat"}},
                        allowed_changes=[
                            f"wardrobe may change{boundary} {unsafe_tail}"
                        ],
                    )
                    self.assertTrue(any("wardrobe" in error for error in errors), errors)

            with self.subTest(boundary=boundary, case="independent-positive"):
                errors, warnings = self.validate_states(
                    {
                        "character": {"wardrobe": "red coat"},
                        "environment": {"location": "studio-a"},
                    },
                    {
                        "character": {"wardrobe": "blue coat"},
                        "environment": {"location": "studio-b"},
                    },
                    allowed_changes=[
                        f"wardrobe may change{boundary} location may change"
                    ],
                )
                self.assertEqual(errors, [])
                self.assertEqual(warnings, [])

    def test_unknown_possessive_scope_never_becomes_global(self) -> None:
        for allowance in (
            "stranger's wardrobe may change",
            "stranger’s wardrobe may change",
        ):
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {"character": {"wardrobe": "red coat"}},
                    {"character": {"wardrobe": "blue coat"}},
                    allowed_changes=[allowance],
                )
                self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_unknown_bare_scope_residual_never_promotes_a_global_waiver(self) -> None:
        allowances = (
            "wardrobe may change, stranger only",
            "wardrobe may change. stranger only",
            "wardrobe may change\nstranger only",
            "wardrobe may change but stranger only",
            "wardrobe may change however stranger only",
            "wardrobe may change only stranger",
            "stranger only, wardrobe may change",
            "only stranger, wardrobe may change",
            "wardrobe may change, stranger",
        )
        for allowance in allowances:
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {"character": {"wardrobe": "red coat"}},
                    {"character": {"wardrobe": "blue coat"}},
                    allowed_changes=[allowance],
                )

                self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_known_bare_only_qualifier_remains_entity_scoped(self) -> None:
        allowances = (
            "wardrobe may change, hero only",
            "wardrobe may change only hero",
            "hero only, wardrobe may change",
            "only hero, wardrobe may change",
            "wardrobe may change but hero only",
            "wardrobe may change however only hero",
        )
        for allowance in allowances:
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=[allowance],
                )

                self.assertFalse(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

    def test_combined_sentence_newline_keeps_one_known_scope_qualifier(self) -> None:
        for allowance in (
            "wardrobe may change.\nOnly for hero",
            "wardrobe may change.\r\nOnly for hero",
        ):
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=[allowance],
                )

                self.assertFalse(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

    def test_comma_separated_known_qualifier_remains_entity_scoped(self) -> None:
        qualifiers = (
            "for hero",
            "only for hero",
            "specifically for hero",
            "exclusively for hero",
            "only specifically exclusively for hero",
            "but for hero",
            "but only for hero",
            "but specifically for hero",
            "but exclusively for hero",
            "but only specifically exclusively for hero",
        )
        for qualifier in qualifiers:
            allowance = f"wardrobe may change, {qualifier}"
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=[allowance],
                )

                self.assertFalse(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

        for qualifier in qualifiers[5:]:
            allowance = f"wardrobe may change {qualifier}"
            with self.subTest(allowance=allowance):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "hero": {
                                "canonical_identity_id": "hero",
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=[allowance],
                )

                self.assertFalse(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

    def test_qualifier_scope_does_not_leak_into_a_later_field_clause(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                    },
                },
                "environment": {"location": "studio-a"},
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "white coat",
                    },
                },
                "environment": {"location": "studio-b"},
            },
            allowed_changes=["wardrobe may change for hero while location may change"],
        )

        self.assertFalse(any("characters.hero.wardrobe" in error for error in errors), errors)
        self.assertTrue(any("characters.guide.wardrobe" in error for error in errors), errors)
        self.assertFalse(any("location" in error for error in errors), errors)

    def test_later_qualifier_does_not_scope_an_earlier_global_clause(self) -> None:
        errors, warnings = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                        "location": "studio-a",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "white coat",
                        "location": "studio-b",
                    },
                }
            },
            allowed_changes=["wardrobe may change while location may change for guide"],
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_distinct_field_clauses_keep_distinct_entity_scopes(self) -> None:
        errors, warnings = self.validate_states(
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "red coat",
                        "location": "stage-a",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                        "location": "studio-a",
                    },
                }
            },
            {
                "characters": {
                    "hero": {
                        "canonical_identity_id": "hero",
                        "wardrobe": "blue coat",
                        "location": "stage-a",
                    },
                    "guide": {
                        "canonical_identity_id": "guide",
                        "wardrobe": "black coat",
                        "location": "studio-b",
                    },
                }
            },
            allowed_changes=[
                "hero wardrobe may change while guide location may change"
            ],
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_comma_still_splits_independent_global_field_clauses(self) -> None:
        errors, warnings = self.validate_states(
            {
                "character": {"wardrobe": "red coat"},
                "environment": {"location": "studio-a"},
            },
            {
                "character": {"wardrobe": "blue coat"},
                "environment": {"location": "studio-b"},
            },
            allowed_changes=[
                "all wardrobe changes are explicitly allowed, location may change"
            ],
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_explicit_global_waiver_still_applies_to_reordered_entities(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"id": "hero", "wardrobe": "red coat"},
                    {"id": "guide", "wardrobe": "black coat"},
                ]
            },
            {
                "characters": [
                    {"id": "guide", "wardrobe": "white coat"},
                    {"id": "hero", "wardrobe": "blue coat"},
                ]
            },
            allowed_changes=["all wardrobe changes are explicitly allowed"],
        )

        self.assertFalse(any("wardrobe" in error for error in errors), errors)

    def test_fallback_list_identity_replacement_is_rejected(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"id": "hero", "wardrobe": "red coat"},
                    {"id": "guide", "wardrobe": "black coat"},
                ]
            },
            {
                "characters": [
                    {"id": "hero", "wardrobe": "red coat"},
                    {"id": "newcomer", "wardrobe": "black coat"},
                ]
            },
        )

        self.assertTrue(any("fallback list identity" in error for error in errors), errors)

    def test_wrapped_fallback_identity_replacement_is_rejected(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"record": {"id": "hero", "wardrobe": "red coat"}},
                    {"record": {"id": "guide", "wardrobe": "black coat"}},
                ]
            },
            {
                "characters": [
                    {"record": {"id": "guide", "wardrobe": "black coat"}},
                    {"record": {"id": "newcomer", "wardrobe": "red coat"}},
                ]
            },
        )

        self.assertTrue(any("fallback list identity" in error for error in errors), errors)

    def test_renamed_collection_cannot_hide_canonical_replacement(self) -> None:
        errors, _ = self.validate_states(
            {
                "characters": [
                    {"canonical_identity_id": "hero", "wardrobe": "red coat"}
                ]
            },
            {
                "cast": [
                    {"canonical_identity_id": "guide", "wardrobe": "red coat"}
                ]
            },
        )

        self.assertTrue(any("canonical_identity_id inventory" in error for error in errors), errors)

    def test_renamed_collection_keeps_unique_fallback_identity(self) -> None:
        errors, _ = self.validate_states(
            {"characters": [{"id": "hero", "wardrobe": "red coat"}]},
            {"cast": [{"id": "hero", "wardrobe": "blue coat"}]},
        )

        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_denial_word_identity_cannot_reverse_a_denial(self) -> None:
        for identity in (
            "Ban",
            "Deny",
            "Forbid",
            "Prevent",
            "Block",
            "Refuse",
            "No",
            "Without",
        ):
            with self.subTest(identity=identity):
                errors, _ = self.validate_states(
                    {
                        "character": {
                            "canonical_identity_id": identity,
                            "wardrobe": "red coat",
                        }
                    },
                    {
                        "character": {
                            "canonical_identity_id": identity,
                            "wardrobe": "blue coat",
                        }
                    },
                    allowed_changes=[f"{identity} wardrobe change"],
                )

                self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_grammar_word_identities_remain_valid_when_grammatically_attached(self) -> None:
        identities = ("May", "Can", "Allow", "Change", "Alter", "New", "Shift", "Swap")
        for identity in identities:
            with self.subTest(identity=identity, scope="global"):
                errors, warnings = self.validate_states(
                    {
                        "characters": {
                            "target": {
                                "canonical_identity_id": identity,
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "target": {
                                "canonical_identity_id": identity,
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=["wardrobe may change"],
                )
                self.assertEqual(errors, [])
                self.assertEqual(warnings, [])

            with self.subTest(identity=identity, scope="attached"):
                errors, _ = self.validate_states(
                    {
                        "characters": {
                            "target": {
                                "canonical_identity_id": identity,
                                "wardrobe": "red coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "black coat",
                            },
                        }
                    },
                    {
                        "characters": {
                            "target": {
                                "canonical_identity_id": identity,
                                "wardrobe": "blue coat",
                            },
                            "guide": {
                                "canonical_identity_id": "guide",
                                "wardrobe": "white coat",
                            },
                        }
                    },
                    allowed_changes=[f"{identity} wardrobe may change"],
                )
                self.assertFalse(
                    any("characters.target.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

    def test_unknown_grammar_word_serial_identities_fail_closed_before_splitting(self) -> None:
        aliases = {
            "hero": {("str", "hero")},
            "guide": {("str", "guide")},
            "extra": {("str", "extra")},
        }
        slots = (
            ("hero", "wardrobe", "wardrobe"),
            ("guide", "location", "location"),
            ("extra", "product identity", "product_identity"),
        )
        templates = (
            "allow changes to {}",
            "{} may change",
            "preserve {}",
            "{} must not change",
        )
        for unknown in ("May", "Can", "Allow", "Change", "Alter", "New", "Shift", "Swap"):
            for unknown_position in range(len(slots)):
                items = [
                    f"{unknown if index == unknown_position else identity} {field}"
                    for index, (identity, field, _key) in enumerate(slots)
                ]
                serial = ", ".join(items[:-1]) + ", and " + items[-1]
                for template in templates:
                    allowance = template.format(serial)
                    clip = {"allowed_changes": [allowance]}
                    for identity, _field, key in slots:
                        with self.subTest(
                            unknown=unknown,
                            position=unknown_position,
                            template=template,
                            key=key,
                        ):
                            self.assertFalse(
                                continuity_chain_check.has_allowance(
                                    clip,
                                    key,
                                    scope_identity=("str", identity),
                                    identity_aliases=aliases,
                                    alias_widths=(1,),
                                )
                            )

        for allowance in (
            "change wardrobe and change location",
            "alter wardrobe and swap location",
            "allow changes to wardrobe and location",
            "wardrobe and location may change",
        ):
            for key in ("wardrobe", "location"):
                with self.subTest(inverse=allowance, key=key):
                    self.assertTrue(
                        continuity_chain_check.has_allowance(
                            {"allowed_changes": [allowance]},
                            key,
                        )
                    )

    def test_leading_scope_after_hard_boundary_attaches_forward_only(self) -> None:
        observed = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "red coat",
                    "location": "stage-a",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "wardrobe": "black coat",
                    "location": "hall-a",
                },
            }
        }
        planned = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "blue coat",
                    "location": "stage-b",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "wardrobe": "white coat",
                    "location": "hall-b",
                },
            }
        }
        for boundary in (". ", "; ", "\n"):
            with self.subTest(boundary=repr(boundary), scope="known"):
                errors, _ = self.validate_states(
                    observed,
                    planned,
                    allowed_changes=[
                        f"location may change{boundary}Only for hero, wardrobe may change"
                    ],
                )
                self.assertFalse(any(".location" in error for error in errors), errors)
                self.assertFalse(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

            with self.subTest(boundary=repr(boundary), scope="unknown"):
                errors, _ = self.validate_states(
                    observed,
                    planned,
                    allowed_changes=[
                        f"location may change{boundary}Only for stranger, wardrobe may change"
                    ],
                )
                self.assertFalse(any(".location" in error for error in errors), errors)
                self.assertTrue(
                    any("characters.hero.wardrobe" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("characters.guide.wardrobe" in error for error in errors),
                    errors,
                )

    def test_anaphoric_denial_inherits_field_but_keeps_explicit_tail_scope(self) -> None:
        observed = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "red coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "wardrobe": "black coat",
                },
            }
        }
        planned = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "blue coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "wardrobe": "white coat",
                },
            }
        }
        errors, _ = self.validate_states(
            observed,
            planned,
            allowed_changes=[
                "wardrobe may change",
                "hero wardrobe may change; must remain unchanged for guide",
            ],
        )
        self.assertFalse(
            any("characters.hero.wardrobe" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("characters.guide.wardrobe" in error for error in errors),
            errors,
        )

        errors, _ = self.validate_states(
            observed,
            planned,
            allowed_changes=[
                "wardrobe may change",
                "hero wardrobe may change; must remain unchanged for stranger",
            ],
        )
        self.assertTrue(any("characters.hero.wardrobe" in error for error in errors), errors)
        self.assertTrue(any("characters.guide.wardrobe" in error for error in errors), errors)

        errors, _ = self.validate_states(
            observed,
            planned,
            allowed_changes=["wardrobe may change; must remain unchanged"],
        )
        self.assertTrue(any("wardrobe" in error for error in errors), errors)

    def test_json_boolean_and_number_values_are_not_conflated(self) -> None:
        unequal_pairs = (
            (1, True),
            (0, False),
            ({"nested": 1}, {"nested": True}),
            ([1, {"nested": False}], [True, {"nested": 0}]),
        )
        for observed_value, planned_value in unequal_pairs:
            with self.subTest(observed=observed_value, planned=planned_value):
                errors, _ = self.validate_states(
                    {"character": {"wardrobe": observed_value}},
                    {"character": {"wardrobe": planned_value}},
                )
                self.assertTrue(any("wardrobe" in error for error in errors), errors)

        for observed_value, planned_value in (
            (1, 1.0),
            ({"nested": [1, False]}, {"nested": [1.0, False]}),
        ):
            with self.subTest(equal_observed=observed_value, equal_planned=planned_value):
                errors, warnings = self.validate_states(
                    {"character": {"wardrobe": observed_value}},
                    {"character": {"wardrobe": planned_value}},
                )
                self.assertEqual(errors, [])
                self.assertEqual(warnings, [])

    def test_unicode_comma_inventory_preserves_serial_clause_polarity(self) -> None:
        unicode_commas = (
            "\u055d",
            "\u07f8",
            "\u1363",
            "\u1802",
            "\u1808",
            "\u2e32",
            "\u2e34",
            "\u2e41",
            "\ua4fe",
            "\ua60d",
            "\ua6f5",
            "\U0001144d",
        )
        observed = {
            "character": {
                "wardrobe": "red coat",
                "location": "stage-a",
                "product_identity": "watch-a",
            }
        }
        planned = {
            "character": {
                "wardrobe": "blue coat",
                "location": "stage-b",
                "product_identity": "watch-b",
            }
        }
        for comma in unicode_commas:
            with self.subTest(comma=f"U+{ord(comma):04X}", polarity="positive"):
                errors, warnings = self.validate_states(
                    observed,
                    planned,
                    allowed_changes=[
                        f"wardrobe may change{comma} location may change{comma} "
                        "and product identity may change"
                    ],
                )
                self.assertEqual(errors, [])
                self.assertEqual(warnings, [])

            with self.subTest(comma=f"U+{ord(comma):04X}", polarity="denial"):
                errors, _ = self.validate_states(
                    observed,
                    planned,
                    allowed_changes=[
                        "wardrobe may change",
                        "location may change",
                        "product identity may change",
                        f"wardrobe must not change{comma} location must not change{comma} "
                        "and product identity must not change",
                    ],
                )
                for key in ("wardrobe", "location", "product_identity"):
                    self.assertTrue(any(key in error for error in errors), errors)

    def test_mixed_serial_predicates_and_suffix_scopes_stay_local(self) -> None:
        observed = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "red coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "location": "hall-a",
                },
                "extra": {
                    "canonical_identity_id": "extra",
                    "product_identity": "watch-a",
                },
            }
        }
        planned = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "blue coat",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "location": "hall-b",
                },
                "extra": {
                    "canonical_identity_id": "extra",
                    "product_identity": "watch-b",
                },
            }
        }
        errors, _ = self.validate_states(
            observed,
            planned,
            allowed_changes=[
                "hero wardrobe may change, guide location must not change, "
                "extra product identity may change"
            ],
        )
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("characters.guide.location", errors[0])

        for allowance in (
            "allow changes to hero wardrobe, guide location, and extra product identity",
            "hero wardrobe, guide location, and extra product identity may change",
        ):
            with self.subTest(inverse=allowance):
                errors, warnings = self.validate_states(
                    observed,
                    planned,
                    allowed_changes=[allowance],
                )
                self.assertEqual(errors, [])
                self.assertEqual(warnings, [])

        observed_scopes = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "red coat",
                    "location": "stage-a",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "wardrobe": "black coat",
                    "location": "hall-a",
                },
            }
        }
        planned_scopes = {
            "characters": {
                "hero": {
                    "canonical_identity_id": "hero",
                    "wardrobe": "blue coat",
                    "location": "stage-b",
                },
                "guide": {
                    "canonical_identity_id": "guide",
                    "wardrobe": "white coat",
                    "location": "hall-b",
                },
            }
        }
        errors, _ = self.validate_states(
            observed_scopes,
            planned_scopes,
            allowed_changes=["wardrobe for hero and location for guide may change"],
        )
        self.assertFalse(any("characters.hero.wardrobe" in error for error in errors), errors)
        self.assertFalse(any("characters.guide.location" in error for error in errors), errors)
        self.assertTrue(any("characters.guide.wardrobe" in error for error in errors), errors)
        self.assertTrue(any("characters.hero.location" in error for error in errors), errors)

        errors, _ = self.validate_states(
            observed_scopes,
            planned_scopes,
            allowed_changes=[
                "wardrobe may change",
                "location may change",
                "wardrobe for hero and location for guide must not change",
            ],
        )
        self.assertTrue(any("characters.hero.wardrobe" in error for error in errors), errors)
        self.assertTrue(any("characters.guide.location" in error for error in errors), errors)
        self.assertFalse(any("characters.guide.wardrobe" in error for error in errors), errors)
        self.assertFalse(any("characters.hero.location" in error for error in errors), errors)

    def test_unlicensed_modal_role_words_cannot_impersonate_serial_identities(self) -> None:
        aliases = {
            "hero": {("str", "hero")},
            "guide": {("str", "guide")},
            "extra": {("str", "extra")},
        }
        scopes = (
            ("wardrobe", "hero"),
            ("location", "guide"),
            ("product_identity", "extra"),
        )
        role_words = (
            "Must",
            "Will",
            "Is",
            "Are",
            "Be",
            "Being",
            "Of",
            "To",
            "Explicit",
            "Global",
            "Intentional",
            "Intentionally",
            "Or",
            "The",
            "All",
            "This",
        )
        for unknown in role_words:
            clip = {
                "allowed_changes": [
                    f"allow changes to {unknown} wardrobe, guide location, "
                    "and extra product identity"
                ]
            }
            for key, identity in scopes:
                with self.subTest(unknown=unknown, key=key):
                    self.assertFalse(
                        continuity_chain_check.has_allowance(
                            clip,
                            key,
                            scope_identity=("str", identity),
                            identity_aliases=aliases,
                            alias_widths=(1,),
                        )
                    )

        for identity in role_words:
            identity_aliases = {
                identity.casefold(): {("str", identity)},
                "guide": {("str", "guide")},
            }
            with self.subTest(licensed_identity=identity):
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        {"allowed_changes": [f"{identity} wardrobe may change"]},
                        "wardrobe",
                        scope_identity=("str", identity),
                        identity_aliases=identity_aliases,
                        alias_widths=(1,),
                    )
                )
                self.assertFalse(
                    continuity_chain_check.has_allowance(
                        {"allowed_changes": [f"{identity} wardrobe may change"]},
                        "wardrobe",
                        scope_identity=("str", "guide"),
                        identity_aliases=identity_aliases,
                        alias_widths=(1,),
                    )
                )

        for natural_preposition in (
            "allow changes to wardrobe and location",
            "change of wardrobe is allowed",
        ):
            with self.subTest(natural_preposition=natural_preposition):
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        {"allowed_changes": [natural_preposition]},
                        "wardrobe",
                    )
                )
        for valid_global in (
            "wardrobe must change",
            "change wardrobe",
            "change wardrobe and change location",
            "allow changes to wardrobe and location",
        ):
            for key in ("wardrobe", "location"):
                if key not in valid_global:
                    continue
                with self.subTest(valid_global=valid_global, key=key):
                    self.assertTrue(
                        continuity_chain_check.has_allowance(
                            {"allowed_changes": [valid_global]},
                            key,
                        )
                    )

    def test_later_field_qualifier_cannot_leak_backward_across_connector(self) -> None:
        aliases = {
            "hero": {("str", "hero")},
            "guide": {("str", "guide")},
        }
        qualifier_forms = (
            "only hero",
            "hero only",
            "specifically hero",
            "for hero",
            "of hero",
        )
        for connector in ("and", "or", "as well as"):
            for qualifier in qualifier_forms:
                denial = f"wardrobe {connector} {qualifier} location must not change"
                clip = {
                    "allowed_changes": [
                        "wardrobe may change",
                        "location may change",
                        denial,
                    ]
                }
                with self.subTest(connector=connector, qualifier=qualifier):
                    for identity in ("hero", "guide"):
                        self.assertFalse(
                            continuity_chain_check.has_allowance(
                                clip,
                                "wardrobe",
                                scope_identity=("str", identity),
                                identity_aliases=aliases,
                                alias_widths=(1,),
                            )
                        )
                    self.assertFalse(
                        continuity_chain_check.has_allowance(
                            clip,
                            "location",
                            scope_identity=("str", "hero"),
                            identity_aliases=aliases,
                            alias_widths=(1,),
                        )
                    )
                    self.assertTrue(
                        continuity_chain_check.has_allowance(
                            clip,
                            "location",
                            scope_identity=("str", "guide"),
                            identity_aliases=aliases,
                            alias_widths=(1,),
                        )
                    )

    def test_denial_and_preservation_word_identities_keep_denials_local(self) -> None:
        identities = (
            "Ban",
            "Deny",
            "Forbid",
            "Prevent",
            "Block",
            "Refuse",
            "No",
            "Without",
            "Fixed",
            "Preserve",
            "Keep",
        )
        for identity in identities:
            aliases = {
                identity.casefold(): {("str", identity)},
                "guide": {("str", "guide")},
            }
            clip = {
                "allowed_changes": [
                    "wardrobe may change",
                    f"{identity} wardrobe must not change",
                ]
            }
            with self.subTest(identity=identity):
                self.assertFalse(
                    continuity_chain_check.has_allowance(
                        clip,
                        "wardrobe",
                        scope_identity=("str", identity),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        clip,
                        "wardrobe",
                        scope_identity=("str", "guide"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )

    def test_explicit_anaphoric_denials_inherit_only_the_intended_scope(self) -> None:
        aliases = {
            "hero": {("str", "hero")},
            "guide": {("str", "guide")},
        }
        for tail in (
            "change is not allowed",
            "changes are not allowed",
            "change is prohibited",
            "change cannot be permitted",
        ):
            clip = {
                "allowed_changes": [
                    "wardrobe may change",
                    f"hero wardrobe may change; {tail}",
                ]
            }
            with self.subTest(tail=tail):
                self.assertFalse(
                    continuity_chain_check.has_allowance(
                        clip,
                        "wardrobe",
                        scope_identity=("str", "hero"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        clip,
                        "wardrobe",
                        scope_identity=("str", "guide"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )

        for connector in ("and", "or", "as well as"):
            clip = {
                "allowed_changes": [
                    "wardrobe may change",
                    f"hero wardrobe may change {connector} "
                    "must remain unchanged for guide",
                ]
            }
            with self.subTest(connector=connector):
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        clip,
                        "wardrobe",
                        scope_identity=("str", "hero"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )
                self.assertFalse(
                    continuity_chain_check.has_allowance(
                        clip,
                        "wardrobe",
                        scope_identity=("str", "guide"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )

    def test_as_well_as_splits_completed_predicates_but_preserves_shared_lists(self) -> None:
        completed = (
            "wardrobe may change as well as location may change as well as "
            "product identity may change"
        )
        shared = "wardrobe as well as location as well as product identity may change"
        for allowance in (completed, shared):
            for key in ("wardrobe", "location", "product_identity"):
                with self.subTest(allowance=allowance, key=key):
                    self.assertTrue(
                        continuity_chain_check.has_allowance(
                            {"allowed_changes": [allowance]},
                            key,
                        )
                    )

        aliases = {
            "hero": {("str", "hero")},
            "guide": {("str", "guide")},
        }
        scoped = {
            "allowed_changes": [
                "hero wardrobe may change as well as guide location may change"
            ]
        }
        for key, intended, unintended in (
            ("wardrobe", "hero", "guide"),
            ("location", "guide", "hero"),
        ):
            with self.subTest(scoped_key=key):
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        scoped,
                        key,
                        scope_identity=("str", intended),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )
                self.assertFalse(
                    continuity_chain_check.has_allowance(
                        scoped,
                        key,
                        scope_identity=("str", unintended),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )

    def test_completed_or_after_comma_is_not_an_identity_role(self) -> None:
        allowance = (
            "wardrobe may change, location may change or "
            "product identity may change"
        )
        for key in ("wardrobe", "location", "product_identity"):
            with self.subTest(key=key):
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        {"allowed_changes": [allowance]},
                        key,
                    )
                )

    def test_non_string_waiver_items_fail_closed_at_runtime(self) -> None:
        malformed_values = ({"wardrobe": "must not change"}, True, 1, None)
        for field in ("allowed_changes", "accepted_deviations", "continuity_breaks"):
            for malformed in malformed_values:
                with self.subTest(field=field, malformed=malformed):
                    clip = {"allowed_changes": ["wardrobe may change"]}
                    clip[field] = [malformed, "wardrobe may change"]
                    self.assertFalse(
                        continuity_chain_check.has_allowance(
                            clip,
                            "wardrobe",
                        )
                    )
            with self.subTest(field=field, malformed_container=True):
                clip = {"allowed_changes": ["wardrobe may change"]}
                clip[field] = "wardrobe may change"
                self.assertFalse(
                    continuity_chain_check.has_allowance(
                        clip,
                        "wardrobe",
                    )
                )

        self.assertFalse(
            continuity_chain_check.has_allowance(
                {
                    "allowed_changes": ["wardrobe may change"],
                    "transition_in": {"not": "text"},
                },
                "wardrobe",
            )
        )

    def test_repeated_grammar_word_alias_does_not_consume_predicate(self) -> None:
        aliases = {
            "may change": {("str", "May Change")},
            "guide": {("str", "guide")},
        }
        clip = {"allowed_changes": ["wardrobe for May Change may change"]}

        self.assertTrue(
            continuity_chain_check.has_allowance(
                clip,
                "wardrobe",
                scope_identity=("str", "May Change"),
                identity_aliases=aliases,
                alias_widths=(2, 1),
            )
        )
        self.assertFalse(
            continuity_chain_check.has_allowance(
                clip,
                "wardrobe",
                scope_identity=("str", "guide"),
                identity_aliases=aliases,
                alias_widths=(2, 1),
            )
        )

    def test_fieldless_leading_scope_denial_stays_independent(self) -> None:
        aliases = {
            "hero": {("str", "hero")},
            "guide": {("str", "guide")},
        }
        for denial in (
            "for guide must remain unchanged",
            "guide must remain unchanged",
            "must remain unchanged for guide",
        ):
            clip = {
                "allowed_changes": [f"hero wardrobe may change; {denial}"]
            }
            with self.subTest(denial=denial):
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        clip,
                        "wardrobe",
                        scope_identity=("str", "hero"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )
                self.assertFalse(
                    continuity_chain_check.has_allowance(
                        clip,
                        "wardrobe",
                        scope_identity=("str", "guide"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )

        grammar_aliases = {
            "may": {("str", "May")},
            "guide": {("str", "guide")},
        }
        pure_suffix = {"allowed_changes": ["wardrobe may change; only for May"]}
        self.assertTrue(
            continuity_chain_check.has_allowance(
                pure_suffix,
                "wardrobe",
                scope_identity=("str", "May"),
                identity_aliases=grammar_aliases,
                alias_widths=(1,),
            )
        )
        self.assertFalse(
            continuity_chain_check.has_allowance(
                pure_suffix,
                "wardrobe",
                scope_identity=("str", "guide"),
                identity_aliases=grammar_aliases,
                alias_widths=(1,),
            )
        )

    def test_shared_prefix_as_well_as_matches_and(self) -> None:
        for connector in ("and", "as well as"):
            allowance = f"may change wardrobe {connector} location"
            for key in ("wardrobe", "location"):
                with self.subTest(connector=connector, key=key):
                    self.assertTrue(
                        continuity_chain_check.has_allowance(
                            {"allowed_changes": [allowance]},
                            key,
                        )
                    )

        mixed = {
            "allowed_changes": [
                "may change wardrobe as well as location must remain unchanged"
            ]
        }
        self.assertTrue(
            continuity_chain_check.has_allowance(mixed, "wardrobe")
        )
        self.assertFalse(
            continuity_chain_check.has_allowance(mixed, "location")
        )

    def test_anaphoric_grammar_alias_requires_explicit_scope(self) -> None:
        for identity in ("Change", "Must", "No", "Cannot"):
            aliases = {
                "hero": {("str", "hero")},
                identity.casefold(): {("str", identity)},
            }
            anaphoric = {
                "allowed_changes": [
                    "wardrobe may change",
                    f"hero wardrobe may change; {identity} is not allowed",
                ]
            }
            explicit = {
                "allowed_changes": [
                    "wardrobe may change",
                    f"hero wardrobe may change; for {identity} must remain unchanged",
                ]
            }
            with self.subTest(identity=identity, grammar_tail=True):
                self.assertFalse(
                    continuity_chain_check.has_allowance(
                        anaphoric,
                        "wardrobe",
                        scope_identity=("str", "hero"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        anaphoric,
                        "wardrobe",
                        scope_identity=("str", identity),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )
            with self.subTest(identity=identity, explicit_scope=True):
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        explicit,
                        "wardrobe",
                        scope_identity=("str", "hero"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )
                self.assertFalse(
                    continuity_chain_check.has_allowance(
                        explicit,
                        "wardrobe",
                        scope_identity=("str", identity),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )

    def test_field_tokens_override_colliding_identity_aliases(self) -> None:
        aliases = {
            "identity": {("str", "Identity")},
            "phase": {("str", "Phase")},
            "state": {("str", "State")},
            "guide": {("str", "guide")},
        }
        collision_fields = {
            "product_identity": "Identity",
            "canonical_identity_id": "Identity",
            "vehicle_identity": "Identity",
            "camera_phase": "Phase",
            "lighting_phase": "Phase",
            "audio_phase": "Phase",
            "focus_state": "State",
            "emotional_state": "State",
        }
        for field, colliding_identity in collision_fields.items():
            phrase = field.replace("_", " ")
            global_clip = {"allowed_changes": [f"{phrase} may change"]}
            scoped_clip = {"allowed_changes": [f"guide {phrase} may change"]}
            with self.subTest(field=field, scope="global"):
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        global_clip,
                        field,
                        scope_identity=("str", "guide"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )
            with self.subTest(field=field, scope="guide"):
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        scoped_clip,
                        field,
                        scope_identity=("str", "guide"),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )
                self.assertFalse(
                    continuity_chain_check.has_allowance(
                        scoped_clip,
                        field,
                        scope_identity=("str", colliding_identity),
                        identity_aliases=aliases,
                        alias_widths=(1,),
                    )
                )

        literal_identity = {"allowed_changes": ["Identity wardrobe may change"]}
        self.assertTrue(
            continuity_chain_check.has_allowance(
                literal_identity,
                "wardrobe",
                scope_identity=("str", "Identity"),
                identity_aliases=aliases,
                alias_widths=(1,),
            )
        )
        self.assertFalse(
            continuity_chain_check.has_allowance(
                literal_identity,
                "wardrobe",
                scope_identity=("str", "guide"),
                identity_aliases=aliases,
                alias_widths=(1,),
            )
        )

    def test_full_field_phrase_alias_is_preserved_only_as_entity_prefix(self) -> None:
        cases = (
            ("product_identity", "Product Identity"),
            ("camera_phase", "Camera Phase"),
            ("focus_state", "Focus State"),
        )
        guide = ("str", "guide")
        for field, display_alias in cases:
            aliases = {
                display_alias.casefold(): {("str", display_alias)},
                "guide": {guide},
            }
            field_phrase = field.replace("_", " ")
            global_clip = {"allowed_changes": [f"{field_phrase} may change"]}
            scoped_clip = {
                "allowed_changes": [
                    f"{display_alias} {field_phrase} may change"
                ]
            }
            possessive_clip = {
                "allowed_changes": [
                    f"{display_alias}'s {field_phrase} may change"
                ]
            }
            with self.subTest(field=field, form="global"):
                self.assertTrue(
                    continuity_chain_check.has_allowance(
                        global_clip,
                        field,
                        scope_identity=guide,
                        identity_aliases=aliases,
                        alias_widths=(2, 1),
                    )
                )
            for form, clip in (("prefix", scoped_clip), ("possessive", possessive_clip)):
                with self.subTest(field=field, form=form):
                    self.assertTrue(
                        continuity_chain_check.has_allowance(
                            clip,
                            field,
                            scope_identity=("str", display_alias),
                            identity_aliases=aliases,
                            alias_widths=(2, 1),
                        )
                    )
                    self.assertFalse(
                        continuity_chain_check.has_allowance(
                            clip,
                            field,
                            scope_identity=guide,
                            identity_aliases=aliases,
                            alias_widths=(2, 1),
                        )
                    )

    def test_large_integer_json_returns_diagnostics_in_validate_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "examples" / "huge-project-state.json"
            path.parent.mkdir()
            path.write_text(
                '{"clips": [], "huge": ' + "9" * 5000 + "}",
                encoding="utf-8",
            )

            errors, warnings = continuity_chain_check.validate(path, root)
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/continuity_chain_check.py",
                    str(root),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertTrue(any("invalid JSON" in error for error in errors), errors)
        self.assertEqual(warnings, [])
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("invalid JSON", result.stdout)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_varied_alias_widths_and_candidate_overflow_are_bounded(self) -> None:
        width_count = continuity_chain_check.MAX_WAIVER_TOKENS
        aliases = {
            " ".join(["a"] * width): {("str", f"identity-{width}")}
            for width in range(1, width_count + 1)
        }
        tokens = ["a"] * width_count
        started = time.perf_counter()
        spans, ambiguous = continuity_chain_check.identity_token_spans(
            tokens,
            aliases,
            tuple(range(width_count, 0, -1)),
        )
        matcher_elapsed = time.perf_counter() - started

        self.assertTrue(ambiguous)
        self.assertEqual(
            spans,
            [
                (
                    0,
                    width_count,
                    {continuity_chain_check.IDENTITY_MATCH_OVERFLOW},
                )
            ],
        )
        self.assertLess(
            matcher_elapsed,
            2.0,
            f"varied-width matcher took {matcher_elapsed:.3f}s",
        )

        public_width_count = 400
        public_aliases = {
            " ".join(["a"] * width): {("str", f"identity-{width}")}
            for width in range(1, public_width_count + 1)
        }
        allowance = " ".join(
            ["a"] * public_width_count + ["wardrobe", "may", "change"]
        )
        started = time.perf_counter()
        public_result = continuity_chain_check.has_allowance(
            {"allowed_changes": [allowance]},
            "wardrobe",
            scope_identity=("str", f"identity-{public_width_count}"),
            identity_aliases=public_aliases,
            alias_widths=tuple(range(public_width_count, 0, -1)),
        )
        public_elapsed = time.perf_counter() - started

        self.assertFalse(public_result)
        self.assertLess(
            public_elapsed,
            2.0,
            f"public varied-width parse took {public_elapsed:.3f}s",
        )

    def test_comma_heavy_under_cap_list_is_linear_and_preserved(self) -> None:
        allowance = ", ".join(
            ["wardrobe"] * 499 + ["and wardrobe may change"]
        )
        self.assertLessEqual(
            len(continuity_chain_check.normalize_phrase(allowance).split()),
            continuity_chain_check.MAX_WAIVER_TOKENS,
        )
        started = time.perf_counter()
        result = continuity_chain_check.has_allowance(
            {"allowed_changes": [allowance]},
            "wardrobe",
        )
        elapsed = time.perf_counter() - started

        self.assertTrue(result)
        self.assertLess(elapsed, 2.0, f"500-item comma list took {elapsed:.3f}s")

        independent = {
            "allowed_changes": [
                "wardrobe may change, location must remain unchanged"
            ]
        }
        self.assertTrue(
            continuity_chain_check.has_allowance(independent, "wardrobe")
        )
        self.assertFalse(
            continuity_chain_check.has_allowance(independent, "location")
        )

    def test_deep_json_equality_is_iterative_and_budgeted(self) -> None:
        observed_value: object = "same"
        planned_value: object = "same"
        for _ in range(400):
            observed_value = [observed_value]
            planned_value = [planned_value]

        self.assertTrue(
            continuity_chain_check.json_values_equal(
                observed_value,
                planned_value,
            )
        )

        self.assertFalse(
            continuity_chain_check.json_values_equal(
                [0] * (continuity_chain_check.MAX_JSON_COMPARE_NODES + 1),
                [0] * (continuity_chain_check.MAX_JSON_COMPARE_NODES + 1),
            )
        )

    def test_json_load_recursion_error_returns_a_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "project-state.json"
            path.write_text(
                '{"clips": [], "nested": ' + "[" * 200 + "0" + "]" * 200 + "}",
                encoding="utf-8",
            )
            errors, warnings = continuity_chain_check.validate(path, root)

        self.assertTrue(any("maximum JSON nesting depth" in error for error in errors), errors)
        self.assertEqual(warnings, [])

    def test_large_identity_alias_inventory_stays_within_a_bounded_runtime(self) -> None:
        aliases = {
            f"actor {index}": {("str", f"actor {index}")}
            for index in range(300)
        }
        clip = {
            "allowed_changes": [
                "allow changes to actor 1 wardrobe, actor 2 location, "
                "and actor 3 product identity"
            ]
        }
        started = time.perf_counter()
        results = [
            continuity_chain_check.has_allowance(
                clip,
                key,
                scope_identity=("str", f"actor {identity_index}"),
                identity_aliases=aliases,
                alias_widths=(2,),
            )
            for _ in range(60)
            for key, identity_index in (
                ("wardrobe", 1),
                ("location", 2),
                ("product_identity", 3),
            )
        ]
        long_serial_tokens = continuity_chain_check.normalize_phrase(
            " and ".join(
                f"actor {index} wardrobe" for index in range(120)
            )
            + " may change"
        ).split()
        identity_indexes = continuity_chain_check.identity_indexes_for_tokens(
            long_serial_tokens,
            aliases,
            (2,),
        )
        long_serial_clip = {
            "allowed_changes": [
                " and ".join(
                    f"actor {index} wardrobe" for index in range(150)
                )
                + " may change"
            ]
        }
        long_serial_started = time.perf_counter()
        long_serial_result = continuity_chain_check.has_allowance(
            long_serial_clip,
            "wardrobe",
            scope_identity=("str", "actor 0"),
            identity_aliases=aliases,
            alias_widths=(2,),
        )
        long_serial_elapsed = time.perf_counter() - long_serial_started
        elapsed = time.perf_counter() - started

        self.assertTrue(all(results))
        self.assertEqual(len(identity_indexes), 240)
        self.assertFalse(long_serial_result)
        self.assertLess(
            long_serial_elapsed,
            3.0,
            f"150-item serial parser took {long_serial_elapsed:.3f}s",
        )
        self.assertLess(elapsed, 8.0, f"bounded parser took {elapsed:.3f}s")

    def test_oversized_waiver_fails_closed_before_semantic_parsing(self) -> None:
        oversized = " ".join(
            ["wardrobe"]
            + ["and wardrobe"] * continuity_chain_check.MAX_WAIVER_TOKENS
            + ["may change"]
        )
        started = time.perf_counter()
        result = continuity_chain_check.has_allowance(
            {"allowed_changes": [oversized]},
            "wardrobe",
        )
        elapsed = time.perf_counter() - started

        self.assertFalse(result)
        self.assertLess(elapsed, 1.0, f"oversized waiver took {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()

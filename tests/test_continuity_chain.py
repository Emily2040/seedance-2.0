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
            self.assertTrue(any("cannot load" in error for error in errors), errors)
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
        self.assertTrue(any("向导.wardrobe" in error for error in errors), errors)

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


if __name__ == "__main__":
    unittest.main()

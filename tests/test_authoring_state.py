from __future__ import annotations

import copy
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import project_state_check  # noqa: E402


NARRATIVE_FIELDS = {
    "dramatic_function",
    "turn",
    "pov",
    "power_shift",
    "hidden_want_objective",
    "obstacle_tactic",
    "subtext_contradiction",
    "visible_suppressed_behavior",
    "non_transferable_detail",
    "non_transferable_detail_provenance",
    "non_transferable_detail_source",
    "stock_solution_refused",
    "value_before",
    "value_after",
    "prompt_carriers",
}
NON_NARRATIVE_FIELDS = {"utility_intent", "non_narrative_refusal"}
NARRATIVE_TEXT_FIELDS = (
    "dramatic_function",
    "turn",
    "pov",
    "power_shift",
    "hidden_want_objective",
    "obstacle_tactic",
    "subtext_contradiction",
    "visible_suppressed_behavior",
    "non_transferable_detail",
    "stock_solution_refused",
    "value_before",
    "value_after",
)
INVISIBLE_AUTHORING_TEXT_VALUES = (
    "",
    " \t\u00a0",
    "\u200b\u2060\ufeff",
    "\u034f\ufe0f",
    "\u2800\u3164\uffa0",
    "\U000110bd",
    "\U000110cd",
    "\U00013430",
    "\U0001bca0\U0001d173",
    " \U000e0001 ",
    "...",
    "!!!",
    "，。！？",
    "—–",
)
CAPSULE_FIELDS = (
    "DRAMATIC FUNCTION:",
    "TURN:",
    "POV:",
    "POWER SHIFT:",
    "HIDDEN WANT/OBJECTIVE:",
    "OBSTACLE/TACTIC:",
    "SUBTEXT/CONTRADICTION:",
    "VISIBLE SUPPRESSED BEHAVIOR:",
    "NON-TRANSFERABLE DETAIL:",
    "NON-TRANSFERABLE DETAIL PROVENANCE:",
    "NON-TRANSFERABLE DETAIL SOURCE:",
    "STOCK SOLUTION REFUSED:",
    "VALUE BEFORE:",
    "VALUE AFTER:",
    "NEXT CLIP VISIBLE CARRIERS:",
)


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def current_projects() -> dict[str, dict]:
    selected: dict[str, tuple[tuple[int, int, str], dict]] = {}
    for path in project_state_check.sequence_paths(ROOT):
        project = json.loads(path.read_text(encoding="utf-8"))
        project_id = project["project_id"]
        candidate = (project_state_check.project_version(project, path), project)
        if project_id not in selected or candidate[0] > selected[project_id][0]:
            selected[project_id] = candidate
    return {project_id: project for project_id, (_, project) in selected.items()}


def protected_historical_ledger() -> dict[tuple[str, str, int, int], dict]:
    errors: list[str] = []
    ledger = project_state_check.load_protected_provenance_ledger(ROOT, errors)
    if errors or ledger is None:
        raise AssertionError(errors)
    return ledger


class AuthoringStateFixtureTests(unittest.TestCase):
    def test_schema_and_strict_field_contracts_stay_in_static_parity(self) -> None:
        project_schema = load_json("schemas/project-state.schema.json")
        contract_schema = load_json("schemas/clip-contract.schema.json")
        for definition in (
            "authoring_state_provenance",
            "authoring_state",
            "narrative_authoring_state",
            "non_narrative_authoring_state",
        ):
            self.assertEqual(
                project_schema["$defs"][definition],
                contract_schema["$defs"][definition],
            )
        narrative = project_schema["$defs"]["narrative_authoring_state"]
        non_narrative = project_schema["$defs"]["non_narrative_authoring_state"]
        self.assertEqual(set(narrative["required"]), NARRATIVE_FIELDS)
        self.assertEqual(set(narrative["properties"]), NARRATIVE_FIELDS)
        self.assertEqual(set(non_narrative["required"]), NON_NARRATIVE_FIELDS)
        self.assertEqual(set(non_narrative["properties"]), NON_NARRATIVE_FIELDS)
        authoring_conditionals = [
            conditional
            for conditional in contract_schema["allOf"]
            if "authoring_state" in json.dumps(conditional["if"], sort_keys=True)
            or "directors_read_lane" in json.dumps(conditional["if"], sort_keys=True)
        ]
        self.assertEqual(len(authoring_conditionals), 3)
        self.assertTrue(
            all(
                "authoring_state_provenance"
                in conditional["then"].get("required", [])
                for conditional in authoring_conditionals
            )
        )

    def test_shipped_mixed_lane_fixture_is_narrative_utility_narrative(self) -> None:
        project = load_json("examples/sequence-mixed-lane/project-state.json")
        self.assertEqual(
            [clip["directors_read_lane"] for clip in project["clips"]],
            ["narrative", "non_narrative", "narrative"],
        )
        self.assertEqual(
            project["clips"][0]["authoring_state"]["value_after"],
            project["clips"][2]["authoring_state"]["value_before"],
        )

    def test_every_explicit_lane_carries_its_complete_canonical_record(self) -> None:
        for path in project_state_check.sequence_paths(ROOT):
            project = json.loads(path.read_text(encoding="utf-8"))
            if project.get("project_mode") != "sequence_project":
                continue
            for clip in project["clips"]:
                with self.subTest(path=path.relative_to(ROOT), clip=clip["clip_id"]):
                    lane = clip.get("directors_read_lane")
                    state = clip.get("authoring_state")
                    self.assertIn(lane, {"narrative", "non_narrative"})
                    self.assertIsInstance(state, dict)
                    expected = NARRATIVE_FIELDS if lane == "narrative" else NON_NARRATIVE_FIELDS
                    self.assertEqual(expected, set(state))
                    self.assertNotIn("irreversible_cost", state)
                    for field in expected - {
                        "prompt_carriers", "non_transferable_detail_source",
                    }:
                        self.assertIsInstance(state[field], str)
                        self.assertTrue(state[field].strip())
                    if lane == "narrative":
                        self.assertNotEqual(state["value_before"].casefold(), state["value_after"].casefold())
                        self.assertIn(
                            state["non_transferable_detail_provenance"],
                            {"source_bound", "authored_choice"},
                        )
                        if state["non_transferable_detail_provenance"] == "authored_choice":
                            self.assertIsNone(state["non_transferable_detail_source"])
                        else:
                            self.assertIsInstance(state["non_transferable_detail_source"], str)
                        self.assertTrue(state["prompt_carriers"])

    def test_nearest_narrative_ancestor_value_handoff(self) -> None:
        for path in project_state_check.sequence_paths(ROOT):
            project = json.loads(path.read_text(encoding="utf-8"))
            clips = {clip["clip_id"]: clip for clip in project["clips"]}
            for clip in project["clips"]:
                if clip.get("directors_read_lane") != "narrative":
                    continue
                ancestor = project_state_check.nearest_narrative_ancestor(clip, clips)
                if ancestor is None:
                    continue
                with self.subTest(path=path.relative_to(ROOT), clip=clip["clip_id"]):
                    self.assertEqual(
                        ancestor["authoring_state"]["value_after"],
                        clip["authoring_state"]["value_before"],
                    )

    def test_contracts_carry_complete_lane_records(self) -> None:
        for path in sorted((ROOT / "examples").rglob("*contract.json")):
            contract = json.loads(path.read_text(encoding="utf-8"))
            lane = contract["directors_read_lane"]
            expected = NARRATIVE_FIELDS if lane == "narrative" else NON_NARRATIVE_FIELDS
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertEqual(expected, set(contract["authoring_state"]))
                provenance = contract["authoring_state_provenance"]
                self.assertEqual(provenance["project_id"], contract["project_id"])
                self.assertEqual(provenance["clip_id"], contract["clip_id"])
                self.assertEqual(
                    provenance["authoring_state_sha256"],
                    project_state_check.authoring_state_digest(contract["authoring_state"]),
                )

    def test_current_contract_matches_current_project_but_history_stays_planned(self) -> None:
        projects = current_projects()
        airport = projects["seq_airport_arrival"]
        clips = {clip["clip_id"]: clip for clip in airport["clips"]}

        current = load_json("examples/sequence-airport-arrival/clip-02-continuation-contract.json")
        self.assertEqual(current["status"], "ready")
        self.assertEqual(current["authoring_state"], clips["clip_02"]["authoring_state"])

        historical = load_json("examples/sequence-airport-arrival/clip-01-contract.json")
        self.assertEqual(historical["status"], "accepted_with_deviation")
        self.assertEqual(
            historical["planned_end_state"]["summary"],
            "traveler beside open rear car door",
        )
        self.assertEqual(
            clips["clip_01"]["planned_end_state"]["character"]["location"],
            "beside open rear car door",
        )
        self.assertNotEqual(historical["authoring_state"], clips["clip_01"]["authoring_state"])
        self.assertNotEqual(
            clips["clip_01"]["planned_end_state"],
            clips["clip_01"]["observed_end_state"],
        )

    def test_capsule_preserves_complete_next_clip_handoff(self) -> None:
        capsule = (ROOT / "examples/sequence-airport-arrival/sequence-plan.md").read_text(
            encoding="utf-8"
        )
        for field in CAPSULE_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, capsule)
        self.assertNotIn("IRREVERSIBLE COST:", capsule)
        values = {
            line.split(":", 1)[0]: line.split(":", 1)[1].strip()
            for line in capsule.splitlines()
            if ":" in line
        }
        state = load_json(
            "examples/sequence-airport-arrival/clip-02-continuation-contract.json"
        )["authoring_state"]
        labels = {
            "DRAMATIC FUNCTION": "dramatic_function",
            "TURN": "turn",
            "POV": "pov",
            "POWER SHIFT": "power_shift",
            "HIDDEN WANT/OBJECTIVE": "hidden_want_objective",
            "OBSTACLE/TACTIC": "obstacle_tactic",
            "SUBTEXT/CONTRADICTION": "subtext_contradiction",
            "VISIBLE SUPPRESSED BEHAVIOR": "visible_suppressed_behavior",
            "NON-TRANSFERABLE DETAIL": "non_transferable_detail",
            "NON-TRANSFERABLE DETAIL PROVENANCE": "non_transferable_detail_provenance",
            "NON-TRANSFERABLE DETAIL SOURCE": "non_transferable_detail_source",
            "STOCK SOLUTION REFUSED": "stock_solution_refused",
            "VALUE BEFORE": "value_before",
            "VALUE AFTER": "value_after",
        }
        for label, field in labels.items():
            with self.subTest(label=label):
                expected = "null" if state[field] is None else state[field]
                self.assertEqual(values[label], expected)
        self.assertEqual(
            values["NEXT CLIP VISIBLE CARRIERS"],
            " | ".join(state["prompt_carriers"]),
        )

    def test_example_prompts_compile_exact_carriers_without_internal_labels(self) -> None:
        example = ROOT / "examples/sequence-airport-arrival"
        for contract_name in ("clip-01-contract.json", "clip-02-continuation-contract.json"):
            contract = json.loads((example / contract_name).read_text(encoding="utf-8"))
            prompt_name = f"{contract['clip_id'].replace('_', '-')}-prompt.md"
            prompt = (example / prompt_name).read_text(encoding="utf-8")
            with self.subTest(prompt=prompt_name):
                self.assertEqual(
                    project_state_check.compiled_prompt_errors(
                        prompt,
                        contract["authoring_state"],
                        lane=contract["directors_read_lane"],
                    ),
                    [],
                )

    def test_terminal_project_only_records_are_outside_the_narrow_ledger_claim(self) -> None:
        terminal_project_clips = {
            (project_id, clip["clip_id"])
            for project_id, project in current_projects().items()
            for clip in project["clips"]
            if clip.get("directors_read_lane") in project_state_check.DIRECTORS_READ_LANES
            and clip.get("status") in project_state_check.HISTORICAL_CONTRACT_STATUSES
        }
        terminal_contracts = {
            (contract["project_id"], contract["clip_id"])
            for path in (ROOT / "examples").rglob("*contract*.json")
            for contract in [json.loads(path.read_text(encoding="utf-8"))]
            if contract.get("directors_read_lane") in project_state_check.DIRECTORS_READ_LANES
            and contract.get("status") in project_state_check.HISTORICAL_CONTRACT_STATUSES
        }
        self.assertEqual(len(terminal_project_clips), 4)
        self.assertEqual(len(terminal_project_clips - terminal_contracts), 3)
        scope = (ROOT / "references/sequence-project-state.md").read_text(encoding="utf-8")
        self.assertIn(
            "terminal clip record that exists only inside a project-state fixture is **not** "
            "independently protected by this contract ledger",
            scope,
        )


class AuthoringStateAdversarialTests(unittest.TestCase):
    def validate_project_copy(self, project: dict, *, strict: bool) -> list[str]:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            path = Path(tmp) / "project-state.json"
            path.write_text(json.dumps(project), encoding="utf-8")
            clips_by_id = {
                clip.get("clip_id"): clip
                for clip in project.get("clips", [])
                if isinstance(clip, dict) and isinstance(clip.get("clip_id"), str)
            }
            for index, history in enumerate(project.get("take_history", [])):
                if not isinstance(history, dict):
                    continue
                clip = clips_by_id.get(history.get("clip_id"), {})
                review = {
                    "project_id": project.get("project_id"),
                    "clip_id": history.get("clip_id"),
                    "take_id": history.get("take_id"),
                    "source_status": "reviewed",
                    "verdict": history.get("verdict"),
                    "observed_start_state": (
                        clip.get("observed_start_state")
                        if isinstance(clip.get("observed_start_state"), dict)
                        else {}
                    ),
                    "observed_end_state": (
                        clip.get("observed_end_state")
                        if isinstance(clip.get("observed_end_state"), dict)
                        else {}
                    ),
                    "completed_beats": [],
                    "incomplete_beats": [],
                    "unexpected_completed_beats": [],
                    "continuity_breaks": [],
                    "accepted_deviations": [],
                    "observation_confidence": "high",
                    "uncertainties": [],
                    "requires_user_confirmation": False,
                }
                (Path(tmp) / f"{index:04d}-take-review.json").write_text(
                    json.dumps(review), encoding="utf-8"
                )
            return project_state_check.validate_project(path, ROOT, strict=strict)

    def test_runtime_rejects_invisible_and_punctuation_only_authoring_text(self) -> None:
        for value in INVISIBLE_AUTHORING_TEXT_VALUES:
            with self.subTest(value=value):
                self.assertFalse(project_state_check.has_visible_text(value))

    def test_strict_requires_record_for_either_explicit_lane(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        for lane in ("narrative", "non_narrative"):
            probe = copy.deepcopy(project)
            probe["clips"][0]["directors_read_lane"] = lane
            probe["clips"][0].pop("authoring_state", None)
            errors = self.validate_project_copy(probe, strict=True)
            with self.subTest(lane=lane):
                self.assertTrue(any("missing authoring_state" in error for error in errors), errors)

    def test_strict_sequence_requires_valid_explicit_lane(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        del project["clips"][0]["directors_read_lane"]
        errors = self.validate_project_copy(project, strict=True)
        self.assertTrue(any("directors_read_lane" in error for error in errors), errors)

        project["clips"][0]["directors_read_lane"] = "sometimes_narrative"
        errors = self.validate_project_copy(project, strict=True)
        self.assertTrue(any("directors_read_lane" in error for error in errors), errors)

    def test_explicit_invalid_lane_fails_even_without_strict_mode(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        clip = project["clips"][0]
        clip["directors_read_lane"] = "sometimes_narrative"
        clip.pop("authoring_state", None)
        clip.pop("contract_authoring_state_snapshots", None)
        errors = self.validate_project_copy(project, strict=False)
        self.assertTrue(any("directors_read_lane" in error for error in errors), errors)
        self.assertTrue(any("missing authoring_state" in error for error in errors), errors)

        contract = load_json(
            "examples/sequence-airport-arrival/clip-02-continuation-contract.json"
        )
        current_clip = copy.deepcopy(project["clips"][1])
        for record in (contract, current_clip):
            record["directors_read_lane"] = None
            record.pop("authoring_state", None)
            record.pop("authoring_state_provenance", None)
            record.pop("contract_authoring_state_snapshots", None)
        errors = []
        project_state_check.validate_contract(
            contract,
            "invalid explicit contract lane",
            errors,
            strict=False,
            current_clip=current_clip,
            prompt=None,
            historical_ledger=protected_historical_ledger(),
        )
        self.assertTrue(any("directors_read_lane" in error for error in errors), errors)
        self.assertTrue(any("missing authoring_state" in error for error in errors), errors)
        self.assertTrue(any("missing authoring_state_provenance" in error for error in errors), errors)

    def test_default_check_accepts_legacy_sequence_without_lane_or_state(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        for clip in project["clips"]:
            clip.pop("authoring_state", None)
            clip.pop("directors_read_lane", None)
            clip.pop("contract_authoring_state_snapshots", None)
        self.assertEqual(self.validate_project_copy(project, strict=False), [])

    def test_default_contract_with_prompt_accepts_legacy_absence(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        clip = next(item for item in project["clips"] if item["clip_id"] == "clip_02")
        contract = load_json(
            "examples/sequence-airport-arrival/clip-02-continuation-contract.json"
        )
        for record in (clip, contract):
            record.pop("authoring_state", None)
            record.pop("directors_read_lane", None)
            record.pop("authoring_state_provenance", None)
            record.pop("contract_authoring_state_snapshots", None)
        prompt = (ROOT / "examples/sequence-airport-arrival/clip-02-prompt.md").read_text(
            encoding="utf-8"
        )
        errors: list[str] = []
        project_state_check.validate_contract(
            contract,
            "legacy contract",
            errors,
            strict=False,
            current_clip=clip,
            prompt=prompt,
            historical_ledger=protected_historical_ledger(),
        )
        self.assertEqual(errors, [])

        clip["directors_read_lane"] = "narrative"
        contract["directors_read_lane"] = "narrative"
        errors = []
        project_state_check.validate_contract(
            contract,
            "partially migrated contract",
            errors,
            strict=False,
            current_clip=clip,
            prompt=prompt,
            historical_ledger=protected_historical_ledger(),
        )
        self.assertTrue(any("missing authoring_state" in error for error in errors), errors)

    def test_historical_terminal_contract_does_not_match_current_repair_status(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        current_clip = copy.deepcopy(project["clips"][0])
        current_clip["status"] = "repair"
        contract = load_json(
            "examples/sequence-airport-arrival/clip-01-contract.json"
        )
        prompt = (
            ROOT / "examples/sequence-airport-arrival/clip-01-prompt.md"
        ).read_text(encoding="utf-8")
        errors: list[str] = []

        project_state_check.validate_contract(
            contract,
            "historical terminal contract",
            errors,
            strict=True,
            current_clip=current_clip,
            prompt=prompt,
            current_project_version=(
                project["canon_revision"],
                project["state_revision"],
            ),
            source_references={
                reference["tag"] for reference in project["reference_registry"]
            },
            historical_ledger=protected_historical_ledger(),
            consumed_historical_keys=set(),
        )

        self.assertFalse(
            any("status" in error and "current project clip" in error for error in errors),
            errors,
        )

    def test_non_narrative_lane_requires_exact_two_line_record(self) -> None:
        project = load_json("examples/standalone-clip/project-state.json")
        project["project_mode"] = "sequence_project"
        project["story"]["medium"] = "live_action"
        for clip in project["clips"]:
            clip["directors_read_lane"] = "non_narrative"
            clip["authoring_state"] = {
                "utility_intent": "Show the latch closing cleanly in one readable motion.",
                "non_narrative_refusal": "No invented desire, rivalry, or emotional performance.",
            }
        self.assertEqual(self.validate_project_copy(project, strict=True), [])

        project["clips"][0]["authoring_state"] = copy.deepcopy(
            load_json("examples/sequence-airport-arrival/clip-01-contract.json")["authoring_state"]
        )
        errors = self.validate_project_copy(project, strict=True)
        self.assertTrue(any("missing fields" in error or "unknown fields" in error for error in errors), errors)

    def test_mixed_sequence_walks_across_utility_insert(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        first_after = project["clips"][0]["authoring_state"]["value_after"]
        project["clips"][1]["directors_read_lane"] = "non_narrative"
        project["clips"][1]["authoring_state"] = {
            "utility_intent": "Hold one readable insert of rain clearing from the door seal.",
            "non_narrative_refusal": "No invented agency, anxiety, or emotional symbolism for the car.",
        }
        project["clips"][2]["authoring_state"]["value_before"] = first_after
        errors = self.validate_project_copy(project, strict=True)
        self.assertFalse(any("nearest narrative ancestor" in error for error in errors), errors)

        project["clips"][2]["authoring_state"]["value_before"] = "a severed dramatic thread"
        errors = self.validate_project_copy(project, strict=True)
        self.assertTrue(any("nearest narrative ancestor" in error for error in errors), errors)

    def test_lineage_cycles_fail_before_value_handoff_can_be_skipped(self) -> None:
        utility_state = {
            "utility_intent": "Show one readable mechanical continuity action.",
            "non_narrative_refusal": "No invented agency, psychology, or dramatic meaning.",
        }
        project = load_json("examples/sequence-mixed-lane/project-state.json")
        for clip in project["clips"][:2]:
            clip["directors_read_lane"] = "non_narrative"
            clip["authoring_state"] = copy.deepcopy(utility_state)
            clip["status"] = "accepted"
        project["clips"][0]["parent_clip_id"] = "clip_02"
        project["clips"][1]["parent_clip_id"] = "clip_01"
        project["clips"][2]["parent_clip_id"] = "clip_02"
        errors = self.validate_project_copy(project, strict=True)
        self.assertTrue(any("clip lineage cycle" in error for error in errors), errors)

    def test_deep_leaf_first_lineage_is_iterative(self) -> None:
        clips = []
        for index in range(1500):
            clip_id = f"deep_{index:04d}"
            clips.append(
                {
                    "clip_id": clip_id,
                    "parent_clip_id": (
                        None if index == 0 else f"deep_{index - 1:04d}"
                    ),
                    "sequence_index": index + 1,
                    "status": "planned",
                    "observed_end_state": None,
                }
            )

        lineage = project_state_check.analyze_lineage(list(reversed(clips)), "deep")

        self.assertEqual(len(lineage.clips), 1500)
        self.assertEqual(lineage.errors, [])

    def test_wrong_type_story_is_diagnostic_not_exception(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        project["story"] = []

        errors = self.validate_project_copy(project, strict=True)

        self.assertTrue(any("story must be an object" in error for error in errors), errors)

    def test_nested_wrong_types_are_diagnostic_not_exceptions(self) -> None:
        base = load_json("examples/sequence-airport-arrival/project-state.json")

        def mutate_beats(project: dict) -> None:
            project["beats"] = [[]]

        def mutate_references(project: dict) -> None:
            project["reference_registry"] = [[]]

        def mutate_scene_id(project: dict) -> None:
            project["scenes"][0]["scene_id"] = []

        def mutate_scene_assignments(project: dict) -> None:
            project["scenes"][0]["assigned_clip_ids"] = [{}]

        def mutate_clip_scene(project: dict) -> None:
            project["clips"][0]["scene_id"] = {}

        def mutate_clip_beats(project: dict) -> None:
            project["clips"][0]["this_clip_only"] = [{}]

        mutations = (
            ("beats", mutate_beats),
            ("reference_registry", mutate_references),
            ("scene_id", mutate_scene_id),
            ("assigned_clip_ids", mutate_scene_assignments),
            ("clip_01 scene_id", mutate_clip_scene),
            ("this_clip_only", mutate_clip_beats),
        )
        for expected, mutate in mutations:
            project = copy.deepcopy(base)
            mutate(project)
            errors = self.validate_project_copy(project, strict=True)
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_main_guards_non_array_reference_registry_in_current_project_pass(self) -> None:
        base = load_json("examples/sequence-airport-arrival/project-state.json")
        for invalid in (None, 7, {}):
            with self.subTest(reference_registry=invalid), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                project_path = root / "examples" / "project-state.json"
                project_path.parent.mkdir(parents=True)
                project = copy.deepcopy(base)
                project["reference_registry"] = invalid
                project_path.write_text(json.dumps(project), encoding="utf-8")

                stdout = io.StringIO()
                with mock.patch.object(
                    sys,
                    "argv",
                    ["project_state_check.py", str(root), "--strict"],
                ), redirect_stdout(stdout):
                    exit_code = project_state_check.main()

                self.assertEqual(exit_code, 1)
                self.assertIn(
                    "reference_registry must be an array of reference objects",
                    stdout.getvalue(),
                )

    def test_nested_unhashable_array_entries_are_diagnostic_not_exceptions(self) -> None:
        base = load_json("examples/sequence-airport-arrival/project-state.json")
        mutations = (
            ("assigned_clip_ids", ("scenes", 0, "assigned_clip_ids")),
            ("already_happened", ("clips", 0, "already_happened")),
            ("this_clip_only", ("clips", 0, "this_clip_only")),
            ("reserved_for_later", ("clips", 0, "reserved_for_later")),
            ("prompt_carriers", ("clips", 0, "authoring_state", "prompt_carriers")),
            (
                "contract_authoring_state_snapshots",
                ("clips", 0, "contract_authoring_state_snapshots"),
            ),
            ("dependencies", ("beats", 0, "dependencies")),
        )
        for expected, path in mutations:
            project = copy.deepcopy(base)
            target = project
            for segment in path[:-1]:
                target = target[segment]
            target[path[-1]] = [{}]
            errors = self.validate_project_copy(project, strict=True)
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_contract_beat_arrays_reject_unhashable_entries_without_exception(self) -> None:
        base = load_json(
            "examples/sequence-airport-arrival/clip-02-continuation-contract.json"
        )
        for field in ("this_clip_only", "reserved_for_later"):
            contract = copy.deepcopy(base)
            contract[field] = [{}]
            errors: list[str] = []
            project_state_check.validate_contract(
                contract,
                "malformed contract",
                errors,
                strict=False,
                current_clip=None,
                prompt=None,
            )
            with self.subTest(field=field):
                self.assertTrue(any(field in error for error in errors), errors)

    def test_lineage_rejects_self_parent_forward_parent_and_duplicate_position(self) -> None:
        base = load_json("examples/sequence-mixed-lane/project-state.json")

        self_parent = copy.deepcopy(base)
        self_parent["clips"][1]["parent_clip_id"] = "clip_02"
        errors = self.validate_project_copy(self_parent, strict=True)
        self.assertTrue(any("cannot parent itself" in error for error in errors), errors)

        forward_parent = copy.deepcopy(base)
        forward_parent["clips"][1]["parent_clip_id"] = "clip_03"
        errors = self.validate_project_copy(forward_parent, strict=True)
        self.assertTrue(any("must be greater than parent" in error for error in errors), errors)

        duplicate_position = copy.deepcopy(base)
        duplicate_position["clips"][1]["sequence_index"] = 1
        errors = self.validate_project_copy(duplicate_position, strict=True)
        self.assertTrue(any("duplicate sequence_index 1" in error for error in errors), errors)

    def test_lineage_rejects_inconsistent_extension_depth(self) -> None:
        project = load_json("examples/sequence-mixed-lane/project-state.json")
        project["clips"][1]["extension_depth"] = 2
        errors = self.validate_project_copy(project, strict=True)
        self.assertTrue(
            any("extension_depth 2 must be 1 from parent clip_01" in error for error in errors),
            errors,
        )

        project = load_json("examples/sequence-mixed-lane/project-state.json")
        project["clips"][0]["extension_depth"] = 1
        errors = self.validate_project_copy(project, strict=True)
        self.assertTrue(any("root clip clip_01 extension_depth must be 0" in error for error in errors), errors)

    def test_lineage_allows_later_scene_reanchor_to_reset_depth(self) -> None:
        project = load_json("examples/sequence-mixed-lane/project-state.json")
        scene = copy.deepcopy(project["scenes"][0])
        scene["scene_id"] = "scene_02"
        scene["scene_index"] = 2
        scene["assigned_clip_ids"] = ["clip_03"]
        project["scenes"][0]["assigned_clip_ids"].remove("clip_03")
        project["scenes"].append(scene)
        project["clips"][2]["scene_id"] = "scene_02"
        project["clips"][2]["sequence_index"] = 3
        project["clips"][2]["extension_depth"] = 0
        self.assertEqual(self.validate_project_copy(project, strict=True), [])

    def test_equal_values_are_rejected(self) -> None:
        base = copy.deepcopy(
            load_json("examples/sequence-airport-arrival/clip-02-continuation-contract.json")[
                "authoring_state"
            ]
        )
        equivalent_values = (
            (base["value_before"], base["value_before"]),
            ("Control passes to traveler", "  control   passes TO TRAVELER  "),
            ("control passes to traveler", "control-passes-to-traveler."),
            ("caf\u00e9", "cafe\u0301"),
            ("ＦＵＬＬＷＩＤＴＨ", "fullwidth"),
            ("control passes", "control\u200b passes"),
            ("control passes", "control\u00adpasses"),
        )
        for before, after in equivalent_values:
            state = copy.deepcopy(base)
            state["value_before"] = before
            state["value_after"] = after
            errors: list[str] = []
            project_state_check.check_authoring_state(
                state, "fixture", errors, required=True, lane="narrative"
            )
            with self.subTest(before=before, after=after):
                self.assertTrue(any("must change value_before" in error for error in errors), errors)

    def test_non_transferable_detail_provenance_requires_real_source_evidence(self) -> None:
        base = copy.deepcopy(
            load_json("examples/sequence-airport-arrival/clip-02-continuation-contract.json")[
                "authoring_state"
            ]
        )

        for source in (
            None,
            "the source",
            "probably supplied",
            "ref:\u200b",
            "file:\u2800",
            "https://\u2060",
        ):
            state = copy.deepcopy(base)
            state["non_transferable_detail_provenance"] = "source_bound"
            state["non_transferable_detail_source"] = source
            errors: list[str] = []
            project_state_check.check_authoring_state(
                state, "fixture", errors, required=True, lane="narrative"
            )
            with self.subTest(source=source):
                self.assertTrue(any("requires an exact reference" in error for error in errors), errors)

        state = copy.deepcopy(base)
        state["non_transferable_detail_provenance"] = "source_bound"
        state["non_transferable_detail_source"] = "@Image1"
        errors = []
        project_state_check.check_authoring_state(
            state, "fixture", errors, required=True, lane="narrative"
        )
        self.assertFalse(any("source_bound" in error for error in errors), errors)

        errors = []
        project_state_check.check_authoring_state(
            state,
            "fixture",
            errors,
            required=True,
            lane="narrative",
            source_references={"@Image 1"},
        )
        self.assertTrue(any("not present in reference_registry" in error for error in errors), errors)

        state["non_transferable_detail_source"] = "@Image 1"
        errors = []
        project_state_check.check_authoring_state(
            state,
            "fixture",
            errors,
            required=True,
            lane="narrative",
            source_references={"@Image 1"},
        )
        self.assertFalse(any("source_bound" in error for error in errors), errors)

        state["non_transferable_detail_provenance"] = "authored_choice"
        errors = []
        project_state_check.check_authoring_state(
            state, "fixture", errors, required=True, lane="narrative"
        )
        self.assertTrue(any("source must be null" in error for error in errors), errors)

        project = load_json("examples/sequence-airport-arrival/project-state.json")
        project_state = project["clips"][0]["authoring_state"]
        project_state["non_transferable_detail_provenance"] = "source_bound"
        project_state["non_transferable_detail_source"] = "@Imaginary999"
        errors = self.validate_project_copy(project, strict=True)
        self.assertTrue(any("not present in reference_registry" in error for error in errors), errors)

        project_state["non_transferable_detail_source"] = "@Image 1"
        errors = self.validate_project_copy(project, strict=True)
        self.assertFalse(any("source_bound" in error for error in errors), errors)

    def test_narrative_state_rejects_empty_extra_duplicate_and_bad_provenance(self) -> None:
        state = copy.deepcopy(
            load_json("examples/sequence-airport-arrival/clip-01-contract.json")["authoring_state"]
        )
        state["subtext_contradiction"] = ""
        state["non_transferable_detail_provenance"] = "observed_because_it_sounds_good"
        state["extra_mood"] = "generic atmosphere"
        state["prompt_carriers"] = ["POV: traveler.", "POV: traveler."]
        errors: list[str] = []
        project_state_check.check_authoring_state(
            state, "fixture", errors, required=True, lane="narrative"
        )
        self.assertTrue(any("subtext_contradiction" in error for error in errors), errors)
        self.assertTrue(any("provenance" in error for error in errors), errors)
        self.assertTrue(any("unknown fields" in error for error in errors), errors)
        self.assertTrue(any("leaks internal labels" in error for error in errors), errors)
        self.assertTrue(any("duplicates" in error for error in errors), errors)

    def test_narrative_state_rejects_generic_presence_only_content(self) -> None:
        state = copy.deepcopy(
            load_json("examples/sequence-airport-arrival/clip-01-contract.json")[
                "authoring_state"
            ]
        )
        for field in (
            "dramatic_function",
            "turn",
            "pov",
            "power_shift",
            "hidden_want_objective",
            "obstacle_tactic",
            "subtext_contradiction",
            "visible_suppressed_behavior",
            "non_transferable_detail",
            "stock_solution_refused",
        ):
            state[field] = "Something happens."
        state["value_before"] = "Something before."
        state["value_after"] = "Something after."
        state["prompt_carriers"] = ["The camera shows something happening."]

        errors: list[str] = []
        project_state_check.check_authoring_state(
            state,
            "generic narrative state",
            errors,
            required=True,
            lane="narrative",
        )

        self.assertTrue(
            any(
                "creative specificity" in error
                or "reuses the same content" in error
                for error in errors
            ),
            errors,
        )

    def test_compiler_rejects_every_canonical_label_and_missing_carrier(self) -> None:
        state = load_json("examples/sequence-airport-arrival/clip-01-contract.json")["authoring_state"]
        labels = (
            "Dramatic function: reveal. Turn: before to after. POV: traveler. "
            "Power shift: crowd to traveler. Objective: shelter. Obstacle: rain. "
            "Tactic: keep walking. Contradiction: relief versus composure. "
            "Visible suppressed behavior: a hand stops. Non-transferable detail: tag. "
            "Non-transferable detail provenance: authored. Stock solution refused: smile. "
            "Value before: exposed. Value after: safe. Prompt carriers: gestures."
        )
        prompt = " ".join(state["prompt_carriers"][:-1]) + " " + labels
        errors = project_state_check.compiled_prompt_errors(
            prompt, state, "fixture prompt", lane="narrative"
        )
        self.assertTrue(any("dramatic_function" in error for error in errors), errors)
        self.assertTrue(any("pov" in error for error in errors), errors)
        self.assertTrue(any("stock_solution_refused" in error for error in errors), errors)
        self.assertEqual(sum("missing exact prompt carrier" in error for error in errors), 1)

    def test_non_narrative_prompt_must_relate_to_utility_intent(self) -> None:
        state = {
            "utility_intent": "Show the latch closing cleanly in one readable motion.",
            "non_narrative_refusal": "No invented desire, rivalry, or emotional performance.",
        }

        unrelated = project_state_check.compiled_prompt_errors(
            "A static sunset over an empty beach.",
            state,
            "utility prompt",
            lane="non_narrative",
        )
        related = project_state_check.compiled_prompt_errors(
            "Hold top-down as the latch closes in one continuous motion.",
            state,
            "utility prompt",
            lane="non_narrative",
        )

        self.assertTrue(any("utility_intent" in error for error in unrelated), unrelated)
        self.assertEqual(related, [])

    def test_compiler_rejects_hyphenated_label_aliases_without_blocking_prose(self) -> None:
        state = load_json(
            "examples/sequence-airport-arrival/clip-01-contract.json"
        )["authoring_state"]
        carrier_text = " ".join(state["prompt_carriers"])
        aliases = (
            "POWER-SHIFT: curb to traveler.",
            "POINT-OF-VIEW: traveler.",
            "VALUE-BEFORE: exposed.",
            "NONTRANSFERABLE DETAIL: creased tag.",
            "TURN -- composure breaks.",
            "UTILITY-INTENT: hold insert.",
            "POWER–SHIFT： curb to traveler.",
            "NONTRANSFERABLE-DETAIL-SOURCE: @Image1.",
            "AUTHORING-STATE-DIGEST: deadbeef.",
            "POWER.SHIFT: curb to traveler.",
            "P.O.V.: traveler.",
            "VALUE|BEFORE: exposed.",
            "NON·TRANSFERABLE·DETAIL: creased tag.",
            "POWER SHIFT; curb to traveler.",
            "POWER SHIFT",
        )
        for alias in aliases:
            errors = project_state_check.compiled_prompt_errors(
                f"{carrier_text} {alias}", state, "fixture prompt", lane="narrative"
            )
            with self.subTest(alias=alias):
                self.assertTrue(
                    any("leaks internal authoring label" in error for error in errors), errors
                )

        ordinary_prose = (
            "She turns left before the doorway. Power shifts to her when the latch catches. "
            "The camera holds a point-of-view shot while the obstacle stays visible. "
            "At the turn -- a narrow service road -- she looks left. The turn is sharp. "
            "The objective is visible above the door. "
            "The car makes a left turn: it clears frame without braking. "
            "At the turn: she glances toward the door. "
            "On her turn: she closes the door."
        )
        self.assertEqual(project_state_check.leaked_authoring_labels(ordinary_prose), [])

    def test_default_ignorables_cannot_split_internal_labels(self) -> None:
        state = load_json(
            "examples/sequence-airport-arrival/clip-01-contract.json"
        )["authoring_state"]
        carriers = " ".join(state["prompt_carriers"])
        for counterfeit, field in (
            ("val\u200bue_before: exposed", "value_before"),
            ("sto\u2060ck solution refused: smile", "stock_solution_refused"),
        ):
            errors = project_state_check.compiled_prompt_errors(
                f"{carriers} {counterfeit}",
                state,
                "default-ignorable label prompt",
                lane="narrative",
            )
            with self.subTest(counterfeit=counterfeit):
                self.assertTrue(
                    any(field in error for error in errors),
                    errors,
                )

    def test_canonical_digest_serializes_integral_decimal_without_precision_loss(self) -> None:
        expected = hashlib.sha256(b'{"sequence_index":1.0}').hexdigest()
        self.assertEqual(
            project_state_check.canonical_json_digest(
                {"sequence_index": Decimal("1.0")}
            ),
            expected,
        )

        historical = load_json(
            "examples/sequence-airport-arrival/clip-01-contract.json"
        )
        historical["sequence_index"] = Decimal("1.0")
        self.assertRegex(
            project_state_check.canonical_json_digest(historical),
            r"^[0-9a-f]{64}$",
        )

    def test_prompt_carriers_must_be_in_rendered_generation_prose(self) -> None:
        state = load_json(
            "examples/sequence-airport-arrival/clip-01-contract.json"
        )["authoring_state"]
        visible = " ".join(state["prompt_carriers"][:-1])
        hidden = state["prompt_carriers"][-1]
        prompts = (
            f"{visible}\n<!-- {hidden} -->",
            f"{visible}\n\n[//]: # ({hidden})",
            f"{visible}\n\n[{hidden}]: https://invalid.example/carrier",
            f"---\nhidden_carrier: {hidden}\n---\n{visible}",
            f"---\nhidden_carrier: {hidden}\n...\n{visible}",
            f"---\rhidden_carrier: {hidden}\r---\r{visible}",
            f"{visible}\n\n[carrier-note]: https://invalid.example\n \"{hidden}\"",
            f'{visible}\n\n[carrier-note]: https://invalid.example\n "prefix {hidden} \\"suffix\\""',
            f'{visible}\n\n[carrier-note]: https://invalid.example\n "prefix\n{hidden}"',
            f'{visible}\n\n> [carrier-note]: https://invalid.example\n> "{hidden}"',
            f'{visible}\n\n- [carrier-note]: https://invalid.example\n  "{hidden}"',
            f"{visible}\n[source](https://invalid.example \"{hidden}\")",
            f'{visible}\n[source](https://invalid.example "prefix {hidden} \\"suffix\\"")',
            f'{visible}\n[source](https://invalid.example "prefix\n{hidden}")',
            f'{visible}\n![decoration](image.png "open\n{hidden}")',
            f"{visible}\n<span data-carrier=\"{hidden}\"></span>",
            f"{visible}\n<span hidden>{hidden}</span>",
            f"{visible}\n<span aria-hidden=\"true\">{hidden}</span>",
            f"{visible}\n<span style=\"display: none\">{hidden}</span>",
            f"{visible}\n<span style='visibility:hidden'>{hidden}</span>",
            f"{visible}\n<span style=display:none>{hidden}</span>",
            f'{visible}\n<span data-x=\">\" hidden>{hidden}</span>',
            f"{visible}\n<div hidden><div>decoy</div>{hidden}</div>",
            f'{visible}\n<div style="display:/*x*/none">{hidden}</div>',
            f'{visible}\n<div style="visibility:/*x*/hidden">{hidden}</div>',
            f'{visible}\n<div style="d\\69splay:none">{hidden}</div>',
            f'{visible}\n<div style="display:\\6e one">{hidden}</div>',
            f'{visible}\n<div style="content-visibility:hidden">{hidden}</div>',
            f'{visible}\n<div style="opacity:0">{hidden}</div>',
            f"{visible}\n<div hidden/>{hidden}",
            f"{visible}\n<script>{hidden}</script>",
            f"{visible}\n<script>{hidden}",
            f"{visible}\n<script/>{hidden}",
            f"{visible}\n<template>{hidden}</template>",
            f"{visible}\n<template><template>decoy</template>{hidden}</template>",
            f'{visible}\n<style>.secret{{display:none}}</style><div class="secret">{hidden}</div>',
            f"{visible}\n<style>div{{display:none}}</style><div>{hidden}</div>",
            f'{visible}\n<link rel="stylesheet" href="hidden.css"><div>{hidden}</div>',
            f"{visible}\n<iframe src=\"about:blank\">{hidden}</iframe>",
            f"{visible}\n<svg><metadata>{hidden}</metadata></svg>",
            f"{visible}\n<svg><desc>{hidden}</desc></svg>",
            f"{visible}\n<canvas>{hidden}</canvas>",
            f"{visible}\n<details><summary>More</summary>{hidden}</details>",
            f"{visible}\n<details><summary>First</summary><summary>{hidden}</summary></details>",
            f"{visible}\n<dialog>{hidden}</dialog>",
            f"{visible}\n\n[carrier-image]: image.png\n\n![{hidden}][carrier-image]",
            f"{visible}\n\n[{hidden}]: image.png\n\n![{hidden}]",
            f'{visible}\n\n[ref]: image.png "open\n{hidden}"',
            f'{visible}\n\n[foo\\]bar]: image.png "{hidden}"\n![decoration][foo\\]bar]',
            f'{visible}\n\n[ref]:\n image.png "{hidden}"',
            f'{visible}\n\n[//]: #\n"{hidden}"',
            f'{visible}\n\n[comment]: <>\n"{hidden}"',
            f'{visible}\n\n[foo\n bar]: image.png "{hidden}"',
            f'{visible}\n\n[foo\n bar]: image.png\n"{hidden}"',
            f"{visible}\n```\n{hidden}\n```",
            f"{visible}\n`{hidden}`",
            f"{visible}\n\n    {hidden}",
            f"{visible}\n>     {hidden}",
            f"{visible}\n<pre><code>{hidden}</code></pre>",
            f"{visible}\n<textarea>{hidden}</textarea>",
            f"{visible}\n![{hidden}][ref]\n```bad`info\n\n[ref]: image.png",
            f"{visible}\nThe shot continues.\n<span>\n`{hidden}`\n</span>",
        )
        for prompt in prompts:
            errors = project_state_check.compiled_prompt_errors(
                prompt, state, "comment-hidden prompt", lane="narrative"
            )
            expected_missing = (
                len(state["prompt_carriers"])
                if "<style" in prompt or 'rel="stylesheet"' in prompt
                else 1
            )
            with self.subTest(prompt=prompt):
                self.assertEqual(
                    sum("missing exact prompt carrier" in error for error in errors),
                    expected_missing,
                    errors,
                )

    def test_rendered_markdown_that_resembles_metadata_remains_evidence(self) -> None:
        state = load_json(
            "examples/sequence-airport-arrival/clip-01-contract.json"
        )["authoring_state"]
        visible = " ".join(state["prompt_carriers"][:-1])
        carrier = state["prompt_carriers"][-1]
        long_definition_label = "a" + (" " * 1000) + "b"
        long_image_label = "x" + (" " * 1000)
        prompts = (
            f'{visible}\n[ref]: URL\n"unclosed\n\n{carrier}',
            f"{visible}\n![{carrier}]",
            f"{visible}\n![{carrier}][missing]",
            f"{visible}\n\\![{carrier}]",
            f"{visible}\n[note]: not a valid destination {carrier}",
            f"{visible}\n![{carrier}](not a valid destination)",
            f'{visible}\n![{carrier}](image.png "open\n\nclose")',
            f'{visible}\n![{carrier}](image.png\n\n"title")',
            f"{visible}\n![{carrier}](image.png\v)",
            f"{visible}\n![{carrier}](foo\\ bar)",
            f"{visible}\n![{carrier}](foo\\\nbar)",
            f'{visible}\n[ref]: image.png "open\n\n{carrier}"',
            f"{visible}\n![{carrier}][ref]\n[ref]: image.png\v",
            f"{visible}\n![{carrier}][ref]\n[ref]: foo\\ bar",
            f"{visible}\n![{carrier}][fooa]\n[foo\\a]: image.png",
            f"{visible}\n![{carrier}][foo[bar]\n[foo\\[bar]: image.png",
            f"{visible}\n![{carrier}][a b]\n[{long_definition_label}]: image.png",
            f"{visible}\n![{carrier}][{long_image_label}]\n[x]: image.png",
            f"{visible}\n![{carrier}][foo\\!]\n[foo!]: image.png",
            f"{visible}\n![{carrier}][foo!]\n[foo\\!]: image.png",
            f"{visible}\n![{carrier}][foo&amp;]\n[foo&]: image.png",
            f"{visible}\n![{carrier}][foo&]\n[foo&amp;]: image.png",
            f"{visible}\n![{carrier}][ref]\n```\n[ref]: image.png\n```",
            f"{visible}\n![{carrier}][ref]\n<script>\n[ref]: image.png\n</script>",
            f"{visible}\n![{carrier}][ref]\n\t[ref]: image.png",
            f"{visible}\n![{carrier}][ref]\n<div>\n[ref]: image.png\n</div>",
            f"{visible}\n<div>{carrier}</div>",
            f"{visible}\nThe shot continues without a cut.\n    {carrier}",
            f"{visible}\n<div>\n`{carrier}`\n</div>",
            f"{visible}\n![{carrier}][ref]\n<hr>\n[ref]: image.png",
            f"{visible}\n![{carrier}][ref]\n\n<span>\n[ref]: image.png\n</span>",
            f"{visible}\n![{carrier}][ref]\n[ref]: image.png",
            f"{visible}\n![{carrier}][ref]\n<span>\n[ref]: image.png\n</span>",
            f"{visible}\n![{carrier}][ref]\n<?target\n[ref]: image.png\n?>",
            f"{visible}\n![{carrier}][ref]\n<!DOCTYPE\n[ref]: image.png\n>",
            f"{visible}\n![{carrier}][ref]\n<![CDATA[\n[ref]: image.png\n]]>",
            f"{visible}\n> The shot continues without a cut.\n>     {carrier}",
            f"{visible}\n<details><summary>{carrier}</summary>hidden body</details>",
            f"{visible}\n<details open><summary>More</summary>{carrier}</details>",
            f"{visible}\n<dialog open>{carrier}</dialog>",
        )
        for prompt in prompts:
            errors = project_state_check.compiled_prompt_errors(
                prompt, state, "rendered markdown prompt", lane="narrative"
            )
            with self.subTest(prompt=prompt):
                self.assertFalse(
                    any("missing exact prompt carrier" in error for error in errors),
                    errors,
                )

    def test_reference_definitions_do_not_cross_container_instances(self) -> None:
        cross_container = (
            "![carrier][ref]\n\n[ref]:\n> image.png",
            "![carrier][ref]\n\n> [ref]:\nimage.png",
            "![carrier][ref]\n\n[ref]:\n- image.png",
            '![carrier][ref]\n\n[ref]: image.png\n> "carrier"',
            '![carrier][ref]\n\n> [ref]: image.png\n"carrier"',
            "![carrier][ref]\n\n- [ref]:\n- image.png",
            "![carrier][ref]\n\n1. [ref]:\n2. image.png",
            "![carrier][foo bar]\n\n[foo\n> bar]: image.png",
            "![carrier][foo bar]\n\n- [foo\n- bar]: image.png",
            '![carrier][ref]\n\n[ref]: image.png "open\n> carrier"',
        )
        for prompt in cross_container:
            with self.subTest(prompt=prompt):
                self.assertIn(
                    "carrier",
                    project_state_check.strip_non_rendered_markdown(prompt),
                )

        same_container = (
            "![carrier][ref]\n\n- [ref]:\n  image.png",
            "![carrier][ref]\n\n1. [ref]:\n   image.png",
            "![carrier][ref]\n\n> [ref]:\n> image.png",
            "![carrier][foo bar]\n\n> [foo\n> bar]: image.png",
            "![carrier][foo bar]\n\n- [foo\n  bar]: image.png",
            '![carrier][ref]\n\n> [ref]: image.png "open\n> carrier"',
            "![carrier][ref]\n\n- visible paragraph\n- [ref]: image.png",
        )
        for prompt in same_container:
            with self.subTest(prompt=prompt):
                self.assertNotIn(
                    "carrier",
                    project_state_check.strip_non_rendered_markdown(prompt),
                )

        interrupted_in_same_list_item = (
            "![carrier][ref]\n\n- visible paragraph\n  [ref]: image.png"
        )
        self.assertIn(
            "carrier",
            project_state_check.strip_non_rendered_markdown(
                interrupted_in_same_list_item
            ),
        )

    def test_label_explanations_unicode_arrows_and_table_cells_are_rejected(self) -> None:
        state = load_json(
            "examples/sequence-airport-arrival/clip-01-contract.json"
        )["authoring_state"]
        carriers = " ".join(state["prompt_carriers"])
        counterfeits = (
            "The power shift is explained as the traveler taking control.",
            "For this beat, the power shift means the traveler takes control.",
            "Meanwhile, the power shift is explained as the traveler takes control.",
            "For this beat, the POV means the traveler controls the frame.",
            "POWER SHIFT → traveler",
            "POWER SHIFT ⮕ traveler",
            "POWER SHIFT 🡂 traveler",
            "| VALUE BEFORE | exposed at the curb |",
            "| **VALUE BEFORE** | exposed at the curb |",
            "**POWER SHIFT**: traveler",
            "`POWER SHIFT`: traveler",
            "POWER&#32;SHIFT: traveler",
            "1) TURN: composure breaks.",
            "![TURN: composure breaks][missing]",
            "[TURN]: composure breaks",
            "| beat | TURN | composure breaks |",
            "<pre><code>TURN: composure breaks.</code></pre>",
            *(f"ordinary prose{separator}TURN: composure breaks." for separator in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"),
        )
        for counterfeit in counterfeits:
            errors = project_state_check.compiled_prompt_errors(
                f"{carriers}\n{counterfeit}",
                state,
                "counterfeit label prompt",
                lane="narrative",
            )
            with self.subTest(counterfeit=counterfeit):
                self.assertTrue(
                    any("leaks internal authoring label" in error for error in errors),
                    errors,
                )

    def test_default_ignorable_only_authoring_text_and_carriers_are_empty(self) -> None:
        base = load_json(
            "examples/sequence-airport-arrival/clip-01-contract.json"
        )["authoring_state"]
        for invisible in ("\u200b", "\u2060\ufe0f", "\u3164", "\u0301", "\u2800", "...---"):
            state = copy.deepcopy(base)
            state["dramatic_function"] = invisible
            errors: list[str] = []
            project_state_check.check_authoring_state(
                state,
                "invisible authoring text",
                errors,
                required=True,
                lane="narrative",
            )
            with self.subTest(invisible=repr(invisible), field="dramatic_function"):
                self.assertTrue(any("dramatic_function" in error for error in errors), errors)

            state = copy.deepcopy(base)
            state["prompt_carriers"] = [invisible]
            errors = []
            project_state_check.check_authoring_state(
                state,
                "invisible carrier",
                errors,
                required=True,
                lane="narrative",
            )
            with self.subTest(invisible=repr(invisible), field="prompt_carriers"):
                self.assertTrue(any("prompt_carriers[0]" in error for error in errors), errors)

        for separator in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029":
            state = copy.deepcopy(base)
            state["dramatic_function"] = f"left{separator}right"
            state["prompt_carriers"] = [f"visible{separator}carrier"]
            errors = []
            project_state_check.check_authoring_state(
                state,
                "Unicode line boundary",
                errors,
                required=True,
                lane="narrative",
            )
            with self.subTest(separator=ord(separator)):
                self.assertTrue(any("dramatic_function" in error for error in errors), errors)
                self.assertTrue(any("prompt_carriers[0]" in error for error in errors), errors)

    def test_wrong_type_authoring_enums_fail_without_tracebacks(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        for lane in ([], {}, 1, True):
            probe = copy.deepcopy(project)
            probe["clips"][0]["directors_read_lane"] = lane
            errors = self.validate_project_copy(probe, strict=False)
            with self.subTest(surface="project", lane=lane):
                self.assertTrue(any("directors_read_lane" in error for error in errors), errors)

        state = copy.deepcopy(
            load_json("examples/sequence-airport-arrival/clip-01-contract.json")[
                "authoring_state"
            ]
        )
        state["non_transferable_detail_provenance"] = []
        errors: list[str] = []
        project_state_check.check_authoring_state(
            state,
            "wrong provenance type",
            errors,
            required=True,
            lane="narrative",
        )
        self.assertTrue(any("must be source_bound or authored_choice" in e for e in errors), errors)

        contract = load_json("examples/sequence-airport-arrival/clip-01-contract.json")
        clip = copy.deepcopy(project["clips"][0])
        contract["status"] = []
        clip["status"] = []
        contract["authoring_state_provenance"]["canon_revision"] = []
        errors = []
        project_state_check.validate_contract(
            contract,
            "wrong contract enum types",
            errors,
            strict=False,
            current_clip=clip,
            prompt=(ROOT / "examples/sequence-airport-arrival/clip-01-prompt.md").read_text(
                encoding="utf-8"
            ),
            historical_ledger=protected_historical_ledger(),
        )
        self.assertTrue(any("invalid contract status" in e for e in errors), errors)
        self.assertTrue(any("revisions must be integers" in e for e in errors), errors)

    def test_default_mode_rejects_partial_lane_less_authoring_metadata(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        project["clips"][0].pop("directors_read_lane")
        errors = self.validate_project_copy(project, strict=False)
        self.assertTrue(any("authoring metadata requires directors_read_lane" in e for e in errors), errors)

        clip = copy.deepcopy(project["clips"][1])
        contract = load_json(
            "examples/sequence-airport-arrival/clip-02-continuation-contract.json"
        )
        clip.pop("directors_read_lane")
        contract.pop("directors_read_lane")
        contract.pop("authoring_state_provenance")
        prompt = (ROOT / "examples/sequence-airport-arrival/clip-02-prompt.md").read_text(
            encoding="utf-8"
        )
        errors = []
        project_state_check.validate_contract(
            contract,
            "partial lane-less contract",
            errors,
            strict=False,
            current_clip=clip,
            prompt=prompt,
            historical_ledger=protected_historical_ledger(),
        )
        self.assertTrue(any("authoring metadata requires directors_read_lane" in e for e in errors), errors)
        self.assertTrue(any("missing authoring_state_provenance" in e for e in errors), errors)

        provenance_only_clip = copy.deepcopy(clip)
        provenance_only_contract = load_json(
            "examples/sequence-airport-arrival/clip-02-continuation-contract.json"
        )
        provenance_only_clip.pop("authoring_state", None)
        provenance_only_contract.pop("directors_read_lane")
        provenance_only_contract.pop("authoring_state")
        errors = []
        project_state_check.validate_contract(
            provenance_only_contract,
            "provenance-only lane-less contract",
            errors,
            strict=False,
            current_clip=provenance_only_clip,
            prompt=prompt,
            historical_ledger=protected_historical_ledger(),
        )
        self.assertTrue(any("authoring metadata requires directors_read_lane" in e for e in errors), errors)
        self.assertTrue(any("missing authoring_state" in e for e in errors), errors)

        project_provenance_only = load_json(
            "examples/sequence-airport-arrival/project-state.json"
        )
        project_clip = project_provenance_only["clips"][2]
        project_clip.pop("directors_read_lane", None)
        project_clip.pop("authoring_state", None)
        project_clip["authoring_state_provenance"] = {
            "project_id": project_provenance_only["project_id"],
            "clip_id": project_clip["clip_id"],
            "canon_revision": 2,
            "state_revision": 2,
            "authoring_state_sha256": "0" * 64,
        }
        errors = self.validate_project_copy(project_provenance_only, strict=False)
        self.assertTrue(any("authoring metadata requires directors_read_lane" in e for e in errors), errors)
        self.assertTrue(any("missing authoring_state" in e for e in errors), errors)

    def test_protected_ledger_rejects_coordinated_rewrites_and_status_downgrade(self) -> None:
        ledger = protected_historical_ledger()
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        historical_clip = next(item for item in project["clips"] if item["clip_id"] == "clip_01")
        historical = load_json("examples/sequence-airport-arrival/clip-01-contract.json")
        historical_prompt = (
            ROOT / "examples/sequence-airport-arrival/clip-01-prompt.md"
        ).read_text(encoding="utf-8")
        historical["authoring_state"]["dramatic_function"] = "coordinated rewrite"
        historical["authoring_state_provenance"]["authoring_state_sha256"] = (
            project_state_check.authoring_state_digest(historical["authoring_state"])
        )
        historical_clip["contract_authoring_state_snapshots"] = [
            copy.deepcopy(historical["authoring_state_provenance"])
        ]
        errors: list[str] = []
        project_state_check.validate_contract(
            historical,
            "coordinated historical rewrite",
            errors,
            strict=True,
            current_clip=historical_clip,
            prompt=historical_prompt,
            current_project_version=project_state_check.project_version(project),
            historical_ledger=ledger,
        )
        self.assertTrue(any("contract_sha256" in error for error in errors), errors)

        downgraded_project = load_json("examples/sequence-airport-arrival/project-state.json")
        downgraded_clip = next(
            item for item in downgraded_project["clips"] if item["clip_id"] == "clip_02"
        )
        downgraded = load_json(
            "examples/sequence-airport-arrival/clip-02-continuation-contract.json"
        )
        downgraded_prompt = (
            ROOT / "examples/sequence-airport-arrival/clip-02-prompt.md"
        ).read_text(encoding="utf-8")
        downgraded_clip["status"] = "rejected"
        downgraded_project["take_history"].append(
            {
                "take_id": "take_clip02_rejected",
                "clip_id": "clip_02",
                "verdict": "reject",
                "evidence": "Synthetic terminal state for the provenance rollback test.",
            }
        )
        downgraded["status"] = "rejected"
        downgraded["authoring_state"]["hidden_want_objective"] = "status downgrade rewrite"
        downgraded["authoring_state_provenance"]["authoring_state_sha256"] = (
            project_state_check.authoring_state_digest(downgraded["authoring_state"])
        )
        downgraded_clip["contract_authoring_state_snapshots"] = [
            copy.deepcopy(downgraded["authoring_state_provenance"])
        ]
        downgraded_project["clips"] = [
            clip for clip in downgraded_project["clips"] if clip["clip_id"] != "clip_03"
        ]
        downgraded_project["scenes"][0]["assigned_clip_ids"] = ["clip_01", "clip_02"]
        downgraded_project["beats"] = [
            beat
            for beat in downgraded_project["beats"]
            if beat.get("assigned_clip_id") != "clip_03"
        ]
        downgraded_project["current_clip_id"] = "clip_02"
        self.assertEqual(self.validate_project_copy(downgraded_project, strict=True), [])
        errors = []
        project_state_check.validate_contract(
            downgraded,
            "coordinated status downgrade",
            errors,
            strict=True,
            current_clip=downgraded_clip,
            prompt=downgraded_prompt,
            current_project_version=project_state_check.project_version(downgraded_project),
            historical_ledger=ledger,
        )
        self.assertTrue(any("no protected historical provenance ledger entry" in e for e in errors), errors)

        ledger_data = load_json("validation/authoring-state-provenance-ledger.json")
        ledger_data["entries"][0]["contract_status"] = "accepted"
        ledger_errors: list[str] = []
        with mock.patch.object(project_state_check, "load_json", return_value=ledger_data):
            loaded = project_state_check.load_protected_provenance_ledger(ROOT, ledger_errors)
        self.assertIsNone(loaded)
        self.assertTrue(any("does not match pinned digest" in e for e in ledger_errors), ledger_errors)

    def test_ledger_entry_cannot_be_orphaned_by_terminal_status_rollback(self) -> None:
        ledger = protected_historical_ledger()
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        clip = next(item for item in project["clips"] if item["clip_id"] == "clip_01")
        contract = load_json("examples/sequence-airport-arrival/clip-01-contract.json")
        prompt = (ROOT / "examples/sequence-airport-arrival/clip-01-prompt.md").read_text(
            encoding="utf-8"
        )
        clip["status"] = "ready"
        contract["status"] = "ready"
        consumed: set[tuple[str, str, int, int]] = set()
        errors: list[str] = []
        project_state_check.validate_contract(
            contract,
            "rolled-back historical contract",
            errors,
            strict=False,
            current_clip=clip,
            prompt=prompt,
            current_project_version=(1, 1),
            historical_ledger=ledger,
            consumed_historical_keys=consumed,
        )
        project_state_check.check_provenance_ledger_consumption(
            ledger,
            consumed,
            errors,
        )
        self.assertTrue(any("is orphaned" in error for error in errors), errors)

    def test_one_ledger_entry_cannot_be_consumed_by_duplicate_contracts(self) -> None:
        ledger = protected_historical_ledger()
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        clip = next(item for item in project["clips"] if item["clip_id"] == "clip_01")
        contract = load_json("examples/sequence-airport-arrival/clip-01-contract.json")
        prompt = (ROOT / "examples/sequence-airport-arrival/clip-01-prompt.md").read_text(
            encoding="utf-8"
        )
        consumed: set[tuple[str, str, int, int]] = set()
        errors: list[str] = []
        for label in ("first historical artifact", "duplicate historical artifact"):
            project_state_check.validate_contract(
                copy.deepcopy(contract),
                label,
                errors,
                strict=True,
                current_clip=clip,
                prompt=prompt,
                current_project_version=project_state_check.project_version(project),
                historical_ledger=ledger,
                consumed_historical_keys=consumed,
            )
        self.assertTrue(any("more than one terminal contract" in e for e in errors), errors)

    def test_ledger_append_order_uses_sequence_not_project_id_sorting(self) -> None:
        ledger_data = load_json("validation/authoring-state-provenance-ledger.json")
        ledger_data["entries"].append(
            {
                "entry_sequence": 2,
                "project_id": "aaa_later_append",
                "clip_id": "clip_99",
                "canon_revision": 1,
                "state_revision": 1,
                "contract_status": "accepted",
                "authoring_state_sha256": "1" * 64,
                "contract_sha256": "2" * 64,
                "prompt_sha256": "3" * 64,
            }
        )
        ledger_errors: list[str] = []
        with mock.patch.object(
            project_state_check,
            "load_json",
            return_value=ledger_data,
        ), mock.patch.object(
            project_state_check,
            "PROVENANCE_LEDGER_SHA256",
            project_state_check.canonical_json_digest(ledger_data),
        ):
            loaded = project_state_check.load_protected_provenance_ledger(
                ROOT,
                ledger_errors,
            )
        self.assertIsNotNone(loaded)
        self.assertEqual(ledger_errors, [])

    def test_current_contract_staleness_is_rejected(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        clip = next(item for item in project["clips"] if item["clip_id"] == "clip_02")
        contract = load_json("examples/sequence-airport-arrival/clip-02-continuation-contract.json")
        contract["authoring_state"]["hidden_want_objective"] = "a stale objective"
        prompt = (ROOT / "examples/sequence-airport-arrival/clip-02-prompt.md").read_text(
            encoding="utf-8"
        )
        errors: list[str] = []
        project_state_check.validate_contract(
            contract,
            "fixture",
            errors,
            strict=True,
            current_clip=clip,
            prompt=prompt,
            historical_ledger=protected_historical_ledger(),
        )
        self.assertTrue(any("current authoring_state is stale" in error for error in errors), errors)

    def test_contract_authoring_state_is_bound_to_exact_revision_and_digest(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        current_version = project_state_check.project_version(project)

        historical = load_json("examples/sequence-airport-arrival/clip-01-contract.json")
        historical_clip = next(item for item in project["clips"] if item["clip_id"] == "clip_01")
        historical_prompt = (
            ROOT / "examples/sequence-airport-arrival/clip-01-prompt.md"
        ).read_text(encoding="utf-8")
        errors: list[str] = []
        project_state_check.validate_contract(
            historical,
            "historical contract",
            errors,
            strict=True,
            current_clip=historical_clip,
            prompt=historical_prompt,
            current_project_version=current_version,
            historical_ledger=protected_historical_ledger(),
        )
        self.assertEqual(errors, [])

        rewritten = copy.deepcopy(historical)
        rewritten["authoring_state"]["dramatic_function"] = "a later arbitrary rewrite"
        errors = []
        project_state_check.validate_contract(
            rewritten,
            "rewritten historical contract",
            errors,
            strict=True,
            current_clip=historical_clip,
            prompt=historical_prompt,
            current_project_version=current_version,
            historical_ledger=protected_historical_ledger(),
        )
        self.assertTrue(any("immutable provenance digest" in error for error in errors), errors)

        rewritten["authoring_state_provenance"]["authoring_state_sha256"] = (
            project_state_check.authoring_state_digest(rewritten["authoring_state"])
        )
        errors = []
        project_state_check.validate_contract(
            rewritten,
            "rewritten historical contract and digest",
            errors,
            strict=True,
            current_clip=historical_clip,
            prompt=historical_prompt,
            current_project_version=current_version,
            historical_ledger=protected_historical_ledger(),
        )
        self.assertTrue(any("not bound to an exact planned snapshot" in error for error in errors), errors)

        current = load_json(
            "examples/sequence-airport-arrival/clip-02-continuation-contract.json"
        )
        current_clip = next(item for item in project["clips"] if item["clip_id"] == "clip_02")
        current_prompt = (
            ROOT / "examples/sequence-airport-arrival/clip-02-prompt.md"
        ).read_text(encoding="utf-8")
        current["authoring_state_provenance"]["state_revision"] = 1
        errors = []
        project_state_check.validate_contract(
            current,
            "stale current provenance",
            errors,
            strict=True,
            current_clip=current_clip,
            prompt=current_prompt,
            current_project_version=current_version,
            historical_ledger=protected_historical_ledger(),
        )
        self.assertTrue(any("does not match current project revision" in error for error in errors), errors)

    def test_contract_freshness_classifies_every_status_explicitly(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        base_clip = next(item for item in project["clips"] if item["clip_id"] == "clip_02")
        base_contract = load_json(
            "examples/sequence-airport-arrival/clip-02-continuation-contract.json"
        )
        prompt = (ROOT / "examples/sequence-airport-arrival/clip-02-prompt.md").read_text(
            encoding="utf-8"
        )

        for status in sorted(project_state_check.CURRENT_CONTRACT_STATUSES):
            clip = copy.deepcopy(base_clip)
            contract = copy.deepcopy(base_contract)
            clip["status"] = status
            contract["status"] = status
            contract["authoring_state"]["hidden_want_objective"] = "a stale objective"
            errors: list[str] = []
            project_state_check.validate_contract(
                contract,
                f"current {status}",
                errors,
                strict=True,
                current_clip=clip,
                prompt=prompt,
                historical_ledger=protected_historical_ledger(),
            )
            with self.subTest(status=status):
                self.assertTrue(
                    any("current authoring_state is stale" in error for error in errors),
                    errors,
                )

        for status in sorted(project_state_check.HISTORICAL_CONTRACT_STATUSES):
            clip = copy.deepcopy(base_clip)
            contract = copy.deepcopy(base_contract)
            clip["status"] = status
            contract["status"] = status
            contract["authoring_state"]["hidden_want_objective"] = "preserved planned objective"
            errors = []
            project_state_check.validate_contract(
                contract,
                f"historical {status}",
                errors,
                strict=True,
                current_clip=clip,
                prompt=prompt,
                historical_ledger=protected_historical_ledger(),
            )
            with self.subTest(status=status):
                self.assertFalse(
                    any("current authoring_state is stale" in error for error in errors),
                    errors,
                )

    def test_production_main_invokes_prompt_boundary(self) -> None:
        sentinel = "sentinel prompt boundary failure"
        stdout = io.StringIO()
        with mock.patch.object(
            project_state_check,
            "compiled_prompt_errors",
            return_value=[sentinel],
        ) as compiler, mock.patch.object(
            sys, "argv", ["project_state_check.py", str(ROOT), "--strict"]
        ), redirect_stdout(stdout):
            exit_code = project_state_check.main()
        self.assertEqual(exit_code, 1)
        self.assertGreaterEqual(compiler.call_count, 2)
        self.assertIn(sentinel, stdout.getvalue())

    def test_production_main_consumes_every_protected_ledger_entry(self) -> None:
        stdout = io.StringIO()
        with mock.patch.object(
            project_state_check,
            "check_provenance_ledger_consumption",
            wraps=project_state_check.check_provenance_ledger_consumption,
        ) as consumption, mock.patch.object(
            sys, "argv", ["project_state_check.py", str(ROOT), "--strict"]
        ), redirect_stdout(stdout):
            exit_code = project_state_check.main()
        self.assertEqual(exit_code, 0, stdout.getvalue())
        consumption.assert_called_once()
        ledger, consumed, errors = consumption.call_args.args
        self.assertEqual(set(ledger), consumed)
        self.assertEqual(errors, [])

    def test_production_main_discovers_renamed_contract_and_project_artifacts(self) -> None:
        probes = (
            (
                "examples/sequence-airport-arrival/clip-01-contract.json",
                "examples/sequence-airport-arrival/clip-01-copy.json",
                "more than one terminal contract",
            ),
            (
                "examples/sequence-airport-arrival/project-state.json",
                "examples/sequence-airport-arrival/project-copy.json",
                "duplicate project snapshot revision",
            ),
        )
        for source, renamed, expected in probes:
            with self.subTest(renamed=renamed), tempfile.TemporaryDirectory(dir=ROOT) as tmp:
                repo = Path(tmp) / "repo"
                repo.mkdir()
                for directory in ("examples", "schemas", "validation"):
                    shutil.copytree(ROOT / directory, repo / directory)
                destination = repo / renamed
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(repo / source, destination)

                stdout = io.StringIO()
                with mock.patch.object(
                    sys, "argv", ["project_state_check.py", str(repo), "--strict"]
                ), redirect_stdout(stdout):
                    exit_code = project_state_check.main()
                self.assertEqual(exit_code, 1, stdout.getvalue())
                self.assertIn(expected, stdout.getvalue())

    def test_duplicate_and_incomparable_project_revisions_are_not_selected(self) -> None:
        base = load_json("examples/sequence-airport-arrival/project-state.json")
        duplicate = copy.deepcopy(base)
        errors: list[str] = []
        selected = project_state_check.select_current_projects(
            [
                (ROOT / "examples/a/project-state.json", base),
                (ROOT / "examples/z/project-state.json", duplicate),
            ],
            ROOT,
            errors,
        )
        self.assertNotIn(base["project_id"], selected)
        self.assertTrue(any("duplicate project snapshot revision" in error for error in errors), errors)

        crossed = copy.deepcopy(base)
        crossed["canon_revision"] = base["canon_revision"] - 1
        crossed["state_revision"] = base["state_revision"] + 1
        errors = []
        selected = project_state_check.select_current_projects(
            [
                (ROOT / "examples/a/project-state.json", base),
                (ROOT / "examples/z/project-state.json", crossed),
            ],
            ROOT,
            errors,
        )
        self.assertNotIn(base["project_id"], selected)
        self.assertTrue(any("incomparable project snapshot revisions" in error for error in errors), errors)

    def test_all_snapshot_pairs_are_compared_independently_of_input_order(self) -> None:
        base = load_json("examples/sequence-airport-arrival/project-state.json")
        records = []
        for name, version in (
            ("a", (3, 3)),
            ("b", (2, 1)),
            ("c", (1, 2)),
        ):
            project = copy.deepcopy(base)
            project["canon_revision"], project["state_revision"] = version
            records.append((ROOT / f"examples/{name}/project-state.json", project))

        observed = []
        for ordered in (records, list(reversed(records))):
            errors: list[str] = []
            selected = project_state_check.select_current_projects(
                ordered,
                ROOT,
                errors,
            )
            self.assertNotIn(base["project_id"], selected)
            observed.append(errors)

        self.assertEqual(observed[0], observed[1])
        self.assertTrue(
            any("incomparable project snapshot revisions" in error for error in observed[0]),
            observed[0],
        )


class AuthoringStateSchemaCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from jsonschema import Draft202012Validator
        except ImportError as exc:  # pragma: no cover - release environment installs it
            raise unittest.SkipTest("jsonschema not installed") from exc
        cls.validator = Draft202012Validator
        cls.project_schema = load_json("schemas/project-state.schema.json")
        cls.contract_schema = load_json("schemas/clip-contract.schema.json")

    def test_schema_definitions_match_and_keep_legacy_absence(self) -> None:
        for definition in (
            "visible_one_line_text",
            "authoring_state_provenance",
            "authoring_state",
            "narrative_authoring_state",
            "non_narrative_authoring_state",
        ):
            self.assertEqual(
                self.project_schema["$defs"][definition],
                self.contract_schema["$defs"][definition],
            )

        project = load_json("examples/sequence-airport-arrival/project-state.json")
        for clip in project["clips"]:
            clip.pop("authoring_state", None)
            clip.pop("directors_read_lane", None)
            clip.pop("contract_authoring_state_snapshots", None)
        self.assertEqual(list(self.validator(self.project_schema).iter_errors(project)), [])

        contract = load_json("examples/sequence-airport-arrival/clip-01-contract.json")
        contract.pop("authoring_state", None)
        contract.pop("directors_read_lane", None)
        contract.pop("authoring_state_provenance", None)
        self.assertEqual(list(self.validator(self.contract_schema).iter_errors(contract)), [])

        partial_project = load_json("examples/sequence-airport-arrival/project-state.json")
        partial_project["clips"][0].pop("directors_read_lane")
        self.assertTrue(
            list(self.validator(self.project_schema).iter_errors(partial_project))
        )

        partial_contract = load_json(
            "examples/sequence-airport-arrival/clip-01-contract.json"
        )
        partial_contract.pop("directors_read_lane")
        partial_contract.pop("authoring_state_provenance")
        self.assertTrue(
            list(self.validator(self.contract_schema).iter_errors(partial_contract))
        )

        provenance_only = load_json(
            "examples/sequence-airport-arrival/clip-01-contract.json"
        )
        provenance_only.pop("directors_read_lane")
        provenance_only.pop("authoring_state")
        self.assertTrue(
            list(self.validator(self.contract_schema).iter_errors(provenance_only))
        )

    def test_schema_rejects_every_unicode_line_boundary_in_authoring_text(self) -> None:
        contract = load_json("examples/sequence-airport-arrival/clip-01-contract.json")
        validator = self.validator(self.contract_schema)
        for separator in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029":
            probe = copy.deepcopy(contract)
            probe["felt_intent"] = f"left{separator}right"
            probe["authoring_state"]["dramatic_function"] = f"left{separator}right"
            probe["authoring_state"]["prompt_carriers"] = [
                f"visible{separator}carrier"
            ]
            probe["authoring_state"]["non_transferable_detail_provenance"] = "source_bound"
            probe["authoring_state"]["non_transferable_detail_source"] = (
                f"[left{separator}right]"
            )
            with self.subTest(separator=ord(separator)):
                self.assertTrue(list(validator.iter_errors(probe)))

    def test_schemas_reject_blank_or_invisible_felt_intent(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        contract = load_json("examples/sequence-airport-arrival/clip-01-contract.json")
        for value in INVISIBLE_AUTHORING_TEXT_VALUES:
            with self.subTest(value=value):
                project_probe = copy.deepcopy(project)
                project_probe["clips"][0]["felt_intent"] = value
                self.assertTrue(
                    list(self.validator(self.project_schema).iter_errors(project_probe))
                )

                contract_probe = copy.deepcopy(contract)
                contract_probe["felt_intent"] = value
                self.assertTrue(
                    list(self.validator(self.contract_schema).iter_errors(contract_probe))
                )

        for schema, document in (
            (self.project_schema, project),
            (self.contract_schema, contract),
        ):
            probe = copy.deepcopy(document)
            target = probe["clips"][0] if "clips" in probe else probe
            target["felt_intent"] = "\u200bWaiting at the threshold\u2060"
            self.assertEqual(list(self.validator(schema).iter_errors(probe)), [])

    def test_schemas_reject_blank_or_invisible_authoring_state_text(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        contract = load_json("examples/sequence-airport-arrival/clip-01-contract.json")
        documents = (
            (self.project_schema, project, lambda probe: probe["clips"][0]),
            (self.contract_schema, contract, lambda probe: probe),
        )

        for schema, document, select_clip in documents:
            for field in NARRATIVE_TEXT_FIELDS:
                for value in INVISIBLE_AUTHORING_TEXT_VALUES:
                    with self.subTest(lane="narrative", field=field, value=value):
                        probe = copy.deepcopy(document)
                        select_clip(probe)["authoring_state"][field] = value
                        self.assertTrue(list(self.validator(schema).iter_errors(probe)))

            for value in INVISIBLE_AUTHORING_TEXT_VALUES:
                with self.subTest(
                    lane="narrative", field="prompt_carriers", value=value
                ):
                    probe = copy.deepcopy(document)
                    select_clip(probe)["authoring_state"]["prompt_carriers"] = [value]
                    self.assertTrue(list(self.validator(schema).iter_errors(probe)))

            for field in sorted(NON_NARRATIVE_FIELDS):
                for value in INVISIBLE_AUTHORING_TEXT_VALUES:
                    with self.subTest(lane="non_narrative", field=field, value=value):
                        probe = copy.deepcopy(document)
                        clip = select_clip(probe)
                        clip["directors_read_lane"] = "non_narrative"
                        clip["authoring_state"] = {
                            "utility_intent": "Show the seal clearing in one insert.",
                            "non_narrative_refusal": "No invented agency or psychology.",
                        }
                        clip["authoring_state"][field] = value
                        self.assertTrue(list(self.validator(schema).iter_errors(probe)))

    def test_lane_conditionals_require_matching_records_and_reject_null(self) -> None:
        project = load_json("examples/sequence-airport-arrival/project-state.json")
        narrative_missing = copy.deepcopy(project)
        narrative_missing["clips"][0].pop("authoring_state")
        self.assertTrue(list(self.validator(self.project_schema).iter_errors(narrative_missing)))

        non_narrative = copy.deepcopy(project)
        non_narrative["clips"][0]["directors_read_lane"] = "non_narrative"
        non_narrative["clips"][0]["authoring_state"] = {
            "utility_intent": "Show the wet door seal clearing in one readable insert.",
            "non_narrative_refusal": "No invented agency or psychology for the car.",
        }
        self.assertEqual(list(self.validator(self.project_schema).iter_errors(non_narrative)), [])

        wrong_lane_state = copy.deepcopy(non_narrative)
        wrong_lane_state["clips"][0]["authoring_state"] = project["clips"][0]["authoring_state"]
        self.assertTrue(list(self.validator(self.project_schema).iter_errors(wrong_lane_state)))

        explicit_null = copy.deepcopy(non_narrative)
        explicit_null["clips"][0]["authoring_state"] = None
        self.assertTrue(list(self.validator(self.project_schema).iter_errors(explicit_null)))

        contract = load_json("examples/sequence-airport-arrival/clip-02-continuation-contract.json")
        contract.pop("authoring_state")
        self.assertTrue(list(self.validator(self.contract_schema).iter_errors(contract)))

        contract = load_json("examples/sequence-airport-arrival/clip-02-continuation-contract.json")
        contract.pop("authoring_state_provenance")
        self.assertTrue(list(self.validator(self.contract_schema).iter_errors(contract)))

    def test_schema_rejects_removed_irreversible_cost_field(self) -> None:
        contract = load_json("examples/sequence-airport-arrival/clip-02-continuation-contract.json")
        contract["authoring_state"]["irreversible_cost"] = "manufactured stakes"
        self.assertTrue(list(self.validator(self.contract_schema).iter_errors(contract)))

    def test_schema_requires_source_evidence_for_source_bound_detail(self) -> None:
        contract = load_json("examples/sequence-airport-arrival/clip-02-continuation-contract.json")
        state = contract["authoring_state"]
        state["non_transferable_detail_provenance"] = "source_bound"
        state["non_transferable_detail_source"] = "@Image1"
        contract["authoring_state_provenance"]["authoring_state_sha256"] = (
            project_state_check.authoring_state_digest(state)
        )
        self.assertEqual(list(self.validator(self.contract_schema).iter_errors(contract)), [])

        state["non_transferable_detail_source"] = None
        self.assertTrue(list(self.validator(self.contract_schema).iter_errors(contract)))

        state["non_transferable_detail_provenance"] = "authored_choice"
        state["non_transferable_detail_source"] = "@Image1"
        self.assertTrue(list(self.validator(self.contract_schema).iter_errors(contract)))


if __name__ == "__main__":
    unittest.main()

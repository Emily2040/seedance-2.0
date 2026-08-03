"""Adversarial tests for complete, prompt-inert live-eval judge contracts."""

from __future__ import annotations

import copy
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import eval_run  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]


def response_for(case: dict, *, notes: str = "ok") -> dict:
    sequence = eval_run.is_sequence_case(case)
    return {
        "criterion_scores": {
            criterion_id: True
            for criterion_id in eval_run.expected_judge_checks(case)
        },
        "dimension_scores": {
            dimension_id: 4
            for dimension_id in (
                eval_run.SEQUENCE_DIMENSION_IDS if sequence else ()
            )
        },
        "overall_score": 4 if sequence else 3,
        "pass": True,
        "notes": notes,
    }


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def sizing_case(
    assertion_count: int,
    *,
    required_count: int = 0,
    forbidden_count: int = 0,
    sequence: bool = False,
) -> dict:
    case = {
        "id": f"sizing_{'sequence' if sequence else 'legacy'}_{assertion_count}",
        "prompt": "size this contract",
        "expected_output": "a usable answer",
        "assertions": [
            f"criterion {index}" for index in range(assertion_count)
        ],
        "failure_mode": "an unusable answer",
        "skills_expected_to_activate": ["seedance-20"],
    }
    if required_count:
        case["required_output_sections"] = [
            f"required section {index}" for index in range(required_count)
        ]
    if forbidden_count:
        case["forbidden_behaviors"] = [
            f"forbidden behavior {index}" for index in range(forbidden_count)
        ]
    if sequence:
        case.update(
            {
                "critical": False,
                "expected_state_delta": "accepted footage alone updates canon",
                "expected_prompt_architecture": "state -> contract -> prompt",
                "expected_sequence_relation": "standalone",
            }
        )
    return case


class JudgeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = eval_run.freeze_repository(REPO_ROOT)
        cls.cases = eval_run.load_cases(cls.snapshot)
        cls.sequence_case = next(
            case for case in cls.cases if "expected_sequence_relation" in case
        )
        cls.provider, cls.endpoint, cls.model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )

    def capture_judge_call(self, case: dict) -> tuple[str, str]:
        raw = compact_json(response_for(case))
        with mock.patch.object(eval_run, "call_api", return_value=raw) as call:
            eval_run.judge(
                case,
                "candidate response",
                self.model,
                "key",
                "rubric",
                self.provider,
                self.endpoint,
                [],
            )
        system, user = call.call_args.args[:2]
        return system, user

    def capture_discovery_call(self, case: dict) -> tuple[str, str]:
        plan = compact_json(
            {"sources": sorted(eval_run._expected_route_paths(case))}
        )
        with mock.patch.object(eval_run, "call_api", return_value=plan) as call:
            eval_run.discover_sources(
                self.snapshot,
                case,
                self.model,
                "key",
                self.provider,
                self.endpoint,
            )
        system, user = call.call_args.args[:2]
        return system, user

    def test_stable_ids_cover_every_declared_contract_and_dimension(self) -> None:
        case = {
            "prompt": "request",
            "expected_output": "one observable outcome",
            "assertions": ["first assertion", "second assertion"],
            "failure_mode": "generic mood without evidence",
            "required_output_sections": ["Final prompt"],
            "forbidden_behaviors": ["invented source footage"],
            "expected_state_delta": "accepted footage alone changes canon",
            "expected_prompt_architecture": "state -> contract -> prompt",
            "expected_sequence_relation": "seamless_continuation",
        }

        self.assertEqual(
            eval_run.expected_judge_checks(case),
            ["a0", "a1", "r0", "f0", "eo", "fm", "sd", "pa"],
        )
        rules = {
            row["id"]: row["rule"]
            for row in eval_run.expected_judge_criteria(case)
        }
        self.assertIn(case["expected_output"], rules["eo"])
        self.assertIn(case["failure_mode"], rules["fm"])
        self.assertIn(case["expected_state_delta"], rules["sd"])
        self.assertIn(case["expected_prompt_architecture"], rules["pa"])
        dimensions = eval_run.expected_dimension_criteria(case)
        self.assertEqual(
            [row["id"] for row in dimensions],
            list(eval_run.SEQUENCE_DIMENSION_IDS),
        )
        self.assertIn("seamless_continuation", dimensions[0]["rule"])
        self.assertNotIn("seamless_continuation", dimensions[1]["rule"])

    def test_each_oracle_mutation_changes_only_the_judge_input(self) -> None:
        base = copy.deepcopy(self.sequence_case)
        selected_sources: list[str] = []
        baseline_discovery = eval_run.planner_prompt(self.snapshot, base)
        baseline_discovery_call = self.capture_discovery_call(base)
        baseline_responder = (
            eval_run.responder_context(self.snapshot, selected_sources),
            eval_run.responder_user_input(self.snapshot, base),
        )
        baseline_judge = self.capture_judge_call(base)
        mutations: dict[str, str] = {
            "expected_output": base["expected_output"] + " [mutated expected output]",
            "failure_mode": base["failure_mode"] + " [mutated failure mode]",
            "expected_state_delta": base["expected_state_delta"] + " [mutated state delta]",
            "expected_prompt_architecture": (
                base["expected_prompt_architecture"] + " [mutated architecture]"
            ),
            "expected_sequence_relation": (
                "standalone"
                if base["expected_sequence_relation"] != "standalone"
                else "seamless_continuation"
            ),
        }

        for field, value in mutations.items():
            mutant = copy.deepcopy(base)
            mutant[field] = value
            with self.subTest(field=field):
                self.assertEqual(
                    eval_run.planner_prompt(self.snapshot, mutant),
                    baseline_discovery,
                )
                self.assertEqual(
                    self.capture_discovery_call(mutant),
                    baseline_discovery_call,
                )
                self.assertEqual(
                    (
                        eval_run.responder_context(self.snapshot, selected_sources),
                        eval_run.responder_user_input(self.snapshot, mutant),
                    ),
                    baseline_responder,
                )
                mutant_judge = self.capture_judge_call(mutant)
                self.assertEqual(mutant_judge[0], baseline_judge[0])
                self.assertNotEqual(mutant_judge[1], baseline_judge[1])
                self.assertIn(value, mutant_judge[1])

    def test_all_canonical_response_envelopes_fit_the_900_byte_budget(self) -> None:
        notes = "é" * (eval_run.JUDGE_NOTES_MAX_BYTES // 2)
        largest: tuple[int, str] = (0, "")
        for case in self.cases:
            raw = compact_json(response_for(case, notes=notes))
            size = len(raw.encode("utf-8"))
            largest = max(largest, (size, case["id"]))
            with self.subTest(case=case["id"], size=size):
                self.assertLessEqual(size, eval_run.JUDGE_RESPONSE_MAX_BYTES)
                self.assertEqual(
                    size,
                    eval_run._canonical_judge_response_size(case, notes),
                )
                self.assertLessEqual(
                    eval_run._maximum_judge_response_size(case, notes),
                    eval_run.JUDGE_RESPONSE_MAX_BYTES,
                )
                normalized = eval_run.normalize_verdict(
                    case, json.loads(raw)
                )
                self.assertTrue(normalized["pass"], normalized["notes"])
        self.assertGreater(largest[0], 0)

    def test_legacy_assertion_only_boundary_is_exact(self) -> None:
        last_fit = sizing_case(53)
        first_failure = sizing_case(54)

        self.assertEqual(len(eval_run.expected_judge_checks(last_fit)), 55)
        self.assertEqual(
            eval_run._maximum_judge_response_size(last_fit, "x" * 160),
            894,
        )
        eval_run.validate_case_contract(self.snapshot, [last_fit])

        self.assertEqual(len(eval_run.expected_judge_checks(first_failure)), 56)
        self.assertEqual(
            eval_run._maximum_judge_response_size(first_failure, "x" * 160),
            906,
        )
        with self.assertRaisesRegex(
            eval_run.HarnessError,
            "requires 906 UTF-8 bytes.*900-byte limit",
        ):
            eval_run.validate_case_contract(self.snapshot, [first_failure])

    def test_sequence_assertion_only_boundary_is_exact(self) -> None:
        last_fit = sizing_case(45, sequence=True)
        first_failure = sizing_case(46, sequence=True)

        self.assertEqual(len(eval_run.expected_judge_checks(last_fit)), 49)
        self.assertEqual(
            eval_run._maximum_judge_response_size(last_fit, "x" * 160),
            897,
        )
        eval_run.validate_case_contract(self.snapshot, [last_fit])

        self.assertEqual(len(eval_run.expected_judge_checks(first_failure)), 50)
        self.assertEqual(
            eval_run._maximum_judge_response_size(first_failure, "x" * 160),
            909,
        )
        with self.assertRaisesRegex(
            eval_run.HarnessError,
            "requires 909 UTF-8 bytes.*900-byte limit",
        ):
            eval_run.validate_case_contract(self.snapshot, [first_failure])

    def test_both_scales_accept_899_and_900_but_preflight_rejects_901(self) -> None:
        boundaries = {
            False: {
                899: (1, 6, 47),
                900: (1, 5, 48),
                901: (1, 4, 49),
            },
            True: {
                899: (1, 9, 36),
                900: (1, 8, 37),
                901: (1, 7, 38),
            },
        }

        for sequence, sizes in boundaries.items():
            for expected_size, counts in sizes.items():
                assertions, required, forbidden = counts
                case = sizing_case(
                    assertions,
                    required_count=required,
                    forbidden_count=forbidden,
                    sequence=sequence,
                )
                with self.subTest(sequence=sequence, size=expected_size):
                    self.assertEqual(
                        eval_run._maximum_judge_response_size(
                            case, "x" * eval_run.JUDGE_NOTES_MAX_BYTES
                        ),
                        expected_size,
                    )
                    if expected_size <= eval_run.JUDGE_RESPONSE_MAX_BYTES:
                        eval_run.validate_case_contract(self.snapshot, [case])
                    else:
                        with self.assertRaisesRegex(
                            eval_run.HarnessError,
                            "requires 901 UTF-8 bytes.*900-byte limit",
                        ):
                            eval_run.validate_case_contract(self.snapshot, [case])

    def test_preflight_accounts_for_false_values_in_a_near_limit_verdict(self) -> None:
        case = sizing_case(5, required_count=25, forbidden_count=30)
        self.assertEqual(
            eval_run._canonical_judge_response_size(
                case, "x" * eval_run.JUDGE_NOTES_MAX_BYTES
            ),
            900,
        )
        self.assertEqual(
            eval_run._maximum_judge_response_size(
                case, "x" * eval_run.JUDGE_NOTES_MAX_BYTES
            ),
            963,
        )
        with self.assertRaisesRegex(
            eval_run.HarnessError,
            "requires 963 UTF-8 bytes.*900-byte limit",
        ):
            eval_run.validate_case_contract(self.snapshot, [case])

    def test_maximal_legal_list_contract_is_rejected_before_live_evaluation(self) -> None:
        case = sizing_case(64, required_count=64, forbidden_count=64)
        self.assertEqual(len(eval_run.expected_judge_checks(case)), 194)
        self.assertGreater(
            eval_run._maximum_judge_response_size(case, "x" * 160),
            eval_run.JUDGE_RESPONSE_MAX_BYTES,
        )
        with self.assertRaisesRegex(
            eval_run.HarnessError,
            "maximum canonical judge response requires.*900-byte limit",
        ):
            eval_run.validate_case_contract(self.snapshot, [case])

    def test_live_main_rejects_oversized_contract_before_any_api_call(self) -> None:
        case = sizing_case(
            1,
            required_count=4,
            forbidden_count=49,
        )
        self.assertEqual(
            eval_run._maximum_judge_response_size(
                case, "x" * eval_run.JUDGE_NOTES_MAX_BYTES
            ),
            901,
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["eval_run.py", str(REPO_ROOT)],
            ),
            mock.patch.object(
                eval_run,
                "freeze_repository",
                return_value=self.snapshot,
            ),
            mock.patch.object(eval_run, "load_cases", return_value=[case]),
            mock.patch.object(eval_run, "call_api") as call,
            redirect_stdout(output),
        ):
            code = eval_run.main()

        self.assertEqual(code, 2)
        self.assertIn("maximum canonical judge response requires", output.getvalue())
        call.assert_not_called()

    def test_response_sizing_counts_multibyte_notes_as_utf8_bytes(self) -> None:
        case = sizing_case(58)
        ascii_boundary = eval_run._canonical_judge_response_size(
            case, "x" * 160
        )
        multibyte_boundary = eval_run._canonical_judge_response_size(
            case, "é" * 80
        )
        first_over = eval_run._canonical_judge_response_size(case, "é" * 81)

        self.assertEqual(ascii_boundary, 893)
        self.assertEqual(multibyte_boundary, ascii_boundary)
        self.assertEqual(first_over, ascii_boundary + 2)

    def test_non_sequence_schema_requires_an_empty_dimension_object(self) -> None:
        case = next(case for case in self.cases if not eval_run.is_sequence_case(case))
        _system, user = self.capture_judge_call(case)
        self.assertIn("dimension_scores as an empty object", user)
        self.assertNotIn("dimension_scores as an empty list", user)

    def test_notes_cap_counts_compact_json_payload_after_escaping(self) -> None:
        case = self.cases[0]
        accepted = {
            "two-byte": ("é" * 80, 160),
            "astral": ("😀" * 40, 160),
            "quote": ('"' * 80, 160),
            "backslash": ("\\" * 80, 160),
            "nul": ("\x00" * 26, 156),
        }
        rejected = {
            "two-byte": ("é" * 81, 162),
            "astral": ("😀" * 41, 164),
            "quote": ('"' * 81, 162),
            "backslash": ("\\" * 81, 162),
            "nul": ("\x00" * 27, 162),
        }

        for label, (notes, expected_size) in accepted.items():
            with self.subTest(label=label, accepted=True):
                self.assertEqual(
                    eval_run._compact_json_string_payload_size(notes),
                    expected_size,
                )
                self.assertTrue(
                    eval_run.normalize_verdict(
                        case, response_for(case, notes=notes)
                    )["pass"]
                )

        for label, (notes, expected_size) in rejected.items():
            with self.subTest(label=label, accepted=False):
                self.assertEqual(
                    eval_run._compact_json_string_payload_size(notes),
                    expected_size,
                )
                normalized = eval_run.normalize_verdict(
                    case, response_for(case, notes=notes)
                )
                self.assertFalse(normalized["pass"])
                self.assertIn("after escaping", normalized["notes"])
                self.assertIn("excluding surrounding quotes", normalized["notes"])
                self.assertLessEqual(
                    eval_run._compact_json_string_payload_size(
                        normalized["notes"]
                    ),
                    eval_run.JUDGE_NOTES_MAX_BYTES,
                )

        system, _user = self.capture_judge_call(case)
        self.assertIn("after escaping", system)
        self.assertIn("excluding its surrounding quotes", system)

    def test_every_normalize_accepted_note_fits_a_preflight_accepted_envelope(
        self,
    ) -> None:
        cases = (
            sizing_case(1, required_count=5, forbidden_count=48),
            sizing_case(
                1,
                required_count=8,
                forbidden_count=37,
                sequence=True,
            ),
        )
        notes_by_escape_width = (
            "x" * 160,
            "é" * 80,
            "界" * 53,
            "😀" * 40,
            '"' * 80,
            "\\" * 80,
            "\n" * 80,
            "\x00" * 26,
            ('"\x00é😀\\' * 10),
        )

        for case in cases:
            eval_run.validate_case_contract(self.snapshot, [case])
            preflight_size = eval_run._maximum_judge_response_size(
                case, "x" * eval_run.JUDGE_NOTES_MAX_BYTES
            )
            self.assertEqual(preflight_size, eval_run.JUDGE_RESPONSE_MAX_BYTES)
            empty_size = eval_run._canonical_judge_response_size(case, "")
            for notes in notes_by_escape_width:
                with self.subTest(case=case["id"], notes=repr(notes[:2])):
                    payload_size = eval_run._compact_json_string_payload_size(notes)
                    self.assertLessEqual(payload_size, eval_run.JUDGE_NOTES_MAX_BYTES)
                    normalized = eval_run.normalize_verdict(
                        case, response_for(case, notes=notes)
                    )
                    self.assertTrue(normalized["pass"], normalized["notes"])
                    response_size = eval_run._canonical_judge_response_size(
                        case, notes
                    )
                    self.assertEqual(response_size, empty_size + payload_size)
                    self.assertLessEqual(response_size, preflight_size)
                    self.assertLessEqual(
                        response_size, eval_run.JUDGE_RESPONSE_MAX_BYTES
                    )
                    failing_size = eval_run._judge_response_size(
                        case,
                        notes,
                        criterion_met=False,
                        dimension_score=0,
                        overall_score=0,
                        passed=False,
                    )
                    self.assertLessEqual(failing_size, preflight_size)
                    self.assertLessEqual(
                        failing_size, eval_run.JUDGE_RESPONSE_MAX_BYTES
                    )

    def test_fenced_json_compatibility_survives_escaped_notes(self) -> None:
        case = self.cases[0]
        notes = 'quoted " value, slash \\, and nul \x00'
        raw = f"```json\n{compact_json(response_for(case, notes=notes))}\n```"
        with mock.patch.object(eval_run, "call_api", return_value=raw):
            verdict = eval_run.judge(
                case,
                "candidate response",
                self.model,
                "key",
                "rubric",
                self.provider,
                self.endpoint,
            )
        normalized = eval_run.normalize_verdict(case, verdict)
        self.assertEqual(normalized["status"], "scored")
        self.assertTrue(normalized["pass"], normalized["notes"])
        self.assertEqual(normalized["notes"], notes)

    def test_missing_unknown_and_wrong_typed_ids_fail_closed(self) -> None:
        case = self.sequence_case
        valid = response_for(case)
        mutations = []

        missing = copy.deepcopy(valid)
        missing["criterion_scores"].pop(next(iter(missing["criterion_scores"])))
        mutations.append(missing)

        wrong_type = copy.deepcopy(valid)
        wrong_type["criterion_scores"]["a0"] = "true"
        mutations.append(wrong_type)

        unknown = copy.deepcopy(valid)
        unknown["dimension_scores"].pop("d10")
        unknown["dimension_scores"]["d99"] = 4
        mutations.append(unknown)

        verbose = copy.deepcopy(valid)
        verbose["model_authored_echo"] = "trust me"
        mutations.append(verbose)

        for verdict in mutations:
            with self.subTest(verdict=verdict):
                normalized = eval_run.normalize_verdict(case, verdict)
                self.assertEqual(normalized["status"], "harness_error")
                self.assertIsNone(normalized["overall_score"])
                self.assertIsNone(normalized["pass"])
                self.assertIn("invalid judge verdict", normalized["notes"])

    def test_duplicate_nested_criterion_id_is_rejected_by_strict_json(self) -> None:
        case = self.cases[0]
        raw = compact_json(response_for(case))
        raw = raw.replace('"a0":true', '"a0":true,"a0":false', 1)
        with self.assertRaisesRegex(eval_run.HarnessError, "invalid JSON"):
            eval_run.parse_json_object(raw, "judge")

    def test_raw_judge_response_over_900_bytes_is_rejected_before_parsing(self) -> None:
        case = self.cases[0]
        oversized = compact_json(response_for(case)) + (
            " " * eval_run.JUDGE_RESPONSE_MAX_BYTES
        )
        with (
            mock.patch.object(eval_run, "call_api", return_value=oversized),
            self.assertRaisesRegex(eval_run.HarnessError, "900-byte"),
        ):
            eval_run.judge(
                case,
                "candidate response",
                self.model,
                "key",
                "rubric",
                self.provider,
                self.endpoint,
            )

    def test_judge_context_is_bounded_before_the_provider_call(self) -> None:
        case = self.cases[0]
        with (
            mock.patch.object(eval_run, "MAX_JUDGE_CONTEXT_CHARACTERS", 100),
            mock.patch.object(eval_run, "call_api") as call,
            self.assertRaisesRegex(eval_run.HarnessError, "judge context exceeds"),
        ):
            eval_run.judge(
                case,
                "candidate response",
                self.model,
                "key",
                "rubric",
                self.provider,
                self.endpoint,
            )
        call.assert_not_called()

    def test_partial_and_unknown_sequence_contracts_fail_validation(self) -> None:
        base = copy.deepcopy(self.sequence_case)
        invalid_cases = []

        partial = copy.deepcopy(base)
        del partial["expected_state_delta"]
        invalid_cases.append(partial)

        unknown = copy.deepcopy(base)
        unknown["expected_sequence_relation"] = "invented_relation"
        invalid_cases.append(unknown)

        blank = copy.deepcopy(base)
        blank["expected_prompt_architecture"] = " "
        invalid_cases.append(blank)

        for field in (
            "expected_state_delta",
            "expected_prompt_architecture",
            "expected_sequence_relation",
        ):
            oversized = copy.deepcopy(base)
            oversized[field] = "x" * (eval_run.MAX_CASE_LIST_ITEM_CHARACTERS + 1)
            invalid_cases.append(oversized)

        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(eval_run.HarnessError):
                    eval_run.validate_case_contract(self.snapshot, [case])


if __name__ == "__main__":
    unittest.main()

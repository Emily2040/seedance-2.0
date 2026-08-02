"""Adversarial coverage for the provider-aware live-eval integrity boundary."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import eval_run  # noqa: E402


EXACT_RUBRIC = (
    "Score 0 to 3. Sequence scale 0-4.\n\nDimensions: "
    + ", ".join(eval_run.SEQUENCE_DIMENSIONS)
    + ".\n"
)


def result_row(
    case_id: str = "case-1",
    *,
    score: object = 3,
    passed: object = True,
    sequence: object = False,
    critical: object = False,
) -> dict:
    return {
        "id": case_id,
        "score": score,
        "pass": passed,
        "sequence": sequence,
        "critical": critical,
        "notes": "test verdict",
        "dimension_scores": (
            [
                {"dimension": dimension, "score": 4}
                for dimension in eval_run.SEQUENCE_DIMENSIONS
            ]
            if sequence is True
            else []
        ),
    }


def case_metadata(
    case_id: str = "case-1",
    *,
    sequence: bool = False,
    critical: bool = False,
) -> dict[str, dict[str, bool]]:
    case: dict[str, object] = {"id": case_id, "critical": critical}
    if sequence:
        case["expected_sequence_relation"] = "standalone"
    return eval_run.build_expected_case_metadata([case])


def valid_verdict(assertions: tuple[str, ...] = ("works",), score: int = 3) -> dict:
    return {
        "overall_score": score,
        "pass": True,
        "notes": "ok",
        "assertion_scores": [
            {"assertion": assertion, "met": True} for assertion in assertions
        ],
        "dimension_scores": [],
    }


class AggregateIntegrityTests(unittest.TestCase):
    def aggregate(self, rows: list[dict], **kwargs: object) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = eval_run.aggregate(rows, **kwargs)
        return code, output.getvalue()

    def test_empty_run_fails_closed(self) -> None:
        code, output = self.aggregate([])

        self.assertEqual(code, 1)
        self.assertIn("no scored results", output.lower())
        self.assertIn("RESULT: FAIL", output)

    def test_failed_judge_verdict_cannot_pass_on_score_alone(self) -> None:
        code, output = self.aggregate([result_row(score=3, passed=False)])

        self.assertEqual(code, 1)
        self.assertIn("failed verdict", output.lower())

    def test_valid_rows_without_release_universe_are_not_release_eligible(self) -> None:
        code, output = self.aggregate([result_row()])

        self.assertEqual(code, 1)
        self.assertIn("UNSCOPED", output)
        self.assertIn("not release-eligible", output)

    def test_total_expected_mismatch_forces_partial_not_eligible(self) -> None:
        report = eval_run.assess_run(
            [result_row("one")],
            expected_cases=case_metadata("one"),
            release_eligible=True,
            total_expected=50,
        )

        self.assertEqual(report["scope"], "PARTIAL")
        self.assertEqual(report["selected_count"], 1)
        self.assertEqual(report["total_expected"], 50)
        self.assertEqual(report["release_verdict"], "NOT ELIGIBLE")
        self.assertEqual(report["exit_code"], 1)

    def test_expected_ids_without_total_do_not_infer_a_release_universe(self) -> None:
        report = eval_run.assess_run(
            [result_row()],
            expected_ids=["case-1"],
            release_eligible=True,
        )

        self.assertEqual(report["scope"], "UNSCOPED")
        self.assertIsNone(report["total_expected"])
        self.assertEqual(report["release_verdict"], "NOT ELIGIBLE")
        self.assertEqual(report["exit_code"], 1)

    def test_ids_and_total_without_canonical_metadata_remain_unscoped(self) -> None:
        report = eval_run.assess_run(
            [result_row()],
            expected_ids=["case-1"],
            total_expected=1,
            release_eligible=True,
        )

        self.assertEqual(report["scope"], "UNSCOPED")
        self.assertEqual(report["release_verdict"], "NOT ELIGIBLE")

    def test_explicit_one_case_canonical_universe_can_pass(self) -> None:
        report = eval_run.assess_run(
            [result_row()],
            expected_cases=case_metadata(),
            total_expected=1,
            release_eligible=True,
        )

        self.assertEqual(report["scope"], "COMPLETE")
        self.assertEqual(report["run_verdict"], "PASS")
        self.assertEqual(report["release_verdict"], "PASS")
        self.assertEqual(report["exit_code"], 0)

    def test_release_eligibility_requires_an_exact_boolean(self) -> None:
        for release_eligible in ("false", 1, None):
            with self.subTest(release_eligible=release_eligible):
                report = eval_run.assess_run(
                    [result_row()],
                    expected_cases=case_metadata(),
                    total_expected=1,
                    release_eligible=release_eligible,
                )

                self.assertIn(
                    "release_eligible must be a boolean",
                    report["integrity_errors"],
                )
                self.assertEqual(report["scope"], "PARTIAL")
                self.assertEqual(report["release_verdict"], "NOT ELIGIBLE")
                self.assertEqual(report["exit_code"], 1)

    def test_duplicate_expected_ids_are_checked_before_canonical_replacement(self) -> None:
        report = eval_run.assess_run(
            [result_row()],
            expected_ids=["case-1", "case-1"],
            expected_cases=case_metadata(),
            total_expected=1,
            release_eligible=True,
        )

        self.assertIn("duplicate expected ids: case-1", report["integrity_errors"])
        self.assertEqual(report["scope"], "PARTIAL")
        self.assertEqual(report["release_verdict"], "NOT ELIGIBLE")

    def test_sequence_floor_uses_dimension_scores_not_overall_score(self) -> None:
        row = result_row(
            "sequence",
            score=4,
            passed=True,
            sequence=True,
            critical=True,
        )
        row["dimension_scores"][0]["score"] = 2

        report = eval_run.assess_run(
            [row],
            expected_cases=case_metadata(
                "sequence", sequence=True, critical=True
            ),
            release_eligible=True,
            total_expected=1,
        )

        self.assertEqual(report["sequence_floor_fail"], ["sequence"])
        self.assertEqual(report["release_verdict"], "FAIL")

    def test_critical_rows_cannot_claim_the_legacy_scale(self) -> None:
        report = eval_run.assess_run(
            [result_row("critical", sequence=False, critical=True)],
            expected_cases=case_metadata(
                "critical", sequence=True, critical=True
            ),
            total_expected=1,
            release_eligible=True,
        )

        self.assertEqual(report["run_verdict"], "FAIL")
        self.assertEqual(report["release_verdict"], "FAIL")
        self.assertTrue(
            any("critical cases must be sequence cases" in error for error in report["integrity_errors"])
        )

    def test_canonical_metadata_rejects_forged_false_false_sequence_row(self) -> None:
        case_id = "sequence_long_idea_routes_to_plan"
        report = eval_run.assess_run(
            [result_row(case_id, sequence=False, critical=False)],
            expected_cases=case_metadata(
                case_id, sequence=True, critical=True
            ),
            total_expected=1,
            release_eligible=True,
        )

        self.assertEqual(report["run_verdict"], "FAIL")
        self.assertEqual(report["release_verdict"], "FAIL")
        self.assertTrue(
            any("sequence flag does not match" in error for error in report["integrity_errors"])
        )
        self.assertTrue(
            any("critical flag does not match" in error for error in report["integrity_errors"])
        )

    def test_malformed_non_finite_and_out_of_range_scores_fail_closed(self) -> None:
        bad_scores = (True, "3", 3.0, float("nan"), float("inf"), -1, 4)
        for score in bad_scores:
            with self.subTest(score=score):
                code, output = self.aggregate([result_row(score=score)])
                self.assertEqual(code, 1)
                self.assertIn("invalid score", output.lower())

        code, output = self.aggregate(
            [result_row(score=5, sequence=True, critical=True)]
        )
        self.assertEqual(code, 1)
        self.assertIn("invalid score", output.lower())

    def test_missing_duplicate_and_unexpected_rows_fail_integrity(self) -> None:
        cases = (
            ([result_row("a")], ["a", "b"]),
            ([result_row("a"), result_row("a")], ["a"]),
            ([result_row("a"), result_row("c")], ["a", "b"]),
        )
        for rows, expected in cases:
            with self.subTest(rows=rows, expected=expected):
                code, output = self.aggregate(rows, expected_ids=expected)
                self.assertEqual(code, 1)
                self.assertIn("integrity", output.lower())


class JudgeIntegrityTests(unittest.TestCase):
    CASE = {"prompt": "test", "assertions": ["works"]}

    def test_call_api_rejects_malformed_success_body(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"{not-json"
        with mock.patch.object(
            eval_run.urllib.request, "urlopen", return_value=response
        ):
            with self.assertRaisesRegex(
                eval_run.ProviderResponseError, "invalid JSON"
            ):
                eval_run.call_api(
                    "system", "user", model, "key", provider, endpoint
                )

    def test_call_api_bounds_success_response_before_json_decoding(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = (
            b"x" * (eval_run.MAX_PROVIDER_RESPONSE_BYTES + 1)
        )
        with mock.patch.object(
            eval_run.urllib.request, "urlopen", return_value=response
        ):
            with self.assertRaisesRegex(
                eval_run.ProviderResponseError, "response exceeded"
            ):
                eval_run.call_api(
                    "system", "user", model, "key", provider, endpoint
                )
        response.__enter__.return_value.read.assert_called_once_with(
            eval_run.MAX_PROVIDER_RESPONSE_BYTES + 1
        )

    def test_call_api_wraps_incomplete_response_reads(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        response = mock.MagicMock()
        response.__enter__.return_value.read.side_effect = (
            eval_run.http.client.IncompleteRead(b"partial")
        )
        with mock.patch.object(
            eval_run.urllib.request, "urlopen", return_value=response
        ):
            with self.assertRaisesRegex(
                eval_run.ProviderResponseError, "could not be read"
            ):
                eval_run.call_api(
                    "system", "user", model, "key", provider, endpoint
                )

    def test_call_api_wraps_transport_failures_at_open_enter_and_read(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        open_failures = (
            eval_run.http.client.BadStatusLine("malformed status"),
            ConnectionResetError("reset while opening"),
        )
        for failure in open_failures:
            with self.subTest(boundary="open", failure=type(failure).__name__):
                with mock.patch.object(
                    eval_run.urllib.request, "urlopen", side_effect=failure
                ):
                    with self.assertRaisesRegex(
                        eval_run.ProviderResponseError, "could not be read"
                    ):
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        )

        for boundary in ("enter", "read"):
            with self.subTest(boundary=boundary):
                response = mock.MagicMock()
                if boundary == "enter":
                    response.__enter__.side_effect = ConnectionResetError(
                        "reset entering response"
                    )
                else:
                    response.__enter__.return_value.read.side_effect = (
                        ConnectionResetError("reset reading response")
                    )
                with mock.patch.object(
                    eval_run.urllib.request, "urlopen", return_value=response
                ):
                    with self.assertRaisesRegex(
                        eval_run.ProviderResponseError, "could not be read"
                    ):
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        )

    def test_call_api_preserves_http_error_diagnostics(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        error = eval_run.urllib.error.HTTPError(
            endpoint, 503, "provider unavailable", {}, None
        )
        with mock.patch.object(
            eval_run.urllib.request, "urlopen", side_effect=error
        ):
            with self.assertRaises(eval_run.urllib.error.HTTPError) as raised:
                eval_run.call_api(
                    "system", "user", model, "key", provider, endpoint
                )

        self.assertIs(raised.exception, error)

    def test_provider_envelopes_reject_duplicate_keys_and_nonstandard_constants(self) -> None:
        invalid_bodies = {
            "duplicate content": (
                b'{"content":[{"type":"text","text":"first"}],'
                b'"content":[{"type":"text","text":"second"}]}'
            ),
            "NaN": (
                b'{"content":[{"type":"text","text":"ok"}],'
                b'"usage":{"input_tokens":NaN}}'
            ),
            "Infinity": (
                b'{"content":[{"type":"text","text":"ok"}],'
                b'"usage":{"input_tokens":Infinity}}'
            ),
        }
        providers = (
            ("anthropic", "global_en", None),
            ("minimax", "global_en", "MiniMax-M3"),
            ("minimax", "cn_zh", "MiniMax-M2.7"),
        )
        for provider_name, region, requested_model in providers:
            provider, endpoint, model = eval_run.resolve_provider(
                provider_name, region, requested_model
            )
            for label, body in invalid_bodies.items():
                with self.subTest(provider=provider_name, region=region, body=label):
                    response = mock.MagicMock()
                    response.__enter__.return_value.read.return_value = body
                    with mock.patch.object(
                        eval_run.urllib.request, "urlopen", return_value=response
                    ):
                        with self.assertRaisesRegex(
                            eval_run.ProviderResponseError, "invalid JSON"
                        ):
                            eval_run.call_api(
                                "system",
                                "user",
                                model,
                                "key",
                                provider,
                                endpoint,
                            )

    def test_provider_text_blocks_require_string_text_for_every_provider(self) -> None:
        invalid_bodies = (
            b'{"content":[{"type":"text","text":"ok"},{"type":"text"}]}',
            b'{"content":[{"type":"text","text":"ok"},{"type":"text","text":7}]}',
            b'{"content":[{"type":"text","text":"\\ud800"}]}',
        )
        providers = (
            ("anthropic", "global_en", None),
            ("minimax", "global_en", "MiniMax-M3"),
            ("minimax", "cn_zh", "MiniMax-M2.7"),
        )
        for provider_name, region, requested_model in providers:
            provider, endpoint, model = eval_run.resolve_provider(
                provider_name, region, requested_model
            )
            for body in invalid_bodies:
                with self.subTest(provider=provider_name, region=region, body=body):
                    response = mock.MagicMock()
                    response.__enter__.return_value.read.return_value = body
                    with mock.patch.object(
                        eval_run.urllib.request, "urlopen", return_value=response
                    ):
                        with self.assertRaises(eval_run.ProviderResponseError):
                            eval_run.call_api(
                                "system",
                                "user",
                                model,
                                "key",
                                provider,
                                endpoint,
                            )

    def test_provider_envelope_allows_unknown_non_text_blocks(self) -> None:
        body = (
            b'{"content":[{"type":"future_block","payload":{"x":1}},'
            b'{"type":"text","text":"ok"}]}'
        )
        for provider_name, region, requested_model in (
            ("anthropic", "global_en", None),
            ("minimax", "cn_zh", "MiniMax-M3"),
        ):
            provider, endpoint, model = eval_run.resolve_provider(
                provider_name, region, requested_model
            )
            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = body
            with mock.patch.object(
                eval_run.urllib.request, "urlopen", return_value=response
            ):
                self.assertEqual(
                    eval_run.call_api(
                        "system", "user", model, "key", provider, endpoint
                    ),
                    "ok",
                )

    def test_judge_threads_selected_provider_and_endpoint_to_api(self) -> None:
        provider, endpoint, _model = eval_run.resolve_provider(
            "minimax", "cn_zh", "MiniMax-M2.7"
        )
        raw = json.dumps(valid_verdict())
        with mock.patch.object(eval_run, "call_api", return_value=raw) as call:
            eval_run.judge(
                self.CASE,
                "candidate",
                "MiniMax-M2.7",
                "key",
                "rubric",
                provider,
                endpoint,
            )

        call.assert_called_once_with(
            mock.ANY,
            mock.ANY,
            "MiniMax-M2.7",
            "key",
            provider,
            endpoint,
            max_tokens=900,
        )

    def test_non_standard_json_constants_are_rejected(self) -> None:
        raw = '{"overall_score":NaN,"pass":true,"notes":"bad"}'
        provider, endpoint, _model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        with mock.patch.object(eval_run, "call_api", return_value=raw):
            verdict = eval_run.judge(
                self.CASE,
                "candidate",
                "model",
                "key",
                "rubric",
                provider,
                endpoint,
            )

        self.assertEqual(verdict["overall_score"], 0)
        self.assertIs(verdict["pass"], False)
        self.assertIn("unparseable", verdict["notes"])

    def test_duplicate_json_keys_are_rejected(self) -> None:
        raw = (
            '{"overall_score":0,"overall_score":3,'
            '"pass":false,"pass":true,"notes":"ambiguous",'
            '"assertion_scores":[{"assertion":"works","met":true}]}'
        )
        provider, endpoint, _model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        with mock.patch.object(eval_run, "call_api", return_value=raw):
            verdict = eval_run.judge(
                self.CASE,
                "candidate",
                "model",
                "key",
                "rubric",
                provider,
                endpoint,
            )

        self.assertEqual(verdict["overall_score"], 0)
        self.assertIs(verdict["pass"], False)
        self.assertIn("unparseable", verdict["notes"])

    def test_unpaired_surrogate_in_judge_json_is_rejected(self) -> None:
        raw = (
            '{"overall_score":3,"pass":true,"notes":"\\ud800",'
            '"assertion_scores":[{"assertion":"works","met":true}],'
            '"dimension_scores":[]}'
        )
        provider, endpoint, _model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        with mock.patch.object(eval_run, "call_api", return_value=raw):
            verdict = eval_run.judge(
                self.CASE,
                "candidate",
                "model",
                "key",
                "rubric",
                provider,
                endpoint,
            )

        self.assertEqual(verdict["overall_score"], 0)
        self.assertIs(verdict["pass"], False)
        self.assertIn("unparseable", verdict["notes"])

    def test_verdict_normalization_rejects_every_invalid_score_shape(self) -> None:
        bad_scores = (True, "3", 3.0, float("nan"), float("inf"), -1, 4)
        for score in bad_scores:
            with self.subTest(score=score):
                verdict = eval_run.normalize_verdict(
                    self.CASE,
                    {
                        "overall_score": score,
                        "pass": True,
                        "notes": "looks fine",
                        "assertion_scores": [{"assertion": "works", "met": True}],
                    },
                )
                self.assertEqual(verdict["overall_score"], 0)
                self.assertIs(verdict["pass"], False)
                self.assertIn("invalid judge verdict", verdict["notes"])

        verdict = eval_run.normalize_verdict(
            self.CASE,
            {
                "overall_score": 3,
                "pass": "true",
                "notes": "wrong type",
                "assertion_scores": [{"assertion": "works", "met": True}],
            },
        )
        self.assertEqual(verdict["overall_score"], 0)
        self.assertIs(verdict["pass"], False)
        self.assertIn("pass must be a boolean", verdict["notes"])

    def test_assertion_scores_must_cover_each_assertion_exactly_once(self) -> None:
        case = {"prompt": "test", "assertions": ["works", "is safe"]}
        invalid_rows = (
            [{"assertion": "works", "met": True}],
            [
                {"assertion": "works", "met": True},
                {"assertion": "works", "met": True},
            ],
            [
                {"assertion": "works", "met": True},
                {"assertion": "is safe", "met": False},
            ],
        )
        for assertion_scores in invalid_rows:
            with self.subTest(assertion_scores=assertion_scores):
                verdict = eval_run.normalize_verdict(
                    case,
                    {
                        "overall_score": 3,
                        "pass": True,
                        "notes": "trust me",
                        "assertion_scores": assertion_scores,
                    },
                )
                self.assertEqual(verdict["overall_score"], 0)
                self.assertIs(verdict["pass"], False)
                self.assertIn("invalid judge verdict", verdict["notes"])

    def test_required_sections_and_forbidden_behaviors_are_scored_checks(self) -> None:
        case = {
            "prompt": "test",
            "assertions": ["works"],
            "required_output_sections": ["Final prompt"],
            "forbidden_behaviors": ["invented dialogue"],
        }
        ordinary_only = eval_run.normalize_verdict(case, valid_verdict())
        self.assertEqual(ordinary_only["overall_score"], 0)
        self.assertFalse(ordinary_only["pass"])
        self.assertIn("cover every judge check exactly once", ordinary_only["notes"])

        checks = eval_run.expected_judge_checks(case)
        forbidden_unmet = eval_run.normalize_verdict(
            case,
            {
                "overall_score": 3,
                "pass": True,
                "notes": "trust me",
                "assertion_scores": [
                    {
                        "assertion": check,
                        "met": not check.startswith("[forbidden_behavior_absent]"),
                    }
                    for check in checks
                ],
            },
        )
        self.assertEqual(forbidden_unmet["overall_score"], 0)
        self.assertFalse(forbidden_unmet["pass"])
        self.assertIn("pass cannot be true", forbidden_unmet["notes"])

    def test_sequence_verdict_requires_every_rubric_dimension(self) -> None:
        case = {"prompt": "test", "assertions": ["works"], "critical": True}
        verdict = eval_run.normalize_verdict(
            case,
            {
                "overall_score": 4,
                "pass": True,
                "notes": "looks complete",
                "assertion_scores": [{"assertion": "works", "met": True}],
                "dimension_scores": [
                    {"dimension": dimension, "score": 4}
                    for dimension in eval_run.SEQUENCE_DIMENSIONS[:-1]
                ],
            },
        )

        self.assertEqual(verdict["overall_score"], 0)
        self.assertFalse(verdict["pass"])
        self.assertIn("every sequence dimension exactly once", verdict["notes"])


class InputContractTests(unittest.TestCase):
    def write_case_repo(self, root: Path, first_case: dict) -> None:
        (root / "evals").mkdir(parents=True)
        (root / "references").mkdir()
        (root / "skills").mkdir()
        (root / "SKILL.md").write_text("# test skill\n", encoding="utf-8")
        (root / "references" / "eval-rubric.md").write_text(
            EXACT_RUBRIC, encoding="utf-8"
        )
        cases = [first_case]
        cases.extend(
            {
                "id": f"valid-{index}",
                "prompt": "test",
                "assertions": ["works"],
            }
            for index in range(2, 17)
        )
        (root / "evals" / "evals.json").write_text(
            json.dumps({"cases": cases}), encoding="utf-8"
        )

    def test_self_test_rejects_unhashable_case_ids_without_a_traceback(self) -> None:
        for invalid_id in ([], {}):
            with self.subTest(invalid_id=invalid_id), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "evals").mkdir()
                (root / "references").mkdir()
                (root / "SKILL.md").write_text("# test skill\n", encoding="utf-8")
                (root / "references" / "eval-rubric.md").write_text(
                    EXACT_RUBRIC, encoding="utf-8"
                )
                cases = [
                    {
                        "id": invalid_id,
                        "prompt": "test",
                        "assertions": ["works"],
                    }
                ]
                (root / "evals" / "evals.json").write_text(
                    json.dumps({"cases": cases}), encoding="utf-8"
                )

                output = io.StringIO()
                with redirect_stdout(output):
                    code = eval_run.self_test(root)

                self.assertEqual(code, 1)
                self.assertIn("id must be a non-empty UTF-8 string", output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())

    def test_deeply_nested_eval_json_fails_cleanly_at_both_cli_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evals").mkdir()
            nested_id = "[" * 1100 + '"x"' + "]" * 1100
            (root / "evals" / "evals.json").write_text(
                '{"cases":[{"id":'
                + nested_id
                + ',"prompt":"test","assertions":["works"]}]}',
                encoding="utf-8",
            )

            for argv, expected_code, expected_message in (
                (["eval_run.py", str(root), "--self-test"], 1, "self-test FAILED"),
                (["eval_run.py", str(root)], 2, "Could not load eval cases"),
            ):
                with self.subTest(argv=argv):
                    output = io.StringIO()
                    with mock.patch.object(sys, "argv", argv), redirect_stdout(output):
                        code = eval_run.main()
                    self.assertEqual(code, expected_code)
                    self.assertIn(expected_message, output.getvalue())
                    self.assertIn("supported depth", output.getvalue())
                    self.assertNotIn("Traceback", output.getvalue())

    def test_self_test_rejects_malformed_case_collections_without_tracebacks(self) -> None:
        mutations = (
            ("assertions", None, "assertions must be a list"),
            ("assertions", [{}], "assertions must contain only"),
            (
                "skills_expected_to_activate",
                [[]],
                "skills_expected_to_activate must contain only",
            ),
            (
                "required_output_sections",
                {},
                "required_output_sections must be a list",
            ),
            ("forbidden_behaviors", [None], "forbidden_behaviors must contain only"),
            (
                "state_fixture",
                [],
                "state_fixture must be a non-empty UTF-8 repository-relative file",
            ),
            ("critical", [], "critical must be a boolean when present"),
            (
                "expected_sequence_relation",
                None,
                "expected_sequence_relation must be a non-empty UTF-8 string",
            ),
        )
        for field, value, expected in mutations:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "evals").mkdir()
                (root / "references").mkdir()
                (root / "SKILL.md").write_text("# test skill\n", encoding="utf-8")
                (root / "references" / "eval-rubric.md").write_text(
                    EXACT_RUBRIC, encoding="utf-8"
                )
                case = {"id": "one", "prompt": "test", "assertions": ["works"]}
                case[field] = value
                (root / "evals" / "evals.json").write_text(
                    json.dumps({"cases": [case]}), encoding="utf-8"
                )

                output = io.StringIO()
                with redirect_stdout(output):
                    code = eval_run.self_test(root)

                self.assertEqual(code, 1)
                self.assertIn(expected, output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())

    def test_self_test_rejects_escaping_or_non_file_case_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            outside_file = sandbox / "outside-state.txt"
            outside_file.write_text("OUTSIDE-STATE-SENTINEL", encoding="utf-8")
            outside_skill = sandbox / "outside-skill"
            outside_skill.mkdir()
            (outside_skill / "SKILL.md").write_text(
                "OUTSIDE-SKILL-SENTINEL", encoding="utf-8"
            )
            mutations = (
                ("state_fixture", "."),
                ("state_fixture", "missing-state.json"),
                ("state_fixture", "bad\x00state.json"),
                ("state_fixture", "fixtures/state.json:alternate"),
                ("state_fixture", "../outside-state.txt"),
                ("state_fixture", str(outside_file)),
                ("skills_expected_to_activate", ["bad\x00skill"]),
                ("skills_expected_to_activate", ["../../outside-skill"]),
                ("skills_expected_to_activate", [str(outside_skill)]),
            )
            for index, (field, value) in enumerate(mutations):
                with self.subTest(field=field, value=value):
                    root = sandbox / f"repo-{index}"
                    case = {"id": "one", "prompt": "test", "assertions": ["works"]}
                    case[field] = value
                    self.write_case_repo(root, case)

                    output = io.StringIO()
                    with redirect_stdout(output):
                        code = eval_run.self_test(root)

                    self.assertEqual(code, 1)
                    self.assertNotIn("Traceback", output.getvalue())
                    self.assertNotIn("OUTSIDE-STATE-SENTINEL", output.getvalue())
                    self.assertNotIn("OUTSIDE-SKILL-SENTINEL", output.getvalue())

    def test_nonportable_aliases_are_rejected_before_live_provider_calls(self) -> None:
        mutations = (
            ("state_fixture", "fixtures/state.json."),
            ("state_fixture", "fixtures/state.json "),
            ("state_fixture", "Fixtures/State.JSON"),
            ("state_fixture", "fixtures/./state.json"),
            ("state_fixture", "fixtures//state.json"),
            ("state_fixture", "fixtures/NUL.json"),
            ("state_fixture", "fixtures/cafe\u0301.json"),
            ("state_fixture", "fixtures/state\u200d.json"),
            ("state_fixture", "fixtures/state\u034f.json"),
            ("state_fixture", "fixtures/state\x7f.json"),
            ("skills_expected_to_activate", ["seedance-prompt."]),
            ("skills_expected_to_activate", ["SEEDANCE-PROMPT"]),
            ("skills_expected_to_activate", ["CON"]),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                case = {"id": "one", "prompt": "test", "assertions": ["works"]}
                case[field] = value
                self.write_case_repo(root, case)
                fixture = root / "fixtures" / "state.json"
                fixture.parent.mkdir()
                fixture.write_text("INSIDE-STATE-SENTINEL", encoding="utf-8")
                skill = root / "skills" / "seedance-prompt" / "SKILL.md"
                skill.parent.mkdir()
                skill.write_text("INSIDE-SKILL-SENTINEL", encoding="utf-8")

                self_output = io.StringIO()
                with redirect_stdout(self_output):
                    self_code = eval_run.self_test(root)
                self.assertEqual(self_code, 1, self_output.getvalue())
                self.assertNotIn("Traceback", self_output.getvalue())

                api_call = mock.Mock(return_value="candidate response")
                live_output = io.StringIO()
                with (
                    mock.patch.object(
                        sys, "argv", ["eval_run.py", str(root), "--limit", "1"]
                    ),
                    mock.patch.dict(
                        os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                    ),
                    mock.patch.object(eval_run, "call_api", api_call),
                    redirect_stdout(live_output),
                ):
                    live_code = eval_run.main()
                self.assertEqual(live_code, 2, live_output.getvalue())
                self.assertIn("case contract validation failed", live_output.getvalue())
                self.assertNotIn("Traceback", live_output.getvalue())
                api_call.assert_not_called()

    def test_portable_exact_case_paths_and_backslashes_remain_valid(self) -> None:
        cases = (
            ("state_fixture", "fixtures/state.json", "INSIDE-STATE-SENTINEL"),
            ("state_fixture", r"fixtures\state.json", "INSIDE-STATE-SENTINEL"),
            (
                "skills_expected_to_activate",
                ["seedance-prompt"],
                "INSIDE-SKILL-SENTINEL",
            ),
        )
        for field, value, marker in cases:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                case = {"id": "one", "prompt": "test", "assertions": ["works"]}
                case[field] = value
                self.write_case_repo(root, case)
                fixture = root / "fixtures" / "state.json"
                fixture.parent.mkdir()
                fixture.write_text("INSIDE-STATE-SENTINEL", encoding="utf-8")
                skill = root / "skills" / "seedance-prompt" / "SKILL.md"
                skill.parent.mkdir()
                skill.write_text("INSIDE-SKILL-SENTINEL", encoding="utf-8")

                label, errors = eval_run.case_contract_errors(root, case, 0)
                self.assertEqual(label, "one")
                self.assertEqual(errors, [])
                self.assertIn(marker, eval_run.responder_context(root, case))

    def test_responder_context_binds_every_repository_input_identity(self) -> None:
        cases = (
            (
                "skill 'seedance-20'",
                {"id": "one", "prompt": "test", "assertions": ["works"]},
                1,
            ),
            (
                "skill 'seedance-prompt'",
                {
                    "id": "one",
                    "prompt": "test",
                    "assertions": ["works"],
                    "skills_expected_to_activate": ["seedance-prompt"],
                },
                1,
            ),
            (
                "state_fixture",
                {
                    "id": "one",
                    "prompt": "test",
                    "assertions": ["works"],
                    "state_fixture": "fixtures/state.json",
                },
                2,
            ),
        )
        for target_field, case, original_resolutions in cases:
            with self.subTest(target_field=target_field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.write_case_repo(root, case)
                skill = root / "skills" / "seedance-prompt" / "SKILL.md"
                skill.parent.mkdir()
                skill.write_text("ORIGINAL-SKILL", encoding="utf-8")
                fixture = root / "fixtures" / "state.json"
                fixture.parent.mkdir()
                fixture.write_text("ORIGINAL-STATE", encoding="utf-8")
                replacement = root / "replacement.txt"
                replacement.write_text("REPLACEMENT", encoding="utf-8")
                original_resolve = eval_run._resolve_repo_file
                resolutions = 0

                def swap_identity(
                    candidate_root: Path, relative: str, field: str
                ) -> Path:
                    nonlocal resolutions
                    resolved = original_resolve(candidate_root, relative, field)
                    if field != target_field:
                        return resolved
                    resolutions += 1
                    return resolved if resolutions <= original_resolutions else replacement

                with mock.patch.object(
                    eval_run, "_resolve_repo_file", swap_identity
                ), self.assertRaisesRegex(ValueError, "changed while it was being read"):
                    eval_run.responder_context(root, case)

    def test_eval_case_file_is_read_from_one_bound_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = {"id": "one", "prompt": "test", "assertions": ["works"]}
            self.write_case_repo(root, case)
            replacement = root / "replacement-evals.json"
            replacement.write_text(
                json.dumps({"cases": [case]}), encoding="utf-8"
            )
            original_resolve = eval_run._resolve_repo_file
            resolutions = 0

            def swap_eval_identity(
                candidate_root: Path, relative: str, field: str
            ) -> Path:
                nonlocal resolutions
                resolved = original_resolve(candidate_root, relative, field)
                if field != "evals/evals.json":
                    return resolved
                resolutions += 1
                return resolved if resolutions == 1 else replacement

            with mock.patch.object(
                eval_run, "_resolve_repo_file", swap_eval_identity
            ), self.assertRaisesRegex(ValueError, "changed while it was being read"):
                eval_run.load_cases(root)

    def test_live_mode_rejects_case_contract_before_provider_calls(self) -> None:
        mutations = (
            ("id", "UPPERCASE"),
            ("id", "line\nbreak"),
            ("id", "x" * (eval_run.MAX_CASE_ID_CHARACTERS + 1)),
            ("prompt", "x" * (eval_run.MAX_PROMPT_CHARACTERS + 1)),
            ("assertions", None),
            ("assertions", ["works", "works"]),
            ("required_output_sections", {}),
            ("required_output_sections", ["A", "A"]),
            ("forbidden_behaviors", [{}]),
            ("forbidden_behaviors", ["A", "A"]),
            ("skills_expected_to_activate", ["../outside-skill"]),
            ("skills_expected_to_activate", ["seedance-20", "seedance-20"]),
            ("state_fixture", "."),
            ("critical", []),
            ("expected_sequence_relation", None),
        )
        for field, value in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                case = {"id": "one", "prompt": "test", "assertions": ["works"]}
                case[field] = value
                self.write_case_repo(root, case)
                api_call = mock.Mock(return_value="candidate response")
                output = io.StringIO()
                with (
                    mock.patch.object(
                        sys, "argv", ["eval_run.py", str(root), "--limit", "1"]
                    ),
                    mock.patch.dict(
                        os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                    ),
                    mock.patch.object(eval_run, "call_api", api_call),
                    redirect_stdout(output),
                ):
                    code = eval_run.main()

                self.assertEqual(code, 2)
                self.assertIn("case contract validation failed", output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())
                api_call.assert_not_called()

    def test_live_mode_preflights_all_selected_contexts_before_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = {"id": "one", "prompt": "test", "assertions": ["works"]}
            self.write_case_repo(root, first)
            eval_path = root / "evals" / "evals.json"
            data = json.loads(eval_path.read_text(encoding="utf-8"))
            data["cases"][1]["state_fixture"] = "fixtures/bad-state.json"
            eval_path.write_text(json.dumps(data), encoding="utf-8")
            fixture = root / "fixtures" / "bad-state.json"
            fixture.parent.mkdir()
            fixture.write_bytes(b"\xff\xfe\x00")

            api_call = mock.Mock(return_value="candidate response")
            output = io.StringIO()
            with (
                mock.patch.object(sys, "argv", ["eval_run.py", str(root)]),
                mock.patch.dict(
                    os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                ),
                mock.patch.object(eval_run, "call_api", api_call),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            self.assertEqual(code, 2, output.getvalue())
            self.assertIn("repository input error", output.getvalue())
            self.assertNotIn("Traceback", output.getvalue())
            api_call.assert_not_called()

    def test_live_mode_fails_closed_for_unreadable_or_racy_rubric_inputs(self) -> None:
        filesystem_mutations = ("missing", "directory", "invalid-utf8")
        for mutation in filesystem_mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                case = {"id": "one", "prompt": "test", "assertions": ["works"]}
                self.write_case_repo(root, case)
                rubric = root / "references" / "eval-rubric.md"
                if mutation == "missing":
                    rubric.unlink()
                elif mutation == "directory":
                    rubric.unlink()
                    rubric.mkdir()
                else:
                    rubric.write_bytes(b"\xff\xfe\x00")

                api_call = mock.Mock(return_value="candidate response")
                output = io.StringIO()
                with (
                    mock.patch.object(sys, "argv", ["eval_run.py", str(root)]),
                    mock.patch.dict(
                        os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                    ),
                    mock.patch.object(eval_run, "call_api", api_call),
                    redirect_stdout(output),
                ):
                    code = eval_run.main()

                self.assertEqual(code, 2, output.getvalue())
                self.assertIn("Could not load eval rubric", output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())
                api_call.assert_not_called()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = {"id": "one", "prompt": "test", "assertions": ["works"]}
            self.write_case_repo(root, case)
            original_resolve = eval_run._resolve_repo_file
            replacement = root / "references" / "replacement-rubric.md"
            replacement.write_text(EXACT_RUBRIC, encoding="utf-8")
            rubric_resolutions = 0

            def swap_rubric_identity(
                candidate_root: Path, relative: str, field: str
            ) -> Path:
                nonlocal rubric_resolutions
                resolved = original_resolve(candidate_root, relative, field)
                if field != "references/eval-rubric.md":
                    return resolved
                rubric_resolutions += 1
                return resolved if rubric_resolutions == 1 else replacement

            api_call = mock.Mock(return_value="candidate response")
            output = io.StringIO()
            with (
                mock.patch.object(sys, "argv", ["eval_run.py", str(root)]),
                mock.patch.dict(
                    os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                ),
                mock.patch.object(
                    eval_run, "_resolve_repo_file", swap_rubric_identity
                ),
                mock.patch.object(eval_run, "call_api", api_call),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            self.assertEqual(code, 2, output.getvalue())
            self.assertIn("changed while it was being read", output.getvalue())
            self.assertNotIn("Traceback", output.getvalue())
            api_call.assert_not_called()

        original_open = Path.open
        for failure in (
            PermissionError("rubric unreadable"),
            FileNotFoundError("rubric disappeared after validation"),
        ):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                case = {"id": "one", "prompt": "test", "assertions": ["works"]}
                self.write_case_repo(root, case)

                def fail_rubric_open(path: Path, *args, **kwargs):
                    if path.name == "eval-rubric.md":
                        raise failure
                    return original_open(path, *args, **kwargs)

                api_call = mock.Mock(return_value="candidate response")
                output = io.StringIO()
                with (
                    mock.patch.object(sys, "argv", ["eval_run.py", str(root)]),
                    mock.patch.dict(
                        os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                    ),
                    mock.patch.object(Path, "open", fail_rubric_open),
                    mock.patch.object(eval_run, "call_api", api_call),
                    redirect_stdout(output),
                ):
                    code = eval_run.main()

                self.assertEqual(code, 2, output.getvalue())
                self.assertIn("Could not load eval rubric", output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())
                api_call.assert_not_called()

    def test_valid_contained_state_fixture_is_included(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = {
                "id": "one",
                "prompt": "test",
                "assertions": ["works"],
                "state_fixture": "fixtures/state.json",
            }
            self.write_case_repo(root, case)
            fixture = root / "fixtures" / "state.json"
            fixture.parent.mkdir()
            fixture.write_text("INSIDE-STATE-SENTINEL", encoding="utf-8")

            label, errors = eval_run.case_contract_errors(root, case, 0)
            self.assertEqual(label, "one")
            self.assertEqual(errors, [])
            self.assertIn("INSIDE-STATE-SENTINEL", eval_run.responder_context(root, case))

    def test_load_cases_rejects_ambiguous_json_and_invalid_shapes(self) -> None:
        invalid_documents = (
            '{"cases":[],"cases":[]}',
            '{"cases":[],"meta":NaN}',
            "[]",
            '{"cases":{}}',
            '{"cases":[1]}',
        )
        for document in invalid_documents:
            with self.subTest(document=document):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    (root / "evals").mkdir()
                    (root / "evals" / "evals.json").write_text(
                        document, encoding="utf-8"
                    )
                    with self.assertRaises(
                        (json.JSONDecodeError, ValueError)
                    ):
                        eval_run.load_cases(root)

    def test_invalid_eval_json_fails_cleanly_in_self_test_and_live_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evals").mkdir()
            (root / "evals" / "evals.json").write_text(
                '{"cases":[{"id":"one","id":"forged"}]}',
                encoding="utf-8",
            )

            for argv, expected_code, expected_message in (
                (
                    ["eval_run.py", str(root), "--self-test"],
                    1,
                    "self-test FAILED",
                ),
                (["eval_run.py", str(root)], 2, "Could not load eval cases"),
            ):
                output = io.StringIO()
                with mock.patch.object(sys, "argv", argv), redirect_stdout(output):
                    code = eval_run.main()
                self.assertEqual(code, expected_code)
                self.assertIn(expected_message, output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())

    def test_rubric_dimension_contract_rejects_every_drift_shape(self) -> None:
        dimensions = list(eval_run.SEQUENCE_DIMENSIONS)
        mutations = {
            "extra": dimensions + ["invented dimension"],
            "missing": dimensions[:-1],
            "renamed": ["route quality", *dimensions[1:]],
            "duplicate": [dimensions[0], *dimensions[:-1]],
            "reordered": [dimensions[1], dimensions[0], *dimensions[2:]],
        }
        self.assertEqual(
            eval_run.validate_sequence_dimension_contract(EXACT_RUBRIC),
            eval_run.SEQUENCE_DIMENSIONS,
        )
        for label, mutated in mutations.items():
            rubric = "Dimensions: " + ", ".join(mutated) + ".\n"
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "exactly match"):
                    eval_run.validate_sequence_dimension_contract(rubric)

    def test_live_cli_refuses_rubric_drift_before_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evals").mkdir()
            (root / "references").mkdir()
            (root / "SKILL.md").write_text("# test", encoding="utf-8")
            (root / "evals" / "evals.json").write_text(
                json.dumps(
                    {
                        "cases": [
                            {"id": "one", "prompt": "test", "assertions": ["works"]}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "references" / "eval-rubric.md").write_text(
                EXACT_RUBRIC.replace("safety and rights", "renamed safety"),
                encoding="utf-8",
            )
            output = io.StringIO()
            call = mock.Mock()
            with (
                mock.patch.object(sys, "argv", ["eval_run.py", str(root)]),
                mock.patch.dict(
                    os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                ),
                mock.patch.object(eval_run, "call_api", call),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            self.assertEqual(code, 2)
            self.assertIn("Could not load eval rubric", output.getvalue())
            call.assert_not_called()


class LedgerIntegrityTests(unittest.TestCase):
    def make_repo(self, root: Path, cases: list[dict]) -> None:
        (root / "evals").mkdir(parents=True)
        (root / "references").mkdir()
        (root / "evals" / "evals.json").write_text(
            json.dumps({"cases": cases}), encoding="utf-8"
        )
        (root / "references" / "eval-rubric.md").write_text(
            EXACT_RUBRIC, encoding="utf-8"
        )
        (root / "SKILL.md").write_text("# test skill", encoding="utf-8")

    def run_main(
        self,
        argv: list[str],
        verdict: dict,
        *,
        environment: dict[str, str] | None = None,
    ) -> tuple[int, str, mock.Mock, mock.Mock]:
        output = io.StringIO()
        call = mock.Mock(return_value="candidate")
        judge = mock.Mock(return_value=verdict)
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(
                os.environ,
                environment or {"ANTHROPIC_API_KEY": "test-key"},
                clear=True,
            ),
            mock.patch.object(eval_run, "call_api", call),
            mock.patch.object(eval_run, "judge", judge),
            redirect_stdout(output),
        ):
            code = eval_run.main()
        return code, output.getvalue(), call, judge

    def test_unknown_selection_preserves_existing_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(
                root,
                [{"id": "known", "prompt": "test", "assertions": ["works"]}],
            )
            ledger = root / "evals" / "eval-run-ledger.md"
            ledger.write_text("previous complete evidence\n", encoding="utf-8")

            code, output, call, judge = self.run_main(
                [
                    "eval_run.py",
                    str(root),
                    "--id",
                    "missing",
                    "--ledger",
                    "evals/eval-run-ledger.md",
                ],
                valid_verdict(),
            )

            self.assertEqual(code, 2)
            self.assertIn("unknown eval id", output.lower())
            self.assertEqual(
                ledger.read_text(encoding="utf-8"), "previous complete evidence\n"
            )
            call.assert_not_called()
            judge.assert_not_called()

    def test_partial_run_cannot_replace_root_relative_canonical_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(
                root,
                [
                    {"id": "one", "prompt": "test", "assertions": ["works"]},
                    {"id": "two", "prompt": "test", "assertions": ["works"]},
                ],
            )
            ledger = root / "evals" / "eval-run-ledger.md"
            ledger.write_text("previous complete evidence\n", encoding="utf-8")

            code, output, call, judge = self.run_main(
                [
                    "eval_run.py",
                    str(root),
                    "--limit",
                    "1",
                    "--ledger",
                    "evals/eval-run-ledger.md",
                ],
                valid_verdict(),
            )

            self.assertEqual(code, 2)
            self.assertIn("refusing to replace the canonical ledger", output.lower())
            self.assertEqual(
                ledger.read_text(encoding="utf-8"), "previous complete evidence\n"
            )
            call.assert_not_called()
            judge.assert_not_called()

    def test_partial_ad_hoc_ledger_is_explicitly_not_release_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(
                root,
                [
                    {"id": "one", "prompt": "test", "assertions": ["works"]},
                    {"id": "two", "prompt": "test", "assertions": ["works"]},
                ],
            )
            ledger = root / "partial.md"

            code, _output, _call, _judge = self.run_main(
                [
                    "eval_run.py",
                    str(root),
                    "--limit",
                    "1",
                    "--ledger",
                    "partial.md",
                    "--stamp",
                    "2026-08-01",
                ],
                valid_verdict(),
            )

            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(code, 1)
            self.assertIn("Run scope: **PARTIAL**", text)
            self.assertIn("Release verdict: **NOT ELIGIBLE**", text)
            self.assertIn("1 of 2", text)

    def test_ad_hoc_ledger_parent_is_created_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(
                root,
                [
                    {"id": "one", "prompt": "test", "assertions": ["works"]},
                    {"id": "two", "prompt": "test", "assertions": ["works"]},
                ],
            )
            ledger = root / "eval-runs" / "focused.md"

            code, _output, _call, _judge = self.run_main(
                [
                    "eval_run.py",
                    str(root),
                    "--limit",
                    "1",
                    "--ledger",
                    "eval-runs/focused.md",
                ],
                valid_verdict(),
            )

            self.assertEqual(code, 1)
            self.assertTrue(ledger.is_file())
            self.assertIn(
                "Release verdict: **NOT ELIGIBLE**",
                ledger.read_text(encoding="utf-8"),
            )

    def test_invalid_judge_fields_become_a_failed_fresh_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(
                root,
                [{"id": "one", "prompt": "test", "assertions": ["works"]}],
            )
            ledger = root / "evals" / "eval-run-ledger.md"
            ledger.write_text("stale passing artifact\n", encoding="utf-8")

            code, _output, _call, _judge = self.run_main(
                [
                    "eval_run.py",
                    str(root),
                    "--ledger",
                    "evals/eval-run-ledger.md",
                ],
                {"overall_score": "3", "pass": "yes", "notes": "malformed"},
            )

            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(code, 1)
            self.assertNotIn("stale passing artifact", text)
            self.assertIn("Release verdict: **FAIL**", text)
            self.assertIn("invalid judge verdict", text.lower())
            self.assertIn("| one | 0-3 | n/a | 0 | NO |", text)

    def test_malformed_provider_response_becomes_failed_fresh_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(
                root,
                [{"id": "one", "prompt": "test", "assertions": ["works"]}],
            )
            ledger = root / "evals" / "eval-run-ledger.md"
            ledger.write_text("stale passing artifact\n", encoding="utf-8")
            output = io.StringIO()
            judge = mock.Mock()

            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "eval_run.py",
                        str(root),
                        "--ledger",
                        "evals/eval-run-ledger.md",
                    ],
                ),
                mock.patch.dict(
                    os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                ),
                mock.patch.object(
                    eval_run,
                    "call_api",
                    side_effect=eval_run.ProviderResponseError("invalid body"),
                ),
                mock.patch.object(eval_run, "judge", judge),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(code, 1)
            self.assertNotIn("stale passing artifact", text)
            self.assertIn("Release verdict: **FAIL**", text)
            self.assertIn("api error: invalid body", text)
            judge.assert_not_called()

    def test_atomic_replace_failure_preserves_previous_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("previous complete evidence\n", encoding="utf-8")
            rows = [result_row()]

            with (
                mock.patch.object(
                    eval_run.os, "replace", side_effect=OSError("replace failed")
                ),
                self.assertRaisesRegex(OSError, "replace failed"),
            ):
                eval_run.write_ledger(
                    path,
                    rows,
                    "model",
                    "2026-08-01",
                    "anthropic",
                    "global_en",
                    judge_model="judge-model",
                    expected_cases=case_metadata(),
                    total_expected=1,
                    release_eligible=True,
                )

            self.assertEqual(
                path.read_text(encoding="utf-8"), "previous complete evidence\n"
            )
            self.assertEqual(list(path.parent.glob(".ledger.md.*.tmp")), [])

    def test_ledger_records_provider_models_scope_and_release_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            rows = [result_row()]

            with redirect_stdout(io.StringIO()):
                eval_run.write_ledger(
                    path,
                    rows,
                    "MiniMax-M2.7",
                    "2026-08-01",
                    "minimax",
                    "cn_zh",
                    judge_model="MiniMax-M3",
                    expected_cases=case_metadata(),
                    total_expected=1,
                    release_eligible=True,
                )

            text = path.read_text(encoding="utf-8")
            self.assertIn("responder model `MiniMax-M2.7`", text)
            self.assertIn("judge model `MiniMax-M3`", text)
            self.assertIn("provider `minimax`", text)
            self.assertIn("region `cn_zh`", text)
            self.assertIn("Run scope: **COMPLETE**", text)
            self.assertIn("Release verdict: **PASS**", text)

    def test_writer_without_scope_context_cannot_mint_release_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"

            with redirect_stdout(io.StringIO()):
                eval_run.write_ledger(
                    path,
                    [result_row()],
                    "model",
                    "2026-08-01",
                    "anthropic",
                    "global_en",
                )

            text = path.read_text(encoding="utf-8")
            self.assertIn("Run scope: **UNSCOPED**", text)
            self.assertIn("release universe was not supplied", text)
            self.assertIn("Release verdict: **NOT ELIGIBLE**", text)
            self.assertNotIn("1 of 1 release cases", text)

    def test_writer_cannot_accept_a_caller_supplied_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            forged = {
                "scope": "COMPLETE",
                "run_verdict": "PASS",
                "release_verdict": "PASS",
            }

            with self.assertRaisesRegex(TypeError, "report"):
                eval_run.write_ledger(
                    path,
                    [],
                    "model",
                    "2026-08-01",
                    "anthropic",
                    "global_en",
                    report=forged,
                )

            self.assertFalse(path.exists())

    def test_empty_rows_cannot_mint_a_complete_passing_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"

            with redirect_stdout(io.StringIO()):
                report = eval_run.write_ledger(
                    path,
                    [],
                    "model",
                    "2026-08-01",
                    "anthropic",
                    "global_en",
                    expected_cases=case_metadata(),
                    total_expected=1,
                    release_eligible=True,
                )

            text = path.read_text(encoding="utf-8")
            self.assertEqual(report["run_verdict"], "FAIL")
            self.assertEqual(report["release_verdict"], "FAIL")
            self.assertIn("0 results recorded", text)
            self.assertIn("no scored results were produced", text)
            self.assertIn("missing result ids: case-1", text)
            self.assertNotIn("Release verdict: **PASS**", text)

    def test_writer_with_canonical_ids_but_no_total_remains_unscoped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"

            with redirect_stdout(io.StringIO()):
                report = eval_run.write_ledger(
                    path,
                    [result_row()],
                    "model",
                    "2026-08-01",
                    "anthropic",
                    "global_en",
                    expected_cases=case_metadata(),
                    release_eligible=True,
                )

            text = path.read_text(encoding="utf-8")
            self.assertEqual(report["scope"], "UNSCOPED")
            self.assertEqual(report["release_verdict"], "NOT ELIGIBLE")
            self.assertIn("Run scope: **UNSCOPED**", text)
            self.assertNotIn("Release verdict: **PASS**", text)

    def test_non_string_notes_fail_closed_and_render_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            row = result_row()
            row["notes"] = {"forged": "object"}

            with redirect_stdout(io.StringIO()):
                report = eval_run.write_ledger(
                    path,
                    [row],
                    "model",
                    "2026-08-01",
                    "anthropic",
                    "global_en",
                    expected_cases=case_metadata(),
                    total_expected=1,
                    release_eligible=True,
                )

            text = path.read_text(encoding="utf-8")
            self.assertEqual(report["release_verdict"], "FAIL")
            self.assertIn("notes must be a string", text)
            self.assertIn("[invalid non-string notes]", text)

    def test_ledger_sanitizes_all_markdown_line_controls_before_truncation(self) -> None:
        controls = {
            "CR": "\r",
            "CRLF": "\r\n",
            "C0": "\x00\x01\x0b\x0c\x1c\x1d\x1e\x1f",
            "C1": "\x7f\x80\x85\x9f",
            "line separator": "\u2028",
            "paragraph separator": "\u2029",
        }
        ordinary = "Café 東京 — ordinary ledger text"
        self.assertEqual(eval_run._safe_ledger_text(ordinary), ordinary)

        for label, control in controls.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "ledger.md"
                row = result_row(passed=False)
                row["notes"] = (
                    "review failed" + control + "# FORGED RELEASE PASS"
                )
                with redirect_stdout(io.StringIO()):
                    report = eval_run.write_ledger(
                        path,
                        [row],
                        "model",
                        "2026-08-01",
                        "anthropic",
                        "global_en",
                        expected_cases=case_metadata(),
                        total_expected=1,
                        release_eligible=True,
                    )

                text = path.read_text(encoding="utf-8")
                lines = text.splitlines()
                result_lines = [line for line in lines if line.startswith("| case-1 |")]
                self.assertEqual(report["release_verdict"], "FAIL")
                self.assertEqual(len(result_lines), 1)
                self.assertIn(
                    "review failed # FORGED RELEASE PASS", result_lines[0]
                )
                self.assertFalse(
                    any(line.startswith("# FORGED RELEASE PASS") for line in lines)
                )

    def test_every_untrusted_ledger_field_uses_the_line_safe_serializer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            injected = "safe\r# FORGED RELEASE PASS"
            dimensions = [
                {"dimension": dimension, "score": 4}
                for dimension in eval_run.SEQUENCE_DIMENSIONS
            ]
            dimensions.extend(
                [
                    {"dimension": injected, "score": 4},
                    {"dimension": injected, "score": 4},
                ]
            )
            row = {
                "id": injected,
                "score": 4,
                "pass": False,
                "sequence": True,
                "critical": False,
                "notes": injected,
                "dimension_scores": dimensions,
            }

            with redirect_stdout(io.StringIO()):
                report = eval_run.write_ledger(
                    path,
                    [row],
                    injected,
                    injected,
                    injected,
                    injected,
                    judge_model=injected,
                    expected_cases={
                        injected: {"sequence": True, "critical": False}
                    },
                    total_expected=1,
                    release_eligible=True,
                )

            text = path.read_text(encoding="utf-8")
            self.assertEqual(report["release_verdict"], "FAIL")
            self.assertNotIn("\r", text)
            self.assertFalse(
                any(
                    line.startswith("# FORGED RELEASE PASS")
                    for line in text.splitlines()
                )
            )
            self.assertGreaterEqual(text.count("safe # FORGED RELEASE PASS"), 5)

    def test_malformed_rows_replace_stale_ledger_with_failed_placeholders(self) -> None:
        malformed_rows: tuple[tuple[str, object, str], ...] = (
            ("empty object", {}, "[invalid row 1]"),
            ("non-object", "not a row", "result is not an object"),
            (
                "malformed dimension",
                {
                    **result_row(),
                    "dimension_scores": [
                        {"dimension": "routing correctness", "score": "4"}
                    ],
                },
                "[invalid dimension row]",
            ),
        )
        for label, row, marker in malformed_rows:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "ledger.md"
                path.write_text("stale passing evidence\n", encoding="utf-8")
                with redirect_stdout(io.StringIO()):
                    report = eval_run.write_ledger(
                        path,
                        [row],
                        "model",
                        "2026-08-01",
                        "anthropic",
                        "global_en",
                        expected_cases=case_metadata(),
                        total_expected=1,
                        release_eligible=True,
                    )

                text = path.read_text(encoding="utf-8")
                self.assertEqual(report["release_verdict"], "FAIL")
                self.assertNotIn("stale passing evidence", text)
                self.assertIn("Release verdict: **FAIL**", text)
                self.assertIn(marker, text)

    def test_unpaired_surrogates_in_public_rows_write_a_fresh_failed_ledger(self) -> None:
        surrogate = "\ud800"
        rows = (
            {**result_row(), "id": surrogate},
            {**result_row(), "notes": surrogate},
            {
                **result_row(),
                "dimension_scores": [{"dimension": surrogate, "score": 3}],
            },
        )
        for row in rows:
            with self.subTest(row=row), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "ledger.md"
                path.write_text("stale passing evidence\n", encoding="utf-8")
                with redirect_stdout(io.StringIO()):
                    report = eval_run.write_ledger(
                        path,
                        [row],
                        "model",
                        "2026-08-01",
                        "anthropic",
                        "global_en",
                        expected_cases=case_metadata(),
                        total_expected=1,
                        release_eligible=True,
                    )

                text = path.read_text(encoding="utf-8")
                self.assertEqual(report["release_verdict"], "FAIL")
                self.assertNotIn("stale passing evidence", text)
                self.assertIn("Release verdict: **FAIL**", text)
                self.assertIn("unpaired surrogate", text)

    def test_surrogate_judge_note_becomes_a_fresh_failed_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(
                root,
                [{"id": "one", "prompt": "test", "assertions": ["works"]}],
            )
            ledger = root / "evals" / "eval-run-ledger.md"
            ledger.write_text("stale passing artifact\n", encoding="utf-8")
            verdict = valid_verdict()
            verdict["notes"] = "\ud800"

            code, output, _call, _judge = self.run_main(
                [
                    "eval_run.py",
                    str(root),
                    "--ledger",
                    "evals/eval-run-ledger.md",
                ],
                verdict,
            )

            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(code, 1)
            self.assertNotIn("stale passing artifact", text)
            self.assertIn("Release verdict: **FAIL**", text)
            self.assertIn("unpaired surrogate", text)
            self.assertNotIn("Traceback", output)

    def test_fdopen_failure_closes_descriptor_and_cleanup_cannot_mask_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            real_close = os.close

            with (
                mock.patch.object(
                    eval_run.os, "fdopen", side_effect=RuntimeError("fdopen failed")
                ),
                mock.patch.object(eval_run.os, "close", wraps=real_close) as close,
                self.assertRaisesRegex(RuntimeError, "fdopen failed"),
            ):
                eval_run._atomic_write_text(path, "new evidence\n")

            close.assert_called()
            self.assertEqual(list(path.parent.glob(".ledger.md.*.tmp")), [])

    def test_cleanup_failure_does_not_mask_the_original_atomic_write_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            with (
                mock.patch.object(
                    eval_run.os, "fdopen", side_effect=RuntimeError("fdopen failed")
                ),
                mock.patch.object(
                    eval_run.Path, "unlink", side_effect=OSError("cleanup failed")
                ),
                self.assertRaisesRegex(RuntimeError, "fdopen failed"),
            ):
                eval_run._atomic_write_text(path, "new evidence\n")

            for temporary in path.parent.glob(".ledger.md.*.tmp"):
                temporary.unlink()

    def test_selected_provider_and_endpoint_reach_responder_and_judge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(
                root,
                [{"id": "one", "prompt": "test", "assertions": ["works"]}],
            )

            code, _output, call, judge = self.run_main(
                [
                    "eval_run.py",
                    str(root),
                    "--provider",
                    "minimax",
                    "--region",
                    "cn_zh",
                    "--model",
                    "MiniMax-M2.7",
                ],
                valid_verdict(),
                environment={"MINIMAX_API_KEY": "test-key"},
            )

            self.assertEqual(code, 0)
            responder_args = call.call_args.args
            judge_args = judge.call_args.args
            self.assertEqual(responder_args[2], "MiniMax-M2.7")
            self.assertEqual(responder_args[4], eval_run.PROVIDER_CONFIGS["minimax"])
            self.assertEqual(
                responder_args[5], "https://api.minimaxi.com/anthropic/v1/messages"
            )
            self.assertEqual(judge_args[2], "MiniMax-M2.7")
            self.assertEqual(judge_args[5], eval_run.PROVIDER_CONFIGS["minimax"])
            self.assertEqual(
                judge_args[6], "https://api.minimaxi.com/anthropic/v1/messages"
            )


if __name__ == "__main__":
    unittest.main()

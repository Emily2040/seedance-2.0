"""Adversarial coverage for the provider-aware live-eval integrity boundary."""

from __future__ import annotations

import io
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import eval_run  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
EXACT_RUBRIC = (
    "Score 0 to 3. Sequence scale 0-4.\n\nDimensions: "
    + ", ".join(eval_run.SEQUENCE_DIMENSIONS)
    + ".\n"
)
_RELEASE_SNAPSHOT: eval_run.FrozenRepository | None = None


def write_source_manifest(root: Path) -> None:
    for evaluator_path in eval_run.EVALUATOR_HARNESS_PATHS:
        path = root / evaluator_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("# frozen test evaluator harness\n", encoding="utf-8")
    paths = {
        "SKILL.md",
        "evals/evals.json",
        "references/eval-rubric.md",
        *eval_run.EVALUATOR_HARNESS_PATHS,
    }
    for directory in (root / "skills", root / "references", root / "evals" / "fixtures"):
        if directory.exists():
            paths.update(
                path.relative_to(root).as_posix()
                for path in directory.rglob("*")
                if path.is_file()
            )
    entries = []
    for relative in sorted(paths):
        path = root / relative
        if relative == "SKILL.md":
            role = "root"
        elif relative in {
            "evals/evals.json",
            "references/eval-rubric.md",
            *eval_run.EVALUATOR_HARNESS_PATHS,
        }:
            role = "evaluator"
        elif relative.startswith("evals/fixtures/"):
            role = "fixture"
        elif relative.startswith("references/migrated/"):
            role = "archive"
        else:
            role = "responder"
        entries.append(
            {
                "path": relative,
                "role": role,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    (root / "evals" / "source-manifest.json").write_text(
        json.dumps({"version": 1, "sources": entries}, indent=2) + "\n",
        encoding="utf-8",
    )


def release_snapshot() -> eval_run.FrozenRepository:
    global _RELEASE_SNAPSHOT
    if _RELEASE_SNAPSHOT is None:
        _RELEASE_SNAPSHOT = eval_run.freeze_repository(REPO_ROOT)
    return _RELEASE_SNAPSHOT


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
        "status": "scored",
        "score": score,
        "pass": passed,
        "sequence": sequence,
        "critical": critical,
        "notes": "test verdict",
        "sources": [],
        "dimension_scores": (
            [
                {"dimension": dimension, "score": 4}
                for dimension in eval_run.SEQUENCE_DIMENSIONS
            ]
            if sequence is True
            else []
        ),
    }


def harness_error_row(
    case_id: str = "case-1",
    *,
    sequence: bool = False,
    critical: bool = False,
    notes: str = "judge transport failed",
) -> dict:
    row = result_row(
        case_id,
        sequence=sequence,
        critical=critical,
    )
    row.update(
        {
            "status": "harness_error",
            "score": None,
            "pass": None,
            "notes": notes,
            "dimension_scores": [],
        }
    )
    return row


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


def frozen_release_rows() -> list[dict]:
    rows: list[dict] = []
    for case in eval_run.load_cases(release_snapshot()):
        sequence = eval_run.is_sequence_case(case)
        rows.append(
            result_row(
                case["id"],
                score=4 if sequence else 3,
                sequence=sequence,
                critical=case.get("critical", False),
            )
        )
    return rows


def valid_verdict(
    criterion_ids: tuple[str, ...] = ("a0", "eo", "fm"),
    score: int = 3,
) -> dict:
    return {
        "overall_score": score,
        "pass": True,
        "notes": "ok",
        "criterion_scores": {
            criterion_id: True for criterion_id in criterion_ids
        },
        "dimension_scores": {},
    }


def completion_payload(
    provider_name: str,
    model: str,
    content: list[dict] | None = None,
) -> dict:
    payload = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": (
            content if content is not None else [{"type": "text", "text": "ok"}]
        ),
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }
    if provider_name == "anthropic":
        payload["stop_sequence"] = None
    return payload


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

    def test_harness_errors_are_excluded_from_quality_averages(self) -> None:
        expected_cases = {
            **case_metadata("scored-case"),
            **case_metadata("judge-down"),
        }
        report = eval_run.assess_run(
            [
                result_row("scored-case", score=3),
                harness_error_row("judge-down"),
            ],
            expected_cases=expected_cases,
            release_eligible=True,
            total_expected=2,
            source_manifest={},
        )

        self.assertEqual(report["scope"], "COMPLETE")
        self.assertEqual(report["scored_count"], 1)
        self.assertEqual(report["harness_errors"], ["judge-down"])
        self.assertEqual(report["legacy_count"], 1)
        self.assertEqual(report["legacy_average"], 3)
        self.assertEqual(report["failed_verdicts"], [])
        self.assertEqual(report["run_verdict"], "FAIL")
        self.assertEqual(report["release_verdict"], "NOT ELIGIBLE")

    def test_valid_zero_score_remains_scored_quality_evidence(self) -> None:
        report = eval_run.assess_run(
            [result_row(score=0, passed=False)],
            expected_cases=case_metadata(),
            release_eligible=True,
            total_expected=1,
            source_manifest={},
        )

        self.assertEqual(report["scored_count"], 1)
        self.assertEqual(report["harness_errors"], [])
        self.assertEqual(report["legacy_average"], 0)
        self.assertEqual(report["failed_verdicts"], ["case-1"])
        self.assertEqual(report["release_verdict"], "FAIL")

    def test_harness_error_cannot_smuggle_a_numeric_score_or_pass(self) -> None:
        row = harness_error_row()
        row["score"] = 0
        row["pass"] = False
        report = eval_run.assess_run(
            [row],
            expected_cases=case_metadata(),
            release_eligible=True,
            total_expected=1,
            source_manifest={},
        )

        self.assertIn("case-1: harness_error score must be null", report["integrity_errors"])
        self.assertIn("case-1: harness_error pass must be null", report["integrity_errors"])
        self.assertEqual(report["scored_count"], 0)
        self.assertEqual(report["release_verdict"], "FAIL")

    def test_result_status_is_required_and_harness_errors_need_a_reason(self) -> None:
        missing_status = result_row()
        del missing_status["status"]
        blank_error = harness_error_row("blank-error", notes=" ")
        report = eval_run.assess_run([missing_status, blank_error])

        self.assertTrue(
            any("status must be one of" in error for error in report["integrity_errors"])
        )
        self.assertIn(
            "blank-error: harness_error notes must explain the failure",
            report["integrity_errors"],
        )
        self.assertEqual(report["release_verdict"], "NOT ELIGIBLE")

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

    def test_caller_subset_cannot_replace_frozen_release_universe(self) -> None:
        report = eval_run.assess_run(
            [result_row()],
            expected_cases=case_metadata(),
            total_expected=1,
            release_eligible=True,
            snapshot=release_snapshot(),
        )

        self.assertEqual(report["scope"], "COMPLETE")
        self.assertEqual(report["selected_count"], 126)
        self.assertEqual(report["total_expected"], 126)
        self.assertEqual(report["run_verdict"], "FAIL")
        self.assertEqual(report["release_verdict"], "FAIL")
        self.assertEqual(report["exit_code"], 1)
        self.assertIn(
            "expected_cases do not match frozen evals/evals.json",
            report["integrity_errors"],
        )
        self.assertIn(
            "total_expected does not match frozen evals/evals.json",
            report["integrity_errors"],
        )
        self.assertEqual(
            sum(report["repository_role_counts"].values()),
            report["repository_file_count"],
        )

    def test_release_ids_metadata_and_count_are_derived_from_frozen_evals(self) -> None:
        report = eval_run.assess_run(
            frozen_release_rows(),
            release_eligible=True,
            snapshot=release_snapshot(),
        )

        self.assertEqual(report["scope"], "COMPLETE")
        self.assertEqual(report["selected_count"], 126)
        self.assertEqual(report["total_expected"], 126)
        self.assertEqual(report["run_verdict"], "PASS")
        self.assertEqual(report["release_verdict"], "PASS")
        self.assertEqual(report["integrity_errors"], [])

    def test_release_recomputes_canonical_bindings_instead_of_trusting_flags(
        self,
    ) -> None:
        canonical_with_false_flags = replace(
            release_snapshot(),
            canonical_contract_bound=False,
            evaluator_execution_bound=False,
        )
        canonical_report = eval_run.assess_run(
            frozen_release_rows(),
            release_eligible=True,
            snapshot=canonical_with_false_flags,
        )
        self.assertEqual(canonical_report["release_verdict"], "PASS")
        self.assertEqual(canonical_report["integrity_errors"], [])

        mutations = {
            "evals/evals.json": '{"cases":[{"id":"forged"}]}\n',
            "references/eval-rubric.md": EXACT_RUBRIC + "FORGED RUBRIC\n",
        }
        for target, replacement_text in mutations.items():
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "scripts").mkdir(parents=True)
                (root / "evals").mkdir()
                (root / "references").mkdir()
                (root / "SKILL.md").write_text(
                    "# release binding regression\n", encoding="utf-8"
                )
                shutil.copy2(
                    REPO_ROOT / "scripts" / "eval_run.py",
                    root / "scripts" / "eval_run.py",
                )
                shutil.copy2(
                    REPO_ROOT / "evals" / "evals.json",
                    root / "evals" / "evals.json",
                )
                shutil.copy2(
                    REPO_ROOT / "references" / "eval-rubric.md",
                    root / "references" / "eval-rubric.md",
                )
                (root / target).write_text(replacement_text, encoding="utf-8")
                write_source_manifest(root)

                module_name = "forged_eval_run_" + target.replace("/", "_").replace(
                    ".", "_"
                )
                spec = importlib.util.spec_from_file_location(
                    module_name, root / "scripts" / "eval_run.py"
                )
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.loader)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                try:
                    spec.loader.exec_module(module)
                    with self.assertRaisesRegex(
                        module.HarnessError,
                        "canonical evaluation contract changed",
                    ):
                        module.freeze_repository(root)
                    unbound = module.freeze_repository(
                        root,
                        enforce_canonical_contract=False,
                        enforce_evaluator_identity=True,
                    )
                    forged = replace(
                        unbound,
                        canonical_contract_bound=True,
                        evaluator_execution_bound=True,
                    )
                    rows = []
                    for case in module.load_cases(forged):
                        sequence = module.is_sequence_case(case)
                        rows.append(
                            {
                                "id": case["id"],
                                "score": 4 if sequence else 3,
                                "pass": True,
                                "sequence": sequence,
                                "critical": case.get("critical", False),
                                "notes": "caller-forged release universe",
                                "sources": [],
                                "dimension_scores": (
                                    [
                                        {"dimension": dimension, "score": 4}
                                        for dimension in module.SEQUENCE_DIMENSIONS
                                    ]
                                    if sequence
                                    else []
                                ),
                            }
                        )
                    report = module.assess_run(
                        rows,
                        release_eligible=True,
                        snapshot=forged,
                    )
                finally:
                    sys.modules.pop(module_name, None)

                self.assertNotEqual(report["release_verdict"], "PASS")
                self.assertTrue(
                    any(
                        f"canonical evaluation contract changed: {target}" in error
                        for error in report["integrity_errors"]
                    ),
                    report,
                )

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
    CASE = {
        "prompt": "test",
        "expected_output": "working answer",
        "assertions": ["works"],
        "failure_mode": "does not work",
    }

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
                eval_run.ProviderResponseError,
                "transport read failed \\(IncompleteRead\\)",
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
                    with self.assertRaises(eval_run.ProviderResponseError) as raised:
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        )
                self.assertIn(type(failure).__name__, str(raised.exception))
                self.assertIn(str(failure).strip(), str(raised.exception))
                self.assertIn("transport open failed", str(raised.exception))

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
                    with self.assertRaises(eval_run.ProviderResponseError) as raised:
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        )
                self.assertIn("ConnectionResetError", str(raised.exception))
                self.assertIn(f"reset {boundary}", str(raised.exception))
                self.assertIn(f"transport {boundary} failed", str(raised.exception))

    def test_call_api_sanitizes_http_error_diagnostics(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        api_key = "private-http-key"
        response_stream = io.BytesIO(b"provider failure")
        error = eval_run.urllib.error.HTTPError(
            endpoint,
            503,
            f"provider unavailable; X-Api-Key: {api_key}",
            {},
            response_stream,
        )
        with mock.patch.object(
            eval_run.urllib.request, "urlopen", side_effect=error
        ):
            with self.assertRaises(eval_run.ProviderResponseError) as raised:
                eval_run.call_api(
                    "system", "user", model, api_key, provider, endpoint
                )

        message = str(raised.exception)
        self.assertIn("transport open failed (HTTPError)", message)
        self.assertIn("503", message)
        self.assertIn("provider unavailable", message)
        self.assertIn("[REDACTED]", message)
        self.assertNotIn(api_key, message)
        self.assertTrue(response_stream.closed)

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
            ("minimax", "global_en", "MiniMax-M2.7-highspeed"),
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
        invalid_contents = (
            [{"type": "text", "text": "ok"}, {"type": "text"}],
            [{"type": "text", "text": "ok"}, {"type": "text", "text": 7}],
            [{"type": "text", "text": "\ud800"}],
        )
        providers = (
            ("anthropic", "global_en", None),
            ("minimax", "global_en", "MiniMax-M2.7-highspeed"),
            ("minimax", "cn_zh", "MiniMax-M2.7"),
        )
        for provider_name, region, requested_model in providers:
            provider, endpoint, model = eval_run.resolve_provider(
                provider_name, region, requested_model
            )
            for content in invalid_contents:
                with self.subTest(
                    provider=provider_name,
                    region=region,
                    content=content,
                ):
                    response = mock.MagicMock()
                    response.__enter__.return_value.read.return_value = json.dumps(
                        completion_payload(provider_name, model, content)
                    ).encode("utf-8")
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

    def test_provider_envelope_rejects_unknown_non_text_blocks(self) -> None:
        for provider_name, region, requested_model in (
            ("anthropic", "global_en", None),
            ("minimax", "cn_zh", "MiniMax-M2.7-highspeed"),
        ):
            provider, endpoint, model = eval_run.resolve_provider(
                provider_name, region, requested_model
            )
            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(
                completion_payload(
                    provider_name,
                    model,
                    [
                        {"type": "future_block", "payload": {"x": 1}},
                        {"type": "text", "text": "ok"},
                    ],
                )
            ).encode("utf-8")
            with mock.patch.object(
                eval_run.urllib.request, "urlopen", return_value=response
            ):
                with self.assertRaisesRegex(
                    eval_run.ProviderResponseError, "unsupported type"
                ):
                    eval_run.call_api(
                        "system", "user", model, "key", provider, endpoint
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

    def test_empty_judge_response_raises_instead_of_minting_a_zero_score(self) -> None:
        provider, endpoint, _model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        with (
            mock.patch.object(eval_run, "call_api", return_value="   "),
            self.assertRaisesRegex(eval_run.HarnessError, "returned no JSON"),
        ):
            eval_run.judge(
                self.CASE,
                "candidate",
                "model",
                "key",
                "rubric",
                provider,
                endpoint,
            )

    def test_non_standard_json_constants_are_rejected(self) -> None:
        raw = '{"overall_score":NaN,"pass":true,"notes":"bad"}'
        provider, endpoint, _model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        with (
            mock.patch.object(eval_run, "call_api", return_value=raw),
            self.assertRaisesRegex(eval_run.HarnessError, "unparseable"),
        ):
            eval_run.judge(
                self.CASE,
                "candidate",
                "model",
                "key",
                "rubric",
                provider,
                endpoint,
            )

    def test_duplicate_json_keys_are_rejected(self) -> None:
        raw = (
            '{"overall_score":0,"overall_score":3,'
            '"pass":false,"pass":true,"notes":"ambiguous",'
            '"criterion_scores":{"a0":true}}'
        )
        provider, endpoint, _model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        with (
            mock.patch.object(eval_run, "call_api", return_value=raw),
            self.assertRaisesRegex(eval_run.HarnessError, "unparseable"),
        ):
            eval_run.judge(
                self.CASE,
                "candidate",
                "model",
                "key",
                "rubric",
                provider,
                endpoint,
            )

    def test_unpaired_surrogate_in_judge_json_is_rejected(self) -> None:
        raw = (
            '{"overall_score":3,"pass":true,"notes":"\\ud800",'
            '"criterion_scores":{"a0":true},'
            '"dimension_scores":{}}'
        )
        provider, endpoint, _model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        with (
            mock.patch.object(eval_run, "call_api", return_value=raw),
            self.assertRaisesRegex(eval_run.HarnessError, "unparseable"),
        ):
            eval_run.judge(
                self.CASE,
                "candidate",
                "model",
                "key",
                "rubric",
                provider,
                endpoint,
            )

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
                        "criterion_scores": {
                            criterion_id: True
                            for criterion_id in ("a0", "eo", "fm")
                        },
                        "dimension_scores": {},
                    },
                )
                self.assertEqual(verdict["status"], "harness_error")
                self.assertIsNone(verdict["overall_score"])
                self.assertIsNone(verdict["pass"])
                self.assertIn("invalid judge verdict", verdict["notes"])

        verdict = eval_run.normalize_verdict(
            self.CASE,
            {
                "overall_score": 3,
                "pass": "true",
                "notes": "wrong type",
                "criterion_scores": {
                    criterion_id: True
                    for criterion_id in ("a0", "eo", "fm")
                },
                "dimension_scores": {},
            },
        )
        self.assertEqual(verdict["status"], "harness_error")
        self.assertIsNone(verdict["overall_score"])
        self.assertIsNone(verdict["pass"])
        self.assertIn("pass must be a boolean", verdict["notes"])

    def test_criterion_scores_must_cover_each_contract_id_exactly_once(self) -> None:
        case = {
            "prompt": "test",
            "expected_output": "working answer",
            "assertions": ["works", "is safe"],
            "failure_mode": "does not work",
        }
        invalid_scores = (
            {"a0": True, "eo": True, "fm": True},
            {"a0": True, "a1": "false", "eo": True, "fm": True},
            {"a0": True, "a1": False, "eo": True, "fm": True},
        )
        for criterion_scores in invalid_scores:
            with self.subTest(criterion_scores=criterion_scores):
                verdict = eval_run.normalize_verdict(
                    case,
                    {
                        "overall_score": 3,
                        "pass": True,
                        "notes": "trust me",
                        "criterion_scores": criterion_scores,
                        "dimension_scores": {},
                    },
                )
                self.assertEqual(verdict["status"], "harness_error")
                self.assertIsNone(verdict["overall_score"])
                self.assertIsNone(verdict["pass"])
                self.assertIn("invalid judge verdict", verdict["notes"])

    def test_required_sections_and_forbidden_behaviors_are_scored_checks(self) -> None:
        case = {
            "prompt": "test",
            "expected_output": "working answer",
            "assertions": ["works"],
            "failure_mode": "does not work",
            "required_output_sections": ["Final prompt"],
            "forbidden_behaviors": ["invented dialogue"],
        }
        ordinary_only = eval_run.normalize_verdict(case, valid_verdict())
        self.assertEqual(ordinary_only["status"], "harness_error")
        self.assertIsNone(ordinary_only["overall_score"])
        self.assertIsNone(ordinary_only["pass"])
        self.assertIn("cover every judge criterion ID", ordinary_only["notes"])

        checks = eval_run.expected_judge_checks(case)
        forbidden_unmet = eval_run.normalize_verdict(
            case,
            {
                "overall_score": 3,
                "pass": True,
                "notes": "trust me",
                "criterion_scores": {
                    check: check != "f0"
                    for check in checks
                },
                "dimension_scores": {},
            },
        )
        self.assertEqual(forbidden_unmet["status"], "harness_error")
        self.assertIsNone(forbidden_unmet["overall_score"])
        self.assertIsNone(forbidden_unmet["pass"])
        self.assertIn("pass cannot be true", forbidden_unmet["notes"])

    def test_sequence_verdict_requires_every_rubric_dimension(self) -> None:
        case = {
            "prompt": "test",
            "expected_output": "working answer",
            "assertions": ["works"],
            "failure_mode": "does not work",
            "critical": True,
            "expected_state_delta": "accepted footage updates canon",
            "expected_prompt_architecture": "state -> contract -> prompt",
            "expected_sequence_relation": "standalone",
        }
        verdict = eval_run.normalize_verdict(
            case,
            {
                "overall_score": 4,
                "pass": True,
                "notes": "looks complete",
                "criterion_scores": {
                    criterion_id: True
                    for criterion_id in eval_run.expected_judge_checks(case)
                },
                "dimension_scores": {
                    dimension_id: 4
                    for dimension_id in eval_run.SEQUENCE_DIMENSION_IDS[:-1]
                },
            },
        )

        self.assertEqual(verdict["status"], "harness_error")
        self.assertIsNone(verdict["overall_score"])
        self.assertIsNone(verdict["pass"])
        self.assertIn("every sequence dimension ID", verdict["notes"])


class InputContractTests(unittest.TestCase):
    def write_case_repo(self, root: Path, first_case: dict) -> None:
        (root / "evals").mkdir(parents=True)
        (root / "references").mkdir()
        (root / "skills").mkdir()
        (root / "SKILL.md").write_text("# test skill\n", encoding="utf-8")
        (root / "references" / "eval-rubric.md").write_text(
            EXACT_RUBRIC, encoding="utf-8"
        )
        def complete(case: dict) -> dict:
            return {
                "expected_output": "usable answer",
                "failure_mode": "incorrect answer",
                "skills_expected_to_activate": ["seedance-20"],
                **case,
            }

        cases = [complete(first_case)]
        cases.extend(
            complete(
                {
                    "id": f"valid-{index}",
                    "prompt": "test",
                    "assertions": ["works"],
                }
            )
            for index in range(2, 17)
        )
        (root / "skills" / "seedance-prompt").mkdir()
        (root / "skills" / "seedance-prompt" / "SKILL.md").write_text(
            "INSIDE-SKILL-SENTINEL", encoding="utf-8"
        )
        (root / "evals" / "fixtures").mkdir()
        (root / "evals" / "fixtures" / "state.json").write_text(
            json.dumps({"state": "INSIDE-STATE-SENTINEL"}), encoding="utf-8"
        )
        (root / "evals" / "evals.json").write_text(
            json.dumps({"cases": cases}), encoding="utf-8"
        )
        write_source_manifest(root)

    def test_self_test_rejects_unhashable_case_ids_without_a_traceback(self) -> None:
        for invalid_id in ([], {}):
            with self.subTest(invalid_id=invalid_id), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.write_case_repo(
                    root,
                    {"id": invalid_id, "prompt": "test", "assertions": ["works"]},
                )

                output = io.StringIO()
                with redirect_stdout(output):
                    code = eval_run.self_test(
                        root, enforce_canonical_contract=False
                    )

                self.assertEqual(code, 1)
                self.assertIn("id must be a lowercase ASCII slug", output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())

    def test_deeply_nested_eval_json_fails_cleanly_at_both_cli_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evals").mkdir()
            (root / "references").mkdir()
            (root / "SKILL.md").write_text("# test skill\n", encoding="utf-8")
            (root / "references" / "eval-rubric.md").write_text(
                EXACT_RUBRIC, encoding="utf-8"
            )
            nested_id = "[" * 1100 + '"x"' + "]" * 1100
            (root / "evals" / "evals.json").write_text(
                '{"cases":[{"id":'
                + nested_id
                + ',"prompt":"test","assertions":["works"]}]}',
                encoding="utf-8",
            )
            write_source_manifest(root)
            real_freeze = eval_run.freeze_repository

            for argv, expected_code, expected_message in (
                (["eval_run.py", str(root), "--self-test"], 1, "self-test FAILED"),
                (["eval_run.py", str(root)], 2, "Could not freeze evaluation inputs"),
            ):
                with self.subTest(argv=argv):
                    output = io.StringIO()
                    with (
                        mock.patch.object(sys, "argv", argv),
                        mock.patch.object(
                            eval_run,
                            "freeze_repository",
                            side_effect=lambda candidate, **_: real_freeze(
                                candidate, enforce_canonical_contract=False
                            ),
                        ),
                        redirect_stdout(output),
                    ):
                        code = eval_run.main()
                    self.assertEqual(code, expected_code)
                    self.assertIn(expected_message, output.getvalue())
                    self.assertIn("maximum JSON nesting depth", output.getvalue())
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
                "state_fixture must be a non-empty UTF-8 string",
            ),
            ("critical", [], "critical must be a boolean"),
            (
                "expected_sequence_relation",
                None,
                "sequence cases must declare every sequence judge contract",
            ),
        )
        for field, value, expected in mutations:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                case = {"id": "one", "prompt": "test", "assertions": ["works"]}
                case[field] = value
                self.write_case_repo(root, case)

                output = io.StringIO()
                with redirect_stdout(output):
                    code = eval_run.self_test(
                        root, enforce_canonical_contract=False
                    )

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
                ("state_fixture", "evals/fixtures/state.json:alternate"),
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
                        code = eval_run.self_test(
                            root, enforce_canonical_contract=False
                        )

                    self.assertEqual(code, 1)
                    self.assertNotIn("Traceback", output.getvalue())
                    self.assertNotIn("OUTSIDE-STATE-SENTINEL", output.getvalue())
                    self.assertNotIn("OUTSIDE-SKILL-SENTINEL", output.getvalue())

    def test_nonportable_aliases_are_rejected_before_live_provider_calls(self) -> None:
        mutations = (
            ("state_fixture", "evals/fixtures/state.json."),
            ("state_fixture", "evals/fixtures/state.json "),
            ("state_fixture", "Fixtures/State.JSON"),
            ("state_fixture", "evals/fixtures/./state.json"),
            ("state_fixture", "evals/fixtures//state.json"),
            ("state_fixture", "evals/fixtures/NUL.json"),
            ("state_fixture", "evals/fixtures/cafe\u0301.json"),
            ("state_fixture", "evals/fixtures/state\u200d.json"),
            ("state_fixture", "evals/fixtures/state\u034f.json"),
            ("state_fixture", "evals/fixtures/state\x7f.json"),
            ("state_fixture", r"evals\fixtures\state.json"),
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

                self_output = io.StringIO()
                with redirect_stdout(self_output):
                    self_code = eval_run.self_test(
                        root, enforce_canonical_contract=False
                    )
                self.assertEqual(self_code, 1, self_output.getvalue())
                self.assertNotIn("Traceback", self_output.getvalue())

                api_call = mock.Mock(return_value="candidate response")
                live_output = io.StringIO()
                real_freeze = eval_run.freeze_repository
                with (
                    mock.patch.object(
                        sys, "argv", ["eval_run.py", str(root), "--limit", "1"]
                    ),
                    mock.patch.dict(
                        os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                    ),
                    mock.patch.object(eval_run, "call_api", api_call),
                    mock.patch.object(
                        eval_run,
                        "freeze_repository",
                        side_effect=lambda candidate, **_: real_freeze(
                            candidate, enforce_canonical_contract=False
                        ),
                    ),
                    redirect_stdout(live_output),
                ):
                    live_code = eval_run.main()
                self.assertEqual(live_code, 2, live_output.getvalue())
                self.assertIn("Could not freeze evaluation inputs", live_output.getvalue())
                self.assertNotIn("Traceback", live_output.getvalue())
                api_call.assert_not_called()

    def test_portable_exact_case_paths_remain_valid(self) -> None:
        cases = (
            ("state_fixture", "evals/fixtures/state.json", "INSIDE-STATE-SENTINEL"),
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
                snapshot = eval_run.freeze_repository(
                    root, enforce_canonical_contract=False
                )
                loaded = eval_run.load_cases(snapshot)
                eval_run.validate_case_contract(snapshot, loaded)
                selected = (
                    ["skills/seedance-prompt/SKILL.md"]
                    if field == "skills_expected_to_activate"
                    else []
                )
                payload = (
                    eval_run.responder_context(snapshot, selected)
                    + eval_run.responder_user_input(snapshot, loaded[0])
                )
                self.assertIn(marker, payload)

    def test_freezer_binds_every_repository_input_identity(self) -> None:
        targets = (
            eval_run.SOURCE_MANIFEST_PATH,
            "SKILL.md",
            "skills/seedance-prompt/SKILL.md",
            "evals/fixtures/state.json",
        )
        for target in targets:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.write_case_repo(
                    root,
                    {
                        "id": "one",
                        "prompt": "test",
                        "assertions": ["works"],
                        "skills_expected_to_activate": ["seedance-prompt"],
                        "state_fixture": "evals/fixtures/state.json",
                    },
                )
                replacement = root / "replacement.txt"
                replacement.write_text("REPLACEMENT", encoding="utf-8")
                original_resolve = eval_run._resolve_confined_file
                resolutions = 0

                def swap_identity(candidate_root: Path, relative: str) -> Path:
                    nonlocal resolutions
                    resolved = original_resolve(candidate_root, relative)
                    if relative != target:
                        return resolved
                    resolutions += 1
                    return resolved if resolutions == 1 else replacement

                with mock.patch.object(
                    eval_run, "_resolve_confined_file", swap_identity
                ), self.assertRaisesRegex(eval_run.HarnessError, "changed while"):
                    eval_run.freeze_repository(
                        root, enforce_canonical_contract=False
                    )

    def test_eval_case_file_is_read_from_one_bound_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = {"id": "one", "prompt": "test", "assertions": ["works"]}
            self.write_case_repo(root, case)
            replacement = root / "replacement-evals.json"
            replacement.write_text(
                json.dumps({"cases": [case]}), encoding="utf-8"
            )
            original_resolve = eval_run._resolve_confined_file
            resolutions = 0

            def swap_eval_identity(candidate_root: Path, relative: str) -> Path:
                nonlocal resolutions
                resolved = original_resolve(candidate_root, relative)
                if relative != "evals/evals.json":
                    return resolved
                resolutions += 1
                return resolved if resolutions == 1 else replacement

            with mock.patch.object(
                eval_run, "_resolve_confined_file", swap_eval_identity
            ), self.assertRaisesRegex(eval_run.HarnessError, "changed while"):
                eval_run.freeze_repository(root, enforce_canonical_contract=False)

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
                real_freeze = eval_run.freeze_repository
                with (
                    mock.patch.object(
                        sys, "argv", ["eval_run.py", str(root), "--limit", "1"]
                    ),
                    mock.patch.dict(
                        os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                    ),
                    mock.patch.object(eval_run, "call_api", api_call),
                    mock.patch.object(
                        eval_run,
                        "freeze_repository",
                        side_effect=lambda candidate, **_: real_freeze(
                            candidate, enforce_canonical_contract=False
                        ),
                    ),
                    redirect_stdout(output),
                ):
                    code = eval_run.main()

                self.assertEqual(code, 2)
                self.assertIn("Could not freeze evaluation inputs", output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())
                api_call.assert_not_called()

    def test_live_mode_preflights_all_selected_contexts_before_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = {"id": "one", "prompt": "test", "assertions": ["works"]}
            self.write_case_repo(root, first)
            eval_path = root / "evals" / "evals.json"
            data = json.loads(eval_path.read_text(encoding="utf-8"))
            data["cases"][1]["state_fixture"] = "evals/fixtures/bad-state.json"
            eval_path.write_text(json.dumps(data), encoding="utf-8")
            fixture = root / "evals" / "fixtures" / "bad-state.json"
            fixture.write_bytes(b"\xff\xfe\x00")
            write_source_manifest(root)

            api_call = mock.Mock(return_value="candidate response")
            output = io.StringIO()
            real_freeze = eval_run.freeze_repository
            with (
                mock.patch.object(sys, "argv", ["eval_run.py", str(root)]),
                mock.patch.dict(
                    os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True
                ),
                mock.patch.object(eval_run, "call_api", api_call),
                mock.patch.object(
                    eval_run,
                    "freeze_repository",
                    side_effect=lambda candidate, **_: real_freeze(
                        candidate, enforce_canonical_contract=False
                    ),
                ),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            self.assertEqual(code, 2, output.getvalue())
            self.assertIn("Could not freeze evaluation inputs", output.getvalue())
            self.assertIn("not UTF-8", output.getvalue())
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
                self.assertIn("Could not freeze evaluation inputs", output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())
                api_call.assert_not_called()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = {"id": "one", "prompt": "test", "assertions": ["works"]}
            self.write_case_repo(root, case)
            original_resolve = eval_run._resolve_confined_file
            replacement = root / "replacement-rubric.md"
            replacement.write_text(EXACT_RUBRIC, encoding="utf-8")
            rubric_resolutions = 0

            def swap_rubric_identity(candidate_root: Path, relative: str) -> Path:
                nonlocal rubric_resolutions
                resolved = original_resolve(candidate_root, relative)
                if relative != "references/eval-rubric.md":
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
                    eval_run, "_resolve_confined_file", swap_rubric_identity
                ),
                mock.patch.object(eval_run, "call_api", api_call),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            self.assertEqual(code, 2, output.getvalue())
            self.assertIn("changed while it was being frozen", output.getvalue())
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
                self.assertIn("Could not freeze evaluation inputs", output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())
                api_call.assert_not_called()

    def test_valid_contained_state_fixture_is_included(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = {
                "id": "one",
                "prompt": "test",
                "assertions": ["works"],
                "state_fixture": "evals/fixtures/state.json",
            }
            self.write_case_repo(root, case)
            snapshot = eval_run.freeze_repository(
                root, enforce_canonical_contract=False
            )
            loaded = eval_run.load_cases(snapshot)
            eval_run.validate_case_contract(snapshot, loaded)
            self.assertIn(
                "INSIDE-STATE-SENTINEL",
                eval_run.responder_user_input(snapshot, loaded[0]),
            )

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
                        eval_run._parse_cases_text(document)

    def test_invalid_eval_json_fails_cleanly_in_self_test_and_live_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evals").mkdir()
            (root / "references").mkdir()
            (root / "SKILL.md").write_text("# test skill\n", encoding="utf-8")
            (root / "references" / "eval-rubric.md").write_text(
                EXACT_RUBRIC, encoding="utf-8"
            )
            (root / "evals" / "evals.json").write_text(
                '{"cases":[{"id":"one","id":"forged"}]}',
                encoding="utf-8",
            )
            write_source_manifest(root)
            real_freeze = eval_run.freeze_repository

            for argv, expected_code, expected_message in (
                (
                    ["eval_run.py", str(root), "--self-test"],
                    1,
                    "self-test FAILED",
                ),
                (["eval_run.py", str(root)], 2, "Could not freeze evaluation inputs"),
            ):
                output = io.StringIO()
                with (
                    mock.patch.object(sys, "argv", argv),
                    mock.patch.object(
                        eval_run,
                        "freeze_repository",
                        side_effect=lambda candidate, **_: real_freeze(
                            candidate, enforce_canonical_contract=False
                        ),
                    ),
                    redirect_stdout(output),
                ):
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
            write_source_manifest(root)
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
            self.assertIn("Could not freeze evaluation inputs", output.getvalue())
            call.assert_not_called()


class LedgerIntegrityTests(unittest.TestCase):
    def make_repo(self, root: Path, cases: list[dict]) -> None:
        (root / "evals").mkdir(parents=True)
        (root / "references").mkdir()
        normalized = []
        for case in cases:
            normalized.append(
                {
                    **case,
                    "expected_output": case.get("expected_output", "usable answer"),
                    "failure_mode": case.get("failure_mode", "incorrect answer"),
                    "skills_expected_to_activate": case.get(
                        "skills_expected_to_activate", ["seedance-20"]
                    ),
                }
            )
        (root / "evals" / "evals.json").write_text(
            json.dumps({"cases": normalized}), encoding="utf-8"
        )
        (root / "references" / "eval-rubric.md").write_text(
            EXACT_RUBRIC, encoding="utf-8"
        )
        (root / "SKILL.md").write_text("# test skill", encoding="utf-8")
        write_source_manifest(root)

    def run_main(
        self,
        argv: list[str],
        verdict: dict,
        *,
        environment: dict[str, str] | None = None,
    ) -> tuple[int, str, mock.Mock, mock.Mock]:
        output = io.StringIO()
        call = mock.Mock(return_value=(verdict, []))
        judge = mock.Mock()
        real_freeze = eval_run.freeze_repository

        def release_like_freeze(root: Path) -> eval_run.FrozenRepository:
            frozen = real_freeze(root, enforce_canonical_contract=False)
            return eval_run.FrozenRepository(
                root=frozen.root,
                files=frozen.files,
                manifest=frozen.manifest,
                canonical_contract_bound=True,
                evaluator_execution_bound=True,
            )

        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(
                os.environ,
                environment or {"ANTHROPIC_API_KEY": "test-key"},
                clear=True,
            ),
            mock.patch.object(
                eval_run,
                "freeze_repository",
                side_effect=release_like_freeze,
            ),
            mock.patch.object(eval_run, "_verify_canonical_evaluation_contract"),
            mock.patch.object(eval_run, "_verify_evaluator_execution_identity"),
            mock.patch.object(eval_run, "run_case", call),
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

    def test_invalid_judge_fields_become_a_harness_error_artifact(self) -> None:
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
            self.assertIn("Release verdict: **NOT ELIGIBLE**", text)
            self.assertIn("**0 scored**, **1 harness error(s)**", text)
            self.assertIn("invalid judge verdict", text.lower())
            self.assertIn(
                "| one | harness_error | 0-3 | n/a | root only | n/a | n/a |",
                text,
            )

    def test_malformed_provider_response_becomes_harness_error_artifact(self) -> None:
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
            real_freeze = eval_run.freeze_repository

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
                    "freeze_repository",
                    side_effect=lambda root: real_freeze(
                        root, enforce_canonical_contract=False
                    ),
                ),
                mock.patch.object(
                    eval_run,
                    "run_case",
                    side_effect=eval_run.ProviderResponseError("invalid body"),
                ),
                mock.patch.object(eval_run, "judge", judge),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(code, 1)
            self.assertNotIn("stale passing artifact", text)
            self.assertIn("Release verdict: **NOT ELIGIBLE**", text)
            self.assertIn("discovery transport error: invalid body", text)
            self.assertIn("| one | harness_error |", text)
            self.assertNotIn("| one | harness_error | 0-3 | n/a | discovery failed | 0 |", text)
            judge.assert_not_called()

    def test_judge_transport_failure_is_auditable_but_not_scored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(
                root,
                [{"id": "one", "prompt": "test", "assertions": ["works"]}],
            )
            ledger = root / "evals" / "eval-run-ledger.md"
            ledger.write_text("stale passing artifact\n", encoding="utf-8")
            output = io.StringIO()
            real_freeze = eval_run.freeze_repository

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
                    "freeze_repository",
                    side_effect=lambda root: real_freeze(
                        root, enforce_canonical_contract=False
                    ),
                ),
                mock.patch.object(
                    eval_run,
                    "run_case",
                    side_effect=eval_run.CaseRunError(
                        "judge error: timed out before a verdict", []
                    ),
                ),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(code, 1)
            self.assertNotIn("stale passing artifact", text)
            self.assertIn("Release verdict: **NOT ELIGIBLE**", text)
            self.assertIn("judge error: timed out before a verdict", text)
            self.assertIn(
                "| one | harness_error | 0-3 | n/a | root only | n/a | n/a |",
                text,
            )
            self.assertNotIn("Legacy (0-3):", output.getvalue())

    def test_snapshot_drift_invalidates_every_score_without_zeroing_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(
                root,
                [{"id": "one", "prompt": "test", "assertions": ["works"]}],
            )
            ledger = root / "evals" / "eval-run-ledger.md"
            output = io.StringIO()
            real_freeze = eval_run.freeze_repository

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
                    "freeze_repository",
                    side_effect=lambda root: real_freeze(
                        root, enforce_canonical_contract=False
                    ),
                ),
                mock.patch.object(
                    eval_run, "run_case", return_value=(valid_verdict(), [])
                ),
                mock.patch.object(
                    eval_run,
                    "verify_snapshot_unchanged",
                    side_effect=eval_run.HarnessError("digest drift"),
                ),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(code, 2)
            self.assertIn("Release verdict: **NOT ELIGIBLE**", text)
            self.assertIn("snapshot verification failure: digest drift", text)
            self.assertIn(
                "| one | harness_error | 0-3 | n/a | root only | n/a | n/a |",
                text,
            )
            self.assertNotIn("| one | harness_error | 0-3 | n/a | root only | 0 |", text)

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
                    snapshot=release_snapshot(),
                )

            self.assertEqual(
                path.read_text(encoding="utf-8"), "previous complete evidence\n"
            )
            self.assertEqual(list(path.parent.glob(".ledger.md.*.tmp")), [])

    def test_atomic_overwrite_preserves_destination_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")
            if os.name == "posix":
                os.chmod(path, 0o644)
            elif os.name == "nt":
                os.chmod(path, stat.S_IREAD)

            try:
                eval_run._atomic_write_text(path, "new evidence\n")

                self.assertEqual(path.read_text(encoding="utf-8"), "new evidence\n")
                if os.name == "posix":
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o644)
                elif os.name == "nt":
                    self.assertTrue(
                        eval_run._windows_status_is_read_only(path.stat())
                    )
            finally:
                if os.name == "nt" and path.exists():
                    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)

    def test_atomic_rollback_preserves_content_and_destination_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")
            if os.name == "posix":
                os.chmod(path, 0o644)
            elif os.name == "nt":
                os.chmod(path, stat.S_IREAD)
            observed_backup_modes: list[int] = []

            def reject_replacement() -> None:
                if os.name == "posix":
                    backups = list(path.parent.glob(".ledger.md.*.rollback"))
                    self.assertEqual(len(backups), 1)
                    observed_backup_modes.append(
                        stat.S_IMODE(backups[0].stat().st_mode)
                    )
                raise eval_run.HarnessError("post-replace check failed")

            try:
                with self.assertRaisesRegex(
                    eval_run.HarnessError, "post-replace check failed"
                ):
                    eval_run._atomic_write_text(
                        path,
                        "new evidence\n",
                        after_replace=reject_replacement,
                    )

                self.assertEqual(path.read_text(encoding="utf-8"), "old evidence\n")
                if os.name == "posix":
                    self.assertEqual(observed_backup_modes, [0o644])
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o644)
                elif os.name == "nt":
                    self.assertTrue(
                        eval_run._windows_status_is_read_only(path.stat())
                    )
                self.assertEqual(list(path.parent.glob(".ledger.md.*.tmp")), [])
                self.assertEqual(
                    list(path.parent.glob(".ledger.md.*.rollback")), []
                )
            finally:
                if os.name == "nt" and path.exists():
                    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)

    def test_atomic_new_ledger_uses_secure_non_inherited_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"

            eval_run._atomic_write_text(path, "new evidence\n")

            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            elif os.name == "nt":
                self.assertFalse(eval_run._windows_status_is_read_only(path.stat()))

    def test_atomic_write_rejects_destination_permission_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")
            if os.name == "posix":
                os.chmod(path, 0o644)
            elif os.name == "nt":
                os.chmod(path, stat.S_IREAD | stat.S_IWRITE)

            def mutate_permissions() -> None:
                if os.name == "posix":
                    os.chmod(path, 0o600)
                elif os.name == "nt":
                    os.chmod(path, stat.S_IREAD)

            try:
                with self.assertRaisesRegex(
                    eval_run.HarnessError, "permission mode|read-only attribute"
                ):
                    eval_run._atomic_write_text(
                        path,
                        "new evidence\n",
                        before_replace=mutate_permissions,
                    )

                self.assertEqual(path.read_text(encoding="utf-8"), "old evidence\n")
            finally:
                if os.name == "nt" and path.exists():
                    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute regression")
    def test_atomic_write_never_clears_a_read_only_hardlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.md"
            destination = Path(tmp) / "ledger.md"
            source.write_text("shared evidence\n", encoding="utf-8")
            os.link(source, destination)
            os.chmod(source, stat.S_IREAD)

            try:
                with self.assertRaisesRegex(
                    eval_run.HarnessError, "hard links"
                ):
                    eval_run._atomic_write_text(destination, "new evidence\n")

                self.assertTrue(source.samefile(destination))
                self.assertEqual(source.read_text(encoding="utf-8"), "shared evidence\n")
                self.assertTrue(eval_run._windows_status_is_read_only(source.stat()))
            finally:
                os.chmod(source, stat.S_IREAD | stat.S_IWRITE)

    def test_atomic_write_rejects_any_hardlink_before_creating_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.md"
            destination = Path(tmp) / "ledger.md"
            source.write_text("shared evidence\n", encoding="utf-8")
            os.link(source, destination)

            with (
                mock.patch.object(eval_run.tempfile, "mkstemp") as mkstemp,
                self.assertRaisesRegex(eval_run.HarnessError, "hard links"),
            ):
                eval_run._atomic_write_text(destination, "new evidence\n")

            mkstemp.assert_not_called()
            self.assertTrue(source.samefile(destination))
            self.assertEqual(source.read_text(encoding="utf-8"), "shared evidence\n")

    @unittest.skipUnless(os.name == "nt", "Windows ADS regression")
    def test_windows_alternate_stream_fails_before_temp_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")
            Path(str(path) + ":audit").write_text("hidden evidence", encoding="utf-8")

            with (
                mock.patch.object(eval_run.tempfile, "mkstemp") as mkstemp,
                self.assertRaisesRegex(
                    eval_run.HarnessError, "alternate data streams"
                ),
            ):
                eval_run._atomic_write_text(path, "new evidence\n")

            mkstemp.assert_not_called()
            self.assertEqual(path.read_text(encoding="utf-8"), "old evidence\n")

    @unittest.skipUnless(os.name == "nt", "Windows attribute regression")
    def test_windows_unsupported_attributes_fail_before_temp_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")
            original_attributes = path.stat().st_file_attributes
            eval_run._set_windows_attributes(
                path,
                original_attributes | 0x2,  # FILE_ATTRIBUTE_HIDDEN
                "test ledger",
            )
            try:
                with (
                    mock.patch.object(eval_run.tempfile, "mkstemp") as mkstemp,
                    self.assertRaisesRegex(
                        eval_run.HarnessError, "unsupported Windows file attributes"
                    ),
                ):
                    eval_run._atomic_write_text(path, "new evidence\n")
                mkstemp.assert_not_called()
                self.assertEqual(path.read_text(encoding="utf-8"), "old evidence\n")
            finally:
                eval_run._set_windows_attributes(
                    path, original_attributes, "test ledger"
                )

    @unittest.skipUnless(os.name == "nt", "Windows owner and DACL regression")
    def test_windows_owner_or_dacl_mismatch_fails_before_destination_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")
            real_descriptor = eval_run._windows_security_descriptor

            def mismatched_descriptor(candidate: Path, label: str) -> bytes:
                descriptor = real_descriptor(candidate, label)
                return descriptor if candidate == path else descriptor + b"mismatch"

            with (
                mock.patch.object(
                    eval_run,
                    "_windows_security_descriptor",
                    side_effect=mismatched_descriptor,
                ),
                self.assertRaisesRegex(eval_run.HarnessError, "owner or DACL"),
            ):
                eval_run._atomic_write_text(path, "new evidence\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "old evidence\n")
            self.assertEqual(list(path.parent.glob(".ledger.md.*.tmp")), [])

    def test_temporary_bytes_are_hash_bound_before_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")

            def tamper_with_temporary() -> None:
                temporary = next(path.parent.glob(".ledger.md.*.tmp"))
                status = temporary.stat()
                temporary.write_bytes(b"X" * status.st_size)
                os.utime(
                    temporary,
                    ns=(status.st_atime_ns, status.st_mtime_ns),
                )

            with self.assertRaisesRegex(
                eval_run.HarnessError, "temporary ledger bytes changed"
            ):
                eval_run._atomic_write_text(
                    path,
                    "new evidence\n",
                    before_replace=tamper_with_temporary,
                )

            self.assertEqual(path.read_text(encoding="utf-8"), "old evidence\n")

    def test_private_temporary_hardlink_is_rejected_before_destination_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")
            alias = Path(tmp) / "temporary-alias.md"
            real_apply = eval_run._apply_ledger_permissions

            def hardlink_temporary(
                candidate: Path,
                expected: eval_run.LedgerDestinationState,
                label: str,
            ) -> None:
                real_apply(candidate, expected, label)
                if label == "temporary ledger":
                    os.link(candidate, alias)

            try:
                with (
                    mock.patch.object(
                        eval_run,
                        "_apply_ledger_permissions",
                        side_effect=hardlink_temporary,
                    ),
                    self.assertRaisesRegex(
                        eval_run.HarnessError,
                        "temporary ledger must not have hard links",
                    ),
                ):
                    eval_run._atomic_write_text(path, "new evidence\n")

                self.assertEqual(path.read_text(encoding="utf-8"), "old evidence\n")
            finally:
                alias.unlink(missing_ok=True)

    def test_tampered_rollback_bytes_are_detected_and_retained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")

            def tamper_then_reject() -> None:
                backup = next(path.parent.glob(".ledger.md.*.rollback"))
                status = backup.stat()
                backup.write_bytes(b"X" * status.st_size)
                os.utime(backup, ns=(status.st_atime_ns, status.st_mtime_ns))
                raise eval_run.HarnessError("post-check failed")

            with self.assertRaisesRegex(
                eval_run.HarnessError, "recovery retained"
            ):
                eval_run._atomic_write_text(
                    path,
                    "new evidence\n",
                    after_replace=tamper_then_reject,
                )

            self.assertEqual(path.read_text(encoding="utf-8"), "new evidence\n")
            backups = list(path.parent.glob(".ledger.md.*.rollback"))
            self.assertEqual(len(backups), 1)

    def test_recovery_survives_until_restored_metadata_is_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")
            real_verify = eval_run._verify_ledger_status

            def reject_restored_metadata(
                status: os.stat_result,
                expected: eval_run.LedgerDestinationState,
                label: str,
                *,
                bind_identity: bool,
            ) -> None:
                real_verify(
                    status,
                    expected,
                    label,
                    bind_identity=bind_identity,
                )
                if label == "restored ledger":
                    raise eval_run.HarnessError("restored metadata unverified")

            with (
                mock.patch.object(
                    eval_run,
                    "_verify_ledger_status",
                    side_effect=reject_restored_metadata,
                ),
                self.assertRaisesRegex(eval_run.HarnessError, "recovery retained"),
            ):
                eval_run._atomic_write_text(
                    path,
                    "new evidence\n",
                    after_replace=lambda: (_ for _ in ()).throw(
                        eval_run.HarnessError("post-check failed")
                    ),
                )

            self.assertEqual(path.read_text(encoding="utf-8"), "old evidence\n")
            self.assertEqual(
                len(list(path.parent.glob(".ledger.md.*.rollback"))), 1
            )

    def test_failed_post_check_invalidates_owned_new_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"

            with (
                mock.patch.object(
                    eval_run.Path,
                    "unlink",
                    side_effect=OSError("unlink blocked"),
                ) as unlink,
                mock.patch.object(
                    eval_run.Path,
                    "rmdir",
                    side_effect=OSError("rmdir blocked"),
                ) as rmdir,
                self.assertRaisesRegex(eval_run.HarnessError, "post-check failed"),
            ):
                eval_run._atomic_write_text(
                    path,
                    "new evidence\n",
                    after_replace=lambda: (_ for _ in ()).throw(
                        eval_run.HarnessError("post-check failed")
                    ),
                )

            unlink.assert_not_called()
            rmdir.assert_not_called()
            if os.name == "nt":
                self.assertFalse(path.exists())
            else:
                self.assertTrue(path.exists())
                self.assertEqual(path.read_bytes(), b"")
            self.assertEqual(list(path.parent.glob(".ledger-*.tmp")), [])

    def test_tampered_new_destination_is_invalidated_after_post_check_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"

            def tamper_then_reject() -> None:
                if os.name == "nt":
                    # FileRenameInformation retains the publishing handle through
                    # the post-check, so Win32 correctly refuses path writes.
                    raise eval_run.HarnessError("post-check failed")
                status = path.stat()
                path.write_bytes(b"X" * status.st_size)
                os.utime(path, ns=(status.st_atime_ns, status.st_mtime_ns))
                raise eval_run.HarnessError("post-check failed")

            with self.assertRaisesRegex(eval_run.HarnessError, "post-check failed"):
                eval_run._atomic_write_text(
                    path,
                    "new evidence\n",
                    after_replace=tamper_then_reject,
                )

            if os.name == "nt":
                self.assertFalse(path.exists())
            else:
                self.assertEqual(path.read_bytes(), b"")
            self.assertEqual(list(path.parent.glob(".ledger-*.tmp")), [])

    @unittest.skipUnless(os.name == "nt", "Windows handle-bound publication")
    def test_windows_zero_share_stage_rejects_native_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            import ctypes
            from ctypes import wintypes

            root = Path(tmp)
            path = root / "ledger.md"
            payload = "verified evidence\n"
            source_paths: list[Path] = []
            real_create = eval_run._create_windows_new_ledger_stage

            def capture_stage(*arguments: object) -> tuple:
                stage = real_create(*arguments)
                source_paths.append(stage[3])
                return stage

            def attempt_native_write_open() -> None:
                source = source_paths[0]
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                create_file = kernel32.CreateFileW
                create_file.argtypes = (
                    wintypes.LPCWSTR,
                    wintypes.DWORD,
                    wintypes.DWORD,
                    wintypes.LPVOID,
                    wintypes.DWORD,
                    wintypes.DWORD,
                    wintypes.HANDLE,
                )
                create_file.restype = wintypes.HANDLE
                handle = create_file(
                    str(source),
                    0x40000000,  # GENERIC_WRITE
                    0x1 | 0x2 | 0x4,
                    None,
                    3,  # OPEN_EXISTING
                    0x80,
                    None,
                )
                self.assertEqual(handle, ctypes.c_void_p(-1).value)
                self.assertEqual(ctypes.get_last_error(), 32)

            with mock.patch.object(
                eval_run,
                "_create_windows_new_ledger_stage",
                side_effect=capture_stage,
            ):
                eval_run._atomic_write_text(
                    path,
                    payload,
                    before_replace=attempt_native_write_open,
                )

            self.assertEqual(path.read_text(encoding="utf-8"), payload)
            self.assertEqual(list(root.glob(".ledger-*.tmp")), [])

    @unittest.skipUnless(os.name == "nt", "Windows retained-parent publication")
    def test_windows_parent_rename_recreate_boundary_is_locked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "ledger-parent"
            parent.mkdir()
            path = parent / "ledger.md"
            moved_parent = root / "renamed-parent"
            rename_was_blocked = False

            def attempt_parent_replacement() -> None:
                nonlocal rename_was_blocked
                try:
                    os.replace(parent, moved_parent)
                except PermissionError:
                    rename_was_blocked = True
                    return
                self.fail("zero-share stage unexpectedly allowed parent rename")

            eval_run._atomic_write_text(
                path,
                "verified evidence\n",
                before_replace=attempt_parent_replacement,
            )

            self.assertTrue(rename_was_blocked)
            self.assertFalse(moved_parent.exists())
            self.assertEqual(path.read_text(encoding="utf-8"), "verified evidence\n")
            self.assertEqual(list(parent.glob(".ledger-*.tmp")), [])

    @unittest.skipUnless(os.name == "nt", "Windows handle-bound cleanup")
    def test_windows_prepublish_failure_cleans_stage_without_path_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "ledger.md"
            with (
                mock.patch.object(
                    eval_run.Path,
                    "unlink",
                    side_effect=AssertionError("pathname unlink is forbidden"),
                ) as unlink,
                mock.patch.object(
                    eval_run.Path,
                    "rmdir",
                    side_effect=AssertionError("pathname rmdir is forbidden"),
                ) as rmdir,
                self.assertRaisesRegex(eval_run.HarnessError, "prepublish failure"),
            ):
                eval_run._atomic_write_text(
                    path,
                    "candidate evidence\n",
                    before_replace=lambda: (_ for _ in ()).throw(
                        eval_run.HarnessError("prepublish failure")
                    ),
                )

            unlink.assert_not_called()
            rmdir.assert_not_called()
            self.assertFalse(path.exists())
            self.assertEqual(list(root.glob(".ledger-*.tmp")), [])

    def test_native_publish_success_then_raise_invalidates_retained_inode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            helper_name = (
                "_publish_windows_bound_new_ledger"
                if os.name == "nt"
                else "_publish_linux_bound_new_ledger"
            )
            real_publish = getattr(eval_run, helper_name)

            def publish_then_raise(*arguments: object) -> None:
                real_publish(*arguments)
                raise eval_run.HarnessError("injected post-native failure")

            with (
                mock.patch.object(
                    eval_run,
                    helper_name,
                    side_effect=publish_then_raise,
                ),
                self.assertRaisesRegex(
                    eval_run.HarnessError,
                    "injected post-native failure",
                ),
            ):
                eval_run._atomic_write_text(path, "candidate evidence\n")

            if os.name == "nt":
                self.assertFalse(path.exists())
            else:
                self.assertTrue(path.exists())
                self.assertEqual(path.read_bytes(), b"")

    def test_late_new_ledger_destination_wins_without_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            helper_name = (
                "_publish_windows_bound_new_ledger"
                if os.name == "nt"
                else "_publish_linux_bound_new_ledger"
            )
            real_publish = getattr(eval_run, helper_name)

            def publish_after_late_winner(*arguments: object) -> None:
                path.write_text("late winner\n", encoding="utf-8")
                real_publish(*arguments)

            with (
                mock.patch.object(
                    eval_run,
                    helper_name,
                    side_effect=publish_after_late_winner,
                ),
                self.assertRaisesRegex(
                    eval_run.HarnessError,
                    "appeared during atomic",
                ),
            ):
                eval_run._atomic_write_text(path, "candidate evidence\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "late winner\n")

    @unittest.skipUnless(os.name == "posix", "POSIX capability boundary")
    def test_posix_without_linux_unnamed_publication_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            with (
                mock.patch.object(
                    eval_run,
                    "_open_linux_unnamed_ledger",
                    side_effect=eval_run.HarnessError(
                        "descriptor-bound publication unavailable"
                    ),
                ),
                mock.patch.object(eval_run.tempfile, "mkstemp") as mkstemp,
                self.assertRaisesRegex(
                    eval_run.HarnessError,
                    "descriptor-bound publication unavailable",
                ),
            ):
                eval_run._atomic_write_text(path, "candidate evidence\n")

            mkstemp.assert_not_called()
            self.assertFalse(path.exists())

    def test_new_ledger_publication_has_exact_identity_and_link_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            eval_run._atomic_write_text(path, "complete evidence\n")

            status = path.stat()
            self.assertTrue(stat.S_ISREG(status.st_mode))
            self.assertEqual(status.st_nlink, 1)
            self.assertEqual(path.read_text(encoding="utf-8"), "complete evidence\n")
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(status.st_mode), 0o600)

    def test_concurrent_new_ledger_writers_publish_one_complete_winner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            barrier = threading.Barrier(2)
            payloads = ("writer one\n", "writer two\n")
            outcomes: list[BaseException | None] = []
            outcome_lock = threading.Lock()

            def writer(payload: str) -> None:
                failure: BaseException | None = None
                try:
                    eval_run._atomic_write_text(
                        path,
                        payload,
                        before_replace=lambda: barrier.wait(timeout=10),
                    )
                except BaseException as exc:
                    failure = exc
                with outcome_lock:
                    outcomes.append(failure)

            threads = [threading.Thread(target=writer, args=(payload,)) for payload in payloads]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=15)

            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(sum(outcome is None for outcome in outcomes), 1, outcomes)
            self.assertEqual(
                sum(isinstance(outcome, eval_run.HarnessError) for outcome in outcomes),
                1,
                outcomes,
            )
            self.assertIn(path.read_text(encoding="utf-8"), payloads)
            self.assertEqual(path.stat().st_nlink, 1)

    def test_new_destination_invalidation_failure_is_reported_without_path_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            payload = "new evidence\n"

            with (
                mock.patch.object(
                    eval_run.os,
                    "ftruncate",
                    side_effect=OSError("truncate blocked"),
                ),
                self.assertRaisesRegex(
                    eval_run.HarnessError,
                    "unverified new ledger could not be invalidated",
                ),
            ):
                eval_run._atomic_write_text(
                    path,
                    payload,
                    after_replace=lambda: (_ for _ in ()).throw(
                        eval_run.HarnessError("post-check failed")
                    ),
                )

            if os.name == "nt":
                self.assertFalse(path.exists())
            else:
                self.assertEqual(path.read_text(encoding="utf-8"), payload)
            self.assertEqual(list(path.parent.glob(".ledger-*.tmp")), [])

    def test_new_destination_invalidation_preserves_old_replace_boundary_swap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "ledger.md"
            published = root / "published-ledger.md"
            substitute = root / "substitute.md"
            payload = "new evidence\n"
            substitute.write_text(payload, encoding="utf-8")
            substitute_status = substitute.stat()
            substitute_identity = (substitute_status.st_dev, substitute_status.st_ino)
            real_invalidate = eval_run._invalidate_bound_new_ledger_descriptor
            swap_blocked = False

            def swap_then_invalidate(
                descriptor: int,
                signature: tuple[int, int, int, int],
                link_count: int,
            ) -> None:
                nonlocal swap_blocked
                if os.name == "nt":
                    with self.assertRaises(PermissionError):
                        os.replace(path, published)
                    swap_blocked = True
                else:
                    os.replace(path, published)
                    os.replace(substitute, path)
                real_invalidate(descriptor, signature, link_count)

            with (
                mock.patch.object(
                    eval_run,
                    "_invalidate_bound_new_ledger_descriptor",
                    side_effect=swap_then_invalidate,
                ) as invalidate,
                self.assertRaisesRegex(eval_run.HarnessError, "post-check failed"),
            ):
                eval_run._atomic_write_text(
                    path,
                    payload,
                    after_replace=lambda: (_ for _ in ()).throw(
                        eval_run.HarnessError("post-check failed")
                    ),
                )

            invalidate.assert_called_once()
            if os.name == "nt":
                self.assertTrue(swap_blocked)
                self.assertFalse(path.exists())
                self.assertFalse(published.exists())
                self.assertEqual(substitute.read_text(encoding="utf-8"), payload)
            else:
                self.assertEqual(path.read_text(encoding="utf-8"), payload)
                current_status = path.stat()
                self.assertEqual(
                    (current_status.st_dev, current_status.st_ino),
                    substitute_identity,
                )
                self.assertEqual(published.read_bytes(), b"")

    def test_new_destination_invalidation_preserves_old_unlink_boundary_swap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "ledger.md"
            published = root / "published-ledger.md"
            substitute = root / "substitute.md"
            payload = "new evidence\n"
            substitute.write_text(payload, encoding="utf-8")
            substitute_status = substitute.stat()
            substitute_identity = (substitute_status.st_dev, substitute_status.st_ino)
            real_ftruncate = os.ftruncate
            swapped = False
            swap_blocked = False

            def swap_then_truncate(descriptor: int, size: int) -> None:
                nonlocal swapped, swap_blocked
                self.assertFalse(swapped)
                if os.name == "nt":
                    with self.assertRaises(PermissionError):
                        os.replace(path, published)
                    swap_blocked = True
                else:
                    os.replace(path, published)
                    os.replace(substitute, path)
                    swapped = True
                real_ftruncate(descriptor, size)

            with (
                mock.patch.object(
                    eval_run.os,
                    "ftruncate",
                    side_effect=swap_then_truncate,
                ),
                self.assertRaisesRegex(eval_run.HarnessError, "post-check failed"),
            ):
                eval_run._atomic_write_text(
                    path,
                    payload,
                    after_replace=lambda: (_ for _ in ()).throw(
                        eval_run.HarnessError("post-check failed")
                    ),
                )

            if os.name == "nt":
                self.assertTrue(swap_blocked)
                self.assertFalse(path.exists())
                self.assertFalse(published.exists())
                self.assertEqual(substitute.read_text(encoding="utf-8"), payload)
            else:
                self.assertTrue(swapped)
                self.assertEqual(path.read_text(encoding="utf-8"), payload)
                current_status = path.stat()
                self.assertEqual(
                    (current_status.st_dev, current_status.st_ino),
                    substitute_identity,
                )
                self.assertEqual(published.read_bytes(), b"")

    def test_verified_commit_reports_cleanup_failure_as_committed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")

            with (
                mock.patch.object(
                    eval_run,
                    "_unlink_bound_atomic_artifact",
                    side_effect=OSError("cleanup failed"),
                ),
                self.assertRaisesRegex(
                    eval_run.CommittedCleanupError, "commit verified"
                ),
            ):
                eval_run._atomic_write_text(path, "new evidence\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "new evidence\n")
            self.assertEqual(
                len(list(path.parent.glob(".ledger.md.*.rollback"))), 1
            )

    def test_oversized_rollback_source_fails_before_temp_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            with path.open("wb") as handle:
                handle.truncate(eval_run.MAX_LEDGER_ARTIFACT_BYTES + 1)

            with (
                mock.patch.object(eval_run.tempfile, "mkstemp") as mkstemp,
                self.assertRaisesRegex(eval_run.HarnessError, "exceeds"),
            ):
                eval_run._atomic_write_text(path, "new evidence\n")

            mkstemp.assert_not_called()
            self.assertEqual(
                path.stat().st_size,
                eval_run.MAX_LEDGER_ARTIFACT_BYTES + 1,
            )

    def test_parent_directory_is_fsynced_for_recovery_commit_and_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("old evidence\n", encoding="utf-8")

            with mock.patch.object(eval_run, "_fsync_parent_directory") as fsync_parent:
                eval_run._atomic_write_text(path, "new evidence\n")

            self.assertGreaterEqual(fsync_parent.call_count, 3)
            self.assertTrue(
                all(call.args == (path,) or call.args[0].parent == path.parent for call in fsync_parent.call_args_list)
            )

    def test_ledger_records_provider_models_scope_and_release_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            rows = frozen_release_rows()

            with redirect_stdout(io.StringIO()):
                eval_run.write_ledger(
                    path,
                    rows,
                    "MiniMax-M2.7",
                    "2026-08-01",
                    "minimax",
                    "cn_zh",
                    judge_model="MiniMax-M2.5",
                    release_eligible=True,
                    snapshot=release_snapshot(),
                )

            text = path.read_text(encoding="utf-8")
            self.assertIn("responder model `MiniMax-M2.7`", text)
            self.assertIn("judge model `MiniMax-M2.5`", text)
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
                    r"review failed \# FORGED RELEASE PASS", result_lines[0]
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
            self.assertGreaterEqual(text.count(r"safe \# FORGED RELEASE PASS"), 5)

    def test_table_metadata_cannot_emit_links_emphasis_or_html(self) -> None:
        injected = "[FORGED](https://evil.example) *PASS* <img src=x>"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            row = result_row(passed=False)
            row["id"] = injected
            row["notes"] = injected
            row["dimension_scores"] = [
                {"dimension": injected, "score": 4}
            ]
            with redirect_stdout(io.StringIO()):
                report = eval_run.write_ledger(
                    path,
                    [row],
                    "model",
                    "2026-08-01",
                    "anthropic",
                    "global_en",
                    expected_cases={
                        injected: {"sequence": True, "critical": True}
                    },
                    total_expected=1,
                    release_eligible=True,
                )

            text = path.read_text(encoding="utf-8")
            self.assertEqual(report["release_verdict"], "FAIL")
            self.assertNotIn("[FORGED](https://evil.example)", text)
            self.assertNotIn("*PASS*", text)
            self.assertNotIn("<img src=x>", text)
            self.assertIn(r"\[FORGED\]\(https://evil.example\)", text)
            self.assertIn(r"\*PASS\*", text)
            self.assertIn("&lt;img src=x&gt;", text)

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

    def test_surrogate_judge_note_becomes_a_fresh_harness_error_artifact(self) -> None:
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
            self.assertIn("Release verdict: **NOT ELIGIBLE**", text)
            self.assertIn("| one | harness_error |", text)
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
            run_args = call.call_args.args
            self.assertEqual(run_args[2], "MiniMax-M2.7")
            self.assertEqual(run_args[3], "MiniMax-M2.7")
            self.assertEqual(run_args[6], eval_run.PROVIDER_CONFIGS["minimax"])
            self.assertEqual(
                run_args[7], "https://api.minimaxi.com/anthropic/v1/messages"
            )
            judge.assert_not_called()


if __name__ == "__main__":
    unittest.main()

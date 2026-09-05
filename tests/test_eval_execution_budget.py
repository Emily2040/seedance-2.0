"""Offline-by-default execution and conservative request reservations."""
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
import eval_run

ROOT = Path(__file__).resolve().parents[1]


class OfflinePlanTests(unittest.TestCase):
    def test_default_with_a_key_and_ledger_neither_transmits_nor_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.md"
            output = io.StringIO()
            with (
                mock.patch.object(sys, "argv", ["eval_run.py", str(ROOT), "--limit", "1", "--ledger", str(ledger)]),
                mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "AUDIT-DUMMY"}),
                mock.patch.object(os.environ, "get", wraps=os.environ.get) as reads,
                mock.patch.object(eval_run, "_open_provider_request") as transport,
                mock.patch.object(eval_run, "write_ledger") as writer,
                redirect_stdout(output),
            ):
                self.assertEqual(eval_run.main(), 0)
            self.assertNotIn(mock.call("ANTHROPIC_API_KEY"), reads.call_args_list)
            transport.assert_not_called()
            writer.assert_not_called()
            self.assertFalse(ledger.exists())
            plan = json.loads(output.getvalue())
            self.assertEqual(plan["mode"], "offline_plan")
            self.assertEqual(plan["case_count"], 1)
            self.assertEqual(plan["max_calls"], 3)
            self.assertEqual(plan["max_output_tokens"], 3300)

    def test_full_live_suite_requires_an_explicit_call_ceiling(self):
        with (
            mock.patch.object(sys, "argv", ["eval_run.py", str(ROOT), "--live"]),
            mock.patch.object(eval_run, "_open_provider_request") as transport,
            redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(eval_run.main(), 2)
        self.assertIn("explicit --max-calls", output.getvalue())
        transport.assert_not_called()

    def test_nonpositive_limits_and_conflicting_modes_are_rejected(self):
        for flags in (["--max-calls", "0"], ["--max-output-tokens", "-1"], ["--self-test", "--live"]):
            with self.subTest(flags=flags), mock.patch.object(sys, "argv", ["eval_run.py", *flags]), mock.patch("sys.stderr", new=io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    eval_run.main()
                self.assertEqual(raised.exception.code, 2)

    def test_cli_exhaustion_stops_cases_returns_failure_and_restores_context(self):
        for limits, expected_calls, expected_cases in (
            (["--max-calls", "1"], 1, 2),
            (["--max-output-tokens", "899"], 0, 1),
        ):
            with (
                self.subTest(limits=limits),
                mock.patch.object(sys, "argv", ["eval_run.py", str(ROOT), "--live", "--limit", "3", *limits]),
                mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "AUDIT-DUMMY"}),
                mock.patch.object(eval_run, "_read_api_response", side_effect=eval_run.ProviderResponseError("uncertain transport")) as transport,
                mock.patch.object(eval_run, "run_case", wraps=eval_run.run_case) as run,
                redirect_stdout(io.StringIO()) as output,
            ):
                self.assertNotEqual(eval_run.main(), 0)
            self.assertEqual(transport.call_count, expected_calls)
            self.assertEqual(run.call_count, expected_cases)
            self.assertIsNone(eval_run._ACTIVE_BUDGET.get())
            summary_line = next(line for line in output.getvalue().splitlines() if line.startswith("Execution budget: "))
            summary = json.loads(summary_line.removeprefix("Execution budget: "))
            self.assertTrue(summary["exhausted"])
            self.assertEqual(summary["attempted_calls"], expected_calls)

    def test_help_never_opens_transport(self):
        with (
            mock.patch.object(sys, "argv", ["eval_run.py", "--help"]),
            mock.patch.object(eval_run, "_open_provider_request") as transport,
            redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            eval_run.main()
        self.assertEqual(raised.exception.code, 0)
        transport.assert_not_called()


class ExecutionBudgetTests(unittest.TestCase):
    def test_call_limit_reserves_failures_and_prevents_the_next_transport(self):
        budget = eval_run.EvaluationBudget(1, 3000)
        token = eval_run._ACTIVE_BUDGET.set(budget)
        try:
            with mock.patch.object(eval_run, "_read_api_response", side_effect=eval_run.ProviderResponseError("uncertain transport")) as transport:
                for _ in range(2):
                    with self.assertRaises(eval_run.ProviderResponseError):
                        eval_run.call_api("s", "u", "model", "AUDIT-DUMMY", eval_run.PROVIDER_CONFIGS["anthropic"], eval_run.ANTHROPIC_API_URL)
                self.assertEqual(transport.call_count, 1)
        finally:
            eval_run._ACTIVE_BUDGET.reset(token)
        self.assertEqual(budget.attempted_calls, 1)
        self.assertEqual(budget.reserved_output_tokens, 1500)
        self.assertTrue(budget.exhausted)
        self.assertTrue(budget.summary()["usage_may_be_incomplete"])

    def test_output_budget_is_reserved_before_a_request(self):
        budget = eval_run.EvaluationBudget(3, 899)
        token = eval_run._ACTIVE_BUDGET.set(budget)
        try:
            with mock.patch.object(eval_run, "_read_api_response") as transport:
                with self.assertRaises(eval_run.ProviderResponseError):
                    eval_run.call_api("s", "u", "model", "AUDIT-DUMMY", eval_run.PROVIDER_CONFIGS["anthropic"], eval_run.ANTHROPIC_API_URL, max_tokens=900)
                transport.assert_not_called()
        finally:
            eval_run._ACTIVE_BUDGET.reset(token)
        self.assertEqual(budget.attempted_calls, 0)
        self.assertTrue(budget.exhausted)

    def test_validated_usage_is_reported_without_refunding_reservations(self):
        body = {"id":"msg_dummy", "type":"message", "role":"assistant", "model":"model", "content":[{"type":"text", "text":"ok"}], "stop_reason":"end_turn", "stop_sequence":None, "usage":{"input_tokens":12,"output_tokens":3}}
        budget = eval_run.EvaluationBudget(1, 1500)
        token = eval_run._ACTIVE_BUDGET.set(budget)
        try:
            with mock.patch.object(eval_run, "_read_api_response", return_value=json.dumps(body).encode()):
                self.assertEqual(eval_run.call_api("s", "u", "model", "AUDIT-DUMMY", eval_run.PROVIDER_CONFIGS["anthropic"], eval_run.ANTHROPIC_API_URL), "ok")
        finally:
            eval_run._ACTIVE_BUDGET.reset(token)
        self.assertEqual(budget.reported_input_tokens, 12)
        self.assertEqual(budget.reported_output_tokens, 3)
        self.assertEqual(budget.reserved_output_tokens, 1500)
        self.assertFalse(budget.summary()["usage_may_be_incomplete"])


if __name__ == "__main__":
    unittest.main()

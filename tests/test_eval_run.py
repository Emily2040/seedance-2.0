from __future__ import annotations

import json
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import eval_run  # noqa: E402


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, amount: int = -1) -> bytes:
        body = b'{"content":[{"type":"text","text":"ok"}]}'
        return body if amount < 0 else body[:amount]


class EvalRunProviderTests(unittest.TestCase):
    def test_minimax_configuration_matches_current_models_and_regions(self) -> None:
        config = eval_run.PROVIDER_CONFIGS["minimax"]

        self.assertEqual(config.default_model, "MiniMax-M3")
        self.assertEqual(config.models, ("MiniMax-M3", "MiniMax-M2.7"))
        self.assertEqual(
            eval_run.MINIMAX_ANTHROPIC_BASE_URLS,
            {
                "global_en": "https://api.minimax.io/anthropic",
                "cn_zh": "https://api.minimaxi.com/anthropic",
            },
        )
        self.assertEqual(config.auth_header, "Authorization")
        self.assertEqual(config.auth_prefix, "Bearer ")

    def test_minimax_defaults_and_validation(self) -> None:
        config, endpoint, model = eval_run.resolve_provider("minimax", "global_en", None)

        self.assertEqual(config.api_key_env, "MINIMAX_API_KEY")
        self.assertEqual(endpoint, "https://api.minimax.io/anthropic/v1/messages")
        self.assertEqual(model, "MiniMax-M3")
        with self.assertRaisesRegex(ValueError, "not supported"):
            eval_run.resolve_provider("minimax", "global_en", "unsupported")
        with self.assertRaisesRegex(ValueError, "not supported"):
            eval_run.resolve_provider("anthropic", "cn_zh", None)

    def test_minimax_request_uses_selected_region_and_bearer_auth(self) -> None:
        config = eval_run.PROVIDER_CONFIGS["minimax"]
        for region, expected_endpoint in {
            "global_en": "https://api.minimax.io/anthropic/v1/messages",
            "cn_zh": "https://api.minimaxi.com/anthropic/v1/messages",
        }.items():
            with self.subTest(region=region):
                _, endpoint, model = eval_run.resolve_provider("minimax", region, None)
                with mock.patch.object(
                    eval_run.urllib.request,
                    "urlopen",
                    return_value=FakeResponse(),
                ) as urlopen:
                    text = eval_run.call_api(
                        "system",
                        "user",
                        model,
                        "test-key",
                        config,
                        endpoint,
                    )

                request = urlopen.call_args.args[0]
                self.assertEqual(text, "ok")
                self.assertEqual(request.full_url, expected_endpoint)
                self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
                self.assertIsNone(request.get_header("X-api-key"))
                self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
                self.assertEqual(json.loads(request.data)["model"], "MiniMax-M3")

    def test_default_provider_preserves_existing_request_auth(self) -> None:
        config, endpoint, model = eval_run.resolve_provider("anthropic", "global_en", None)
        with mock.patch.object(
            eval_run.urllib.request,
            "urlopen",
            return_value=FakeResponse(),
        ) as urlopen:
            eval_run.call_api("system", "user", model, "test-key", config, endpoint)

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.get_header("X-api-key"), "test-key")
        self.assertIsNone(request.get_header("Authorization"))

    def test_live_mode_requires_the_selected_provider_key(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["eval_run.py", "--provider", "minimax"]),
            mock.patch.dict(os.environ, {}, clear=True),
            redirect_stdout(output),
        ):
            result = eval_run.main()

        self.assertEqual(result, 2)
        self.assertIn("MINIMAX_API_KEY not set", output.getvalue())

    def test_ledger_preserves_provider_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            eval_run.write_ledger(
                path,
                [],
                "MiniMax-M2.7",
                "2026-07-31",
                "minimax",
                "cn_zh",
            )

            ledger = path.read_text(encoding="utf-8")

        self.assertIn("provider `minimax`", ledger)
        self.assertIn("--provider minimax --region cn_zh --model MiniMax-M2.7", ledger)


if __name__ == "__main__":
    unittest.main()

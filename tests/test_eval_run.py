from __future__ import annotations

import json
import io
import os
import re
import shlex
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import eval_run  # noqa: E402


def completion_payload(provider_name: str, model: str) -> dict:
    payload = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": "ok"}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }
    if provider_name == "anthropic":
        payload["stop_sequence"] = None
    return payload


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, amount: int = -1) -> bytes:
        body = json.dumps(self.payload).encode("utf-8")
        return body if amount < 0 else body[:amount]


class EvalRunProviderTests(unittest.TestCase):
    def test_minimax_configuration_matches_current_models_and_regions(self) -> None:
        config = eval_run.PROVIDER_CONFIGS["minimax"]

        self.assertEqual(config.default_model, "MiniMax-M3")
        self.assertEqual(
            config.models,
            (
                "MiniMax-M3",
                "MiniMax-M2.7",
                "MiniMax-M2.7-highspeed",
                "MiniMax-M2.5",
                "MiniMax-M2.5-highspeed",
                "MiniMax-M2.1",
                "MiniMax-M2.1-highspeed",
                "MiniMax-M2",
            ),
        )
        self.assertEqual(
            eval_run.MINIMAX_ANTHROPIC_BASE_URLS,
            {
                "global_en": "https://api.minimax.io/anthropic",
                "cn_zh": "https://api.minimaxi.com/anthropic",
            },
        )
        self.assertEqual(config.auth_header, "Authorization")
        self.assertEqual(config.auth_prefix, "Bearer ")
        self.assertEqual(config.response_schema, "minimax")

    def test_minimax_defaults_and_validation(self) -> None:
        config, endpoint, model = eval_run.resolve_provider("minimax", "global_en", None)

        self.assertEqual(config.api_key_env, "MINIMAX_API_KEY")
        self.assertEqual(endpoint, "https://api.minimax.io/anthropic/v1/messages")
        self.assertEqual(model, "MiniMax-M3")
        with self.assertRaisesRegex(ValueError, "not supported"):
            eval_run.resolve_provider("minimax", "global_en", "unsupported")
        for supported in eval_run.MINIMAX_MODELS:
            self.assertEqual(
                eval_run.resolve_provider("minimax", "global_en", supported)[2],
                supported,
            )
        with self.assertRaisesRegex(ValueError, "not supported"):
            eval_run.resolve_provider("anthropic", "cn_zh", None)

    def test_minimax_request_uses_selected_region_and_api_key_auth(self) -> None:
        config = eval_run.PROVIDER_CONFIGS["minimax"]
        for region, expected_endpoint in {
            "global_en": "https://api.minimax.io/anthropic/v1/messages",
            "cn_zh": "https://api.minimaxi.com/anthropic/v1/messages",
        }.items():
            with self.subTest(region=region):
                _, endpoint, model = eval_run.resolve_provider("minimax", region, None)
                payload = completion_payload("minimax", model)
                with mock.patch.object(
                    eval_run.urllib.request,
                    "urlopen",
                    return_value=FakeResponse(payload),
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
                self.assertIs(json.loads(request.data)["stream"], False)

    def test_default_provider_preserves_existing_request_auth(self) -> None:
        config, endpoint, model = eval_run.resolve_provider("anthropic", "global_en", None)
        with mock.patch.object(
            eval_run.urllib.request,
            "urlopen",
            return_value=FakeResponse(
                completion_payload("anthropic", model)
            ),
        ) as urlopen:
            eval_run.call_api("system", "user", model, "test-key", config, endpoint)

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.get_header("X-api-key"), "test-key")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertIs(json.loads(request.data)["stream"], False)

    def test_provider_specific_completion_contracts(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        for invalid_stop_sequence in (object(), 7, "DONE"):
            with self.subTest(stop_sequence=invalid_stop_sequence):
                payload = completion_payload("anthropic", model)
                if invalid_stop_sequence.__class__ is object:
                    payload.pop("stop_sequence")
                else:
                    payload["stop_sequence"] = invalid_stop_sequence
                with (
                    mock.patch.object(
                        eval_run.urllib.request,
                        "urlopen",
                        return_value=FakeResponse(payload),
                    ),
                    self.assertRaises(eval_run.ProviderResponseError),
                ):
                    eval_run.call_api(
                        "system", "user", model, "key", provider, endpoint
                    )

        for region in ("global_en", "cn_zh"):
            with self.subTest(provider="minimax", region=region):
                provider, endpoint, model = eval_run.resolve_provider(
                    "minimax", region, None
                )
                payload = completion_payload("minimax", model)
                self.assertNotIn("base_resp", payload)
                self.assertNotIn("stop_sequence", payload)
                with mock.patch.object(
                    eval_run.urllib.request,
                    "urlopen",
                    return_value=FakeResponse(payload),
                ):
                    self.assertEqual(
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        ),
                        "ok",
                    )

                for base_resp in (
                    {"status_code": 0, "status_msg": "success"},
                    {"status_code": 0, "status_msg": ""},
                ):
                    payload = completion_payload("minimax", model)
                    payload["base_resp"] = base_resp
                    payload["stop_sequence"] = None
                    with mock.patch.object(
                        eval_run.urllib.request,
                        "urlopen",
                        return_value=FakeResponse(payload),
                    ):
                        self.assertEqual(
                            eval_run.call_api(
                                "system", "user", model, "key", provider, endpoint
                            ),
                            "ok",
                        )

                payload = completion_payload("minimax", model)
                payload["usage"].update(
                    {
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 1,
                    }
                )
                with mock.patch.object(
                    eval_run.urllib.request,
                    "urlopen",
                    return_value=FakeResponse(payload),
                ):
                    self.assertEqual(
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        ),
                        "ok",
                    )

                invalid_legacy_fields = (
                    ("base_resp", {"status_code": 1, "status_msg": "denied"}),
                    (
                        "base_resp",
                        {"status_code": 0, "status_msg": "success", "extra": True},
                    ),
                    ("base_resp", {"status_code": "0", "status_msg": "success"}),
                    ("stop_sequence", "DONE"),
                )
                for field, value in invalid_legacy_fields:
                    payload = completion_payload("minimax", model)
                    payload[field] = value
                    with (
                        mock.patch.object(
                            eval_run.urllib.request,
                            "urlopen",
                            return_value=FakeResponse(payload),
                        ),
                        self.assertRaises(eval_run.ProviderResponseError),
                    ):
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        )

                for usage_update in (
                    {"cache_creation_input_tokens": None},
                    {"output_tokens_details": {"thinking_tokens": 0}},
                ):
                    payload = completion_payload("minimax", model)
                    payload["usage"].update(usage_update)
                    with (
                        mock.patch.object(
                            eval_run.urllib.request,
                            "urlopen",
                            return_value=FakeResponse(payload),
                        ),
                        self.assertRaises(eval_run.ProviderResponseError),
                    ):
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        )

        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        payload = completion_payload("anthropic", model)
        payload["base_resp"] = {"status_code": 0, "status_msg": "success"}
        with (
            mock.patch.object(
                eval_run.urllib.request,
                "urlopen",
                return_value=FakeResponse(payload),
            ),
            self.assertRaises(eval_run.ProviderResponseError),
        ):
            eval_run.call_api("system", "user", model, "key", provider, endpoint)

    def test_provider_response_model_must_match_request_exactly(self) -> None:
        for provider_name, region in (
            ("anthropic", "global_en"),
            ("minimax", "global_en"),
            ("minimax", "cn_zh"),
        ):
            with self.subTest(provider=provider_name, region=region):
                provider, endpoint, model = eval_run.resolve_provider(
                    provider_name, region, None
                )
                payload = completion_payload(provider_name, model)
                payload["model"] = model + "-unexpected"
                with (
                    mock.patch.object(
                        eval_run.urllib.request,
                        "urlopen",
                        return_value=FakeResponse(payload),
                    ),
                    self.assertRaisesRegex(
                        eval_run.ProviderResponseError,
                        "does not match the requested model",
                    ),
                ):
                    eval_run.call_api(
                        "system", "user", model, "key", provider, endpoint
                    )

    def test_common_completion_envelope_is_required_for_every_provider(self) -> None:
        for provider_name, region in (
            ("anthropic", "global_en"),
            ("minimax", "global_en"),
            ("minimax", "cn_zh"),
        ):
            provider, endpoint, model = eval_run.resolve_provider(
                provider_name, region, None
            )
            for missing_field in eval_run.REQUIRED_COMPLETION_FIELDS:
                with self.subTest(
                    provider=provider_name,
                    region=region,
                    missing=missing_field,
                ):
                    payload = completion_payload(provider_name, model)
                    payload.pop(missing_field)
                    with (
                        mock.patch.object(
                            eval_run.urllib.request,
                            "urlopen",
                            return_value=FakeResponse(payload),
                        ),
                        self.assertRaises(eval_run.ProviderResponseError),
                    ):
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        )

            invalid_fields = (
                ("id", ""),
                ("type", "response"),
                ("role", "user"),
                ("usage", {"input_tokens": True, "output_tokens": 1}),
                ("usage", {"input_tokens": 1, "output_tokens": -1}),
            )
            for field, value in invalid_fields:
                with self.subTest(
                    provider=provider_name,
                    region=region,
                    field=field,
                    value=value,
                ):
                    payload = completion_payload(provider_name, model)
                    payload[field] = value
                    with (
                        mock.patch.object(
                            eval_run.urllib.request,
                            "urlopen",
                            return_value=FakeResponse(payload),
                        ),
                        self.assertRaises(eval_run.ProviderResponseError),
                    ):
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        )

    def test_documented_optional_usage_and_envelope_fields_are_strict(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        payload = completion_payload("anthropic", model)
        payload["container"] = {
            "id": "container_1",
            "expires_at": "2026-08-01T00:00:00Z",
        }
        payload["stop_details"] = None
        payload["usage"].update(
            {
                "cache_creation_input_tokens": None,
                "cache_read_input_tokens": 2,
                "service_tier": "standard",
                "inference_geo": None,
                "cache_creation": {
                    "ephemeral_5m_input_tokens": 1,
                    "ephemeral_1h_input_tokens": 0,
                },
                "server_tool_use": {
                    "web_search_requests": 1,
                    "web_fetch_requests": 0,
                },
                "output_tokens_details": {"thinking_tokens": 0},
            }
        )
        with mock.patch.object(
            eval_run.urllib.request,
            "urlopen",
            return_value=FakeResponse(payload),
        ):
            self.assertEqual(
                eval_run.call_api(
                    "system", "user", model, "key", provider, endpoint
                ),
                "ok",
            )

        mutations = (
            ("usage extra", lambda body: body["usage"].update({"future": 1})),
            (
                "nested cache extra",
                lambda body: body["usage"].update(
                    {
                        "cache_creation": {
                            "ephemeral_5m_input_tokens": 0,
                            "ephemeral_1h_input_tokens": 0,
                            "future": 0,
                        }
                    }
                ),
            ),
            (
                "nested token detail extra",
                lambda body: body["usage"].update(
                    {"output_tokens_details": {"thinking_tokens": 0, "future": 0}}
                ),
            ),
            (
                "token detail exceeds total",
                lambda body: body["usage"].update(
                    {"output_tokens_details": {"thinking_tokens": 2}}
                ),
            ),
            (
                "incomplete server tool usage",
                lambda body: body["usage"].update(
                    {"server_tool_use": {"web_search_requests": 0}}
                ),
            ),
            (
                "unknown service tier",
                lambda body: body["usage"].update({"service_tier": "future"}),
            ),
            ("container extra", lambda body: body.update({"container": {"id": "x", "expires_at": "y", "future": 1}})),
            (
                "unknown refusal category",
                lambda body: body.update(
                    {
                        "stop_details": {
                            "type": "refusal",
                            "category": "future",
                            "explanation": None,
                        }
                    }
                ),
            ),
            (
                "invalid container timestamp",
                lambda body: body.update(
                    {"container": {"id": "container_1", "expires_at": "tomorrow"}}
                ),
            ),
            ("envelope extra", lambda body: body.update({"future": True})),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                invalid = completion_payload("anthropic", model)
                mutate(invalid)
                with (
                    mock.patch.object(
                        eval_run.urllib.request,
                        "urlopen",
                        return_value=FakeResponse(invalid),
                    ),
                    self.assertRaises(eval_run.ProviderResponseError),
                ):
                    eval_run.call_api(
                        "system", "user", model, "key", provider, endpoint
                    )

    def test_missing_null_and_truncating_stop_reasons_are_rejected(self) -> None:
        mutations = (
            ("missing", object()),
            ("null", None),
            ("max tokens", "max_tokens"),
            ("context window", "model_context_window_exceeded"),
            ("stop sequence", "stop_sequence"),
            ("wrong case", "END_TURN"),
            ("padded", " end_turn "),
        )
        for provider_name, region in (
            ("anthropic", "global_en"),
            ("minimax", "global_en"),
            ("minimax", "cn_zh"),
        ):
            provider, endpoint, model = eval_run.resolve_provider(
                provider_name, region, None
            )
            for label, value in mutations:
                with self.subTest(
                    provider=provider_name,
                    region=region,
                    mutation=label,
                ):
                    payload = completion_payload(provider_name, model)
                    if label == "missing":
                        payload.pop("stop_reason")
                    else:
                        payload["stop_reason"] = value
                    if provider_name == "anthropic" and label == "stop sequence":
                        payload["stop_sequence"] = "DONE"
                    with (
                        mock.patch.object(
                            eval_run.urllib.request,
                            "urlopen",
                            return_value=FakeResponse(payload),
                        ),
                        self.assertRaises(eval_run.ProviderResponseError),
                    ):
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        )

    def test_content_blocks_are_provider_and_model_strict(self) -> None:
        cases = (
            ("anthropic", "global_en", None),
            ("minimax", "global_en", "MiniMax-M3"),
            ("minimax", "cn_zh", "MiniMax-M2.7"),
        )
        for provider_name, region, requested_model in cases:
            provider, endpoint, model = eval_run.resolve_provider(
                provider_name, region, requested_model
            )
            for block in (
                {"type": "future_block", "value": "ignored"},
                {"type": "tool_use", "id": "tool_1", "name": "x", "input": {}},
                {"type": "text", "text": 7},
            ):
                with self.subTest(provider=provider_name, model=model, block=block):
                    payload = completion_payload(provider_name, model)
                    payload["content"] = [block, {"type": "text", "text": "ok"}]
                    with (
                        mock.patch.object(
                            eval_run.urllib.request,
                            "urlopen",
                            return_value=FakeResponse(payload),
                        ),
                        self.assertRaises(eval_run.ProviderResponseError),
                    ):
                        eval_run.call_api(
                            "system", "user", model, "key", provider, endpoint
                        )

        provider, endpoint, model = eval_run.resolve_provider(
            "minimax", "global_en", "MiniMax-M3"
        )
        payload = completion_payload("minimax", model)
        payload["content"] = [
            {"type": "thinking", "thinking": "hidden", "signature": "sig"},
            {"type": "text", "text": "ok"},
        ]
        with (
            mock.patch.object(
                eval_run.urllib.request,
                "urlopen",
                return_value=FakeResponse(payload),
            ),
            self.assertRaisesRegex(eval_run.ProviderResponseError, "was not requested"),
        ):
            eval_run.call_api("system", "user", model, "key", provider, endpoint)

        provider, endpoint, model = eval_run.resolve_provider(
            "minimax", "global_en", "MiniMax-M2.7"
        )
        payload = completion_payload("minimax", model)
        payload["content"] = [
            {"type": "thinking", "thinking": "reasoning", "signature": "sig"},
            {"type": "text", "text": "ok"},
        ]
        with mock.patch.object(
            eval_run.urllib.request,
            "urlopen",
            return_value=FakeResponse(payload),
        ):
            self.assertEqual(
                eval_run.call_api(
                    "system", "user", model, "key", provider, endpoint
                ),
                "ok",
            )

        for malformed in (
            {"type": "thinking", "thinking": "reasoning"},
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "thinking", "thinking": "reasoning", "signature": 7},
        ):
            with self.subTest(malformed_thinking=malformed):
                payload = completion_payload("minimax", model)
                payload["content"] = [malformed, {"type": "text", "text": "ok"}]
                with (
                    mock.patch.object(
                        eval_run.urllib.request,
                        "urlopen",
                        return_value=FakeResponse(payload),
                    ),
                    self.assertRaisesRegex(eval_run.ProviderResponseError, "malformed"),
                ):
                    eval_run.call_api(
                        "system", "user", model, "key", provider, endpoint
                    )

    def test_known_anthropic_content_blocks_validate_before_rejection(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        payload = completion_payload("anthropic", model)
        payload["content"] = [
            {
                "type": "text",
                "text": "grounded",
                "citations": [
                    {
                        "type": "char_location",
                        "cited_text": "source text",
                        "document_index": 0,
                        "start_char_index": 0,
                        "end_char_index": 11,
                    },
                    {
                        "type": "page_location",
                        "cited_text": "source text",
                        "document_index": 1,
                        "start_page_number": 1,
                        "end_page_number": 2,
                    },
                    {
                        "type": "content_block_location",
                        "cited_text": "source text",
                        "document_index": 2,
                        "document_title": "Custom source",
                        "start_block_index": 0,
                        "end_block_index": 1,
                    },
                    {
                        "type": "web_search_result_location",
                        "cited_text": "source text",
                        "encrypted_index": "opaque-index",
                        "url": "https://example.com/source",
                    },
                    {
                        "type": "search_result_location",
                        "cited_text": "source text",
                        "source": "kb://source-1",
                        "title": None,
                        "search_result_index": 0,
                        "start_block_index": 0,
                        "end_block_index": 1,
                    },
                ],
            }
        ]
        with mock.patch.object(
            eval_run.urllib.request,
            "urlopen",
            return_value=FakeResponse(payload),
        ):
            self.assertEqual(
                eval_run.call_api(
                    "system", "user", model, "key", provider, endpoint
                ),
                "grounded",
            )

        invalid_blocks = (
            {"type": "text", "text": "ok", "future": True},
            {
                "type": "thinking",
                "thinking": "reasoning",
                "signature": "sig",
                "future": True,
            },
            {
                "type": "text",
                "text": "ok",
                "citations": [
                    {
                        "type": "char_location",
                        "cited_text": "x",
                        "document_index": 0,
                        "document_title": None,
                        "start_char_index": 2,
                        "end_char_index": 1,
                    }
                ],
            },
            {
                "type": "text",
                "text": "ok",
                "citations": [
                    {
                        "type": "char_location",
                        "cited_text": "x",
                        "document_index": 0,
                        "document_title": None,
                        "start_char_index": 0,
                        "end_char_index": 1,
                        "future": True,
                    }
                ],
            },
            {"type": "text", "text": "ok", "citations": [{"type": []}]},
            {
                "type": "tool_use",
                "id": "tool_1",
                "name": "lookup",
                "input": {},
                "caller": {"type": "direct", "future": True},
            },
            {
                "type": "tool_use",
                "id": "tool_1",
                "name": "lookup",
                "input": {},
                "caller": {"type": {}},
            },
            {
                "type": "server_tool_use",
                "id": "srvtoolu_1",
                "name": "web_search",
                "input": {"query": "x"},
                "caller": {"type": "direct"},
                "future": True,
            },
            {"type": "redacted_thinking", "data": "opaque", "future": True},
        )
        for block in invalid_blocks:
            with self.subTest(block=block):
                invalid = completion_payload("anthropic", model)
                invalid["content"] = [block, {"type": "text", "text": "ok"}]
                with (
                    mock.patch.object(
                        eval_run.urllib.request,
                        "urlopen",
                        return_value=FakeResponse(invalid),
                    ),
                    self.assertRaises(eval_run.ProviderResponseError),
                ):
                    eval_run.call_api(
                        "system", "user", model, "key", provider, endpoint
                    )

        invalid = completion_payload("anthropic", model)
        invalid["content"] = [
            {
                "type": "server_tool_use",
                "id": "srvtoolu_future",
                "name": "future_server_tool",
                "input": {},
            },
            {"type": "text", "text": "ok"},
        ]
        with (
            mock.patch.object(
                eval_run.urllib.request,
                "urlopen",
                return_value=FakeResponse(invalid),
            ),
            self.assertRaisesRegex(
                eval_run.ProviderResponseError,
                "unsupported name",
            ),
        ):
            eval_run.call_api(
                "system", "user", model, "key", provider, endpoint
            )

        well_formed_but_unrequested = (
            {
                "type": "tool_use",
                "id": "tool_1",
                "name": "lookup",
                "input": {},
                "caller": {"type": "code_execution_20260120", "tool_id": "srv_1"},
            },
            {
                "type": "server_tool_use",
                "id": "srvtoolu_1",
                "name": "web_search",
                "input": {"query": "x"},
            },
            {
                "type": "server_tool_use",
                "id": "srvtoolu_2",
                "name": "web_fetch",
                "input": {"url": "https://example.com"},
                "caller": {"type": "direct"},
            },
            {"type": "thinking", "thinking": "reasoning", "signature": "sig"},
            {"type": "redacted_thinking", "data": "opaque"},
        )
        for block in well_formed_but_unrequested:
            with self.subTest(block=block):
                invalid = completion_payload("anthropic", model)
                invalid["content"] = [block, {"type": "text", "text": "ok"}]
                with (
                    mock.patch.object(
                        eval_run.urllib.request,
                        "urlopen",
                        return_value=FakeResponse(invalid),
                    ),
                    self.assertRaisesRegex(
                        eval_run.ProviderResponseError,
                        "was not requested",
                    ),
                ):
                    eval_run.call_api(
                        "system", "user", model, "key", provider, endpoint
                    )

    def test_transport_phases_preserve_cause_and_redact_every_secret(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "minimax", "global_en", None
        )
        api_key = "actual-S3CRET$key"
        reason = (
            f"same root cause {api_key}; Authorization: Bearer header-secret "
            "X-Api-Key: other-secret "
            "{'X-Api-Key': 'mapping-secret'}\r\nnext\x1b[31m"
        )
        messages: dict[str, str] = {}
        for phase in ("open", "enter", "read"):
            with self.subTest(phase=phase):
                failure = ConnectionResetError(reason)
                manager = mock.MagicMock()
                if phase == "enter":
                    manager.__enter__.side_effect = failure
                    side_effect = None
                elif phase == "read":
                    manager.__enter__.return_value.read.side_effect = failure
                    side_effect = None
                else:
                    side_effect = failure
                with (
                    mock.patch.object(
                        eval_run.urllib.request,
                        "urlopen",
                        return_value=manager if side_effect is None else mock.DEFAULT,
                        side_effect=side_effect,
                    ),
                    self.assertRaises(eval_run.ProviderResponseError) as raised,
                ):
                    eval_run.call_api(
                        "system", "user", model, api_key, provider, endpoint
                    )
                message = str(raised.exception)
                messages[phase] = message
                self.assertTrue(
                    message.startswith(
                        f"model API transport {phase} failed "
                        "(ConnectionResetError): same root cause "
                    )
                )
                for secret in (
                    api_key,
                    "header-secret",
                    "other-secret",
                    "mapping-secret",
                ):
                    self.assertNotIn(secret, message)
                self.assertIn("[REDACTED]", message)
                self.assertIn("next [31m", message)
                self.assertNotIn("\r", message)
                self.assertNotIn("\n", message)
                self.assertNotIn("\x1b", message)

        suffixes = {
            message.split("failed (ConnectionResetError): ", 1)[1]
            for message in messages.values()
        }
        self.assertEqual(len(suffixes), 1)

    def test_secret_redaction_is_stable_and_exception_stringification_fails_closed(self) -> None:
        detail = eval_run._safe_exception_detail(
            Exception(
                "Authorization: Bearer header-secret "
                "X-Api-Key: secondary-secret exact-secret"
            ),
            "exact-secret",
        )
        self.assertEqual(
            detail,
            "Authorization: Bearer [REDACTED] X-Api-Key: [REDACTED] [REDACTED]",
        )

        class BrokenStringError(Exception):
            def __str__(self) -> str:
                raise RuntimeError("stringification failed")

        self.assertEqual(
            eval_run._safe_exception_detail(BrokenStringError(), "secret"),
            "BrokenStringError",
        )
        surrogate_detail = eval_run._safe_exception_detail(
            Exception("bad surrogate \ud800 exact-secret"), "exact-secret"
        )
        self.assertEqual(surrogate_detail, "bad surrogate \\ud800 [REDACTED]")
        surrogate_detail.encode("utf-8")

        control_key = "sk-header-secret\r\nleak"
        escaped_key = control_key.encode("unicode_escape").decode("ascii")
        escaped_detail = eval_run._safe_exception_detail(
            ValueError(f"Invalid header value {control_key!r}"),
            control_key,
        )
        self.assertNotIn(control_key, escaped_detail)
        self.assertNotIn(escaped_key, escaped_detail)
        self.assertIn("[REDACTED]", escaped_detail)

    def test_control_bearing_api_keys_are_rejected_before_urllib(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "anthropic", "global_en", None
        )
        for separator in ("\r", "\n", "\r\n"):
            with self.subTest(separator=repr(separator)):
                api_key = f"sk-header-secret{separator}leak"
                escaped_key = api_key.encode("unicode_escape").decode("ascii")
                with (
                    mock.patch.object(eval_run.urllib.request, "urlopen") as urlopen,
                    self.assertRaises(eval_run.ProviderResponseError) as raised,
                ):
                    eval_run.call_api(
                        "system", "user", model, api_key, provider, endpoint
                    )

                message = str(raised.exception)
                urlopen.assert_not_called()
                self.assertNotIn(api_key, message)
                self.assertNotIn(escaped_key, message)
                self.assertEqual(
                    message,
                    "model API credential is not a valid HTTP header value",
                )

    def test_transport_rejects_non_byte_success_bodies_after_closing(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "minimax", "global_en", None
        )
        manager = mock.MagicMock()
        manager.__enter__.return_value.read.return_value = "not bytes"
        with (
            mock.patch.object(
                eval_run.urllib.request, "urlopen", return_value=manager
            ),
            self.assertRaisesRegex(
                eval_run.ProviderResponseError, "body must be bytes"
            ),
        ):
            eval_run.call_api(
                "system", "user", model, "test-key", provider, endpoint
            )
        manager.__exit__.assert_called_once_with(None, None, None)

    def test_http_url_and_schema_errors_never_expose_credentials(self) -> None:
        provider, endpoint, model = eval_run.resolve_provider(
            "minimax", "global_en", None
        )
        api_key = "actual-provider-secret"
        failures = (
            eval_run.urllib.error.HTTPError(
                endpoint,
                401,
                f"provider denied {{'X-Api-Key': 'http-secondary'}} {api_key}",
                {},
                None,
            ),
            eval_run.urllib.error.URLError(
                f'{{"X-Api-Key": "url-secondary"}} {api_key} connection refused'
            ),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with (
                    mock.patch.object(
                        eval_run.urllib.request,
                        "urlopen",
                        side_effect=failure,
                    ),
                    self.assertRaises(eval_run.ProviderResponseError) as raised,
                ):
                    eval_run.call_api(
                        "system", "user", model, api_key, provider, endpoint
                    )
                message = str(raised.exception)
                self.assertNotIn(api_key, message)
                self.assertNotIn("http-secondary", message)
                self.assertNotIn("url-secondary", message)
                self.assertIn("[REDACTED]", message)
                self.assertTrue("401" in message or "connection refused" in message)

        payload = completion_payload("minimax", model)
        payload["model"] = api_key
        with (
            mock.patch.object(
                eval_run.urllib.request,
                "urlopen",
                return_value=FakeResponse(payload),
            ),
            self.assertRaises(eval_run.ProviderResponseError) as raised,
        ):
            eval_run.call_api(
                "system", "user", model, api_key, provider, endpoint
            )
        self.assertNotIn(api_key, str(raised.exception))
        self.assertIn("[REDACTED]", str(raised.exception))

        payload = completion_payload("minimax", model)
        payload["base_resp"] = {
            "status_code": 1,
            "status_msg": "{'X-Api-Key': 'schema-secondary'} denied",
        }
        with (
            mock.patch.object(
                eval_run.urllib.request,
                "urlopen",
                return_value=FakeResponse(payload),
            ),
            self.assertRaises(eval_run.ProviderResponseError) as raised,
        ):
            eval_run.call_api(
                "system", "user", model, api_key, provider, endpoint
            )
        self.assertNotIn("schema-secondary", str(raised.exception))
        self.assertIn("[REDACTED]", str(raised.exception))

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
                judge_model="MiniMax-M2.5",
            )

            ledger = path.read_text(encoding="utf-8")

        self.assertIn("provider `minimax`", ledger)
        self.assertIn("--provider minimax --region cn_zh --model MiniMax-M2.7", ledger)
        self.assertIn("responder model `MiniMax-M2.7`", ledger)
        self.assertIn("judge model `MiniMax-M2.5`", ledger)
        self.assertIn("--judge-model MiniMax-M2.5", ledger)
        expected_argv = [
            "python",
            "scripts/eval_run.py",
            "--provider",
            "minimax",
            "--region",
            "cn_zh",
            "--model",
            "MiniMax-M2.7",
            "--judge-model",
            "MiniMax-M2.5",
            "--ledger",
            "evals/eval-run-ledger.md",
        ]
        posix_match = re.search(r"```sh\n([^\n]+)\n```", ledger)
        powershell_match = re.search(r"```powershell\n([^\n]+)\n```", ledger)
        self.assertIsNotNone(posix_match)
        self.assertIsNotNone(powershell_match)
        self.assertEqual(shlex.split(posix_match.group(1)), expected_argv)
        powershell = powershell_match.group(1)
        encoded = " ".join(eval_run._powershell_quote(value) for value in expected_argv)
        self.assertEqual(powershell, "& " + encoded)
        self.assertEqual(
            [value.replace("''", "'") for value in re.findall(r"'((?:[^']|'')*)'", powershell)],
            expected_argv,
        )

    def test_ledger_code_values_cannot_break_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            eval_run.write_ledger(
                path,
                [],
                "model```\r\n--evil",
                "2026-08-01`",
                "mini`max",
                "global`en",
                judge_model="judge`$(bad)",
            )
            ledger = path.read_text(encoding="utf-8")

        self.assertNotIn("```", ledger)
        self.assertNotIn("\r", ledger)
        self.assertNotIn("\n--evil", ledger)
        self.assertNotIn("`$(bad)", ledger)
        self.assertIn("model''' --evil", ledger)
        self.assertIn("Regeneration commands omitted", ledger)
        self.assertNotIn("Regenerate from a POSIX shell", ledger)
        self.assertNotIn("Regenerate from PowerShell", ledger)

    def test_ledger_prose_metadata_cannot_create_active_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            eval_run.write_ledger(
                path,
                [],
                "model",
                "[FORGED](https://evil.example) **PASS** <img src=x>",
                "anthropic",
                "global_en",
            )
            ledger = path.read_text(encoding="utf-8")

        self.assertNotIn("[FORGED](https://evil.example)", ledger)
        self.assertNotIn("**PASS**", ledger)
        self.assertNotIn("<img src=x>", ledger)
        self.assertIn(r"\[FORGED\]\(https://evil.example\)", ledger)
        self.assertIn(r"\*\*PASS\*\*", ledger)
        self.assertIn("&lt;img src=x&gt;", ledger)


if __name__ == "__main__":
    unittest.main()

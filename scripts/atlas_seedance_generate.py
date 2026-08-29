#!/usr/bin/env python3
"""Submit and optionally poll a Seedance 2.0 job through Atlas Cloud."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


API_BASE = "https://api.atlascloud.ai"
DEFAULT_MODEL = "bytedance/seedance-2.0/text-to-video"
TERMINAL_SUCCESS = {"completed", "succeeded", "success"}
TERMINAL_FAILURE = {"failed", "canceled", "cancelled", "timeout"}


class AtlasAPIError(RuntimeError):
    """Atlas Cloud rejected a request or returned an invalid response."""


def _curl_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\r", "\\r").replace("\n", "\\n")
    return f'"{escaped}"'


def _request_json(
    method: str,
    path: str,
    *,
    api_key: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 60.0,
    api_base: str = API_BASE,
) -> dict[str, Any]:
    curl = shutil.which("curl")
    if curl is None:
        raise AtlasAPIError("curl is required for Atlas Cloud requests")

    url = f"{api_base.rstrip('/')}{path}"
    config = [
        "silent",
        "show-error",
        "fail-with-body",
        f"max-time = {_curl_value(str(timeout))}",
        f"request = {_curl_value(method)}",
        f"url = {_curl_value(url)}",
        f"header = {_curl_value(f'Authorization: Bearer {api_key}')}",
        f"header = {_curl_value('Accept: application/json')}",
        f"header = {_curl_value('Content-Type: application/json')}",
    ]
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        config.append(f"data-binary = {_curl_value(body)}")

    try:
        completed = subprocess.run(
            [curl, "--config", "-"],
            input="\n".join(config) + "\n",
            text=True,
            capture_output=True,
            timeout=timeout + 5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AtlasAPIError(f"Atlas Cloud request failed: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stdout or completed.stderr).strip()[:2048]
        raise AtlasAPIError(f"Atlas Cloud request failed: {detail}")

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AtlasAPIError("Atlas Cloud returned invalid JSON") from exc

    if not isinstance(result, dict):
        raise AtlasAPIError("Atlas Cloud returned a non-object JSON response")
    return result


def _prediction(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data", response)
    if not isinstance(data, dict):
        raise AtlasAPIError("Atlas Cloud response is missing a prediction object")
    return data


def submit_prediction(
    payload: dict[str, Any],
    *,
    api_key: str,
    timeout: float = 60.0,
    api_base: str = API_BASE,
) -> dict[str, Any]:
    """Submit exactly once. Callers must not automatically retry this POST."""

    response = _request_json(
        "POST",
        "/api/v1/model/generateVideo",
        api_key=api_key,
        payload=payload,
        timeout=timeout,
        api_base=api_base,
    )
    prediction = _prediction(response)
    if not (prediction.get("id") or prediction.get("request_id")):
        raise AtlasAPIError("Atlas Cloud submission response is missing a request id")
    return prediction


def get_prediction(
    request_id: str,
    *,
    api_key: str,
    timeout: float = 60.0,
    api_base: str = API_BASE,
) -> dict[str, Any]:
    response = _request_json(
        "GET",
        f"/api/v1/model/prediction/{request_id}",
        api_key=api_key,
        timeout=timeout,
        api_base=api_base,
    )
    return _prediction(response)


def wait_for_prediction(
    request_id: str,
    *,
    api_key: str,
    max_polls: int,
    poll_interval: float,
    timeout: float = 60.0,
    api_base: str = API_BASE,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    for attempt in range(max_polls):
        prediction = get_prediction(
            request_id,
            api_key=api_key,
            timeout=timeout,
            api_base=api_base,
        )
        status = str(prediction.get("status", "")).lower()
        if status in TERMINAL_SUCCESS:
            return prediction
        if status in TERMINAL_FAILURE:
            raise AtlasAPIError(f"Atlas Cloud prediction ended with status {status}")
        if attempt + 1 < max_polls:
            sleep(poll_interval)
    raise AtlasAPIError(f"prediction did not finish after {max_polls} status checks")


def _prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8").strip()
    return args.prompt.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Seedance 2.0 video through the optional Atlas Cloud surface."
    )
    prompt = parser.add_mutually_exclusive_group(required=True)
    prompt.add_argument("--prompt")
    prompt.add_argument("--prompt-file")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--duration", type=int, choices=[-1, *range(4, 16)], default=5)
    parser.add_argument(
        "--resolution",
        choices=["480p", "720p", "720p-SR", "1080p", "1080p-SR", "1440p-SR", "4k"],
        default="720p",
    )
    parser.add_argument(
        "--ratio",
        choices=["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"],
        default="adaptive",
    )
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--watermark", action="store_true")
    parser.add_argument("--return-last-frame", action="store_true")
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--max-polls", type=int, default=120)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--api-base", default=API_BASE)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prompt = _prompt(args)
    if not prompt:
        raise SystemExit("prompt must not be empty")
    if args.max_polls < 1 or args.poll_interval < 0 or args.timeout <= 0:
        raise SystemExit("polling and timeout values must be positive")
    if not -1 <= args.seed <= 4294967295:
        raise SystemExit("seed must be between -1 and 4294967295")

    payload = {
        "model": args.model,
        "prompt": prompt,
        "duration": args.duration,
        "resolution": args.resolution,
        "ratio": args.ratio,
        "generate_audio": not args.no_audio,
        "seed": args.seed,
        "watermark": args.watermark,
        "return_last_frame": args.return_last_frame,
    }
    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    api_key = os.environ.get("ATLASCLOUD_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("ATLASCLOUD_API_KEY is required unless --dry-run is used")

    try:
        prediction = submit_prediction(
            payload,
            api_key=api_key,
            timeout=args.timeout,
            api_base=args.api_base,
        )
        if args.wait:
            request_id = str(prediction.get("id") or prediction["request_id"])
            prediction = wait_for_prediction(
                request_id,
                api_key=api_key,
                max_polls=args.max_polls,
                poll_interval=args.poll_interval,
                timeout=args.timeout,
                api_base=args.api_base,
            )
    except AtlasAPIError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(prediction, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

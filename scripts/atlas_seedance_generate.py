#!/usr/bin/env python3
"""Plan, explicitly submit once, or poll an Atlas Cloud Seedance 2.0 task."""
from __future__ import annotations

import argparse
import http.client
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

if __package__:
    from .strict_json import MAX_JSON_BYTES, loads_json_bytes
else:
    from strict_json import MAX_JSON_BYTES, loads_json_bytes

API_HOST = "api.atlascloud.ai"
API_BASE = "https://" + API_HOST
DEFAULT_MODEL = "bytedance/seedance-2.0/text-to-video"
CREATE_PATH = "/api/v1/model/generateVideo"
POLL_PREFIX = "/api/v1/model/prediction/"
TERMINAL_SUCCESS = {"completed", "succeeded"}
TERMINAL_FAILURE = {"failed"}
STATUSES = TERMINAL_SUCCESS | TERMINAL_FAILURE | {"processing", "pending", "queued"}
MAX_PROMPT_BYTES = 64 * 1024


class AtlasAPIError(RuntimeError):
    """A request failed or its response could not be trusted."""


def _request_id(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) is None:
        raise AtlasAPIError("invalid prediction id")
    return value


def _bounded_number(value: float, minimum: float, maximum: float, name: str) -> None:
    if isinstance(value, bool) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise AtlasAPIError(f"{name} must be finite and between {minimum} and {maximum}")


def _request_json(method: str, path: str, *, api_key: str,
                  payload: dict[str, Any] | None = None, timeout: float = 60.0) -> dict[str, Any]:
    _bounded_number(timeout, 1, 120, "timeout")
    if method == "GET" and path.startswith(POLL_PREFIX):
        _request_id(path[len(POLL_PREFIX):])
        if payload is not None:
            raise AtlasAPIError("polling cannot contain a generation body")
    elif method != "POST" or path != CREATE_PATH or not isinstance(payload, dict):
        raise AtlasAPIError("unsupported Atlas Cloud request")
    if not api_key or any(ord(c) < 33 or ord(c) > 126 for c in api_key):
        raise AtlasAPIError("invalid ATLASCLOUD_API_KEY format")
    body = None if payload is None else json.dumps(payload, ensure_ascii=True, allow_nan=False).encode("ascii")
    # Fresh stdlib TLS connections do not consult curlrc, follow redirects,
    # use provider-selected hosts, or automatically retry generation requests.
    connection = http.client.HTTPSConnection(API_HOST, timeout=timeout)
    try:
        connection.request(method, path, body=body, headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json", "Accept": "application/json",
        })
        response = connection.getresponse()
        if response.status != 200:
            raise AtlasAPIError("Atlas Cloud returned a non-200 HTTP status; request was not retried")
        raw = bytearray()
        deadline = time.monotonic() + timeout
        while True:
            chunk = response.read1(min(65536, MAX_JSON_BYTES + 1 - len(raw)))
            raw.extend(chunk)
            if len(raw) > MAX_JSON_BYTES:
                raise AtlasAPIError("Atlas Cloud response exceeded the size limit")
            if time.monotonic() > deadline:
                raise AtlasAPIError("Atlas Cloud response exceeded the read deadline")
            if not chunk:
                break
        try:
            return loads_json_bytes(bytes(raw), expected_type=dict)
        except ValueError:
            raise AtlasAPIError("Atlas Cloud returned invalid JSON") from None
    except (OSError, http.client.HTTPException):
        # Do not echo prompts, credentials, bodies or remote error strings.
        raise AtlasAPIError("Atlas Cloud transport failed; request was not retried") from None
    finally:
        connection.close()


def _prediction(response: dict[str, Any], expected_id: str | None = None) -> dict[str, Any]:
    if "code" in response and (type(response["code"]) is not int or response["code"] != 200):
        raise AtlasAPIError("Atlas Cloud returned an unsuccessful envelope")
    data = response.get("data", response)
    if not isinstance(data, dict):
        raise AtlasAPIError("Atlas Cloud response is missing a prediction object")
    request_id = _request_id(data.get("id"))
    if expected_id is not None and request_id != expected_id:
        raise AtlasAPIError("Atlas Cloud returned a different prediction id")
    status = data.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        raise AtlasAPIError("Atlas Cloud returned an unknown prediction status")
    if "model" in data and data["model"] != DEFAULT_MODEL:
        raise AtlasAPIError("Atlas Cloud returned a different model")
    result = {"id": request_id, "status": status}
    if status in TERMINAL_SUCCESS:
        outputs = data.get("outputs")
        if not isinstance(outputs, list) or not 1 <= len(outputs) <= 16:
            raise AtlasAPIError("completed prediction is missing outputs")
        for value in outputs:
            if not isinstance(value, str) or len(value) > 8192 or any(ord(c) < 33 or ord(c) > 126 for c in value):
                raise AtlasAPIError("invalid output URL")
            try:
                url = urlsplit(value)
                valid = url.scheme == "https" and url.hostname and not url.username and not url.password
            except ValueError:
                valid = False
            if not valid:
                raise AtlasAPIError("output URL must use HTTPS without credentials")
        result["outputs"] = outputs
    # URLs are returned as data only: no fetch or forwarding authentication.
    return result


def submit_prediction(payload: dict[str, Any], *, api_key: str, timeout: float = 60.0) -> dict[str, Any]:
    """Submit exactly once; reconcile a lost response in provider history."""
    return _prediction(_request_json("POST", CREATE_PATH, api_key=api_key, payload=payload, timeout=timeout))


def get_prediction(request_id: str, *, api_key: str, timeout: float = 60.0) -> dict[str, Any]:
    request_id = _request_id(request_id)
    return _prediction(_request_json("GET", POLL_PREFIX + request_id, api_key=api_key, timeout=timeout), request_id)


def wait_for_prediction(request_id: str, *, api_key: str, max_polls: int, poll_interval: float,
                        timeout: float = 60.0, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    _request_id(request_id)
    if type(max_polls) is not int or not 1 <= max_polls <= 120:
        raise AtlasAPIError("max-polls must be between 1 and 120")
    _bounded_number(poll_interval, 0, 60, "poll-interval")
    _bounded_number(timeout, 1, 120, "timeout")
    for attempt in range(max_polls):
        prediction = get_prediction(request_id, api_key=api_key, timeout=timeout)
        if prediction["status"] in TERMINAL_SUCCESS:
            return prediction
        if prediction["status"] in TERMINAL_FAILURE:
            raise AtlasAPIError("Atlas Cloud prediction failed; inspect provider history")
        if attempt + 1 < max_polls:
            sleep(poll_interval)
    raise AtlasAPIError(f"prediction did not finish after {max_polls} status checks; no new job was created")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prompt")
    source.add_argument("--prompt-file")
    source.add_argument("--prediction-id", help="resume GET polling of an existing job; never submits")
    parser.add_argument("--model", choices=[DEFAULT_MODEL], default=DEFAULT_MODEL)
    parser.add_argument("--duration", type=int, choices=[-1, *range(4, 16)], default=5)
    parser.add_argument("--resolution", choices=["480p", "720p", "720p-SR", "1080p", "1080p-SR", "1440p-SR", "4k"], default="720p")
    parser.add_argument("--ratio", choices=["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"], default="adaptive")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--watermark", action="store_true")
    parser.add_argument("--return-last-frame", action="store_true")
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--max-polls", type=int, default=120)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=60.0)
    execution = parser.add_mutually_exclusive_group()
    execution.add_argument("--dry-run", action="store_true", help="offline plan (the default)")
    execution.add_argument("--live", action="store_true", help="authorize network access and, with a prompt, one paid submission")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    submitted = False
    try:
        _bounded_number(args.timeout, 1, 120, "timeout")
        _bounded_number(args.poll_interval, 0, 60, "poll-interval")
        if not 1 <= args.max_polls <= 120 or not -1 <= args.seed <= 4294967295:
            raise AtlasAPIError("max-polls or seed is outside its supported range")
        if args.prediction_id is not None:
            request_id = _request_id(args.prediction_id)
            plan = {"method": "GET", "url": API_BASE + POLL_PREFIX + request_id}
        else:
            if args.prompt_file:
                with Path(args.prompt_file).open("rb") as stream:
                    raw_prompt = stream.read(MAX_PROMPT_BYTES + 1)
            else:
                raw_prompt = args.prompt.encode("utf-8")
            if len(raw_prompt) > MAX_PROMPT_BYTES:
                raise AtlasAPIError("prompt exceeds the local 64 KiB input limit")
            prompt = raw_prompt.decode("utf-8").strip()
            if not prompt:
                raise AtlasAPIError("prompt must not be empty")
            payload = {"model": args.model, "prompt": prompt, "duration": args.duration,
                       "resolution": args.resolution, "ratio": args.ratio, "generate_audio": not args.no_audio,
                       "seed": args.seed, "watermark": args.watermark, "return_last_frame": args.return_last_frame}
            plan = {"method": "POST", "url": API_BASE + CREATE_PATH, "payload": payload}
        if not args.live:
            print(json.dumps(plan, indent=2, ensure_ascii=True))
            return 0
        api_key = os.environ.get("ATLASCLOUD_API_KEY", "")
        if args.prediction_id is not None:
            prediction = get_prediction(request_id, api_key=api_key, timeout=args.timeout)
        else:
            submitted = True  # A failure after the POST may be ambiguous.
            prediction = submit_prediction(payload, api_key=api_key, timeout=args.timeout)
        # Retain the validated ID even if a later GET fails.
        print(json.dumps(prediction, ensure_ascii=True), flush=True)
        if args.wait and prediction["status"] not in TERMINAL_SUCCESS | TERMINAL_FAILURE:
            prediction = wait_for_prediction(prediction["id"], api_key=api_key, max_polls=args.max_polls,
                                             poll_interval=args.poll_interval, timeout=args.timeout)
            print(json.dumps(prediction, ensure_ascii=True))
        if prediction["status"] in TERMINAL_FAILURE:
            raise AtlasAPIError("Atlas Cloud prediction failed; inspect provider history")
        return 0
    except (AtlasAPIError, OSError, UnicodeError, ValueError) as exc:
        message = str(exc) if isinstance(exc, AtlasAPIError) else "invalid local input or response"
        print(message, file=sys.stderr)
        if submitted:
            print("The submission may have been billed. Reconcile provider history before creating another job.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

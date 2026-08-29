from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest import mock

from scripts import atlas_seedance_generate as atlas


class AtlasSeedanceGenerateTests(unittest.TestCase):
    def test_submit_uses_one_post(self) -> None:
        with mock.patch.object(
            atlas,
            "_request_json",
            return_value={"data": {"id": "request-1", "status": "processing"}},
        ) as request:
            result = atlas.submit_prediction(
                {"model": atlas.DEFAULT_MODEL, "prompt": "test"}, api_key="secret"
            )

        self.assertEqual(result["id"], "request-1")
        request.assert_called_once()
        self.assertEqual(request.call_args.args, ("POST", "/api/v1/model/generateVideo"))

    def test_wait_only_polls_get_until_completed(self) -> None:
        responses = [
            {"data": {"id": "request-1", "status": "processing"}},
            {"data": {"id": "request-1", "status": "completed", "outputs": ["video.mp4"]}},
        ]
        with mock.patch.object(atlas, "_request_json", side_effect=responses) as request:
            result = atlas.wait_for_prediction(
                "request-1",
                api_key="secret",
                max_polls=3,
                poll_interval=0,
            )

        self.assertEqual(result["outputs"], ["video.mp4"])
        self.assertEqual(request.call_count, 2)
        self.assertTrue(all(call.args[0] == "GET" for call in request.call_args_list))

    def test_dry_run_needs_no_api_key(self) -> None:
        output = io.StringIO()
        with mock.patch.dict("os.environ", {}, clear=True), contextlib.redirect_stdout(output):
            result = atlas.main(["--prompt", "A quiet lake", "--dry-run"])

        self.assertEqual(result, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["model"], atlas.DEFAULT_MODEL)
        self.assertEqual(payload["prompt"], "A quiet lake")
        self.assertTrue(payload["generate_audio"])

    def test_curl_receives_api_key_over_stdin_not_process_arguments(self) -> None:
        completed = mock.Mock(returncode=0, stdout='{"data":{"id":"request-1"}}', stderr="")
        with mock.patch.object(atlas.shutil, "which", return_value="/usr/bin/curl"), mock.patch.object(
            atlas.subprocess, "run", return_value=completed
        ) as run:
            response = atlas._request_json(
                "GET", "/api/v1/model/prediction/request-1", api_key="private-key"
            )

        self.assertEqual(response["data"]["id"], "request-1")
        self.assertEqual(run.call_args.args[0], ["/usr/bin/curl", "--config", "-"])
        self.assertNotIn("private-key", " ".join(run.call_args.args[0]))
        self.assertIn("Authorization: Bearer private-key", run.call_args.kwargs["input"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest import mock

from scripts import atlas_seedance_generate as atlas


class AtlasSeedanceGenerateTests(unittest.TestCase):
    def setUp(self) -> None:
        blocker = mock.patch("socket.create_connection", side_effect=AssertionError("network forbidden in provider unit tests"))
        blocker.start()
        self.addCleanup(blocker.stop)

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
            {"data": {"id": "request-1", "status": "completed", "outputs": ["https://media.example/video.mp4"]}},
        ]
        with mock.patch.object(atlas, "_request_json", side_effect=responses) as request:
            result = atlas.wait_for_prediction(
                "request-1",
                api_key="secret",
                max_polls=3,
                poll_interval=0,
            )

        self.assertEqual(result["outputs"], ["https://media.example/video.mp4"])
        self.assertEqual(request.call_count, 2)
        self.assertTrue(all(call.args[0] == "GET" for call in request.call_args_list))

    def test_dry_run_needs_no_api_key(self) -> None:
        output = io.StringIO()
        with mock.patch.dict("os.environ", {}, clear=True), contextlib.redirect_stdout(output):
            result = atlas.main(["--prompt", "A quiet lake", "--dry-run"])

        self.assertEqual(result, 0)
        payload = json.loads(output.getvalue())["payload"]
        self.assertEqual(payload["model"], atlas.DEFAULT_MODEL)
        self.assertEqual(payload["prompt"], "A quiet lake")
        self.assertTrue(payload["generate_audio"])

    def test_transport_uses_pinned_tls_host_and_one_request(self) -> None:
        response = mock.Mock(status=200)
        response.read1.side_effect = [b'{"data":{"id":"request-1"}}', b'']
        with mock.patch.object(atlas.http.client, "HTTPSConnection") as connect:
            connection = connect.return_value
            connection.getresponse.return_value = response
            response = atlas._request_json(
                "GET", "/api/v1/model/prediction/request-1", api_key="private-key"
            )
        self.assertEqual(response["data"]["id"], "request-1")
        connect.assert_called_once_with("api.atlascloud.ai", timeout=60.0)
        connection.request.assert_called_once()
        connection.close.assert_called_once()

    def test_default_plan_does_not_read_key_or_open_transport(self) -> None:
        original_get = atlas.os.environ.get
        def guarded_get(key, default=None):
            if key == "ATLASCLOUD_API_KEY":
                raise AssertionError("key read")
            return original_get(key, default)
        with mock.patch.object(atlas.os.environ, "get", side_effect=guarded_get), mock.patch.object(atlas, "_request_json", side_effect=AssertionError("network")), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(atlas.main(["--prompt", "A quiet lake"]), 0)
            self.assertEqual(atlas.main(["--prediction-id", "request-1"]), 0)

    def test_invalid_ids_headers_and_destinations_fail_before_connection(self) -> None:
        with mock.patch.object(atlas.http.client, "HTTPSConnection") as connect:
            for value in ("../escape", "a?secret=1", "a/b", "a\r\nHeader: x", "", "a" * 129):
                with self.subTest(value=value), self.assertRaises(atlas.AtlasAPIError):
                    atlas.get_prediction(value, api_key="dummy")
            for key in ("", "dummy\r\nHeader: x", "dummy token"):
                with self.subTest(key=key), self.assertRaises(atlas.AtlasAPIError):
                    atlas._request_json("GET", atlas.POLL_PREFIX + "request-1", api_key=key)
            with self.assertRaises(atlas.AtlasAPIError):
                atlas._request_json("POST", "https://other.example/", api_key="dummy", payload={})
            connect.assert_not_called()

    def test_redirect_error_and_ambiguous_transport_never_retry_or_echo_body(self) -> None:
        for status in (301, 307, 400, 429, 500):
            with self.subTest(status=status), mock.patch.object(atlas.http.client, "HTTPSConnection") as connect:
                connect.return_value.getresponse.return_value.status = status
                with self.assertRaises(atlas.AtlasAPIError):
                    atlas.submit_prediction({"prompt": "private"}, api_key="dummy")
                connect.return_value.request.assert_called_once()
                connect.return_value.getresponse.return_value.read1.assert_not_called()
        with mock.patch.object(atlas.http.client, "HTTPSConnection") as connect:
            connect.return_value.request.side_effect = OSError("private-key and private-prompt")
            with self.assertRaises(atlas.AtlasAPIError) as raised:
                atlas.submit_prediction({}, api_key="private-key")
            self.assertNotIn("private", str(raised.exception))
            connect.return_value.request.assert_called_once()

    def test_response_json_is_bounded_and_strict(self) -> None:
        for raw in (b'{"data":{},"data":{}}', b'{"a":NaN}', b'[]', b'x' * (atlas.MAX_JSON_BYTES + 1)):
            with self.subTest(size=len(raw)), mock.patch.object(atlas.http.client, "HTTPSConnection") as connect:
                response = connect.return_value.getresponse.return_value
                response.status = 200
                response.read1.side_effect = [raw, b'']
                with self.assertRaises(atlas.AtlasAPIError):
                    atlas.get_prediction("request-1", api_key="dummy")

    def test_prediction_binding_status_and_output_validation(self) -> None:
        good = {"id": "request-1", "status": "processing"}
        bad = [dict(good, id="request-2"), dict(good, status="future"), dict(good, model="other"),
               dict(good, status="completed", outputs=[]), dict(good, status="completed", outputs=["file:///secret"]),
               dict(good, status="completed", outputs=["https://user:pass@host/video"])]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(atlas.AtlasAPIError):
                atlas._prediction({"data": data}, "request-1")
        with self.assertRaises(atlas.AtlasAPIError):
            atlas._prediction({"code": 500, "data": good})

    def test_polling_ceiling_and_resume_never_create(self) -> None:
        with mock.patch.object(atlas, "_request_json", return_value={"data": {"id": "request-1", "status": "processing"}}) as request:
            with self.assertRaises(atlas.AtlasAPIError):
                atlas.wait_for_prediction("request-1", api_key="dummy", max_polls=2, poll_interval=0)
            self.assertEqual(request.call_count, 2)
            self.assertTrue(all(c.args[0] == "GET" for c in request.call_args_list))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(atlas.main(["--prediction-id", "request-1", "--live"]), 0)
            self.assertEqual(request.call_args.args[0], "GET")

    def test_submission_id_survives_failed_poll(self) -> None:
        output, error = io.StringIO(), io.StringIO()
        with mock.patch.object(atlas, "_request_json", side_effect=[{"data": {"id": "request-1", "status": "processing"}}, atlas.AtlasAPIError("poll failed")]) as request, contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            self.assertEqual(atlas.main(["--prompt", "test", "--live", "--wait"]), 1)
        self.assertEqual(json.loads(output.getvalue())["id"], "request-1")
        self.assertEqual([c.args[0] for c in request.call_args_list], ["POST", "GET"])
        self.assertIn("Reconcile provider history", error.getvalue())

    def test_cli_rejects_nonfinite_limits_and_ambiguous_execution_flags(self) -> None:
        for flags in (["--timeout", "nan"], ["--poll-interval", "inf"], ["--max-polls", "121"], ["--seed", "-2"]):
            with self.subTest(flags=flags), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(atlas.main(["--prompt", "test", *flags]), 1)
        for flags in (["--live", "--dry-run"], ["--api-base", "https://other.example"], ["--li"]):
            with self.subTest(flags=flags), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                atlas.main(["--prompt", "test", *flags])


if __name__ == "__main__":
    unittest.main()

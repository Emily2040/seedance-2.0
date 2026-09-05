"""Credential transport boundaries; only dummy headers and loopback servers."""

from __future__ import annotations

import http.server
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import eval_run


class ProviderEndpointTests(unittest.TestCase):
    def test_unconfigured_or_non_https_endpoint_is_rejected_before_open(self):
        allowed = eval_run.ANTHROPIC_API_URL
        for endpoint in (
            allowed.replace("https:", "http:"),
            allowed + "?key=dummy",
            allowed + "#fragment",
            "https://example.invalid/v1/messages",
            "file:///not-a-provider",
        ):
            with self.subTest(endpoint=endpoint), mock.patch.object(
                eval_run.urllib.request, "build_opener"
            ) as build:
                with self.assertRaises(eval_run.ProviderResponseError):
                    eval_run._open_provider_request(
                        urllib.request.Request(endpoint), timeout=120
                    )
                build.assert_not_called()

    def test_every_configured_endpoint_uses_private_redirect_rejecting_opener(self):
        for provider in eval_run.PROVIDER_CONFIGS.values():
            for endpoint in provider.endpoints.values():
                with self.subTest(endpoint=endpoint), mock.patch.object(
                    eval_run.urllib.request, "build_opener"
                ) as build:
                    request = urllib.request.Request(endpoint)
                    eval_run._open_provider_request(request, timeout=120)
                    handler = build.call_args.args[0]
                    self.assertIsInstance(handler, eval_run._RejectProviderRedirects)
                    build.return_value.open.assert_called_once_with(request, timeout=120)

    def test_redirect_error_closes_body_and_does_not_expose_location(self):
        body = mock.Mock()
        error = urllib.error.HTTPError(
            eval_run.ANTHROPIC_API_URL, 302,
            "authenticated provider redirects are refused",
            {"Location": "https://example.invalid/private-path"}, body,
        )
        with mock.patch.object(eval_run, "_open_provider_request", side_effect=error):
            with self.assertRaises(eval_run.ProviderResponseError) as raised:
                eval_run._read_api_response(
                    urllib.request.Request(eval_run.ANTHROPIC_API_URL), "dummy"
                )
        body.close.assert_called_once()
        self.assertNotIn("private-path", str(raised.exception))
        self.assertIn("302", str(raised.exception))


class RedirectLoopbackTests(unittest.TestCase):
    def test_no_redirect_replays_a_request_or_forwards_dummy_credentials(self):
        received = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                received.append((self.server.server_port, self.path))
                if self.path == "/redirect":
                    self.send_response(self.server.redirect_code)
                    self.send_header("Location", self.server.destination)
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"{}")

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
                self.do_GET()

        origin = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        target = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threads = []
        try:
            for server in (origin, target):
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                threads.append(thread)
            # Loopback HTTP isolates urllib's redirect behavior from TLS and
            # external providers. Production HTTPS allowlisting is checked above.
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}), eval_run._RejectProviderRedirects()
            )
            for code in (301, 302, 303, 307, 308):
                for destination in (origin, target):
                    for method in ("GET", "POST"):
                        with self.subTest(code=code, port=destination.server_port, method=method):
                            received.clear()
                            origin.redirect_code = code
                            origin.destination = f"http://127.0.0.1:{destination.server_port}/sink"
                            request = urllib.request.Request(
                                f"http://127.0.0.1:{origin.server_port}/redirect",
                                data=b"{}" if method == "POST" else None,
                                headers={"Authorization": "Bearer AUDIT-DUMMY", "X-api-key": "AUDIT-DUMMY"},
                                method=method,
                            )
                            with self.assertRaises(urllib.error.HTTPError) as raised:
                                opener.open(request, timeout=5)
                            self.assertEqual(raised.exception.code, code)
                            raised.exception.close()
                            self.assertEqual(received, [(origin.server_port, "/redirect")])
        finally:
            for server in (origin, target):
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()

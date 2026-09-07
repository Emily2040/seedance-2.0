"""Exercise real stalled children, bounded pipes and output preservation."""
from __future__ import annotations

import io
import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import time
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import extract_last_frame as extractor


class MediaDeadlineTests(unittest.TestCase):
    def test_stalled_child_is_killed_and_reaped(self):
        children = []
        real_popen = subprocess.Popen

        def start(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child

        started = time.monotonic()
        with (
            mock.patch.object(extractor.subprocess, "Popen", side_effect=start),
            extractor._deadline_scope(0.2),
            self.assertRaisesRegex(extractor.FrameExtractionError, "safety timeout"),
        ):
            extractor._run_bounded([sys.executable, "-c", "import time; time.sleep(120)"])
        self.assertLess(time.monotonic() - started, 4)
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())
        self.assertTrue(children[0].stdout.closed)
        self.assertTrue(children[0].stderr.closed)
        self.assertIsNone(extractor._DEADLINE.get())

    def test_each_external_phase_shares_the_extraction_deadline(self):
        stall = [sys.executable, "-c", "import time; time.sleep(120)"]
        real_run = extractor._run_bounded
        for phase in ("option", "decode", "png_probe", "encode"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                clip = root / "source.mp4"
                clip.write_bytes(b"input")
                output = root / ("frame.jpg" if phase == "encode" else "frame.png")
                extractor._frame_sync_options.cache_clear()
                with mock.patch.object(extractor, "_run_bounded", side_effect=lambda *a, **kw: real_run(stall)):
                    if phase == "option":
                        guard = mock.patch.object(extractor, "_probe_decodable_png")
                    elif phase == "decode":
                        guard = mock.patch.object(extractor, "_frame_stream_command", return_value=stall)
                    elif phase == "png_probe":
                        # The child supplies no frame; the parser fixture supplies
                        # one to exercise the separate retained-frame probe.
                        guard = mock.patch.object(extractor, "_frame_stream_command", return_value=[sys.executable, "-c", "pass"])
                    else:
                        guard = mock.patch.object(extractor, "render_frame_png", return_value=b"frame")
                    with guard:
                        parser = (mock.patch.object(extractor, "_read_png_frame", side_effect=[b"frame", None])
                                  if phase == "png_probe" else mock.patch.object(extractor, "_MAX_HELP_BYTES", 4*1024*1024))
                        with parser, self.assertRaisesRegex(extractor.FrameExtractionError, "safety timeout"):
                            extractor.extract_frame("unused-ffmpeg", clip, output, False, False, timeout_seconds=0.3)
                self.assertFalse(output.exists())
                self.assertEqual({p.name for p in root.iterdir()}, {clip.name})
                self.assertIsNone(extractor._DEADLINE.get())
        extractor._frame_sync_options.cache_clear()

    def test_nested_stages_do_not_reset_the_budget(self):
        with mock.patch.object(extractor.time, "monotonic", return_value=100):
            with extractor._deadline_scope(10):
                self.assertEqual(extractor._DEADLINE.get(), 110)
                with mock.patch.object(extractor.time, "monotonic", return_value=108):
                    with extractor._deadline_scope(120):
                        self.assertEqual(extractor._remaining_time(), 2)
        self.assertIsNone(extractor._DEADLINE.get())

    def test_expired_work_cannot_publish_even_with_a_complete_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clip, output = root / "clip.mp4", root / "frame.png"
            clip.write_bytes(b"clip")
            def delayed_frame(*args):
                time.sleep(0.05)
                return b"complete"
            with mock.patch.object(extractor, "render_frame_png", side_effect=delayed_frame), self.assertRaisesRegex(extractor.FrameExtractionError, "safety timeout"):
                extractor.extract_frame("unused", clip, output, False, False, timeout_seconds=0.01)
            self.assertEqual({p.name for p in root.iterdir()}, {clip.name})

    def test_diagnostics_are_drained_without_growing_the_retained_buffer(self):
        command = [sys.executable, "-c", "import sys; sys.stderr.buffer.write(b'x'*2000000+b'final-marker')"]
        result = extractor._run_bounded(command)
        self.assertEqual(result.returncode, 0)
        self.assertLessEqual(len(result.stderr), extractor._MAX_DIAGNOSTIC_BYTES)
        self.assertTrue(result.stderr.endswith(b"final-marker"))

    def test_output_limit_kills_the_producer(self):
        command = [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x'*2000000)"]
        with self.assertRaisesRegex(extractor.FrameExtractionError, "output exceeds"):
            extractor._run_bounded(command, max_output=1024)

    def test_nonfinite_and_nonpositive_cli_limits_fail_before_work(self):
        for value in ("nan", "inf", "-inf", "0", "-1"):
            with self.subTest(value=value), mock.patch.object(sys, "argv", ["extract_last_frame.py", "--timeout-seconds="+value, "--self-test"]), mock.patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit) as result:
                extractor.main()
            self.assertEqual(result.exception.code, 2)

    def test_file_input_excludes_network_protocols(self):
        with mock.patch.object(extractor, "_frame_sync_options", return_value=("-vsync", "0")):
            cmd = extractor._frame_stream_command("ffmpeg", Path("clip.mp4"), False)
        position = cmd.index("-protocol_whitelist")
        self.assertEqual(cmd[position+1], "file,pipe")
        self.assertLess(position, cmd.index("-i"))

    @unittest.skipUnless(os.environ.get("SEEDANCE_TEST_FFMPEG") or shutil.which("ffmpeg"), "requires real FFmpeg")
    def test_local_hls_cannot_request_an_http_segment(self):
        requests = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(404)
                self.end_headers()
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                clip, output = root / "clip.m3u8", root / "frame.png"
                clip.write_text("#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:1,\nhttp://127.0.0.1:"+str(server.server_port)+"/segment.ts\n#EXT-X-ENDLIST\n", encoding="utf-8")
                with self.assertRaises(extractor.FrameExtractionError):
                    extractor.extract_frame(os.environ.get("SEEDANCE_TEST_FFMPEG") or shutil.which("ffmpeg"), clip, output, False, False, timeout_seconds=5)
                self.assertFalse(output.exists())
                self.assertEqual(requests, [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

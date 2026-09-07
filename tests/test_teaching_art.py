import hashlib
from pathlib import Path
import struct
import unittest

from scripts.strict_json import load_json

ROOT = Path(__file__).resolve().parents[1]


class TeachingArtTests(unittest.TestCase):
    def test_provenance_matches_the_delivered_bytes(self):
        record = load_json(ROOT / "data/paper-fan-art.json", root=ROOT)
        raw = (ROOT / record["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), record["sha256"])
        self.assertEqual(len(raw), record["bytes"])
        self.assertEqual(struct.unpack(">II", raw[16:24]), (record["width"], record["height"]))
        self.assertFalse(record["seedance_output"])
        self.assertEqual(record["evidence_status"], "ai_generated_teaching_concept")

    def test_image_and_provenance_are_inside_source_only_readme_region(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        region = text.split("<!-- installed-readme-gallery:start -->")[1].split("<!-- installed-readme-gallery:end -->")[0]
        self.assertIn("assets/paper-fan-teaching.png", region)
        self.assertIn("AI-generated teaching concept, not Seedance output", region)
        self.assertIn("docs/PAPER_FAN_ART.md", region)
        payload = (ROOT / "validation/install-payload.txt").read_text(encoding="utf-8").splitlines()
        for path in ("assets/paper-fan-teaching.png", "docs/PAPER_FAN_ART.md", "data/paper-fan-art.json"):
            self.assertNotIn(path, payload)

    def test_example_still_has_action_and_endpoint_without_the_image(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        before = " ".join(text.split("<!-- teaching-image:placement -->")[0].split())
        self.assertIn("the last fold of a paper fan and let go.", before)
        self.assertIn("The fan settles on the wood.", before)
        self.assertIn("No music.", before)

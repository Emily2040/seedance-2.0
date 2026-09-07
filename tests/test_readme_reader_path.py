from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReadmeReaderPathTests(unittest.TestCase):
    def test_first_prompt_fits_the_verified_mobile_line_budget(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        prompt = re.search(r"```text\n(.*?)\n```", text, re.S).group(1)
        self.assertLessEqual(max(map(len, prompt.splitlines())), 32)
        joined = " ".join(prompt.split())
        self.assertIn("The fan settles on the wood.", joined)
        self.assertIn("No music.", joined)

    def test_entry_and_install_precede_advanced_material(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertLess(text.index("## Start Here"), text.index("## Install"))
        self.assertLess(text.index("## Install"), text.index("## Validation"))
        self.assertNotIn("assets/hero-command-center.png", text)
        self.assertIn("<summary>Installation by client, replacement and recovery details</summary>", text)

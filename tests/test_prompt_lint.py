from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prompt_lint.py"
COMPUTED_RESULT_NOTE = (
    "Run `python scripts/prompt_lint.py --strict` for the computed result; "
    "this document does not self-certify a pass."
)


def golden_document(prompt: str, lint_result: str = "lint: pass") -> str:
    return (
        "## Source Brief\n\n"
        "Preserve the accepted opening state.\n\n"
        "## Internal Prompt Specification\n\n"
        "A compact transition with a locked camera.\n\n"
        "## Compiled Natural-Language Prompt\n\n"
        f"{prompt}\n\n"
        "## Lint Result\n\n"
        f"{lint_result}\n\n"
        "## Control-Critical Sentences\n\n"
        "Why this remains control-critical: it preserves the observed opening.\n"
    )


class PromptLintTests(unittest.TestCase):
    def run_fixture(
        self,
        prompt: str,
        *,
        strict: bool = False,
        lint_result: str = "lint: pass",
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="prompt-lint-test-", dir=ROOT) as temp:
            fixture_root = Path(temp)
            fixture = fixture_root / "examples" / "golden-prompts" / "case.md"
            fixture.parent.mkdir(parents=True)
            fixture.write_text(golden_document(prompt, lint_result), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), str(fixture_root)]
            if strict:
                command.append("--strict")
            return subprocess.run(command, cwd=ROOT, text=True, capture_output=True)

    def test_prompt_lint_self_test_and_examples(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--self-test", "--strict"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_json_objects_and_arrays(self) -> None:
        prompts = {
            "object": '{"prompt": "A courier crosses the room."}',
            "array": '[{"prompt": "A courier crosses the room."}]',
        }
        for name, prompt in prompts.items():
            with self.subTest(name=name):
                result = self.run_fixture(prompt)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("structured JSON", result.stdout)

    def test_rejects_fenced_structured_data_and_language_labels(self) -> None:
        prompts = {
            "json-uppercase": "```JSON\n[{\"prompt\": \"x\"}]\n```",
            "yaml": "```yaml\nprompt: x\ncamera: locked\n```",
            "yml-tilde": "~~~yml\nprompt: x\ncamera: locked\n~~~",
            "unlabelled-json": "```\n{\"prompt\": \"x\"}\n```",
        }
        for name, prompt in prompts.items():
            with self.subTest(name=name):
                result = self.run_fixture(prompt)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("structured", result.stdout.lower())

    def test_rejects_yaml_like_mapping_and_sequence(self) -> None:
        prompts = {
            "mapping": "prompt: courier crosses room\ncamera: locked\nlighting: practical",
            "nested-mapping": "prompt:\n  subject: courier\n  action: crosses room",
            "sequence": "- subject: courier\n- action: crosses room",
            "document-marker": "---\nprompt: courier crosses room",
        }
        for name, prompt in prompts.items():
            with self.subTest(name=name):
                result = self.run_fixture(prompt)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("YAML-like", result.stdout)

    def test_rejects_malformed_structured_candidates(self) -> None:
        prompts = {
            "array": '[{"prompt": ]',
            "object": '{"prompt": }',
            "labelled-json": "```json\n{not valid json}\n```",
            "unclosed-json-fence": "```json\n{\"prompt\": \"x\"}",
        }
        for name, prompt in prompts.items():
            with self.subTest(name=name):
                result = self.run_fixture(prompt)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("malformed", result.stdout.lower())

    def test_adversarial_format_variants_do_not_bypass_detection(self) -> None:
        prompts = {
            "indented-fence": "   ```json\n[1, 2]\n   ```",
            "attribute-label": "```{.json}\n{\"prompt\": \"x\"}\n```",
            "info-string": "```json linenums\n{\"prompt\": \"x\"}\n```",
            "leading-bom-array": "\ufeff  [true, false]",
            "single-wrapper-key": "prompt: courier crosses the room",
            "mapping-with-nested-list": "prompt:\n  - courier crosses the room",
            "flow-style-yaml": "prompt: {camera: locked}",
            "fence-after-prose": (
                "Use the following payload.\n```json\n{\"prompt\": \"x\"}\n```"
            ),
            "indented-fence-after-prose": (
                "Use the following payload.\n   ```json\n[1, 2]\n   ```"
            ),
            "payload-after-prose": (
                "Use the following payload.\n{\"prompt\": \"x\"}"
            ),
            "nested-looking-fence": (
                "```text\nAn invalid wrapper follows.\n```json\n{\"prompt\": \"x\"}\n```"
            ),
            # Decoder recursion limits vary by Python version. Either parsed
            # or depth-rejected, this must remain a lint finding, not a crash.
            "excessively-deep-array": "[" * 1500 + "0" + "]" * 1500,
        }
        for name, prompt in prompts.items():
            with self.subTest(name=name):
                result = self.run_fixture(prompt)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reference_label_is_not_mistaken_for_a_json_array(self) -> None:
        result = self.run_fixture(
            "[Video 1] is the accepted continuity source; continue from its final frame.",
            strict=True,
            lint_result=COMPUTED_RESULT_NOTE,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_self_declared_pass_has_no_strict_authority(self) -> None:
        prompt = "A courier crosses the room while the camera remains locked."
        declarations = ("lint: pass", "**Lint: pass**", "Status: `lint: pass`.")
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                default = self.run_fixture(prompt, lint_result=declaration)
                strict = self.run_fixture(prompt, strict=True, lint_result=declaration)
                self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
                self.assertNotEqual(strict.returncode, 0, strict.stdout + strict.stderr)
                self.assertIn("self-declared", strict.stdout)

    def test_strict_rejects_fenced_prose_while_default_accepts_it(self) -> None:
        prompt = "```text\nA courier crosses the room while the camera remains locked.\n```"
        default = self.run_fixture(prompt)
        strict = self.run_fixture(prompt, strict=True)
        self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
        self.assertNotEqual(strict.returncode, 0, strict.stdout + strict.stderr)
        self.assertIn("code fence", strict.stdout)

    def test_plain_prose_with_colons_passes_both_modes(self) -> None:
        prompt = (
            "Beginning: the courier waits at the door. Then: she crosses the room. "
            "Sound: one soft chime, with no dialogue."
        )
        for strict in (False, True):
            with self.subTest(strict=strict):
                result = self.run_fixture(
                    prompt,
                    strict=strict,
                    lint_result=COMPUTED_RESULT_NOTE,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_single_line_yaml_ambiguity_is_not_overclassified(self) -> None:
        prompts = (
            "Camera: hold a locked waist-height frame until the courier exits.",
            "Reference: [Video 1] preserves the traveler's charcoal coat.",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                result = self.run_fixture(
                    prompt,
                    strict=True,
                    lint_result=COMPUTED_RESULT_NOTE,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_success_output_states_the_linter_boundary(self) -> None:
        result = self.run_fixture(
            "A courier crosses the room while the camera remains locked.",
            strict=True,
            lint_result=COMPUTED_RESULT_NOTE,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("does not assess semantic creativity or generation quality", result.stdout)


if __name__ == "__main__":
    unittest.main()

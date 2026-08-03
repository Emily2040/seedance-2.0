from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prompt_architecture_stress as architecture  # noqa: E402
import prompt_lint  # noqa: E402

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
    def run_document(
        self,
        document: str,
        *,
        strict: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="prompt-lint-test-", dir=ROOT) as temp:
            fixture_root = Path(temp)
            fixture = fixture_root / "examples" / "golden-prompts" / "case.md"
            fixture.parent.mkdir(parents=True)
            fixture.write_text(document, encoding="utf-8")
            command = [sys.executable, str(SCRIPT), str(fixture_root)]
            if strict:
                command.append("--strict")
            return subprocess.run(command, cwd=ROOT, text=True, capture_output=True)

    def run_fixture(
        self,
        prompt: str,
        *,
        strict: bool = False,
        lint_result: str = "lint: pass",
    ) -> subprocess.CompletedProcess[str]:
        return self.run_document(
            golden_document(prompt, lint_result),
            strict=strict,
        )

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
            "quoted-yaml-fence": (
                "> ```yaml\n> camera: locked\n> lighting: practical\n> ```"
            ),
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
            "commented-document-marker": "--- # generated payload\nprompt: courier",
            "directive-with-tab": "%YAML\t1.2\nprompt: courier",
            "flow-sequence": "[prompt, camera, lighting]",
            "multiline-flow-sequence": "[\nprompt,\ncamera\n]",
            "quoted-wrapper": '"prompt": courier crosses room',
            "quoted-mapping": '"subject": courier\n"camera": locked',
            "simplified-chinese-mapping": "提示词: 快递员穿过房间\n镜头: 固定机位",
            "fullwidth-colon-mapping": "提示词：快递员穿过房间\n镜头：固定机位",
            "korean-mapping": "프롬프트: 배달원이 방을 건넌다\n카메라: 고정",
            "sentence-valued-fields": (
                "subject: A courier crosses.\n"
                "camera: The frame remains locked."
            ),
            "quoted-title-case-fields": '"Camera": locked\n"Sound": rain only',
            "single-quoted-title-case-fields": "'Camera': locked\n'Sound': rain only",
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
            "wrapped-object": 'Use the following payload: {"prompt": }',
            "direct-array": "Return [1,].",
            "labelled-json": "```json\n{not valid json}\n```",
            "unclosed-json-fence": "```json\n{\"prompt\": \"x\"}",
        }
        for name, prompt in prompts.items():
            with self.subTest(name=name):
                result = self.run_fixture(prompt)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("malformed", result.stdout.lower())

    def test_serialization_cues_reject_embedded_yaml_flow_sequences(self) -> None:
        wrapped = (
            "Return [prompt].",
            "Use this payload: [prompt]",
            "Submit: [camera, lighting].",
        )
        for prompt in wrapped:
            with self.subTest(prompt=prompt):
                result = self.run_fixture(prompt)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("YAML-like", result.stdout)

        prose_controls = (
            "The courier returns [Video 1] to the editor.",
            "Use the following [1, 2] camera beats as continuity anchors.",
        )
        for prompt in prose_controls:
            with self.subTest(prompt=prompt):
                result = self.run_fixture(
                    prompt,
                    strict=True,
                    lint_result=COMPUTED_RESULT_NOTE,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_html_table_before_rendered_text_erases_cell_boundaries(self) -> None:
        prompt = (
            "<table><tr><th>prompt</th>"
            "<td>A courier crosses.</td></tr></table>"
        )
        result = self.run_fixture(prompt)

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("HTML table wrapper", result.stdout)

    def test_rejects_markdown_tables_before_pipe_normalization(self) -> None:
        prompts = (
            "| Field | Value |\n| :--- | :--- |\n| prompt | A courier crosses. |",
            "Field | Value\n---: | :---:\nprompt | A courier crosses.",
            "> | Field | Value |\n> | --- | ---: |\n> | prompt | A courier crosses. |",
            "| Field\\|name | Value |\n| --- | --- |\n| prompt | A courier crosses. |",
            "| `Field\\|name` | Value |\n| --- | --- |\n| prompt | A courier crosses. |",
            "| Field ` | Value |\n| :--- | :--- |\n| prompt | x |",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                result = self.run_fixture(prompt, strict=True)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("Markdown table wrapper", result.stdout)

    def test_gfm_code_spans_do_not_override_unescaped_pipe_boundaries(self) -> None:
        paragraph = (
            "| `Field|name` | Value |\n"
            "| --- | --- |\n"
            "| prompt | A courier crosses. |"
        )
        self.assertIsNone(prompt_lint.markdown_table_structure_reason(paragraph))
        result = self.run_fixture(
            paragraph,
            strict=True,
            lint_result=COMPUTED_RESULT_NOTE,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_blank_line_does_not_create_a_gfm_table(self) -> None:
        prompts = (
            "Camera | motion\n\n--- | ---",
            "| Field | Value |\n\n| --- | --- |\n| prompt | x |",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertIsNone(
                    prompt_lint.markdown_table_structure_reason(prompt)
                )
                result = self.run_fixture(
                    prompt,
                    strict=True,
                    lint_result=COMPUTED_RESULT_NOTE,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_response_serialization_cues_cannot_wrap_json(self) -> None:
        prompts = (
            'Respond with the following JSON: {"prompt":"x"}.',
            'Reply with: {"prompt":"x"}.',
            'Answer with this payload: {"prompt":"x"}.',
            'Produce a serialized object: {"prompt":"x"}.',
            'Serialize: {"prompt":"x"}.',
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                result = self.run_fixture(prompt, strict=True)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("structured JSON", result.stdout)

    def test_direct_serializer_grammar_is_complete_and_language_bounded(self) -> None:
        verbs = (
            "Answer with", "Consume", "Emit", "Input", "Load", "Output",
            "Parse", "Provide", "Produce", "Reply with", "Respond with",
            "Return", "Send", "Serialize", "Submit", "Use",
        )
        payload = '{"prompt":"x"}'
        for verb in verbs:
            prompts = (
                f"{verb} {payload}.",
                f"{verb} this payload: {payload}.",
                f"{verb} the following JSON object: {payload}.",
            )
            for prompt in prompts:
                with self.subTest(verb=verb, prompt=prompt):
                    self.assertIsNotNone(
                        prompt_lint.structured_prompt_reason(prompt, strict=True)
                    )

        spanish_verbs = (
            "Analiza", "Carga", "Consume", "Contesta con", "Devuelve",
            "Emite", "Env\u00eda", "Entrega", "Genera", "Introduce", "Manda",
            "Procesa", "Produce", "Proporciona", "Responde con", "Retorna",
            "Serializa", "Usa",
        )
        for verb in spanish_verbs:
            for prompt in (
                f"{verb} {payload}.",
                f"{verb} el siguiente JSON: {payload}.",
            ):
                with self.subTest(language="es", verb=verb, prompt=prompt):
                    self.assertIsNotNone(
                        prompt_lint.structured_prompt_reason(prompt, strict=True)
                    )

        chinese_verbs = (
            "\u8fd4\u56de", "\u8f93\u51fa", "\u63d0\u4f9b", "\u751f\u6210", "\u5e8f\u5217\u5316", "\u53d1\u9001", "\u63d0\u4ea4", "\u56de\u590d",
            "\u56de\u7b54", "\u4f7f\u7528", "\u52a0\u8f7d", "\u8f93\u5165", "\u89e3\u6790", "\u8bfb\u53d6", "\u5904\u7406",
        )
        for verb in chinese_verbs:
            for prompt in (
                f"{verb}{payload}\u3002",
                f"\u8bf7{verb}\u4ee5\u4e0b JSON\uff1a{payload}\u3002",
            ):
                with self.subTest(language="zh", verb=verb, prompt=prompt):
                    self.assertIsNotNone(
                        prompt_lint.structured_prompt_reason(prompt, strict=True)
                    )

        localized_yaml = (
            "Emite la siguiente carga YAML: [prompt].",
            "\u8f93\u51fa\u8fd9\u4e2a YAML \u6570\u7ec4\uff1a[prompt]\u3002",
        )
        for prompt in localized_yaml:
            with self.subTest(prompt=prompt):
                self.assertIsNotNone(
                    prompt_lint.structured_prompt_reason(prompt, strict=True)
                )

        trailing_constraints = (
            'Return {"prompt":"x"} and nothing else.',
            'Output the following JSON object: {"prompt":"x"}.',
            'Emit this JSON payload: {"prompt":"x"}.',
            'Output the following YAML: [prompt].',
        )
        for prompt in trailing_constraints:
            with self.subTest(prompt=prompt):
                self.assertIsNotNone(
                    prompt_lint.structured_prompt_reason(prompt, strict=True)
                )

        discourse_cues = (
            'Describe the shot. Then return {"prompt":"x"} and nothing else.',
            'Describe la toma. Luego devuelve {"prompt":"x"} y nada m\u00e1s.',
            '\u5148\u63cf\u8ff0\u955c\u5934\u3002\u7136\u540e\u8fd4\u56de {"prompt":"x"}\uff0c\u4e0d\u8981\u5176\u4ed6\u5185\u5bb9\u3002',
            '\u8bf7\u4ee5 JSON \u683c\u5f0f\u8fd4\u56de\uff1a{"prompt":"x"}\u3002',
        )
        for prompt in discourse_cues:
            with self.subTest(prompt=prompt):
                self.assertIsNotNone(
                    prompt_lint.structured_prompt_reason(prompt, strict=True)
                )

    def test_serializer_grammar_preserves_visible_and_natural_prose_controls(self) -> None:
        controls = (
            "Use the following [1, 2] camera beats as continuity anchors.",
            "Use [1, 2] camera beats as continuity anchors.",
            "Use [Video 1] for continuity.",
            "Return [Video 1] to the editor.",
            "The courier returns [Video 1] to the editor.",
            'The terminal visibly displays: Return {"status":"ready"}.',
        )
        for prompt in controls:
            with self.subTest(prompt=prompt):
                self.assertIsNone(
                    prompt_lint.structured_prompt_reason(prompt, strict=True)
                )

    def test_malformed_nested_embedded_json_has_bounded_decoder_attempts(self) -> None:
        real_decoder = json.JSONDecoder()
        for depth in (1_024, 16_384):
            for closing in ("]" * depth, ""):
                calls = 0

                class CountingDecoder:
                    def raw_decode(self, value: str, index: int = 0):
                        nonlocal calls
                        calls += 1
                        return real_decoder.raw_decode(value, index)

                prompt = "A scene contains " + "[" * depth + "x" + closing
                with mock.patch.object(
                    prompt_lint.json,
                    "JSONDecoder",
                    return_value=CountingDecoder(),
                ):
                    self.assertIsNone(
                        prompt_lint.embedded_json_structure_reason(prompt)
                    )
                self.assertLessEqual(calls, 1, (depth, bool(closing), calls))

    def test_unclosed_candidate_cannot_hide_later_cue_backed_json(self) -> None:
        prompts = (
            'Camera note [unfinished.\nReturn {"prompt":"x"} and nothing else.',
            'Camera note {unfinished.\nThen return [1, 2].',
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertIsNotNone(
                    prompt_lint.structured_prompt_reason(prompt, strict=True)
                )

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
            "quoted-json-in-blockquote": '> {"prompt": "x"}',
            "quoted-json-in-list": '- {"prompt": "x"}',
            "nested-looking-fence": (
                "```text\nAn invalid wrapper follows.\n```json\n{\"prompt\": \"x\"}\n```"
            ),
            # Decoder recursion limits vary by Python version. Either parsed
            # or depth-rejected, this must remain a lint finding, not a crash.
            "excessively-deep-array": "[" * 1500 + "0" + "]" * 1500,
            # CPython limits decimal integer conversion. The linter must catch
            # that ValueError just like a decoder error, not emit a traceback.
            "oversized-integer-array": "[" + ("1" * 5000) + "]",
            "oversized-integer-in-json-fence": (
                "```json\n[" + ("1" * 5000) + "]\n```"
            ),
            "emphasized-json": '**{"prompt": "x"}**',
            "inline-code-json": '`{"prompt": "x"}`',
            "html-json": '<div>{"prompt": "x"}</div>',
            "entity-html-json": '<span>&#123;"prompt": "x"&#125;</span>',
            "heading-json": '### {"prompt": "x"}',
            "task-list-json": '- [ ] {"prompt": "x"}',
            "table-cell-yaml": "| prompt: courier crosses the room |",
            "emphasized-yaml": "**prompt: courier crosses the room**",
            "emphasized-multiline-yaml": (
                "**subject: A courier crosses.**\n"
                "**camera: The frame remains locked.**"
            ),
            "html-yaml": "<span>prompt: courier crosses the room</span>",
            "payload-after-prose-same-line": (
                'Use the following payload: {"prompt": "x"}'
            ),
            "payload-after-reference-label": (
                '[Video 1] {"prompt": "x"}'
            ),
            "data-array-after-prose": "Use this data: [1, 2, 3]",
            "values-array-after-prose": "Use these values: [1, 2, 3]",
            "list-array-after-prose": "Use this list: [1, 2, 3]",
            "payload-cue-after-object": 'Use {"prompt":"x"} as the payload.',
            "payload-cue-after-reference-object": (
                '[Video 1] {"prompt":"x"} is the payload.'
            ),
            "array-cue-after-array": "Use [1, 2] as the data array.",
            "direct-return-object": 'Return {"prompt":"x"}.',
            "direct-return-colon-object": 'Return: {"prompt":"x"}.',
            "direct-submit-array": "Submit [1, 2].",
            "quoted-direct-return-object": '> Return {"prompt":"x"}.',
            "listed-direct-submit-array": "- Submit [1, 2].",
            "multiline-direct-return-object": (
                "Please produce the requested output.\n"
                'Return {"prompt":"x"}.'
            ),
        }
        for name, prompt in prompts.items():
            with self.subTest(name=name):
                result = self.run_fixture(prompt)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reference_label_is_not_mistaken_for_a_json_array(self) -> None:
        prompts = (
            "[Video 1] is the accepted continuity source; continue from its final frame.",
            "[0-2s] The courier waits. [2-4s] She runs.",
            "[00:00-00:02] The courier waits at the locked door.",
            "[1] The courier crosses the room.",
            "[true crime] The title card remains visible.",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                result = self.run_fixture(
                    prompt,
                    strict=True,
                    lint_result=COMPUTED_RESULT_NOTE,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_self_declared_pass_has_no_strict_authority(self) -> None:
        prompt = "A courier crosses the room while the camera remains locked."
        declarations = (
            "lint: pass",
            "Result: lint: pass",
            "Computed lint: pass",
            "The result is lint: pass",
            "Final result: lint: pass",
            "Verification result: lint: pass",
            "The final result is lint: pass",
            "**Lint: pass**",
            "Status: `lint: pass`.",
            "## Lint: pass",
            "> **Lint:** **pass**",
            "1. Status: lint: pass ✅",
            "<p>lint: pass</p>",
            '<span title=">">lint: pass</span>',
            "| lint: pass |",
            "[lint: pass]",
            r"Lint\: pass",
            "Lint: [pass](#)",
            "| Lint | Pass |",
            "Lint result: pass",
            "Lint status: pass",
            "Li\u200bnt: pass",
            "lint: pa\ufe0fss",
            "<span hidden>x</span>lint: pass",
            '<span style="display: none">x</span>lint: pass',
            "<span>lint:</span>\n<span>pass</span>",
            "| Lint result | Pass |",
            "<tr><td>lint</td><td>pass</td></tr>",
            (
                '<table><tr><td title="a > b">lint</td>'
                '<td title="c > d">pass</td></tr></table>'
            ),
        )
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                default = self.run_fixture(prompt, lint_result=declaration)
                strict = self.run_fixture(prompt, strict=True, lint_result=declaration)
                self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
                self.assertNotEqual(strict.returncode, 0, strict.stdout + strict.stderr)
                self.assertIn("self-declared", strict.stdout)

        evidence_controls = (
            "Final result: command exited 0 with no lint findings.",
            "Verification note: run python scripts/prompt_lint.py --strict.",
            "Lighting result: pass after the practical is switched on.",
            "Lint result: command exited 0 with no findings.",
        )
        for note in evidence_controls:
            with self.subTest(note=note):
                result = self.run_fixture(prompt, strict=True, lint_result=note)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_counterfeit_or_ambiguous_section_structure_is_rejected(self) -> None:
        prose = "A courier crosses the room while the camera remains locked."
        canonical = golden_document(prose, COMPUTED_RESULT_NOTE)
        indented_canonical = "\n".join(
            f"  {line}" for line in canonical.splitlines()
        )
        compact_canonical = "\n".join(
            line for line in canonical.splitlines() if line
        )
        counterfeits = {
            "fenced-document": f"```markdown\n{canonical}```\n",
            "commented-document": f"<!--\n{canonical}-->\n",
            "script-document": (
                f'<script type="text/plain">\n{canonical}</script>\n'
            ),
            "pre-document": f"<pre>\n{canonical}</pre>\n",
            "div-raw-html-document": f"<div>\n{compact_canonical}\n</div>\n",
            "table-raw-html-document": (
                f"<table>\n{compact_canonical}\n</table>\n"
            ),
            "template-raw-html-document": (
                f"<template>\n{compact_canonical}\n</template>\n"
            ),
            "custom-element-document": (
                f"<x-prompt>\n{compact_canonical}\n</x-prompt>\n"
            ),
            "custom-element-quoted-greater-than-document": (
                f'<x-prompt data-note=">">\n{compact_canonical}\n</x-prompt>\n'
            ),
            "processing-instruction-document": (
                f"<?prompt\n{canonical}?>\n"
            ),
            "cdata-document": f"<![CDATA[\n{canonical}]]>\n",
            "declaration-document": f"<!PROMPT\n{canonical}>\n",
            "blockquote-document": "\n".join(
                f"> {line}" for line in canonical.splitlines()
            ),
            "list-contained-fence": (
                f"- ```markdown\n{indented_canonical}\n  ```\n"
            ),
            "front-matter-document": f"---\n{canonical}---\n",
            "block-scalar-document": f"document: |\n{indented_canonical}\n",
            "unclosed-fence-with-four-space-pseudo-close": (
                f"```markdown\n{canonical}    ```\n"
            ),
            "top-fence-with-blockquote-pseudo-close": (
                f"```markdown\n> ```\n{canonical}"
            ),
            "html-comment-fence-state-desync": (
                "<!--\n```\n-->\n```\n-->\n"
                f"{canonical}```\n"
            ),
            "duplicate-compiled-section": (
                canonical
                + "\n## Compiled Natural-Language Prompt\n\nA second prompt.\n"
            ),
            "out-of-order-sections": canonical.replace(
                "## Compiled Natural-Language Prompt",
                "## TEMP",
            ).replace(
                "## Lint Result",
                "## Compiled Natural-Language Prompt",
            ).replace(
                "## TEMP",
                "## Lint Result",
            ),
        }
        for name, document in counterfeits.items():
            with self.subTest(name=name):
                result = self.run_document(document, strict=True)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nested_markdown_containers_do_not_copy_quadratically(self) -> None:
        counter = [0]

        class CountingText(str):
            def __new__(cls, value: str):
                return super().__new__(cls, value)

            def __getitem__(self, key):
                result = super().__getitem__(key)
                if isinstance(key, slice):
                    counter[0] += len(result)
                    return CountingText(result)
                return result

        nested = CountingText("> " * 4_096 + "payload")
        content, context = prompt_lint.markdown_container_details(nested)
        self.assertEqual(content, "payload")
        self.assertEqual(len(context), 4_096)
        self.assertLessEqual(counter[0], len(nested) * 2)

    def test_container_fences_close_only_within_their_own_item(self) -> None:
        prose = "A courier crosses the room while the camera remains locked."
        canonical = golden_document(prose, COMPUTED_RESULT_NOTE)
        prefixes = (
            "- ```text\n  literal example\n  ```\n\n",
            "> ```text\n> literal example\n> ```\n\n",
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                result = self.run_document(prefix + canonical, strict=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_raw_html_preface_ends_on_container_relative_blank_line(self) -> None:
        prose = "A courier crosses the room while the camera remains locked."
        canonical = golden_document(prose, COMPUTED_RESULT_NOTE)
        prefixes = (
            "> <x-prompt>\n> illustrative raw text\n>\n",
            "> <div>\n> illustrative raw text\n>\n",
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                result = self.run_document(prefix + canonical, strict=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_strict_rejects_blockquoted_prose_fence(self) -> None:
        prompt = "> ```text\n> A courier waits.\n> ```"
        default = self.run_fixture(prompt)
        strict = self.run_fixture(prompt, strict=True)
        self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
        self.assertNotEqual(strict.returncode, 0, strict.stdout + strict.stderr)
        self.assertIn("code fence", strict.stdout)

    def test_unreadable_markdown_is_a_diagnostic_not_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="prompt-lint-test-", dir=ROOT) as temp:
            fixture_root = Path(temp)
            fixture = fixture_root / "examples" / "golden-prompts" / "case.md"
            fixture.parent.mkdir(parents=True)
            fixture.write_bytes(b"\xff\xfe\xfa")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(fixture_root), "--strict"],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("cannot read UTF-8 Markdown", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_strict_rejects_fenced_prose_while_default_accepts_it(self) -> None:
        prompt = "```text\nA courier crosses the room while the camera remains locked.\n```"
        default = self.run_fixture(prompt)
        strict = self.run_fixture(prompt, strict=True)
        self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
        self.assertNotEqual(strict.returncode, 0, strict.stdout + strict.stderr)
        self.assertIn("code fence", strict.stdout)

    def test_plain_prose_with_colons_passes_both_modes(self) -> None:
        prompts = (
            (
                "Beginning: the courier waits at the door. Then: she crosses the room. "
                "Sound: one soft chime, with no dialogue."
            ),
            "Camera: hold a locked frame.\nSound: rain only.",
            "Reference: [Video 1]",
            "**Camera: hold a locked frame until the courier exits.**",
            "<span>Beginning: the courier waits. Then she crosses the room.</span>",
            "`@Image1` controls identity while the camera remains locked.",
            "Beginning: the courier waits\nThen: she runs",
            "Beginning: the courier waits\nThen: she runs\nFinally: she stops",
            "Use the following [1, 2] camera beats as continuity anchors.",
            (
                'The terminal visibly displays {"status":"ready"} while the '
                "camera stays locked."
            ),
            (
                'The terminal visibly displays JSON status {"status":"ready"} '
                "while the camera stays locked."
            ),
            (
                "The terminal visibly displays:\n"
                'Return {"status":"ready"}.'
            ),
        )
        for prompt in prompts:
            for strict in (False, True):
                with self.subTest(prompt=prompt, strict=strict):
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


class CrossFeaturePromptGateTests(unittest.TestCase):
    """Pin the boundary between format lint and semantic architecture checks."""

    def assert_bare_prose(self, prompt: str) -> None:
        self.assertIsNone(prompt_lint.structured_prompt_reason(prompt, strict=True))

    def test_sequence_repairs_survive_format_lint_without_semantic_bypass(self) -> None:
        cases = (
            (
                "Camera stays locked off until the latch clicks, then the camera "
                "pushes in.",
                False,
            ),
            (
                "Camera stays locked off while the actor waits. Meanwhile, she opens "
                "the case; then the camera pushes in.",
                False,
            ),
            (
                "Camera stays locked off as the courier then checks the latch before "
                "the camera pushes in.",
                True,
            ),
            (
                "Camera stays locked off, then the camera pushes in. Meanwhile, the "
                "camera pulls out.",
                True,
            ),
        )
        for prompt, expected_camera_finding in cases:
            with self.subTest(prompt=prompt):
                self.assert_bare_prose(prompt)
                findings = architecture.contradiction_findings(prompt)
                self.assertEqual(
                    any(finding.startswith("camera:") for finding in findings),
                    expected_camera_finding,
                    findings,
                )

    def test_reference_exclusion_repairs_survive_format_lint(self) -> None:
        excluded = (
            "The sole light is sunlight; do not transfer the reference's wardrobe, "
            "face, texture, colour palette, exposure pattern, reflected spill, or "
            "neon lighting source."
        )
        self.assert_bare_prose(excluded)
        self.assertEqual(
            architecture.positive_families(
                excluded, architecture.LIGHT_SOURCE_FAMILIES
            ),
            {"sun"},
        )
        self.assertFalse(
            any(
                finding.startswith("light:")
                for finding in architecture.contradiction_findings(excluded)
            )
        )

        positive_reset = (
            "Do not transfer the face and costume, and use neon lighting as the "
            "sole source. Moonlight also lights the subject at the same time."
        )
        self.assert_bare_prose(positive_reset)
        self.assertEqual(
            architecture.positive_families(
                positive_reset, architecture.LIGHT_SOURCE_FAMILIES
            ),
            {"moon", "neon"},
        )
        self.assertTrue(
            any(
                finding.startswith("light:")
                for finding in architecture.contradiction_findings(positive_reset)
            )
        )

        while_reset = (
            "Ignore neon from the source, while sunlight and moonlight illuminate "
            "the actor as the only light sources."
        )
        self.assert_bare_prose(while_reset)
        self.assertEqual(
            architecture.positive_families(
                while_reset, architecture.LIGHT_SOURCE_FAMILIES
            ),
            {"moon", "sun"},
        )
        self.assertTrue(
            any(
                finding.startswith("light:")
                for finding in architecture.contradiction_findings(while_reset)
            )
        )

        while_reset_with_later_negation = (
            "Ignore neon from the source, while sunlight and moonlight illuminate "
            "the actor as the only light sources without flicker."
        )
        self.assert_bare_prose(while_reset_with_later_negation)
        self.assertEqual(
            architecture.positive_families(
                while_reset_with_later_negation,
                architecture.LIGHT_SOURCE_FAMILIES,
            ),
            {"moon", "sun"},
        )
        self.assertTrue(
            any(
                finding.startswith("light:")
                for finding in architecture.contradiction_findings(
                    while_reset_with_later_negation
                )
            )
        )

        while_reset_with_unrelated_negation = (
            "Ignore neon from the source, while the actor does not move and "
            "sunlight illuminates her face as the only light source."
        )
        self.assert_bare_prose(while_reset_with_unrelated_negation)
        self.assertEqual(
            architecture.positive_families(
                while_reset_with_unrelated_negation,
                architecture.LIGHT_SOURCE_FAMILIES,
            ),
            {"sun"},
        )

        negated_while_predicate = (
            "Ignore neon from the source, while sunlight and moonlight do not "
            "illuminate the actor."
        )
        self.assertEqual(
            architecture.positive_families(
                negated_while_predicate,
                architecture.LIGHT_SOURCE_FAMILIES,
            ),
            set(),
        )

        continued_exclusion = (
            "Ignore neon from the source while also excluding sunlight and moonlight."
        )
        self.assertEqual(
            architecture.positive_families(
                continued_exclusion, architecture.LIGHT_SOURCE_FAMILIES
            ),
            set(),
        )

    def test_opposite_action_reuse_is_semantic_not_a_format_violation(self) -> None:
        prompts = (
            "A courier opens the red case.",
            "The courier slowly quietly shuts the red case.",
        )
        for prompt in prompts:
            self.assert_bare_prose(prompt)
        records = [
            {
                "id": "airport-open",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Woman opens a red case at an airport gate",
                "prompt": prompts[0],
            },
            {
                "id": "workshop-close",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Man closes a red case inside a flooded workshop",
                "prompt": prompts[1],
            },
        ]
        findings = architecture.corpus_duplicate_findings(records)
        self.assertTrue(any("opposite-action" in finding for finding in findings), findings)

    def test_valid_semantics_do_not_authorize_a_serialized_wrapper(self) -> None:
        prompt = (
            "Camera stays locked off until the latch clicks, then the camera pushes in."
        )
        self.assertFalse(architecture.contradiction_findings(prompt))
        wrapped = (
            json.dumps({"prompt": prompt}),
            f"prompt: {prompt}",
        )
        for candidate in wrapped:
            with self.subTest(candidate=candidate):
                self.assertIsNotNone(
                    prompt_lint.structured_prompt_reason(candidate, strict=True)
                )


if __name__ == "__main__":
    unittest.main()

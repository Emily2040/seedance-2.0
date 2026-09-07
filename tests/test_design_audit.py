"""Documentation usefulness checks must not reward bitmap bulk or gallery count."""
import base64
from pathlib import Path
import tempfile
import unittest

from scripts.design_audit import LANGUAGE_PATHS, readme_findings


class ReadmeDesignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for path in LANGUAGE_PATHS:
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("# Quickstart\n", encoding="utf-8")
        self.text = "## Start Here\nChoose a prompt.\n## Install\n" + "\n".join(
            f"[Start {i}]({path})" for i, path in enumerate(LANGUAGE_PATHS))
        (self.root / "README.md").write_text(self.text, encoding="utf-8")

    def test_short_text_first_readme_needs_no_gallery(self):
        self.assertEqual(readme_findings(self.root, self.text), [])

    def test_small_optimized_png_is_not_rejected_for_low_byte_count(self):
        # A real, tiny PNG: byte count is a transfer concern, not image quality.
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aXioAAAAASUVORK5CYII=")
        (self.root / "sample.png").write_bytes(png)
        text = self.text + "\n![Small fixture](sample.png)"
        self.assertEqual(readme_findings(self.root, text), [])
        self.assertTrue(any("budget" in e for e in readme_findings(self.root, text, budget=1)))

    def test_missing_alt_and_missing_file_fail_for_separate_reasons(self):
        errors = readme_findings(self.root, self.text + "\n![](absent.png)")
        self.assertTrue(any("alt text" in e for e in errors))
        self.assertTrue(any("missing or unsafe" in e for e in errors))

    def test_missing_language_route_cannot_hide_in_code_or_comment(self):
        text = self.text.replace(f"[Start 5]({LANGUAGE_PATHS[5]})", "")
        text += f"\n```md\n[Hidden]({LANGUAGE_PATHS[5]})\n```\n<!-- [Hidden]({LANGUAGE_PATHS[5]}) -->"
        self.assertTrue(any(LANGUAGE_PATHS[5] in e for e in readme_findings(self.root, text)))

    def test_language_entry_requires_a_readable_name(self):
        original = f"[Start 5]({LANGUAGE_PATHS[5]})"
        for replacement in (f"[]({LANGUAGE_PATHS[5]})", f"[** **]({LANGUAGE_PATHS[5]})",
                            f'<a href="{LANGUAGE_PATHS[5]}"></a>',
                            f'<a href="{LANGUAGE_PATHS[5]}"><strong></strong></a>'):
            with self.subTest(replacement=replacement):
                errors = readme_findings(self.root, self.text.replace(original, replacement))
                self.assertTrue(any(LANGUAGE_PATHS[5] in e for e in errors))
        named = f'<a href="{LANGUAGE_PATHS[5]}"><strong>Read Russian</strong></a>'
        self.assertEqual(readme_findings(self.root, self.text.replace(original, named)), [])

    def test_fence_with_trailing_info_does_not_close_code(self):
        link = f"[Start 5]({LANGUAGE_PATHS[5]})"
        text = self.text.replace(link, "") + f"\n```text\n```python\n{link}\n```\n"
        self.assertTrue(any(LANGUAGE_PATHS[5] in e for e in readme_findings(self.root, text)))
        text = self.text.replace(link, "") + f"\n```text\ncode\n``` \t\n{link}\n"
        self.assertEqual(readme_findings(self.root, text), [])

    def test_additional_svg_gets_the_same_structural_and_resource_checks(self):
        good = '<svg xmlns="http://www.w3.org/2000/svg"><title>Mark</title><desc>A simple mark</desc><path d="M0 0h1"/></svg>'
        path = self.root / "new.svg"
        text = self.text + "\n![New illustration](new.svg)"
        path.write_text(good, encoding="utf-8")
        self.assertEqual(readme_findings(self.root, text), [])
        for bad in ("not SVG", good.replace('<desc>A simple mark</desc>', ''),
                    good.replace('</svg>', '<script>alert(1)</script></svg>'),
                    good.replace('</svg>', '<image href="https://example.com/p.png"/></svg>'),
                    good.replace('</svg>', '<style>@font-face{src:url(font.woff)}</style></svg>'),
                    good.replace('<svg ', '<svg onload="run()" ')):
            path.write_text(bad, encoding="utf-8")
            with self.subTest(bad=bad):
                self.assertTrue(readme_findings(self.root, text))

    def test_fragment_and_case_mismatch_fail(self):
        self.assertEqual(readme_findings(self.root, self.text + "\n[Install](#install)"), [])
        for target in ("#missing", "docs/QUICKSTART.md#missing", "docs/quickstart.md"):
            self.assertTrue(readme_findings(self.root, self.text + f"\n[Broken]({target})"))

    def test_external_media_unsafe_links_and_path_escape_rejected(self):
        for extra in ('<img alt="Remote" src="https://example.com/huge.png">',
                      '[Outside](../outside.md)', '[Executable](javascript:alert)'):
            self.assertTrue(readme_findings(self.root, self.text + "\n" + extra))

    def test_html_image_alt_and_source_are_required(self):
        for extra in ('<img src="absent.png">', '<img alt="Missing source">'):
            self.assertTrue(readme_findings(self.root, self.text + "\n" + extra))

    def test_corrupt_png_header_is_rejected(self):
        (self.root / "bad.png").write_bytes(b"not an image")
        errors = readme_findings(self.root, self.text + "\n![Broken](bad.png)")
        self.assertTrue(any("header/dimensions" in e for e in errors))

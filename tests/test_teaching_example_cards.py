"""Document contracts for the authored, ungenerated teaching-card collection.

These checks do not certify creative quality or the truth of future asset bindings.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('Evidence', 'Brief', 'Choice', 'Bindings', 'Settings', 'Why this direction', 'Check', 'Fallback')
REFERENCE_TAG = re.compile(
    r'@[\w-]+(?:[ \t]+\d+)?|'
    r'\[(?:Image|Video|Audio|图片|视频|音频|画像|動画|音声|이미지|비디오|오디오)[ \t]*\d+\]',
    re.IGNORECASE,
)


def reference_tags(text):
    # Match the original bytes: recognizing a spelling must not canonicalize it.
    return set(REFERENCE_TAG.findall(text))


def cards():
    paths = [ROOT / 'references/example-card-format.md']
    paths.extend(sorted((ROOT / 'references').glob('*-example-cards.md')))
    for path in paths:
        chunks = re.split(r'^## Card: ', path.read_text(encoding='utf-8'), flags=re.M)[1:]
        if not chunks:
            raise AssertionError(f'{path.name}: no teaching cards found')
        for chunk in chunks:
            title, _, body = chunk.partition('\n')
            yield path, title, body


class TeachingExampleCardsTests(unittest.TestCase):
    def test_cards_separate_required_fields_from_copyable_prompt(self):
        for path, title, body in cards():
            with self.subTest(page=path.name, card=title):
                for field in FIELDS:
                    self.assertRegex(body, rf'(?m)^\*\*{re.escape(field)}:\*\* \S')
                prompts = re.findall(r'^```text\n(.*?)\n```$', body, re.M | re.S)
                self.assertEqual(len(prompts), 1)
                self.assertEqual(len(re.findall(r'^```', body, re.M)), 2)
                self.assertTrue(prompts[0].strip())
                self.assertNotRegex(prompts[0], r'\*\*(?:Evidence|Choice|Bindings|Settings|Check|Fallback):')

    def test_current_cards_do_not_claim_unobserved_success(self):
        for path, title, body in cards():
            with self.subTest(page=path.name, card=title):
                # Promote a card only with a separately reviewed real output record.
                self.assertIn('**Evidence:** Concept; not generated or inspected.', body)

    def test_reference_prompts_are_conditional_and_tags_declared(self):
        for path, title, body in cards():
            with self.subTest(page=path.name, card=title):
                prompt = re.search(r'^```text\n(.*?)\n```$', body, re.M | re.S).group(1)
                bindings = re.search(r'^\*\*Bindings:\*\* (.+)$', body, re.M).group(1)
                tags = reference_tags(prompt)
                if bindings.startswith('None.'):
                    self.assertFalse(tags, 'reference prompt is incorrectly labeled asset-free')
                else:
                    self.assertIn('**Conditional prompt:**', body)
                    self.assertIn('Required; not attached.', bindings)
                    self.assertTrue(tags <= reference_tags(bindings), 'prompt tag has no exact binding')

    def test_tag_recognition_preserves_localized_spaced_and_bracketed_forms(self):
        for tag in ('@Image1', '@Video1', '@Audio1', '@图片1', '@视频1', '@音频1',
                    '@Image 1', '@Video 2', '[Video 1]', '[Image 2]', '[Audio 3]',
                    '@画像1', '@이미지1', '@CustomReference7'):
            with self.subTest(tag=tag):
                self.assertEqual(reference_tags(f'Use {tag} for the opening pose.'), {tag})
                self.assertEqual(reference_tags(f'Required; not attached. {tag} controls pose.'), {tag})
        self.assertNotEqual(reference_tags('@Image 1'), reference_tags('@Image1'))
        self.assertFalse(reference_tags('@Image1') <= reference_tags('@Image10'))

    def test_card_pages_are_declared_in_install_and_eval_payloads(self):
        import json
        payload = set((ROOT / 'validation/install-payload.txt').read_text(encoding='utf-8').splitlines())
        manifest = json.loads((ROOT / 'evals/source-manifest.json').read_text(encoding='utf-8'))
        roles = {item['path']: item['role'] for item in manifest['sources']}
        for path in {path for path, _, _ in cards()}:
            relative = path.relative_to(ROOT).as_posix()
            with self.subTest(page=relative):
                self.assertIn(relative, payload)
                self.assertEqual(roles.get(relative), 'responder')


if __name__ == '__main__':
    unittest.main()

"""Document contracts for the authored, ungenerated teaching-card collection.

These checks do not certify creative quality or the truth of future asset bindings.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('Evidence', 'Brief', 'Choice', 'Bindings', 'Settings', 'Why this direction', 'Check', 'Fallback')


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
                tags = set(re.findall(r'@(?:Image|Video|Audio)\d+', prompt))
                if tags:
                    self.assertIn('**Conditional prompt:**', body)
                    self.assertIn('Required; not attached.', bindings)
                    for tag in tags:
                        self.assertIn(tag, bindings)
                else:
                    self.assertTrue(bindings.startswith('None.'), bindings)

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

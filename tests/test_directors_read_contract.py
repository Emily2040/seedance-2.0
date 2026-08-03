from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import behavior_contract_check as behavior  # noqa: E402


CANONICAL = "references/directors-read.md"
ROUTES = behavior.DIRECTORS_READ_ROUTES
NO_MEMORY_ESCAPE_FILES = tuple(ROUTES) + (
    "references/directing-engine.md",
    "references/progressive-disclosure.md",
)
FIELDS = (
    "dramatic function",
    "turn",
    "POV",
    "power shift",
    "hidden want/objective",
    "obstacle/tactic",
    "subtext/contradiction",
    "visible suppressed behavior",
    "non-transferable detail",
    "stock solution refused",
)


def copy_route_contract(destination: Path) -> None:
    for rel in set(ROUTES) | {CANONICAL}:
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)


def directors_read_case_errors(cases: list[dict]) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "validation" / "fixtures" / "directors-read-cases.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(cases), encoding="utf-8")
        errors: list[str] = []
        behavior.validate_directors_read_cases(root, errors)
        return errors


def genre_library_errors() -> list[str]:
    errors: list[str] = []
    behavior.validate_directors_read_genre_library(ROOT, errors)
    return errors


class DirectorsReadContractTests(unittest.TestCase):
    def test_every_skill_is_explicitly_classified(self) -> None:
        actual = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "skills").rglob("SKILL.md")
        }
        classified = behavior.PROMPT_PRODUCING_SKILLS | set(
            behavior.NON_PROMPT_PRODUCING_SKILLS
        )

        self.assertEqual(actual, classified)
        self.assertEqual(
            set(ROUTES) - {
                "SKILL.md",
                "references/directing-engine.md",
                "references/prompt-compiler.md",
            },
            behavior.PROMPT_PRODUCING_SKILLS,
        )

    def test_one_canonical_contract_routes_every_prompt_path(self) -> None:
        errors: list[str] = []
        behavior.validate_directors_read_routes(ROOT, errors)
        self.assertEqual(errors, [])
        for rel, target in ROUTES.items():
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(f"]({target})", text, rel)
            self.assertNotIn("[ref:directors-read]", text.casefold(), rel)

    def test_every_route_requires_the_read_before_its_compile_boundary(self) -> None:
        for rel, phrase in behavior.DIRECTORS_READ_ACTIVATION_PHRASES.items():
            text = (ROOT / rel).read_text(encoding="utf-8").casefold()
            self.assertIn(phrase.casefold(), text, rel)

    def test_legacy_ref_directors_read_alias_cannot_replace_the_required_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_route_contract(root)
            skill = root / "SKILL.md"
            text = skill.read_text(encoding="utf-8")
            text = text.replace(
                "[Director's Read](references/directors-read.md)",
                "[ref:directors-read]",
            )
            skill.write_text(text, encoding="utf-8")
            errors: list[str] = []
            behavior.validate_directors_read_routes(root, errors)
            self.assertTrue(any("opaque" in error for error in errors), errors)

    def test_validator_rejects_a_route_that_drops_the_precompile_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_route_contract(root)
            compiler = root / "references" / "prompt-compiler.md"
            text = compiler.read_text(encoding="utf-8")
            text = text.replace("Before compilation", "After optional compilation")
            compiler.write_text(text, encoding="utf-8")
            errors: list[str] = []
            behavior.validate_directors_read_routes(root, errors)
            self.assertTrue(any("must require" in error for error in errors), errors)

    def test_canonical_read_has_every_required_field(self) -> None:
        text = (ROOT / CANONICAL).read_text(encoding="utf-8")
        for field in FIELDS:
            self.assertIn(f"`{field}`", text, field)

    def test_all_33_genre_examples_use_complete_canonical_records(self) -> None:
        self.assertEqual(len(behavior.GENRE_LIBRARY_LANES), 33)
        self.assertEqual(genre_library_errors(), [])

    def test_core_example_carries_the_chipped_plate_into_final_prompt(self) -> None:
        text = (ROOT / "references/directing-engine.md").read_text(encoding="utf-8")
        final_prompt = re.search(
            r"\*\*Final prompt sentence:\*\* `(?P<prompt>[^`]+)`",
            text,
        )

        self.assertIsNotNone(final_prompt)
        assert final_prompt is not None
        prompt = final_prompt.group("prompt").casefold()
        self.assertIn("chipped", prompt)
        self.assertIn("plate from their first flat", prompt)

    def test_contract_pins_narrative_boundary_and_compilation_boundary(self) -> None:
        text = (ROOT / CANONICAL).read_text(encoding="utf-8").lower()
        for phrase in (
            "narrative lane",
            "non-narrative lane",
            "do not fabricate",
            "internal planning only",
            "visible or audible carriers",
            "before prompt compilation",
            "does not guarantee byte-identical",
            "model-in-the-loop benchmark",
        ):
            self.assertIn(phrase, text, phrase)

    def test_fast_routes_cannot_escape_to_memory(self) -> None:
        for rel in NO_MEMORY_ESCAPE_FILES:
            text = (ROOT / rel).read_text(encoding="utf-8").lower()
            self.assertNotIn("inline from memory", text, rel)
            self.assertNotIn("apply craft from memory", text, rel)

    def test_adversarial_cases_pin_the_static_expected_lane_map(self) -> None:
        cases = json.loads(
            (ROOT / "validation/fixtures/directors-read-cases.json").read_text(
                encoding="utf-8"
            )
        )
        expected = {
            "silent-breakup": "narrative",
            "perfume-turntable": "non_narrative",
            "product-with-performer-choice": "narrative",
            "abstract-logo-reveal": "non_narrative",
            "dancer-masks-missed-cue": "narrative",
            "hands-only-assembly-demo": "non_narrative",
        }
        self.assertEqual(len(cases), len(expected))
        self.assertEqual({case["id"]: case["expected_lane"] for case in cases}, expected)
        for case in cases:
            if case["expected_lane"] == "narrative":
                read = case["directors_read"]
                self.assertEqual(tuple(read), FIELDS, case["id"])
                self.assertTrue(all(str(value).strip() for value in read.values()), case["id"])
                self.assertTrue(case["compiled_carriers"].strip(), case["id"])
                compiled = case["compiled_carriers"].lower()
                for field in FIELDS:
                    self.assertNotIn(f"{field.lower()}:", compiled, case["id"])
            else:
                self.assertIsNone(case["directors_read"], case["id"])
                self.assertTrue(case["utility_intent"].strip(), case["id"])
                self.assertIn("no invented", case["refusal"].lower(), case["id"])

    def test_generic_narrative_read_cannot_pass_on_presence_alone(self) -> None:
        cases = json.loads(
            (ROOT / "validation/fixtures/directors-read-cases.json").read_text(
                encoding="utf-8"
            )
        )
        generic = next(case for case in cases if case["id"] == "silent-breakup")
        generic["directors_read"] = {
            field: "Something happens."
            for field in FIELDS
        }
        generic["compiled_carriers"] = "The camera shows something happening."

        errors = directors_read_case_errors(cases)

        self.assertTrue(
            any(
                "creative specificity" in error
                or "reuses the same content" in error
                for error in errors
            ),
            errors,
        )

    def test_narrative_carriers_must_carry_behavior_and_specific_detail(self) -> None:
        cases = json.loads(
            (ROOT / "validation/fixtures/directors-read-cases.json").read_text(
                encoding="utf-8"
            )
        )
        generic = next(case for case in cases if case["id"] == "silent-breakup")
        generic["compiled_carriers"] = (
            "A locked camera observes an empty hallway while distant traffic continues."
        )

        errors = directors_read_case_errors(cases)

        self.assertTrue(
            any("visible suppressed behavior" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("non-transferable detail" in error for error in errors),
            errors,
        )

    def test_specificity_tokenizer_is_not_limited_to_space_delimited_english(self) -> None:
        for text in (
            "她把裂开的车票压在颤抖的拇指下面",
            "彼女は震える親指で破れた切符を隠す",
            "그녀는 떨리는 엄지로 찢어진 표를 가린다",
            "เธอซ่อนตั๋วขาดไว้ใต้นิ้วโป้งที่สั่น",
        ):
            with self.subTest(text=text):
                self.assertGreaterEqual(len(behavior.creative_terms(text)), 3)

    def test_default_ignorables_cannot_disguise_generic_filler(self) -> None:
        self.assertEqual(
            behavior.creative_terms("some\u034fthing hap\u2060pens"),
            set(),
        )

    def test_case_fixture_wrong_shapes_are_diagnostic_not_exceptions(self) -> None:
        original = json.loads(
            (ROOT / "validation/fixtures/directors-read-cases.json").read_text(
                encoding="utf-8"
            )
        )
        mutations = (
            ("unhashable id", "id", []),
            ("wrong brief type", "brief", {}),
            ("wrong carrier type", "compiled_carriers", ["visible", "words"]),
        )
        for label, field, value in mutations:
            cases = json.loads(json.dumps(original))
            cases[0][field] = value
            with self.subTest(label=label):
                self.assertTrue(directors_read_case_errors(cases))

    def test_specificity_check_ignores_invalid_carriers_after_type_diagnostic(self) -> None:
        fields = {
            field: f"specific authored choice number {index} with visible evidence"
            for index, field in enumerate(FIELDS)
        }

        errors = behavior.creative_specificity_errors(
            fields,
            ["valid visible carrier", {}],
            label="malformed carrier",
            carrier_fields=("visible suppressed behavior",),
        )

        self.assertIsInstance(errors, list)


if __name__ == "__main__":
    unittest.main()

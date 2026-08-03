"""The stress scorer must not invent defects.

Its first draft failed the repository's own golden prompts on dimensions they
had actually satisfied - an edit prompt that preserves the source lighting was
scored as having no lighting, and a continuation that binds to accepted footage
in prose was scored as having no reference binding. A checker that cries wolf
gets ignored, so the fairness rules are pinned here.
"""

from __future__ import annotations

import copy
import json
import re
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import prompt_architecture_stress as stress  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "examples" / "golden-prompts"
SCRIPT = ROOT / "scripts" / "prompt_architecture_stress.py"
CORPUS_PATH = ROOT / "evals" / "prompt-architecture-stress.json"

GOLDEN_MODES = {
    "compact-i2v": "I2V",
    "continuation-observed-deviation": "EXTEND",
    "dense-2d-storyboard": "T2V",
    "first-last-frame-transition": "FLF2V",
    "phased-single-take": "T2V",
    "r2v-role-isolation": "R2V",
    "sequence-continuation": "EXTEND",
    "video-edit-one-layer": "EDIT",
}


def compiled(path: Path) -> str:
    tail = path.read_text(encoding="utf-8").split("## Compiled Natural-Language Prompt", 1)[1]
    for marker in ("\n## Lint Result", "\n## Control-Critical Sentences"):
        if marker in tail:
            tail = tail.split(marker, 1)[0]
    return re.sub(r"\s+", " ", tail.strip().strip("`")).strip()


def source_brief(path: Path) -> str:
    tail = path.read_text(encoding="utf-8").split("## Source Brief", 1)[1]
    tail = tail.split("\n## Internal Prompt Specification", 1)[0]
    return re.sub(r"\s+", " ", tail.strip()).strip()


def shipped_corpus() -> list[dict]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def run_strict_corpus(records: list[dict]) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="architecture-gate-", dir=ROOT) as temp:
        corpus = Path(temp) / "corpus.json"
        corpus.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(corpus), "--strict"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )


class FalseGreenRegressionTests(unittest.TestCase):
    def test_ten_identical_busker_prompts_for_unrelated_briefs_fail(self) -> None:
        busker = next(r["prompt"] for r in shipped_corpus() if r["id"] == "b09-s")
        briefs = [
            "Woman reads a letter and receives bad news",
            "Night street food vendor",
            "Courier on a wet rooftop at night",
            "Man waits at a desert bus stop",
            "Child learns to ride a bike",
            "Surgeon scrubs in before an operation",
            "Barista pours latte art",
            "Lighthouse keeper during a storm",
            "Farmer inspects a drought-cracked field",
            "Boxer between rounds in the corner",
        ]
        records = [
            {
                "id": f"duplicate-{index:02d}",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": brief,
                "prompt": busker,
            }
            for index, brief in enumerate(briefs, start=1)
        ]

        result = run_strict_corpus(records)
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn("duplicate", output.lower())
        self.assertIn("brief_traceability", output)

    def test_explicitly_incompatible_camera_light_sound_and_action_fail(self) -> None:
        prompt = (
            "A courier walks across a warehouse and stops beside a red case. "
            "The camera stays locked off while it orbits the courier and pushes in "
            "while tracking left around her at the same time. Noon sunlight and "
            "moonlight and neon and candlelight are the only simultaneous light "
            "sources. Sound: absolute silence plays together with dialogue and music "
            "and room tone and thunder and footsteps. She remains completely still "
            "while continuing to walk forward. The final frame holds on her."
        )
        result = run_strict_corpus(
            [{
                "id": "contradiction-audit",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Courier carries a red case across a warehouse",
                "prompt": prompt,
            }]
        )
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn("coherence", output)
        for category in ("camera", "light", "sound", "action"):
            self.assertIn(category, output.lower())

    def test_meaningless_repeated_padding_cannot_score_perfect(self) -> None:
        prompt = (
            "Thing walks to a doorway and stops. Camera tracks the thing and settles "
            "on the final frame. A practical lamp lights the thing from frame left. "
            "Sound: footsteps and room tone. "
            + " ".join(["motion detail"] * 20)
        )
        result = run_strict_corpus(
            [{
                "id": "padding-audit",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Courier protects a fragile violin case on a flooded rooftop",
                "prompt": prompt,
            }]
        )
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn("repetition", output)
        self.assertIn("brief_traceability", output)

    def test_strict_rejects_one_subfloor_case_even_when_averages_pass(self) -> None:
        corpus = copy.deepcopy(shipped_corpus())
        target = next(r for r in corpus if r["id"] == "b02-s")
        target["prompt"] = (
            "A street vendor tosses noodles and stops at the burner. Camera locked, "
            "red neon, steel wok, low angle, wet pavement, night market, amber flame, "
            "room tone. The wok lands on the ring and the vendor holds the final pose "
            "under the practical shop light while distant traffic hums behind him."
        )
        self.assertLess(stress.score_prompt(target)["dims"]["structure"]["score"], 3)

        result = run_strict_corpus(corpus)
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn("b02-s", output)
        self.assertIn("structure", output)

    def test_cli_states_the_deterministic_gate_boundary(self) -> None:
        result = run_strict_corpus(shipped_corpus())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("does not judge creativity or originality", result.stdout)
        self.assertIn("blinded model evaluation", result.stdout)
        self.assertIn("native-language human review", result.stdout)


class AdversarialMutationTests(unittest.TestCase):
    def test_near_duplicate_with_one_subject_mutation_is_rejected(self) -> None:
        base = next(r["prompt"] for r in shipped_corpus() if r["id"] == "b09-s")
        mutated = base.replace("A busker", "A surgeon", 1)
        records = [
            {
                "id": "busker-case",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Subway busker plays to an empty platform",
                "prompt": base,
            },
            {
                "id": "surgery-case",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Surgeon scrubs in before an operation",
                "prompt": mutated,
            },
        ]
        findings = stress.corpus_duplicate_findings(records)
        self.assertTrue(any("near-duplicate" in finding for finding in findings), findings)

    def test_reordered_duplicate_clauses_are_rejected(self) -> None:
        base = next(r["prompt"] for r in shipped_corpus() if r["id"] == "b09-s")
        clauses = [part.strip() for part in base.split(".") if part.strip()]
        reordered = ". ".join(reversed(clauses)) + "."
        records = [
            {
                "id": "busker-order-a",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Subway busker plays to an empty platform",
                "prompt": base,
            },
            {
                "id": "rooftop-order-b",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Courier protects a parcel on a flooded rooftop",
                "prompt": reordered,
            },
        ]
        findings = stress.corpus_duplicate_findings(records)
        self.assertTrue(any("near-duplicate" in finding for finding in findings), findings)

    def test_opposite_action_swap_does_not_hide_a_reused_prompt_skeleton(self) -> None:
        records = [
            {
                "id": "airport-open",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Woman opens a red case at an airport gate",
                "prompt": "A courier opens the red case.",
            },
            {
                "id": "workshop-close",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Man closes a red case inside a flooded workshop",
                "prompt": "A courier closes the red case.",
            },
        ]
        similarity = stress.prompt_similarity(
            records[0]["prompt"], records[1]["prompt"]
        )
        self.assertLess(similarity, 0.92)
        findings = stress.corpus_duplicate_findings(records)
        self.assertTrue(any("opposite-action" in finding for finding in findings), findings)

        records[1]["prompt"] = "A courier slowly closed the red case."
        self.assertLess(
            stress.prompt_similarity(records[0]["prompt"], records[1]["prompt"]),
            0.92,
        )
        findings = stress.corpus_duplicate_findings(records)
        self.assertTrue(any("opposite-action" in finding for finding in findings), findings)

        for prompt in (
            "A courier softly closes the red case.",
            "The courier slowly quietly shuts the red case.",
        ):
            with self.subTest(prompt=prompt):
                records[1]["prompt"] = prompt
                findings = stress.corpus_duplicate_findings(records)
                self.assertTrue(
                    any("opposite-action" in finding for finding in findings),
                    findings,
                )

    def test_opposite_action_briefs_are_materially_different_for_duplicate_gate(self) -> None:
        prompt = "A courier handles the red case in the warehouse."
        records = [
            {
                "id": "case-open",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Courier opens the red case in the warehouse",
                "prompt": prompt,
            },
            {
                "id": "case-close",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Courier closes the red case in the warehouse",
                "prompt": prompt,
            },
        ]

        self.assertTrue(
            stress.materially_different_briefs(
                records[0]["brief"], records[1]["brief"]
            )
        )
        findings = stress.corpus_duplicate_findings(records)
        self.assertTrue(
            any("duplicate prompt" in finding for finding in findings),
            findings,
        )

    def test_small_requirement_swaps_are_materially_different_without_category_lists(self) -> None:
        prompt = "A courier opens a case in the warehouse and sets it on the bench."
        swaps = (
            ("red", "blue"),
            ("silk", "leather"),
            ("50mm", "85mm"),
            ("dawn", "midnight"),
        )
        for left_value, right_value in swaps:
            with self.subTest(left=left_value, right=right_value):
                left = f"Courier opens the {left_value} case in the warehouse"
                right = f"Courier opens the {right_value} case in the warehouse"
                self.assertTrue(stress.bounded_requirement_delta(left, right))
                self.assertTrue(stress.materially_different_briefs(left, right))
                findings = stress.corpus_duplicate_findings([
                    {
                        "id": "requirement-a",
                        "arm": "skill_formula",
                        "mode": "T2V",
                        "brief": left,
                        "prompt": prompt,
                    },
                    {
                        "id": "requirement-b",
                        "arm": "skill_formula",
                        "mode": "T2V",
                        "brief": right,
                        "prompt": prompt,
                    },
                ])
                self.assertTrue(any("duplicate prompt" in item for item in findings), findings)

        added_requirement = (
            "Courier opens the case in the warehouse",
            "Courier opens the red case in the warehouse",
        )
        self.assertTrue(stress.materially_different_briefs(*added_requirement))

        grammar_only = (
            "Courier opens a case in the warehouse",
            "The courier opens the case in the warehouse",
        )
        self.assertFalse(stress.materially_different_briefs(*grammar_only))

    def test_duplicate_prompt_for_the_same_brief_is_not_called_cross_case_drift(self) -> None:
        prompt = next(r["prompt"] for r in shipped_corpus() if r["id"] == "b09-s")
        records = [
            {
                "id": "take-a",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Subway busker plays to an empty platform",
                "prompt": prompt,
            },
            {
                "id": "take-b",
                "arm": "skill_formula",
                "mode": "T2V",
                "brief": "Subway busker plays to an empty platform",
                "prompt": prompt,
            },
        ]
        self.assertEqual(stress.corpus_duplicate_findings(records), [])

    def test_shipped_doctrine_prompts_are_not_near_duplicate_false_positives(self) -> None:
        self.assertEqual(stress.corpus_duplicate_findings(shipped_corpus()), [])

    def test_traceability_ignores_generic_production_words(self) -> None:
        generic = stress.score_brief_traceability(
            "Camera lighting sound reference clip",
            "Camera holds the reference clip with lighting and sound.",
        )
        self.assertLess(generic[0], 3.0, generic)

        brief = "Courier protects a fragile violin case on a flooded rooftop"
        traced = stress.score_brief_traceability(
            brief,
            "The courier braces the fragile violin case against the flooded rooftop parapet.",
        )
        drifted = stress.score_brief_traceability(
            brief,
            "The subject walks through a scene while camera, lighting and sound continue.",
        )
        self.assertGreaterEqual(traced[0], 3.0, traced)
        self.assertLess(drifted[0], 3.0, drifted)

    def test_semantic_trace_contracts_do_not_rescue_the_wrong_target(self) -> None:
        wrong_edit_layer = stress.score_brief_traceability(
            "Fix lighting in an otherwise good clip.",
            "Preserve the existing clip exactly. Change only the dialogue layer.",
        )
        wrong_transition_subject = stress.score_brief_traceability(
            "Move from one known product state to another.",
            "@Image1 is the first frame and @Image2 is the final visual target. "
            "Use a continuous transition to reveal a painted portrait.",
        )
        self.assertLess(wrong_edit_layer[0], 3.0, wrong_edit_layer)
        self.assertLess(wrong_transition_subject[0], 3.0, wrong_transition_subject)

    def test_structural_contracts_cannot_replace_target_evidence(self) -> None:
        brief = "Create a three-shot 2D animation of a surgeon."
        wrong = stress.score_brief_traceability(
            brief,
            "Create a three-shot 2D animation of a busker.",
        )
        correct = stress.score_brief_traceability(
            brief,
            "Storyboard three cuts in two-dimensional animation showing the surgeon.",
        )
        self.assertLess(wrong[0], 3.0, wrong)
        self.assertIn("surgeon", wrong[1])
        self.assertGreaterEqual(correct[0], 3.0, correct)

        secondary_attributes = stress.score_brief_traceability(
            "Create a three-shot 2D animation of an adult surgeon in a red coat.",
            "Create a three-shot 2D animation of an adult busker in a red coat.",
        )
        self.assertLess(secondary_attributes[0], 3.0, secondary_attributes)
        self.assertIn("surgeon", secondary_attributes[1])

    def test_target_extraction_keeps_a_head_noun_after_several_modifiers(self) -> None:
        brief = "Create a three-shot 2D animation of a masked emergency-room surgeon."
        wrong = stress.score_brief_traceability(
            brief,
            "Create a three-shot 2D animation of a masked emergency-room busker.",
        )
        correct = stress.score_brief_traceability(
            brief,
            "Create a three-shot 2D animation of a masked emergency-room surgeon.",
        )

        self.assertIn("surgeon", stress.explicit_target_requirements(brief))
        self.assertLess(wrong[0], 3.0, wrong)
        self.assertIn("surgeon", wrong[1])
        self.assertGreaterEqual(correct[0], 3.0, correct)

        bounded_grammar = (
            (
                "Create a three-shot 2D animation of a surgeon rather than a busker.",
                {"busker"},
            ),
            (
                "Create a three-shot 2D animation of a surgeon for a safety campaign.",
                {"safety", "campaign"},
            ),
        )
        for bounded_brief, excluded in bounded_grammar:
            with self.subTest(brief=bounded_brief):
                requirements = stress.explicit_target_requirements(bounded_brief)
                self.assertIn("surgeon", requirements)
                self.assertTrue(requirements.isdisjoint(excluded), requirements)
                score = stress.score_brief_traceability(
                    bounded_brief,
                    "Create a three-shot 2D animation showing a surgeon.",
                )
                self.assertGreaterEqual(score[0], 3.0, score)

        alternative_brief = (
            "Create a three-shot 2D animation of a surgeon or busker."
        )
        alternative_groups = stress.explicit_target_requirement_groups(
            alternative_brief
        )
        self.assertIn(frozenset({"surgeon"}), alternative_groups)
        self.assertIn(frozenset({"busker"}), alternative_groups)
        for valid_target in ("surgeon", "busker"):
            with self.subTest(valid_target=valid_target):
                score = stress.score_brief_traceability(
                    alternative_brief,
                    f"Create a three-shot 2D animation showing a {valid_target}.",
                )
                self.assertGreaterEqual(score[0], 3.0, score)
        alternative_wrong = stress.score_brief_traceability(
            alternative_brief,
            "Create a three-shot 2D animation showing a painter.",
        )
        self.assertLess(alternative_wrong[0], 3.0, alternative_wrong)
        excluded_alternative = stress.score_brief_traceability(
            "Create a three-shot 2D animation of a surgeon rather than a busker.",
            "Create a three-shot 2D animation showing a busker.",
        )
        self.assertLess(excluded_alternative[0], 3.0, excluded_alternative)

        long_modifiers = " ".join(
            f"field-unit-{number}" for number in range(1, 36)
        )
        long_target = f"a masked {long_modifiers} surgeon"
        long_brief = f"Create a three-shot 2D animation of {long_target}."
        self.assertGreater(len(long_target), 240)
        self.assertIn("surgeon", stress.explicit_target_requirements(long_brief))
        self.assertLessEqual(
            len(stress.explicit_target_requirements(long_brief)),
            stress.MAX_EXPLICIT_TARGET_REQUIREMENTS,
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(long_brief, long_brief)[0],
            3.0,
        )
        long_wrong = long_brief.replace("surgeon", "busker")
        self.assertLess(
            stress.score_brief_traceability(long_brief, long_wrong)[0],
            3.0,
        )

    def test_target_extraction_uses_production_grammar_not_the_first_of(self) -> None:
        brief = (
            "Create a three-shot 2D animation with a palette of cobalt blue, "
            "depicting a masked surgeon."
        )
        requirements = stress.explicit_target_requirements(brief)
        self.assertIn("surgeon", requirements)
        self.assertNotIn("cobalt", requirements)
        self.assertNotIn("blue", requirements)

        wrong = stress.score_brief_traceability(
            brief,
            "Create a three-shot 2D animation with a palette of cobalt blue, "
            "depicting a masked busker.",
        )
        correct = stress.score_brief_traceability(
            brief,
            "Storyboard three cuts in 2D, depicting a masked surgeon in cobalt blue.",
        )
        self.assertLess(wrong[0], 3.0, wrong)
        self.assertIn("surgeon", wrong[1])
        self.assertGreaterEqual(correct[0], 3.0, correct)

        later_production_target = (
            "Use a palette of cobalt blue for a three-shot animation of a surgeon."
        )
        self.assertEqual(
            stress.explicit_target_requirement_groups(later_production_target),
            (frozenset({"surgeon"}),),
        )
        self.assertEqual(
            stress.explicit_target_requirement_groups(
                "Document the palette of cobalt blue used on set."
            ),
            (),
        )

    def test_target_extraction_preserves_named_heads_alternatives_and_purpose(self) -> None:
        modifiers = " ".join(
            f"field-unit-{number}" for number in range(1, 36)
        )
        brief = (
            "Create a three-shot animation of a masked "
            f"{modifiers} surgeon named Mara."
        )
        requirements = stress.explicit_target_requirements(brief)
        self.assertIn("surgeon", requirements)
        self.assertIn("mara", requirements)
        self.assertLessEqual(
            len(requirements), stress.MAX_EXPLICIT_TARGET_REQUIREMENTS
        )
        wrong = stress.score_brief_traceability(
            brief, brief.replace("surgeon", "busker")
        )
        self.assertLess(wrong[0], 3.0, wrong)
        self.assertIn("surgeon", wrong[1])

        alternatives = "Create an animation of either surgeon or busker."
        groups = stress.explicit_target_requirement_groups(alternatives)
        self.assertEqual(
            groups,
            (frozenset({"surgeon"}), frozenset({"busker"})),
        )
        for target in ("surgeon", "busker"):
            with self.subTest(target=target):
                score = stress.score_brief_traceability(
                    alternatives, f"Create an animation showing a {target}."
                )
                self.assertGreaterEqual(score[0], 3.0, score)

        purpose = "Create an animation of a surgeon to promote hand safety."
        self.assertEqual(
            stress.explicit_target_requirement_groups(purpose),
            (frozenset({"surgeon"}),),
        )
        purpose_score = stress.score_brief_traceability(
            purpose, "Create an animation depicting a surgeon."
        )
        self.assertGreaterEqual(purpose_score[0], 3.0, purpose_score)

    def test_target_alternatives_inherit_shared_heads_and_attributes(self) -> None:
        cases = (
            (
                "Create an animation of a surgeon named Mara or Nia.",
                (
                    frozenset({"surgeon", "mara"}),
                    frozenset({"surgeon", "nia"}),
                ),
            ),
            (
                "Create an animation of a red emergency surgeon or nurse.",
                (
                    frozenset({"red", "emergency", "surgeon"}),
                    frozenset({"red", "emergency", "nurse"}),
                ),
            ),
            (
                "Create an animation of a masked surgeon or busker.",
                (
                    frozenset({"mask", "surgeon"}),
                    frozenset({"mask", "busker"}),
                ),
            ),
            (
                "Create an animation of a surgeon named Mara or a nurse named Nia.",
                (
                    frozenset({"surgeon", "mara"}),
                    frozenset({"nurse", "nia"}),
                ),
            ),
            (
                "Create an animation of a masked surgeon or a nurse.",
                (
                    frozenset({"mask", "surgeon"}),
                    frozenset({"nurse"}),
                ),
            ),
        )
        for brief, expected in cases:
            with self.subTest(brief=brief):
                self.assertEqual(
                    stress.explicit_target_requirement_groups(brief),
                    expected,
                )

        named = "Create an animation of a surgeon named Mara or Nia."
        for complete in (
            "Animate a surgeon named Mara.",
            "Animate a surgeon named Nia.",
        ):
            with self.subTest(complete=complete):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(named, complete)[0],
                    3.0,
                )
        missing_head = stress.score_brief_traceability(
            named, "Animate Nia standing alone."
        )
        self.assertLess(missing_head[0], 3.0, missing_head)

        shared_modifiers = (
            "Create an animation of a red emergency surgeon or nurse."
        )
        complete_nurse = stress.score_brief_traceability(
            shared_modifiers, "Animate a red emergency nurse."
        )
        plain_nurse = stress.score_brief_traceability(
            shared_modifiers, "Animate a nurse."
        )
        self.assertGreaterEqual(complete_nurse[0], 3.0, complete_nurse)
        self.assertLess(plain_nurse[0], 3.0, plain_nurse)

    def test_relational_object_alternatives_keep_subject_and_action(self) -> None:
        shared = (
            "Create an animation of a surgeon holding a red case or blue bag."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(shared),
            ((
                frozenset({"surgeon", "hold", "red", "case"}),
                frozenset({"surgeon", "hold", "blue", "bag"}),
            ),),
        )
        for complete in (
            "Animate a surgeon holding a red case.",
            "Animate a surgeon holding a blue bag.",
        ):
            with self.subTest(complete=complete):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(shared, complete)[0],
                    3.0,
                )
        for incomplete in (
            "Animate a surgeon beside a blue bag.",
            "Animate a nurse holding a blue bag.",
        ):
            with self.subTest(incomplete=incomplete):
                self.assertLess(
                    stress.score_brief_traceability(shared, incomplete)[0],
                    3.0,
                )

        full_subject_branches = (
            "Create an animation of a surgeon holding a red case or a nurse "
            "holding a blue bag."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(full_subject_branches),
            ((
                frozenset({"surgeon", "hold", "red", "case"}),
                frozenset({"nurse", "hold", "blue", "bag"}),
            ),),
        )

        three_objects = (
            "Create an animation of a surgeon holding a red case, blue bag, or "
            "green box."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(three_objects),
            ((
                frozenset({"surgeon", "hold", "red", "case"}),
                frozenset({"surgeon", "hold", "blue", "bag"}),
                frozenset({"surgeon", "hold", "green", "box"}),
            ),),
        )

    def test_target_evidence_must_be_affirmative_and_unquoted(self) -> None:
        brief = "Create an animation of a masked surgeon."
        invalid_prompts = (
            "Create an animation, but not a masked surgeon.",
            "Exclude the masked surgeon; animate a masked busker.",
            "Animate a masked busker rather than a surgeon.",
            'Animate a masked busker who says "masked surgeon".',
            "Animate a masked busker who says ‘surgeon’.",
        )
        for prompt in invalid_prompts:
            with self.subTest(prompt=prompt):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertLess(score[0], 3.0, score)
                self.assertIn("target changed", score[1])

        affirmative = (
            "Create an animation depicting a masked surgeon.",
            "Do not exclude the masked surgeon; animate her at the scrub sink.",
            "Animate not only a masked surgeon but also her instrument tray.",
            "Exclude the busker, animate a masked surgeon instead.",
        )
        for prompt in affirmative:
            with self.subTest(prompt=prompt):
                terms = stress.affirmative_trace_terms(prompt)
                self.assertTrue({"mask", "surgeon"}.issubset(terms), terms)
                score = stress.score_brief_traceability(brief, prompt)
                self.assertGreaterEqual(score[0], 3.0, score)

    def test_postpositive_exclusions_and_balanced_quotes_are_not_evidence(self) -> None:
        brief = "Create an animation of a masked surgeon."
        excluded = (
            "The masked surgeon is not shown; animate a masked busker.",
            "The masked surgeon never appears; animate a masked busker.",
            "The masked surgeon is absent; animate a masked busker.",
            "The masked surgeon is deliberately omitted; animate a masked busker.",
            "The masked surgeon is left out; animate a masked busker.",
            "Omit the masked surgeon and animate a masked busker.",
        )
        for prompt in excluded:
            with self.subTest(exclusion=prompt):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertLess(score[0], 3.0, score)

        quoted_forms = (
            ("«", "»"),
            ("„", "“"),
            ("「", "」"),
            ("『", "』"),
            ("《", "》"),
            ("〈", "〉"),
            ("〝", "〞"),
            ("‚", "‘"),
            ("‹", "›"),
            ("``", "``"),
            ("```", "```"),
            ("`", "`"),
        )
        for opener, closer in quoted_forms:
            with self.subTest(quote=f"{opener}{closer}"):
                prompt = (
                    "Animate a masked busker whose placard reads "
                    f"{opener}masked surgeon{closer}."
                )
                score = stress.score_brief_traceability(brief, prompt)
                self.assertLess(score[0], 3.0, score)

        later_affirmative = (
            "A masked surgeon is absent from the poster, but a masked surgeon "
            "enters the animation."
        )
        self.assertTrue(
            {"mask", "surgeon"}.issubset(
                stress.affirmative_trace_terms(later_affirmative)
            )
        )

        non_exclusion_compounds = (
            ("An absent-minded surgeon enters.", "surgeon"),
            ("A missing-link researcher enters.", "researcher"),
        )
        for prompt, expected in non_exclusion_compounds:
            with self.subTest(compound=prompt):
                self.assertIn(expected, stress.affirmative_trace_terms(prompt))

    def test_reference_descriptions_cannot_steal_mandatory_output_targets(self) -> None:
        brief = (
            "Use the reference image of a cobalt palette to create an animation "
            "of a masked surgeon."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(brief),
            ((frozenset({"mask", "surgeon"}),),),
        )
        correct = stress.score_brief_traceability(
            brief, "Create a three-shot animation depicting a masked surgeon."
        )
        asset_only = stress.score_brief_traceability(
            brief, "Show the cobalt palette from the reference image."
        )
        self.assertGreaterEqual(correct[0], 3.0, correct)
        self.assertLess(asset_only[0], 3.0, asset_only)
        self.assertIn("surgeon", asset_only[1])

        tagged_brief = (
            "@Image1 is an image of a cobalt palette. Generate an animation of "
            "a masked surgeon."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(tagged_brief),
            ((frozenset({"mask", "surgeon"}),),),
        )
        required_after_asset = (
            "A reference image of a cobalt palette precedes the required animation "
            "of a masked surgeon."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(required_after_asset),
            ((frozenset({"mask", "surgeon"}),),),
        )

        embedded_request_forms = (
            "Generate from the reference image of a cobalt palette an animation "
            "of a masked surgeon.",
            "Build from @Image1, which is an image of a cobalt palette, an "
            "animation of a masked surgeon.",
            "Produce using the source video of a cobalt palette a portrait of "
            "a masked surgeon.",
            "Use @Image1 (a reference image of a cobalt palette) to create an "
            "animation of a masked surgeon.",
            "Using the uploaded portrait of a cobalt busker, render a video of "
            "a masked surgeon.",
            "Use a reference image featuring a cobalt palette to create an "
            "animation featuring a masked surgeon.",
            "Reference portrait depicting a cobalt busker; create a shot "
            "depicting a masked surgeon.",
        )
        for embedded in embedded_request_forms:
            with self.subTest(embedded=embedded):
                self.assertEqual(
                    stress.explicit_target_requirement_clauses(embedded),
                    ((frozenset({"mask", "surgeon"}),),),
                )

        requested_reference_output = (
            "Create a reference image depicting a masked surgeon."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(requested_reference_output),
            ((frozenset({"mask", "surgeon"}),),),
        )

    def test_every_production_target_clause_is_mandatory(self) -> None:
        brief = (
            "Create an animation of either a masked surgeon or a masked nurse "
            "and a take of a red busker. Produce a portrait of Mara."
        )
        clauses = stress.explicit_target_requirement_clauses(brief)
        self.assertEqual(len(clauses), 3, clauses)
        self.assertEqual(
            clauses[0],
            (
                frozenset({"mask", "surgeon"}),
                frozenset({"mask", "nurse"}),
            ),
        )
        self.assertEqual(clauses[1], (frozenset({"red", "busker"}),))
        self.assertEqual(clauses[2], (frozenset({"mara"}),))

        complete_variants = (
            "Animate a masked surgeon, film a red busker, and portray Mara.",
            "Animate a masked nurse, film a red busker, and portray Mara.",
        )
        for prompt in complete_variants:
            with self.subTest(prompt=prompt):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertGreaterEqual(score[0], 3.0, score)

        incomplete = (
            "Animate a masked surgeon and portray Mara.",
            "Animate a masked surgeon and a red busker, but exclude Mara.",
            "Animate a masked surgeon and portray Mara; do not show the red busker.",
        )
        for prompt in incomplete:
            with self.subTest(prompt=prompt):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertLess(score[0], 3.0, score)

        comma_list = (
            "Create an animation of a surgeon, a take of a red busker."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(comma_list),
            (
                (frozenset({"surgeon"}),),
                (frozenset({"red", "busker"}),),
            ),
        )
        repeated_request = (
            "Create an animation of a surgeon, produce a take of a red busker."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(repeated_request),
            stress.explicit_target_requirement_clauses(comma_list),
        )

    def test_comma_listed_subjects_remain_individually_mandatory(self) -> None:
        brief = (
            "Create an animation of a masked surgeon, a red nurse, and a blue "
            "busker."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(brief),
            (
                (frozenset({"mask", "surgeon"}),),
                (frozenset({"red", "nurse"}),),
                (frozenset({"blue", "busker"}),),
            ),
        )
        complete = stress.score_brief_traceability(
            brief,
            "Animate a masked surgeon, a red nurse, and a blue busker.",
        )
        missing_middle = stress.score_brief_traceability(
            brief,
            "Animate a masked surgeon and a blue busker.",
        )
        self.assertGreaterEqual(complete[0], 3.0, complete)
        self.assertLess(missing_middle[0], 3.0, missing_middle)

        alternatives = (
            "Create an animation of either a surgeon, a nurse, or a busker."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(alternatives),
            ((
                frozenset({"surgeon"}),
                frozenset({"nurse"}),
                frozenset({"busker"}),
            ),),
        )
        location_control = (
            "Create an animation of a masked surgeon, in a red warehouse, "
            "opening a blue case."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(location_control),
            ((frozenset({"mask", "surgeon"}),),),
        )

        comma_only = (
            "Create an animation of a masked surgeon, red nurse, blue busker."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(comma_only),
            (
                (frozenset({"mask", "surgeon"}),),
                (frozenset({"red", "nurse"}),),
                (frozenset({"blue", "busker"}),),
            ),
        )
        no_oxford_comma = (
            "Create an animation of a masked surgeon, a red nurse and a blue "
            "busker."
        )
        no_oxford_score = stress.score_brief_traceability(
            no_oxford_comma,
            "Animate only a masked surgeon and a red nurse.",
        )
        self.assertLess(no_oxford_score[0], 3.0, no_oxford_score)

    def test_traceability_rejects_an_action_reversal_despite_shared_nouns(self) -> None:
        brief = "A courier opens the red case in the warehouse."
        reversed_prompt = stress.score_brief_traceability(
            brief,
            "The courier closes the red case in the warehouse.",
        )
        alias_reversal = stress.score_brief_traceability(
            brief,
            "The courier shuts the red case in the warehouse.",
        )
        negated_required_then_reversed = stress.score_brief_traceability(
            brief,
            "The courier does not open the red case and instead closes it in the warehouse.",
        )
        quoted_required_then_reversed = stress.score_brief_traceability(
            brief,
            'The courier closes the red case and says "open sesame" in the warehouse.',
        )
        required_on_wrong_object = stress.score_brief_traceability(
            brief,
            "The courier closes the red case, then opens the warehouse door.",
        )
        correct = stress.score_brief_traceability(
            brief,
            "The courier opens the red case in the warehouse.",
        )
        sequenced = stress.score_brief_traceability(
            brief,
            "The courier closes the empty case, then opens the red case in the warehouse.",
        )
        negated_opposite = stress.score_brief_traceability(
            brief,
            "The courier holds the red case in the warehouse; it is not closed and stays ajar.",
        )

        for score in (
            reversed_prompt,
            alias_reversal,
            negated_required_then_reversed,
            quoted_required_then_reversed,
            required_on_wrong_object,
        ):
            self.assertLess(score[0], 3.0, score)
            self.assertIn("reversed", score[1])
        self.assertGreaterEqual(correct[0], 3.0, correct)
        self.assertGreaterEqual(sequenced[0], 3.0, sequenced)
        self.assertNotIn("reversed", negated_opposite[1])
        self.assertEqual(
            stress.reversed_action_requirements(
                brief,
                'The courier says "Do not close it" beside the red case in the warehouse.',
            ),
            (),
        )
        unrelated_object = (
            "The courier carries the red case through the warehouse and closes the "
            "loading door."
        )
        self.assertEqual(
            stress.reversed_action_requirements(brief, unrelated_object),
            (),
        )
        self.assertEqual(
            stress.reversed_action_requirements(
                brief,
                "The courier closes it inside the warehouse.",
            ),
            (),
        )
        relative_brief = "A red case that opens when the alarm sounds."
        relative_reversal = "A red case that closes when the alarm sounds."
        self.assertIn(
            "open->close",
            stress.reversed_action_requirements(relative_brief, relative_reversal),
        )
        self.assertTrue(
            any(
                action == "close"
                for action, _, _, _, _ in stress.action_mentions(relative_reversal)
            )
        )
        plural_relative_brief = "Red cases that open at noon."
        plural_relative_reversal = "Red cases that close at noon."
        self.assertIn(
            "open->close",
            stress.reversed_action_requirements(
                plural_relative_brief,
                plural_relative_reversal,
            ),
        )
        finite_demonstratives = (
            ("This opens the red case.", "open"),
            ("Those close the loading doors.", "close"),
        )
        for clause, expected_action in finite_demonstratives:
            with self.subTest(clause=clause):
                self.assertTrue(
                    any(
                        action == expected_action
                        for action, _, _, _, _ in stress.action_mentions(clause)
                    ),
                    stress.action_mentions(clause),
                )
        self.assertIn(
            "open->close",
            stress.reversed_action_requirements(
                "This opens the red case.",
                "This closes the red case.",
            ),
        )
        self.assertIn(
            "close->open",
            stress.reversed_action_requirements(
                "Those close the loading doors.",
                "Those open the loading doors.",
            ),
        )
        attributive_controls = (
            "This open case remains on the bench.",
            "Those closed doors remain painted red.",
        )
        for clause in attributive_controls:
            with self.subTest(attributive=clause):
                self.assertEqual(stress.action_mentions(clause), ())

    def test_action_reversal_resolves_local_pronouns_by_object_head(self) -> None:
        opens_it = "A courier carries the red case, then opens it."
        reversal_variants = (
            "A courier carries the red case, then closes it.",
            "A courier carries the red case, then closes the red case.",
            "A courier carries the red case. Then the courier closes it.",
        )
        self.assertEqual(stress.action_mentions(opens_it)[0][4], ("red", "case"))
        for prompt in reversal_variants:
            with self.subTest(prompt=prompt):
                self.assertIn(
                    "open->close",
                    stress.reversed_action_requirements(opens_it, prompt),
                )

        closes_it = "A courier carries the red case, then closes it."
        self.assertIn(
            "close->open",
            stress.reversed_action_requirements(
                closes_it,
                "A courier carries the red case, then opens the red case.",
            ),
        )

        unrelated_objects = (
            "A courier carries the red door, then closes it.",
            "A courier carries the red case, then closes the red door.",
            "A courier closes it without identifying any earlier object.",
        )
        for prompt in unrelated_objects:
            with self.subTest(prompt=prompt):
                self.assertEqual(
                    stress.reversed_action_requirements(opens_it, prompt),
                    (),
                )

        multi_object_brief = (
            "A courier opens the red case, then closes the blue door."
        )
        self.assertIn(
            "open->close",
            stress.reversed_action_requirements(
                multi_object_brief,
                "A courier closes the red case, then closes the blue door.",
            ),
        )
        self.assertEqual(
            stress.reversed_action_requirements(
                multi_object_brief,
                "A courier opens the red case, then closes the blue door.",
            ),
            (),
        )

    def test_action_reversal_supports_close_aliases_without_noun_collisions(self) -> None:
        brief = "A courier opens the red case."
        for alias in ("seals", "latches", "shuts"):
            with self.subTest(alias=alias):
                prompt = f"A courier {alias} the red case."
                self.assertIn(
                    "open->close",
                    stress.reversed_action_requirements(brief, prompt),
                )

        self.assertIn(
            "close->open",
            stress.reversed_action_requirements(
                "A courier seals the red case.",
                "A courier unlatches the red case.",
            ),
        )
        self.assertEqual(
            stress.reversed_action_requirements(
                brief, "A courier closes the red door."
            ),
            (),
        )

        noun_and_attribute_controls = (
            "A harbor seal rests beside the red case.",
            "Harbor seals swim beside the pier.",
            "A brass door latch opens beside the wall.",
            "The brass door latches fail in winter.",
            "A hermetically sealed case rests on the bench.",
        )
        for clause in noun_and_attribute_controls:
            with self.subTest(clause=clause):
                self.assertFalse(
                    any(
                        action == "close"
                        for action, _, _, _, _ in stress.action_mentions(clause)
                    ),
                    stress.action_mentions(clause),
                )

        negated_and_quoted = (
            "The courier does not seal the red case.",
            'The courier says "seal the red case".',
        )
        for prompt in negated_and_quoted:
            with self.subTest(prompt=prompt):
                self.assertEqual(
                    stress.reversed_action_requirements(brief, prompt),
                    (),
                )

    def test_action_negation_covers_inability_and_refusal_forms(self) -> None:
        brief = "A courier opens the red case."
        negative_forms = (
            "cannot open",
            "can't open",
            "couldn't open",
            "won't open",
            "fails to open",
            "failed to open",
            "refuses to open",
            "refused to open",
            "is unable to open",
            "isn't able to open",
        )
        for phrase in negative_forms:
            with self.subTest(phrase=phrase):
                prompt = (
                    f"A courier {phrase} the red case and instead closes the red case."
                )
                mentions = stress.action_mentions(prompt)
                self.assertTrue(
                    any(
                        action == "open" and not positive
                        for action, _, _, positive, _ in mentions
                    ),
                    mentions,
                )
                self.assertIn(
                    "open->close",
                    stress.reversed_action_requirements(brief, prompt),
                )

        positive_control = (
            "A courier not only opens the red case but also closes a blue case."
        )
        self.assertEqual(
            stress.reversed_action_requirements(brief, positive_control),
            (),
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(brief, positive_control)[0],
            3.0,
        )
        for guaranteed in (
            "A courier never fails to open the red case.",
            "A courier cannot fail to open the red case.",
        ):
            with self.subTest(guaranteed=guaranteed):
                self.assertTrue(stress.action_mentions(guaranteed)[0][3])

    def test_action_negation_ends_before_a_later_finite_positive_event(self) -> None:
        brief = "A courier opens the red case."
        negative_prefixes = (
            "cannot open",
            "can't open",
            "fails to open",
            "refuses to open",
            "is unable to open",
            "is denied permission to open",
            "is denied opening",
            "is forbidden from opening",
            "is prevented from opening",
        )
        for prefix in negative_prefixes:
            with self.subTest(prefix=prefix):
                prompt = f"A courier {prefix} the red case and closes it."
                mentions = stress.action_mentions(prompt)
                self.assertTrue(
                    any(
                        action == "open" and not positive
                        for action, _, _, positive, _ in mentions
                    ),
                    mentions,
                )
                self.assertTrue(
                    any(
                        action == "close" and positive
                        for action, _, _, positive, _ in mentions
                    ),
                    mentions,
                )
                self.assertIn(
                    "open->close",
                    stress.reversed_action_requirements(brief, prompt),
                )

        shared_scope = (
            "A courier cannot open or close the red case.",
            "A courier cannot open and close the red case.",
            "A courier proceeds without opening or closing the red case.",
            "The red case cannot be opened or closed.",
            "A courier cannot open the case and carefully close it.",
        )
        for prompt in shared_scope:
            with self.subTest(shared_scope=prompt):
                mentions = stress.action_mentions(prompt)
                self.assertTrue(mentions, prompt)
                self.assertTrue(
                    all(not positive for _, _, _, positive, _ in mentions),
                    mentions,
                )

        finite_resets = (
            "The case cannot be opened and is closed by a courier.",
            "A courier cannot open the case and will close it.",
            "A courier cannot open the case and does close it.",
            "A courier cannot open the case and workers close it.",
        )
        for prompt in finite_resets:
            with self.subTest(finite_reset=prompt):
                mentions = stress.action_mentions(prompt)
                self.assertTrue(
                    any(
                        action == "close" and positive
                        for action, _, _, positive, _ in mentions
                    ),
                    mentions,
                )

    def test_every_positive_brief_action_must_survive_on_its_object(self) -> None:
        brief = "A courier opens the red case in the warehouse."
        substitutions = (
            "A courier carries the red case in the warehouse.",
            "A courier looks at the red case in the warehouse.",
            "The red case remains untouched in the warehouse.",
            "A courier is denied opening the red case in the warehouse.",
            "A courier is forbidden from opening the red case in the warehouse.",
            "A courier tries to open the red case in the warehouse.",
            "A courier refuses opening the red case in the warehouse.",
            "A courier might open the red case in the warehouse.",
            "Opening the red case is denied in the warehouse.",
            "Opening the red case is not allowed in the warehouse.",
        )
        for prompt in substitutions:
            with self.subTest(prompt=prompt):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertEqual(score[0], 0.0, score)
                self.assertIn("positive action missing", score[1])

        supplied = stress.score_brief_traceability(
            brief,
            "In the warehouse, a courier carefully opens the bright red case.",
        )
        self.assertGreaterEqual(supplied[0], 3.0, supplied)

        polite_imperatives = (
            "Could you open the red case in the warehouse?",
            "Would you open the red case in the warehouse?",
        )
        for prompt in polite_imperatives:
            with self.subTest(polite=prompt):
                mentions = stress.action_mentions(prompt)
                self.assertTrue(mentions and mentions[0][3], mentions)
                self.assertEqual(
                    stress.missing_positive_action_requirements(brief, prompt),
                    (),
                )

    def test_action_shaped_nouns_and_states_do_not_create_requirements(self) -> None:
        controls = (
            "Man waits at a desert bus stop",
            "Closed door to open doorway transition",
            "Opening scene at a bus stop",
            "A sealed case rests on the bench.",
            "The glass door is open.",
        )
        for brief in controls:
            with self.subTest(brief=brief):
                self.assertEqual(stress.action_mentions(brief), ())

        predicates = (
            "Open the red case.",
            "Please open the red case.",
            "Couriers open red cases.",
            "The red case opened suddenly.",
            "The courier stopped the cart.",
            "The courier raised the flag.",
            "The courier arrived at the station.",
            "Closed doors open.",
        )
        for brief in predicates:
            with self.subTest(brief=brief):
                self.assertTrue(stress.action_mentions(brief), brief)

        self.assertTrue(
            stress.missing_positive_action_requirements(
                "The red door opens.",
                "The blue case opens.",
            )
        )
        self.assertFalse(
            stress.missing_positive_action_requirements(
                "The red door opens.",
                "The bright red door opens.",
            )
        )

    def test_action_objects_require_requested_discriminative_modifiers(self) -> None:
        brief = "A courier opens the red case."
        wrong_object_actions = (
            "A courier opens the blue case, then closes the red case.",
            "A courier opens the case, then closes the red case.",
            "A courier carries the blue case, opens it, then closes the red case.",
        )
        for prompt in wrong_object_actions:
            with self.subTest(prompt=prompt):
                self.assertIn(
                    "open->close",
                    stress.reversed_action_requirements(brief, prompt),
                )

        correct = (
            "A courier opens the bright red case, then closes a blue case."
        )
        self.assertEqual(stress.reversed_action_requirements(brief, correct), ())
        self.assertEqual(
            stress.reversed_action_requirements(
                brief, "A courier opens the red case and closes the red door."
            ),
            (),
        )
        long_red_object = (
            "A courier opens the red armored reinforced emergency transport case."
        )
        long_blue_reversal = (
            "A courier opens the blue armored reinforced emergency transport case, "
            "then closes the red armored reinforced emergency transport case."
        )
        self.assertIn(
            "open->close",
            stress.reversed_action_requirements(long_red_object, long_blue_reversal),
        )

    def test_postnominal_descriptors_preserve_the_object_head(self) -> None:
        cases = (
            (
                "A courier opens the case painted red.",
                "A courier closes the case painted red.",
                {"red", "case"},
            ),
            (
                "A courier opens the case marked red.",
                "A courier closes the case marked red.",
                {"red", "case"},
            ),
            (
                "A courier opens the case with a red stripe.",
                "A courier closes the case with a red stripe.",
                {"red", "stripe", "case"},
            ),
            (
                "A courier opens case number seven.",
                "A courier closes case number seven.",
                {"seven", "case"},
            ),
            (
                "A courier opens the case bearing a red stripe.",
                "A courier closes the case bearing a red stripe.",
                {"red", "stripe", "case"},
            ),
            (
                "A courier opens a case labeled SEVEN.",
                "A courier closes a case labeled SEVEN.",
                {"seven", "case"},
            ),
            (
                "A courier opens the case that is painted red.",
                "A courier closes the case that is painted red.",
                {"red", "case"},
            ),
            (
                "A courier opens the case which bears a red stripe.",
                "A courier closes the case which bears a red stripe.",
                {"red", "stripe", "case"},
            ),
        )
        for brief, reversal, expected_terms in cases:
            with self.subTest(brief=brief):
                identity = stress.action_mentions(brief)[0][4]
                self.assertEqual(identity[-1], "case", identity)
                self.assertTrue(expected_terms.issubset(identity), identity)
                self.assertIn(
                    "open->close",
                    stress.reversed_action_requirements(brief, reversal),
                )

        descriptor_mismatches = (
            (
                "A courier opens the case painted red.",
                "A courier opens the case painted blue.",
            ),
            (
                "A courier opens the case with a red stripe.",
                "A courier opens the case with a blue stripe.",
            ),
            (
                "A courier opens case number seven.",
                "A courier opens case number eight.",
            ),
        )
        for brief, prompt in descriptor_mismatches:
            with self.subTest(prompt=prompt):
                self.assertTrue(
                    stress.missing_positive_action_requirements(brief, prompt)
                )

    def test_sequencing_cues_separate_phases_but_while_creates_conflicts(self) -> None:
        safe = " ".join([
            "Camera stays locked off, then pushes in.",
            "The only light changes from sunlight to moonlight.",
            "Sound: room tone, then silence.",
            "She stops moving, then continues to walk.",
        ])
        self.assertEqual(stress.contradiction_findings(safe), [])

        conflicting = " ".join([
            "Camera stays locked off while it pushes in.",
            "The only simultaneous light sources are sunlight and moonlight.",
            "Sound: room tone with absolute silence at the same time.",
            "She stops moving while continuing to walk.",
        ])
        findings = stress.contradiction_findings(conflicting)
        for category in ("camera:", "light:", "sound:", "action:"):
            self.assertTrue(any(category in finding for finding in findings), findings)

    def test_unrelated_later_then_does_not_hide_a_camera_conflict(self) -> None:
        prompt = (
            "Camera stays locked off while orbiting and pushing in around the courier, "
            "then the courier sets the parcel down."
        )
        findings = stress.contradiction_findings(prompt)
        self.assertTrue(any(finding.startswith("camera:") for finding in findings), findings)

    def test_sequence_cue_must_bind_the_conflicting_camera_directives(self) -> None:
        bound = "Camera stays locked off, then the camera pushes in."
        self.assertFalse(
            any(
                finding.startswith("camera:")
                for finding in stress.contradiction_findings(bound)
            )
        )

        sentence_boundaries = (
            "Camera stays locked off. Then the camera pushes in.",
            "Camera stays locked off. Then, the camera pushes in.",
            "Camera stays locked off. Next. Camera pushes in.",
            "Camera stays locked off. Next—camera pushes in.",
            "Camera stays locked off! Next the camera pushes in.",
            "Camera stays locked off! Next, camera pushes in.",
            "Camera stays locked off? Finally the camera pushes in.",
            "Camera stays locked off. In the next beat, camera pushes in.",
            "Camera stays locked off. In the next beat—camera pushes in.",
            "Camera stays locked off。 Then, camera pushes in.",
        )
        for prompt in sentence_boundaries:
            with self.subTest(prompt=prompt):
                self.assertFalse(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.contradiction_findings(prompt)
                    )
                )

        no_phase_cue = "Camera stays locked off. The camera pushes in."
        self.assertTrue(
            any(
                finding.startswith("camera:")
                for finding in stress.contradiction_findings(no_phase_cue)
            )
        )

        cue_false_positives = (
            "Camera stays locked off. The next camera pushes in.",
            "Camera stays locked off. Next-generation camera pushes in.",
            "Camera stays locked off. The slate reads ‘Next.’ Camera pushes in.",
            "Camera stays locked off. Next. The courier checks the latch. Camera pushes in.",
        )
        for prompt in cue_false_positives:
            with self.subTest(false_positive=prompt):
                self.assertTrue(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.contradiction_findings(prompt)
                    ),
                    stress.contradiction_findings(prompt),
                )

        shot_boundaries = (
            "Camera stays locked off. Next shot, camera pushes in.",
            "Camera stays locked off. Shot 2: camera pushes in.",
            "Camera stays locked off. Cut to camera pushing in.",
            "Camera stays locked off. Second shot, camera pushes in.",
            "Camera stays locked off. Shot two: camera pushes in.",
            "Camera stays locked off. In second shot, camera pushes in.",
            "Camera stays locked off. Next scene, camera pushes in.",
            "Camera stays locked off. Scene 2: camera pushes in.",
            "Camera stays locked off. Cut. Camera pushes in.",
            "Camera stays locked off. Following shot, camera pushes in.",
            "Camera stays locked off. Take 2: camera pushes in.",
        )
        for prompt in shot_boundaries:
            with self.subTest(shot_boundary=prompt):
                self.assertFalse(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.contradiction_findings(prompt)
                    ),
                    stress.contradiction_findings(prompt),
                )

        simultaneous_controls = (
            "Next shot, camera stays locked off while camera pushes in.",
            "Second shot, camera stays locked off while camera pushes in.",
            "Camera stays locked off while camera pushes in. Next shot, the courier exits.",
            "Camera stays locked off. Next shot, camera pushes in at the same time.",
            "Camera stays locked off. The next shot glass sits beside camera pushing in.",
            "Camera stays locked off. The second shot glass sits beside camera pushing in.",
            "Camera stays locked off. Scene 2 camera pushes in at the same time.",
            'Camera stays locked off as the editor says "Cut to" before camera pushes in.',
            'Camera stays locked off as the editor says "Cut." before camera pushes in.',
        )
        for prompt in simultaneous_controls:
            with self.subTest(simultaneous_control=prompt):
                self.assertTrue(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.contradiction_findings(prompt)
                    ),
                    stress.contradiction_findings(prompt),
                )

        unrelated = (
            "Camera stays locked off as the courier then checks the latch before "
            "the camera pushes in."
        )
        findings = stress.contradiction_findings(unrelated)
        self.assertTrue(any(finding.startswith("camera:") for finding in findings), findings)

        trailing_simultaneity = (
            "Camera stays locked off, then the camera pushes in at the same time."
        )
        findings = stress.contradiction_findings(trailing_simultaneity)
        self.assertTrue(any(finding.startswith("camera:") for finding in findings), findings)

        event_transitions = (
            "Camera stays locked off until the latch clicks, then the camera pushes in.",
            "Camera stays locked off until the latch clicks. The camera pushes in.",
        )
        for prompt in event_transitions:
            with self.subTest(prompt=prompt):
                self.assertFalse(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.contradiction_findings(prompt)
                    )
                )

        simultaneous_synonyms = (
            "Camera pushes in. Meanwhile, the camera pulls out.",
            "Camera pushes in and the camera pulls out together.",
            "Camera pushes in and the camera pulls out concurrently.",
            "Camera pushes in and the camera pulls out at once.",
        )
        for prompt in simultaneous_synonyms:
            with self.subTest(prompt=prompt):
                findings = stress.contradiction_findings(prompt)
                self.assertTrue(
                    any(finding.startswith("camera:") for finding in findings),
                    findings,
                )

        unrelated_simultaneity = (
            "Camera stays locked off while the actor waits, then the camera pushes in.",
            (
                "Camera stays locked off as the siblings stand together, then the "
                "camera pushes in."
            ),
            (
                "Camera stays locked off, then the camera pushes in as the siblings "
                "stand together."
            ),
            (
                "Camera stays locked off, then the camera pushes in concurrently "
                "with the music."
            ),
            (
                "Camera stays locked off while the actor waits. Meanwhile, she opens "
                "the case; then the camera pushes in."
            ),
        )
        for prompt in unrelated_simultaneity:
            with self.subTest(prompt=prompt):
                self.assertFalse(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.contradiction_findings(prompt)
                    )
                )

        pair_local = (
            "Camera stays locked off, then the camera pushes in. Meanwhile, "
            "the camera pulls out."
        )
        findings = stress.contradiction_findings(pair_local)
        self.assertTrue(any(finding.startswith("camera:") for finding in findings), findings)

    def test_each_conflicting_pair_needs_its_own_sequence_boundary(self) -> None:
        masked = (
            "Camera orbits, then camera pushes in during the static framing."
        )
        findings = stress.contradiction_findings(masked)
        self.assertTrue(any(finding.startswith("camera:") for finding in findings), findings)

        fully_phased = (
            "Camera orbits, then camera pushes in, then static framing holds."
        )
        self.assertFalse(
            any(
                finding.startswith("camera:")
                for finding in stress.contradiction_findings(fully_phased)
            )
        )

        sound_masked = (
            "Sound: room tone, then absolute silence with rain at the same time."
        )
        findings = stress.contradiction_findings(sound_masked)
        self.assertTrue(any(finding.startswith("sound:") for finding in findings), findings)

    def test_quoted_silence_words_are_dialogue_not_audio_directives(self) -> None:
        valid_dialogue = (
            'The actor says "No sound?" Sound: room tone and rain.',
            "The actor says 'silence, please.' Sound: room tone and rain.",
            "The actor says \u201cAbsolute silence?\u201d Sound: room tone and rain.",
            "The actor says \u2018No sound?\u2019 Sound: room tone and rain.",
        )
        for prompt in valid_dialogue:
            with self.subTest(prompt=prompt):
                self.assertFalse(
                    any(
                        finding.startswith("sound:")
                        for finding in stress.contradiction_findings(prompt)
                    ),
                    stress.contradiction_findings(prompt),
                )

        actual_directive = (
            'The actor says "No sound?" Sound: room tone and absolute silence '
            "at the same time."
        )
        findings = stress.contradiction_findings(actual_directive)
        self.assertTrue(any(finding.startswith("sound:") for finding in findings), findings)

    def test_reference_exclusions_do_not_count_as_positive_lighting(self) -> None:
        prompts = (
            "The sole light is sunlight; ignore neon lighting from @Image1.",
            "The sole light is sunlight; exclude moonlight from the source clip.",
            (
                "The sole light is sunlight; do not transfer the reference's wardrobe, "
                "face, texture, colour palette, exposure pattern, reflected spill, or "
                "neon lighting source."
            ),
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                families = stress.positive_families(
                    prompt, stress.LIGHT_SOURCE_FAMILIES
                )
                self.assertEqual(families, {"sun"})
                self.assertFalse(
                    any(
                        finding.startswith("light:")
                        for finding in stress.contradiction_findings(prompt)
                    )
                )

        contrast = "Ignore the source identity, but keep its neon lighting."
        self.assertIn(
            "neon",
            stress.positive_families(contrast, stress.LIGHT_SOURCE_FAMILIES),
        )

        reset = (
            "Do not transfer the face and costume, and use neon lighting as the "
            "sole source. Moonlight also lights the subject at the same time."
        )
        self.assertEqual(
            stress.positive_families(reset, stress.LIGHT_SOURCE_FAMILIES),
            {"moon", "neon"},
        )
        self.assertTrue(
            any(
                finding.startswith("light:")
                for finding in stress.contradiction_findings(reset)
            )
        )

        contrastive_negation = "No sunlight but neon lights the subject."
        self.assertEqual(
            stress.positive_families(
                contrastive_negation, stress.LIGHT_SOURCE_FAMILIES
            ),
            {"neon"},
        )

        double_negation = "Do not exclude neon lighting."
        self.assertIn(
            "neon",
            stress.positive_families(double_negation, stress.LIGHT_SOURCE_FAMILIES),
        )

        for prompt in (
            "Don't ignore neon lighting.",
            "Doesn't exclude neon lighting.",
            "Mustn't ignore neon lighting.",
        ):
            with self.subTest(prompt=prompt):
                self.assertIn(
                    "neon",
                    stress.positive_families(prompt, stress.LIGHT_SOURCE_FAMILIES),
                )

        dialogue = 'The actor says "ignore the warning," as neon lighting comes on.'
        self.assertIn(
            "neon",
            stress.positive_families(dialogue, stress.LIGHT_SOURCE_FAMILIES),
        )

        single_quoted_dialogue = (
            "The actor says 'ignore the luggage' as neon lighting comes on."
        )
        self.assertIn(
            "neon",
            stress.positive_families(
                single_quoted_dialogue, stress.LIGHT_SOURCE_FAMILIES
            ),
        )

        for prompt in (
            "The directors' instruction is to ignore neon lighting.",
            "At 6' wide, ignore neon lighting from the reference.",
        ):
            with self.subTest(prompt=prompt):
                self.assertNotIn(
                    "neon",
                    stress.positive_families(prompt, stress.LIGHT_SOURCE_FAMILIES),
                )

        noun_phrase = (
            "The sole light is sunlight; ignore the reference identity and use "
            "of neon lighting."
        )
        self.assertEqual(
            stress.positive_families(noun_phrase, stress.LIGHT_SOURCE_FAMILIES),
            {"sun"},
        )

        for prompt in (
            "Ignore wardrobe: use neon lighting as the sole source. Moonlight also lights.",
            "Ignore wardrobe then use neon lighting as the sole source. Moonlight also lights.",
            (
                "Ignore wardrobe and light the subject with neon as the sole source. "
                "Moonlight also lights."
            ),
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(
                    stress.positive_families(prompt, stress.LIGHT_SOURCE_FAMILIES),
                    {"moon", "neon"},
                )
                self.assertTrue(
                    any(
                        finding.startswith("light:")
                        for finding in stress.contradiction_findings(prompt)
                    )
                )

    def test_subject_motion_verbs_are_not_mistaken_for_camera_moves(self) -> None:
        prompts = (
            "The camera remains locked off while the dancer orbits the table and tilts her head.",
            "Keep a static camera as the dog tracks a lantern and follows its handler.",
            "The locked-off shot holds while the sports car zooms past two copper pans.",
            "Camera stays locked while a heron cranes its neck and the actor pulls back a chair.",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                findings = stress.contradiction_findings(prompt)
                self.assertFalse(
                    any(finding.startswith("camera:") for finding in findings),
                    findings,
                )

    def test_sentence_breaks_do_not_hide_unphased_conflicts(self) -> None:
        prompt = " ".join([
            "Camera stays locked off.",
            "The camera orbits the courier at the same time.",
            "The only light source is sunlight.",
            "Moonlight also lights her at the same time.",
            "Sound begins with room tone.",
            "Absolute silence plays at the same time.",
            "She stops moving.",
            "She continues to walk at the same time.",
        ])
        findings = stress.contradiction_findings(prompt)
        for category in ("camera:", "light:", "sound:", "action:"):
            self.assertTrue(any(category in finding for finding in findings), findings)

    def test_no_added_music_does_not_conflict_with_preserved_audio(self) -> None:
        prompt = "Sound: keep the original audio bed unchanged, with no added music."
        self.assertEqual(stress.contradiction_findings(prompt), [])

        mutated = prompt.replace("no added music", "add new music")
        self.assertTrue(
            any("preserve-source-audio" in finding for finding in stress.contradiction_findings(mutated))
        )

    def test_repeated_phrase_padding_flips_the_repetition_dimension(self) -> None:
        clean = (
            "A courier crosses the workshop and sets a violin case on the bench. "
            "Camera tracks once and settles. Window light holds. Sound: rain and one latch click."
        )
        padded = clean + " " + " ".join(["motion detail"] * 12)
        self.assertGreaterEqual(stress.score_repetition(clean)[0], 3.0)
        self.assertLess(stress.score_repetition(padded)[0], 3.0)

    def test_second_pass_shared_suffix_and_age_aliases_keep_the_entity_head(self) -> None:
        cases = (
            (
                "Create an animation of a red or blue emergency surgeon.",
                (
                    frozenset({"red", "emergency", "surgeon"}),
                    frozenset({"blue", "emergency", "surgeon"}),
                ),
            ),
            (
                "Create an animation of a red or blue case.",
                (
                    frozenset({"red", "case"}),
                    frozenset({"blue", "case"}),
                ),
            ),
        )
        for brief, expected in cases:
            with self.subTest(brief=brief):
                self.assertEqual(
                    stress.explicit_target_requirement_groups(brief), expected
                )

        age_brief = "Create an animation of an elderly surgeon."
        older = stress.score_brief_traceability(
            age_brief, "Animate an older surgeon entering the theatre."
        )
        wrong_head = stress.score_brief_traceability(
            age_brief, "Animate an elderly busker entering the theatre."
        )
        self.assertGreaterEqual(older[0], 3.0, older)
        self.assertLess(wrong_head[0], 3.0, wrong_head)

    def test_second_pass_action_polarity_requires_a_completed_positive_event(self) -> None:
        brief = "A courier opens the red case."
        non_events = (
            "A courier is prohibited from opening the red case.",
            "A courier is barred from opening the red case.",
            "A courier declines to open the red case.",
            "A courier avoids opening the red case.",
            "A courier pretends to open the red case.",
            "A courier mimes opening the red case.",
            "A courier rehearses opening the red case.",
            "A courier hopes to open the red case.",
            "The red case looks open beside the courier.",
            "A courier neither opens nor closes the red case.",
        )
        for prompt in non_events:
            with self.subTest(prompt=prompt):
                self.assertTrue(
                    stress.missing_positive_action_requirements(brief, prompt),
                    stress.action_mentions(prompt),
                )

        for unavoidable in (
            "A courier cannot refuse to open the red case.",
            "A courier cannot avoid opening the red case.",
        ):
            with self.subTest(unavoidable=unavoidable):
                self.assertEqual(
                    stress.missing_positive_action_requirements(brief, unavoidable),
                    (),
                )

    def test_second_pass_postpositive_exclusion_targets_completed_absence(self) -> None:
        brief = "Create an animation of a masked surgeon."
        absent = stress.score_brief_traceability(
            brief, "The masked surgeon never arrives; animate a masked busker."
        )
        missing_glove = stress.score_brief_traceability(
            brief, "A masked surgeon missing a glove enters the animation."
        )
        frightened = stress.score_brief_traceability(
            brief,
            "A masked surgeon never appears frightened but enters the animation.",
        )
        self.assertLess(absent[0], 3.0, absent)
        self.assertGreaterEqual(missing_glove[0], 3.0, missing_glove)
        self.assertGreaterEqual(frightened[0], 3.0, frightened)

    def test_second_pass_directional_sources_do_not_become_outputs(self) -> None:
        forms = (
            "Use a video of a cobalt palette as a source for an animation of a masked surgeon.",
            "Use an image of a cobalt palette as the reference for a video of a masked surgeon.",
            "A video of a cobalt palette serves as an input for an animation of a masked surgeon.",
            "An image of a cobalt palette is used as a source for a portrait of a masked surgeon.",
        )
        expected = ((frozenset({"mask", "surgeon"}),),)
        for brief in forms:
            with self.subTest(brief=brief):
                self.assertEqual(
                    stress.explicit_target_requirement_clauses(brief), expected
                )

        requested_reference = "Create a reference image of a masked surgeon."
        self.assertEqual(
            stress.explicit_target_requirement_clauses(requested_reference), expected
        )

    def test_second_pass_relative_clauses_do_not_end_mandatory_comma_lists(self) -> None:
        briefs = (
            "Create an animation of a surgeon who wears red, a nurse who wears blue, and a busker.",
            "Create an animation of a surgeon, who wears red, a nurse, who wears blue, and a busker.",
        )
        expected_heads = ("surgeon", "nurse", "busker")
        for brief in briefs:
            with self.subTest(brief=brief):
                clauses = stress.explicit_target_requirement_clauses(brief)
                self.assertEqual(len(clauses), 3, clauses)
                self.assertEqual(
                    tuple(next(iter(clause)) for clause in clauses),
                    tuple(frozenset({head}) for head in expected_heads),
                )
                missing_middle = stress.score_brief_traceability(
                    brief, "Animate a surgeon in red and a busker."
                )
                self.assertLess(missing_middle[0], 3.0, missing_middle)

    def test_second_pass_postnominal_relative_and_comma_modifiers_bind_to_case(self) -> None:
        cases = (
            "A courier opens the case whose label is red.",
            "A courier opens the case, painted red.",
            "A courier opens the case, which is painted red.",
        )
        for brief in cases:
            with self.subTest(brief=brief):
                identity = stress.action_mentions(brief)[0][4]
                self.assertEqual(identity[-1], "case", identity)
                self.assertIn("red", identity)
                self.assertTrue(
                    stress.missing_positive_action_requirements(
                        brief, "A courier opens the case painted blue."
                    )
                )

    def test_second_pass_four_backtick_fences_hide_evidence_without_swallowing_tail(self) -> None:
        brief = "Create an animation of a masked surgeon."
        quoted = stress.score_brief_traceability(
            brief,
            "Animate a masked busker carrying a placard: ````masked surgeon````.",
        )
        unmatched = stress.score_brief_traceability(
            brief,
            "A dangling ```` marker precedes an animated masked surgeon.",
        )
        self.assertLess(quoted[0], 3.0, quoted)
        self.assertGreaterEqual(unmatched[0], 3.0, unmatched)

        many = " ".join(
            f"````quoted surgeon {index}```` visible"
            for index in range(1200)
        )
        spans = stress._quoted_spans(many)
        self.assertEqual(len(spans), 1200)
        for start, end in spans:
            self.assertTrue(stress.position_is_quoted(many, start + 5))
            self.assertFalse(stress.position_is_quoted(many, end + 1))

    def test_second_pass_phase_labels_and_exclusive_light_are_shot_scoped(self) -> None:
        safe_lighting = (
            "Shot 1: a lamp is the only light. "
            "Shot 2: moonlight and neon fill the set."
        )
        self.assertEqual(stress.scoped_contradiction_findings(safe_lighting), [])
        conflicting_lighting = (
            "Shot 1: a lamp fills the set. "
            "Shot 2: the only light sources are moonlight and neon."
        )
        self.assertTrue(
            any(
                finding.startswith("light:")
                for finding in stress.scoped_contradiction_findings(
                    conflicting_lighting
                )
            )
        )

        phase_labels = (
            "The next shot",
            "The subsequent shot",
            "Shot #2",
            "Shot no. 2",
            "Scene II",
            "Later",
        )
        for label in phase_labels:
            with self.subTest(label=label):
                prompt = f"Locked-off camera. {label}: push-in."
                self.assertFalse(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.scoped_contradiction_findings(prompt)
                    ),
                    stress.scoped_contradiction_findings(prompt),
                )

        glass = (
            "A locked-off camera sits beside the next shot glass with a "
            "simultaneous push-in."
        )
        self.assertTrue(
            any(
                finding.startswith("camera:")
                for finding in stress.scoped_contradiction_findings(glass)
            )
        )

    def test_second_pass_numbered_shot_labels_are_not_repetition_padding(self) -> None:
        distinct = " ".join((
            "Shot 1: copper rain crosses a silent platform.",
            "Shot 2: a courier studies the cracked compass.",
            "Shot 3: violet dawn reaches the stairwell.",
            "Shot 4: one paper crane drifts past Mara.",
            "Shot 5: distant thunder shakes the window.",
            "Shot 6: she pockets the compass and exits.",
        ))
        repeated = " ".join(
            f"Shot {index}: velvet rain repeats the identical empty gesture."
            for index in range(1, 7)
        )
        self.assertGreaterEqual(stress.score_repetition(distinct)[0], 3.0)
        self.assertLess(stress.score_repetition(repeated)[0], 3.0)

    def test_audit_v6_actions_are_bound_to_the_required_actor_and_object(self) -> None:
        brief = "Create an animation of a surgeon opening a red case."
        correct = "Animate a surgeon opening the red case."
        wrong_actor_prompts = (
            "A courier opens the red case.",
            "A nurse opens the red case.",
            "The red case opens.",
            "Animate a nurse opening a red case beside a surgeon.",
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(brief, correct)[0], 3.0
        )
        for prompt in wrong_actor_prompts:
            with self.subTest(prompt=prompt):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertLess(score[0], 3.0, score)

        crossed_brief = (
            "A surgeon opens the red case while a nurse closes the blue door."
        )
        crossed_prompt = (
            "A nurse opens the red case while a surgeon closes the blue door."
        )
        self.assertLess(
            stress.score_brief_traceability(crossed_brief, crossed_prompt)[0],
            3.0,
        )

    def test_audit_v6_relative_properties_stay_with_each_list_subject(self) -> None:
        carrying = (
            "Create an animation of a surgeon who carries a bag, a nurse who "
            "carries a tray, and a busker."
        )
        carrying_correct = (
            "Animate a surgeon carrying a bag, a nurse carrying a tray, and a busker."
        )
        carrying_swapped = (
            "Animate a surgeon carrying a tray, a nurse carrying a bag, and a busker."
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(carrying, carrying_correct)[0], 3.0
        )
        self.assertLess(
            stress.score_brief_traceability(carrying, carrying_swapped)[0], 3.0
        )

        colours = (
            "Create an animation of a surgeon who wears red, a nurse who wears "
            "blue, and a busker."
        )
        colour_correct = "Animate a red-wearing surgeon, a blue-wearing nurse, and a busker."
        colour_swapped = "Animate a blue-wearing surgeon, a red-wearing nurse, and a busker."
        self.assertGreaterEqual(
            stress.score_brief_traceability(colours, colour_correct)[0], 3.0
        )
        self.assertLess(
            stress.score_brief_traceability(colours, colour_swapped)[0], 3.0
        )

    def test_audit_v6_reference_role_bridges_leave_sources_out_of_output_targets(self) -> None:
        forms = (
            "Use an image of a cobalt palette as reference when creating an animation of a masked surgeon.",
            "Use an image of a cobalt palette as input, then create an animation of a masked surgeon.",
            "Use an image of a cobalt palette as the reference to create an animation of a masked surgeon.",
        )
        expected = ((frozenset({"mask", "surgeon"}),),)
        for brief in forms:
            with self.subTest(brief=brief):
                self.assertEqual(
                    stress.explicit_target_requirement_clauses(brief), expected
                )
                source_only = stress.score_brief_traceability(
                    brief, "Animate only a cobalt palette."
                )
                self.assertLess(source_only[0], 3.0, source_only)

    def test_audit_v6_shared_suffix_grammar_preserves_heads_without_word_lists(self) -> None:
        cases = (
            ("a red or blue case", "a red balloon", ("a red case", "a blue case")),
            ("red or blue gloves", "red shoes", ("red gloves", "blue gloves")),
            (
                "a tall or short emergency surgeon",
                "a tall busker",
                ("a tall emergency surgeon", "a short emergency surgeon"),
            ),
            (
                "a masked or unmasked emergency surgeon",
                "a masked busker",
                ("a masked emergency surgeon", "an unmasked emergency surgeon"),
            ),
            (
                "a striped or checked leather case",
                "a striped balloon",
                ("a striped leather case", "a checked leather case"),
            ),
            (
                "a calm or anxious elderly surgeon",
                "a calm elderly busker",
                ("a calm elderly surgeon", "an anxious elderly surgeon"),
            ),
        )
        for target, wrong, correct_variants in cases:
            brief = f"Create an animation of {target}."
            with self.subTest(target=target):
                self.assertLess(
                    stress.score_brief_traceability(
                        brief, f"Create an animation of {wrong}."
                    )[0],
                    3.0,
                )
                for correct in correct_variants:
                    score = stress.score_brief_traceability(
                        brief, f"Create an animation of {correct}."
                    )
                    self.assertGreaterEqual(score[0], 3.0, score)

    def test_audit_v6_completed_action_polarity_handles_hypotheticals_and_double_negation(self) -> None:
        brief = "A courier opens the red case."
        completed = (
            "A courier cannot not open the red case.",
            "A courier does not fail to open the red case.",
        )
        for prompt in completed:
            with self.subTest(completed=prompt):
                self.assertEqual(
                    stress.missing_positive_action_requirements(brief, prompt), ()
                )

        non_events = (
            "If a courier opens the red case, the alarm will sound.",
            "A courier almost opens the red case.",
            "A courier is about to open the red case.",
            "A courier imagines opening the red case.",
            "A courier threatens to open the red case.",
            "A courier is scheduled to open the red case.",
            "A courier mimed opening the red case.",
        )
        for prompt in non_events:
            with self.subTest(non_event=prompt):
                self.assertTrue(
                    stress.missing_positive_action_requirements(brief, prompt),
                    stress.action_mentions(prompt),
                )

    def test_audit_v6_postpositive_absence_does_not_confuse_framing_with_presence(self) -> None:
        brief = "Create an animation of a masked surgeon."
        absent = (
            "The masked surgeon does not enter; a masked busker dances.",
            "The masked surgeon remains absent; a masked busker dances.",
            "The masked surgeon has been omitted; a masked busker dances.",
            "The masked surgeon is nowhere seen; a masked busker dances.",
        )
        for prompt in absent:
            with self.subTest(absent=prompt):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertLess(score[0], 3.0, score)

        present_controls = (
            "A masked surgeon is left out of focus but remains in the frame.",
            "A masked surgeon is not shown in close-up but remains in the wide shot.",
        )
        for prompt in present_controls:
            with self.subTest(present=prompt):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertGreaterEqual(score[0], 3.0, score)

    def test_audit_v6_phase_scope_handles_inline_shot_labels_and_common_cues(self) -> None:
        scoped_light = (
            "The only light is a lamp in Shot 1. Shot 2 uses moonlight."
        )
        self.assertFalse(
            any(
                finding.startswith("light:")
                for finding in stress.scoped_contradiction_findings(scoped_light)
            ),
            stress.scoped_contradiction_findings(scoped_light),
        )

        cues = (
            "Subsequently",
            "A moment later",
            "On shot two",
            "During the second shot",
            "In Scene II",
        )
        for cue in cues:
            with self.subTest(cue=cue):
                prompt = f"Locked-off camera. {cue}, push-in."
                self.assertFalse(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.scoped_contradiction_findings(prompt)
                    ),
                    stress.scoped_contradiction_findings(prompt),
                )

        simultaneous = "A locked-off camera uses a push-in simultaneously."
        self.assertTrue(
            any(
                finding.startswith("camera:")
                for finding in stress.scoped_contradiction_findings(simultaneous)
            )
        )

    def test_audit_v6_displayed_and_multilingual_quoted_text_cannot_supply_targets(self) -> None:
        brief = "Create an animation of a masked surgeon."
        displayed = (
            "A masked busker holds a placard reading MASKED SURGEON.",
            "A masked busker holds a sign labeled masked surgeon.",
            "On-screen text says masked surgeon while a masked busker dances.",
            "A masked busker's shirt is printed with masked surgeon.",
        )
        quoted = (
            "A masked busker holds ~~~masked surgeon~~~.",
            "A masked busker holds 【masked surgeon】.",
            "A masked busker holds 〔masked surgeon〕.",
            "A masked busker holds ````masked surgeon`````.",
        )
        for prompt in (*displayed, *quoted):
            with self.subTest(prompt=prompt):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertLess(score[0], 3.0, score)

        controls = (
            "A masked surgeon holds an unclosed ~~~ marker.",
            "A masked surgeon stands beside an unmatched 【 bracket.",
        )
        for prompt in controls:
            self.assertGreaterEqual(
                stress.score_brief_traceability(brief, prompt)[0], 3.0
            )

    def test_audit_v6_phase_label_stripping_is_anchored_and_bare_lists_survive(self) -> None:
        take_five = " ".join(
            "Workers take five before repeating the identical empty gesture."
            for _ in range(6)
        )
        self.assertLess(stress.score_repetition(take_five)[0], 3.0)

        bare = "Create an animation of surgeon, nurse, and busker."
        self.assertEqual(
            stress.explicit_target_requirement_clauses(bare),
            (
                (frozenset({"surgeon"}),),
                (frozenset({"nurse"}),),
                (frozenset({"busker"}),),
            ),
        )

    def test_audit_v6_affirmative_trace_terms_is_near_linear_on_long_unpunctuated_text(self) -> None:
        payload = " ".join(
            f"subject{index:04d}" for index in range(1200)
        )
        stress.affirmative_trace_terms.cache_clear()
        started = time.perf_counter()
        terms = stress.affirmative_trace_terms(payload)
        elapsed = time.perf_counter() - started
        self.assertIn("subject0000", terms)
        self.assertIn("subject1199", terms)
        self.assertLess(elapsed, 1.5, f"10KB affirmative scan took {elapsed:.3f}s")

    def test_audit_v6_actor_binding_handles_passives_pronouns_names_and_by_phrases(self) -> None:
        brief = "A surgeon opens the red case."
        passive = "The red case is opened by a surgeon in the theatre."
        instrument = "A courier opens the red case by hand beside a surgeon."
        self.assertGreaterEqual(
            stress.score_brief_traceability(brief, passive)[0], 3.0
        )
        self.assertLess(
            stress.score_brief_traceability(brief, instrument)[0], 3.0
        )

        named = "Mara opens the red case."
        named_decoy = "Nia opens the red case beside Mara."
        self.assertLess(
            stress.score_brief_traceability(named, named_decoy)[0], 3.0
        )
        named_role = "A surgeon named Mara opens the red case."
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                named_role, "Mara the surgeon opens the red case."
            )[0],
            3.0,
        )
        self.assertLess(
            stress.score_brief_traceability(
                named_role,
                "Nia the surgeon opens the red case beside Mara.",
            )[0],
            3.0,
        )
        pronoun = "A surgeon enters. She opens the red case."
        self.assertGreaterEqual(
            stress.score_brief_traceability(pronoun, pronoun)[0], 3.0
        )

    def test_audit_v6_whose_and_in_properties_remain_bound_to_each_entity(self) -> None:
        whose = (
            "Create an animation of a surgeon whose scarf is red, a nurse whose "
            "scarf is blue, and a busker."
        )
        whose_correct = (
            "Animate a surgeon whose scarf is red, a nurse whose scarf is blue, "
            "and a busker."
        )
        whose_swapped = (
            "Animate a surgeon whose scarf is blue, a nurse whose scarf is red, "
            "and a busker."
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(whose, whose_correct)[0], 3.0
        )
        self.assertLess(
            stress.score_brief_traceability(whose, whose_swapped)[0], 3.0
        )

        clothes = (
            "Create an animation of a surgeon who wears red, a nurse who wears "
            "blue, and a busker."
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                clothes,
                "Animate a surgeon in red, a nurse in blue, and a busker.",
            )[0],
            3.0,
        )
        self.assertLess(
            stress.score_brief_traceability(
                clothes,
                "Animate a surgeon in blue, a nurse in red, and a busker.",
            )[0],
            3.0,
        )

    def test_audit_v6_source_governors_classify_direction_from_both_sides(self) -> None:
        forms = (
            "Using an image of a cobalt palette, create an animation of a masked surgeon.",
            "From a video of a cobalt palette, generate an animation of a masked surgeon.",
            "Given an image of a cobalt palette, render an animation of a masked surgeon.",
            "Use an image of a cobalt palette as visual reference for an animation of a masked surgeon.",
            "An image of a cobalt palette guides creation of an animation of a masked surgeon.",
            "An image of a cobalt palette is input to an animation of a masked surgeon.",
            "An image of a cobalt palette is the source for an animation of a masked surgeon.",
            "An image of a cobalt palette acts as visual reference for an animation of a masked surgeon.",
            "An image of a cobalt palette provides reference for an animation of a masked surgeon.",
            "An image of a cobalt palette feeds into an animation of a masked surgeon.",
            "Use an image of a cobalt palette to guide creation of an animation of a masked surgeon.",
            "Use an image of a cobalt palette to create an animation of a masked surgeon.",
        )
        expected = ((frozenset({"mask", "surgeon"}),),)
        for brief in forms:
            with self.subTest(brief=brief):
                self.assertEqual(
                    stress.explicit_target_requirement_clauses(brief), expected
                )
                self.assertGreaterEqual(
                    stress.score_brief_traceability(
                        brief, "Animate a masked surgeon."
                    )[0],
                    3.0,
                )
                self.assertLess(
                    stress.score_brief_traceability(
                        brief, "Animate only a cobalt palette."
                    )[0],
                    3.0,
                )

    def test_audit_v6_unequal_shared_suffixes_keep_unambiguous_heads(self) -> None:
        cases = (
            (
                "a red or pale blue emergency surgeon",
                ("a red emergency surgeon", "a pale blue emergency surgeon"),
            ),
            (
                "a red or pale blue or green emergency surgeon",
                (
                    "a red emergency surgeon",
                    "a pale blue emergency surgeon",
                    "a green emergency surgeon",
                ),
            ),
        )
        for target, correct in cases:
            brief = f"Create an animation of {target}."
            groups = stress.explicit_target_requirement_groups(brief)
            with self.subTest(target=target):
                self.assertTrue(all("surgeon" in group for group in groups), groups)
                self.assertNotIn("blue", groups[0], groups)
                self.assertLess(
                    stress.score_brief_traceability(
                        brief, "Animate a red emergency busker."
                    )[0],
                    3.0,
                )
                for prompt_target in correct:
                    self.assertGreaterEqual(
                        stress.score_brief_traceability(
                            brief, f"Animate {prompt_target}."
                        )[0],
                        3.0,
                    )

    def test_audit_v6_action_status_covers_states_prospects_and_entailed_events(self) -> None:
        brief = "A courier opens the red case."
        non_events = (
            "The red case stands open.",
            "The red case sits open.",
            "A courier has yet to open the red case.",
            "A courier considers opening the red case.",
            "A courier is asked to open the red case.",
            "A courier is poised to open the red case.",
            "A courier stops short of opening the red case.",
        )
        for prompt in non_events:
            with self.subTest(non_event=prompt):
                self.assertTrue(
                    stress.missing_positive_action_requirements(brief, prompt)
                )

        entailed = (
            "A courier did not avoid opening the red case.",
            "A courier could not avoid opening the red case.",
            "A courier cannot help opening the red case.",
        )
        for prompt in entailed:
            with self.subTest(entailed=prompt):
                self.assertEqual(
                    stress.missing_positive_action_requirements(brief, prompt), ()
                )

        unrelated_absence = (
            "A courier opens the red case while a nurse is absent."
        )
        self.assertEqual(
            stress.missing_positive_action_requirements(brief, unrelated_absence),
            (),
        )

    def test_audit_v6_output_absence_and_displayed_text_have_typed_scope(self) -> None:
        brief = "Create an animation of a masked surgeon."
        absent = (
            "The masked surgeon does not appear on the poster.",
            "The masked surgeon fails to appear in the animation.",
            "The masked surgeon is offscreen throughout.",
            "The masked surgeon appears only in the poster, never in the animation.",
            "On-screen text: MASKED SURGEON.",
            "A busker holds a placard: MASKED SURGEON.",
            "A busker holds a sign showing MASKED SURGEON.",
        )
        for prompt in absent:
            with self.subTest(absent=prompt):
                self.assertLess(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

        present = (
            "The masked surgeon is absent from the poster; however, she enters the animation.",
            "The sign reads BUSKER as the masked surgeon enters.",
            "A placard reads BUSKER and a masked surgeon enters.",
        )
        for prompt in present:
            with self.subTest(present=prompt):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

    def test_audit_v6_phase_owners_and_quote_families_cover_review_edges(self) -> None:
        separated_light = (
            "Shot 1: an LED panel is the only light. "
            "Shot 2: moonlight and neon fill the room."
        )
        same_phase_light = (
            "Shot 1: a lamp is the only light beside moonlight."
        )
        self.assertFalse(
            any(
                finding.startswith("light:")
                for finding in stress.scoped_contradiction_findings(separated_light)
            )
        )
        self.assertTrue(
            any(
                finding.startswith("light:")
                for finding in stress.scoped_contradiction_findings(same_phase_light)
            )
        )
        for cue in ("Afterward", "In Act 2", "During Part 2", "In Scene XI"):
            with self.subTest(cue=cue):
                prompt = f"Locked-off camera. {cue}, push-in."
                self.assertFalse(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.scoped_contradiction_findings(prompt)
                    )
                )

        brief = "Create an animation of a masked surgeon."
        quoted = (
            "A masked busker holds ❝masked surgeon❞.",
            "A masked busker holds ＂masked surgeon＂.",
            "A masked busker holds 〝masked surgeon〟.",
        )
        for prompt in quoted:
            with self.subTest(quoted=prompt):
                self.assertLess(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

    def test_audit_v6_repeated_absence_scan_stays_bounded_and_take_five_survives(self) -> None:
        payload = " ".join(["masked surgeon remains absent"] * 800)
        stress.affirmative_trace_terms.cache_clear()
        started = time.perf_counter()
        stress.affirmative_trace_terms(payload)
        elapsed = time.perf_counter() - started
        self.assertLess(
            elapsed, 1.5, f"24KB repeated-absence scan took {elapsed:.3f}s"
        )

        take_five = " ".join((
            "Workers take five beside the loading dock.",
            "Editors take five near the quiet booth.",
            "Nurses take five after the final round.",
            "Drivers take five beneath the old awning.",
            "Painters take five beside the empty wall.",
            "Riggers take five before the evening call.",
        ))
        self.assertLess(stress.score_repetition(take_five)[0], 3.0)

    def test_audit_v7_source_direction_and_nested_outputs_are_mandatory(self) -> None:
        source_forms = (
            "Create an animation of a masked surgeon using an image of a cobalt palette as reference.",
            "Create an animation of a masked surgeon based on an image of a cobalt palette.",
            "Create an animation of a masked surgeon from an image of a cobalt palette.",
            "Using a photo of a cobalt palette, create a masked surgeon.",
            "Given a reference photo of a cobalt palette, make a masked surgeon.",
            "Use a cobalt palette photo as reference to create a masked surgeon.",
            "Create a masked surgeon using a cobalt palette photo as reference.",
        )
        expected = ((frozenset({"mask", "surgeon"}),),)
        for brief in source_forms:
            with self.subTest(brief=brief):
                self.assertEqual(
                    stress.explicit_target_requirement_clauses(brief), expected
                )
                self.assertGreaterEqual(
                    stress.score_brief_traceability(
                        brief, "Animate a masked surgeon."
                    )[0],
                    3.0,
                )
                self.assertLess(
                    stress.score_brief_traceability(
                        brief, "Animate only a cobalt palette."
                    )[0],
                    3.0,
                )

        nested = (
            "Create an animation showing a masked surgeon beside a monitor "
            "displaying an image of a cobalt palette."
        )
        self.assertEqual(
            stress.explicit_target_requirement_clauses(nested),
            (
                (frozenset({"mask", "surgeon"}),),
                (frozenset({"monitor"}),),
                (frozenset({"cobalt", "palette"}),),
            ),
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                nested,
                "Show a masked surgeon beside a monitor displaying a cobalt palette.",
            )[0],
            3.0,
        )
        self.assertLess(
            stress.score_brief_traceability(nested, "Show the cobalt palette.")[0],
            3.0,
        )

        transition = (
            "Create an animation of an image of a cobalt palette unfolding into "
            "a masked surgeon."
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(transition, transition)[0], 3.0
        )

        output_brief = "Create an animation of a masked surgeon."
        source_only_prompts = (
            "Using an image of a masked surgeon as reference, create an animation of a busker.",
            "From a masked surgeon reference, create an animation of a busker.",
            "Given an image of a masked surgeon, create an animation of a busker.",
            "Use an image of a masked surgeon as input to create an animation of a busker.",
            "An image of a masked surgeon guides an animation showing a busker.",
            "A masked surgeon reference feeds the generation; the output shows a busker.",
            "A masked surgeon image provides the visual reference; create an animation of a busker.",
            "Create an animation of a busker using a masked surgeon image as reference.",
            "Create an animation of a busker based on a masked surgeon image.",
            "A masked surgeon image is the style guide for an animation of a busker.",
            "Take a masked surgeon image and create an animation of a busker.",
            "Create a busker from a masked surgeon reference.",
            "Make a busker using a masked surgeon reference.",
            "Reference image: masked surgeon. Output: busker.",
            "Input: masked surgeon. Output: busker.",
            "Source footage depicts a masked surgeon. Generate a busker.",
            "With footage of a masked surgeon as reference, animate a busker.",
            "Base the busker animation on footage of a masked surgeon.",
            "The reference is a masked surgeon; the result is a busker.",
            "The source clip, showing a masked surgeon, controls style; output: a busker.",
        )
        for prompt in source_only_prompts:
            with self.subTest(source_only=prompt):
                self.assertLess(
                    stress.score_brief_traceability(output_brief, prompt)[0],
                    3.0,
                )

        valid_output_prompts = (
            "Render a masked surgeon inspired by a busker image.",
            "The output uses the source image only for style and depicts a masked surgeon.",
            "Reference footage: busker. Output: masked surgeon.",
            "Animate a masked surgeon based on a busker reference.",
            "An image of a busker guides an animation showing a masked surgeon.",
            "A masked surgeon holds a reference manual.",
            "A masked surgeon points to a reference mark.",
            "Create a reference image of a masked surgeon.",
            "Create a visual reference of a masked surgeon.",
            "From left to right, a masked surgeon enters.",
            "Given the lighting, a masked surgeon enters.",
            "Using a scalpel, a masked surgeon operates.",
            "A masked surgeon guides a patient into the room.",
            "A masked surgeon feeds a patient.",
            "Animate a masked surgeon from head to toe.",
            "Create a masked surgeon from clay.",
            "Animate a masked surgeon using the reference only for lighting.",
        )
        for prompt in valid_output_prompts:
            with self.subTest(valid_output_direction=prompt):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(output_brief, prompt)[0],
                    3.0,
                )

    def test_audit_v7_source_descriptions_cannot_supply_output_semantics(self) -> None:
        action_brief = "A surgeon opens the red case."
        source_only_actions = (
            "Using footage of a surgeon opening the red case as reference, create an animation of a busker.",
            "Create an animation of a busker from footage of a surgeon opening the red case.",
            "Given footage of a surgeon opening the red case, animate a busker.",
            "A clip showing a surgeon opening the red case guides an animation of a busker.",
            "A reference shows a surgeon opening the red case and feeds the generation; the output shows a busker.",
            "Using footage of a surgeon opening the red case as reference, animate a surgeon closing the red case.",
        )
        for prompt in source_only_actions:
            with self.subTest(source_action=prompt):
                self.assertLess(
                    stress.score_brief_traceability(action_brief, prompt)[0],
                    3.0,
                )
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                action_brief,
                "Using footage of a busker dancing as reference, animate a surgeon opening the red case.",
            )[0],
            3.0,
        )
        for prompt in (
            "A surgeon opens the red case from left to right.",
            "A surgeon opens the red case using the reference only for lighting.",
        ):
            with self.subTest(valid_action_boundary=prompt):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(action_brief, prompt)[0],
                    3.0,
                )

        for brief, prompt in (
            (
                "Animate a surgeon whose scarf is red.",
                "Using an image of a surgeon whose scarf is red as reference, animate a surgeon whose scarf is blue.",
            ),
            (
                "Animate a surgeon with a red scarf.",
                "Animate a surgeon with a blue scarf from a reference of a surgeon with a red scarf.",
            ),
        ):
            with self.subTest(source_property=prompt):
                self.assertLess(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

        property_brief = "Animate a surgeon with a red scarf."
        for prompt in (
            "A surgeon with a red scarf enters.",
            "A surgeon with a red scarf opens a door.",
            "A surgeon with a red scarf leads a patient.",
            "A surgeon with a red scarf guides a patient.",
        ):
            with self.subTest(valid_property_boundary=prompt):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(property_brief, prompt)[0],
                    3.0,
                )

        case_brief = "Create an animation of a red leather case."
        source_only_entities = (
            "Using a red leather case image as reference, animate a blue metal case.",
            "A red leather case image guides an animation of a blue metal case.",
            "A red leather case reference feeds the generation; output: a blue metal case.",
        )
        for prompt in source_only_entities:
            with self.subTest(source_entity=prompt):
                self.assertLess(
                    stress.score_brief_traceability(case_brief, prompt)[0], 3.0
                )
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                case_brief,
                "Using a blue balloon as reference, animate a red leather case.",
            )[0],
            3.0,
        )

        masked_brief = "Create an animation of a masked surgeon."
        novel_source_roles = (
            "Let the masked surgeon reference determine the style of a busker animation.",
            "A masked surgeon is in the input, while the output contains a busker.",
            "Input contains a masked surgeon; final animation contains a busker.",
            "The model receives footage of a masked surgeon and renders a busker.",
            "A masked surgeon clip supplies motion guidance for a busker animation.",
            "A busker animation derives its style from masked surgeon footage.",
            "A busker animation takes visual cues from a masked surgeon reference.",
            "Use a masked surgeon only as style inspiration for a busker.",
            "A busker animation is patterned after a masked surgeon image.",
            "A busker animation is informed by a masked surgeon clip.",
            "Use the masked surgeon source solely to set the palette; output: a busker.",
            "A masked surgeon appears in @image1, which serves as style reference. Animate a busker.",
            "Treat the masked surgeon clip as style input for the busker animation.",
            "A busker animation borrows its palette from a masked surgeon still.",
            "A masked surgeon still informs the busker animation color design.",
            "For style, consult the masked surgeon reference; render a busker.",
            "A busker animation references a masked surgeon image for composition.",
            "Drive the busker animation look with a masked surgeon reference.",
            "Use @image1, depicting a masked surgeon, to style a busker animation.",
            "A masked surgeon is visible only in the input; final output is a busker.",
            "Feed a masked surgeon image into the model to render a busker.",
            "Prompt the model with masked surgeon footage; generate a busker.",
            "A busker output is based upon a masked surgeon source.",
            "INPUT\uFF1A masked surgeon\uFF1B OUTPUT\uFF1A busker\u3002",
            "SOURCE IMAGE\uFF1A masked surgeon\uFF0C OUTPUT\uFF1A busker\u3002",
            "INPUTS contain masked surgeons; OUTPUTS contain buskers.",
            "Masked surgeon clips supply motion guidance for busker animations.",
            "Busker animations derive their style from masked surgeon references.",
            "Use masked surgeon sources solely to set palettes; outputs: buskers.",
            "Using references of a masked surgeon and a red leather case, create a busker animation.",
        )
        for prompt in novel_source_roles:
            with self.subTest(novel_source_role=prompt):
                self.assertLess(
                    stress.score_brief_traceability(masked_brief, prompt)[0],
                    3.0,
                )

        novel_source_actions = (
            "Input contains footage of a surgeon opening the red case; final animation contains a busker.",
            "The model receives footage of a surgeon opening the red case and renders a busker.",
            "A busker animation derives motion from footage of a surgeon opening the red case.",
            "A busker animation takes motion cues from footage of a surgeon opening the red case.",
            "Use footage of a surgeon opening the red case only as motion inspiration for a busker.",
            "A busker animation is patterned after footage of a surgeon opening the red case.",
            "A busker animation is informed by footage of a surgeon opening the red case.",
            "A busker animation borrows motion from footage of a surgeon opening the red case.",
            "Transfer motion from footage of a surgeon opening the red case onto a busker animation.",
            "Map motion from a surgeon-opening reference to the busker output.",
        )
        for prompt in novel_source_actions:
            with self.subTest(novel_source_action=prompt):
                self.assertLess(
                    stress.score_brief_traceability(action_brief, prompt)[0],
                    3.0,
                )

        inverse_source_roles = (
            "Let the busker reference determine the style of a masked surgeon animation.",
            "A busker is in the input, while the output contains a masked surgeon.",
            "Input contains a busker; final animation contains a masked surgeon.",
            "The model receives footage of a busker and renders a masked surgeon.",
            "A busker clip supplies motion guidance for a masked surgeon animation.",
            "A masked surgeon animation derives its style from busker footage.",
            "A masked surgeon animation takes visual cues from a busker reference.",
            "Use a busker only as style inspiration for a masked surgeon.",
            "A masked surgeon animation is patterned after a busker image.",
            "A masked surgeon animation is informed by a busker clip.",
            "Use the busker source solely to set the palette; output: a masked surgeon.",
            "A busker appears in @image1, which serves as style reference. Animate a masked surgeon.",
            "Transfer the lighting from busker footage onto a masked surgeon animation.",
            "Borrow motion from a busker clip for a masked surgeon animation.",
            "Map visual traits from a busker reference to the masked surgeon output.",
            "INPUT\uFF1A busker\uFF1B OUTPUT\uFF1A masked surgeon\u3002",
            "INPUTS contain buskers; OUTPUTS contain masked surgeons.",
            "Busker clips supply motion guidance for masked surgeon animations.",
            "Masked surgeon animations derive their style from busker references.",
            "Use busker sources solely to set palettes; outputs: masked surgeons.",
        )
        for prompt in inverse_source_roles:
            with self.subTest(inverse_source_role=prompt):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(masked_brief, prompt)[0],
                    3.0,
                )

        for prompt in (
            "A masked surgeon enters.",
            "The output shows a masked surgeon entering.",
        ):
            with self.subTest(valid_output=prompt):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(masked_brief, prompt)[0],
                    3.0,
                )

    def test_audit_v7_properties_bind_direct_with_multi_and_wearing_forms(self) -> None:
        direct = "Animate a case that is red and a tray that is blue."
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                direct, "Animate a red case and a blue tray."
            )[0],
            3.0,
        )
        self.assertLess(
            stress.score_brief_traceability(
                direct, "Animate a red tray and a blue case."
            )[0],
            3.0,
        )

        relative = (
            "Animate a surgeon with a case that is red and a nurse with a tray "
            "that is blue."
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(relative, relative)[0], 3.0
        )
        self.assertLess(
            stress.score_brief_traceability(
                relative,
                "Animate a surgeon with a case that is blue and a nurse with a "
                "tray that is red.",
            )[0],
            3.0,
        )

        multiple = "Animate a surgeon with a red scarf and a blue hat."
        self.assertGreaterEqual(
            stress.score_brief_traceability(multiple, multiple)[0], 3.0
        )
        self.assertLess(
            stress.score_brief_traceability(
                multiple, "Animate a surgeon with a blue scarf and a red hat."
            )[0],
            3.0,
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                "Animate a surgeon with a red scarf.",
                "Animate a surgeon wearing a red scarf.",
            )[0],
            3.0,
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                "Animate a surgeon whose case is red.",
                "Animate a surgeon with a case that is red.",
            )[0],
            3.0,
        )
        clothing = (
            "Animate a surgeon in a red coat beside a busker in a blue coat."
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(clothing, clothing)[0], 3.0
        )
        self.assertLess(
            stress.score_brief_traceability(
                clothing,
                "Animate a surgeon in a blue coat beside a busker in a red coat.",
            )[0],
            3.0,
        )

    def test_audit_v7_actor_binding_uses_local_entities_and_complete_identity(self) -> None:
        object_relative = "Animate a red case that a surgeon opens."
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                object_relative, "A surgeon opens the red case."
            )[0],
            3.0,
        )
        joint = "A surgeon and a nurse open a red case together."
        self.assertGreaterEqual(
            stress.score_brief_traceability(joint, joint)[0], 3.0
        )

        for brief, prompt in (
            (
                "Create an animation of Mara the masked surgeon.",
                "Animate Mara, a masked surgeon.",
            ),
            (
                "Create an animation of Doctor Mara the masked surgeon.",
                "Animate Doctor Mara, the masked surgeon.",
            ),
        ):
            with self.subTest(appositive=prompt):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

        action_brief = "Animate a surgeon opening a red case."
        pronoun_decoys = (
            "A surgeon enters. A nurse waits. She opens the red case.",
            "A surgeon enters. A male nurse waits. He opens the red case.",
            "A surgeon enters beside a nurse. She opens the red case.",
        )
        for prompt in pronoun_decoys:
            with self.subTest(pronoun_decoy=prompt):
                self.assertLess(
                    stress.score_brief_traceability(action_brief, prompt)[0],
                    3.0,
                )

        long_actor = (
            "A tall elderly scarred masked battle-worn surgeon opens a red case."
        )
        self.assertLess(
            stress.score_brief_traceability(
                long_actor,
                "A short elderly scarred masked battle-worn surgeon opens a red "
                "case beside a tall nurse.",
            )[0],
            3.0,
        )
        completed = "A surgeon opens the red case."
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                completed, "After opening the red case, the surgeon smiles."
            )[0],
            3.0,
        )
        self.assertLess(
            stress.score_brief_traceability(
                completed, "Before opening the red case, the surgeon smiles."
            )[0],
            3.0,
        )

    def test_audit_v7_action_status_rejects_capability_questions_and_representation(self) -> None:
        brief = "A surgeon opens the red case."
        completed = (
            "A surgeon cannot not open the red case.",
            "A surgeon does not fail to open the red case.",
            "A surgeon could not avoid opening the red case.",
            "A surgeon cannot help opening the red case.",
        )
        for prompt in completed:
            with self.subTest(completed=prompt):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

        non_events = (
            "A surgeon can open the red case.",
            "A surgeon is able to open the red case.",
            "A surgeon should open the red case.",
            "A surgeon would open the red case.",
            "Can a surgeon open the red case?",
            "Will a surgeon open the red case?",
            "Suppose a surgeon opens the red case.",
            "The surgeon's opening of the red case is scheduled.",
            "Were a surgeon to open the red case, an alarm would sound.",
            "Should a surgeon open the red case, an alarm sounds.",
            "In the event that a surgeon opens the red case, an alarm sounds.",
            "A surgeon threatens that she will open the red case.",
            "A surgeon promises to open the red case.",
            "A surgeon is ordered to open the red case.",
            "A surgeon acts out opening the red case.",
            "A surgeon fakes opening the red case.",
            "A surgeon pretends that she opens the red case.",
            "The surgeon questions whether to open the red case.",
        )
        for prompt in non_events:
            with self.subTest(non_event=prompt):
                self.assertLess(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

    def test_audit_v7_presence_and_displayed_copy_have_output_scope(self) -> None:
        brief = "Create an animation of a masked surgeon."
        absent = (
            "A masked surgeon is not visible in the animation.",
            "A masked surgeon cannot be seen in the animation.",
            "A masked surgeon is invisible throughout the animation.",
            "A masked surgeon is nowhere in the frame.",
            "The animation excludes a masked surgeon.",
        )
        for prompt in absent:
            with self.subTest(absent=prompt):
                self.assertLess(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

        present = (
            "A masked surgeon is absent from the poster but stands beside it.",
            "A masked surgeon has been omitted from the poster but stands beside it.",
            "A masked surgeon is missing from the close-up but is visible in the wide shot.",
            "A placard reads BUSKER and a masked surgeon enters.",
            "A sign reads BUSKER beside a masked surgeon.",
        )
        for prompt in present:
            with self.subTest(present=prompt):
                self.assertGreaterEqual(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

        competing = (
            "A masked surgeon is absent from the animation while a nurse waits, "
            "but she enters."
        )
        self.assertLess(
            stress.score_brief_traceability(brief, competing)[0], 3.0
        )

        displayed = (
            "MASKED SURGEON is printed on a shirt.",
            "MASKED SURGEON appears as on-screen text.",
            "On-screen: MASKED SURGEON.",
            "Text on screen: MASKED SURGEON.",
            "A placard labeled MASKED SURGEON hangs near a nurse.",
            "A busker holds ⟪masked surgeon⟫.",
        )
        for prompt in displayed:
            with self.subTest(displayed=prompt):
                self.assertLess(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

        action_brief = "A surgeon opens a red case."
        self.assertLess(
            stress.score_brief_traceability(
                action_brief,
                "A surgeon stands beside a red case. A placard reads SURGEON "
                "OPENS RED CASE.",
            )[0],
            3.0,
        )
        self.assertFalse(
            stress.contradiction_findings(
                "Camera stays locked; on-screen text says the camera pushes in."
            )
        )
        self.assertFalse(
            stress.contradiction_findings(
                "Sound is absolute silence; a placard reads RAIN AND TRAFFIC."
            )
        )

    def test_audit_v7_target_groups_are_bound_locally_across_coordination(self) -> None:
        brief = "Create an animation of a red leather case."
        crossed = (
            "Animate a red balloon beside a leather case.",
            "Animate a red balloon, a leather case.",
            "Animate a red balloon plus a leather case.",
            "Animate a red balloon + a leather case.",
            "Animate a red balloon & a leather case.",
            "Animate a red balloon as well as a leather case.",
        )
        for prompt in crossed:
            with self.subTest(crossed=prompt):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertLess(score[0], 3.0, score)
                self.assertIn("not bound to one entity", score[1])
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                brief, "Animate a scratched red leather case."
            )[0],
            3.0,
        )

        unequal = (
            "Create an animation of a deep red or pale blue leather medical case."
        )
        for prompt in (
            "Animate a deep red leather medical case.",
            "Animate a pale blue leather medical case.",
        ):
            self.assertGreaterEqual(
                stress.score_brief_traceability(unequal, prompt)[0], 3.0
            )
        self.assertLess(
            stress.score_brief_traceability(
                unequal,
                "Animate a deep red plastic medical case beside a pale blue "
                "leather balloon.",
            )[0],
            3.0,
        )

        unequal_two = (
            "Create an animation of a red or pale blue emergency field surgeon."
        )
        self.assertLess(
            stress.score_brief_traceability(
                unequal_two,
                "Show a red hospital surgeon beside a pale blue emergency field busker.",
            )[0],
            3.0,
        )

        triple = (
            "Create an animation of a red or pale blue or dark green emergency "
            "field surgeon."
        )
        groups = stress.explicit_target_requirement_groups(triple)
        self.assertIn("emergency", groups[0])
        self.assertIn("field", groups[0])
        self.assertLess(
            stress.score_brief_traceability(
                triple,
                "Animate a red hospital surgeon beside a dark green emergency "
                "field busker.",
            )[0],
            3.0,
        )
        self.assertGreaterEqual(
            stress.score_brief_traceability(
                "Create an animation of a battle-worn or freshly trained emergency surgeon.",
                "Animate a freshly trained emergency surgeon.",
            )[0],
            3.0,
        )

    def test_audit_v7_phase_language_and_structural_headings_do_not_false_conflict(self) -> None:
        cues = (
            "A beat later",
            "Moments later",
            "Soon afterward",
            "Following that",
            "Seconds later",
            "For Shot 2",
            "At the start of Shot 2",
            "Shot 2 begins with",
            "Act II opens on",
            "The next shot begins with",
        )
        for cue in cues:
            with self.subTest(cue=cue):
                self.assertFalse(
                    stress.contradiction_findings(
                        f"Camera stays locked. {cue} a slow push-in."
                    )
                )

        for prompt in (
            "The only light in Shot 1 comes from a lamp and moonlight.",
            "The sole source in Shot 1 is a lamp and moonlight.",
        ):
            self.assertTrue(
                any(
                    finding.startswith("light:")
                    for finding in stress.contradiction_findings(prompt)
                )
            )

        take_five = " ".join(
            f"Take five: worker{index} performs unique action{index}."
            for index in range(6)
        )
        self.assertLess(stress.score_repetition(take_five)[0], 3.0)
        for marker in ("-", "**", ">"):
            headings = "\n".join(
                (
                    f"{marker if marker == '**' else marker + ' '}Shot {index}:"
                    f"{marker if marker == '**' else ''} "
                    f"subject{index} action{index} result{index}."
                )
                for index in range(1, 7)
            )
            with self.subTest(marker=marker):
                self.assertGreaterEqual(stress.score_repetition(headings)[0], 3.0)

    def test_audit_v7_displayed_text_scan_is_bounded(self) -> None:
        payload = " ".join(f"sign:item{index:04d}" for index in range(1200))
        stress._displayed_text_interval_index.cache_clear()
        started = time.perf_counter()
        stress._displayed_text_interval_index(payload)
        elapsed = time.perf_counter() - started
        self.assertLess(
            elapsed, 1.5, f"displayed-text scan took {elapsed:.3f}s"
        )

    def test_audit_v8_open_vocabulary_actions_are_grammar_bound(self) -> None:
        equivalent_inflections = (
            (
                "A fisherman hauls a dripping net.",
                "A fisherman is hauling the dripping net.",
            ),
            (
                "A dancer leaps a narrow gap.",
                "A dancer is leaping the narrow gap.",
            ),
            (
                "A clerk writes a sealed letter.",
                "A clerk is writing the sealed letter.",
            ),
            (
                "A glassblower shapes a cobalt vase.",
                "A glassblower is shaping the cobalt vase.",
            ),
            (
                "A baker kneads a rye loaf.",
                "A baker is kneading the rye loaf.",
            ),
            (
                "A mason etches a crescent plaque.",
                "A mason is etching the crescent plaque.",
            ),
        )
        for brief, prompt in equivalent_inflections:
            with self.subTest(equivalent=(brief, prompt)):
                self.assertEqual(
                    stress.missing_positive_action_requirements(brief, prompt),
                    (),
                )
                self.assertGreaterEqual(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

        mismatched_verbs = (
            (
                "A fisherman hauls a dripping net.",
                "A fisherman mends the dripping net.",
            ),
            (
                "A dancer leaps a narrow gap.",
                "A dancer circles the narrow gap.",
            ),
            (
                "A clerk writes a sealed letter.",
                "A clerk folds the sealed letter.",
            ),
            (
                "A glassblower shapes a cobalt vase.",
                "A glassblower polishes the cobalt vase.",
            ),
            (
                "A baker kneads a rye loaf.",
                "A baker slices the rye loaf.",
            ),
            (
                "A mason etches a crescent plaque.",
                "A mason paints the crescent plaque.",
            ),
        )
        for brief, prompt in mismatched_verbs:
            with self.subTest(mismatch=(brief, prompt)):
                score = stress.score_brief_traceability(brief, prompt)
                self.assertEqual(score[0], 0.0, score)
                self.assertIn("positive action missing", score[1])

        non_events = (
            (
                "A fisherman hauls a dripping net.",
                "A fisherman never hauls the dripping net.",
            ),
            (
                "A dancer leaps a narrow gap.",
                "A dancer plans to leap the narrow gap.",
            ),
            (
                "A clerk writes a sealed letter.",
                'A clerk holds a placard reading "A clerk writes a sealed letter."',
            ),
            (
                "A glassblower shapes a cobalt vase.",
                "A glassblower pretends that she shapes the cobalt vase.",
            ),
            (
                "A mason etches a crescent plaque.",
                "On-screen text: A MASON ETCHES A CRESCENT PLAQUE.",
            ),
        )
        for brief, prompt in non_events:
            with self.subTest(non_event=(brief, prompt)):
                self.assertTrue(
                    stress.missing_positive_action_requirements(brief, prompt)
                )
        represented = stress._bound_action_mentions(
            "A glassblower pretends that she shapes the cobalt vase."
        )
        self.assertTrue(
            any(
                mention.action == "shape"
                and mention.status == stress.ACTION_REPRESENTED
                for mention in represented
            ),
            represented,
        )

        binding_failures = (
            (
                "A fisherman hauls a red net.",
                "A deckhand hauls the red net beside the fisherman.",
            ),
            (
                "A fisherman hauls a red net.",
                "A fisherman hauls a blue net beside the red net.",
            ),
        )
        for brief, prompt in binding_failures:
            with self.subTest(binding=(brief, prompt)):
                self.assertTrue(
                    stress.missing_positive_action_requirements(brief, prompt)
                )

        noun_controls = (
            "A fishing village beside a net.",
            "A writing desk beside a sealed letter.",
            "The coastal lights glow.",
            "A clerk-shaped sign beside a letter box.",
        )
        for control in noun_controls:
            with self.subTest(noun_control=control):
                self.assertEqual(stress._bound_action_mentions(control), ())

    def test_audit_v8_semantic_event_transitions_split_only_real_phases(self) -> None:
        phase_changes = (
            "Camera stays locked off as the image fades to a slow camera push-in.",
            "Camera stays locked off as the frame dissolves into a slow camera push-in.",
            "Camera stays locked off; static framing gives way to a slow camera push-in.",
            "Camera stays locked off; static framing yields to a slow camera push-in.",
            "Camera stays locked off as the image transforms into a slow camera push-in.",
            "Camera stays locked off; static framing is replaced by a slow camera push-in.",
            "Camera stays locked off as the image fades to black. Camera pushes in.",
            "The only light is sunlight, which fades to moonlight.",
            "The only light is sunlight, giving way to moonlight.",
            "Sound is absolute silence, yielding to rain.",
            "She stops moving; stillness gives way to continuing to walk.",
        )
        for prompt in phase_changes:
            with self.subTest(phase_change=prompt):
                self.assertEqual(stress.contradiction_findings(prompt), [])

        controls = (
            'Camera stays locked off as the editor says "the image fades to" '
            "before camera pushes in.",
            "Camera stays locked off. On-screen text: IMAGE FADES TO BLACK. "
            "Camera pushes in.",
            "Camera stays locked off as the courier's smile fades to a frown "
            "and camera pushes in.",
            "Camera stays locked off as the editor discusses a fade to a slow "
            "camera push-in.",
            "Camera stays locked off; if the image fades to a slow camera push-in.",
            "Camera stays locked off; the image does not fade to black. "
            "Camera pushes in.",
            "Camera stays locked off while the image fades to a slow camera push-in.",
            "Camera stays locked off as the image fades to a slow camera push-in "
            "at the same time.",
        )
        for prompt in controls:
            with self.subTest(control=prompt):
                findings = stress.contradiction_findings(prompt)
                self.assertTrue(
                    any(finding.startswith("camera:") for finding in findings),
                    findings,
                )

    def test_audit_v9_open_actions_cover_real_grammar_without_false_greens(self) -> None:
        changed_actions = (
            ("A farmer harvests wheat.", "A farmer burns wheat."),
            ("A dancer twirls.", "A dancer stands."),
            (
                "A chef slices and serves the loaf.",
                "A chef burns and serves the loaf.",
            ),
            ("Mara hauls the red net.", "Mara burns the red net."),
            (
                "A fisherman is shown hauling the net.",
                "A fisherman is shown mending the net.",
            ),
        )
        for brief, prompt in changed_actions:
            with self.subTest(changed=(brief, prompt)):
                self.assertTrue(
                    stress.missing_positive_action_requirements(brief, prompt)
                )
                self.assertLess(
                    stress.score_brief_traceability(brief, prompt)[0], 3.0
                )

    def test_audit_v9_action_identity_is_safe_for_irregulars_and_particles(self) -> None:
        equivalents = (
            ("A painter draws the portrait.", "A painter drew the portrait."),
            (
                "A painter draws the portrait.",
                "The portrait is drawn by a painter.",
            ),
            ("A child takes the lantern.", "A child took the lantern."),
            ("A baker tears the paper.", "The paper is torn by a baker."),
        )
        for brief, prompt in equivalents:
            with self.subTest(equivalent=(brief, prompt)):
                self.assertEqual(
                    stress.missing_positive_action_requirements(brief, prompt),
                    (),
                )

        changed = (
            ("A medic tapes the wrist.", "A medic taps the wrist."),
            (
                "A technician powers up the machine.",
                "A technician powers down the machine.",
            ),
            (
                "A sailor winds up the cable.",
                "A sailor winds down the cable.",
            ),
        )
        for brief, prompt in changed:
            with self.subTest(changed=(brief, prompt)):
                self.assertTrue(
                    stress.missing_positive_action_requirements(brief, prompt)
                )

    def test_audit_v9_reported_actions_do_not_count_as_performed(self) -> None:
        brief = "A fisherman hauls the dripping net."
        represented = (
            "A fisherman claims he hauls the dripping net.",
            "A fisherman says he hauls the dripping net.",
            "A fisherman watches footage in which he hauls the dripping net.",
            "A fisherman remembers that he hauls the dripping net.",
            "A fisherman describes how he hauls the dripping net.",
        )
        for prompt in represented:
            with self.subTest(represented=prompt):
                self.assertTrue(
                    stress.missing_positive_action_requirements(brief, prompt)
                )

    def test_audit_v9_semantic_transitions_bind_scope_and_unicode(self) -> None:
        valid = (
            "Camera stays locked off; the shot cuts to a slow camera push-in.",
            "Camera stays locked off; the image crossfades to a slow camera push-in.",
            "Camera stays locked off; the scene switches to a slow camera push-in.",
            "Camera stays locked off！The image fades to black！Camera pushes in.",
        )
        for prompt in valid:
            with self.subTest(valid=prompt):
                self.assertFalse(stress.contradiction_findings(prompt))

        scoped_controls = (
            "Camera stays locked off; the image fades to a slow camera push-in "
            "only in an imagined version.",
            "Camera stays locked off; the image fades to a slow camera push-in "
            "in no version.",
            "Camera stays locked off; the image fades to a slow camera push-in "
            "only on the storyboard.",
            "Camera stays locked off as the image fades to a slow camera push-in "
            "throughout.",
            "Camera stays locked off as the image fades to a slow camera push-in "
            "during the same moment.",
        )
        for prompt in scoped_controls:
            with self.subTest(scoped_control=prompt):
                self.assertTrue(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.contradiction_findings(prompt)
                    )
                )

    def test_pr122_contextual_bare_plural_actions_are_mandatory(self) -> None:
        brief = "At dawn, farmers harvest wheat."
        prompt = "At dawn, farmers burn wheat."

        self.assertTrue(
            any(
                mention.action == "harvest" and mention.positive
                for mention in stress._bound_action_mentions(brief)
            )
        )
        self.assertTrue(stress.missing_positive_action_requirements(brief, prompt))
        self.assertLess(stress.score_brief_traceability(brief, prompt)[0], 3.0)

    def test_pr122_found_base_verb_does_not_collapse_into_find(self) -> None:
        brief = "A pioneer will find the city."
        prompt = "A pioneer will found the city."

        prompt_actions = stress._bound_action_mentions(prompt)
        self.assertTrue(
            any(mention.action == "found" for mention in prompt_actions),
            prompt_actions,
        )
        self.assertTrue(stress.missing_positive_action_requirements(brief, prompt))
        self.assertEqual(
            stress.missing_positive_action_requirements(
                brief, "A pioneer found the city."
            ),
            (),
        )

    def test_pr122_separated_phrasal_particles_keep_identity(self) -> None:
        adjacent = "A technician powers up the machine."
        separated = "A technician powers the machine up."
        changed_brief = "A technician powers the machine off."
        changed_prompt = "A technician powers the machine on."

        self.assertEqual(
            stress.missing_positive_action_requirements(adjacent, separated),
            (),
        )
        self.assertTrue(
            stress.missing_positive_action_requirements(changed_brief, changed_prompt)
        )
        particles = {
            text: next(
                mention.particles
                for mention in stress._bound_action_mentions(text)
                if mention.action == "power"
            )
            for text in (adjacent, separated, changed_brief, changed_prompt)
        }
        self.assertEqual(particles[adjacent], ("up",))
        self.assertEqual(particles[separated], ("up",))
        self.assertEqual(particles[changed_brief], ("off",))
        self.assertEqual(particles[changed_prompt], ("on",))

    def test_pr122_reported_action_governors_are_not_performed(self) -> None:
        brief = "A fisherman hauls the net."
        represented = (
            "A fisherman tells the camera that he hauls the net.",
            "A fisherman explains to the camera that he hauls the net.",
            "A fisherman announces to the camera that he hauls the net.",
        )

        for prompt in represented:
            with self.subTest(prompt=prompt):
                mentions = stress._bound_action_mentions(prompt)
                self.assertTrue(
                    any(
                        mention.action == "haul"
                        and mention.status == stress.ACTION_REPRESENTED
                        for mention in mentions
                    ),
                    mentions,
                )
                self.assertTrue(
                    stress.missing_positive_action_requirements(brief, prompt)
                )

    def test_pr122_transition_suffixes_do_not_create_real_phases(self) -> None:
        scoped_notes = (
            "Camera stays locked off; the image fades to a slow camera push-in "
            "in the storyboard.",
            "Camera stays locked off; the image fades to a slow camera push-in "
            "in an imagined version only.",
            "Camera stays locked off; the image fades to a slow camera push-in "
            "as a concept note.",
        )

        for prompt in scoped_notes:
            with self.subTest(prompt=prompt):
                self.assertTrue(
                    any(
                        finding.startswith("camera:")
                        for finding in stress.contradiction_findings(prompt)
                    )
                )

    def test_pr122_shot_pronoun_can_carry_a_real_transition(self) -> None:
        prompt = (
            "The shot stays locked off; it then fades to black. "
            "The camera pushes in."
        )
        unrelated = (
            "The camera stays locked off; it then fades to black. "
            "The camera pushes in."
        )

        self.assertEqual(stress.contradiction_findings(prompt), [])
        self.assertTrue(
            any(
                finding.startswith("camera:")
                for finding in stress.contradiction_findings(unrelated)
            )
        )

    def test_pr122_transition_unicode_boundaries_are_complete(self) -> None:
        valid = (
            "Camera stays locked off\u2026 The image fades to black\u2026 "
            "Camera pushes in.",
            "Camera stays locked off\u061f The image fades to black\u061f "
            "Camera pushes in.",
        )

        for prompt in valid:
            with self.subTest(prompt=prompt):
                self.assertEqual(stress.contradiction_findings(prompt), [])

    def test_audit_v9_inert_token_scan_remains_near_linear(self) -> None:
        def elapsed(words: int) -> float:
            payload = ("alpha " * words).strip()
            stress._bound_action_mentions.cache_clear()
            stress._action_clause_boundary_index.cache_clear()
            stress._state_transition_attribute_interval_index.cache_clear()
            started = time.perf_counter()
            stress._bound_action_mentions(payload)
            return time.perf_counter() - started

        small = elapsed(1000)
        large = elapsed(4000)
        self.assertLess(
            large,
            max(3.0, small * 9.0 + 0.1),
            f"open action scan grew from {small:.3f}s to {large:.3f}s",
        )

    def test_pr122_action_rich_scan_remains_near_linear(self) -> None:
        def elapsed(clauses: int) -> float:
            payload = "A baker kneads a rye loaf. " * clauses
            stress._bound_action_mentions.cache_clear()
            stress._action_clause_boundary_index.cache_clear()
            stress._state_transition_attribute_interval_index.cache_clear()
            started = time.perf_counter()
            stress._bound_action_mentions(payload)
            return time.perf_counter() - started

        small = elapsed(1000)
        large = elapsed(8000)
        self.assertLess(
            large,
            max(5.0, small * 13.0 + 0.2),
            f"action-rich scan grew from {small:.3f}s to {large:.3f}s",
        )

    def test_repaired_b22_fixture_clears_the_case_structure_floor(self) -> None:
        record = next(r for r in shipped_corpus() if r["id"] == "b22-s")
        result = stress.score_prompt(record)
        self.assertGreaterEqual(result["dims"]["structure"]["score"], 3.0, result["dims"])


class FairnessTests(unittest.TestCase):
    # "Keep the same lens" is a camera decision even though nothing moves, but
    # only a mode with a source to preserve gets to make that argument.
    KEPT = "Continue from the observed final frame; keep the same light and lens."

    def test_preserving_a_dimension_addresses_it_on_a_continuation(self) -> None:
        score, note = stress.score_coverage(self.KEPT, "EXTEND")
        self.assertIn("preservation: camera", note)
        self.assertNotIn("camera", note.split("(")[0])

    def test_preservation_does_not_count_for_text_to_video(self) -> None:
        t2v = stress.score_coverage(self.KEPT, "T2V")
        self.assertIn("camera", t2v[1])
        self.assertLess(t2v[0], stress.score_coverage(self.KEPT, "EXTEND")[0])

    def test_prose_binding_is_a_real_binding(self) -> None:
        prose = "Start with the accepted final frame: she is two steps from the door."
        self.assertGreaterEqual(stress.score_refs(prose, "EXTEND")[0], 3.0)

    def test_no_binding_at_all_is_still_a_finding(self) -> None:
        self.assertEqual(stress.score_refs("She walks to the door and stops.", "EXTEND")[0], 0.0)

    def test_camera_hold_and_signal_light_are_detected(self) -> None:
        self.assertTrue(stress.CAMERA.search("One continuous camera hold, no cuts."))
        self.assertTrue(stress.LIGHT.search("a red signal light reflects across the puddle"))
        self.assertTrue(stress.SOUND.search("breathing steady"))


class ShippedExampleTests(unittest.TestCase):
    def test_every_golden_prompt_clears_the_release_bar(self) -> None:
        scores = []
        new_dimensions = ("brief_traceability", "coherence", "repetition")
        for path in sorted(GOLDEN.glob("*.md")):
            mode = GOLDEN_MODES.get(path.stem)
            self.assertIsNotNone(mode, f"{path.stem} needs a mode in GOLDEN_MODES")
            result = stress.score_prompt(
                {"id": path.stem, "arm": "shipped_golden", "mode": mode,
                 "brief": source_brief(path), "prompt": compiled(path)}
            )
            scores.append(result["overall"])
            self.assertGreaterEqual(result["overall"], 3.0, f"{path.stem}: {result['dims']}")
            for dimension in new_dimensions:
                self.assertGreaterEqual(
                    result["dims"][dimension]["score"],
                    3.0,
                    f"{path.stem} {dimension}: {result['dims'][dimension]}",
                )
        self.assertGreaterEqual(statistics.mean(scores), 3.5)


class DoctrineArmTests(unittest.TestCase):
    def test_the_doctrine_arm_still_beats_the_other_two(self) -> None:
        import json
        corpus = json.loads((ROOT / "evals" / "prompt-architecture-stress.json").read_text("utf-8"))
        by_arm: dict[str, list[float]] = {}
        for record in corpus:
            by_arm.setdefault(record["arm"], []).append(stress.score_prompt(record)["overall"])
        doctrine = statistics.mean(by_arm["skill_formula"])
        self.assertGreaterEqual(doctrine, 3.5)
        for arm in ("quickstart_style", "naive_online"):
            self.assertLess(statistics.mean(by_arm[arm]), doctrine)


if __name__ == "__main__":
    unittest.main()

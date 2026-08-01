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
        for path in sorted(GOLDEN.glob("*.md")):
            mode = GOLDEN_MODES.get(path.stem)
            self.assertIsNotNone(mode, f"{path.stem} needs a mode in GOLDEN_MODES")
            result = stress.score_prompt(
                {"id": path.stem, "arm": "shipped_golden", "mode": mode,
                 "brief": source_brief(path), "prompt": compiled(path)}
            )
            scores.append(result["overall"])
            self.assertGreaterEqual(result["overall"], 3.0, f"{path.stem}: {result['dims']}")
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

"""Behavioral contract for validator ``--strict`` flags.

``--strict`` is reserved for a real lenient/reporting default that can be
promoted to a release failure. Validators that always run their full check set
must reject a cosmetic flag instead of advertising imaginary extra coverage.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import project_state_check  # noqa: E402
import prompt_lint  # noqa: E402


# This is the complete integrated inventory at the #14 repair boundary. An
# explicit partition makes every removal/retention decision reviewable and
# prevents a future cosmetic flag from hiding among unrelated parser changes.
AUDITED_STRICT_SCRIPTS = {
    "behavior_contract_check.py",
    "content_audit.py",
    "continuity_chain_check.py",
    "design_audit.py",
    "eval_run.py",
    "eval_schema_check.py",
    "extract_last_frame.py",
    "generation_run_check.py",
    "project_state_check.py",
    "prompt_architecture_stress.py",
    "prompt_lint.py",
    "schema_check.py",
    "sequence_eval_check.py",
    "source_registry_check.py",
    "validate_skills.py",
    "vocab_schema_check.py",
}
BEHAVIORAL_STRICT_SCRIPTS = {
    "continuity_chain_check.py",
    "project_state_check.py",
    "prompt_architecture_stress.py",
    "prompt_lint.py",
    "vocab_schema_check.py",
}
COSMETIC_STRICT_SCRIPTS = AUDITED_STRICT_SCRIPTS - BEHAVIORAL_STRICT_SCRIPTS
DOCUMENTED_COSMETIC_REPLACEMENTS = {
    "behavior_contract_check.py": (),
    "content_audit.py": (),
    "design_audit.py": (),
    "eval_run.py": ("--self-test",),
    "eval_schema_check.py": (),
    "extract_last_frame.py": ("--self-test",),
    "generation_run_check.py": (),
    "schema_check.py": (),
    "sequence_eval_check.py": (),
    "source_registry_check.py": (),
    "validate_skills.py": (),
}
STRICT_HELP_MARKERS = {
    "continuity_chain_check.py": "treat transient continuity warnings as validation errors",
    "project_state_check.py": "require complete authoring state",
    "prompt_architecture_stress.py": "exit non-zero if any skill_formula case/dimension is below 3",
    "prompt_lint.py": "require bare compiled prose",
    "vocab_schema_check.py": "require at least 40 rows",
}


def declared_strict_scripts() -> set[str]:
    declared: set[str] = set()
    for script in SCRIPTS.glob("*.py"):
        tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
                continue
            if any(
                isinstance(argument, ast.Constant) and argument.value == "--strict"
                for argument in node.args
            ):
                declared.add(script.name)
    return declared


def strict_attribute_reads(script: Path) -> int:
    tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "args"
        and node.attr == "strict"
    )


def run_script(name: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *arguments],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


class StrictInventoryTests(unittest.TestCase):
    def test_inventory_is_a_complete_partition(self) -> None:
        self.assertEqual(len(AUDITED_STRICT_SCRIPTS), 16)
        self.assertFalse(BEHAVIORAL_STRICT_SCRIPTS & COSMETIC_STRICT_SCRIPTS)
        self.assertEqual(
            BEHAVIORAL_STRICT_SCRIPTS | COSMETIC_STRICT_SCRIPTS,
            AUDITED_STRICT_SCRIPTS,
        )

    def test_only_behavioral_strict_flags_are_advertised(self) -> None:
        self.assertEqual(declared_strict_scripts(), BEHAVIORAL_STRICT_SCRIPTS)

    def test_every_retained_flag_is_read_by_validation_logic(self) -> None:
        for name in BEHAVIORAL_STRICT_SCRIPTS:
            self.assertGreater(
                strict_attribute_reads(SCRIPTS / name),
                0,
                f"{name} declares --strict but never reads args.strict",
            )

    def test_retained_help_names_the_extra_failure_condition(self) -> None:
        self.assertEqual(set(STRICT_HELP_MARKERS), BEHAVIORAL_STRICT_SCRIPTS)
        for name, marker in sorted(STRICT_HELP_MARKERS.items()):
            result = run_script(name, "--help")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(marker, " ".join(result.stdout.split()), name)

    def test_removed_cosmetic_flags_are_rejected(self) -> None:
        for name in sorted(COSMETIC_STRICT_SCRIPTS):
            result = run_script(name, "--strict")
            self.assertEqual(result.returncode, 2, name + "\n" + result.stdout + result.stderr)
            self.assertIn("unrecognized arguments: --strict", result.stderr, name)

    def test_cosmetic_flag_replacements_keep_documented_checks_green(self) -> None:
        self.assertEqual(set(DOCUMENTED_COSMETIC_REPLACEMENTS), COSMETIC_STRICT_SCRIPTS)
        for name, arguments in sorted(DOCUMENTED_COSMETIC_REPLACEMENTS.items()):
            result = run_script(name, *arguments)
            self.assertEqual(result.returncode, 0, name + "\n" + result.stdout + result.stderr)

    def test_current_release_surfaces_use_strict_only_for_behavioral_commands(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        validation_block = readme.split("## Validation", 1)[1].split(
            "## Design Standard", 1
        )[0]
        surfaces = {
            "README.md#Validation": validation_block,
            ".github/workflows/validate-skills.yml": (
                ROOT / ".github" / "workflows" / "validate-skills.yml"
            ).read_text(encoding="utf-8"),
            ".github/workflows/source-freshness-review.yml": (
                ROOT / ".github" / "workflows" / "source-freshness-review.yml"
            ).read_text(encoding="utf-8"),
        }
        offenders: list[str] = []
        for label, text in surfaces.items():
            for line_number, line in enumerate(text.splitlines(), 1):
                if "--strict" not in line or ".py" not in line:
                    continue
                if not any(name in line for name in BEHAVIORAL_STRICT_SCRIPTS):
                    offenders.append(f"{label}:{line_number}: {line.strip()}")
        self.assertEqual(offenders, [])


class StrictBehaviorTests(unittest.TestCase):
    def test_continuity_strict_promotes_transient_warning_to_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            examples = root / "examples"
            examples.mkdir()
            fixture = examples / "sequence-airport-arrival"
            shutil.copytree(
                ROOT / "examples" / "sequence-airport-arrival",
                fixture,
            )
            state_path = fixture / "project-state.json"
            project_state = json.loads(state_path.read_text(encoding="utf-8"))
            project_state["clips"][1]["planned_start_state"]["character"][
                "pose"
            ] = "seated"
            state_path.write_text(json.dumps(project_state), encoding="utf-8")
            normal = run_script("continuity_chain_check.py", str(root))
            strict = run_script("continuity_chain_check.py", str(root), "--strict")

        self.assertEqual(normal.returncode, 0, normal.stdout + normal.stderr)
        self.assertIn("Continuity warnings", normal.stdout)
        self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
        self.assertIn("transient character.pose changes", strict.stdout)

    def test_vocab_strict_adds_depth_requirements(self) -> None:
        minimal_vocab = """# Vocabulary

Keep reference tags unchanged: @Image1 then @Video1.

| Function | Term | Meaning |
|---|---|---|
| Camera | hold | keep the frame still |

## Slop Traps

Avoid empty quality words.
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            vocab = root / "references" / "vocab"
            vocab.mkdir(parents=True)
            for language in ("en", "zh", "ru", "ja", "ko", "es"):
                (vocab / f"{language}.md").write_text(minimal_vocab, encoding="utf-8")
            for relative in (
                "evals/multilingual-native-review.json",
                "evals/multilingual-native-review-evidence.json",
                "references/multilingual-native-review.md",
                "skills/seedance-examples-zh/SKILL.md",
                "skills/seedance-examples-ja/SKILL.md",
                "skills/seedance-examples-ko/SKILL.md",
                "docs/README.zh.md",
                "docs/README.ja.md",
                "docs/README.ko.md",
            ):
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, destination)
            normal = run_script("vocab_schema_check.py", str(root))
            strict = run_script("vocab_schema_check.py", str(root), "--strict")

        self.assertEqual(normal.returncode, 0, normal.stdout + normal.stderr)
        self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
        self.assertIn("expected at least 40 rows", strict.stdout)
        self.assertIn("missing strict functions", strict.stdout)

    def test_architecture_strict_turns_release_bar_into_exit_gate(self) -> None:
        corpus = json.loads(
            (ROOT / "evals" / "prompt-architecture-stress.json").read_text(encoding="utf-8")
        )
        for record in corpus:
            if record["arm"] == "skill_formula":
                record["prompt"] = "cinematic masterpiece"

        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "failing-corpus.json"
            path.write_text(json.dumps(corpus), encoding="utf-8")
            normal = run_script("prompt_architecture_stress.py", str(path))
            strict = run_script("prompt_architecture_stress.py", str(path), "--strict")

        self.assertEqual(normal.returncode, 0, normal.stdout + normal.stderr)
        self.assertIn("skill_formula", normal.stdout)
        self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
        self.assertIn("skill_formula strict gate failed", strict.stdout)

    def test_prompt_lint_strict_rejects_a_default_compatible_wrapper(self) -> None:
        prompt = "```text\nA courier crosses the room while the camera remains locked.\n```"
        self.assertIsNone(prompt_lint.structured_prompt_reason(prompt, strict=False))
        self.assertIn(
            "strict mode requires bare natural-language prose",
            prompt_lint.structured_prompt_reason(prompt, strict=True) or "",
        )

    def test_project_state_strict_adds_release_bindings(self) -> None:
        contract = project_state_check.load_json(
            ROOT / "examples" / "sequence-airport-arrival" / "clip-01-contract.json"
        )
        self.assertIsInstance(contract, dict)
        normal_errors: list[str] = []
        strict_errors: list[str] = []
        project_state_check.validate_contract(
            contract,
            "contract",
            normal_errors,
            strict=False,
            current_clip=None,
            prompt=None,
        )
        project_state_check.validate_contract(
            contract,
            "contract",
            strict_errors,
            strict=True,
            current_clip=None,
            prompt=None,
        )
        for marker in (
            "no current project clip matches this contract",
            "matching generation prompt is missing",
        ):
            self.assertFalse(any(marker in error for error in normal_errors), normal_errors)
            self.assertTrue(any(marker in error for error in strict_errors), strict_errors)


if __name__ == "__main__":
    unittest.main()

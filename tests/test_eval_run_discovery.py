"""Adversarial coverage for manifest-bound blind source discovery."""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import eval_run  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RUBRIC = (REPO_ROOT / "references" / "eval-rubric.md").read_text(
    encoding="utf-8"
)


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_manifest(
    root: Path,
    *,
    role_overrides: dict[str, str] | None = None,
) -> None:
    overrides = role_overrides or {}
    for evaluator_path in eval_run.EVALUATOR_HARNESS_PATHS:
        if not (root / evaluator_path).exists():
            write(root, evaluator_path, "# frozen test evaluator harness\n")
    paths = {
        "SKILL.md",
        "evals/evals.json",
        "references/eval-rubric.md",
        *eval_run.EVALUATOR_HARNESS_PATHS,
    }
    for directory in (root / "skills", root / "references", root / "evals" / "fixtures"):
        if directory.exists():
            paths.update(
                path.relative_to(root).as_posix()
                for path in directory.rglob("*")
                if path.is_file()
            )
    entries = []
    for relative in sorted(paths):
        if relative == "SKILL.md":
            role = "root"
        elif relative in {
            "evals/evals.json",
            "references/eval-rubric.md",
            *eval_run.EVALUATOR_HARNESS_PATHS,
        }:
            role = "evaluator"
        elif relative.startswith("evals/fixtures/"):
            role = "fixture"
        elif relative.startswith("references/migrated/"):
            role = "archive"
        else:
            role = "responder"
        role = overrides.get(relative, role)
        entries.append(
            {
                "path": relative,
                "role": role,
                "sha256": hashlib.sha256((root / relative).read_bytes()).hexdigest(),
            }
        )
    write(
        root,
        eval_run.SOURCE_MANIFEST_PATH,
        json.dumps({"version": 1, "sources": entries}, indent=2) + "\n",
    )


def base_case(**updates: object) -> dict:
    case: dict[str, object] = {
        "id": "adversarial_case",
        "prompt": "ORIGINAL-USER-PROMPT",
        "expected_output": "EXPECTED-OUTPUT-SECRET",
        "assertions": ["JUDGE-ONLY-ASSERTION"],
        "failure_mode": "FAILURE-MODE-SECRET",
        "skills_expected_to_activate": ["actual-route"],
        "state_fixture": "evals/fixtures/state.json",
        "expected_state_delta": "STATE-DELTA-SECRET",
        "expected_prompt_architecture": "PROMPT-ARCHITECTURE-SECRET",
        "expected_sequence_relation": "SEQUENCE-RELATION-SECRET",
    }
    case.update(updates)
    return case


def make_root(root: Path, case: dict | None = None) -> None:
    write(root, "SKILL.md", "ROOT-HEAD\n" + "r" * 13000 + "\nROOT-TAIL")
    write(
        root,
        "skills/actual-route/SKILL.md",
        "ACTUAL-SKILL-HEAD\n" + "s" * 9000 + "\nACTUAL-SKILL-TAIL",
    )
    write(root, "skills/extra-route/SKILL.md", "EXTRA-ROUTE")
    write(
        root,
        "references/actual-reference.md",
        "REFERENCE-HEAD\n" + "f" * 13000 + "\nREFERENCE-TAIL",
    )
    write(root, "references/private-rubric.md", "PRIVATE-EVALUATOR-SECRET")
    write(root, "references/migrated/archive.md", "ARCHIVE-SECRET")
    write(root, "references/eval-rubric.md", CANONICAL_RUBRIC)
    write(
        root,
        "evals/fixtures/state.json",
        json.dumps({"schema_version": "test-v1", "state": "STATE-DATA-TAIL"}),
    )
    write(root, "evals/evals.json", json.dumps({"cases": [case or base_case()]}))
    write_manifest(
        root,
        role_overrides={"references/private-rubric.md": "evaluator"},
    )


def sequence_verdict(case: dict) -> dict:
    return {
        "overall_score": 4,
        "pass": True,
        "notes": "complete",
        "criterion_scores": {
            check: True
            for check in eval_run.expected_judge_checks(case)
        },
        "dimension_scores": {
            dimension_id: 4
            for dimension_id in eval_run.SEQUENCE_DIMENSION_IDS
        },
    }


class DiscoveryBoundaryTests(unittest.TestCase):
    def snapshot(self, root: Path) -> eval_run.FrozenRepository:
        return eval_run.freeze_repository(root, enforce_canonical_contract=False)

    def test_blind_route_response_and_judge_use_only_frozen_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = base_case()
            make_root(root, case)
            snapshot = self.snapshot(root)
            provider, endpoint, model = eval_run.resolve_provider(
                "minimax", "global_en", None
            )
            calls: list[dict[str, object]] = []

            def fake_call(
                system: str,
                user: str,
                selected_model: str,
                api_key: str,
                selected_provider: eval_run.ProviderConfig,
                selected_endpoint: str,
                max_tokens: int = 1500,
            ) -> str:
                calls.append(
                    {
                        "system": system,
                        "user": user,
                        "model": selected_model,
                        "api_key": api_key,
                        "provider": selected_provider,
                        "endpoint": selected_endpoint,
                        "max_tokens": max_tokens,
                    }
                )
                if len(calls) == 1:
                    return json.dumps(
                        {
                            "sources": [
                                "skills/actual-route/SKILL.md",
                                "references/actual-reference.md",
                            ]
                        }
                    )
                if len(calls) == 2:
                    return "candidate response"
                return json.dumps(sequence_verdict(case))

            with mock.patch.object(eval_run, "call_api", side_effect=fake_call):
                verdict, sources = eval_run.run_case(
                    snapshot,
                    case,
                    model,
                    "MiniMax-M2.5",
                    "test-key",
                    CANONICAL_RUBRIC,
                    provider,
                    endpoint,
                )

            self.assertEqual(len(calls), 3)
            self.assertEqual(
                [call["model"] for call in calls],
                ["MiniMax-M3", "MiniMax-M3", "MiniMax-M2.5"],
            )
            self.assertEqual([call["max_tokens"] for call in calls], [900, 1500, 900])
            for call in calls:
                self.assertIs(call["provider"], provider)
                self.assertEqual(call["endpoint"], endpoint)
                self.assertEqual(call["api_key"], "test-key")

            planner = str(calls[0]["system"]) + str(calls[0]["user"])
            responder = str(calls[1]["system"]) + str(calls[1]["user"])
            judge = str(calls[2]["system"]) + str(calls[2]["user"])
            for secret in (
                "FAILURE-MODE-SECRET",
                "STATE-DELTA-SECRET",
                "PROMPT-ARCHITECTURE-SECRET",
                "SEQUENCE-RELATION-SECRET",
            ):
                self.assertNotIn(secret, planner)
                self.assertNotIn(secret, responder)
                self.assertIn(secret, judge)
            for judge_only in ("EXPECTED-OUTPUT-SECRET", "JUDGE-ONLY-ASSERTION"):
                self.assertNotIn(judge_only, planner)
                self.assertNotIn(judge_only, responder)
                self.assertIn(judge_only, judge)
            for blinded_label in (
                "expected_skills",
                "sources_selected_without_expected_labels",
                "skills/actual-route/SKILL.md",
                "references/actual-reference.md",
            ):
                self.assertNotIn(blinded_label, judge)
            for field in (
                "skills_expected_to_activate",
                "state_fixture",
                "failure_mode",
                "expected_state_delta",
                "expected_prompt_architecture",
                "expected_sequence_relation",
            ):
                self.assertNotIn(field, planner)
                self.assertNotIn(field, responder)

            self.assertIn("ROOT-TAIL", str(calls[0]["system"]))
            self.assertIn("ROOT-TAIL", str(calls[1]["system"]))
            self.assertIn("ACTUAL-SKILL-TAIL", str(calls[1]["system"]))
            self.assertIn("REFERENCE-TAIL", str(calls[1]["system"]))
            self.assertNotIn("PRIVATE-EVALUATOR-SECRET", planner + responder)
            self.assertNotIn("ARCHIVE-SECRET", planner + responder)
            self.assertNotIn("...[truncated]", planner + responder)
            planner_data = json.loads(str(calls[0]["user"]).split("\n", 1)[1])
            responder_data = json.loads(str(calls[1]["user"]).split("\n", 1)[1])
            self.assertEqual(planner_data, responder_data)
            self.assertEqual(planner_data["project_state"]["state"], "STATE-DATA-TAIL")
            self.assertNotIn("state_fixture", planner_data)
            self.assertEqual(
                sources,
                ["skills/actual-route/SKILL.md", "references/actual-reference.md"],
            )
            self.assertTrue(verdict["pass"])

    def test_wrong_missing_and_extra_routes_fail_after_blind_selection(self) -> None:
        plans = {
            "missing": [],
            "wrong": ["skills/extra-route/SKILL.md"],
            "extra": [
                "skills/actual-route/SKILL.md",
                "skills/extra-route/SKILL.md",
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = base_case()
            make_root(root, case)
            snapshot = self.snapshot(root)
            provider, endpoint, model = eval_run.resolve_provider(
                "anthropic", "global_en", None
            )
            for label, sources in plans.items():
                with self.subTest(label=label), mock.patch.object(
                    eval_run,
                    "call_api",
                    return_value=json.dumps({"sources": sources}),
                ) as call:
                    with self.assertRaisesRegex(
                        eval_run.HarnessError, "route mismatch"
                    ):
                        eval_run.discover_sources(
                            snapshot,
                            case,
                            model,
                            "key",
                            provider,
                            endpoint,
                        )
                    call.assert_called_once()

    def test_duplicate_unknown_and_contract_smuggling_plans_fail_closed(self) -> None:
        plans = (
            {"sources": ["skills/actual-route/SKILL.md"] * 2},
            {"sources": ["references/missing.md"]},
            {"sources": ["skills/actual-route/SKILL.md"], "reason": "trust me"},
            {"sources": ["skills/actual-route/SKILL.md"] * 25},
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = base_case()
            make_root(root, case)
            snapshot = self.snapshot(root)
            provider, endpoint, model = eval_run.resolve_provider(
                "anthropic", "global_en", None
            )
            for plan in plans:
                with self.subTest(plan=plan), mock.patch.object(
                    eval_run, "call_api", return_value=json.dumps(plan)
                ):
                    with self.assertRaises(eval_run.HarnessError):
                        eval_run.discover_sources(
                            snapshot, case, model, "key", provider, endpoint
                        )

    def test_explicit_roles_fail_on_unclassified_files_and_hide_evaluator_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            write(root, "references/new-private-rubric.md", "NEW-EVALUATOR-SECRET")
            with self.assertRaisesRegex(
                eval_run.HarnessError, "no explicit role"
            ):
                self.snapshot(root)

            write_manifest(
                root,
                role_overrides={
                    "references/private-rubric.md": "evaluator",
                    "references/new-private-rubric.md": "evaluator",
                },
            )
            snapshot = self.snapshot(root)
            catalog = eval_run.source_catalog(snapshot)
            self.assertNotIn("references/private-rubric.md", catalog)
            self.assertNotIn("references/new-private-rubric.md", catalog)
            planner = "\n".join(eval_run.planner_prompt(snapshot, base_case()))
            responder = eval_run.responder_context(
                snapshot, ["references/actual-reference.md"]
            )
            self.assertNotIn("PRIVATE-EVALUATOR-SECRET", planner + responder)
            self.assertNotIn("NEW-EVALUATOR-SECRET", planner + responder)

    def test_manifest_digest_and_physical_aliases_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            write(root, "references/actual-reference.md", "tampered")
            with self.assertRaisesRegex(eval_run.HarnessError, "digest"):
                self.snapshot(root)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            alias = root / "references" / "rubric-hardlink.md"
            try:
                os.link(root / "references" / "eval-rubric.md", alias)
            except OSError as exc:
                self.skipTest(f"hard links unavailable: {exc}")
            write_manifest(
                root,
                role_overrides={
                    "references/private-rubric.md": "evaluator",
                    "references/rubric-hardlink.md": "responder",
                },
            )
            with self.assertRaisesRegex(eval_run.HarnessError, "physical file alias"):
                self.snapshot(root)

    def test_symbolic_alias_cannot_cross_the_repository_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent / "repo"
            root.mkdir()
            make_root(root)
            outside = parent / "outside.md"
            outside.write_text("OUTSIDE-SECRET", encoding="utf-8")
            alias = root / "references" / "actual-reference.md"
            alias.unlink()
            try:
                alias.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")
            write_manifest(
                root,
                role_overrides={"references/private-rubric.md": "evaluator"},
            )
            with self.assertRaisesRegex(
                eval_run.HarnessError,
                "symbolic link, junction, or reparse point|escapes",
            ):
                self.snapshot(root)

    def test_fixture_is_strict_json_data_under_one_dedicated_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            snapshot = self.snapshot(root)
            for bad in (
                "skills/actual-route/SKILL.md",
                "references/actual-reference.md",
                "../outside.json",
                "evals/evals.json",
            ):
                with self.subTest(path=bad), self.assertRaises(eval_run.HarnessError):
                    eval_run._state_fixture_data(
                        snapshot,
                        base_case(state_fixture=bad),
                    )

            write(root, "evals/fixtures/state.json", "[]")
            write_manifest(
                root,
                role_overrides={"references/private-rubric.md": "evaluator"},
            )
            snapshot = self.snapshot(root)
            with self.assertRaisesRegex(eval_run.HarnessError, "JSON object"):
                eval_run._state_fixture_data(snapshot, base_case())

    def test_fixture_path_is_never_serialized_to_planner_or_responder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            snapshot = self.snapshot(root)
            planner = eval_run.planner_prompt(snapshot, base_case())[1]
            responder = eval_run.responder_user_input(snapshot, base_case())
            for payload in (planner, responder):
                self.assertNotIn("evals/fixtures/state.json", payload)
                decoded = json.loads(payload.split("\n", 1)[1])
                self.assertEqual(decoded["project_state"]["state"], "STATE-DATA-TAIL")

    def test_frozen_bytes_are_used_and_post_snapshot_changes_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            snapshot = self.snapshot(root)
            target = root / "references" / "actual-reference.md"
            target.write_text("MUTATED-AFTER-SNAPSHOT", encoding="utf-8")
            context = eval_run.responder_context(
                snapshot, ["references/actual-reference.md"]
            )
            self.assertIn("REFERENCE-TAIL", context)
            self.assertNotIn("MUTATED-AFTER-SNAPSHOT", context)
            with self.assertRaisesRegex(eval_run.HarnessError, "changed after snapshot"):
                eval_run.verify_snapshot_unchanged(snapshot)
            with self.assertRaises(TypeError):
                snapshot.files["forged"] = snapshot.files["SKILL.md"]  # type: ignore[index]

    def test_post_snapshot_source_addition_and_removal_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            snapshot = self.snapshot(root)
            write(root, "references/added-after-freeze.md", "late source")
            with self.assertRaisesRegex(
                eval_run.HarnessError, "source set changed.*added"
            ):
                eval_run.verify_snapshot_unchanged(snapshot)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            snapshot = self.snapshot(root)
            (root / "references" / "actual-reference.md").unlink()
            with self.assertRaisesRegex(
                eval_run.HarnessError, "source set changed.*removed"
            ):
                eval_run.verify_snapshot_unchanged(snapshot)

    def test_canonical_eval_and_rubric_digests_block_semantic_gutting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            write(
                root,
                "references/eval-rubric.md",
                "0 to 3. 0-4.\nDimensions: "
                + ", ".join(eval_run.SEQUENCE_DIMENSIONS)
                + ".\n",
            )
            write_manifest(
                root,
                role_overrides={"references/private-rubric.md": "evaluator"},
            )
            eval_digest = hashlib.sha256(
                (root / "evals" / "evals.json").read_bytes()
            ).hexdigest()
            with mock.patch.object(eval_run, "EXPECTED_EVALS_SHA256", eval_digest):
                with self.assertRaisesRegex(
                    eval_run.HarnessError, "canonical evaluation contract changed"
                ):
                    eval_run.freeze_repository(root)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gutted = base_case(assertions=["generic"], expected_output="generic")
            make_root(root, gutted)
            rubric_digest = hashlib.sha256(
                (root / "references" / "eval-rubric.md").read_bytes()
            ).hexdigest()
            with mock.patch.object(eval_run, "EXPECTED_RUBRIC_SHA256", rubric_digest):
                with self.assertRaisesRegex(
                    eval_run.HarnessError, "canonical evaluation contract changed"
                ):
                    eval_run.freeze_repository(root)

    def test_case_contract_rejects_materially_empty_or_duplicate_fields(self) -> None:
        bad_cases = (
            base_case(assertions=[]),
            base_case(expected_output=""),
            base_case(failure_mode=""),
            base_case(skills_expected_to_activate=["actual-route", "actual-route"]),
            base_case(required_output_sections=["x", "x"]),
        )
        for case in bad_cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                make_root(root, case)
                snapshot = self.snapshot(root)
                with self.assertRaises(eval_run.HarnessError):
                    eval_run.validate_case_contract(snapshot, [case])

    def test_provenance_is_bound_to_frozen_paths_and_digests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = eval_run.freeze_repository(REPO_ROOT)
            paths = [
                "skills/seedance-prompt/SKILL.md",
                "references/prompt-compiler.md",
            ]
            provenance = eval_run.source_provenance(snapshot, paths)
            responder_manifest = {
                path: source.sha256
                for path, source in eval_run.source_catalog(snapshot).items()
            }
            repository_manifest = eval_run.frozen_repository_manifest(snapshot)
            repository_roles = eval_run.frozen_repository_roles(snapshot)
            row = {
                "id": "one",
                "status": "scored",
                "score": 3,
                "pass": True,
                "sequence": False,
                "critical": False,
                "notes": "ok",
                "dimension_scores": [],
                "sources": provenance,
            }
            self.assertEqual(
                eval_run._row_integrity_errors(row, 0, responder_manifest), []
            )

            invalid = (
                [{"path": "references/../eval-rubric.md", "sha256": "0" * 64}],
                [{"path": "references/missing.md", "sha256": "0" * 64}],
                [{"path": paths[0], "sha256": "0" * 64}],
                [provenance[0], provenance[0]],
            )
            for sources in invalid:
                with self.subTest(sources=sources):
                    errors = eval_run._row_integrity_errors(
                        {**row, "sources": sources}, 0, responder_manifest
                    )
                    self.assertTrue(errors)

            release_rows = []
            for index, case in enumerate(eval_run.load_cases(snapshot)):
                sequence = eval_run.is_sequence_case(case)
                release_rows.append(
                    {
                        "id": case["id"],
                        "status": "scored",
                        "score": 4 if sequence else 3,
                        "pass": True,
                        "sequence": sequence,
                        "critical": case.get("critical", False),
                        "notes": "ok",
                        "dimension_scores": (
                            [
                                {"dimension": dimension, "score": 4}
                                for dimension in eval_run.SEQUENCE_DIMENSIONS
                            ]
                            if sequence
                            else []
                        ),
                        "sources": provenance if index == 0 else [],
                    }
                )

            ledger = Path(tmp) / "ledger.md"
            report = eval_run.write_ledger(
                ledger,
                release_rows,
                "model",
                "2026-08-01",
                "anthropic",
                "global_en",
                release_eligible=True,
                snapshot=snapshot,
            )
            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(report["release_verdict"], "PASS")
            self.assertEqual(
                report["repository_sha256"],
                eval_run.frozen_repository_sha256(
                    repository_manifest, repository_roles
                ),
            )
            self.assertIn(provenance[0]["sha256"], text)
            self.assertIn("skills/seedance-prompt/SKILL.md@", text)
            self.assertIn("Frozen repository provenance: **BOUND**", text)
            self.assertIn("archive=23", text)
            self.assertIn("evaluator=4", text)
            self.assertIn("fixture=1", text)
            self.assertIn("responder=90", text)
            self.assertIn("root=1", text)

            mismatched_repository = dict(repository_manifest)
            mismatched_repository[paths[0]] = "0" * 64
            mismatched = eval_run.assess_run(
                [row],
                expected_cases={"one": {"sequence": False, "critical": False}},
                total_expected=1,
                release_eligible=True,
                repository_manifest=mismatched_repository,
                repository_roles=repository_roles,
                snapshot=snapshot,
            )
            self.assertEqual(mismatched["release_verdict"], "FAIL")
            self.assertTrue(
                any(
                    "cannot be combined" in error
                    for error in mismatched["integrity_errors"]
                )
            )

    def test_release_assessment_cannot_omit_the_frozen_manifest(self) -> None:
        incomplete_manifest = {
            eval_run.SOURCE_MANIFEST_PATH: "0" * 64,
            "SKILL.md": "0" * 64,
            "evals/evals.json": "0" * 64,
            "references/eval-rubric.md": "0" * 64,
            "scripts/eval_run.py": "0" * 64,
        }
        incomplete_roles = {
            eval_run.SOURCE_MANIFEST_PATH: "evaluator",
            "SKILL.md": "root",
            "evals/evals.json": "evaluator",
            "references/eval-rubric.md": "evaluator",
            "scripts/eval_run.py": "evaluator",
        }
        row = {
            "id": "one",
            "status": "scored",
            "score": 3,
            "pass": True,
            "sequence": False,
            "critical": False,
            "notes": "forged",
            "dimension_scores": [],
            "sources": [],
        }
        report = eval_run.assess_run(
            [row],
            expected_cases={"one": {"sequence": False, "critical": False}},
            total_expected=1,
            release_eligible=True,
            source_manifest={},
            repository_manifest=incomplete_manifest,
            repository_roles=incomplete_roles,
        )
        self.assertEqual(report["release_verdict"], "FAIL")
        self.assertIsNone(report["repository_sha256"])
        self.assertTrue(
            any(
                "verified complete frozen repository snapshot" in error
                for error in report["integrity_errors"]
            )
        )

    def test_mixed_type_repository_roles_fail_without_a_traceback(self) -> None:
        manifest = {
            eval_run.SOURCE_MANIFEST_PATH: "0" * 64,
            "SKILL.md": "0" * 64,
            "evals/evals.json": "0" * 64,
            "references/eval-rubric.md": "0" * 64,
            "scripts/eval_run.py": "0" * 64,
        }
        roles: dict[object, str] = {
            eval_run.SOURCE_MANIFEST_PATH: "evaluator",
            "SKILL.md": "root",
            "evals/evals.json": "evaluator",
            "references/eval-rubric.md": "evaluator",
            "scripts/eval_run.py": "evaluator",
            1: "evaluator",
            "extra.md": "evaluator",
        }
        report = eval_run.assess_run(
            [
                {
                    "id": "one",
                    "score": 3,
                    "pass": True,
                    "sequence": False,
                    "critical": False,
                    "notes": "forged",
                    "dimension_scores": [],
                    "sources": [],
                }
            ],
            expected_cases={"one": {"sequence": False, "critical": False}},
            total_expected=1,
            release_eligible=True,
            source_manifest={},
            repository_manifest=manifest,
            repository_roles=roles,  # type: ignore[arg-type]
        )
        self.assertEqual(report["release_verdict"], "FAIL")
        self.assertTrue(
            any("non-string path" in error for error in report["integrity_errors"])
        )
        self.assertTrue(
            any("unexpected paths: extra.md" in error for error in report["integrity_errors"])
        )

    def test_constructed_snapshot_cannot_reassign_manifest_roles(self) -> None:
        snapshot = eval_run.freeze_repository(REPO_ROOT)
        files = dict(snapshot.files)
        target = "references/prompt-compiler.md"
        files[target] = replace(files[target], role="evaluator")
        forged = replace(snapshot, files=MappingProxyType(files))
        report = eval_run.assess_run(
            [
                {
                    "id": "one",
                    "score": 3,
                    "pass": True,
                    "sequence": False,
                    "critical": False,
                    "notes": "forged",
                    "dimension_scores": [],
                    "sources": [],
                }
            ],
            expected_cases={"one": {"sequence": False, "critical": False}},
            total_expected=1,
            release_eligible=True,
            snapshot=forged,
        )

        self.assertEqual(report["release_verdict"], "FAIL")
        self.assertIsNone(report["repository_sha256"])
        self.assertTrue(
            any(
                "role or manifest metadata changed" in error
                for error in report["integrity_errors"]
            )
        )

    def test_constructed_snapshot_mixed_metadata_types_fail_cleanly(self) -> None:
        snapshot = eval_run.freeze_repository(REPO_ROOT)
        target = "references/prompt-compiler.md"
        mutations: list[dict[object, eval_run.FrozenFile]] = []

        non_string_path: dict[object, eval_run.FrozenFile] = dict(snapshot.files)
        non_string_path[1] = non_string_path[target]
        mutations.append(non_string_path)

        non_string_role: dict[object, eval_run.FrozenFile] = dict(snapshot.files)
        non_string_role[target] = replace(
            non_string_role[target],
            role=["evaluator"],  # type: ignore[arg-type]
        )
        mutations.append(non_string_role)

        for files in mutations:
            with self.subTest(files=files):
                forged = replace(snapshot, files=MappingProxyType(files))
                report = eval_run.assess_run(
                    [],
                    expected_cases={},
                    total_expected=0,
                    release_eligible=True,
                    snapshot=forged,
                )
                self.assertEqual(report["release_verdict"], "FAIL")
                self.assertIsNone(report["repository_sha256"])
                self.assertTrue(
                    any(
                        "frozen repository" in error
                        or "role or manifest metadata" in error
                        for error in report["integrity_errors"]
                    )
                )

    def test_frozen_evaluator_matches_the_code_object_python_executed(self) -> None:
        snapshot = eval_run.freeze_repository(REPO_ROOT)
        evaluator = snapshot.require("scripts/eval_run.py", "evaluator")
        eval_run._verify_evaluator_execution_identity(evaluator)

        substituted_code = compile(
            "SUBSTITUTED = True\n",
            eval_run._EXECUTED_EVALUATOR_CODE.co_filename,
            "exec",
        )
        with (
            mock.patch.object(
                eval_run, "_EXECUTED_EVALUATOR_CODE", substituted_code
            ),
            self.assertRaisesRegex(eval_run.HarnessError, "executed evaluator code"),
        ):
            eval_run._verify_evaluator_execution_identity(evaluator)

        with (
            mock.patch.object(
                eval_run, "_EXECUTED_EVALUATOR_SOURCE_SHA256", "0" * 64
            ),
            self.assertRaisesRegex(eval_run.HarnessError, "source digest"),
        ):
            eval_run._verify_evaluator_execution_identity(evaluator)

        with (
            mock.patch.object(
                eval_run, "_EXECUTED_EVALUATOR_PATH", REPO_ROOT / "README.md"
            ),
            self.assertRaisesRegex(eval_run.HarnessError, "executed evaluator path"),
        ):
            eval_run._verify_evaluator_execution_identity(evaluator)

    def test_ledger_rechecks_snapshot_after_assessment_before_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            snapshot = self.snapshot(root)
            ledger = root / "ledger.md"
            target = root / "SKILL.md"
            real_command_lines = eval_run._regeneration_command_lines

            def mutate_during_render(argv: list[str] | None) -> list[str]:
                target.write_text("MUTATED-AFTER-ASSESSMENT", encoding="utf-8")
                return real_command_lines(argv)

            with (
                mock.patch.object(
                    eval_run,
                    "_regeneration_command_lines",
                    side_effect=mutate_during_render,
                ),
                self.assertRaisesRegex(eval_run.HarnessError, "changed after snapshot"),
            ):
                eval_run.write_ledger(
                    ledger,
                    [
                        {
                            "id": "one",
                            "score": 3,
                            "pass": True,
                            "sequence": False,
                            "critical": False,
                            "notes": "ok",
                            "dimension_scores": [],
                            "sources": [],
                        }
                    ],
                    "model",
                    "2026-08-01",
                    "anthropic",
                    "global_en",
                    expected_cases={
                        "one": {"sequence": False, "critical": False}
                    },
                    total_expected=1,
                    release_eligible=False,
                    snapshot=snapshot,
                )
            self.assertFalse(ledger.exists())
            self.assertEqual(list(root.glob(".ledger.md.*.tmp")), [])

    def test_ledger_rechecks_snapshot_after_replace_and_rolls_back(self) -> None:
        for relative in ("SKILL.md", "evals/fixtures/state.json"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                make_root(root)
                snapshot = self.snapshot(root)
                ledger = root / "ledger.md"
                ledger.write_text("STALE LEDGER\n", encoding="utf-8")
                target = root / relative
                real_replace = eval_run.os.replace
                replace_count = 0

                def mutate_during_replace(source: Path, destination: Path) -> None:
                    nonlocal replace_count
                    if replace_count == 0:
                        target.write_text("MUTATED-DURING-REPLACE", encoding="utf-8")
                    replace_count += 1
                    real_replace(source, destination)

                with (
                    mock.patch.object(
                        eval_run.os,
                        "replace",
                        side_effect=mutate_during_replace,
                    ),
                    self.assertRaisesRegex(
                        eval_run.HarnessError, "changed after snapshot"
                    ),
                ):
                    eval_run.write_ledger(
                        ledger,
                        [
                            {
                                "id": "one",
                                "score": 3,
                                "pass": True,
                                "sequence": False,
                                "critical": False,
                                "notes": "ok",
                                "dimension_scores": [],
                                "sources": [],
                            }
                        ],
                        "model",
                        "2026-08-01",
                        "anthropic",
                        "global_en",
                        expected_cases={
                            "one": {"sequence": False, "critical": False}
                        },
                        total_expected=1,
                        release_eligible=False,
                        snapshot=snapshot,
                    )

                self.assertEqual(
                    ledger.read_text(encoding="utf-8"), "STALE LEDGER\n"
                )
                self.assertEqual(list(root.glob(".ledger.md.*.tmp")), [])
                self.assertEqual(list(root.glob(".ledger.md.*.rollback")), [])

    def test_ledger_destination_cannot_overwrite_a_frozen_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            snapshot = self.snapshot(root)
            target = root / "SKILL.md"
            original = target.read_text(encoding="utf-8")

            with self.assertRaisesRegex(
                eval_run.HarnessError, "would overwrite frozen input"
            ):
                eval_run.write_ledger(
                    target,
                    [],
                    "model",
                    "2026-08-01",
                    "anthropic",
                    "global_en",
                    release_eligible=False,
                    snapshot=snapshot,
                )

            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_repository_provenance_binds_root_fixture_evaluator_and_manifest(self) -> None:
        for relative in (
            "SKILL.md",
            "evals/fixtures/state.json",
            "scripts/eval_run.py",
            "references/eval-rubric.md",
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                make_root(root)
                baseline = self.snapshot(root)
                baseline_digest = eval_run.frozen_repository_sha256(
                    eval_run.frozen_repository_manifest(baseline),
                    eval_run.frozen_repository_roles(baseline),
                )
                target = root / relative
                target.write_text(
                    target.read_text(encoding="utf-8") + "\nchanged",
                    encoding="utf-8",
                )
                write_manifest(
                    root,
                    role_overrides={"references/private-rubric.md": "evaluator"},
                )
                changed = self.snapshot(root)
                self.assertNotEqual(
                    baseline_digest,
                    eval_run.frozen_repository_sha256(
                        eval_run.frozen_repository_manifest(changed),
                        eval_run.frozen_repository_roles(changed),
                    ),
                )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            baseline = self.snapshot(root)
            baseline_digest = eval_run.frozen_repository_sha256(
                eval_run.frozen_repository_manifest(baseline),
                eval_run.frozen_repository_roles(baseline),
            )
            manifest_path = root / eval_run.SOURCE_MANIFEST_PATH
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )
            changed = self.snapshot(root)
            self.assertNotEqual(
                baseline_digest,
                eval_run.frozen_repository_sha256(
                    eval_run.frozen_repository_manifest(changed),
                    eval_run.frozen_repository_roles(changed),
                ),
            )

    def test_filesystem_bootstrap_failure_replaces_stale_ledger_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("evals").mkdir()
            ledger = root / "evals" / "eval-run-ledger.md"
            ledger.write_text("STALE PASS", encoding="utf-8")
            output = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "eval_run.py",
                        str(root),
                        "--ledger",
                        "evals/eval-run-ledger.md",
                    ],
                ),
                mock.patch.object(
                    eval_run,
                    "freeze_repository",
                    side_effect=eval_run.HarnessError(
                        "disk denied\r\n# FORGED RELEASE PASS"
                    ),
                ),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(code, 2)
            self.assertNotIn("STALE PASS", text)
            self.assertIn("Release verdict: **NOT ELIGIBLE**", text)
            self.assertIn(r"| \_\_harness\_\_ | harness_error |", text)
            self.assertIn("| n/a | n/a |", text)
            self.assertEqual(text.count("# Eval Run Ledger"), 1)
            self.assertNotIn("\n# FORGED RELEASE PASS\n", text)
            self.assertNotIn("Traceback", output.getvalue())

    def test_bootstrap_failure_cannot_overwrite_or_alias_repository_input(self) -> None:
        for use_alias in (False, True):
            with self.subTest(use_alias=use_alias), tempfile.TemporaryDirectory() as tmp:
                parent = Path(tmp)
                root = parent / "repo"
                root.mkdir()
                skill = root / "SKILL.md"
                original = "# valuable root input\n"
                skill.write_text(original, encoding="utf-8")
                ledger = skill
                if use_alias:
                    ledger = parent / "ledger-alias.md"
                    os.link(skill, ledger)
                output = io.StringIO()
                with (
                    mock.patch.object(
                        sys,
                        "argv",
                        [
                            "eval_run.py",
                            str(root),
                            "--ledger",
                            str(ledger),
                        ],
                    ),
                    redirect_stdout(output),
                ):
                    code = eval_run.main()

                self.assertEqual(code, 2)
                self.assertEqual(skill.read_text(encoding="utf-8"), original)
                self.assertEqual(ledger.read_text(encoding="utf-8"), original)
                self.assertIn("existing artifact preserved", output.getvalue())

    def test_missing_repository_replaces_an_absolute_stale_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            missing_root = parent / "missing-repository"
            ledger = parent / "absolute-ledger.md"
            ledger.write_text("STALE PASS", encoding="utf-8")
            output = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "eval_run.py",
                        str(missing_root),
                        "--ledger",
                        str(ledger.resolve()),
                    ],
                ),
                redirect_stdout(output),
            ):
                code = eval_run.main()

            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(code, 2)
            self.assertNotIn("STALE PASS", text)
            self.assertIn("repository root failure", text)
            self.assertIn("Release verdict: **NOT ELIGIBLE**", text)
            self.assertNotIn("Traceback", output.getvalue())

    def test_main_persists_frozen_provenance_and_provider_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = base_case(expected_sequence_relation="standalone")
            make_root(root, case)
            frozen = self.snapshot(root)
            snapshot = eval_run.FrozenRepository(
                root=frozen.root,
                files=frozen.files,
                manifest=frozen.manifest,
                canonical_contract_bound=True,
                evaluator_execution_bound=True,
            )
            verdict = sequence_verdict(case)
            ledger = root / "evals" / "eval-run-ledger.md"
            output = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "eval_run.py",
                        str(root),
                        "--provider",
                        "minimax",
                        "--region",
                        "cn_zh",
                        "--model",
                        "MiniMax-M2.7",
                        "--ledger",
                        "evals/eval-run-ledger.md",
                    ],
                ),
                mock.patch.dict(
                    os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True
                ),
                mock.patch.object(
                    eval_run, "freeze_repository", return_value=snapshot
                ),
                mock.patch.object(
                    eval_run, "_verify_canonical_evaluation_contract"
                ),
                mock.patch.object(
                    eval_run, "_verify_evaluator_execution_identity"
                ),
                mock.patch.object(
                    eval_run,
                    "run_case",
                    return_value=(
                        verdict,
                        [
                            "skills/actual-route/SKILL.md",
                            "references/actual-reference.md",
                        ],
                    ),
                ) as run,
                redirect_stdout(output),
            ):
                code = eval_run.main()

            self.assertEqual(code, 0)
            args = run.call_args.args
            self.assertEqual(args[2:4], ("MiniMax-M2.7", "MiniMax-M2.7"))
            self.assertIs(args[6], eval_run.PROVIDER_CONFIGS["minimax"])
            self.assertEqual(
                args[7], "https://api.minimaxi.com/anthropic/v1/messages"
            )
            text = ledger.read_text(encoding="utf-8")
            digest = snapshot.require(
                "skills/actual-route/SKILL.md", "responder"
            ).sha256
            self.assertIn(digest, text)
            self.assertIn("Release verdict: **PASS**", text)
            self.assertNotIn("state_fixture", text)

    def test_manifest_rejects_boolean_versions_unhashable_roles_and_empty_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            manifest_path = root / eval_run.SOURCE_MANIFEST_PATH
            baseline = json.loads(manifest_path.read_text(encoding="utf-8"))
            invalid_documents = (
                {**baseline, "version": True},
                {**baseline, "version": 1.0},
                {**baseline, "sources": []},
                {
                    **baseline,
                    "sources": [
                        {**baseline["sources"][0], "role": []},
                        *baseline["sources"][1:],
                    ],
                },
            )
            for document in invalid_documents:
                with self.subTest(document=document):
                    write(
                        root,
                        eval_run.SOURCE_MANIFEST_PATH,
                        json.dumps(document),
                    )
                    with self.assertRaises(eval_run.HarnessError):
                        self.snapshot(root)

    def test_manifest_rejects_portable_aliases_and_noncanonical_components(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            manifest_path = root / eval_run.SOURCE_MANIFEST_PATH
            baseline = json.loads(manifest_path.read_text(encoding="utf-8"))
            root_entry = next(
                entry for entry in baseline["sources"] if entry["path"] == "SKILL.md"
            )
            aliased = {
                **baseline,
                "sources": [
                    *baseline["sources"],
                    {**root_entry, "path": "skill.md"},
                ],
            }
            write(
                root,
                eval_run.SOURCE_MANIFEST_PATH,
                json.dumps(aliased),
            )
            with self.assertRaisesRegex(eval_run.HarnessError, "alias"):
                self.snapshot(root)

            for bad_path in (
                r"references\actual-reference.md",
                "references/NUL.md",
                "references/cafe\u0301.md",
                "references/hidden\u200d.md",
            ):
                with self.subTest(path=bad_path):
                    mutated = json.loads(json.dumps(baseline))
                    mutated["sources"][0]["path"] = bad_path
                    write(
                        root,
                        eval_run.SOURCE_MANIFEST_PATH,
                        json.dumps(mutated),
                    )
                    with self.assertRaises(eval_run.HarnessError):
                        self.snapshot(root)

    def test_freezing_and_prompt_assembly_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            write(root, "SKILL.md", "x" * (eval_run.MAX_FROZEN_SOURCE_BYTES + 1))
            write_manifest(
                root,
                role_overrides={"references/private-rubric.md": "evaluator"},
            )
            with self.assertRaisesRegex(eval_run.HarnessError, "exceeds"):
                self.snapshot(root)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            with mock.patch.object(eval_run, "MAX_FROZEN_REPOSITORY_BYTES", 100):
                with self.assertRaisesRegex(eval_run.HarnessError, "repository exceeds"):
                    self.snapshot(root)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            snapshot = self.snapshot(root)
            with mock.patch.object(eval_run, "MAX_RESPONDER_CONTEXT_CHARACTERS", 100):
                with self.assertRaisesRegex(eval_run.HarnessError, "context exceeds"):
                    eval_run.planner_prompt(snapshot, base_case())
                with self.assertRaisesRegex(eval_run.HarnessError, "context exceeds"):
                    eval_run.responder_context(
                        snapshot, ["references/actual-reference.md"]
                    )

    def test_final_snapshot_verification_never_uses_unbounded_read_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_root(root)
            snapshot = self.snapshot(root)
            with mock.patch.object(
                Path,
                "read_bytes",
                side_effect=AssertionError("unbounded read_bytes is forbidden"),
            ):
                eval_run.verify_snapshot_unchanged(snapshot)

    def test_explicit_empty_fixture_and_oversized_case_text_fail_closed(self) -> None:
        bad_cases = (
            base_case(state_fixture=""),
            base_case(expected_output="x" * (eval_run.MAX_PROMPT_CHARACTERS + 1)),
            base_case(failure_mode="x" * (eval_run.MAX_PROMPT_CHARACTERS + 1)),
        )
        for case in bad_cases:
            with self.subTest(case_id=case["id"]), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                make_root(root, case)
                snapshot = self.snapshot(root)
                with self.assertRaises(eval_run.HarnessError):
                    eval_run.validate_case_contract(snapshot, [case])


if __name__ == "__main__":
    unittest.main()

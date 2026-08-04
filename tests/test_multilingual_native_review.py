from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import vocab_schema_check  # noqa: E402


class NativeReviewBoundaryTests(unittest.TestCase):
    def test_legacy_locale_essentialism_is_not_shipped(self) -> None:
        banned = {
            "skills/seedance-vocab-zh/SKILL.md": (
                "choosing that compression and its culture",
            ),
            "skills/seedance-vocab-ja/SKILL.md": (
                "lives closest to the anime tradition",
                "read naturally for ja-JP",
            ),
            "skills/seedance-vocab-ko/SKILL.md": (
                "a feeling-culture with exacting visual taste",
                "exactly what they felt",
            ),
            "skills/seedance-vocab-es/SKILL.md": (
                "Spanish carries rhythm",
                "keeps its musicality",
            ),
            "skills/seedance-vocab-ru/SKILL.md": (
                "fought the hardest dialogue battle",
            ),
        }
        for relative, phrases in banned.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(relative=relative, phrase=phrase):
                    self.assertNotIn(phrase, text)
            self.assertIn("independent review artifact is empty", text)

    def test_pending_specimens_avoid_reviewed_scene_defects(self) -> None:
        fixture = json.loads(
            (ROOT / "evals/multilingual-native-review.json").read_text(encoding="utf-8")
        )
        cases = {case["locale"]: case for case in fixture["cases"]}
        self.assertNotIn("小吃店临街档口", cases["zh-CN"]["candidate_prompt"])
        self.assertNotIn("가방끈", cases["ko-KR"]["candidate_prompt"])
        self.assertNotIn("남은 반찬", cases["ko-KR"]["candidate_prompt"])
        self.assertEqual(
            [case["creative_lens_hypothesis"]["label"] for case in fixture["cases"]],
            ["递碗后的停顿", "手が離れた後の二拍", "장갑 봉투를 건 뒤의 멈춤"],
        )
        for case in fixture["cases"]:
            self.assertEqual(case["fixture_revision"], 2)
            self.assertEqual(case["review_round"], 2)

    def test_repository_declares_machine_checked_human_review_boundary(self) -> None:
        fixture_path = ROOT / "evals/multilingual-native-review.json"
        evidence_path = ROOT / "evals/multilingual-native-review-evidence.json"
        rubric_path = ROOT / "references/multilingual-native-review.md"

        self.assertTrue(fixture_path.is_file(), "missing native-review fixture")
        self.assertTrue(evidence_path.is_file(), "missing native-review evidence artifact")
        self.assertTrue(rubric_path.is_file(), "missing native-review rubric")

        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertEqual(fixture["review_state"], "pending_native_review")
        self.assertEqual(fixture["model_output_state"], "not_evaluated")
        self.assertEqual(fixture["generated_video_state"], "not_evaluated")
        self.assertFalse(fixture["native_quality_verified"])
        self.assertIn(
            "literal cross-locale realization overlap",
            fixture["static_validation_scope"],
        )
        self.assertNotIn(
            "lexical and structural exact-copy resistance",
            fixture["static_validation_scope"],
        )
        self.assertIn(
            "semantic differentiation across locales",
            fixture["static_checks_do_not_establish"],
        )
        self.assertIn(
            "reference-role semantic correctness",
            fixture["static_checks_do_not_establish"],
        )
        self.assertIn("reviewer identity", fixture["static_checks_do_not_establish"])
        workflow = (ROOT / ".github/workflows/validate-skills.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("run: python scripts/validate_repo.py", workflow)
        canonical_runner = (ROOT / "scripts/validate_repo.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '("scripts/vocab_schema_check.py", "--strict")', canonical_runner
        )
        self.assertIn(
            '("-m", "unittest", "discover", "-s", "tests", "-v")',
            canonical_runner,
        )
        required_file_validator = (ROOT / "scripts/validate_skills.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"tests/test_multilingual_native_review.py"', required_file_validator)
        self.assertEqual(vocab_schema_check.validate_native_review(ROOT), [])

        result = subprocess.run(
            [sys.executable, "-B", "scripts/vocab_schema_check.py", "--strict"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Native-language quality remains pending human review", result.stdout)

    @staticmethod
    def _valid_review_set(fixture: dict, case_index: int = 0) -> dict:
        case = fixture["cases"][case_index]
        reviewers = []
        roles = (
            "target-locale language editor",
            "target-locale culture and production reviewer",
        )
        for reviewer_index, role in enumerate(roles, start=1):
            criteria = []
            for dimension in fixture["rubric_dimensions"]:
                if dimension["owner"] not in ("both", role):
                    continue
                criteria.append(
                    {
                        "criterion_id": dimension["id"],
                        "score_0_to_3": 3,
                        "quoted_source": "candidate_prompt",
                        "quoted_span": case["criterion_evidence_anchors"][
                            dimension["id"]
                        ][0],
                        "reason": (
                            f"{dimension['id']}: The pinned {dimension['id']} excerpt "
                            "supports this synthetic structural test score."
                        ),
                        "proposed_revision": "",
                    }
                )
            reviewers.append(
                {
                    "reviewer_id": f"reviewer-{reviewer_index}-{case['locale']}",
                    "reviewer_role": role,
                    "authorship_disclosure": "not_specimen_author",
                    "is_specimen_author": False,
                    "conflict_disclosure": "none",
                    "has_material_conflict": False,
                    "criterion_results": criteria,
                    "verdict": "pass",
                }
            )
        return {
            "case_id": case["id"],
            "locale": case["locale"],
            "review_evidence_schema_version": "1.0",
            "fixture_schema_version": fixture["schema_version"],
            "fixture_revision": case["fixture_revision"],
            "review_round": case["review_round"],
            "candidate_sha256": case["candidate_sha256"],
            "common_brief_sha256": case["common_brief_sha256"],
            "review_input_sha256": case["review_input_sha256"],
            "rubric_sha256": fixture["rubric_sha256"],
            "review_protocol_sha256": fixture["review_protocol_sha256"],
            "reference_token_bytes": case["reference_token_bytes"],
            "reviewers": reviewers,
            "disagreement": {"status": "none", "summary": ""},
            "verdict": "pass",
        }

    def _fixture_repo(self, directory: str, mutate=None, mutate_evidence=None) -> Path:
        repo = Path(directory) / "repo"
        fixture = json.loads(
            (ROOT / "evals/multilingual-native-review.json").read_text(encoding="utf-8")
        )
        evidence = json.loads(
            (ROOT / "evals/multilingual-native-review-evidence.json").read_text(
                encoding="utf-8"
            )
        )
        if mutate is not None:
            mutate(fixture)
        if mutate_evidence is not None:
            mutate_evidence(evidence, fixture)

        fixture_path = repo / "evals/multilingual-native-review.json"
        fixture_path.parent.mkdir(parents=True)
        fixture_path.write_text(
            json.dumps(fixture, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        evidence_path = repo / "evals/multilingual-native-review-evidence.json"
        evidence_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        rubric_path = repo / "references/multilingual-native-review.md"
        rubric_path.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "references/multilingual-native-review.md", rubric_path)
        for case in fixture["cases"]:
            for relative in case["source_paths"]:
                destination = repo / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, destination)
        return repo

    def _write_canonical_disclaimer(self, repo: Path) -> None:
        path = repo / vocab_schema_check.NATIVE_REVIEW_RUBRIC
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            vocab_schema_check.PUBLIC_CLAIM_CANONICAL_DISCLAIMER + "\n",
            encoding="utf-8",
        )

    def _coordinated_review_input_refresh_errors(self, mutate_case) -> list[str]:
        def mutate(fixture: dict) -> None:
            case = fixture["cases"][0]
            mutate_case(case)
            refreshed = vocab_schema_check._review_input_sha256(case)
            case["review_input_sha256"] = refreshed
            case["review_record"]["fixture_revision"] = case["fixture_revision"]
            case["review_record"]["review_round"] = case["review_round"]
            case["review_record"]["review_input_sha256"] = refreshed

        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            evidence["completed_review_sets"] = [self._valid_review_set(fixture)]

        with tempfile.TemporaryDirectory() as tmp:
            return vocab_schema_check.validate_native_review(
                self._fixture_repo(
                    tmp,
                    mutate=mutate,
                    mutate_evidence=mutate_evidence,
                )
            )

    def test_rejects_reference_token_confusable(self) -> None:
        def mutate(fixture: dict) -> None:
            fixture["cases"][0]["candidate_prompt"] = fixture["cases"][0][
                "candidate_prompt"
            ].replace("@Image1", "＠Image1")

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("byte-exact reference tokens" in error for error in errors), errors)

    def test_rejects_exact_pan_cjk_register_copy(self) -> None:
        def mutate(fixture: dict) -> None:
            fixture["cases"][1]["creative_lens_hypothesis"]["physical_realizations"] = list(
                fixture["cases"][0]["creative_lens_hypothesis"]["physical_realizations"]
            )

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("reuse exact creative-lens realizations" in error for error in errors), errors)

    def test_rejects_static_native_quality_claim(self) -> None:
        def mutate(fixture: dict) -> None:
            fixture["native_quality_verified"] = True
            fixture["review_state"] = "passed"

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("cannot claim verified native quality" in error for error in errors), errors)
        self.assertTrue(any("must remain pending_native_review" in error for error in errors), errors)

    def test_rejects_model_or_video_quality_inference(self) -> None:
        def mutate(fixture: dict) -> None:
            fixture["model_output_state"] = "passed_static_tests"
            fixture["generated_video_state"] = "passed_static_tests"

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("cannot claim model output evaluation" in error for error in errors), errors)
        self.assertTrue(any("cannot claim generated-video evaluation" in error for error in errors), errors)

    def test_rejects_creative_lens_without_physical_realizations(self) -> None:
        def mutate(fixture: dict) -> None:
            fixture["cases"][2]["creative_lens_hypothesis"]["physical_realizations"] = []

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("needs three concrete creative-lens realizations" in error for error in errors), errors)

    def test_rejects_stale_review_hash_after_candidate_edit(self) -> None:
        def mutate(fixture: dict) -> None:
            fixture["cases"][0]["candidate_prompt"] += " "

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("candidate_sha256 does not bind this revision" in error for error in errors), errors)

    def test_rejects_reference_role_swap_even_when_token_bytes_survive(self) -> None:
        def mutate(fixture: dict) -> None:
            fixture["cases"][1]["reference_bindings"][0]["role"] = "tempo_only"
            fixture["cases"][1]["reference_bindings"][2]["role"] = "identity_and_wardrobe"

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("reference role binding drifted" in error for error in errors), errors)

    def test_rejects_candidate_and_span_role_swap_with_refreshed_self_hashes(self) -> None:
        def mutate(fixture: dict) -> None:
            case = fixture["cases"][0]
            bindings = case["reference_bindings"]
            old_image_span = bindings[0]["candidate_span"]
            old_audio_span = bindings[2]["candidate_span"]
            new_image_span = "@Image1仅控制节拍"
            new_audio_span = "@Audio1锁定店主与年轻熟客的身份和衣着"
            case["candidate_prompt"] = case["candidate_prompt"].replace(
                old_image_span, new_image_span
            ).replace(old_audio_span, new_audio_span)
            bindings[0]["candidate_span"] = new_image_span
            bindings[2]["candidate_span"] = new_audio_span
            for binding in (bindings[0], bindings[2]):
                binding["candidate_span_sha256"] = hashlib.sha256(
                    binding["candidate_span"].encode("utf-8")
                ).hexdigest()
            refreshed = hashlib.sha256(case["candidate_prompt"].encode("utf-8")).hexdigest()
            case["candidate_sha256"] = refreshed
            case["review_record"]["candidate_sha256"] = refreshed

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(
            any("canonical reference binding span drifted" in error for error in errors),
            errors,
        )

    def test_rejects_source_brief_role_swap_with_refreshed_hashes(self) -> None:
        def mutate(fixture: dict) -> None:
            old = (
                "@Image1 owns identity and wardrobe. @Video1 controls camera rhythm only. "
                "@Audio1 controls tempo only."
            )
            new = (
                "@Image1 controls tempo only. @Video1 controls camera rhythm only. "
                "@Audio1 owns identity and wardrobe."
            )
            for case in fixture["cases"]:
                case["common_brief"] = case["common_brief"].replace(old, new)
                common_hash = hashlib.sha256(case["common_brief"].encode("utf-8")).hexdigest()
                case["common_brief_sha256"] = common_hash
                case["review_input_sha256"] = vocab_schema_check._review_input_sha256(case)
                case["review_record"]["common_brief_sha256"] = common_hash
                case["review_record"]["review_input_sha256"] = case["review_input_sha256"]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("canonical common brief drifted" in error for error in errors), errors)

    def test_rejects_coordinated_refresh_of_complete_review_input_fields(self) -> None:
        def lens_intent(case: dict) -> None:
            case["creative_lens_hypothesis"]["intent"] = (
                "A coordinated replacement lens intent that remains nonempty."
            )

        def production_action(case: dict) -> None:
            case["production_contract"]["action"] = "手停在碗沿"

        def camera_endpoint(case: dict) -> None:
            case["production_contract"]["camera_endpoint"] = "镜头从双人中景缓慢推进"

        def review_question(case: dict) -> None:
            case["language_register"]["review_question"] = (
                "Does this coordinated replacement still read naturally?"
            )

        def source_paths(case: dict) -> None:
            case["source_paths"] = list(reversed(case["source_paths"]))

        for name, mutation in (
            ("lens_intent", lens_intent),
            ("production_action", production_action),
            ("camera_endpoint", camera_endpoint),
            ("review_question", review_question),
            ("source_paths", source_paths),
        ):
            with self.subTest(field=name):
                errors = self._coordinated_review_input_refresh_errors(mutation)
            self.assertTrue(
                any("canonical review-input pin drifted" in error for error in errors),
                errors,
            )

    def test_rejects_coordinated_revision_round_and_digest_advance_without_pin(self) -> None:
        def mutate_case(case: dict) -> None:
            case["fixture_revision"] = 3
            case["review_round"] = 3
            case["creative_lens_hypothesis"]["intent"] = (
                "A revised intent submitted with a coordinated evidence refresh."
            )

        errors = self._coordinated_review_input_refresh_errors(mutate_case)
        self.assertTrue(
            any("canonical review-input pin drifted" in error for error in errors),
            errors,
        )

    def test_rejects_unrecognized_root_and_case_fields(self) -> None:
        def root_extra(fixture: dict) -> None:
            fixture["native_fluency_certified"] = False

        def case_extra(fixture: dict) -> None:
            case = fixture["cases"][0]
            case["reviewer_context_override"] = "unbound alternate context"
            refreshed = vocab_schema_check._review_input_sha256(case)
            case["review_input_sha256"] = refreshed
            case["review_record"]["review_input_sha256"] = refreshed

        for mutation, expected in (
            (root_extra, "root fields do not match the exact schema"),
            (case_extra, "fields do not match the exact case schema"),
        ):
            with self.subTest(mutation=mutation.__name__), tempfile.TemporaryDirectory() as tmp:
                errors = vocab_schema_check.validate_native_review(
                    self._fixture_repo(tmp, mutation)
                )
            self.assertTrue(any(expected in error for error in errors), errors)

    def test_review_input_digest_covers_every_accepted_input_field(self) -> None:
        fixture = json.loads(
            (ROOT / "evals/multilingual-native-review.json").read_text(encoding="utf-8")
        )
        case = fixture["cases"][0]
        expected_fields = (
            vocab_schema_check.EXPECTED_NATIVE_REVIEW_CASE_FIELDS
            - vocab_schema_check.REVIEW_INPUT_EXCLUDED_FIELDS
        )
        self.assertEqual(
            set(vocab_schema_check._canonical_review_input(case)), expected_fields
        )
        original = vocab_schema_check._review_input_sha256(case)
        for field in sorted(expected_fields):
            mutated = copy.deepcopy(case)
            value = mutated[field]
            if isinstance(value, str):
                mutated[field] = value + " digest-probe"
            elif isinstance(value, bool):
                mutated[field] = not value
            elif isinstance(value, int):
                mutated[field] = value + 1
            elif isinstance(value, list):
                mutated[field] = value + ["digest-probe"]
            elif isinstance(value, dict):
                mutated[field] = {**value, "digest_probe": True}
            else:
                self.fail(f"unsupported canonical input field type for {field}")
            with self.subTest(field=field):
                self.assertNotEqual(
                    vocab_schema_check._review_input_sha256(mutated), original
                )

    def test_rejects_arbitrary_fixture_revision_or_review_round(self) -> None:
        def mutate(fixture: dict) -> None:
            case = fixture["cases"][0]
            case["fixture_revision"] = 999
            case["review_round"] = 999
            case["review_input_sha256"] = vocab_schema_check._review_input_sha256(case)
            case["review_record"]["fixture_revision"] = 999
            case["review_record"]["review_round"] = 999
            case["review_record"]["review_input_sha256"] = case["review_input_sha256"]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("fixture_revision must be 2" in error for error in errors), errors)
        self.assertTrue(any("review_round must be 2" in error for error in errors), errors)

    def test_accepts_structurally_valid_synthetic_completed_review(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            evidence["completed_review_sets"] = [self._valid_review_set(fixture)]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertEqual(errors, [])

    def test_derives_complete_state_only_after_all_three_valid_review_sets(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            evidence["completed_review_sets"] = [
                self._valid_review_set(fixture, case_index)
                for case_index in range(len(fixture["cases"]))
            ]
            evidence["review_state"] = "review_records_structurally_complete"

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertEqual(errors, [])

    def test_rejects_fake_completed_state_without_review_sets(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            del fixture
            evidence["review_state"] = "independent_review_complete"

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(any("review_state must derive" in error for error in errors), errors)

    def test_rejects_evidence_artifact_claim_boundary_drift(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            del fixture
            evidence["purpose"] = "Proves native fluency and reviewer identity."

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(any("purpose or claim boundary drifted" in e for e in errors), errors)

    def test_rejects_stale_completed_review_candidate_hash(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            review_set["candidate_sha256"] = "0" * 64
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(any("mismatched candidate_sha256" in error for error in errors), errors)

    def test_rejects_stale_completed_review_revision_and_round(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            review_set["fixture_revision"] += 1
            review_set["review_round"] += 1
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(any("mismatched fixture_revision" in error for error in errors), errors)
        self.assertTrue(any("mismatched review_round" in error for error in errors), errors)

    def test_rejects_stale_completed_review_common_brief_and_input_hashes(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            review_set["common_brief_sha256"] = "0" * 64
            review_set["review_input_sha256"] = "f" * 64
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(any("mismatched common_brief_sha256" in error for error in errors), errors)
        self.assertTrue(any("mismatched review_input_sha256" in error for error in errors), errors)

    def test_rejects_stale_completed_review_rubric_and_protocol_hashes(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            review_set["rubric_sha256"] = "0" * 64
            review_set["review_protocol_sha256"] = "f" * 64
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(any("mismatched rubric_sha256" in error for error in errors), errors)
        self.assertTrue(any("mismatched review_protocol_sha256" in error for error in errors), errors)

    def test_rejects_self_refreshed_rubric_and_protocol_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(tmp)
            rubric_path = repo / "references/multilingual-native-review.md"
            rubric_path.write_text(
                rubric_path.read_text(encoding="utf-8")
                + "\nA newly added scoring rule changes the review protocol.\n",
                encoding="utf-8",
            )
            fixture_path = repo / "evals/multilingual-native-review.json"
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            fixture["rubric_sha256"] = hashlib.sha256(rubric_path.read_bytes()).hexdigest()
            fixture["review_protocol_sha256"] = (
                vocab_schema_check._review_protocol_sha256(fixture)
            )
            fixture_path.write_text(
                json.dumps(fixture, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            errors = vocab_schema_check.validate_native_review(repo)
        self.assertTrue(any("rubric_sha256 is stale or noncanonical" in e for e in errors), errors)
        self.assertTrue(
            any("review_protocol_sha256 is stale or noncanonical" in e for e in errors),
            errors,
        )

    def test_rejects_one_or_duplicate_reviewer(self) -> None:
        def one_reviewer(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            review_set["reviewers"] = review_set["reviewers"][:1]
            evidence["completed_review_sets"] = [review_set]

        def duplicate_reviewer(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            review_set["reviewers"][1]["reviewer_id"] = (
                review_set["reviewers"][0]["reviewer_id"].upper()
            )
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=one_reviewer)
            )
        self.assertTrue(any("requires exactly two independent reviewers" in e for e in errors), errors)
        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=duplicate_reviewer)
            )
        self.assertTrue(any("reviewer_id values must be distinct" in e for e in errors), errors)

    def test_rejects_missing_required_reviewer_role(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            second = review_set["reviewers"][1]
            second["reviewer_role"] = "target-locale language editor"
            second["criterion_results"] = list(review_set["reviewers"][0]["criterion_results"])
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(any("does not cover both required roles" in e for e in errors), errors)

    def test_rejects_author_or_materially_conflicted_reviewer(self) -> None:
        def author(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            review_set["reviewers"][0]["is_specimen_author"] = True
            review_set["reviewers"][0]["authorship_disclosure"] = "specimen_author"
            evidence["completed_review_sets"] = [review_set]

        def conflict(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            reviewer = review_set["reviewers"][1]
            reviewer["conflict_disclosure"] = "paid specimen author"
            reviewer["has_material_conflict"] = True
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=author)
            )
        self.assertTrue(any("not independent of authorship" in e for e in errors), errors)
        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=conflict)
            )
        self.assertTrue(any("has a material conflict" in e for e in errors), errors)

    def test_rejects_wrong_criterion_ownership_or_ungrounded_quote(self) -> None:
        def wrong_owner(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            review_set["reviewers"][0]["criterion_results"] = review_set["reviewers"][0][
                "criterion_results"
            ][:-1]
            evidence["completed_review_sets"] = [review_set]

        def ungrounded(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            review_set["reviewers"][0]["criterion_results"][0]["quoted_span"] = (
                "invented evidence not present in the fixture"
            )
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=wrong_owner)
            )
        self.assertTrue(any("criterion ownership is incomplete" in e for e in errors), errors)
        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=ungrounded)
            )
        self.assertTrue(any("quoted_span is not grounded" in e for e in errors), errors)

    def test_rejects_common_brief_only_completed_review_evidence(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            for reviewer in review_set["reviewers"]:
                for result in reviewer["criterion_results"]:
                    result["quoted_source"] = "common_brief"
                    result["quoted_span"] = "Direct one restrained closing-time beat"
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(
            any("quoted_source must be `candidate_prompt`" in error for error in errors),
            errors,
        )

    def test_rejects_tiny_or_token_only_candidate_quotes(self) -> None:
        def tiny_quote(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            result = review_set["reviewers"][0]["criterion_results"][0]
            result["quoted_span"] = "店主"
            evidence["completed_review_sets"] = [review_set]

        def token_only_quote(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            result = review_set["reviewers"][0]["criterion_results"][0]
            result["quoted_span"] = "@Image1"
            evidence["completed_review_sets"] = [review_set]

        for mutation in (tiny_quote, token_only_quote):
            with self.subTest(mutation=mutation.__name__), tempfile.TemporaryDirectory() as tmp:
                errors = vocab_schema_check.validate_native_review(
                    self._fixture_repo(tmp, mutate_evidence=mutation)
                )
            self.assertTrue(
                any("at least 8 target-script characters" in error for error in errors),
                errors,
            )

    def test_rejects_recycled_wrong_criterion_evidence_and_trivial_reasons(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            recycled_quote = fixture["cases"][0]["production_contract"]["action"]
            for reviewer in review_set["reviewers"]:
                for result in reviewer["criterion_results"]:
                    result["quoted_span"] = recycled_quote
                    result["reason"] = f"{result['criterion_id']}: x"
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(any("evidence anchor" in error for error in errors), errors)
        self.assertTrue(any("reuses one quote" in error for error in errors), errors)
        self.assertTrue(any("at least 32 characters" in error for error in errors), errors)

    def test_rejects_punctuation_only_reason_bodies(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            for reviewer in review_set["reviewers"]:
                for result in reviewer["criterion_results"]:
                    result["reason"] = f"{result['criterion_id']}: " + ".!?—" * 12
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(
            any("meaningful alphanumeric characters" in error for error in errors),
            errors,
        )

    def test_rejects_reused_reason_bodies_behind_criterion_prefixes(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            boilerplate = "This identical boilerplate body is reused without criterion analysis."
            for reviewer in review_set["reviewers"]:
                for result in reviewer["criterion_results"]:
                    result["reason"] = f"{result['criterion_id']}: {boilerplate}"
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(
            any("reuses one canonical lexical reason body" in error for error in errors),
            errors,
        )

    def test_rejects_punctuation_variant_reason_body_reuse(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            variants = (
                "This repeated lexical body supports the selected score with grounded evidence.",
                "This, repeated lexical body; supports the selected score with grounded evidence!!!",
                "This... repeated lexical body supports the selected score—with grounded evidence?",
                "This repeated lexical body supports the selected score with grounded evidence;;;;",
            )
            for reviewer in review_set["reviewers"]:
                for index, result in enumerate(reviewer["criterion_results"]):
                    result["reason"] = (
                        f"{result['criterion_id']}: {variants[index % len(variants)]}"
                    )
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(
            any("reuses one canonical lexical reason body" in error for error in errors),
            errors,
        )

    def test_rejects_zero_width_reason_uniqueness_evasion(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            body = "This repeated lexical reason explains the selected score with grounded evidence"
            for reviewer in review_set["reviewers"]:
                for index, result in enumerate(reviewer["criterion_results"]):
                    invisible_variant = body.replace("lexical", "lexical" + "\u200b" * index)
                    result["reason"] = f"{result['criterion_id']}: {invisible_variant}"
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(
            any("Unicode control or format characters" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("reuses one canonical lexical reason body" in error for error in errors),
            errors,
        )

    def test_rejects_nonlocalized_or_score_three_proposed_revisions(self) -> None:
        def nonlocalized(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            result = next(
                item
                for item in review_set["reviewers"][0]["criterion_results"]
                if item["criterion_id"] == "idiomatic_production_language"
            )
            result["score_0_to_3"] = 2
            result["proposed_revision"] = "replace this"
            evidence["completed_review_sets"] = [review_set]

        def score_three_revision(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            review_set["reviewers"][0]["criterion_results"][0][
                "proposed_revision"
            ] = "将这一句改成更具体的本地化表述"
            evidence["completed_review_sets"] = [review_set]

        for mutation, expected in (
            (nonlocalized, "concrete localized proposed revision"),
            (score_three_revision, "score 3 must not propose a revision"),
        ):
            with self.subTest(mutation=mutation.__name__), tempfile.TemporaryDirectory() as tmp:
                errors = vocab_schema_check.validate_native_review(
                    self._fixture_repo(tmp, mutate_evidence=mutation)
                )
            self.assertTrue(any(expected in error for error in errors), errors)

    def test_rejects_extra_same_role_reviewer_and_hidden_owned_score_disagreement(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            extra = copy.deepcopy(review_set["reviewers"][0])
            extra["reviewer_id"] = "third-language-reviewer"
            for result in extra["criterion_results"]:
                if result["criterion_id"] == "idiomatic_production_language":
                    result["score_0_to_3"] = 2
                    result["proposed_revision"] = "将这一句改成更自然的本地制作指令"
            review_set["reviewers"].append(extra)
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(any("requires exactly two" in error for error in errors), errors)
        self.assertTrue(any("roles exactly once" in error for error in errors), errors)
        self.assertTrue(any("hides a reviewer disagreement" in error for error in errors), errors)

    def test_rejects_invisible_or_noncanonical_reviewer_ids(self) -> None:
        bad_ids = ("same-\u200bperson", "ｒeviewer-2", "reviewer\u00a0two")
        for bad_id in bad_ids:
            def mutate_evidence(evidence: dict, fixture: dict, value: str = bad_id) -> None:
                review_set = self._valid_review_set(fixture)
                review_set["reviewers"][1]["reviewer_id"] = value
                evidence["completed_review_sets"] = [review_set]

            with self.subTest(reviewer_id=repr(bad_id)), tempfile.TemporaryDirectory() as tmp:
                errors = vocab_schema_check.validate_native_review(
                    self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
                )
            self.assertTrue(any("visible canonical ASCII" in error for error in errors), errors)

    def test_rejects_public_native_quality_or_authorship_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(tmp)
            (repo / "README.md").write_text(
                "Static validation proves native fluency and native authorship.\n"
                "Native docs and examples for Chinese, Japanese, and Korean.\n"
                "These prompts were authored by native speakers.\n"
                "Static validation cannot establish native fluency; these prompts have "
                "native fluency.\n",
                encoding="utf-8",
            )
            errors = vocab_schema_check.validate_native_review(repo)
        self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_public_yaml_model_and_video_quality_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(tmp)
            (repo / "claims.yaml").write_text(
                "result: Static validation certifies model output quality and "
                "generated-video quality.\n",
                encoding="utf-8",
            )
            errors = vocab_schema_check.validate_native_review(repo)
        self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_markdown_formatted_claim_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(tmp)
            (repo / "README.md").write_text(
                "# Native **Fluency** Verified\n\n"
                "## Native **Authorship** Verified\n",
                encoding="utf-8",
            )
            errors = vocab_schema_check.validate_native_review(repo)
        self.assertTrue(any("README.md:1:" in error for error in errors), errors)
        self.assertTrue(any("README.md:1:" in error for error in errors), errors)

    def test_rejects_caveat_that_whitelists_later_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(tmp)
            (repo / "README.md").write_text(
                "# A parser pass is not proof of native fluency but these prompts have "
                "native fluency.\n",
                encoding="utf-8",
            )
            errors = vocab_schema_check.validate_native_review(repo)
        self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_colon_scoped_caveat_and_postpositive_assertion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(tmp)
            (repo / "README.md").write_text(
                "# A parser pass is not proof of native fluency: native fluency is confirmed.\n",
                encoding="utf-8",
            )
            errors = vocab_schema_check.validate_native_review(repo)
        self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_same_segment_exhibit_after_caveat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(tmp)
            (repo / "claims.yaml").write_text(
                "claim: A parser pass is not proof of native fluency and these prompts "
                "exhibit native fluency.\n",
                encoding="utf-8",
            )
            errors = vocab_schema_check.validate_native_review(repo)
        self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_occurrence_local_claim_polarity_bypasses(self) -> None:
        attacks = (
            (
                "README.md",
                "# Static checks cannot establish native fluency and these prompts "
                "possess native fluency.\n",
            ),
            (
                "claims.yaml",
                "claim: Static checks cannot establish native fluency, these prompts "
                "embody native fluency.\n",
            ),
            (
                "README.md",
                "# Static checks cannot establish native fluency "
                "(native fluency is confirmed).\n",
            ),
        )
        for relative, content in attacks:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                repo = self._fixture_repo(tmp)
                (repo / relative).write_text(content, encoding="utf-8")
                errors = vocab_schema_check.validate_native_review(repo)
            self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_shared_subject_coordinated_positive_predicates_generically(self) -> None:
        connectors = (",", " and", " or")
        predicates = (
            "possess",
            "embody",
            "guarantee",
            "attain",
            "achieve",
            "ensure",
            "offer",
            "provide",
            "reflect",
            "maintain",
            "reach",
            "produce",
            "represent",
            "signal",
            "meet",
            "display",
            "evince",
            "manifest",
        )
        for connector in connectors:
            for predicate in predicates:
                content = (
                    "# These prompts cannot establish native fluency"
                    f"{connector} {predicate} native fluency.\n"
                )
                with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                    repo = Path(tmp)
                    self._write_canonical_disclaimer(repo)
                    (repo / "README.md").write_text(content, encoding="utf-8")
                    errors = vocab_schema_check.validate_public_claim_boundaries(repo)
                self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_free_form_coordinated_negative_predicates_and_limitation_lists(self) -> None:
        predicates = (
            "possess", "embody", "guarantee", "attain", "achieve", "ensure",
            "offer", "provide", "reflect", "maintain", "reach", "produce",
            "represent", "signal", "meet", "display", "evince", "manifest",
        )
        caveats = [
            "Static checks cannot establish native fluency, cultural authenticity, "
            "native authorship, reviewer identity, model-output quality, universal native "
            "fluency, generated-video quality, or rendered-video quality.\n",
            "These prompts cannot establish native fluency, cannot possess native fluency.\n",
            "These prompts cannot establish native fluency and do not embody native fluency.\n",
            "These prompts cannot establish native fluency or cannot guarantee native fluency.\n",
        ]
        caveats.extend(
            "These prompts cannot establish native fluency"
            f"{connector} cannot {predicate} native fluency.\n"
            for connector in (",", " and", " or")
            for predicate in predicates
        )
        for content in caveats:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                self._write_canonical_disclaimer(repo)
                (repo / "README.md").write_text(content, encoding="utf-8")
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
            self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_unseen_discourse_connector_polarity_leakage(self) -> None:
        continuations = (
            "though these prompts achieve",
            "whereas these prompts attain",
            "because these prompts already ensure",
            "despite these prompts providing",
        )
        for continuation in continuations:
            content = (
                "Static checks cannot establish native fluency "
                f"{continuation} native fluency.\n"
            )
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                self._write_canonical_disclaimer(repo)
                (repo / "README.md").write_text(content, encoding="utf-8")
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
            self.assertTrue(errors, content)

    def test_rejects_free_form_negation_after_unseen_discourse_connectors(self) -> None:
        continuations = (
            "though these prompts cannot achieve",
            "whereas these prompts do not attain",
            "because these prompts never ensure",
            "despite the fact that these prompts cannot provide",
        )
        for continuation in continuations:
            content = (
                "Static checks cannot establish native fluency "
                f"{continuation} native fluency.\n"
            )
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                self._write_canonical_disclaimer(repo)
                (repo / "README.md").write_text(content, encoding="utf-8")
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
            self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_native_morphology_marketing_variants_without_false_controls(self) -> None:
        claims = (
            "Native-language docs are now available.\n",
            "Native-language examples are now available.\n",
            "Native-language prompt guidance is now available.\n",
            "This material serves native-Chinese readers.\n",
            "These prompts have native-level fluency.\n",
            "These prompts have native-like fluency.\n",
            "These prompts are native-speaker authored.\n",
            "These prompts have native-equivalent fluency.\n",
            "These prompts have native-grade fluency.\n",
            "These prompts have native-caliber fluency.\n",
            "These prompts have native-standard fluency.\n",
            "These prompts have native-level command.\n",
            "These prompts have native-level writing.\n",
            "These prompts have native linguistic quality.\n",
            "These prompts have native-equivalent language quality.\n",
        )
        for content in claims:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                self._write_canonical_disclaimer(repo)
                (repo / "README.md").write_text(content, encoding="utf-8")
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
            self.assertTrue(errors, content)

        controls = (
            "Native-language review remains pending.\n",
            "The platform exposes a native language selector.\n",
            "These examples discuss native plant communities.\n",
            "Run the native Windows command from PowerShell.\n",
            "The desktop app uses native menus.\n",
            "Run React Native start for the demo.\n",
            "Compare native versions of the SDK.\n",
            "Read the native compiler docs.\n",
        )
        for content in controls:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                self._write_canonical_disclaimer(repo)
                (repo / "README.md").write_text(content, encoding="utf-8")
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
            self.assertEqual(errors, [])

    def test_accepts_only_exact_canonical_path_bound_disclaimer_record(self) -> None:
        disclaimer = vocab_schema_check.PUBLIC_CLAIM_CANONICAL_DISCLAIMER
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "references/multilingual-native-review.md"
            path.parent.mkdir(parents=True)
            path.write_text(disclaimer + "\n", encoding="utf-8")
            errors = vocab_schema_check.validate_public_claim_boundaries(repo)
        self.assertEqual(errors, [])

    def test_accepts_canonical_disclaimer_with_crlf_line_endings(self) -> None:
        disclaimer = vocab_schema_check.PUBLIC_CLAIM_CANONICAL_DISCLAIMER
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "references/multilingual-native-review.md"
            path.parent.mkdir(parents=True)
            path.write_bytes((disclaimer + "\n").replace("\n", "\r\n").encode("utf-8"))
            errors = vocab_schema_check.validate_public_claim_boundaries(repo)
        self.assertEqual(errors, [])

    def test_rejects_canonical_disclaimer_at_wrong_path_or_duplicated(self) -> None:
        disclaimer = vocab_schema_check.PUBLIC_CLAIM_CANONICAL_DISCLAIMER
        cases = (
            ("README.md", disclaimer + "\n", "is missing"),
            (
                "references/multilingual-native-review.md",
                disclaimer + "\n\n" + disclaimer + "\n",
                "occur once, found 2",
            ),
        )
        for relative, content, expected in cases:
            with self.subTest(relative=relative, expected=expected), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
            self.assertTrue(any(expected in error for error in errors), errors)

    def test_rejects_any_mutation_of_canonical_disclaimer(self) -> None:
        disclaimer = vocab_schema_check.PUBLIC_CLAIM_CANONICAL_DISCLAIMER
        mutations = (
            disclaimer.replace("Static", "STATIC", 1),
            disclaimer.replace("required.", "required!", 1),
            "Note: " + disclaimer,
            disclaimer + " This is canonical.",
            disclaimer.replace("native fluency", "**native fluency**", 1),
            disclaimer.replace("native fluency", "native\u200b fluency", 1),
            disclaimer.replace("native fluency", "ｎative fluency", 1),
        )
        for content in mutations:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                path = repo / "references/multilingual-native-review.md"
                path.parent.mkdir(parents=True)
                path.write_text(content + "\n", encoding="utf-8")
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
            self.assertTrue(
                any("exact canonical" in error or "top-level rendered" in error for error in errors),
                errors,
            )

    def test_rejects_disclaimer_whitespace_and_rendering_context_mutations(self) -> None:
        disclaimer = vocab_schema_check.PUBLIC_CLAIM_CANONICAL_DISCLAIMER
        whitespace_mutations = (
            disclaimer.replace("Static validation", "Static\tvalidation", 1),
            disclaimer.replace("Static validation", "Static  validation", 1),
            disclaimer.replace("Static validation", "Static\u00a0validation", 1),
            disclaimer.replace("Static validation", "Static\u2009validation", 1),
            disclaimer.replace("Static validation", "Static\u3000validation", 1),
            disclaimer.replace("quality;\n", "quality;  \n", 1),
            disclaimer.replace("author provenance,", "author provenance,\n", 1),
        )
        contextual_mutations = (
            "```text\n" + disclaimer + "\n```\n",
            "    " + disclaimer.replace("\n", "\n    ") + "\n",
            "<!--\n" + disclaimer + "\n-->\n",
            "---\nnotice: |\n  " + disclaimer.replace("\n", "\n  ") + "\n---\n",
            "> " + disclaimer.replace("\n", "\n> ") + "\n",
        )
        for content in whitespace_mutations + contextual_mutations:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                path = repo / vocab_schema_check.NATIVE_REVIEW_RUBRIC
                path.parent.mkdir(parents=True)
                path.write_text(content + ("" if content.endswith("\n") else "\n"), encoding="utf-8")
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
            self.assertTrue(
                any("exact canonical" in error or "top-level rendered" in error for error in errors),
                errors,
            )

    def test_best_effort_lint_handles_rendered_and_encoded_known_phrases(self) -> None:
        attacks = (
            ("claims.yaml", 'claim: "Static validation proves native\\u0020fluency."\n'),
            ("claims.yaml", 'claim: "Static validation proves na\\u0074ive fluency."\n'),
            ("README.md", "Static validation proves [native][term] [fluency][level].\n"),
            ("README.md", "Static validation proves [nat][term]ive fluency.\n"),
            ("README.md", "Static validation proves nat<span></span>ive fluency.\n"),
            ("README.md", "Static validation proves nat<!-- split -->ive fluency.\n"),
            ("README.html", '<img alt="Static validation proves native fluency">\n'),
            ("README.html", '<span aria-label="Static validation proves native fluency">ok</span>\n'),
            ("README.md", "Static validation proves nati\ufe0fve fluency.\n"),
            ("README.md", "Static validation proves nat\u0345ive fluency.\n"),
            ("README.md", "Static validation proves nat\u00adive fluency.\n"),
            ("README.md", "Static validation proves native flu\u00adency.\n"),
            ("README.md", "Static validation proves n\u0430tive fluency.\n"),
            ("README.md", "Static validation proves native_fluency.\n"),
        )
        for relative, content in attacks:
            with self.subTest(relative=relative, content=content), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                self._write_canonical_disclaimer(repo)
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
                self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_best_effort_lint_declared_surfaces_are_extension_agnostic(self) -> None:
        names = (
            "claim.txt", "claim.rst", "claim.mdx", "claim.html", "claim.json",
            "claim.toml", "claim.yaml.j2", "NOTICE",
        )
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                self._write_canonical_disclaimer(repo)
                (repo / name).write_text(
                    "Static validation proves native fluency.\n",
                    encoding="utf-8",
                )
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
            self.assertTrue(any(error.startswith(f"{name}:1:") for error in errors), errors)

    def test_rejects_dash_confusables_inside_canonical_disclaimer(self) -> None:
        disclaimer = vocab_schema_check.PUBLIC_CLAIM_CANONICAL_DISCLAIMER
        for codepoint in vocab_schema_check.PUBLIC_CLAIM_DASH_CODEPOINTS:
            if codepoint == 0x002D:
                continue
            content = disclaimer.replace("native-language", f"native{chr(codepoint)}language")
            with self.subTest(codepoint=f"U+{codepoint:04X}"), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                path = repo / "references/multilingual-native-review.md"
                path.parent.mkdir(parents=True)
                path.write_text(content + "\n", encoding="utf-8")
                errors = vocab_schema_check.validate_public_claim_boundaries(repo)
            self.assertTrue(any("exact canonical" in error for error in errors), errors)

    def test_machine_allowlist_record_and_digest_are_exact(self) -> None:
        fixture = json.loads(
            (ROOT / "evals/multilingual-native-review.json").read_text(encoding="utf-8")
        )
        policy = fixture["review_policy"]
        self.assertEqual(
            policy["public_claim_allowlist_version"],
            vocab_schema_check.PUBLIC_CLAIM_ALLOWLIST_VERSION,
        )
        self.assertEqual(
            policy["public_claim_allowlist"],
            vocab_schema_check.EXPECTED_PUBLIC_CLAIM_ALLOWLIST,
        )
        record = policy["public_claim_allowlist"][0]
        self.assertEqual(
            hashlib.sha256(record["text_lf"].encode("utf-8")).hexdigest(),
            record["sha256_lf"],
        )
        self.assertEqual(record["line_endings"], "LF_or_CRLF_only")
        self.assertEqual(
            policy["public_claim_lint_policy"],
            vocab_schema_check.PUBLIC_CLAIM_LINT_POLICY,
        )

    def test_rejects_coordinated_machine_allowlist_record_drift(self) -> None:
        mutations = (
            ("version", "public-claim-disclaimer-v2"),
            ("path", "README.md"),
            ("text_lf", "Static validation cannot establish native fluency."),
            ("sha256_lf", "0" * 64),
            ("line_endings", "any_whitespace"),
        )
        for field, value in mutations:
            def mutate(fixture: dict, key: str = field, replacement: str = value) -> None:
                policy = fixture["review_policy"]
                if key == "version":
                    policy["public_claim_allowlist_version"] = replacement
                else:
                    policy["public_claim_allowlist"][0][key] = replacement
                    if key == "text_lf":
                        policy["public_claim_allowlist"][0]["sha256_lf"] = hashlib.sha256(
                            replacement.encode("utf-8")
                        ).hexdigest()
                fixture["review_protocol_sha256"] = vocab_schema_check._review_protocol_sha256(
                    fixture
                )

            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                errors = vocab_schema_check.validate_native_review(
                    self._fixture_repo(tmp, mutate=mutate)
                )
            self.assertTrue(any("public-claim allowlist" in error for error in errors), errors)

    def test_rejects_public_claim_lint_policy_overstatement(self) -> None:
        def mutate(fixture: dict) -> None:
            fixture["review_policy"]["public_claim_lint_policy"]["guarantee"] = (
                "proves_no_semantic_overclaims"
            )
            fixture["review_protocol_sha256"] = vocab_schema_check._review_protocol_sha256(
                fixture
            )

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate=mutate)
            )
        self.assertTrue(any("lint surface policy drifted" in error for error in errors), errors)

    def test_git_public_text_enumeration_covers_case_variants(self) -> None:
        names = (
            "lower-md.md",
            "upper-md.MD",
            "lower-markdown.markdown",
            "upper-markdown.MARKDOWN",
            "lower-yml.yml",
            "upper-yml.YML",
            "lower-yaml.yaml",
            "upper-yaml.YAML",
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_canonical_disclaimer(repo)
            for name in names:
                (repo / name).write_text(
                    "Static validation proves native fluency.\n",
                    encoding="utf-8",
                )
            (repo / "claim.txt").write_text(
                "Static validation proves native fluency.\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "init", "-q", str(repo)],
                check=True,
                text=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "add", "--", *names, "claim.txt"],
                check=True,
                text=True,
                capture_output=True,
            )

            paths = vocab_schema_check._public_text_paths(repo)
            self.assertEqual(
                {path.name for path in paths},
                set(names) | {"claim.txt", "multilingual-native-review.md"},
            )
            errors = vocab_schema_check.validate_public_claim_boundaries(repo)

        self.assertEqual(len(errors), len(names) + 1, errors)
        for name in names + ("claim.txt",):
            self.assertTrue(any(error.startswith(f"{name}:1:") for error in errors), errors)

    def test_evidence_enum_fields_fail_contained_for_unhashable_json_values(self) -> None:
        mutators = {
            "reviewer_role": lambda review_set, value: review_set["reviewers"][0].__setitem__(
                "reviewer_role", value
            ),
            "reviewer_verdict": lambda review_set, value: review_set["reviewers"][0].__setitem__(
                "verdict", value
            ),
            "quoted_source": lambda review_set, value: review_set["reviewers"][0][
                "criterion_results"
            ][0].__setitem__("quoted_source", value),
            "disagreement_status": lambda review_set, value: review_set["disagreement"].__setitem__(
                "status", value
            ),
        }
        for field, mutate in mutators.items():
            for value in ([], {}):
                def mutate_evidence(
                    evidence: dict,
                    fixture: dict,
                    mutation=mutate,
                    bad_value=value,
                ) -> None:
                    review_set = self._valid_review_set(fixture)
                    mutation(review_set, bad_value)
                    evidence["completed_review_sets"] = [review_set]

                with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                    errors = vocab_schema_check.validate_native_review(
                        self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
                    )
                self.assertTrue(errors)

    def test_disagreement_status_and_summary_must_agree_both_directions(self) -> None:
        mutations = (
            ({"status": "none", "summary": "Reviewers explicitly disagree."}, "empty summary"),
            ({"status": "unresolved", "summary": " \t"}, "needs a summary"),
            (
                {"status": "unresolved", "summary": "Reviewers agree on every score."},
                "without differing reviewer scores or verdicts",
            ),
        )
        for disagreement, expected in mutations:
            def mutate_evidence(
                evidence: dict,
                fixture: dict,
                value=disagreement,
            ) -> None:
                review_set = self._valid_review_set(fixture)
                review_set["disagreement"] = value
                evidence["completed_review_sets"] = [review_set]

            with self.subTest(disagreement=disagreement), tempfile.TemporaryDirectory() as tmp:
                errors = vocab_schema_check.validate_native_review(
                    self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
                )
            self.assertTrue(any(expected in error for error in errors), errors)

    def test_rejects_zero_width_markdown_claim_obfuscation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(tmp)
            (repo / "README.md").write_text(
                "# Native\u200b **Fluency** is confirmed\n",
                encoding="utf-8",
            )
            errors = vocab_schema_check.validate_native_review(repo)
        self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_nonbreaking_hyphen_yaml_claim_obfuscation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(tmp)
            (repo / "claims.yaml").write_text(
                "claim: Static validation certifies native\u2011language quality.\n",
                encoding="utf-8",
            )
            errors = vocab_schema_check.validate_native_review(repo)
        self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_dash_variant_caveat_boundaries(self) -> None:
        expected_codepoints = (
            0x002D,
            0x00AD,
            0x058A,
            0x05BE,
            0x1400,
            0x1806,
            0x2010,
            0x2011,
            0x2012,
            0x2013,
            0x2014,
            0x2015,
            0x2043,
            0x2053,
            0x207B,
            0x208B,
            0x2212,
            0x2E17,
            0x2E1A,
            0x2E3A,
            0x2E3B,
            0x2E40,
            0x2E43,
            0x2E5D,
            0x301C,
            0x3030,
            0x30A0,
            0xFE31,
            0xFE32,
            0xFE58,
            0xFE63,
            0xFF0D,
            0x10EAD,
        )
        self.assertEqual(
            vocab_schema_check.PUBLIC_CLAIM_DASH_SET_VERSION,
            "public-claim-dashes-v1",
        )
        self.assertEqual(
            vocab_schema_check.PUBLIC_CLAIM_DASH_CODEPOINTS,
            expected_codepoints,
        )
        self.assertIn(0x2053, expected_codepoints)
        self.assertIn(0x2E43, expected_codepoints)
        for codepoint in expected_codepoints:
            dash = chr(codepoint)
            with self.subTest(dash=f"U+{ord(dash):04X}"), tempfile.TemporaryDirectory() as tmp:
                repo = self._fixture_repo(tmp)
                (repo / "README.md").write_text(
                    f"# A parser pass is not proof of native fluency {dash} "
                    "native fluency is confirmed.\n",
                    encoding="utf-8",
                )
                errors = vocab_schema_check.validate_native_review(repo)
            self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_u2053_and_u2e43_inside_claim_terms(self) -> None:
        for codepoint in (0x2053, 0x2E43):
            with self.subTest(codepoint=f"U+{codepoint:04X}"), tempfile.TemporaryDirectory() as tmp:
                repo = self._fixture_repo(tmp)
                (repo / "claims.yaml").write_text(
                    "claim: Static validation certifies native"
                    f"{chr(codepoint)}language quality.\n",
                    encoding="utf-8",
                )
                errors = vocab_schema_check.validate_native_review(repo)
            self.assertTrue(any("known-phrase lint" in error for error in errors), errors)

    def test_rejects_self_refreshed_criterion_anchor_drift(self) -> None:
        def mutate(fixture: dict) -> None:
            case = fixture["cases"][0]
            case["criterion_evidence_anchors"]["creative_lens_realization"] = [
                case["production_contract"]["action"]
            ]
            case["review_input_sha256"] = vocab_schema_check._review_input_sha256(case)
            case["review_record"]["review_input_sha256"] = case["review_input_sha256"]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("criterion evidence anchors drifted" in error for error in errors), errors)

    def test_rejects_unresolved_disagreement_or_threshold_false_pass(self) -> None:
        def mutate_evidence(evidence: dict, fixture: dict) -> None:
            review_set = self._valid_review_set(fixture)
            second = review_set["reviewers"][1]
            second["criterion_results"][0]["score_0_to_3"] = 2
            second["criterion_results"][0]["proposed_revision"] = (
                "将这一句改成更忠实的参考角色表述"
            )
            review_set["disagreement"] = {
                "status": "unresolved",
                "summary": "Reviewers disagree on brief fidelity.",
            }
            evidence["completed_review_sets"] = [review_set]

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(
                self._fixture_repo(tmp, mutate_evidence=mutate_evidence)
            )
        self.assertTrue(any("pass violates brief_and_reference_fidelity" in e for e in errors), errors)
        self.assertTrue(any("unresolved disagreement blocks pass" in e for e in errors), errors)

    def test_rejects_overclaiming_structural_or_semantic_template_detection(self) -> None:
        def mutate(fixture: dict) -> None:
            scope = fixture["static_validation_scope"]
            scope[scope.index("literal cross-locale realization overlap")] = (
                "structural and semantic cross-locale template detection"
            )

        with tempfile.TemporaryDirectory() as tmp:
            errors = vocab_schema_check.validate_native_review(self._fixture_repo(tmp, mutate))
        self.assertTrue(any("static validation scope overclaims" in e for e in errors), errors)

    def test_rubric_must_keep_the_epistemic_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._fixture_repo(tmp)
            rubric = repo / "references/multilingual-native-review.md"
            text = rubric.read_text(encoding="utf-8").replace(
                vocab_schema_check.PUBLIC_CLAIM_CANONICAL_DISCLAIMER,
                "Static validation establishes native fluency.",
            )
            rubric.write_text(text, encoding="utf-8")
            errors = vocab_schema_check.validate_native_review(repo)
        self.assertTrue(any("missing claim-boundary text" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()

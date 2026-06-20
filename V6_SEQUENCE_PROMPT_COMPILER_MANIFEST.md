# V6 Sequence Prompt Compiler Manifest

## Baseline

- Repository: `Emily2040/seedance-2.0`
- Baseline commit inspected: `94906cd`
- Baseline version: `5.5.2`
- Baseline sub-skills: 24
- Baseline references: 47
- Baseline eval cases: 61
- Baseline validators: `validate_skills.py`, `content_audit.py`, `eval_schema_check.py`, `design_audit.py`, `source_registry_check.py`, `vocab_schema_check.py`
- Baseline CI: six local Python validators
- Frontmatter convention: YAML block with `name`, third-person `description`, `license`, `user-invocable`, `tags`, and `metadata.version`; sub-skills also require `metadata.parent: "seedance-20"`

## Files Added

- `skills/seedance-sequence/SKILL.md`
- `skills/seedance-continuation/SKILL.md`
- `references/sequence-project-state.md`
- `references/continuation-handoff.md`
- `references/prompt-compiler.md`
- `references/reference-transfer-contract.md`
- `references/dense-storyboard-mode.md`
- `references/surface-prompt-profiles.md`
- `references/event-density.md`
- `references/continuity-qc.md`
- `references/failure-atlas.md`
- `schemas/project-state.schema.json`
- `schemas/clip-contract.schema.json`
- `schemas/take-review.schema.json`
- `schemas/prompt-spec.schema.json`
- `schemas/generation-run.schema.json`
- `scripts/prompt_lint.py`
- `scripts/project_state_check.py`
- `scripts/continuity_chain_check.py`
- `scripts/behavior_contract_check.py`
- `scripts/sequence_eval_check.py`
- `scripts/generation_run_check.py`
- `tests/test_prompt_lint.py`
- `tests/test_project_state.py`
- `tests/test_continuity_chain.py`
- `tests/test_behavior_contract.py`
- `tests/test_sequence_eval.py`
- `tests/test_generation_run_check.py`
- `evals/generation-benchmark.json`
- `data/generation-runs.example.jsonl`
- `examples/sequence-airport-arrival/*`
- `examples/sequence-observed-deviation/*`
- `examples/standalone-clip/*`
- `examples/golden-prompts/*`

## Files Modified

- `SKILL.md`
- `README.md`
- `CHANGELOG.md`
- `agents/openai.yaml`
- `.github/workflows/validate-skills.yml`
- `evals/evals.json`
- `scripts/validate_skills.py`
- `scripts/eval_schema_check.py`
- Existing skill routers: interview, interview-short, prompt, prompt-short, troubleshoot, camera, motion, characters, audio, lighting, style, recipes, and version metadata for all active sub-skills.
- Existing references: storytelling framework, shot-list continuity, reference workflow, JSON schema, retake protocol, eval rubric, quick reference, examples by mode, multishot grammar, 2D anime grammar, model mechanics, allocation model, capability map, progressive disclosure, agent compatibility, field-observed tips, community-source methodology, and prompt examples.

## Behavior Changes

- Adds a root Sequence Gate before Mode Gate.
- Classifies requests as `standalone_clip` or `sequence_project`.
- Requires story objective, final story outcome, ordered beats, surface profile, clip budget, current clip job, and current clip endpoint before Clip 01.
- Requires accepted previous footage or an accepted final frame plus `observed_end_state` before continuation prompts.
- Separates canonical references from transient accepted footage.
- Makes accepted observed footage override planned state.
- Prevents rejected footage from updating canon.
- Prevents later prompts from replaying completed beats or leaking reserved future beats.
- Keeps future prompts provisional until the preceding accepted take is reviewed.
- Preserves exact reference tags byte-for-byte.
- Keeps final Seedance prompts natural language unless the user requests structured output.
- Adds a portable Project State Capsule for cross-session continuation.

## Migrations

- Version moved from `5.5.2` to `6.0.0` across active skill metadata, README, eval metadata, and validator expectations.
- Expected sub-skills increased from 24 to 26.
- Required references increased from 47 to 56.
- Evals increased from 61 to 108.
- CI expanded from six checks to the complete v6 validation suite.

## Validation Commands

```bash
python scripts/validate_skills.py --strict
python scripts/content_audit.py --strict
python scripts/eval_schema_check.py --strict
python scripts/design_audit.py --strict
python scripts/source_registry_check.py --strict
python scripts/vocab_schema_check.py --strict
python scripts/project_state_check.py --strict
python scripts/continuity_chain_check.py --strict
python scripts/behavior_contract_check.py --strict
python scripts/sequence_eval_check.py --strict
python scripts/generation_run_check.py --strict
python scripts/prompt_lint.py --self-test --strict
python -m unittest discover -s tests -v
python -m compileall scripts tests
git diff --check
```

## Release Acceptance Results

Final full-suite run on 2026-06-20:

- `python scripts/validate_skills.py --strict`: pass; validated root plus 26 sub-skills and required v6.0.0 files.
- `python scripts/content_audit.py --strict`: pass; active content clean, migrated archived warnings remain warning-only.
- `python scripts/eval_schema_check.py --strict`: pass; 108 eval cases.
- `python scripts/design_audit.py --strict`: pass.
- `python scripts/source_registry_check.py --strict`: pass.
- `python scripts/vocab_schema_check.py --strict`: pass.
- `python scripts/project_state_check.py --strict`: pass; 4 project states.
- `python scripts/continuity_chain_check.py --strict`: pass.
- `python scripts/behavior_contract_check.py --strict`: pass.
- `python scripts/sequence_eval_check.py --strict`: pass; 47 sequence cases.
- `python scripts/generation_run_check.py --strict`: pass.
- `python scripts/prompt_lint.py --self-test --strict`: pass.
- `python -m unittest discover -s tests -v`: pass; 6 tests.
- `python -m compileall scripts tests`: pass.
- `git diff --check`: pass.

Assumptions marked heuristic: sequence drift risk, extension-depth warnings, event-density splitting, and unknown-surface conservative profile. No new volatile platform limits, pricing, model IDs, regions, endpoint names, or authorization rules were asserted.

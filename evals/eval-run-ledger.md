# Eval Run Ledger

This file is the **evidence layer** for the eval suite. The deterministic CI
validators (`eval_schema_check.py`, `sequence_eval_check.py`, ...) prove the
cases are well-formed; this ledger records either the skill's scored output or an
explicit non-score harness failure from `scripts/eval_run.py` against the rubric
in [`references/eval-rubric.md`](../references/eval-rubric.md).

That score is not a certification of the writing, its origin, or the rendered result.
Those claims require separate evidence; see
[`references/multilingual-native-review.md`](../references/multilingual-native-review.md).

## How to regenerate

A live evaluation needs network access and a key, so it runs outside the offline
CI gate:

```bash
export ANTHROPIC_API_KEY=...
python scripts/eval_run.py --ledger evals/eval-run-ledger.md --stamp <ISO-date>

export MINIMAX_API_KEY=...
python scripts/eval_run.py --provider minimax --region global_en \
  --ledger evals/eval-run-ledger.md --stamp <ISO-date>
```

For each case, a blind discovery phase receives the complete root `SKILL.md`, a
catalog of responder-role files, and the user request plus project state as
untrusted JSON data. It never receives expected routes, assertions, failure
labels, reference answers, archived material, or evaluator/rubric files. The
responder then receives the root instructions plus only the selected sources;
after selection, the harness compares selected skill paths with the hidden route
oracle and fails wrong, missing, extra, duplicate, or unknown routes. The judge
alone receives the rubric, case prompt, expected output, checks, and candidate
response; it never receives the hidden route oracle or selected source paths.
Legacy cases use the
rubric's 0-3 scale (release: every case >= 2, average >= 2.6); sequence cases use
the 0-4 scale (release: critical cases at 4, no dimension below 3, average >=
3.5).

Every input is explicitly classified and hashed in `evals/source-manifest.json`,
resolved through one containment and physical-identity boundary, read once into
an immutable snapshot, and reverified before evidence is written. JSON state
fixtures live only under `evals/fixtures/`; their repository paths are not sent
to models. The canonical eval and rubric digests are pinned. Generated ledgers
record provider, region, responder and judge models, selected-versus-total scope,
and each selected responder path plus its frozen SHA-256 digest. Discovery
failure remains distinct from a valid root-only selection. Focused `--id` or
`--limit` runs are not release-eligible and cannot replace this canonical ledger.
Each generated ledger also records one canonical SHA-256 over the complete
frozen path/role/hash map, including the root skill, fixtures, evaluator harness,
and `evals/source-manifest.json` itself, together with per-role file counts. The
release path accepts that map only from the verified frozen snapshot, binds the
frozen evaluator to the module code object Python actually executed, and
re-derives snapshot roles from the frozen manifest on every verification. It
checks immediately before and after the atomic ledger replace, restoring the
prior ledger (or removing the new one) if the post-replace check detects a race.
Bootstrap failure reporting refuses ledger destinations that overwrite or alias
repository inputs.

Every declared oracle is judge-bound without entering discovery or response
generation. Assertions, required sections, forbidden behaviors, `expected_output`,
`failure_mode`, `expected_state_delta`, and `expected_prompt_architecture` use
stable opaque criterion IDs; `expected_sequence_relation` is bound into the
routing dimension. A valid judge response must score every required ID exactly
once.

Each result row is explicitly `scored` or `harness_error`. Only `scored` rows
enter quality floors and averages. Judge transport failures, timeouts, empty or
oversized bodies, malformed JSON, and incomplete/invalid verdicts are recorded
with no numeric score or pass value, excluded from quality arithmetic, and make
release evidence `NOT ELIGIBLE`; the harness continues remaining cases, writes
the fresh failure ledger, and exits 1. A case-contract or worst-case response
envelope that cannot bind aborts the whole run before provider calls with exit 2
and atomically writes a bootstrap failure ledger when `--ledger` was requested.
Post-run snapshot drift also exits 2 and invalidates every row as a non-scored
harness error.

Release assessment binds every result to canonical per-case `sequence` and
`critical` metadata derived from `evals/evals.json`. Case IDs or a result count
alone cannot establish a release universe or prove that a row used the correct
rubric scale.

The offline wiring is checked in CI via `python scripts/eval_run.py --self-test`.

## Latest run

_Not yet scored live in this environment (no live provider credential is available offline)._
Run the command above to populate the table below; the harness overwrites this
file with per-case scored verdicts or explicit non-scored harness errors.

| id | status | scale | dimension scores | frozen sources (path@sha256) | score | pass | notes |
|---|---|---|---|---|---|---|---|
| _pending_ | — | — | — | — | — | — | run `eval_run.py --ledger` to populate |

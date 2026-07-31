# Eval Run Ledger

This file is the **evidence layer** for the eval suite. The deterministic CI
validators (`eval_schema_check.py`, `sequence_eval_check.py`, ...) prove the
cases are well-formed; this ledger records that the skill's *output* was actually
scored against the rubric in [`references/eval-rubric.md`](../references/eval-rubric.md)
by the model-in-the-loop harness `scripts/eval_run.py`.

## How to regenerate

A live scored pass needs network access and a key, so it runs outside the offline
CI gate:

```bash
export ANTHROPIC_API_KEY=...
python scripts/eval_run.py --ledger evals/eval-run-ledger.md --stamp <ISO-date>

export MINIMAX_API_KEY=...
python scripts/eval_run.py --provider minimax --region global_en \
  --ledger evals/eval-run-ledger.md --stamp <ISO-date>
```

The harness, for each case, builds a responder context from the real skill content
(root `SKILL.md` plus the case's expected sub-skills and any `state_fixture`),
gets a response to the case prompt, then has a judge model score that response
against the case's own assertions. Legacy cases use the rubric's 0-3 scale
(release: every case >= 2, average >= 2.6); sequence cases use the 0-4 scale
(release: critical cases at 4, no dimension below 3, average >= 3.5).

The offline wiring is checked in CI via `python scripts/eval_run.py --self-test`.

## Latest scored run

_Not yet scored live in this environment (no live provider credential is available offline)._
Run the command above to populate the table below; the harness overwrites this
file with per-case scores and a pass/fail verdict against the rubric thresholds.

| id | scale | score | pass | notes |
|---|---|---|---|---|
| _pending_ | — | — | — | run `eval_run.py --run --ledger` to populate |

# Evaluator module boundary

`scripts/eval_ledger_format.py` owns the pure text operations used to render
ledger fields and offline regeneration commands: Unicode validation, stable row
ordering, Markdown escaping, conservative command-value checks and POSIX /
PowerShell quoting. Their original names remain available from `eval_run` as
aliases, so existing imports and CLI entry points continue to work.

Scoring, source selection, provider requests, provenance validation and atomic
ledger publication stay in `scripts/eval_run.py`. This extraction does not
change output wording, escaping rules, command defaults or error classifications.
The existing integrity and provider tests remain the behavior contract.

The formatter is explicitly declared as an evaluator source in
`evals/source-manifest.json`, excluded from responder discovery and the installed
skill payload. Frozen release checks bind both evaluator modules to their actual
executed code objects, paths and source self-digests. Checks are repeated before
attestation and publication, so extracting code does not remove it from the
integrity boundary. Any future module extraction needs the same treatment.
Source counts and repository digests reflect the newly declared module; prior
evaluation records are not rewritten to pretend they used the new layout.

Run `python -m unittest tests.test_eval_ledger_format tests.test_eval_run_integrity`
for formatter and ledger contracts, and `python scripts/eval_run.py --self-test`
for the offline source wiring check. Neither command authorizes paid calls.

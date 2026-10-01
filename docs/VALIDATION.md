# Validation guide

The maintainer's long-form guide to the repository checks: what each proves, what it cannot prove, and how the evaluator and masthead toolchains are trust-bound. The [README](../README.md#validation) carries only the commands; this page carries the reasoning, kept verbatim from the earlier front page.

The validation toolchain supports **CPython 3.11 through 3.13**. CI exercises
both endpoints on Ubuntu and Windows; intermediate CPython 3.12 releases remain
inside the supported range. Python 3.10 and 3.14 are outside this lock's
supported range.

Run these checks before every release. The offline source-metadata check runs with
`--enforce-freshness` here so an old checked-in registry stamp blocks a release;
per-pull-request validation deliberately omits the flag, because metadata age
depends on the calendar rather than on the change under test.

The checks themselves are offline after their build dependencies are installed.
Two maintainer checks need third-party libraries: `schema_check.py` executes JSON
Schema instances, while `build_masthead_outlines.py --check` reproduces the
outlined masthead type. Install both hash-pinned toolchains first — the masthead
installer rebuilds a dedicated checkout-specific temp venv, resolves the lock
from the checkout, and creates it with `--without-pip`. Before that new venv's
launcher can bootstrap pip or install anything, the parent publishes and re-reads
an external initialized trust record for the runner and config. Only that
verified path may run bundled `ensurepip` and force-reinstall the locked wheels.
The installer retains the exact selected wheel bytes, validates pip's
install-report hashes against the lock, and seals
every installed distribution file from `RECORD`. Each installed import payload
must also match the retained locked wheel byte-for-byte. Verification and
rendering then require an external, checkout-keyed trust record that binds the
venv runner, `pyvenv.cfg`, builder script, lock, and sealed marker; the runner
must independently match the current Python installation's stdlib venv launcher.
They run in a fresh `python -I -S -B` child that exposes the sealed site-packages
only after startup, so `PYTHONPATH`, `sitecustomize`, `.pth` processing, a forged
venv runner, a parent preload, or a same-version replacement cannot skip hash
verification or shape the output:

`schema_check.py` proves structure and record-local constraints; it does not and
cannot prove graph-wide lineage. `project_state_check.py` and
`continuity_chain_check.py` are mandatory alongside it for duplicate IDs,
parent existence and order, cycles, executable parent-state continuity, and
binding every post-review clip status to its current take history and sibling
take-review record. Both semantic validators share the same bounded review
index; authority candidates must be stable regular non-link files no larger
than 1 MiB, their captured bytes are capped at 16 MiB per directory, and neither
validator accepts a project-state document as its own review.
Passing the schema alone is never a valid release or handoff gate.

`source_registry_check.py` parses the explicit `last_verified` field, rejects
missing, malformed, duplicate, or future stamps, and compares the checked-in
metadata dates of freshness-critical references. It does not fetch URLs and it
does not prove that any upstream claim is still true. A human or separately
authorized live-verification process must re-read the cited sources and update
the claims before changing a stamp.

```bash
python -m pip install --require-hashes --requirement requirements-validation.lock
python -I -S -B scripts/build_masthead_outlines.py --install-build-deps
```

```bash
python -I -S -B scripts/build_masthead_outlines.py --check
python scripts/validate_repo.py --release
```

`validate_repo.py` resolves the repository from its own file location and does
not call Git, so this release path also works from a Download ZIP extraction,
from a nested caller directory, and from a path containing spaces. The separate
masthead-outline check preserves its sealed build-environment trust boundary;
the runner covers the remaining canonical validators, tests, and an in-memory
source compilation that writes no bytecode.

### Git checkout-only hygiene

After the archive-safe checks, a maintainer working in a Git checkout should
also run:

```bash
git diff --check
```

This whitespace check requires Git metadata. Do not run it in a Download ZIP
extraction.

`prompt_architecture_stress.py` is a deterministic failure gate, not a creativity
or originality judge. In strict mode, every applicable dimension on every
`skill_formula` case must score at least 3, the arm average must remain at least
3.5, and materially different briefs may not reuse duplicate or near-duplicate
prompts. Its mechanical checks cover shooting-brief structure, brief-specific
traceability beyond generic production words, explicit camera/light/sound/action
contradictions, and repetition or padding patterns. Comparative creative quality
still requires blinded model evaluation and native-language human review.

The CI workflow runs the same archive-safe runner on push and pull request, with
the one deliberate difference noted above: it omits `--enforce-freshness`.
Checkout-only whitespace hygiene remains a separate CI step. These checks are
deterministic and offline — they prove the package is well-formed.

The multilingual fixture check proves byte-exact reference-token preservation,
canonical common-brief and candidate bindings, non-derived complete review-input
pins, literal identical-string overlap across locale realizations, and the exact
path, bytes, and digest of the canonical limitation disclaimer. It also runs a
best-effort English known-phrase lint across declared public text surfaces. That
lint is defense in depth, not proof that arbitrary prose or every supported
language contains no semantic overclaim. Translated or paraphrased template
detection, semantic differentiation, and reviewer-reasoning adequacy remain
independent human-review questions under
[`multilingual-native-review.md`](../references/multilingual-native-review.md).

### Checked-in source metadata age

Whether `references/source-registry.md` is stale depends on today's date, not on
the change being tested, so it is not asked per pull request — that would fail
unrelated work on a calendar boundary. It is asked in two places instead:

| Where | Behaviour |
|---|---|
| Release checklist above | `--enforce-freshness` blocks a release when the checked-in registry stamp is older than 30 days |
| `source-freshness-review.yml` | Runs Mondays 09:00 UTC on the default branch and reports metadata age as clean, drifting (past 14 days), or stale (past 30) |

Drift and staleness are tracked in a single automatically maintained issue. It
opens when the registry first drifts, is refreshed in place each week rather
than re-notifying, and closes itself once the registry is back inside the
window.

The scheduled job never edits the registry. Re-stamping `last_verified` without
actually re-reading the upstream sources would record a verification that never
happened, so refreshing it is deliberately a human step. A clean metadata-age
result means only that the recorded review date is recent enough; it is not a
live source or claim verification.

For a future paid comparison, the [capped rendered pilot](../evals/capped-rendered-pilot.md) defines 12 briefs, two arms and two takes, with a 16-attempt canary inside a 48-attempt ceiling. Its schedule is unexecuted; actual assets, settings, pricing and spending authorization must be supplied before a run.

To prove the package is also *good*, run the model-in-the-loop harness. Its
discovery phase sees the root router and a safe catalog, not the expected route
labels; the responder receives only the sources it selected, and the judge then
scores the answer against [`eval-rubric.md`](../references/eval-rubric.md):

```bash
# No network, credential read or ledger write: inspect the selected work first.
python scripts/eval_run.py --limit 1

# Explicit, bounded live smoke run. Supply the key through your environment.
python scripts/eval_run.py --live --limit 1 --max-calls 3 --max-output-tokens 3300 \
  --ledger eval-runs/smoke.md --stamp 2026-09-05

# Preview an alternate provider/region before choosing a live ceiling.
python scripts/eval_run.py --provider minimax --region global_en --limit 1
python scripts/eval_run.py --provider minimax --region cn_zh --model MiniMax-M2.7 --limit 1
python scripts/eval_run.py --provider orcarouter --limit 1
python scripts/eval_run.py --provider cheaperinference --limit 1
```

The optional [OrcaRouter evaluator](ORCAROUTER_EVAL.md) uses its native Messages endpoint and a restricted Claude allowlist. Its default is also an offline plan.

The optional [Cheaper Inference evaluator](CHEAPERINFERENCE_EVAL.md) uses its Anthropic-compatible Messages endpoint and a restricted model allowlist. Its default is also an offline plan.

For advisory current/proposed/plain comparisons, use the [outcome protocol](../references/outcome-comparison.md). It separates useful behavior from exact route agreement, preserves hard gates, and produces no aggregate score for incomplete runs. This offline support does not replace release evaluation.

Without `--live`, the harness prints an offline JSON plan, even if a key or
`--ledger` is supplied. `--self-test` remains the separate offline wiring check.
A live run uses `ANTHROPIC_API_KEY` or `MINIMAX_API_KEY` from the environment.
Each attempted request reserves one call and its requested maximum output tokens
before transport; failed requests do not refund that reservation. The default
ceilings are three calls and 3,300 output tokens per selected case. A full suite
requires an explicit `--max-calls`; inspect the plan and choose your ceiling.
Only a complete run may replace `evals/eval-run-ledger.md`.

Exhausting a ceiling stops the run with an incomplete/error assessment. The final
console summary reports attempted calls, reserved output tokens and validated
provider-reported usage; preserve that summary with the run log. Input tokens,
cache charges and currency cost are not capped or estimated, and failed requests
may still be billed. No live quality result is implied by an offline plan.


The harness uses `Authorization: Bearer <API_KEY>` as documented by both the
[global](https://platform.minimax.io/docs/api-reference/text-chat-anthropic) and
[CN](https://platform.minimaxi.com/docs/api-reference/text-chat-anthropic)
Anthropic-compatible Messages endpoints. Those provider contracts were checked
directly on 2026-08-01: both list the same eight supported models and the common
successful-response fields (`id`, `type`, `role`, `model`, `content`,
`stop_reason`, and `usage`), without requiring either `base_resp` or
`stop_sequence`. Anthropic's own response contract is validated separately,
including its required `stop_sequence` field.

Successful bodies are validated fail-closed: documented optional usage,
citation, thinking, and tool-call structures are type-checked with unknown
fields rejected, while optional MiniMax legacy `base_resp`/`stop_sequence`
fields cannot contradict an otherwise successful response. M2.x thinking
blocks are accepted only in their documented shape; unrequested tool calls and
Anthropic/M3 thinking are rejected as non-final evidence. Transport errors name
the failed open, context-entry, or read phase and redact API keys before console
or ledger output. Generated ledger commands are emitted separately for POSIX
shells and PowerShell, and are omitted when metadata is not safe to round-trip.

Before either offline or live evaluation starts, the harness resolves every eval
input through [`evals/source-manifest.json`](../evals/source-manifest.json), rejects
unclassified files, symlinks/reparse aliases, hard-link aliases, and digest
drift, then freezes the verified UTF-8 bytes for the whole run. The root router,
rubric, eval suite, fixture data, evaluator harness, planner catalog, responder
context, judge, and ledger therefore share one immutable source view. State
fixtures are strict JSON objects under `evals/fixtures/`; models receive the data
but never the fixture path. The judge receives the rubric, case prompt, expected
output, checks, and candidate response, but never expected route labels or
selected source paths. The harness also compiles the frozen evaluator source and
requires it to equal the module code object Python actually executed, with the
same physical `scripts/eval_run.py` path. Every recheck derives path, role, and
digest metadata again from the frozen manifest so a constructed snapshot cannot
reclassify responder files as evaluator-only inputs. A post-run check plus checks
immediately before and after the atomic ledger replace refuse release evidence
if any input changed after the snapshot; a failed post-replace check restores the
prior ledger. For a newly created destination, it invalidates only the retained
published inode to zero length through its open descriptor; a concurrent
namespace substitute is preserved untouched. That first publication is also
source-descriptor-bound: Linux links an unnamed `O_TMPFILE`, while Windows
renames the retained file handle to a target derived from the retained directory
handle. Neither platform re-resolves a mutable staging pathname. Existing ledger permission modes
are bound before the copy and preserved on both replacement and rollback; a new
POSIX ledger remains owner-only, while the Windows read-only attribute is retained
without modifying linked inputs. Bootstrap failure ledgers also
refuse direct, hard-link, symlink, or source-boundary aliases of repository
inputs before writing.

Blind discovery is scored, not merely recorded: after the planner returns, its
selected skill paths must exactly match the hidden
`skills_expected_to_activate` oracle. Missing, wrong, extra, duplicate, unknown,
or non-responder selections fail before response generation. Generated ledger
rows bind every selected responder path to its frozen SHA-256 digest; fabricated,
non-canonical, missing, or mismatched provenance cannot produce a release pass.
The ledger also records one canonical SHA-256 over the complete frozen
path/role/hash map, including `SKILL.md`, fixtures, evaluator files, and the
source manifest itself, plus per-role file counts. Release assessment accepts
that provenance only from the verified `FrozenRepository`; caller-supplied
digest maps cannot stand in for the evaluated checkout.
The canonical eval-suite and rubric digests are pinned so a structurally valid
but semantically gutted replacement also fails closed.

Every declared case oracle reaches the judge through a stable opaque criterion
ID. Assertions, required output sections, forbidden behaviors, `expected_output`,
`failure_mode`, `expected_state_delta`, and `expected_prompt_architecture` are
scored as exact judge-only criteria; `expected_sequence_relation` is bound into
the routing dimension. These oracle values remain hidden from discovery and
response generation, so binding them does not undo the blind-selection boundary.

Result rows have an explicit evidence status. `scored` means the judge returned
a complete, strictly typed verdict with every criterion and dimension ID exactly
once; only these rows enter quality floors and averages. A judge transport error,
timeout, empty body, oversized body, malformed JSON, or incomplete/invalid
verdict becomes `harness_error` with no numeric score or pass value. The harness
continues the remaining selected cases, writes a fresh auditable ledger, excludes
the error row from quality arithmetic, marks release evidence `NOT ELIGIBLE`, and
exits 1. It never represents missing judge evidence as a poor-output score of 0.

Case-contract or response-envelope failures are different: they are known before
the first provider call, so the whole live run aborts with exit 2. If `--ledger`
was requested, the stale artifact is atomically replaced by a bootstrap
`harness_error` ledger. Post-run snapshot drift likewise makes every recorded row
a non-scored harness error and exits 2.

This is the model-response quality gate, not a shape gate or a language/rendering
certification, so it lives outside offline CI; the latest run evidence is
recorded in [`evals/eval-run-ledger.md`](../evals/eval-run-ledger.md).
Language-quality review uses the independent evidence protocol in
[`multilingual-native-review.md`](../references/multilingual-native-review.md). CI
validates recorded bindings and scoring, while the truth and adequacy of
reviewer reasoning remain manual judgments.


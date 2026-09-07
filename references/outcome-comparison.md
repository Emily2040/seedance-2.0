# Outcome comparison protocol

Status: prepared, not run. There are no live comparison scores. The offline
reducer in `scripts/outcome_comparison.py` checks arithmetic and record shape;
it cannot establish that a human judgment is correct or that a clip will work.

## Freeze before collecting responses

Compare three arms on the same unseen briefs: `current` (the accepted release),
`proposed` (one exact candidate commit), and `plain` (the same model and user
brief without the skill). Record exact commits, SHA-256 of each arm's complete
source snapshot, protocol version/bytes, model identifier, provider, generation
settings, call ceiling, token ceilings and run ID. An arm is frozen for the run;
changing any input starts a new run. Keep source inventories with the artifacts.

An independent custodian writes held-out briefs before seeing candidate outputs.
Store briefs, assertions and reference answers outside the responder checkout.
Hash and seal them before the run. Give the responder only the brief, authorized
assets and observed state. Give the judge the same brief and hidden outcome
criteria, never the route oracle, source paths or arm identity. Randomize opaque
response IDs and keep the arm map separate until judgments are locked. Review
all arms in shuffled order; do not use the author of a change as its only judge.

Use at least one held-out variant in each family below; the public calibration
examples are training material, **not held-out evidence**. Include terse and
long briefs, user-selected creative choices, exact dialogue, actual-frame
continuation, missing references, and harmless alternate routes. Retain every
attempt including empty outputs, refusals, judge failures and interrupted runs.

## Judge outcomes, preserve release gates

Hard gates are `safety`, `state` and `reference_fidelity`: preserve authorization,
rights and spending boundaries; use observed state without replaying a completed
beat; preserve actual reference bindings without inventing available files.
A non-applicable gate is true only with a written explanation of why the brief
does not invoke it. A failed gate fails the response regardless of its mean.

Score each dimension from 0 to 3: 0 = absent or contradictory; 1 = major repair;
2 = usable with a localized repair; 3 = usable as written.

| Dimension | Evidence to quote |
|---|---|
| `brief_fidelity` | The required scene job, endpoint, exact line or invariant. |
| `directability` | Playable action, coherent camera and achievable temporal scope. |
| `specificity` | Concrete choices caused by this brief, not interchangeable praise. |
| `user_control` | Honored choices, budget, settings ownership and bounded uncertainty. |

Retain a brief quote, candidate quote and reason for every judgment, including
hard gates. A dimension below 2 fails even if the average is high. Resolve
material human disagreement through recorded adjudication, never by silently
averaging it away. Route agreement is an advisory boolean only in this study.
The reducer retains it and reports separate match/mismatch counts over validly
scored rows, even for an incomplete study; errors are neither matches nor
mismatches. These diagnostic counts do not affect quality scores or pass decisions.
The canonical `eval_run.py` exact-route gate and release thresholds remain in
force; this comparison cannot produce release eligibility or overwrite its ledger.

## Public human-calibration samples

| Brief | Candidate | Calibration decision |
|---|---|---|
| Static shot; fold one paper fan, no music. | Locked frame. Fingers fold the final pleat, then release the fan on the table. Dry paper rustle only. | Usable specificity/directability; an alternate lawful module selection alone must not fail it. |
| Same paper-fan brief. | A stunning cinematic masterpiece with breathtaking motion and immersive sound. | Specificity and brief fidelity fail; polished formatting does not recover the missing action and sound constraint. |
| Continue from an accepted frame: door already open, hand off latch. | Start on the open door; the hand lowers out of frame. Hold the empty doorway. | State can pass; judge against the actual supplied frame as well as these words. |
| Same continuation brief. | The hand grips the latch and opens the door. | State hard gate fails even if the prose is concise. |
| Say exactly “It still ticks.” No music. | The repairer says “It still ticks.” Once, at conversational pace. Clock ticks remain audible. | Exact line and audio constraints can pass. |
| No image attached; preserve my exact product. | The supplied @Image1 guarantees perfect product identity. | Reference fidelity fails: invents a binding and certainty. A conditional draft requesting the missing asset can pass. |

Two human reviewers first score these independently and discuss differences;
record their IDs, conflicts, scores and adjudication before held-out judgment.
These table decisions are author hypotheses, not completed human reviews.

## Offline reduction and evidence handling

Call `assess(record)` or `compare(case_ids, records)` from
`scripts.outcome_comparison`. A scored judgment has exactly:

```json
{"status":"scored","gates":{"safety":true,"state":true,"reference_fidelity":true},"dimensions":{"brief_fidelity":3,"directability":3,"specificity":3,"user_control":3},"route_matches":false,"error":null}
```

A transport, parser or judge-contract failure instead has exactly:

```json
{"status":"harness_error","gates":null,"dimensions":null,"route_matches":null,"error":"judge response incomplete"}
```

Each comparison row wraps a judgment with `case_id` and `arm`. The reducer does
not ingest or authenticate the source snapshots, quotes or reviewers: those
remain mandatory companion artifacts checked by the study operator. It rejects
duplicate/unexpected rows and invalid verdicts. Missing rows or harness errors
make the study incomplete with **no aggregate scores or pass counts**. Individual
valid scores may be retained as observations, never substituted for failed calls.

Do not send reference answers or calibration decisions through source discovery.
This protocol has an evaluator-only source-manifest entry. The reducer is
outside the responder discovery catalog. Both are excluded from the install payload. No provider invocation is added here. Collecting
live responses requires a separately authorized run and explicit ceilings.

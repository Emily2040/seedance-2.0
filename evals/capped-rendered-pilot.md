# Capped rendered pilot

Status: **pending / unexecuted**. This is a preparation protocol, not a generation
request, success-rate claim or statistically powered study. Existing
`generation-benchmark.json` cases remain synthetic structure fixtures. No rendered
observations or costs have been collected for this pilot.

## Question and scope

Does one frozen proposed skill revision produce more usable first attempts than
one frozen accepted revision on the same 12 briefs? Use the 12 brief definitions
in `scripts/pilot_plan.py`. Keep the current/proposed comparison separate from
the three-arm text study; a plain baseline is not included in this paid pilot.

Generate the offline schedule with:

```bash
python scripts/pilot_plan.py
```

The schedule is 12 briefs × 2 arms × 2 takes = **48 maximum attempts**. The four
canary briefs (fan, dialogue, product, continuation) use 16 of those slots. Only
32 remain after a complete canary. Stop the canary if an authorization/reference
failure occurs, if any quoted cost exceeds its reserved upper bound, or if more
than four of its 16 slots fail technically. Record the stop and keep the run
incomplete; do not replace difficult briefs to make the pilot look successful.

This helper has no credentials, network transport, login or generation path.
Its `authorized: false`, `actual_cost: null` and planned rows are deliberate.
Do not copy this planned output into an observed-results table.

## Freeze and approve before spending

Create a signed-off run packet: run ID; exact current/proposed commit hashes and
source inventories; all 12 unedited briefs; material/identity/motion references
with SHA-256, authorized use and exact surface binding; accepted final frame and
observed state for continuation; provider/surface, model/version, resolution,
duration, aspect ratio, audio mode and seed (or explicit unsupported status).
Choose one setting configuration supported for both arms. The continuation and
product references must actually exist; missing assets block their slots.

Select and freeze those settings and references before either arm writes its
prompt. Keep external settings outside prompt prose where the surface owns them.
Within each brief freeze the same inputs across both arms and both takes. Use
matched seeds when supported, recording that they do not guarantee deterministic
or equivalent outputs. Preserve the schedule's assigned within-pair arm order:
each phase and take stratum balances which arm leads, and each brief reverses its
leader for take two. Randomize whole brief blocks within each phase and save that
order before the first request; do not sort pairs back into current-first order.

Obtain explicit execution authorization for the provider, 48-attempt maximum,
account, expiry and all-in credit/currency ceiling. A request to prepare or merge
this protocol is not that authorization. Check current pricing on the actual
surface, including audio, failures, retries and tax where applicable. Record its
timestamp and provenance. `cost_ceiling(Decimal(per_attempt), Decimal(budget))`
calculates 48 × the supplied all-in per-attempt upper bound in the same unit; it
cannot establish that the supplied price is correct. Never substitute average
cost for a bound. If a reliable charge ceiling cannot be enforced, do not start.

## Attempt accounting and interruption

Before transport, persist the slot ID, request hash, start time, reserved maximum
charge, remaining attempt count and remaining money. Every submitted request
consumes its slot, including timeout, moderation block, empty output and failed
download. No automatic retries. Query an existing request by its provider ID
where supported before deciding its status; status checks are not new renders.
An ambiguous submission is `unknown`, retains its reservation and stops further
spending until reconciled. Do not relaunch it on restart.

Keep an append-only observation log with run/slot ID, provider job ID if known,
prompt and settings hashes, timestamps, submitted/blocked/failed/unknown/completed
status, actual cost or explicit `unknown`, artifact hash and failure reason.
Keep the original 48-slot schedule alongside it. An incomplete pilot, missing
receipt, unknown charge, skipped slot or unresolved request stays incomplete.
Unused slots are not successes. Any retry needs a separately authorized protocol
revision and cannot be pooled silently into this two-take comparison.

## Blinded review and reporting

Assign opaque clip IDs and hide arm/commit/prompt-author identity from two
independent reviewers until individual judgments are locked. Both see the exact
brief, reference roles and acceptance criteria, but not the other reviewer's
notes. Disclose conflicts. Review each completed clip for brief fidelity,
continuity, product/reference identity, action completion, temporal stability,
audio/exact dialogue, and usable endpoint. Mark non-applicable dimensions with a
reason. Use 0 = unusable, 1 = major repair, 2 = local repair, 3 = usable as is.
Any rights/authorization failure or wrong observed starting state is a hard fail.
Quote timecodes and visible/audible evidence for each material judgment.

Predeclare primary outcome: proportion of the **12 scheduled take-one slots per arm** that
both reviewers judge usable as is (all applicable dimensions 3 and no hard fail).
Count technical failures and missing take-one clips in that denominator, separately from
quality ratings on rendered clips. Adjudicate disagreement with retained notes;
show original and adjudicated counts. Report both takes, paired per-brief results,
all failure statuses, attempt totals, actual charges including failures, and cost
per accepted take only when charges are complete and accepted count is nonzero.
If zero accepted, show no finite cost-per-accepted figure. Do not headline a
best-of-two result as first-attempt quality. Secondary outcomes report take-two
quality separately and pooled per-render usability over all 24 scheduled slots
per arm, with explicit denominators. A better second take cannot change the
primary first-attempt outcome. An interrupted run remains incomplete, regardless
of any interim proportion.

Keep all results including the stopped canary. Label the schedule `planned`,
mock tooling data `synthetic`, and real records `observed`; those categories must
never be pooled. Publish limitations: small selected set, one surface/settings
configuration, stochastic outputs, subjective judgments, no language coverage or
general superiority claim. Preserve observations if the protocol is later retired.

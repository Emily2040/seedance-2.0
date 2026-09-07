# Retake Protocol — decide whether another take is useful

Use this after a returned take or a user-reported failure. A diagnosis is a proposal, not authorization to generate again. Preserve the user's acceptance criteria, settings, references, prior decisions, and remaining take/spend limits. This is internal workflow guidance; prices and supported edit operations require current evidence from the active surface.

## Inspect before deciding

Name the failed criterion and the evidence: a timestamp, frame, audible error, or explicitly labeled user report. If the host cannot inspect the relevant media, say so and work from that report. Do not claim the take was watched or measured. Keep what already worked visible in the diagnosis so a repair does not discard it.

Separate a plausible cause from an established fact. The same failure in two or three takes does not prove that the prompt is wrong; references, settings, unsupported controls, model limitations, and variation can also contribute. Use [model-mechanics](model-mechanics.md) for testable hypotheses, not hidden-model explanations.

## Choose a verdict

| Verdict | When it fits | Tradeoff or next step |
|---|---|---|
| **Keep** | The shot meets its must-pass criteria. | Accept it and record any allowed deviation; do not spend for an unspecified ideal. |
| **Fix in post** | A localized trim, mix, text overlay, or other feasible edit can meet the criterion. | Check available tools, effort, and whether the fix harms another requirement; post work is not automatically free or trivial. |
| **Edit** | A supported operation can repair the failed layer while preserving the rest. | State the intended change and locks; an edit may still alter other layers and consume credits. |
| **Re-roll** | The current brief remains plausible and another sample could answer a useful question. | Same requested settings, a new seed only if supported and authorized; no certainty that the cause was sampling luck. |
| **Rewrite** | A specific ambiguity, conflict, or missing action has a plausible repair. | Show the smallest relevant prompt change and what it preserves; do not blame the prompt merely because several takes failed. |
| **Stop / change approach** | The budget is exhausted, the user wants to stop, or another take has little expected value. | Keep useful footage and offer a revised shot plan, post work, a practical shoot, or stopping here. These alternatives have their own costs and authorization boundaries. |

## Check the authorization before an external action

1. Reuse the user's existing authorization. Distinguish permission to review or rewrite from permission to submit a generation, edit, upload, or batch.
2. Identify the remaining limit: authorized takes minus attempted submissions, and any applicable currency or other cap. Include failed or uncertain submissions unless their non-submission or refund is confirmed. An uncertain timeout is not permission to submit a duplicate; query the existing job only through an authorized read path when available.
3. Preserve model/tier, operation, duration, resolution, reference roles, and output scope. Changing one of these is a proposal unless the user's existing authorization covers it. A request to “try again” does not imply an upgrade or longer clip.
4. If a currency cap applies, use current surface-specific pricing and a defensible maximum charge before submitting. Unknown pricing stays unknown; a take cap alone is not a money cap. Do not invent a price, refund, retry allowance, or a new budget.
5. At zero/exhausted budget or an explicit stop, request no further generation. Continue with authorized review, a draft revision, or a post plan if useful. Do not pressure the user to top up. If a new external action is requested but its scope is missing, prepare the concrete change first and ask only for the missing authorization.

Never default to five Standard takes or ten Fast drafts. A cost example is not a spending allowance. Keep the user in control of whether the next useful step is a prompt revision, a paid take, an edit, or no more work.

## Make a comparison useful

Prefer changing one relevant variable when the purpose is diagnosis. Record the exact change and the preserved settings. A shared seed does not make different prompts or tiers a controlled experiment. If several changes are needed to fix a clearly invalid setup, make them together and label the result a combined repair rather than attributing success to one change.

Fast, short, or low-resolution drafts can answer some composition questions, but their behavior may not transfer to the final tier, duration, or resolution. Use a cheaper draft only if it tests the actual criterion and is within the user's authorized scope. Do not claim that ten short drafts necessarily teach more than one longer clip.

## Compact response and take log

For a partial failure, a useful response is:

> The label becomes unreadable during the turn (user-reported). Motion and viewing angle may contribute. Keep the accepted lighting and bottle shape; try ending the turn before the label becomes edge-on. One of your three authorized takes remains, with the same model, duration, and resolution. Alternatively, keep the current take and use the approved still for the end hold.

This is a fictional, unrendered review example. In a real review, use actual observations and authorization; never copy its remaining-budget claim into another job. Only offer the still end hold when the asset exists and the edit is feasible.

One line per take can record:

`Take N · failed criterion and evidence · kept strengths · hypothesis · proposed change · preserved settings · remaining authorized limits · verdict / stop reason`

Keep review notes internal or in an already authorized project record. Do not put budget arithmetic, diagnosis labels, or future attempts into the generation prompt.

## Decision examples for review

These cases specify intended skill behavior, not measured live-model results:

| Input situation | Expected decision |
|---|---|
| Two similar failures, one authorized take left | Consider prompt, references, settings, and model behavior; propose one useful comparison without declaring the prompt wrong by definition. |
| Zero takes left; user asks what to change | Provide a draft change or post option; submit nothing and do not request an automatic top-up. |
| User approves one retry at the same settings | Preserve tier, duration, resolution, and scope; do not upgrade to Standard or lengthen the clip. |
| User asks only to rewrite the prompt | Return the revision without submitting a generation or asking for an unnecessary generation budget. |
| Prior submission timed out and charge/job status is unknown | Count it conservatively; do not blindly resubmit or assume the attempt was free. |
| A Fast draft works but exact final dialogue matters | Explain that the final setting still needs review; any further test requires remaining authorization. |

## Sequence Canon

A take review decides whether footage becomes canon:

- Accept: record observed start/end state and allow it to become a parent source.
- Accept with deviation: record the deviation, update downstream beats, and carry unfinished work forward.
- Repair: do not advance the sequence until the repaired tail or layer is accepted.
- Reject: do not update canon and do not use that take as a parent source.

Accepted observed state overrides planned state. If a clip unexpectedly completes a future beat, mark that beat completed and remove it from later prompts. A rewrite, retry plan, or exhausted budget does not itself approve footage or change observed state.

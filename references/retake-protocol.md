# Retake Protocol — the iteration economy

*What happens after a generation comes back. The rest of this skill plans the shot and repairs outright failure; this governs everything in between — the partially good take, which is most of real production. Labels: [heuristic] = default to test · [internal] = workflow guidance. Cost figures are surface-specific and volatile: load `api-status.md` and verify live before budgeting.*

## Triage every take — five verdicts

| Verdict | When | Next move |
|---|---|---|
| **Keep** | The primary spend (the thing this shot is FOR, per `allocation-model.md`) is delivered and nothing is fatal. | Lock it, log it, move on. Perfection in secondary details is post's job. |
| **Fix in post** | The flaw lives in post's domain: color, on-screen text, sound mix, trim, a few unstable frames at the ends. | Never burn takes on what an editor fixes in minutes. |
| **Edit, don't regenerate** | Composition and timing are right; exactly one layer is wrong, and the surface supports edit. | Preserve the take as the source clip; change only the failing layer. |
| **Re-roll** | The prompt is right; the sample was unlucky (sampling variance). | Same prompt, new seed. Two or three re-rolls maximum — then the prompt is the problem, by definition. |
| **Rewrite** | The same flaw appears in two or more takes. | It is systematic, not luck. Diagnose by mechanism (`model-mechanics.md`), change the prompt. |

## The one-variable rule [heuristic]

Change one thing per retake: one prompt clause, OR the seed, OR the mode, OR one reference — never several. Same seed plus one prompt change is the closest available thing to a controlled experiment; new seed with the same prompt is a pure re-roll. Change two things at once and the result is unreadable either way it lands — you learn nothing.

## Attempt budget [heuristic]

Set it before take one: a number of takes (default: five standard-tier, or ten fast-tier drafts) and a written "good enough" — the primary spend delivered, secondary flaws postable. At half the budget with no progress on the same flaw, stop iterating and change strategy: a different mode, decomposition into more shots, or the honest exit below. Iteration without a stop condition is how a five-dollar shot becomes a hundred-dollar shot.

## Cost awareness [internal]

Every second of generation costs real money, and retakes multiply it: at the fal figures last verified in `api-status.md` (≈$0.30/s standard 720p, ≈$0.68/s 1080p — verify live), a single 15-second standard take is several dollars, and a ten-take session is a real invoice. Spend accordingly:

- **Draft cheap, lock expensive**: explore composition on the fast tier, short durations, or lower resolution; spend standard tier and full length only on the locked design.
- Ten four-second drafts answer more questions than one failed fifteen-second take.
- Quote costs to users only with the verification date and a verify-live caveat.

## The shot log [internal]

One line per take — this is the story state made auditable:

`Take N · changed: [the one variable] · seed: [same/new] · verdict: [keep/post/edit/re-roll/rewrite] · evidence: [one sentence]`

Re-reading the log beats re-living it. Two takes in the log with the same flaw is a rewrite, by rule — no third attempt on luck.

## Sequence Canon [internal]

For sequence projects, a take review decides whether footage becomes canon.

- Accept: record observed start/end state and allow it to become a parent source.
- Accept with deviation: record the deviation, update downstream beats, and carry unfinished work forward.
- Repair: do not advance the sequence until the repaired tail or layer is accepted.
- Reject: do not update canon and do not use that take as a parent source.

Accepted observed state overrides planned state. If a clip unexpectedly completes a future beat, mark that beat completed and remove it from later prompts.

## When the answer is "don't generate"

Honest direction sometimes refuses the tool: dense on-screen text belongs to post, a real product's exact behavior may belong to a camera, archival reality belongs to licensing, and a shot that has failed its budget twice after decomposition belongs to a different idea. "Film this one for real" is a deliverable, not a failure.

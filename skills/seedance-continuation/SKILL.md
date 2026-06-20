---
name: seedance-continuation
description: "This skill should be used when a Seedance 2.0 user asks to continue, extend, make the next part, repair the tail, bridge between known frames, re-anchor drift, or create a successor prompt from accepted footage."
license: MIT
user-invocable: true
tags:
  - continuation
  - extend
  - continuity
  - seedance-20
metadata:
  version: "6.0.0"
  updated: "2026-06-20"
  parent: "seedance-20"
  author: "Iamemily2050 (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: "🎬"
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-continuation

Use this for seamless continuation, intentional next shots, bridge clips, tail repair, and re-anchoring after drift. A continuation prompt must be grounded in accepted footage, not only in the old plan.

Load `[ref:continuation-handoff]`, `[ref:sequence-project-state]`, `[ref:prompt-compiler]`, `[ref:reference-transfer-contract]`, and `[ref:continuity-qc]`. Load `[ref:failure-atlas]` when the continuation failed or drift is visible.

## Required Input Gate

Before writing any continuation prompt, require:

- `project_id`;
- current `clip_id`;
- valid `parent_clip_id`;
- full-story objective;
- final story outcome;
- next planned narrative job;
- accepted previous clip or accepted final frame;
- `observed_end_state`;
- continuity locks;
- exact reference registry;
- active surface or conservative surface profile.

If the source is unavailable, say: "I have the story plan, but I do not have the actual ending of the previous generation. Upload the clip or its final frame, or describe exactly what is visible at the end. I should not invent the continuation state."

Do not hide this uncertainty by writing a speculative prompt.

## Continuation Types

`seamless_continuation`: same shot, same geography, same open motion, same or motivated camera continuation, and accepted previous footage as the source.

`intentional_next_shot`: an editorial cut is appropriate. Story continuity matters, but exact frame continuity is not promised. Do not call it seamless.

`bridge_between_known_states`: a defined start state and end state must be connected, often with first/last-frame generation when the active surface supports it.

`repair_tail`: the previous final seconds failed. Repair, edit, or regenerate the tail before continuing because continuing from a failed tail amplifies the error.

`reanchor_after_drift`: identity, detail, geography, motion, audio, or world continuity degraded. Return to canonical identity, the strongest accepted final frame, a stable source clip, or a new intentional shot using canonical references.

## Canon Rule

Accepted observed footage overrides planned state. If the plan says the subject reached the car door but the accepted clip ends two steps away, the next prompt begins two steps away. It does not replay the terminal exit, and it does not assume the subject is inside the car.

Rejected footage never updates canon and never becomes a parent source.

Track `extension_depth`. At depth 2 or greater, warn that repeated extension can increase continuity risk. When visible drift has begun, recommend re-anchoring instead of blindly extending again.

## Output Contract

Return:

1. Continuation type.
2. Source evidence used.
3. Observed end state.
4. Next clip contract.
5. Continuity locks and allowed changes.
6. Completed beats to exclude.
7. Reserved future beats to exclude.
8. Final natural-language Seedance prompt for the current clip only.
9. Updated Project State Capsule or a request for missing source evidence.

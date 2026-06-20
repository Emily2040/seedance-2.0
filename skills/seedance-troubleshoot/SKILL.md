---
name: seedance-troubleshoot
description: "This skill should be used when a Seedance 2.0 output is blurry, jittery, off-prompt, morphing, blocked, visually generic, unstable, desynced, inconsistent, or otherwise fails and needs root-cause diagnosis."
license: MIT
user-invocable: true
tags:
  - diagnostics
  - troubleshooting
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

# seedance-troubleshoot

If the take is partially good rather than failed, route to `[ref:retake-protocol]` triage first - most takes deserve a verdict, not a rewrite. Diagnose failure before rewriting. Do not simply add more adjectives. Identify whether the failure came from mode mismatch, overload, ambiguity, fragile identity, unsafe wording, unsupported platform behavior, or missing preservation constraints.

When the diagnostic tree has no row for the failure, load `[ref:model-mechanics]` and diagnose by mechanism: attention dilution, prior conflict, summoned negation, broken trajectory, compounding error, conditioning conflict, capacity starvation, or an overloaded audio-video joint constraint. Load `[ref:field-observed-tips]`, `[ref:reference-workflow]`, and `[ref:api-workflow]` when the failure involves continuation, edit/extend, source clips, audio references, or platform-specific errors. Load `[ref:shot-list-continuity]` for multi-shot drift and `[ref:delivery-qc]` for final-client or delivery failures. When sequence state is present, load `[ref:failure-atlas]`, `[ref:continuation-handoff]`, and `[ref:continuity-qc]`; diagnose against continuity locks, completed beats, exact reference tags, and reserved future beats.

## Intent

A failed generation feels personal - the user showed the machine their idea and the machine returned something broken. The soul of this skill is rescue without blame: name the mechanism, never the user; save the idea, not just the prompt. They should leave with a fix and their confidence intact.

## Diagnostic Tree

| Symptom | Likely cause | First repair |
|---|---|---|
| Product or face changes | I2V prompt re-described visible identity or overloaded motion. | Add preservation constraints; remove duplicate static detail. |
| Camera jumps | Several incompatible moves or no endpoint. | Choose one move with start and finish. |
| Generic output | Hollow style words and weak action. | Replace with physical action, source light, material, and sound. |
| Motion ignored | Static prompt or no visible consequence. | Add actor, verb, timing, and changed end state. |
| Lip-sync poor | Moving head/camera, long dialogue, unassigned speaker. | Lock framing, shorten line, assign speaker. |
| VFX noisy | Effect has no source, physics, or dissipation. | Add source, material, path, interaction, and endpoint. |
| Prompt blocked | Protected IP, real-person, graphic, or bypass-like wording. | Rewrite intent in safe production language without evasion. |
| Extension quality degrades | No last-frame anchor or too many new variables across continuations. | Use returned last frame as first frame and change one variable. |
| Audio reference ignored | Competing video sound, no visual beat mapping, or unsupported combo. | Mute competing video and map one visible event to the beat. |
| Text/logos break | Small text asked to move or be redrawn. | Keep text static, centered, and protected; animate light around it. |
| Client QC fails | Prompt output treated as final delivery without post/QC. | Route to delivery preflight, post fix, or regenerate only the failing shot. |
| Continuation assumed planned ending | Previous clip was not reviewed or observed_end_state was ignored. | Replace opening with actual observed end state. |
| Previous action restarted | Completed beat was not marked already_happened. | Add completed beat exclusion. |
| Future beat leaked | Reserved beat entered the current prompt. | Remove future beat and stop earlier. |
| Identity reference conflicts with continuity source | Source clip controlled transient state and identity at once. | Re-anchor identity from canonical reference. |
| Screen direction reset | Axis relation was not locked or intentionally reset. | Preserve screen direction or declare new-shot axis reset. |
| Open motion lost | Subject or camera vector was not inherited. | Carry motion vector into the opening sentence. |
| Camera phase restarted | Parent camera endpoint was not recorded. | Start from observed camera phase. |
| Prop state contradicted | Owner, position, or condition was missing. | Add prop state handoff. |
| Audio phase restarted | Completed dialogue or music phase was not logged. | Continue or intentionally change the audio phase. |

## Repair Process

First quote the failing phrase or missing element. Then name the root cause. Next, remove conflicts rather than adding complexity. Recommend one primary repair variable rather than adding more adjectives. Finally, produce one conservative retry prompt and one optional creative variant only if the user wants exploration.

## Conservative Retry Pattern

`[Reference role if any]. Preserve [identity/product/environment] exactly. One visible action: [specific verb and consequence]. Camera: [single move]. Lighting: [physical source]. Sound: [ambient/SFX/dialogue]. Constraints: [what must not change].`

## Escalation Rules

If the same error repeats, split the scene into shorter clips, reduce characters, simplify hand or face motion, use stronger reference role mapping, or change the mode. For unstable text/logos, keep them static, centered, and protected; do not ask the model to redraw small text during motion.

For edit/extend failures, preserve the source clip first and change only the failing layer. If a surface supports returned last frames, use that still as the next first-frame anchor before extending.

## Output Contract

Return root cause, evidence from the prompt or result, repaired prompt, and one conservative retry variant.

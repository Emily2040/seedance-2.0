# Model Mechanics — hypotheses for troubleshooting

Use this reference to propose a repair when an existing checklist does not explain a failure. These are **internal workflow heuristics**, not measured laws or descriptions of Seedance's hidden computation. An output defect can have several causes; one take cannot identify an architecture or training-data cause.

The [official model page](https://seed.bytedance.com/en/seedance2_0) describes unified multimodal audio-video generation. The [model card](https://arxiv.org/abs/2604.14148) reports capabilities and evaluations. Neither establishes the prompt-token weights, spatial allocation, reference precedence, or reset interval asserted by earlier versions of this guide. Sources checked 2026-09-07; suggestions below remain unbenchmarked by this repository.

## Eight diagnostic questions

| Symptom to inspect | Possible explanation | One change to try | Limit or counterexample |
|---|---|---|---|
| Subject or action is missing | The brief has conflicting priorities or leaves the action vague. | Put the essential subject, action, and endpoint together; remove a competing request. | A longer prompt may be necessary for exact dialogue or continuity. Earlier words are not proven to receive a fixed larger weight. |
| Style changes between shots | References or shot descriptions disagree about medium, texture, or lighting. | Repeat the few appearance anchors that must persist; resolve conflicting references. | This cannot establish “cluster hopping” or how often a scene appeared in training. |
| An excluded element appears | The constraint is ambiguous, incompatible with a reference, or simply missed. | Describe the desired visible arrangement and preserve any necessary explicit exclusion. | Negation can work. Mentioning a flaw does not prove it caused that flaw; no universal negative-prompt field is assumed. |
| Action is skipped or unclear | Too many events compete for the available time, or the physical sequence is underspecified. | Give the main action a visible cause, endpoint, and time to complete. | Fast montage and stylized discontinuity can be intentional; do not simplify away the user's direction. |
| Identity drifts in a continuation | The accepted frame already contains drift, reference roles conflict, or the new shot changes appearance. | Inspect the actual prior final frame and compare it with the original identity references before continuing. | No fixed “fifth generation” reset law is established. Original references preserve identity; an approved output frame can preserve current pose and state. Use each for its own role. |
| A reference fights the prompt | Both specify different values for the same property. | Assign each reference a role; state the intended change and what must remain. | Images do not universally outrank text. Editing appearance is a valid request; deleting all appearance text would defeat it. |
| A small face, hand, label, or prop is unreadable | Framing, occlusion, motion, output resolution, or generation error limits readability. | Make the important detail larger, slow the relevant action, or reserve an insert/post step. | Screen-area percentage is not a measured percentage of model representation; more pixels do not guarantee correct detail. |
| Speech or sound misses the visible event | Timing, speaker attribution, performance, or competing audio instructions failed. | Isolate the cue or speaker, reduce competing motion, and inspect the returned audio and picture separately. | Joint audio-video generation does not guarantee lip-sync, exact playback, or explain a particular denoising process. |

## Turn a hypothesis into a useful choice

1. Name the observed failure and the detail that must survive the repair.
2. Check the reference, active-surface settings, and prior accepted state before blaming the prompt.
3. Offer the smallest relevant change and its tradeoff. Keep the original wording/settings for comparison.
4. If the user authorizes another generation, change one variable and record the result. Stop at their take or spend limit; a diagnosis is not permission to spend credits.
5. Keep a surprising successful take visible. Revise the hypothesis instead of inventing a mechanism to preserve the rule.

**Example: a reflection acts independently.** The requirement is a readable mismatch between a person and their reflection. A same-frame attempt tests whether both actions can remain distinct. An insert of the reflection gives more control but loses simultaneous comparison. Compositing preserves that comparison at the cost of post work. Present these choices; do not claim the model cannot perform the effect because “mirrors fight its prior.”

## Continuation handoff

Separate a generation defect from a bookkeeping defect. Repeating an already completed action or starting from a planned rather than observed pose may come from an incorrect handoff. Keep the approved actual final frame, original identity references, completed beats, and reserved future beats in their distinct roles. Use [continuation-handoff](continuation-handoff.md) before compiling the next clip.

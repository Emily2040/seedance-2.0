# Multi-Shot Grammar — direct cuts inside one generation

Multi-shot means several shots within one generated clip. It is not new to the 2.0 line: the [Seedance 1.0 paper](https://arxiv.org/abs/2506.09113) already describes native multi-shot generation. Seedance 2.0's [launch post](https://seed.bytedance.com/en/blog/seedance-2-0-official-launch) demonstrates multi-shot audio-video output. These are capability descriptions, not guarantees that each requested cut will land. Provider sources checked 2026-09-07; the official shot-order statements below were recorded 2026-09-26.

## What the official material rules: shot order, not seconds

Seedance 2.0 keys on **shot order**. Volcengine's Seedance 2.0 prompt guide (document 82379/2222480) says to mark shots as 镜头1, 镜头2, 镜头3 in the order events happen, not to force a duration on each shot, and to let the model set the rhythm from the story. The same guide says the model's support for precise time ranges such as 0–3 秒 is unstable and that forcing durations can produce abnormal output. ByteDance's Seedance 2.5 prompt guide (document 82379/2607689, dated 2026-08-07) lists the difference between the lines outright: 2.0 responds to shot numbers, not timestamps; the newer line responds to integer-second timestamps. ByteDance's troubleshooting file in its `agentkit-samples` repository repeats the 2.0 warning word for word. No official document states a maximum shot count; the official worked examples use three shots for a 15-second clip.

Evidence boundary: the Volcengine pages are outside this repository's review environment, so these statements were read from hash-recorded mirrors of the official PDFs and from ByteDance's GitHub organisation. `docs/EVIDENCE_NOTES_2026-09-26.md` holds the quotes and locators; recheck the live pages before quoting them as current. Two first-party artefacts still show second ranges (the official 2.0 tutorial's showcase prompt and the agentkit skill's storyboard), so the official corpus is not perfectly consistent. The weight of official text is shot order. Seconds therefore survive in this file only as an internal budget, never as prompt syntax on 2.0.

What this means in the prompt:

- Number shots in event order. Chinese prompts use 镜头1 / 镜头2 / 镜头3; English prompts use `Shot 1` / `Shot 2` / `Shot 3` as the same device. Plain prose with “cut to” remains valid prompting ([Runway's official help](https://help.runwayml.com/hc/en-us/articles/50488490233363-Creating-with-Seedance-2-0) shows a multi-shot prose example without headings), and no cited source establishes a universal label parser.
- Write the cut inside the block, in words: “cut to a low angle from the doorway”, 镜头切至, 硬切. A bare label organises content; it is not a cut command.
- Order each shot block the way the guide recommends: the camera move or cut type first, then the subject's action and expression, then any position or space change, then the audio for that shot. End every block with a lock line that repeats the light, each principal's identity and each principal's position in the same words as the first shot; the rules for that, for feeling-plus-anchor expression, for keeping the rest of the frame alive and for prop mechanics are in [direct-for-the-model](direct-for-the-model.md).
- Do not write absolute seconds inside shot blocks on 2.0. When a beat needs a felt length, write it as behaviour: “hold on the settled fan for one beat”, not “hold 2 s”. Timestamp lists also compete with an audio reference as a second clock (see [audio-guide](audio-guide.md)).
- Set duration as the surface parameter. On Chinese-facing surfaces, an optional echo at the start or end of the prompt, 时长：X秒 written with the Chinese 秒, is a documented reinforcing tip, not a control.
- One camera move per shot. A locked camera is written in prose, because `camera_fixed` is not supported on the 2.0 series.
- Constraints stay to the documented sentences (no subtitles, no logo, no watermark) plus this repository's preservation clauses.

## Choose the shape before choosing notation

A storyboard is a content decision, not a duration decision. A 15-second clip of one woman reading a letter is one paragraph.

| Shape | When | What the prompt looks like |
|---|---|---|
| **Continuous** | One scene, one continuous action or state change, at most one speaker, even with a long line | One paragraph in the official order: subject and action, scene, light, one camera move, sound, constraints. No shot labels. Phases, if needed, are written as Beginning / Then / Finally, never as second ranges. |
| **Storyboard** | Several events, a location change, a reveal that needs a cut, or a comparison | Numbered shot blocks in event order, each in the four-part block order above. |

| User's priority | Starting approach | Tradeoff |
|---|---|---|
| One continuous performance | Say “single continuous take”; describe phases and the final hold. | Less editorial control inside the take. |
| A reveal, reaction, or comparison | Describe two shots and the action that motivates the cut. | Each shot needs enough time for its essential beat. |
| Fast montage | Use brief, distinct images with explicit cuts and a total duration supported by the surface. | Less time for dialogue, detailed actions, and final holds. |
| Exact frame timing | Plan separate clips and edit them in post. | 2.0 does not respond to timestamps; model-generated timing alone is insufficient. |

## Score the load, then offer the ladder

This section is an **authored heuristic**, not a documented limit. The official material gives one mechanism for deciding how much belongs in a clip: density. Too little content for the duration and the model improvises; too many shots or too much dialogue for the duration and content and lines garble, and the official remedy is to split, for example four shots into two videos ([event-density](event-density.md) quotes it). The table below turns that warning into a number the agent can explain.

For a storyboard clip, list the beats the user wants (each beat is one shot), then add load points:

| Element in a beat | Load | Why |
|---|---|---|
| A camera move within the shot (a cut to a new locked framing scores 0; the cut is already the beat boundary) | 0.5 | Official: one move per shot; a move needs time to read |
| A spoken line | 1 per 8 English words or 12 Chinese characters, minimum 1 per line | Speech needs its own seconds; these rate constants are unmeasured on 2.0 |
| Each person in frame beyond one | 1 | Multi-subject omission and duplication are documented continuation defects, and the model card lists multi-speaker lip-sync errors |
| Physical contact between bodies, or between a body and a prop, that must land | 1 | Fragile physics; needs a visible cause and endpoint |
| A location or setting change | 2 | A new space is a new composition and light |
| A sound cue that must land on an action | 0.5 | Sync is probabilistic |

A reaction shot or an insert, meaning a shot with no new action, no spoken line and no camera move (a face taking in what just happened, a hand on a cup, a door closing), counts half a beat, because it needs one to two seconds and the model holds it easily. This is what lets a fifteen-second scene be cut like coverage, wide, face, insert, reaction, face, without the count reading as reckless.

Total load L. Available seconds D come from the surface parameter (4–15 on 2.0). Seconds per load point S = D ÷ (beats + L), with reactions and inserts at 0.5 each.

| S | Reading | Ladder position |
|---|---|---|
| 3.0 or more | Comfortable | **Safe** |
| 2.0 to 3.0 | Tight; dialogue and contact at risk | **Stretch** |
| Under 2.0 | The official density warning's territory | **Ambitious**: propose two generations instead |

The constants are consistent with the official three-shots-per-15-seconds examples (one move each: S = 3.3, Safe) and with the field-reported 2–4 sub-shots per 8–15 seconds. They are the first thing a rendered calibration pilot should measure; until then, say so when you use them. Short-drama coverage, four or five shots with a reaction and a line or two in fifteen seconds, lands on Stretch by this arithmetic, and that is the honest label: it is the register the genre is cut in, and the front-page gallery runs it on purpose as the calibration the thresholds are waiting for.

Building the ladder from the user's beat list:

1. Compute S for the beats as asked. That count sits on one rung.
2. Offer the rung below by merging the two lightest beats into one shot (their lines and contacts carry over; the cut disappears), and the rung above by adding the beat the user would most want next.
3. When the list is already Ambitious, offer Stretch and Safe by merging, or by splitting the clip into two generations that keep every beat.
4. When only one count fits, present two rungs, not three.

Wording the agent uses when the shot count is open:

> **Safe, 3 shots.** About 4 seconds per load point; the line “It still ticks” has room to land and settle.
> **Stretch, 4 shots.** About 2.5 seconds per load point; the reaction after the line may get cut short.
> **Ambitious, 5 shots.** Under 2 seconds per load point with a spoken line, which is where the official guidance says lines start to garble. If you want five beats, two generations of 8 seconds are the better spend.
> Pick one, mix two, or say “choose for me”. Six-shot prompts you see online are usually simple montages with no dialogue, or the newer model line.

Rules:

- The ladder is a menu, and menus stay optional. When the user has fixed the shot count, write that count, state its rung in one line, and offer a neighbour only when the count is Ambitious. When the count is open, present the rungs and a recommendation, then write **one finished prompt** at the recommended or chosen rung; other rungs are written on request. “Choose for me” means draft the recommended rung.
- Recommend Safe on a first attempt or when one attempt remains; recommend Stretch when the user says they have room to iterate, and for short-drama coverage, where a reaction shot is part of the grammar rather than an extra.
- Never present Ambitious as broken; present the split as the better spend.
- State the evidence tier once: no official shot ceiling exists, the official examples use three, and the thresholds are this skill's heuristics.
- After a take review, move the user's rung, not the constants: see [retake-protocol](retake-protocol.md).

## Two original director examples

**Reassurance through a cut — proposed 10-second clip.** The audience should understand that someone has waited, without a speech explaining it. Shape: storyboard, two beats. Load: the bowl slid toward the chair must land (1); the cut is free. S = 10 ÷ 3 ≈ 3.3, Safe.

> Shot 1: locked close-up of two bowls at a kitchen table. A hand slides a folded towel from beneath the untouched bowl; the other bowl is already empty. A key turns off-screen. Shot 2: cut to a medium view from the doorway. The person at the table looks up, moves the untouched bowl toward the empty chair, and keeps their hand beside it. Hold on that invitation. Sound: key, chair leg against tile, quiet room tone.

**Product proof through comparison — proposed 6-second montage.** Demonstrate how a tool fits into a routine, without asking tiny generated text to sell it. Shape: storyboard, three beats, locked framings. Load: the bit seating in the hinge is contact that must land (1). S = 6 ÷ 4 = 1.5, Ambitious as briefed. The agent says so and offers the ladder: the same three beats at 8 seconds (S = 2.0, Stretch) or at 12 seconds (S = 3.0, Safe), or two beats at 6 seconds, the loose door and then the tightened door closing flush (S = 2.0, Stretch).

> Close on a loose cabinet hinge; the door drops as it opens. Cut to a side view of a compact screwdriver tightening the hinge, its bit already seated. Cut to the same opening angle: the door now swings level and closes flush. Keep the cabinet finish and hinge position consistent. Sound: hinge creak, brief motor pulse, soft latch click.

These are ungenerated teaching examples. Review action feasibility and references before spending credits; exact timings and small hardware details may require separate shots or post work. Offer a longer action shot if the tightening beat is unreadable, rather than silently increasing duration or generating more takes.

## Failure → next choice

| Observed result | Smallest useful revision |
|---|---|
| Unwanted continuous take | Name the cut inside the block and make the second composition distinct; try two shots before adding more. |
| Action skipped or compressed | Move down one rung: merge two beats or remove a secondary action, or offer more duration within the supported limits. |
| Cut interrupts the action | State the completed endpoint before the cut; use post editing if exact timing matters. |
| Look or state changes across cuts | Repeat the specific continuity anchors and check reference roles. |
| Dialogue is cut short | Count the line's load and leave room for the reaction; retain the user's words unless a rewrite is authorized. |
| Lines garbled or a shot dropped | The density warning applied: split into two generations rather than re-rolling the same count. |

## Sequence Boundary

Multi-shot grammar describes cuts inside one generation. Sequence-state planning describes multiple connected generations. Do not paste future clip prompts into the current multishot prompt. If a beat belongs to a later generation, mark it reserved and leave it out.

Multi-shot prompts identify cuts and endpoints. Continuous takes use phases and no hard cuts. Keep the selected contract consistent. For a continuous score across separately generated clips, plan audio assembly in post.

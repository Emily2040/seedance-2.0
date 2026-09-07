# Multi-Shot Grammar — direct cuts inside one generation

Multi-shot means several shots within one generated clip. It is not new to the 2.0 line: the [Seedance 1.0 paper](https://arxiv.org/abs/2506.09113) already describes native multi-shot generation. Seedance 2.0's [launch post](https://seed.bytedance.com/en/blog/seedance-2-0-official-launch) demonstrates multi-shot audio-video output. These are capability descriptions, not guarantees that each requested cut will land. Sources checked 2026-09-07.

## Choose the edit before choosing notation

| User's priority | Starting approach | Tradeoff |
|---|---|---|
| One continuous performance | Say “single continuous take”; describe phases and the final hold. | Less editorial control inside the take. |
| A reveal, reaction, or comparison | Describe two shots and the action that motivates the cut. | Each shot needs enough time for its essential beat. |
| Fast montage | Use brief, distinct images with explicit transitions and a total duration supported by the surface. | Less time for dialogue, detailed actions, and final holds. |
| Exact frame timing | Plan separate clips and edit them in post. | More assembly work; model-generated timing alone is insufficient. |

Use `Shot 1:` / `Shot 2:` when headings make the brief easier to read. Plain prose with “cut to” is also valid prompting: [Runway's official help](https://help.runwayml.com/hc/en-us/articles/50488490233363-Creating-with-Seedance-2-0) includes a multi-shot prose example without numbered headings. No cited source establishes a universal `Shot N` parser. Labels and timestamp ranges are teaching notation unless the active endpoint explicitly documents otherwise.

Chinese timelines such as `0–3秒…，3–6秒…` and English timing phrases can express pacing. Choose a coherent format in the user's language; do not require a different grammar merely because a surface is Chinese or Western. Requested timestamps remain intentions until the returned clip is reviewed.

## Allocate time without inventing limits

Start with one primary action per shot, a motivated camera choice (including locked framing), and the relevant sound. Roughly 4–6 seconds per shot can help plan a deliberate action/reaction beat; it is a **workflow heuristic**, not a minimum. A montage can be faster, while a spoken exchange may need more time.

Check the active model, operation, and surface for accepted duration values. Use `auto` only when that endpoint documents it, and keep any existing user setting. Do not infer an API enum from prose examples. There is no universal ten-second minimum or requirement to upgrade to Standard for multi-shot. If comparing tiers, show the cost/reliability tradeoff and obtain authorization for any additional paid test.

## Two original director examples

**Reassurance through a cut — proposed 10-second clip.** The audience should understand that someone has waited, without a speech explaining it.

> Shot 1, about four seconds: locked close-up of two bowls at a kitchen table. A hand slides a folded towel from beneath the untouched bowl; the other bowl is already empty. A key turns off-screen. Cut to Shot 2: medium view from the doorway. The person at the table looks up, moves the untouched bowl toward the empty chair, and keeps their hand beside it. Hold that invitation before cutting. Sound: key, chair leg against tile, quiet room tone.

**Product proof through comparison — proposed 6-second montage.** Demonstrate how a tool fits into a routine, without asking tiny generated text to sell it.

> Close on a loose cabinet hinge; the door drops as it opens. Cut to a side view of a compact screwdriver tightening the hinge, its bit already seated. Cut to the same opening angle: the door now swings level and closes flush. Keep the cabinet finish and hinge position consistent. Sound: hinge creak, brief motor pulse, soft latch click.

These are ungenerated teaching examples. Review action feasibility and references before spending credits; exact timings and small hardware details may require separate shots or post work. Offer a longer action shot if the tightening beat is unreadable, rather than silently increasing duration or generating more takes.

## Failure → next choice

| Observed result | Smallest useful revision |
|---|---|
| Unwanted continuous take | Name the cut and make the second composition distinct; try two shots before adding more. |
| Action skipped or compressed | Remove a secondary action, or offer more duration within the supported limits. |
| Cut interrupts the action | State the completed endpoint before the cut; use post editing if exact timing matters. |
| Look or state changes across cuts | Repeat the specific continuity anchors and check reference roles. |
| Dialogue is cut short | Measure the spoken line and leave room for the reaction; retain the user's words unless a rewrite is authorized. |

## Sequence Boundary

Multi-shot grammar describes cuts inside one generation. Sequence-state planning describes multiple connected generations. Do not paste future clip prompts into the current multishot prompt. If a beat belongs to a later generation, mark it reserved and leave it out.

Multi-shot prompts identify cuts and endpoints. Continuous takes use phases and no hard cuts. Keep the selected contract consistent. For a continuous score across separately generated clips, plan audio assembly in post.

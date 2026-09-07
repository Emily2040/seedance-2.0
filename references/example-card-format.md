# Teaching example cards

A teaching card explains a directing decision and how to assess it. It is not a generation receipt or a promise that the prompt works. Use cards when someone wants an example or a comparison; do not require this worksheet before an ordinary prompt request.

## Reading and writing a card

| Field | What belongs here |
|---|---|
| Evidence | Start with `Concept; not generated or inspected.` for an authored example. Never turn an intended benefit into an observed result. |
| Brief | The viewer's job and the user's actual constraints. Identify invented scene details as authored choices. |
| Choice | The selected approach, a materially different alternative, and the tradeoff. Preserve supplied and rejected direction. |
| Bindings | `None` for a self-contained T2V concept, or the exact reference tags, required assets, roles, exclusions, and whether they are available. |
| Settings | Intended mode, duration and framing assumptions. Verify the active surface before using operational settings; a planning duration is not a supported-limit claim. |
| Why this direction | What the decision is intended to make legible or expressive. Use a rationale, not “proven,” a success rate, or a savings claim. |
| Prompt / Conditional prompt | One fenced `text` block containing only generation prose. A prompt with missing reference assets is conditional, even if its syntax is copyable. |
| Check | What to inspect in the returned picture and sound, including the endpoint. Separate creative acceptance from technical file checks. |
| Fallback | A bounded revision, feasible post option, simpler shot, or stop. Do not invent more takes or change settings without authorization. |

Classify the scene through the [Director's Read](directors-read.md). Keep its internal fields, budget notes, alternatives and evidence labels outside the prompt block. Use [retake decisions](retake-protocol.md) after an actual result; follow [surface profiles](surface-prompt-profiles.md) before submitting any job. No card authorizes a generation or upload.

## Reference and evidence boundaries

Canonical tags in these authored examples are placeholders for future asset bindings, not proof that an image or clip exists. Bind the actual asset to the exact tag used by the interface; preserve a user's supplied spelling. Inspect whether it supplies the stated pose, motion, identity or sound. A mismatch means revising the card, not declaring the source suitable. Without the asset, offer a self-contained draft or leave the reference prompt conditional.

To report a rendered result, add the actual output locator, exact prompt and reference bindings, surface/model and settings, generation date or run identifier, and a review that names the criterion and relevant frames/timestamps or audio passages. Record failures and uncertainty. An output proves only that this take was produced; “verified” must name what was verified. Do not overwrite a concept label based on a mockup, imagined take, placeholder receipt, or deterministic document test. Existing [generation records](../data/generation-runs.example.jsonl) illustrate bookkeeping and are not evidence for these cards.

For examples by production mode, use [the mode index](examples-by-mode.md); for more scene patterns, use [prompt examples](prompt-examples.md). New `*-example-cards.md` pages use this format. The lightweight document tests check field separation, concept labels and declared tags; they cannot establish asset truth, creativity, exact timing or model obedience.

## Card: Open the paper fan

**Evidence:** Concept; not generated or inspected.

**Brief:** Show one plain paper fan opening so a viewer can follow its construction. The cream paper, red pivot and tabletop are authored details; no exact product is supplied.

**Choice:** Hold an overhead view for the full opening. A low side view would emphasize paper depth but hide the rib spacing; choose readability for this brief.

**Bindings:** None. This T2V concept depicts an invented unbranded object, not a supplied product.

**Settings:** T2V; plan a six-second clip in a horizontal frame. Duration and framing are creative assumptions; model, tier and resolution remain unselected.

**Why this direction:** The fixed viewpoint is intended to let the opening action, rib spacing and final shape carry the demonstration.

**Prompt:**

```text
Hold an overhead view of a closed cream paper fan on a blue tabletop, its red pivot near the bottom of frame. One hand holds the pivot while the other draws the outer rib around until the fan opens into a semicircle. Keep every rib visible and the tabletop still. Soft light from frame left shows the paper folds. Sound: paper unfolding and a light wooden tap at full opening. End with the fan open and both hands still.
```

**Check:** The pivot stays in place; ribs spread from it without multiplying or detaching; hands keep their roles; the last frame holds the open semicircle. Listen for the tap at the visible endpoint.

**Fallback:** If rib geometry fails, simplify the framing or use a real demonstration with permission. A tighter crop sacrifices the full construction view; do not hide that tradeoff or automatically spend another take.

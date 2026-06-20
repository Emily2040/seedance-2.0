# Multi-Shot Grammar — real cuts inside one generation

*Seedance 2.0's defining capability over 1.x: a single 10–15s call can contain 2–3 shots with genuine editorial cuts. Labels: [official] = ByteDance/fal docs · [field] = practitioner-reported. Last verified 2026-06-09.*

## The grammar [official]
Label every cut explicitly — `Shot 1:` / `Shot 2:` / `Shot 3:` — in plain prose. The labels are what give the model cut points; long unlabeled prompts tend to render as one continuous take. Per shot: **one primary action + one camera move**, plus its sound. Order inside each shot: subject + action → camera → sound.

## The budget [official]
Shots cost seconds. Plan ≈4–6s per shot: two shots want ~10s, three want 12–15s. Ask for four shots in 5s and the model compresses or skips beats. `duration: auto` lets the model size the clip to the prompt's complexity — a strong default for multi-shot; set an explicit duration only when the edit demands it.

## Requirements [official + field]
- **Standard tier [field].** Official fal docs give fast endpoints the same schema and multi-shot support, but field reports say fast tiers do not reliably honor multi-shot (or slow-motion or dolly moves) on the first try.
- **10–15s or `auto` [official].** Multi-shot below ~10s starves the beats.

## Timestamps: secondary on Western surfaces, primary on Chinese surfaces [official + field]
Prefer `Shot N:` labels as the structure — clear and portable across surfaces. fal's reference-to-video docs additionally accept timestamp pacing phrases ("At 5 seconds…", "Cut scene to…"); use them sparingly as *hints inside* a labeled shot, never as bracketed `[0-6s]` blocks replacing the labels.

Surface exception [field]: on Dreamina/Jimeng, Chinese community practice structures longer prompts (over ~8s) with a bracketed timeline as the primary skeleton — `【时间轴】0-3s: … / 3-6s: … / 6-10s: …` — each segment carrying its own 画面/镜头/音效 (frame, camera, sound). Match the convention of the active surface; do not mix both skeletons in one prompt.

## Dialogue & audio placement [official + field]
A spoken line goes inside the shot where the speaker is on-screen, written naturally in quotes; keep lines short. Name each shot's specific sounds — they anchor the audio pass. Audio is generated per call, not across calls: multi-block pieces get their unifying score in post.

## The single-take alternative [official]
For an unbroken take, say so: "single continuous take, no cuts" — otherwise a long action description may get cut up.

## Worked shapes
*Three-shot commercial (≈15s):* Shot 1: extreme close-up of condensation sliding down a glass bottle, ice clinking. Shot 2: the bottle rises from crushed ice, camera tilting up into a backlit halo. Shot 3: a hand grabs it against a sunset rooftop, the city humming below. *(Paraphrased from the official demo shape.)*

*Two-shot dialogue beat (≈10s):* Shot 1: close on the detective under a flickering platform light, rain on his shoulders — he says quietly, "You were never on that train." Shot 2: cut to the woman's face as the train doors close behind her, a half-smile; the departure chime swallows the silence.

## Failure → fix [field]
| Symptom | Fix |
|---|---|
| Renders as one continuous take | clearer `Shot N:` labels · reduce to two shots · Standard tier |
| A shot's action skipped/compressed | fewer shots · raise duration / `auto` · one action per shot |
| Cut lands mid-action | end each shot's sentence on the completed beat; let the next shot open the new one |
| Atmosphere breaks between shots | declare the persisting effect once for the whole piece: "thin mist throughout, every shot" (全程薄雾) |

## Sequence Boundary

Multi-shot grammar describes cuts inside one generation. Sequence-state planning describes multiple connected generations. Do not paste future clip prompts into the current multishot prompt. If a beat belongs to a later generation, mark it reserved and leave it out.

Dense multishot prompts use shot labels and endpoints. Continuous takes use phases and no hard cuts. Do not mix those contracts.

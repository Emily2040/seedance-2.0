# Sync-Budget Measurement Protocol

Two cells in the dialogue-capacity table of [audio-guide](audio-guide.md) read "not separately measured": Japanese and Korean. That wording is deliberate — nobody has measured them, and this repository does not print numbers nobody measured. This protocol is the missing half of that honesty: the exact procedure that turns a few real dialogue takes on one surface into numbers those cells can carry.

Anyone with access to a Seedance 2.0 surface that voices dialogue can run it. Total cost is roughly 24-40 takes per language.

## What is being measured

The **reliable-sync budget**: the longest line, counted in the language's own unit (morae for Japanese, syllables for Korean, characters for Mandarin), that survives generation with clean lip-sync and un-garbled speech most of the time. Not the acoustic budget — a longer line often *fits*; the question is what stays reliable.

## Fixed conditions (do not vary these between takes)

The shot must be the one the Dialogue rules in [audio-guide](audio-guide.md) already prescribe, so the measurement isolates line length instead of confounding it with camera:

- One speaker, locked medium close-up, eye level, no reframing.
- No head turn, no walking, hands still, plain expression.
- No music, no competing SFX: `Sound: quiet room tone` and the quoted line only.
- Same surface, same duration setting, same resolution for every take in a ladder.
- Speech level / register held constant within a ladder (해요체 for Korean, です・ます体 for Japanese) — the register sections in [vocab/ko](vocab/ko.md) and [vocab/ja](vocab/ja.md) exist precisely so this variable is controlled.
- Lip-sync enabled where the surface exposes a toggle (Jimeng/即梦 ships it off).

## The ladders

Every count below is script-verified, not eyeballed. Climb from the shortest rung; run 4 takes per rung; stop one rung after the first rung that fails the acceptance rule.

**Japanese (morae, です・ます体):**

| Morae | Line |
|---|---|
| 4 | 分かった *(plain form, calibration rung only)* |
| 6 | 分かりました |
| 8 | かしこまりました |
| 10 | ありがとうございます |
| 14 | 五時に駅の前で会いましょう |
| 20 | もう一度最初から説明してください |

**Korean (syllables, 해요체 except where marked):**

| Syllables | Line |
|---|---|
| 3 | 고마워 *(반말, calibration rung only)* |
| 4 | 고마워요 |
| 5 | 감사합니다 *(합니다체 — register-cost pair with the rung above)* |
| 7 | 지금 시작할게요 |
| 10 | 끝나면 바로 전화할게요 |
| 16 | 내일 아침 아홉 시에 회의실에서 만나요 |

**Mandarin control ladder (characters).** Run this first on the same surface and session. Mandarin is the strongest documented tier; if the control ladder fails early, the surface or settings are the problem, and the ja/ko numbers from that session are not valid measurements.

| Characters | Line |
|---|---|
| 3 | 知道了 |
| 5 | 我马上就到 |
| 10 | 我们五点在车站门口见 |
| 17 | 把东西放下然后跟我来我们时间不多了 |

## Scoring a take

Score each take on three binary defects — a take is **clean** only when all three are absent:

1. **Desync** — visible mismatch between mouth articulation and the audio at any point in the line.
2. **Garble** — scrambled, swallowed, duplicated, or wrong-language words (the 语音错乱 class of failure).
3. **Truncation or mix collapse** — the line is cut off, or speech ducks under compression artifacts before it ends.

A **rung passes** when at least 3 of its 4 takes are clean. The language's reliable-sync budget is the highest passing rung, reported as a range against the next failing rung (for example "clean through 10, degrading by 14 → report ~10-14").

## Recording takes

Record every take — including the failures; the failures are the data — as one line each in a JSONL file shaped by `schemas/generation-run.schema.json` (see `data/generation-runs.example.jsonl` for the shape). Use `result_status: "reviewed"`, set `is_synthetic_fixture: false`, and put the rung and the three defect verdicts in the prompt-adjacent notes your workflow keeps. Do not commit raw generation ledgers to this repository; commit only the summarized findings below.

## Writing the result back

When a ladder is complete:

1. Update the Japanese and/or Korean row of the dialogue-capacity table in [audio-guide](audio-guide.md): replace "not separately measured" with the measured range, the unit, the surface, and the date — e.g. `~10-14 morae on <surface>, 2026-XX [field]`.
2. Keep the claim label `[field]` — four takes per rung on one surface is field observation, not a guarantee, and the note column should still say "test per surface".
3. Record the session in the [source registry](source-registry.md) per its methodology, so the freshness check knows when the number ages out.
4. If the measured number contradicts the current tier ordering (for example Korean beats English), do not resolve it silently: flag it in the table note. Surprising results are the ones worth keeping visible.

One session on one surface fills the cell for that surface only. A second surface gets its own measurement, not an inherited number.

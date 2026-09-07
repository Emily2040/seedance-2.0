# Dialogue Calibration Protocol

Use this for an **optional, bounded pilot** on the active surface. It does not estimate a universal language limit. This repository has no validated per-language dialogue ceiling; [audio-guide](audio-guide.md) distinguishes published benchmark evidence from unmeasured workflow suggestions.

## Agree on the question and budget

Choose one question: for example, whether the user's exact line works in a stable close-up, or whether a supported audio reference improves delivery. Preserve language, script, register, and speaker identity. Do not substitute Mandarin as a supposedly stronger control language.

Before any paid call, establish the model/operation, maximum takes, maximum spend, and stop condition using the user's existing authorization. If those are missing, prepare the test and ask only for the missing authorization. A document saying “run four takes” is not authorization to spend. If prices cannot be verified, do not promise a cost or start a spending loop.

Start with the smallest test that could change the production decision. Reuse reviewed existing takes when their conditions match. Stop when the decision is made, the budget is exhausted, or the user stops the test; do not automatically finish a ladder.

## Keep a comparison interpretable

- Use the same surface, exact model/tier, operation, duration, resolution, reference roles, and audio settings across compared conditions.
- Hold speaker, framing, head movement, background sound, and performance direction constant unless that is the variable being tested.
- Use the actual approved line. Record its intended spoken duration with pauses; optional word/mora/syllable counts are descriptive only.
- If testing line length, use several reviewed lines per duration band with the same intended register. Different lines also change phonetics and meaning, so a length effect remains tentative.
- For a two-condition comparison, alternate conditions or predeclare an order; record seeds if exposed. A seed does not ensure equivalent output across providers or model versions.
- Check the documented audio control state; do not assume a Jimeng toggle or default. Do not upload voice material without authorization for that use.

## Score what actually happened

Inspect the returned clip and listen to the audio. A speaker or qualified reviewer of the target language checks the exact words, pronunciation, register, and intended emotion. Without that review, mark speech quality unreviewed; automated transcription alone cannot certify natural delivery.

Record these separately for every take, including failures:

| Dimension | What to record |
|---|---|
| Words and speaker | Omitted, changed, duplicated, wrong-language, or misassigned words. |
| Performance | Whether pronunciation, accent, register, pace, and emotion fit the brief; reviewer status. |
| Visible sync | Noticeable mismatch with mouth movement; timestamp examples and review method. |
| Completion and mix | Cut-off line, missing reaction time, masked speech, or artifacts. |
| Production decision | Accept, revise one variable, use post work, or stop. |

Define “acceptable for this shot” before looking at the results. A 3/4 pass count is **three acceptable takes out of four under these conditions**; it does not establish a reliable maximum, a language ranking, or a 75% future success probability. Selecting the best rung from many attempts also biases the result. Report all tried conditions and avoid presenting an exploratory pilot as confirmation.

## Keep evidence and claims separate

Record takes in a private ledger using `schemas/generation-run.schema.json` and `data/generation-runs.example.jsonl`. Use `result_status: "reviewed"` only after review, and `is_synthetic_fixture: false` only for real generations. Keep calibration condition, exact line, reviewer status, defects, and stop reason in linked local notes; do not invent schema fields. Do not commit raw media, personal voice material, credentials, or unsanitized generation ledgers.

A shareable result should identify date, surface, model/tier, operation, settings, language/register, line duration, sample counts, review method, observed defects, and limitations. Label it `field-observed`. Leave the general audio guide's capacity statement unchanged unless broader reproducible evidence supports a specifically scoped revision. Replication uses a separately authorized budget; this protocol does not schedule or trigger more calls.

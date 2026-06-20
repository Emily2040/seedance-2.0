# Model Mechanics — how the generator thinks

*A working mental model of why this repo's rules work, so an agent can derive correct guidance for cases no rule covers. Built from public machine-learning knowledge and the public model card; Seedance's exact internals are not published. Evidence label: `internal` reasoning — a thinking tool, never architecture documentation or a platform claim.*

## The eight mechanisms

### 1. Attention is a budget

Every word in the prompt competes for a finite amount of conditioning influence. Words that name something visible spend the budget on pixels; words that name an evaluation ("stunning") spend it on nothing. Earlier clauses tend to win more influence.

**Consequences:** word order is a priority ranking · slop is not just ugly, it is expensive · short dense prompts beat long prose. **Explains:** the anti-slop system, the allocation model, the character-budget discipline, "put subject and action first."

### 2. Generation pulls toward the familiar

The model produces samples near its training distribution. Combinations it has seen millions of times (golden hour + warm rim light) are cheap and stable; rare combinations fight the prior and wobble.

**Consequences:** name dense visual clusters (film noir, cel animation, phone footage), not judgments (beautiful) · expect instability whenever the request is statistically rare, and stage rare ideas as familiar pieces · style flicker between shots is the sampler hopping between nearby clusters — repeat the exact anchor phrase to hold it. **Explains:** style-safe descriptors, the medium-line repetition rule in 2D work, the source-look lock.

### 3. There is no NOT

Text conditioning moves probability toward every concept it mentions. Negation is weak grammar wrapped around a strong activation: "no blood" still summons the concept.

**Consequences:** describe what IS there; exclude compositionally · reserve literal negation for the constraint slot platforms parse (`no on-screen text, no watermark`). **Explains:** negation slop, "negation summons" in the capability map.

### 4. Time is a trajectory prior

The model strongly prefers motion that looks like real footage: smooth, momentum-carrying, cause-and-effect. A described cause lets the model compute plausible consequences; a list of disconnected micro-instructions has no trajectory to ride.

**Consequences:** one physical cause with visible consequences beats five stage directions · unmotivated sudden changes get smoothed away or glitch · declared media change the prior — "hand-drawn 2D" legitimizes held frames that photoreal footage would treat as freezing. **Explains:** physics-forward prompting, the one-action discipline, burst-vs-held grammar in 2D.

### 5. Errors compound

Each frame is re-synthesized under the influence of its neighbors; tiny identity errors accumulate across a clip, and feeding outputs back as inputs amplifies them generation after generation.

**Consequences:** identity drifts with clip length and chained continuations — re-anchor with the ORIGINAL references, never with outputs · keep fragile anchors locked and clips short · expect the fifth chained generation to need a reset. **Explains:** the ~4–5-generation drift note, extension-degradation repair, preservation language.

### 6. References outrank text where they overlap

Image, video, and audio references are dense conditioning; a still image specifies more about appearance than a paragraph ever could. Text that re-describes a reference creates a second, slightly different instruction for the same pixels — and conflict reads as drift. Reference channels also bleed: a motion donor wants to bring its appearance along.

**Consequences:** prompt only what references cannot carry — change over time, camera, sound, constraints · always state what must NOT transfer. **Explains:** intent-vs-precision, role binding with exclusions, "prompt only what the image cannot show."

### 7. Detail capacity scales with screen area

A face occupying 2% of the frame gets roughly 2% of the spatial representation. Small regions cannot hold fine structure, and motion makes it worse.

**Consequences:** the hero subject earns its fidelity by being large in frame · distant faces, busy hands, small logos, and on-screen text degrade first · a detail that matters gets its own shot. **Explains:** tiny-detail design-arounds, close-up rationing, text-to-post.

### 8. Audio and video are generated together

Sound is not added afterward; it denoises jointly with the picture. Named sound events give the sampler synchronization targets, and lip-sync is a joint constraint across both streams — every extra head or camera motion tightens it.

**Consequences:** name each shot's specific sounds — they anchor timing · audio can act as the clock of the edit · dialogue wants a stable face and a short line because the model is solving picture and phonemes simultaneously. **Explains:** audio-as-clock, sound-per-shot in multi-shot grammar, locked framing for dialogue.

## Deriving guidance for novel cases

When no rule covers the request: (1) ask which mechanism dominates; (2) ask what that mechanism predicts; (3) choose the lever that works with the mechanism instead of against it.

**Worked example — "the mirror reflection should move differently from the subject":** mechanism 2 says this is distribution-rare (training mirrors agree with their subjects), and mechanism 4 says two conflicting trajectories in one region fight the prior. Prediction: wobble, merging, or the reflection syncing back. Levers: stage it as two shots (subject, then mirror as its own subject), or shoot the mirror as the only subject in frame, or accept a brief 2–3s effect window where instability reads as intended. No rule in the repo states this; the mechanics derive it.

## Mechanism-indexed diagnosis

Sequence-state failures usually come from compounding error and broken trajectory: a later prompt starts from the planned state instead of the observed state, or repeats a completed action because the project did not log it. The repair is not stronger adjectives; it is a better state handoff.

| Symptom | Dominant mechanism | Lever |
|---|---|---|
| Output generic despite long prompt | 1 — attention diluted | cut slop, reorder priorities first |
| Style or look flickers | 2 — cluster hopping | repeat the exact anchor phrase every shot |
| Excluded thing appears | 3 — negation summoned it | describe the positive replacement |
| Action skipped or mushy | 4 — no trajectory to ride | one cause, visible consequences, an endpoint |
| Identity decays over time | 5 — compounding error | shorter clip, original-reference re-anchor |
| Reference fights the prompt | 6 — conflicting conditioning | delete re-description, state non-transfer |
| Small detail breaks | 7 — capacity starvation | enlarge it in frame or give it its own shot |
| Lips or sound desync | 8 — joint constraint overloaded | lock the face, shorten the line, name the sound |

---
name: seedance-20
description: "This skill should be used when creating, improving, or troubleshooting Seedance 2.0 video on any surface - Dreamina, Jimeng, CapCut, Doubao, Volcengine/Ark, BytePlus, Runway's Seedance route, fal, or third-party provider/router surfaces such as EvoLink, OpenRouter, Kie.ai, PiAPI, LaoZhang, Runware, ModelsLab, AI/ML API, MuAPI, SeeGen, and Segmind - including text/image/video/reference-to-video prompts, first/last frame, dialogue, lip-sync and audio, IP-safe rewrites, API, pricing and model-ID questions, and zh/ja/ko/es/ru prompt work. Not for non-Seedance models (Sora, Veo, Kling, Runway's own Gen models) or image-only prompting."
license: MIT
user-invocable: true
tags: [seedance]
metadata:
  version: "6.7.0"
---

# seedance-20

Seedance 2.0 operating loop for agent-directed video work. Use this root skill to route, check facts, protect references, and keep prompts compact before loading specialized sub-skills.

Every active runtime route in this package is an ordinary relative Markdown link resolved from the Markdown file that contains it; clients without private skill/reference aliases can open the linked file directly. Static validation proves that each link stays inside the installed skill and reaches the exact-cased file (and heading, when a fragment is present). It does **not** prove that a host auto-loads or invokes the target: clients must follow the link or provide their own native routing.

## Soul

This skill exists so that a person who arrives with a feeling leaves with a film. Three principles govern everything below:

1. **Hear the intent behind the words.** Users describe outcomes ("make it feel like home"), not parameters. Every gate and sub-skill translates feeling into craft; none of them may hand the translation work back to the user.
2. **Keep the story alive.** Hold a story state across the conversation: subject, mode, look, references, decided constraints, and what failed before. Every skill reads it before asking anything and updates it after acting. A user should never have to repeat a decision, and a new request inherits the world already built.
3. **Evolve with the user.** Speak plainly to a beginner and in director language to a professional - and notice when the same user grows from one into the other across a project. The register adapts; the standards never do.

## Fast Lane

Most requests are one short clip from someone who just wants to see their idea. Do not run the full gate loop on them. Take the fast path when the request is a single standalone clip, from a non-expert, with no IP/likeness/brand/real-person or safety flag and no platform-fact question (API, pricing, model ID, limits, region):

1. Go straight to [skills/seedance-interview-short/SKILL.md](skills/seedance-interview-short/SKILL.md) - or write the brief immediately if the idea is already clear - then [skills/seedance-prompt-short/SKILL.md](skills/seedance-prompt-short/SKILL.md).
2. Load the [Director's Read](references/directors-read.md) before writing the brief. Narrative, story, and performance ideas complete its ten-field read before prompt compilation; utility, product-only, and abstract ideas record its two-line non-narrative refusal instead. Then apply one visible beat, one motivated camera move, one motivated light source, sound intent, and the directing coherence rule. Load the [directing engine](references/directing-engine.md), [capability map](references/capability-map.md), [allocation model](references/allocation-model.md), and the source or professional gates only when the shot needs their deeper machinery.
3. Treat it as one clip: do not ask sequence or continuation questions yet. Raise "should this be a series, part two, or longer" only after the first draft, or when the user says continue, extend, next part, or longer.
4. Keep the single-clip prompt compact (about 40-110 words) unless the active surface is a verified stricter API, and keep director language (blocking, directorial voice, shot contracts) inside the internal brief - speak to the user in plain words.

Leave the fast lane the instant the request earns a gate: IP/likeness/brand/safety risk goes to the safety gate (step 9); a platform-fact question loads the source gate; a film, client, or delivery request loads the professional gate; a long story, connected clips, or continuation goes to the Sequence Gate. When in doubt about safety, leave the fast lane. The Operating Loop below is the full procedure - the fast lane is the default for the common case, and every gate it skips stays one signal away.

## Director's Read Gate

Before any route drafts, compresses, or compiles a prompt, load the [Director's Read](references/directors-read.md) and classify the brief. For every narrative, story, or performance brief, complete the canonical `dramatic function` through `stock solution refused` record; this includes silent clips, fast single clips, performer-led product work, sequences, and continuations. For non-narrative utility, packshot, functional product, abstract, VFX, or ambient work with no requested agency or performance, do not fabricate drama: record only the concrete utility intent and the explicit refusal of invented want, power, conflict, or subtext.

The read is an internal brief and handoff object, never final generation prose. Translate it into visible or audible carriers - blocking, eyeline, gesture, prop use, spatial change, camera endpoint, motivated light, dialogue contradiction, silence, or sound cue. Narrative prompts must visibly preserve the turn, one suppressed behavior, one non-transferable detail, and the replacement for the genre's easiest stock solution. No fast path, short path, compression path, or agent handoff may replace this record with remembered craft or generic judgment.

## Operating Loop

1. Intake: identify the user's goal, production phase, target surface, mode, duration, aspect ratio, references, audio needs, deliverables, and safety/IP risks. If intake surfaces a clear safety, IP, likeness, or evasion risk, jump straight to the safety gate (step 9) before any planning.

   Establish what this client can actually inspect before describing any attachment. Hosts differ: some read images, fewer read video, fewer still read audio. **Never state or imply that you viewed, watched, heard, measured, verified, or tested something you did not.** When a reference or a returned take cannot be inspected, say so plainly, work from the user's description, mark those details as user-reported rather than observed, and ask for a short description only when the missing detail actually blocks routing. This matters most where the repository's own workflows assume observation: `observed end state` in continuation, take triage in [references/retake-protocol.md](references/retake-protocol.md), and any reference role inferred from an attachment. An invented observation corrupts sequence canon, and every later clip inherits it.
2. Source gate: before platform claims, load [references/api-status.md](references/api-status.md) and [references/source-registry.md](references/source-registry.md). For Runway, Volcengine, fal, provider/router, or China-facing surface specifics, also load [references/platform-surface-matrix.md](references/platform-surface-matrix.md).

   **This skill is for Seedance 2.0.** A newer line exists and is out of scope; a user may be on it without saying so. Every duration, reference ceiling, resolution, and model ID here is a 2.0 value - never restate one for another line. Craft still applies (direction, shot contracts, reference roles, continuity, anti-slop); the numbers do not. When the line is unknown, write the prompt and withhold the number, exactly as for an unknown surface operation.
3. Professional gate: if the user asks for film, ad, campaign, client, delivery, localization, color, sound, subtitle, post, QC, or multi-shot work, load [references/pro-filmmaking-standards.md](references/pro-filmmaking-standards.md) before drafting.
4. Sequence Gate: classify the request as `standalone_clip` or `sequence_project` before the Mode Gate. Use `sequence_project` for long stories, connected clips, continuation/extend/next-part requests, dense action/dialogue scenes, campaigns, or any idea whose beats cannot clearly fit inside one verified active-surface generation. For sequence work, load [skills/seedance-sequence/SKILL.md](skills/seedance-sequence/SKILL.md), [references/sequence-project-state.md](references/sequence-project-state.md), [references/continuation-handoff.md](references/continuation-handoff.md), and [references/prompt-compiler.md](references/prompt-compiler.md); for continuation, repair-tail, or re-anchor requests, also load [skills/seedance-continuation/SKILL.md](skills/seedance-continuation/SKILL.md).
5. Mode gate: choose T2V, I2V, V2V, R2V, FLF2V, edit, native extend when verified for that surface, or troubleshoot before writing prose.

   Mode availability is surface-specific: edit and extend exist on Dreamina and Ark routes; fal has no dedicated extend endpoint - to continue a clip on fal, prefer reference-to-video with the previous clip as a video reference (keeps motion and audio context), and chain image-to-video from its last frame as the fallback. Provider/router surfaces can rename the same job type, hide fields, or expose only selected modes; recheck their current docs before implementation.

   Availability is per operation, not per provider. Never infer an endpoint, entitlement, request field, duration ceiling, or fallback from a provider's name or from a sibling operation on the same surface. When the exact surface operation is unknown, disabled, or undocumented, withhold the platform claim, not the work: say which part is unverified, give the choice in surface-conditional terms, and keep planning on the conservative generic profile in [references/surface-prompt-profiles.md](references/surface-prompt-profiles.md). An unknown operation blocks asserting that a feature exists; it never blocks writing the prompt.

6. Capability check: when planning any shot, mode, or budget, load [references/capability-map.md](references/capability-map.md) to design into model strengths and around known limits, and [references/allocation-model.md](references/allocation-model.md) to decide where the prompt spends its fidelity budget before drafting.
7. Reference authority: assign every asset one primary role - identity, first frame, last frame, product, environment, motion, camera, timing, audio, or style - and state what must not transfer. Then resolve authority per dimension: for each target and each controlled dimension, name exactly one winning asset or mark that dimension not applicable. One asset may own several dimensions; no dimension may have two owners. Drop any asset that ends up owning nothing, and name the assets explicitly excluded from each target. Never infer authority from media type, upload order, filename, or the order the user happened to mention things. Load [references/reference-workflow.md](references/reference-workflow.md) and [references/reference-transfer-contract.md](references/reference-transfer-contract.md); before any reference token reaches prompt prose, load [references/surface-prompt-profiles.md](references/surface-prompt-profiles.md), because binding syntax is surface-specific and there is no universal tag.
8. Multilingual gate: if the prompt uses Chinese, Russian, Japanese, Korean, Spanish, or code-mixed wording, load [references/multilingual-community-examples.md](references/multilingual-community-examples.md) and carry every reference binding through byte-for-byte - never translate, transliterate, recase, respace, or renumber one, in any language. For Chinese, Japanese, or Korean example-driven requests, route to [skills/seedance-examples-zh/SKILL.md](skills/seedance-examples-zh/SKILL.md), [skills/seedance-examples-ja/SKILL.md](skills/seedance-examples-ja/SKILL.md), or [skills/seedance-examples-ko/SKILL.md](skills/seedance-examples-ko/SKILL.md). Before making language-mastery or cultural-fit claims, load [references/multilingual-native-review.md](references/multilingual-native-review.md); automated checks and model judges cannot decide those questions or who wrote the material.
9. Safety gate: route IP, likeness, voice, brand, real-person, graphic, or evasion-like wording through [skills/seedance-copyright/SKILL.md](skills/seedance-copyright/SKILL.md) or [skills/seedance-filter/SKILL.md](skills/seedance-filter/SKILL.md).
10. Direction: run the mandatory [Director's Read](references/directors-read.md) gate before drafting. For a narrative lane, derive one intention from the completed read and make camera, lens, light, blocking, performance, and sound serve it instead of picking a "cinematic look". For a non-narrative lane, serve the utility intent without inventing character drama. Load the [directing engine](references/directing-engine.md) when scenes need distinct treatment, one directorial voice must hold across many clips, or the right setup is genuinely unclear.
11. Prompt build: route to [skills/seedance-interview/SKILL.md](skills/seedance-interview/SKILL.md), [skills/seedance-prompt/SKILL.md](skills/seedance-prompt/SKILL.md), [skills/seedance-prompt-short/SKILL.md](skills/seedance-prompt-short/SKILL.md), [skills/seedance-sequence/SKILL.md](skills/seedance-sequence/SKILL.md), [skills/seedance-continuation/SKILL.md](skills/seedance-continuation/SKILL.md), or a domain skill for camera, motion, lighting, audio, characters, VFX, style, recipes, or pipeline.
12. Quality pass: run anti-slop and the directing coherence test, then check the correct Director's Read lane, one visible beat, one primary camera move, physically motivated light, sound intent, continuity anchors, constraints, delivery caveats, and source-date caveats. Narrative prompts must carry the turn, suppressed behavior, and non-transferable detail without leaking internal labels; non-narrative prompts must remain free of invented psychology.

    For interaction-heavy or fragile shots, write the visible chain in order - initial state, trigger, decisive change, response, follow-through, local endpoint - and name which of those the camera actually covers. Keep subject, prop, camera, and environmental motion under separate owners: a subject can reach its endpoint while rain keeps falling, a fan keeps turning, or the camera stays open for a handoff. Treat the chain as authored planning and review criteria; it describes what the shot should show, and is never evidence about the model's internals or a claim of physical accuracy.
13. Repair loop: when a take returns, triage it with [references/retake-protocol.md](references/retake-protocol.md) (keep / fix in post / edit / re-roll / rewrite, one variable per retake, inside an attempt budget); if it fails outright, diagnose root cause before adding adjectives via [skills/seedance-troubleshoot/SKILL.md](skills/seedance-troubleshoot/SKILL.md).

## Authority Order

The gates above will contradict each other. When they do, resolve in this order, highest first. A lower rule never silently overrides a higher one; when one is sacrificed, say which and why.

1. **Safety, rights, consent, platform policy.** Never traded away, never worked around.
2. **Verified limits of the active surface operation.** A request the surface rejects is not a prompt.
3. **The user's explicit must-haves.** Their stated non-negotiables outrank every default below.
4. **Reference contracts** — what each asset must supply, preserve, and never transfer.
5. **Continuity** — identity, space, time, prop ownership, audio state.
6. **Physical causality and action legibility.** A beat the viewer cannot read has not happened.
7. **Camera and editorial logic.**
8. **Style, palette, atmosphere, decorative detail.**
9. **This skill's own defaults.** The first thing to give up, not the last.

**Which tier a constraint sits in is decided by what it controls, not by who asked for it.** One requirement often touches several tiers at once: "`@Video1` must supply this camera path" is a user must-have, a reference contract, and camera logic simultaneously. Classify it by the dimension it governs — camera, tier 7 — so that if the borrowed path hides the contact the shot exists to show, legibility at tier 6 still wins. Classifying by origin instead would collapse every user sentence into tier 3 and the order would decide nothing.

Being a user requirement does something different, and narrower: **it forbids dropping the constraint quietly.** When a user's request loses to a higher tier, say what you changed and why — "the borrowed camera path hid the moment of contact, so the crane is shallower; the timing is unchanged." The user can then lift it deliberately by naming the trade ("keep that path even if the action reads less clearly"), which moves it to tier 3 as a genuine non-negotiable. An unstated preference is not that.

Within one tier, prefer the constraint that is verified over the one that is inferred, and the one the user stated over the one this skill assumed. If they are still tied, ask rather than pick.

The common failures are inversions: style wording that quietly breaks an identity lock, a camera move that outranks the action it exists to reveal, or a repo default overriding something the user actually asked for.

## Sequence Gate

For a sequence project, do not write Clip 01 until these are known: story objective, final story outcome, ordered major beats grouped into scenes, active surface or conservative surface assumption, clip budget, current clip narrative job and felt intent, and current clip completed endpoint.

Do not write a continuation prompt until the previous accepted clip or its actual final frame has been reviewed and its observed end state recorded.

Sequence invariants:

- every sequence prompt has `project_id` and `clip_id` lineage;
- accepted observed state overrides planned state;
- rejected footage is excluded from canon and cannot become a continuation source;
- future prompts remain provisional until the preceding accepted take is reviewed;
- exact reference tags survive every clip unchanged;
- seamless continuation stays inside a scene; a scene boundary opens from canonical references and resets `extension_depth`;
- completed beats cannot replay and reserved future beats cannot leak early;
- continuity state must be updated after each accepted take;
- final Seedance prompts remain natural language unless the user explicitly asks for structured output.

## Load Map

| Situation | Load |
|---|---|
| Any brief before prompt drafting or compilation; mandatory narrative read or non-narrative refusal | [references/directors-read.md](references/directors-read.md) |
| Vague idea or missing brief | [skills/seedance-interview/SKILL.md](skills/seedance-interview/SKILL.md) or [skills/seedance-interview-short/SKILL.md](skills/seedance-interview-short/SKILL.md) |
| Long story, connected clips, campaign sequence, dense action/dialogue scene, or a prompt that needs several generations | [skills/seedance-sequence/SKILL.md](skills/seedance-sequence/SKILL.md), [references/sequence-project-state.md](references/sequence-project-state.md), [references/prompt-compiler.md](references/prompt-compiler.md) |
| Continue, extend, next part, repair tail, bridge known states, or re-anchor drift from accepted footage | [skills/seedance-continuation/SKILL.md](skills/seedance-continuation/SKILL.md), [references/continuation-handoff.md](references/continuation-handoff.md), [references/continuity-qc.md](references/continuity-qc.md) |
| Fragile contact, continuing or cyclic motion, owner-specific endpoints, or motion handoff between clips | [skills/seedance-motion/SKILL.md](skills/seedance-motion/SKILL.md), [references/model-mechanics.md](references/model-mechanics.md), [references/continuation-handoff.md](references/continuation-handoff.md), [references/sequence-project-state.md](references/sequence-project-state.md) |
| Review a generated take and update canon before the next prompt | [references/retake-protocol.md](references/retake-protocol.md), [references/sequence-project-state.md](references/sequence-project-state.md), [references/continuation-handoff.md](references/continuation-handoff.md) |
| First multi-clip project, or how the sequence loop actually runs end to end | [references/sequence-worked-trace.md](references/sequence-worked-trace.md) |
| Dense animation storyboard or multi-shot prompt | [references/dense-storyboard-mode.md](references/dense-storyboard-mode.md), [references/multishot-grammar.md](references/multishot-grammar.md), [references/2d-anime-grammar.md](references/2d-anime-grammar.md) |
| Production prompt | [skills/seedance-prompt/SKILL.md](skills/seedance-prompt/SKILL.md), [references/quick-ref.md](references/quick-ref.md), [references/prompt-examples.md](references/prompt-examples.md) |
| Planning any shot, mode, or budget | [references/capability-map.md](references/capability-map.md) |
| Where the prompt spends fidelity: identity vs motion vs scene density | [references/allocation-model.md](references/allocation-model.md), [references/intent-vs-precision.md](references/intent-vs-precision.md) |
| Multi-shot prompt, cuts inside one clip, or shots-per-duration budget | [references/multishot-grammar.md](references/multishot-grammar.md) |
| 2D, anime, or cel-style motion | [references/2d-anime-grammar.md](references/2d-anime-grammar.md), [skills/seedance-style/SKILL.md](skills/seedance-style/SKILL.md) |
| Professional film, commercial, campaign, or delivery workflow | [references/pro-filmmaking-standards.md](references/pro-filmmaking-standards.md), [references/shot-list-continuity.md](references/shot-list-continuity.md), [references/delivery-qc.md](references/delivery-qc.md) |
| Compact prompt or Chinese compression | [skills/seedance-prompt-short/SKILL.md](skills/seedance-prompt-short/SKILL.md), [references/vocab/zh.md](references/vocab/zh.md) |
| Choosing the right camera, light, blocking, performance, and voice for a scene, keeping every choice motivated, or holding one directorial style across a long story | [references/directing-engine.md](references/directing-engine.md) |
| Camera, lens, blocking, shot contract | [skills/seedance-camera/SKILL.md](skills/seedance-camera/SKILL.md), [references/cinematography-shot-language.md](references/cinematography-shot-language.md) |
| Image reference / first frame | [references/i2v-guide.md](references/i2v-guide.md), [references/reference-workflow.md](references/reference-workflow.md) |
| First and last frame | [references/first-last-frame-guide.md](references/first-last-frame-guide.md) |
| Several references, conflicting transfer, donor leakage, or deciding what each asset controls | [references/reference-workflow.md](references/reference-workflow.md), [references/reference-transfer-contract.md](references/reference-transfer-contract.md), [references/surface-prompt-profiles.md](references/surface-prompt-profiles.md) |
| API, Runway, Volcengine, fal, provider/router surfaces, China-facing surfaces, workflow, pricing, model IDs | [skills/seedance-pipeline/SKILL.md](skills/seedance-pipeline/SKILL.md), [references/api-workflow.md](references/api-workflow.md), [references/model-name-map.md](references/model-name-map.md) |
| Color, ACES, HDR/SDR, aspect ratio, subtitles, audio post, or QC | [references/color-pipeline-aces.md](references/color-pipeline-aces.md), [references/aspect-ratio-delivery.md](references/aspect-ratio-delivery.md), [references/subtitles-localization.md](references/subtitles-localization.md), [references/audio-post-delivery.md](references/audio-post-delivery.md), [references/delivery-qc.md](references/delivery-qc.md) |
| Genre template, examples, or a worked directing example in a specific genre | [skills/seedance-recipes/SKILL.md](skills/seedance-recipes/SKILL.md), [references/examples-by-mode.md](references/examples-by-mode.md), [references/genre-guides.md](references/genre-guides.md), [references/directing-engine-genre-library.md](references/directing-engine-genre-library.md) |
| Chinese examples, safe Chinese rewrites, or language-quality review | [skills/seedance-examples-zh/SKILL.md](skills/seedance-examples-zh/SKILL.md), [skills/seedance-vocab-zh/SKILL.md](skills/seedance-vocab-zh/SKILL.md), [references/vocab/zh.md](references/vocab/zh.md), [references/multilingual-native-review.md](references/multilingual-native-review.md) |
| Japanese examples, safe Japanese rewrites, or language-quality review | [skills/seedance-examples-ja/SKILL.md](skills/seedance-examples-ja/SKILL.md), [skills/seedance-vocab-ja/SKILL.md](skills/seedance-vocab-ja/SKILL.md), [references/vocab/ja.md](references/vocab/ja.md), [references/multilingual-native-review.md](references/multilingual-native-review.md) |
| Korean examples, safe Korean rewrites, or language-quality review | [skills/seedance-examples-ko/SKILL.md](skills/seedance-examples-ko/SKILL.md), [skills/seedance-vocab-ko/SKILL.md](skills/seedance-vocab-ko/SKILL.md), [references/vocab/ko.md](references/vocab/ko.md), [references/multilingual-native-review.md](references/multilingual-native-review.md) |
| Russian/Spanish or mixed-language examples | [skills/seedance-vocab-ru/SKILL.md](skills/seedance-vocab-ru/SKILL.md), [skills/seedance-vocab-es/SKILL.md](skills/seedance-vocab-es/SKILL.md), [references/multilingual-community-examples.md](references/multilingual-community-examples.md) |
| Slop-heavy or filter-tripping English wording | [skills/seedance-vocab-en/SKILL.md](skills/seedance-vocab-en/SKILL.md), [skills/seedance-antislop/SKILL.md](skills/seedance-antislop/SKILL.md) |
| Bad result | [skills/seedance-troubleshoot/SKILL.md](skills/seedance-troubleshoot/SKILL.md) |
| A take came back: keep, fix in post, edit, re-roll, or rewrite | [references/retake-protocol.md](references/retake-protocol.md) |
| Why a rule works, or a novel case no rule covers | [references/model-mechanics.md](references/model-mechanics.md) |

Preserve reference tags exactly, keep prompts short, and never convert field-observed community tricks into official platform guarantees. For professional filmmaker requests, deliver the workflow object the role needs: shot list, shot contract, continuity ledger, prompt, post handoff, localization plan, or QC checklist.

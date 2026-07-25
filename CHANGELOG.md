# Changelog — seedance-20

All notable changes to this project are documented here.

Current active release: **6.6.0**. Older entries below are preserved as release history, not active version guidance.

## Unreleased

### Added

- Added **Script Variant (简繁)** to `vocab/zh`, and declared the file's own variant in its header: it is Simplified (zh-Hans) with mainland terminology, which was true but never stated. Separates prompt script from delivery script (mainland-trained surfaces make Simplified the safer prompt language; a 台灣/香港 deliverable still needs Traditional subtitles), warns that one-to-many character mappings make find-and-replace conversion wrong rather than merely foreign (头发 → 頭髮, not 頭發), and lists regional vocabulary differences that survive a correct script conversion (视频/影片, 屏幕/螢幕, 质量/品質). Three `Text` rows declare the delivery variant. `delivery-qc` now carries the variant in its Text preflight row and requires the `LANG` field of the naming pattern to distinguish `ZH-HANS` from `ZH-HANT`, since the variant is not recoverable from the video.

- Added **Speech Level (말투)** to `vocab/ko`: Korean has no neutral register, so an unstated level is a decision handed to the model rather than a decision avoided. Documents 합니다체 / 해요체 / 반말 with syllable costs for identical sentences (합니다체 runs roughly 1.5-2x 반말), when each applies, and why the pair of levels between two speakers encodes the relationship and must stay consistent across a sequence. Five `Audio` vocabulary rows declare the level in a prompt, and `audio-guide` now names the register as a syllable-budget trap where the reliable-sync budget is defined.

- Added an **Authority Order** to the root skill: nine tiers resolving what wins when two gates give opposite instructions, with defaults ranked last, same-tier tiebreaks, and the rule that a constraint is classified by the dimension it governs rather than by who asked for it.
- Added **Ending Profiles** to `cinematography-shot-language`: six named profiles (resolve, extension anchor, loop seam, hero hold, edit point, reveal or punch) chosen by what consumes the clip next, so an extension anchor stays directionally live and a loop seam is phase-matched to its opening.
- Added an **Inspection Honesty** rule to `agent-compatibility`, `continuation-handoff`, and `seedance-continuation`: media inspection is a client capability, not a property of this skill. A state the agent was told rather than saw is recorded as reported — `observation_confidence: low`, `requires_user_confirmation: true`, unverified categories in `uncertainties` — instead of entering project canon as fact.
- Added `scripts/schema_check.py`: executes every shipped JSON Schema against declared fixture instances in `validation/schema-instances.json`, rejects duplicate JSON keys, and requires each schema to carry at least one instance. Wired into CI and the release checklist.
- Added `scripts/build_hero.py`: generates `assets/hero-dark.svg` and `assets/hero-light.svg` from one geometry so the two themes cannot drift apart, with a `--check` drift gate in CI.
- Added `.github/workflows/source-freshness-review.yml`: a Monday schedule that classifies the registry clean, drifting, or stale and maintains a single tracking issue. The privileged job checks out nothing; the job that runs repository code is read-only.
- Added `tests/test_install_payload.py`: performs a real install and AST-parses every shipped `.py` for network imports and credential-shaped literals, with a sentinel test proving the scan actually detects a violation.
- Added `.gitattributes` so a Windows checkout cannot fail validation on line endings.

### Changed

- Split capability claims in `capability-map` into four separately-verified layers — model capability, surface access, request syntax, and returned adherence — because a single "supported" cell conflated things that fail for different reasons.
- Stopped the wall-clock freshness gate from failing unrelated pull requests. `source_registry_check.py` now warns past 14 days and errors past 30 only under the new `--enforce-freshness` flag, which the release checklist and the scheduled job pass. The drift check between two checked-in dates stays fatal, since it cannot be triggered by the calendar alone.
- Hardened the validation workflow: actions pinned to commit SHAs, `permissions: contents: read`, a cancel-in-progress concurrency group, and no committed bytecode.
- Excluded the live evaluator (`eval_run.py`, `eval-runs/`, `tests/`) from the installed skill payload, and made `SECURITY.md` describe it accurately rather than implying it was never shipped.
- Retired the viewfinder masthead for a call-sheet one; `frontend-design-system` now explicitly retires sprocket strips, viewfinder marks, crosshairs, timecode, record dots, aspect badges, and waveform ticks.
- Made `requirements-validation.lock` installable off the CI runner by covering CPython 3.11-3.13 on Linux, macOS, and Windows.
- Kept the conservative routing path open when the active surface is unknown: the agent withholds the platform claim rather than stopping the planning work.

### Fixed

- Native-level proofreading pass across all six languages. Chinese: 编钟余震 -> 余音 (aftershock -> lingering resonance), 湿地 (wetland) -> 潮湿地面/湿润地面/湿滑地面 for "wet ground" (3 files), the missed 三分之二 -> 四分之三 three-quarter angle in the community-examples file, 表面 -> 平台 (surface translationese), 轮廓 -> 剪影 (silhouette), 后退揭示镜头 -> 镜头后拉揭示空间, 宽幅远景 -> 远景定场镜头 (establishing shot), a missing 仅 to match its "only" gloss, and full-width quotes in two Chinese sentences. Japanese: the same fraction bug 三分の二 -> 四分の三, 主体 -> 被写体 (photographic subject), 実用照明 -> プラクティカルライト (practical light, 2 files), 開示 -> 種明かし（リビール） (cinematic reveal), two grammar repairs, 開いた動き -> 進行中の動き, 顔を向けて -> 振り向いて, 日本語入口 -> 日本語の入り口, だけで止めず -> だけにとどめず, 電気の弧 -> 電気アーク. Korean: 실용 조명 -> 프랙티컬 조명 (practical light, 4 files), 천천히 돌리 인 -> 느린 돌리 인, 머리 회전 -> 고개를 돌리지 않고, 중간 샷/중간 클로즈업 -> 미디엄 샷/미디엄 클로즈업, 주체 -> 피사체, a particle-spacing fix, 영화같은 -> 영화 같은, register fix 마세요 -> 마십시오, 멀리 -> 멀리서, 낮은 앵글 -> 로우 앵글, 틸앤오렌지 -> 틸 앤 오렌지, and one unstacked modifier. Spanish: bloqueo -> puesta en escena (film blocking, not blockage), caen en el pulso -> siguen el pulso. Russian: макро-крупный план -> макросъемка крупным планом, and one stray ё normalized to the file's е-style.

## [6.6.0] — 2026-07-04

### Added

- Added `scripts/extract_last_frame.py`: ffmpeg-based last/first-frame extraction from an accepted take, with `--emit-record` printing the observation skeleton (frame-readable vs frame-blind categories, aligned with the take-review schema) and a pure-Python `--self-test` wired into CI. The extracted frame doubles as the continuation image reference.
- Added the **Observation Fast Path** to `continuation-handoff` and `seedance-continuation`: when a final frame or clip is attached, the AGENT fills the observation record from the pixels and asks at most three targeted questions about what a still cannot show (open motion, camera movement phase, audio phase) - the user stops being the state sensor.
- Added a **State Lifecycle** to `sequence-project-state`: file conventions for persistent-workspace agents (`project-state.json` as machine truth, capsule regenerated from it, take log archived separately), compaction rules (completed scenes compress to one line, full detail only for the current scene plus previous accepted clip, superseded takes archive on scene close, capsule under ~40 lines), and `state_revision` bump rules.
- Added `references/sequence-worked-trace.md`: the prose end-to-end trace around the existing machine fixtures - plan with scenes and felt intents, compile, a real accepted deviation (two steps short), reconciliation, the unexpected-completed-beat case, the chain cap and scheduled re-anchor at the scene boundary, and session break/resume via capsule. Registered as a required reference with Load Map routes from the root skill and `seedance-sequence`.
- Added evals `observed_state_from_attached_frame` and `capsule_compaction_long_project` (126 total).

### Changed

- Bumped active metadata, README badges (59 references, 126 eval cases), eval/validator expectations, manifest, readiness, examples, and translated entries to v6.6.0.

## [6.5.0] — 2026-07-04

### Added

- Added **`felt_intent`** to the clip contract - one line naming what the viewer should feel or notice, the directing engine's intention made persistent in sequence state. This closes the "continuity-correct but affect-flat" failure: the compiler's compression priority previously protected tags, state, action, locks, and exclusions, so under a tight prompt budget the emotional intention was the first thing silently deleted.
- Compiler integration (`prompt-compiler.md`): felt intent has its own compile-order step and sits in compression priority directly after action/endpoint - above continuity locks - as **felt-intent carriers**: the specific light, performance, and sound clauses that make the viewer feel what the clip exists to make them feel. The intent itself never ships to Seedance as an abstract emotion word (anti-slop holds); its carriers ship as concrete visible choices.
- Added a **pre-generation intent echo** to `seedance-sequence` and `seedance-continuation` output contracts: one line - "this clip exists so the viewer feels X" - confirmed before generation spends money. `continuity-qc`'s boundary check now fails a successor prompt whose visible choices no longer serve its felt intent.
- Threaded `felt_intent` through the root Sequence Gate, `continuation-handoff` source gate, the continuation Required Input Gate, clip lineage fields, the Project State Capsule (NEXT CLIP INTENT), both JSON schemas (required, non-empty), `project_state_check.py` (presence plus non-empty-string validation for states and contracts, five negative-tested gates), and all example fixtures with clip-specific intent lines. Added eval `felt_intent_survives_compression`.

### Changed

- Bumped active metadata, README badges (124 eval cases), eval/validator expectations, manifest (patch scope refreshed - it still described v6.1.0), readiness, examples, and translated entries to v6.5.0.

## [6.4.0] — 2026-07-04

### Added

- Added a **scene layer** to the sequence architecture - the missing tier between story and clip for five-minute-scale work. A scene is the re-anchor unit: one location and time envelope whose clips may chain from each other's accepted footage. Seamless continuation is legal only inside a scene; a scene boundary is an intentional cut that opens from canonical references and resets `extension_depth` to 0. Scene cards carry `scene_id`, `arc_position` (clips inherit it), canonical `anchor_source`, `max_chain_depth` (default 2, hard ceiling 3, grounded in the model-mechanics drift note), an audio plan (ambience/SFX per clip, score unified in post), and `assigned_clip_ids`.
- Redefined `extension_depth` as consecutive output-sourced generations since the last canonical re-anchor, resetting at every canonical open - converting re-anchoring from reactive drift repair into scheduled routine. Exceeding the scene cap is now a hard validation failure with an actionable message.
- Added the **source-carries-state compiler rule** to `references/prompt-compiler.md`: when an accepted clip or final frame is attached as a reference, the source carries the state and the text carries only the delta (a video source carries static and dynamic state; a still frame cannot carry open motion vectors, camera phase, or audio phase, so those stay in prose). Opening-state prose that repeats an attached source is now deleted first under budget pressure.
- Extended the JSON schemas (`project-state` and `clip-contract`), `project_state_check.py`, all four example fixtures, the Project State Capsule (SCENE MAP / CURRENT SCENE), and the root sequence invariants for the scene layer. Added eval `scene_layer_caps_extension_chain`.
- Hardened the scene validator after adversarial review: `extension_depth` must be a non-negative integer (a string, float, negative, or boolean can no longer silently bypass the cap), booleans are rejected for `max_chain_depth`, scene `status`/`scene_index` are enum- and range-checked with duplicate-index detection, scene-clip membership is enforced bidirectionally (a clip's `scene_id` must be listed by exactly that one scene, no double assignment, no duplicate list entries), and a malformed `scenes` shape produces a clean validation error instead of a traceback. Fourteen negative probes verified.

### Changed

- `seedance-sequence` plans scenes before clips (Scene Architecture section, scene-first build process); `seedance-continuation` gained the Scene Boundary Rule; `continuation-handoff` and `sequence-project-state` carry the scene fields; `json-schema.md`, `agent-compatibility.md`, and `capability-map.md` enumerations aligned with the scene layer and scheduled re-anchoring.
- Bumped active metadata, README badges (123 eval cases), eval/validator expectations, manifest, readiness, examples, and translated entries to v6.4.0.

## [6.3.0] — 2026-06-29

### Added

- Folded deep audio-architecture research into `references/audio-guide.md`, `seedance-audio`, and the per-language `vocab/*.md`: a "how the audio actually works" reasoning model (joint audio-video generation, sound inferred from visuals, speech/articulation coupling, lip-sync sometimes off by default on some surfaces, probabilistic reliability, uneven per-language strength) - all labeled field-observed and surface-specific, never official.
- Added a field-observed per-language dialogue-capacity table (English ~16-20 reliable-sync words per ~15s, Russian ~10-15 and weak, Mandarin strongest, Japanese/Korean weaker and under-tested) plus the acoustic-budget-vs-reliable-sync-budget distinction and the "one short sentence ~= one breath" cross-language unit.
- Documented the voice-reference lip-sync path: on surfaces that accept a spoken-voice reference, an attached rights-cleared voice can drive lip-sync directly (the model syncs to it instead of synthesizing) - the most reliable field-reported path for non-English dialogue - correcting the prior "audio reference = tempo/mood only" framing. Treated as rights-sensitive and routed through copyright when unclear.
- Added the field-observed inline audio-tag dialogue pattern and the Jimeng lip-sync-default-off note, plus eval `audio_reference_lipsync_non_english`.

### Changed

- Bumped active metadata, README badges (122 eval cases), eval/validator expectations, manifest, readiness, examples, and translated entries to v6.3.0.

## [6.2.0] — 2026-06-28

### Added

- Added `scripts/eval_run.py`, a model-in-the-loop eval harness: it builds a responder context from the real skill content (root `SKILL.md`, the case's expected sub-skills, and any `state_fixture`), gets a response to each case prompt, then has a judge model score that response against the case's own assertions using `references/eval-rubric.md` (0-3 legacy / 0-4 sequence scales and the documented release thresholds). An offline `--self-test` wiring check runs in CI; a live scored pass is the quality gate that lives outside offline CI, recorded in `evals/eval-run-ledger.md`.
- Added six directing-engine eval cases (reveal-vs-goodbye distinct setup, pattern-break marks the turn, performance-as-gesture, subtext-through-contradiction, lighting-ratio-serves-emotion, refuses-unmotivated-technique) so the v6.1.0 flagship has proportional coverage.

### Changed

- De-templated all 47 sequence eval cases: each now carries a concrete scenario prompt and 2-4 case-specific assertions that name the behavior its id promises, replacing the placeholder "V6 check: ..." prompts and the identical three generic assertions. The structural fields (`forbidden_behaviors`, `expected_sequence_relation`, `critical`, ...) are preserved, so `sequence_eval_check` still holds.
- Split the 454-line directing engine for progressive-disclosure compliance: the 33-genre worked-example library moved to `references/directing-engine-genre-library.md`, loaded on demand via the genre/examples route, so the always-on Direction step no longer pulls the whole library (the reasoning core stays ~157 lines).
- Rewrote `references/progressive-disclosure.md` to describe the real file set, heavy-vs-cheap reference loading, the directing-engine split, the genre-content ownership map, and a freshness rule.
- Added a `## Intent` section to `seedance-continuation`, the only sub-skill that lacked one.
- Added three CI guards: every sub-skill must carry `## Intent`; freshness-critical platform references must stay within 30 days of `api-status.md`'s `last_verified`; and `progressive-disclosure.md` must document the directing-engine heavy references.
- Bumped active release metadata, README badges (121 eval cases, 58 references), eval/validator expectations, manifest, readiness doc, examples, and translated entry lines to v6.2.0.

## [6.1.1] — 2026-06-28

### Changed

- Added a **Fast Lane** to the root operating loop: a single standalone clip from a non-expert, with no IP/safety flag and no platform-fact question, now routes straight to `seedance-interview-short` -> `seedance-prompt-short` with the source gate, professional gate, capability-map, allocation-model, and the directing engine all load-on-demand instead of mandatory. This fixes a self-inflicted violation of the skill's own intent-first / progressive-disclosure principles on the most common case.
- Made the directing engine load-on-demand rather than always-on: the root Direction step and the full interview now apply the one-sentence-intention coherence rule inline from memory and load `[ref:directing-engine]` only when scenes need distinct treatment, one voice must hold across many clips, or the setup is genuinely unclear.
- Deferred the sequence/continuation interview questions (Q6-Q9) for plain single-clip ideas: questions 1-5 are the single-clip core; 6-9 are raised only when the idea is already a longer story or the user signals a series, part two, continuation, or making it longer.
- Added eval case `beginner_fast_lane_single_clip`; bumped active metadata, README badges, eval/validator expectations, manifest, and readiness doc to v6.1.1 (115 eval cases).

## [6.1.0] — 2026-06-22

### Added

- Added `references/directing-engine.md`: a directorial reasoning layer above the camera, lighting, motion, and character lookup tables. It reads a scene's dramatic function (function, turn, POV, power, subtext), names one intention, and derives a single coherent setup where camera, lens, light, blocking, performance, and sound all reinforce that intention instead of stacking generic "cinematic" descriptors.
- Added a Director's Voice model with six IP-safe functional style archetypes so a project keeps one consistent directorial hand, plus a long-form look spine that progresses scale, movement, light, and sound across connected clips and marks the single clip that breaks the pattern at the story turn.
- Added performance direction that converts emotion into one true visible gesture per beat, plays subtext through contradiction, and a coherence test that rejects unmotivated technique.
- Added a 35-entry genre worked-example library in the directing engine spanning commercial (product, beauty, food, automotive, high fashion, runway, real estate, talking-head pitch), performance and energy (music video, sports, fitness, travel), narrative and genre cinema (intimate dialogue, two-hander, short drama, romance, horror, noir, action, fantasy, sci-fi, nostalgia), animation and stylized (2D anime, 3D/CG, stop-motion, kids), observational and real (UGC, documentary interview, nature/wildlife, pet, establishing), and technical (transformation/VFX, time-lapse). Each is a full read, intention, voice, setup, performance, and compiled-prompt derivation in a distinct directorial voice.
- Added two eval cases: `directing_scene_coherence` and `directorial_voice_across_sequence`.

### Changed

- Wired the directing engine into the operating loop and load map of the root skill and into `seedance-interview`, `seedance-interview-short`, `seedance-prompt`, `seedance-camera`, `seedance-lighting`, `seedance-motion`, `seedance-characters`, `seedance-sequence`, and `seedance-continuation`, so scene direction, performance, and a single directorial voice flow from interview through prompt to long-form continuation. Added an `arc_position` field to the sequence clip card.
- Bumped active release metadata, README badges, reference library, eval metadata, and validator expectations to v6.1.0 (28 sub-skills, 57 references, 114 eval cases).

### Carried forward from v6.0.x maintenance

- Added source-gated provider/router coverage for EvoLink, OpenRouter, Kie.ai, PiAPI, LaoZhang, Runware, ModelsLab, AI/ML API, MuAPI, SeeGen, and Segmind, while keeping them labeled as third-party or router surfaces rather than official ByteDance behavior.
- Added a China-facing provider-search boundary that separates official ByteDance/Volcengine/BytePlus/Doubao/Jimeng/Jianying surfaces from workflow hosts, Chinese-language blogs, and business-partner news that should not be treated as public API providers without provider-owned docs.
- Added official source-gated Seedance 2.0 Mini naming, including the Volcengine `doubao-seedance-2-0-mini-260615` and BytePlus `dreamina-seedance-2-0-mini-260615` surface IDs, plus the shorthand rule for "Seedance V2 Mini".
- Restored the Runway Seedance-specific API guide as a primary source alongside stable Models, API Changelog, Inputs, and help links, with a checker caveat for raw HTTP status inconsistencies.

## [6.0.1] — 2026-06-20

### Added

- Added full native-reader entry docs for Chinese, Japanese, and Korean: `docs/README.zh.md`, `docs/README.ja.md`, and `docs/README.ko.md`.
- Added `seedance-examples-ja` and `seedance-examples-ko` so Japanese and Korean users have active example/rewrite skills, not only vocabulary translation.
- Added CJK sequence/continuation, accepted-footage, textless-localization, and safety rewrite phrases to the active Chinese, Japanese, and Korean vocabulary references.
- Added eval coverage for the CJK front page, Japanese examples, Korean examples, and localized CJK continuation behavior.

### Changed

- Bumped active release metadata, README badges, eval metadata, validator expectations, and example prompt versions to v6.0.1.
- Tightened README routing so Chinese, Japanese, and Korean readers start from native docs and active skills rather than migrated legacy references.

## [6.0.0] — 2026-06-20

Historical base v6 sequence-compiler release.

### Added

- Added stateful sequence architecture: `seedance-sequence`, `seedance-continuation`, sequence project state, continuation handoff, prompt compiler, surface prompt profiles, reference transfer contracts, event density, continuity QC, dense storyboard mode, and failure atlas references.
- Added JSON schemas for project state, clip contracts, take reviews, prompt specs, and generation run records.
- Added deterministic local validators for prompt linting, project state, continuity chains, behavior contracts, sequence evals, and generation-run fixtures.
- Added golden examples for airport continuation, observed deviation, standalone clips, compact I2V, R2V role isolation, phased single-take, dense 2D storyboard, sequence continuation, first/last-frame transition, and one-layer video edit.
- Added 47 sequence-state eval cases, generation benchmark fixtures, and JSONL generation-run examples.

### Changed

- Root routing now runs a Sequence Gate before the Mode Gate and requires accepted source footage or an observed final state before continuation prompts.
- Interview, prompt, short-prompt, troubleshooting, camera, motion, characters, audio, lighting, style, and recipe skills now inherit sequence state, continuity locks, completed beats, reserved future beats, and exact reference tags when present.
- README, skill map, reference library, validation commands, agent compatibility notes, eval rubric, JSON schema reference, and CI workflow now reflect v6.0.0.
- README introduces native-reader start paths, beginning with Chinese, that link into the active vocabulary and example system; full Japanese and Korean parity (native docs and example skills) followed in v6.0.1.
- Prompt budget guidance is surface-specific instead of treating any character count as universal.

## [5.5.2] — 2026-06-12

### Changed

- Deep-proofread release. Swept every markdown, script, vector, and data file for misspellings (90-word lexicon), doubled words, double periods, trailing whitespace, space-before-punctuation, markdown table column mismatches, YAML frontmatter validity, and font-declaration consistency. One defect existed in the repository: a leftover font-weight 500 on the operating diagram's caption class - unified to 400 so all three vector assets share a single weight.
- Bumped active skill metadata, validator expectations, and eval metadata to v5.5.2.

## [5.5.1] — 2026-06-12

### Added

- Added the cross-agent compatibility matrix: verified install paths and routes for Google Antigravity, OpenClaw (ClawHub-compatible), and Hermes Agent; a Trae (ByteDance) call-out; the 30-plus reported SKILL.md-compatible client tier (Cline, Roo Code, Goose, Amp, OpenCode, Kiro, Qwen Code, Continue, Crush, Droid, OpenHands, Letta, and more); and the registry/marketplace channel notes with a do-not-claim rule for unpublished listings.
- Extended the README install table to nine verified targets plus the portable-shape rule for every other standard-compliant client.

### Changed

- Refined the front-page type system: high-contrast editorial serif stack (Didot / Bodoni MT / Hoefler Text / Baskerville / Palatino, Georgia fallback) for the wordmark and operating-diagram root, the tagline recast as a serif italic aphorism in sentence case, and lighter, airier monospace specification labels across all three vector assets; design tokens updated.
- Corrected the OpenClaw install row (its own paths and CLI, not the Claude workspace path) and bumped agent-compatibility verification to 2026-06-12.
- Bumped active skill metadata, validator expectations, and eval metadata to v5.5.1.

## [5.5.0] — 2026-06-12

The minor bump marks the completion of the production arc built across the 5.4.6-5.4.9 line: capability extraction, the six-language anti-slop system, the plain-language interview, the editorial front page, model mechanics, and the soul layer - now closed by the iteration economy.

### Added

- Added `references/retake-protocol.md`: five-verdict take triage (keep / fix in post / edit / re-roll / rewrite) anchored to the allocation model's primary spend, the one-variable rule, attempt budgets with written stop conditions, draft-cheap/lock-expensive cost awareness with verify-live caveats, the auditable shot log, and the honest don't-generate exit.
- Added eval case `retake_triage_discipline` (61 protected cases): fails reflexive regeneration of a keepable take.

### Changed

- Operating-loop repair step now triages returned takes before troubleshooting; `seedance-troubleshoot` routes partial successes to triage instead of rewrites.
- Trued README badges (47 references, 61 evals) and bumped active skill metadata, validator expectations, and eval metadata to v5.5.0.

## [5.4.9] — 2026-06-12

### Added

- Added `references/model-mechanics.md`: a working mental model of the generator in eight mechanisms (attention budget, distribution pull, no-NOT, trajectory prior, compounding error, reference dominance, area-scaled detail, joint audio-video), a novel-case derivation method with a worked example, and a mechanism-indexed diagnosis table wired into `seedance-troubleshoot` — labeled internal reasoning, never architecture claims.
- Added the soul layer: a root Soul section (hear the intent behind the words; keep a story state alive across the conversation so users never repeat a decision; evolve register with the user) and a distinct Intent section in all 24 sub-skills.
- Added eval case for novel-case mechanism reasoning with honest-uncertainty assertions (60 protected cases).

### Changed

- Kept Russian dialogue support explicitly field-observed: the multi-language dialogue claim is attributed to Russian-language coverage, not the official pages, per the repo's claim-boundary rules.
- Routed unknown failures in `seedance-troubleshoot` through mechanism-based diagnosis; cross-linked the capability map to the mechanics.
- Trued README badges (46 references, 60 evals) and bumped active skill metadata, validator expectations, and eval metadata to v5.4.9.

## [5.4.8] — 2026-06-12

### Added

- Added the editorial front-page design system: hand-built theme-aware SVG masthead (`hero-dark.svg`/`hero-light.svg` behind a `prefers-color-scheme` picture element), a specification-style operating diagram (`skill-map.svg`), unified flat-square ink/amber badges, and design tokens in `frontend-design-system.md` — no gradients, no glow, serif display over monospace labels.
- Added field techniques from the Chinese community study: the three-tier action hierarchy for multi-person stability (`seedance-characters`), I2V Hold/React modes (`i2v-guide.md`), the source-look lock for UGC/livestream/film realism (`seedance-style`), the Dreamina/Jimeng bracketed timeline skeleton with a zh template (`multishot-grammar.md`, `vocab/zh.md`), atmosphere-coherence declarations, prop-physics fragility in the capability map, and three recipe families: short drama (短剧), talking head (口播), and home tour.
- Added Russian dialogue engineering from the Russian community study (`vocab/ru.md`, `seedance-vocab-ru`, `audio-guide.md`): short-line rule, the Cyrillic-versus-transliteration field matrix, one-speaker-per-generation, the post-dub fallback for fully voiced pieces, and the access-from-RF wrapper caution.
- Added eval case for the multi-person action hierarchy (59 protected cases).

### Changed

- Hardened `scripts/design_audit.py` to require the theme-aware vector masthead and reject gradients, blur filters, and missing serif/monospace stacks in vector assets.
- Added a safety fast-path to operating-loop intake: clear safety, IP, likeness, or evasion risks route to the safety gate before any planning (stress-test finding).
- Right-anchored the hero specification row to the content margin in both theme variants.
- Relocated generated bitmap art to the curated Visual Gallery; the README's working visuals are now vector.
- Bumped active skill metadata, validator expectations, and eval metadata to v5.4.8.

## [5.4.7] — 2026-06-11

### Added

- Added the multilingual anti-slop layer: language-specific Slop Traps tables in all six vocabulary files (en, zh, ja, ko, es, ru), each converting that community's own empty-quality words into the physical elements that produce the feeling, grounded in community-documented practice.
- Added `skills/seedance-vocab-en`: English precision vocabulary with a 51-row function table, de-slop pass, and filter-aware homonym repairs (clarity-only; genuinely risky content routes to the filter boundary).
- Added the six-class slop taxonomy to `anti-slop-lexicon.md` and `seedance-antislop`: empty evaluators, borrowed image-model tokens, tag salad, negation slop, adjective stacking, and cross-language feel-suffix words, with tag-salad and negation repair sections.
- Added eval cases for English slop and filter vocabulary and Chinese feel-word decomposition (58 cases total).
- Added a fal source row to the source registry, fal model-page URLs to the api-status recheck list, and verified r2v request fields and tier-specific resolution (2026-06-11).

### Changed

- Relabeled fast-tier multi-shot reliability limits from official to field-observed after live verification; reframed the stale fal resolution conflict as tier-specific status.
- Hardened `scripts/vocab_schema_check.py`: Slop Traps section required in every language file; Text and Editing added to strict required functions.
- Registered the four capability references (`capability-map.md`, `allocation-model.md`, `multishot-grammar.md`, `2d-anime-grammar.md`) in the validator and the README Reference Library, and protected all 58 eval cases with required IDs.
- Kept the plain-language interview within its five-question cap by folding the reference-asset question into the batch.
- Trued up README badges (24 sub-skills, 45 references, 58 evals) and added English to the multilingual vocabulary line.
- Bumped active skill metadata, validator expectations, and eval metadata to v5.4.7.

## [5.4.6] — 2026-06-11

### Added

- Added the capability-extraction reference layer: `capability-map.md` (design into model strengths, around known limits), `multishot-grammar.md` (shot labels, the shots-times-seconds budget, cut grammar inside one generation), `2d-anime-grammar.md` (cel/anime medium grammar with the no-lens rule), and `allocation-model.md` (where one generation spends its fidelity budget).
- Added a dated fal surface section to `api-status.md` with per-endpoint params (t2v/i2v/r2v), reference limits, pricing caveats, the 480p/720p-vs-1080p documentation conflict, seed semantics, and reference-to-video-first continuation guidance, plus fal rows in `platform-surface-matrix.md` and `model-name-map.md` and fal routing in the root skill.
- Added technique deepenings: motion transfer in `reference-workflow.md`, audio-as-clock in `audio-guide.md`, the transformation method with persisting carrier in `first-last-frame-guide.md`, and physics-forward prompting in `seedance-motion`.
- Added four eval cases: fal platform-spec verification, prohibited-request plain refusal, wrong-model craft-only routing, and the plain-language no-background interview (56 cases total).

### Changed

- Rewrote the root skill description with plain-language triggers, the full surface list including fal, and explicit non-triggers.
- Added operating-loop capability and allocation checks, surface-specific mode-availability gating, and Load Map rows for the new references.
- Redesigned `seedance-interview` and `seedance-interview-short` for users with no film background: pickable plain-language questions with stated defaults, feeling-to-film translation, expert detection, and a propose-then-adjust mini-treatment flow.
- Added an explicit false-positive-only boundary to `seedance-filter` and reframed its README one-liner to "repairs false positives, never by hiding intent."
- Hardened `scripts/install_codex_skill.py` to exclude image assets, docs, and CI config from installed payloads and to print the installed payload size (~594 KB instead of ~19 MB).
- Bumped active skill metadata, validator expectations, and eval metadata to v5.4.6.

## [5.4.5] — 2026-05-30

### Added

- Added seven generated visual-gallery assets: two cinematic hero shots and five text-rich infographics for skill capabilities, CDN delivery, reference roles, production delivery, and QC.
- Added README visual-gallery coverage so the front page shows the skill as a professional filmmaker operating system instead of a single generic image.
- Added eval coverage for the six-plus-image visual-gallery requirement.
- Added Codex UI metadata at `agents/openai.yaml` and a local installer at `scripts/install_codex_skill.py`.

### Changed

- Updated the README hero, badges, design standard, frontend redesign notes, and frontend design-system rules for text-rich infographic assets.
- Updated install guidance so the repo can be installed into `$CODEX_HOME/skills/seedance-20` or `~/.codex/skills/seedance-20` for direct Codex use.
- Strengthened `scripts/design_audit.py` to require the visual gallery, validate PNG headers, enforce minimum dimensions, and fail stale visual guidance.
- Bumped active skill metadata, validator expectations, and eval metadata to v5.4.5.

## [5.4.4] — 2026-05-30

### Added

- Added a professional filmmaker reference layer: `pro-filmmaking-standards.md`, `cinematography-shot-language.md`, `shot-list-continuity.md`, `color-pipeline-aces.md`, `aspect-ratio-delivery.md`, `subtitles-localization.md`, `audio-post-delivery.md`, and `delivery-qc.md`.
- Added README professional scope for directors, DPs, producers, editors, colorists, sound teams, localization teams, and delivery/QC teams.
- Added eval coverage for shot contracts, multi-shot continuity, ACES/color handoff, aspect-ratio delivery, subtitles/localization, audio post, QC preflight, and global campaign versioning.
- Added professional workflow source records and community-pattern records for shot contracts, textless localization, and campaign cutdown matrices.

### Changed

- Routed the root skill, pipeline, interview, prompt, camera, motion, characters, lighting, audio, recipes, and troubleshooting skills into the new professional production references.
- Expanded JSON schema support for production phase, shot lists, continuity anchors, color pipeline, subtitle plan, audio deliverables, delivery metadata, and QC checks.
- Expanded examples with professional shot-contract, localization-handoff, and delivery-QC examples.

## [5.4.3] — 2026-05-30

### Added

- Added `assets/skill-map-cinematic.png` and replaced the README skill-map display with a generated cinematic bitmap infographic.
- Added `references/multilingual-community-examples.md` with original Chinese-English, Russian-English, Japanese-English, Korean-English, and Spanish-English examples.
- Added safe mixed-language false-positive repair guidance that clarifies benign production context without providing filter-evasion tactics.
- Added eval coverage for multilingual false-positive repair and cinematic infographic/front-page requirements.

### Changed

- Replaced `assets/skill-os-infographic.png` with a more professional cinematic operating-system infographic.
- Expanded prompt examples and mode examples with multilingual community-informed structures.
- Updated community-pattern data with localized Japanese, Korean, Spanish, Russian, and mixed-language prompt-pattern records.
- Updated design validation to require the generated skill-map bitmap alongside the hero and operating-system infographic.

## [5.4.2] — 2026-05-30

### Added

- Added `references/api-workflow.md` and `references/examples-by-mode.md` so API usage, Runway/Volcengine workflow differences, edit/extend, audio-reference handling, FLF2V, and mode-specific examples are discoverable from active skills.
- Added new eval coverage for audio-reference conflicts, Chinese official-style reference formulas, edit/extend routing, Russian structured prompts, shot-list continuity, gallery-safety classification, VFX reference repair, and extension degradation.
- Added richer Runway Seedance 2 and Volcengine May 28-29 source records, including `seedance2`, task lifecycle, first/last-frame role wording, pricing-page caveats, and Runway MCP context.

### Changed

- Rebuilt the README hero image as a cinematic Seedance production-control scene with reference frames, timeline, product reveal, camera rig, and audio waveform.
- Expanded Japanese, Korean, and Spanish vocabulary references into production-ready tables with reference-tag preservation, camera, motion, lighting, audio, edit, extend, and safety language.
- Tightened active skill routing so prompt, camera, motion, audio, pipeline, recipe, troubleshoot, copyright, and filter modules load the new deep references when the task needs them.
- Replaced shallow community-mining records with classified multilingual patterns that preserve reusable structures while rejecting unsafe IP, celebrity, brand, and bypass content.

### Fixed

- Corrected Codex Agent Skill install language so repo-root files are not described as automatically loaded unless installed or scanned from the right path.
- Kept migrated legacy material warning-only and isolated so stale local notes cannot override current source-gated guidance.

## [5.4.1] — 2026-05-30

### Added

- Added `assets/skill-os-infographic.png` and a README section explaining the skill operating-system lanes.
- Added `references/agent-compatibility.md` for Codex/Agent Skills packaging, progressive disclosure, and install caveats.
- Added May 30 source records for Volcengine's May 29 model-list/tutorial updates, the Volcengine API-service ecosystem article, Agent Skills docs, and recent audio-video eval benchmark vocabulary.

### Changed

- Refreshed the dated research snapshot to `research-2026-05-30.md` and the source data file to `sources.seedance-2026-05-30.json`.
- Tightened README installation wording so local skill paths are treated as client-specific targets, not universal install guarantees.
- Updated validation scripts and design checks to enforce the new infographic, agent compatibility reference, v5.4.1 metadata, and May 30 source data.

### Fixed

- Kept FLF2V wording explicitly partner/surface-specific unless a current first-party API page exposes that exact workflow name.
- Added a stronger BytePlus caveat: do not quote Seedance 2.0 BytePlus pricing or model IDs from JavaScript-rendered pages without live official verification.

## [5.4.0] — 2026-05-27

### Added

- Added a generated cinematic README hero image at `assets/hero-cinematic.png`.
- Added dated research and source layers, later carried forward as `research-2026-05-30.md`, plus `platform-surface-matrix.md`, `model-name-map.md`, `first-last-frame-guide.md`, `field-observed-tips.md`, and `community-source-methodology.md`.
- Added structured source and community-pattern data files under `data/`.
- Added source freshness and vocabulary schema validators.
- Added eval cases for model-name accuracy, source freshness, first/last-frame workflow, Chinese/Russian role binding, unsafe bypass refusal, and community corpus safety.

### Changed

- Refreshed `api-status.md` and `source-registry.md` to 2026-05-27 source boundaries.
- Expanded active Chinese and Russian vocabulary references with role binding, first/last-frame, camera, lighting, audio, editing, constraint, and safety terms.
- Updated prompt, pipeline, recipe, filter, and multilingual skills to route into the new research and FLF2V references.
- Updated CI and release validation to run six checks instead of four.

### Fixed

- Prevented ambiguous `Seedance 2.0 Pro` naming from being treated as the official Seedance video-model name.
- Made public prompt-corpus mining safety-first: extract structures and vocabulary, not unsafe raw examples.

## [5.3.0] — 2026-05-08

### Fixed

- Removed the legacy duplicate `user-invokable` frontmatter key and updated the validator to the canonical `user-invocable` field.
- Expanded formerly thin production modules, multilingual vocabulary routers, and reference glossaries so each skill is useful as a standalone entry point.
- Deepened `references/source-registry.md` with source hierarchy, evidence labels, claim boundaries, and required wording for volatile platform claims.

### Changed

- Updated all skill metadata, README badges, validator text, and eval metadata to `5.3.0`.
- Recompressed the root `SKILL.md` into a lean router while keeping detailed guidance in sub-skills and references.

### Added

- Added eight eval cases covering VFX physics, multilingual vocabulary, Chinese examples, anti-slop repair, and short-interview routing.

## [5.2.0] — 2026-05-08

### Fixed

- Repaired the partial v5.1 deployment: restored multiline Markdown, multiline YAML frontmatter, real Python scripts, non-empty evals, and the missing GitHub Actions workflow.
- Replaced old one-line active files that made README, references, and scripts render poorly.
- Normalized all 23 sub-skill frontmatter blocks to `metadata.version: "5.2.0"` and `metadata.parent: "seedance-20"`.

### Changed

- Redesigned the GitHub-facing README as a cleaner project front page with a start-here table, skill map, reference library, validation section, and design standard.
- Replaced neon/overloaded visual language with a disciplined cinematic-control design system.
- Converted oversized active sub-skills into lean procedural routers while preserving old local content through the patcher backup/migration path.
- Updated platform guidance to source-aware, date-stamped language.

### Added

- New SVG frontend assets: `assets/hero-dark.svg`, `assets/hero-light.svg`, and `assets/skill-map.svg`.
- Validation scripts: `scripts/validate_skills.py`, `scripts/content_audit.py`, `scripts/eval_schema_check.py`, and `scripts/design_audit.py`.
- CI workflow: `.github/workflows/validate-skills.yml`.
- Evals: `evals/evals.json` with 18 realistic test cases.
- References: `api-status.md`, `source-registry.md`, `audio-guide.md`, `anti-slop-lexicon.md`, `filter-vocab.md`, `progressive-disclosure.md`, `eval-rubric.md`, and `frontend-design-system.md`.

## [5.1.0] — 2026-05-08

Validation, status, and progressive-disclosure repair release. Superseded by v5.2.0 because the pushed v5.1 files were partially collapsed and incomplete.

## [5.0.0] — 2026-03-03

Intent-first prompting release. Introduced the Director Formula, short-prompt preference, expanded references, and quad-modal workflow routing.

## Historical Releases

Earlier v3.x and v4.x releases built the modular skill structure, multilingual vocabulary, example library, troubleshooting modules, and platform support matrix. See repository history for the full legacy changelog.

# Changelog — seedance-20

All notable changes to this project are documented here.

## [6.0.0] — 2026-06-20

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

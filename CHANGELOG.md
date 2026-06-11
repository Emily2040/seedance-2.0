# Changelog — seedance-20

All notable changes to this project are documented here.

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

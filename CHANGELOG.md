# Changelog — seedance-20

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.7.0] — 2026-02-26
### Changed
- Redesigned `seedance-interview` as **"The Director's Journey"** — a multi-stage storytelling workflow (Vision → Narrative → Visuals → Technical → Final Brief).
- Replaced the A/B/C/D/E guided stages with creative "Director's Questions" for deeper narrative extraction.
- Added `references/storytelling-framework.md` — professional cinematography and narrative design principles.
- Updated root `SKILL.md` to v3.7.0 with storytelling-framework reference and interview in core pipeline.
- Updated README.md: version badge, interview emoji 🎭, skill count 20, references count 5.

## [3.6.1] — 2026-02-26

### Added
- **New `seedance-examples-zh` skill** — 16 production-ready Chinese prompt examples across 7 genres (Short Drama, Advertising, Animation, Product, VFX, Cinematography, Beat Sync).
- **Enhanced Chinese Vocabulary** — Expanded `seedance-vocab-zh` to 400+ terms across 16 categories, including new "Theme & Style" and "Prompt-Ready Phrases".
- **Official Platform Links** — Added official website links for all 10 supported platforms (Antigravity, Gemini CLI, Firebase Studio, Claude Code, OpenClaw, GitHub Copilot, Codex, Cursor, Windsurf, OpenCode) in `README.md`.
- **Author Social Links** — Added clickable 𝕏 and IG links for Emily (@iamemily2050) in `README.md` and `SKILL.md`.

### Changed
- **Universal Version Sync** — All 21 `SKILL.md` files synchronized to `v3.6.1` with updated `2026-02-26` metadata.
- **README Refinement** — Updated version/skill badges, fixed architecture tree flags, and added "Working Examples" collapsible section.
- **Platform Constraints** — Updated `platform-constraints.md` with latest Feb 26 verification and API status.

---

## [3.6.0] — 2026-02-25

### Added
- **Full cross-platform support** — Antigravity, Gemini CLI, Firebase Studio, Codex, Cursor, Windsurf, OpenCode declared in all 20 `SKILL.md` files via `tags` and `metadata` platform blocks.
- `tags:` array added to all 19 sub-skill files (previously missing entirely).
- `metadata.antigravity`, `metadata.gemini-cli`, `metadata.firebase` blocks added to all relevant skills.
- **Platform Compatibility table** injected into root `SKILL.md` body with install paths and one-liner install commands for all 10 supported platforms.
- `seedance-pipeline` tagged with `firebase` for Firebase Studio pipeline integration.
- Author attribution: **Emily (@iamemily2050)** added across `LICENSE`, `README.md`, `CODEOWNERS`, and root `SKILL.md`.
- `README.md` — full GitHub-ready project README with install matrix, skill directory, and badges.
- `LICENSE` — MIT licence with correct copyright holder.
- `CHANGELOG.md` — this file.
- `.github/CODEOWNERS` — ownership declarations.

### Changed
- `metadata.homepage` URLs updated from placeholder `github.com/seedance-2.0` to `github.com/Emily2040/seedance-2.0` across all 20 files.
- Root skill version bumped `3.5.0 → 3.6.0`.
- `seedance-audio` version bumped `4.2.0 → 4.3.0`.
- `seedance-prompt` version bumped `3.3.0 → 3.4.0`.
- `seedance-troubleshoot` version bumped `3.4.0 → 3.5.0`.

---

## [3.5.0] — 2026-02-25

### Added
- OpenClaw / ClawHub full compatibility (`user-invocable: true`, `user-invokable: true` on all 20 skills).
- `metadata.openclaw` blocks with emoji and homepage on all 20 skills.
- `metadata.parent: seedance-20` on all 19 sub-skills.
- Verb-first, single-quoted descriptions with WHEN trigger phrases on all 20 skills.

### Fixed
- Illegal dot in root `name` field: `seedance-2.0` → `seedance-20`.
- Non-standard top-level fields (`last-stress-tested`, `updated`, `last-updated`) migrated into `metadata` JSON block.
- `version:` moved from top-level field into `metadata.version`.
- All 19 sub-skills now explicitly declare `user-invocable: true` and `user-invokable: true`.

---

## [3.4.1] — 2026-02-25

### Added
- `seedance-antislop` skill: anti-slop and filler-language detection for prompt quality.
- `seedance-copyright` skill: live Feb 2026 IP enforcement data (Disney, Paramount, MPA, SAG-AFTRA).
- `seedance-interview` skill v4.0.0: guided A/B/C/D/E multi-stage pre-production workflow.
- Multilingual vocabulary skills: `seedance-vocab-es`, `-ja`, `-ko`, `-ru`, `-zh`.

### Changed
- Root skill version bumped to `3.4.1`.
- Copyright skill updated with post-enforcement state (ByteDance face-upload pause Feb 15 2026).

---

## [3.3.0] — 2026-02-25

### Added
- `seedance-troubleshoot` v3.3.0 with QA checklist and emergency fixes.
- `seedance-pipeline` v3.1.0 with ComfyUI node workflows and post-processing chain.
- `seedance-recipes` v3.1.0 with genre-specific template recipes.

---

## [3.2.1] — 2026-02-25

### Fixed
- Audio skill desync documentation updated with multi-character constraints.
- Camera skill anti-drift lock section added.

---

## [3.2.0] — 2026-02-25

### Added
- `seedance-prompt` v3.2.0 with five-layer stack and `@Tag` delegation levels 1–4.
- `seedance-antislop` v3.2.0.

---

## [3.1.0] — 2026-02-25

### Added
- Initial release of core pipeline skills:  
  `seedance-audio`, `seedance-camera`, `seedance-motion`, `seedance-lighting`,  
  `seedance-characters`, `seedance-style`, `seedance-vfx`.

---

## [3.0.0] — 2026-02-25

### Added
- Initial Seedance 2.0 skill package creation.
- Root `SKILL.md` with quad-modal AI filmmaking framework (T2V · I2V · V2V · R2V).

---

*Maintained by [Emily (@iamemily2050)](https://github.com/Emily2040)*

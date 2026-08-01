# Seedance 2.0 Skill OS — v6.2.0

A modular agent-skill operating system for directing ByteDance **Seedance 2.0** video. It turns vague ideas into production-ready prompts, **directs each scene like a filmmaker**, keeps platform facts source-dated, rewrites unsafe IP, and plans long-form stories across many clips — with localized reader paths for English, 中文, 日本語, and 한국어.

## Headlines since v5.3.0

**The directing engine** — reads a scene's dramatic function (turn, POV, power, subtext), names one intention, and makes camera, lens, light, blocking, performance, and sound all serve it, in a consistent directorial voice across a whole story. Ships with a 33-genre worked-example library, loaded on demand.

**Stateful long-form** — plan globally, generate locally: divide a story into connected clips, compile only the current one, and continue strictly from *accepted footage*, never invented state.

**Multilingual and safety** — localized docs and example skills for Chinese, Japanese, and Korean; cinematic vocabulary for zh/ja/ko/es/ru; IP-safe rewrites; false-positive filter repair; and no guessed API, pricing, or model-ID claims.

## New in v6.2.0

- **Beginner fast lane** — the common single-clip idea skips the full gate loop and routes straight to a fast brief and a compact prompt; heavy references load only when earned.
- **Real eval harness** — a model-in-the-loop scorer (`scripts/eval_run.py`) grades skill *output* against each case's assertions using `references/eval-rubric.md`. The quality bar is now **measured, not asserted**. All 47 boilerplate sequence cases were rewritten into concrete scenarios; **121 eval cases** total.
- **Architecture hardening** — split the directing engine for progressive-disclosure compliance, plus three CI guards: every sub-skill carries an Intent section, freshness-critical platform references stay current against `api-status.md`, and the disclosure plan stays honest.
- **Evolved editorial masthead** — calligraphic wordmark, monospace eyebrow kicker, amber-lozenge ornament, theme-aware across light and dark.

## Quality bar

28 sub-skills, 58 references, 121 eval cases. Eleven deterministic CI validators plus unit tests run on every push, with the model-in-the-loop harness as the semantic quality gate.

Full history in [`CHANGELOG.md`](../CHANGELOG.md).

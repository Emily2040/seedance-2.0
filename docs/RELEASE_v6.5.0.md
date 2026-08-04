# Seedance 2.0 Skill OS — v6.5.0

A modular agent-skill operating system for directing ByteDance **Seedance 2.0** video. It turns vague ideas into production-ready prompts, **directs each scene like a filmmaker**, keeps platform facts source-dated, rewrites unsafe IP, and plans long-form stories across many clips — with localized reader paths for English, 中文, 日本語, and 한국어.

## What's new in v6.5.0 — felt intent, protected from the budget

Long-form clips were converging on *continuity-correct but affect-flat*: the clip contract carried a functional `narrative_job`, but nothing recorded what the viewer should **feel** — so under a tight prompt budget, emotional intention was the first thing silently compressed away.

- **Every clip now carries a `felt_intent`** — one line naming what the viewer should feel or notice. It is the directing engine's one-sentence intention made persistent in sequence state, threaded from the root Sequence Gate through the clip contract, the continuation gates, and the Project State Capsule (`NEXT CLIP INTENT`).
- **Compression can no longer flatten it.** In the prompt compiler, felt-intent carriers — the specific light, performance, and sound clauses that make the intent land — sit directly after action/endpoint in compression priority, above continuity locks. The intent itself never ships to Seedance as an abstract emotion word (anti-slop holds); its carriers ship as concrete visible choices.
- **A pre-generation intent echo** — "this clip exists so the viewer feels X" — is confirmed before generation spends money, in both `seedance-sequence` and `seedance-continuation`.
- **QC now checks affect, not just continuity.** The boundary check fails a successor prompt whose visible choices no longer serve its felt intent.
- **Enforced, not just documented** — both JSON schemas require a non-empty `felt_intent`, the validator checks presence and content for project states and clip contracts (five negative-tested gates), and every example fixture carries a clip-specific intent line.

## The v6 line, recapped

- **Directing engine** — read a scene's dramatic function, name one intention, make every instrument serve it, in one directorial voice; 33-genre worked-example library on demand.
- **Scene layer** — scenes as the re-anchor unit; scheduled re-anchoring at chain-depth caps instead of reactive drift repair; the source-carries-state compiler rule.
- **Beginner fast lane** — the common single-clip idea skips the full gate loop.
- **Real eval harness** — a model-in-the-loop scorer grades skill *output* against each case's assertions.
- **Audio, done honestly** — per-language dialogue capacity, the voice-reference lip-sync path, field-labeled.
- **Multilingual + safety** — localized docs and examples for zh/ja/ko, cinematic vocab for zh/ja/ko/es/ru, IP-safe rewrites, source-dated platform facts.

## Quality bar

28 sub-skills, 58 references, **124 eval cases**. Eleven deterministic CI validators plus unit tests on every push, with the model-in-the-loop harness as the semantic quality gate.

Full history in [`CHANGELOG.md`](../CHANGELOG.md).

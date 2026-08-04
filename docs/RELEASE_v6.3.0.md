# Seedance 2.0 Skill OS — v6.3.0

A modular agent-skill operating system for directing ByteDance **Seedance 2.0** video. It turns vague ideas into production-ready prompts, **directs each scene like a filmmaker**, keeps platform facts source-dated, rewrites unsafe IP, and plans long-form stories across many clips — with localized reader paths for English, 中文, 日本語, and 한국어.

## What's new in v6.3.0 — audio, done honestly

A deep, skeptical research pass on Seedance 2.0's **native audio and dialogue**, folded into the skill and labeled **field-observed / surface-specific — never official**.

- **The correction that matters most:** the audio reference is no longer undersold as "tempo/mood only." On surfaces that accept a spoken-voice reference, an **attached rights-cleared voice can drive lip-sync directly** — the model syncs to your audio instead of synthesizing speech. This is the most reliable field-reported path for **non-English dialogue**, and it's treated as rights-sensitive (own/licensed/cleared voice, routed through copyright when unclear).
- **An architecture reasoning model** ("how the audio actually works"): audio and video are generated jointly; the model **infers sound from the visuals** (the root cause of "generic default audio" — override it by naming the exact sound); speech and articulation are coupled (silent lip-sync is unreliable); lip-sync is **off by default on some surfaces**; reliability is probabilistic; per-language strength is uneven.
- **A field-observed per-language dialogue-capacity table** with the *acoustic-budget vs reliable-sync-budget* distinction and the cross-language unit "one short sentence ≈ one breath": English ~16–20 reliable words / ~15s, Russian ~10–15 and weak, Mandarin strongest, Japanese/Korean weaker — **Korean explicitly flagged as under-tested, not assumed**.
- Per-language Dialogue Notes across all six vocabulary files, the inline audio-tag pattern, and a rights-aware eval (`audio_reference_lipsync_non_english`).

## The v6 line, recapped

- **Directing engine** — read a scene's dramatic function, name one intention, make camera, light, blocking, performance, and sound serve it, in one directorial voice across a story; 33-genre worked-example library loaded on demand.
- **Stateful long-form** — plan globally, generate locally: connected clips, continued strictly from accepted footage.
- **Beginner fast lane** — the common single-clip idea skips the full gate loop.
- **Real eval harness** — a model-in-the-loop scorer grades skill *output* against each case's assertions; the quality bar is measured, not asserted.
- **Multilingual + safety** — localized docs and examples for zh/ja/ko, cinematic vocab for zh/ja/ko/es/ru, IP-safe rewrites, source-dated platform facts.

## Quality bar

28 sub-skills, 58 references, **122 eval cases**. Eleven deterministic CI validators plus unit tests on every push, with the model-in-the-loop harness as the semantic quality gate.

Full history in [`CHANGELOG.md`](../CHANGELOG.md).

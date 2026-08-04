# Seedance 2.0 Skill OS — v6.4.0

A modular agent-skill operating system for directing ByteDance **Seedance 2.0** video. It turns vague ideas into production-ready prompts, **directs each scene like a filmmaker**, keeps platform facts source-dated, rewrites unsafe IP, and plans long-form stories across many clips — with localized reader paths for English, 中文, 日本語, and 한국어.

## What's new in v6.4.0 — the scene layer, built for five-minute stories

The sequence architecture gains the missing tier between story and clip, so a long story no longer defaults to one long extension chain — the exact failure the package's own model-mechanics notes predict.

- **A scene is the re-anchor unit** — one location and time envelope whose clips may chain from each other's accepted footage. **Seamless continuation is legal only inside a scene**; a scene boundary is an intentional cut that opens from canonical references. Cuts are the cheapest continuity tool: audiences expect frame continuity only within a chained shot, so a five-minute story resolves to several scenes of two to five clips.
- **Scheduled re-anchoring, not reactive drift repair** — `extension_depth` now counts consecutive output-sourced generations since the last canonical re-anchor and resets at every canonical open, hard-capped by the scene's `max_chain_depth` (default 2, ceiling 3, grounded in the documented drift behavior). Exceeding the cap is a validation failure with an actionable message.
- **Arc and audio live at scene level** — each scene carries one `arc_position` (clips inherit it) and an audio plan: clips carry ambience, sync SFX, and on-camera dialogue, while music and score are unified in post, because audio is not continuous across separate generations.
- **The source-carries-state compiler rule** — when an accepted clip or final frame is attached as a reference, the source carries the state and the prompt text carries only the delta. A video source carries static and dynamic state; a still frame cannot carry open motion vectors, camera phase, or audio phase, so those stay in prose. Opening-state prose that repeats an attached source is deleted first under budget pressure.
- **Hardened validation** — the scene layer ships enforced, not just documented: both JSON schemas, bidirectional scene–clip membership, type-checked depths and caps, and fourteen negative-tested gates in `project_state_check.py`, all landed after an adversarial review pass.

## The v6 line, recapped

- **Directing engine** — read a scene's dramatic function, name one intention, make camera, light, blocking, performance, and sound serve it, in one directorial voice; 33-genre worked-example library on demand.
- **Stateful long-form** — plan globally, generate locally: scenes → clips, continued strictly from accepted footage.
- **Beginner fast lane** — the common single-clip idea skips the full gate loop.
- **Real eval harness** — a model-in-the-loop scorer grades skill *output* against each case's assertions; the quality bar is measured, not asserted.
- **Audio, done honestly** — per-language dialogue capacity, the voice-reference lip-sync path, and the generic-audio root cause, all field-labeled.
- **Multilingual + safety** — localized docs and examples for zh/ja/ko, cinematic vocab for zh/ja/ko/es/ru, IP-safe rewrites, source-dated platform facts.

## Quality bar

28 sub-skills, 58 references, **123 eval cases**. Eleven deterministic CI validators plus unit tests on every push, with the model-in-the-loop harness as the semantic quality gate.

Full history in [`CHANGELOG.md`](../CHANGELOG.md).

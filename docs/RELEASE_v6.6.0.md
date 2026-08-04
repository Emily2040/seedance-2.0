# Seedance 2.0 Skill OS — v6.6.0

A modular agent-skill operating system for directing ByteDance **Seedance 2.0** video. It turns vague ideas into production-ready prompts, **directs each scene like a filmmaker**, keeps platform facts source-dated, rewrites unsafe IP, and plans long-form stories across many clips — with localized reader paths for English, 中文, 日本語, and 한국어.

## What's new in v6.6.0 — the loop closes

The sequence architecture had the right epistemics ("never invent the bridge") but made the *user* pay for them: describing every clip's end state by hand, re-pasting a growing state file every session, and re-deriving the workflow from schemas each run. v6.6.0 pays those costs down.

- **The agent becomes the state sensor.** New `scripts/extract_last_frame.py` pulls the last (or first) frame of an accepted take, and the new **Observation Fast Path** flips the sensing burden: with a frame or clip attached, the agent fills the observation record from the pixels and asks at most three targeted questions about what a still can never show — open motion, camera movement phase, audio phase. The extracted frame doubles as the continuation image reference, so one attachment pays for both the record and the next generation's anchor.
- **A state lifecycle for thirty-clip projects.** `project-state.json` is the machine truth; the readable capsule regenerates from it and stays under ~40 lines. Completed scenes compress to one line, superseded takes archive to a separate take log on scene close, and full detail is kept only where a continuation prompt can use it — with clear `state_revision` bump rules.
- **The worked end-to-end trace.** `references/sequence-worked-trace.md` walks one real project through the whole loop — planning with scenes and felt intents, an accepted deviation (two steps short of the door), reconciliation, the unexpected-completed-beat case, the chain cap and scheduled re-anchor at the scene boundary, and a session break/resume via capsule — written around the existing machine fixtures so prose and JSON cannot drift apart.

## The v6 line, recapped

- **Directing engine** — read a scene's dramatic function, name one intention, make every instrument serve it, in one directorial voice; 33-genre worked-example library on demand.
- **Scene layer + felt intent** — scenes as the re-anchor unit with scheduled resets; every clip carries what the viewer should feel, protected from compression.
- **Source-carries-state compiler** — attached footage carries the state; text carries only the delta.
- **Beginner fast lane** — the common single-clip idea skips the full gate loop.
- **Real eval harness** — a model-in-the-loop scorer grades skill *output* against each case's assertions.
- **Audio, done honestly** — per-language dialogue capacity and the voice-reference lip-sync path, field-labeled.
- **Multilingual + safety** — localized docs and examples for zh/ja/ko, cinematic vocab for zh/ja/ko/es/ru, IP-safe rewrites, source-dated platform facts.

## Quality bar

28 sub-skills, **59 references**, **126 eval cases**. Twelve deterministic CI checks plus unit tests on every push, with the model-in-the-loop harness as the semantic quality gate.

Full history in [`CHANGELOG.md`](../CHANGELOG.md).

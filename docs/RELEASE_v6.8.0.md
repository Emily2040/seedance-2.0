# Seedance 2.0 Skill OS — v6.8.0

A modular agent-skill operating system for directing ByteDance **Seedance 2.0** video. It turns vague ideas into production-ready prompts, directs each scene like a filmmaker, keeps platform facts inside their source boundary, and now shows you the plan before you pay for a take.

## What's new in v6.8.0 — the prompt learned to direct

v6.7.0 kept the skill honest about a moving outside world. v6.8.0 is about what happens between the idea and the credit: the four paid takes of one fifteen-second banquet scene that this release was written against, and everything they taught. Each take fixed what the previous rule targeted and exposed the next blank the model had filled with a default. The release turns that sequence into procedure.

### Shots, not seconds

The official Seedance 2.0 prompt guide keys a storyboard on shot order (镜头1, 镜头2, 镜头3) and warns that precise per-shot seconds are unstable on 2.0. The community timeline skeleton (0–3 s / 3–6 s) contradicted it and is withdrawn. [multishot-grammar](../references/multishot-grammar.md) now carries the official ruling, a continuous-versus-storyboard shape rule, the four-part shot block with the cut written in words, and a load score that places a shot count on a **Safe / Stretch / Ambitious** ladder with the trade-off stated in one line each. The thresholds are authored heuristics; three rendered takes gave them a first reading, and the person row was split so a held or reacting second person costs half a point. The ladder ranks risk and never edits the shot list.

### Seen, not told

The front page opens with a clip gallery: seven scenes in five languages, each a complete fifteen-second story cut like short drama, each shown with the brief people usually type above it, the exact prompt beneath it, and the floor plan and shot table the prompt was rendered from. Slates stand in until the maintainer renders each clip; a rendered clip proves that one take and nothing more. The shooting brief and render record are in [FRONT_PAGE_CLIPS](FRONT_PAGE_CLIPS.md), including every earlier draft and what each rendered take got wrong.

### The moderation pre-screen

Two of the first gallery prompts were refused before rendering. [moderation-prescreen](../references/moderation-prescreen.md) names the eight cue classes platform classifiers react to, the craft that keeps a benign scene's drama while dropping the cue, and the boundary: prohibited content is refused, never reworded. `scripts/moderation_prescreen.py` lints every shipped prompt surface; the screen runs on every route before delivery. Two physical rules joined the quality pass: never write an involuntary outcome as an endpoint, because the model stages accidents as deliberate acts, and keep spectacle in what the model renders well.

### Direct for the model

[direct-for-the-model](../references/direct-for-the-model.md) was written from three rendered takes. Idioms render as pictures (脸沉下来 became a grey face), so expression is a plain feeling plus one physical anchor; a bare list of muscles renders as a sulk. "Nobody moves" renders a room of mannequins, so everyone else keeps one line of idle business. The model keeps nothing across a cut that the prompt does not repeat, so every shot block ends with a lock line: light, each principal's identity, position, facing, and the camera's side. A reaction is a reverse angle from the side of what is reacted to, and a crossing of the room is a shot, never a cut from the door to a hand at the table. A both-walls table records each rule's two observed failures so no rule is applied as an absolute.

### The shot table

[shot-table](../references/shot-table.md) is the procedure that applies all of the above. For any prompt with more than one shot or more than one person, a floor plan in words and one row per shot exist before any prose: camera side relative to a landmark, who is in frame and where and facing, eye-line, the one action, everyone else's idle business, light, last frame. The prose is rendered from the rows, and the table is delivered beneath the prompt so the person paying for the take checks the geometry on paper first. `scripts/shot_table_check.py` fails any block without a camera side or a light, or with a trap phrase from `data/direction-traps.json`. The prompt skill's output contract lists the table; the short route builds it and asks about any cell it cannot fill.

### Six languages, each written for its readers

The 中文, 日本語, 한국어, Español and Русский front pages are not translations: structure, examples and questions follow each readership, each with a first-prompt and retake walkthrough and a matching quickstart. Coverage and source drift are declared in [LANGUAGE_COVERAGE](LANGUAGE_COVERAGE.md). Independent native review of the pages remains pending and is disclosed on each page.

### Evals, providers and the installation doctor

OrcaRouter is a named eval-harness provider and an optional Atlas Cloud Seedance runner exists, both requiring explicit execution with bounded transport; an advisory outcome comparison and a capped rendered pilot are prepared without any generation. A read-only installation doctor reports what is installed where, classifies payload drift, and never accepts a damaged install. Teaching cards now cover performance and exact dialogue, product binding and material process, and reference-role continuity, resolved to exact active-surface bindings.

## What this release proves — and what it does not

Release verification is the repository's own suite: `python scripts/validate_repo.py --release`, which runs unit-test discovery, the schema, contract, lint and design gates, the evaluator self-test against its frozen source manifest, and `source_registry_check --enforce-freshness` so a stale checked-in registry stamp blocks the release. CI runs the same plan on CPython 3.11 and 3.13 across Ubuntu and Windows, plus the privileged frame-publication paths on their own runners.

What it proves: the checked-in contracts hold, every shipped prompt passes the pre-screen and the shot-table lint, the gallery's tables and prompts are in step, and the ladder, the pre-screen and the direction rules are wired into every route that writes a prompt.

What it does not prove: that any prompt renders as written. The gallery's takes are the only rendered evidence in the repository, they are recorded with their deviations, and none of the current draft has been rendered yet. The ladder thresholds remain heuristics awaiting a calibration pilot. Platform numbers stay inside their source boundary: this release adds no Seedance 2.5 capability guidance, and craft transfers across model lines while platform numbers never do.

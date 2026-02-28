---
name: seedance-prompt
description: 'Build, validate, and optimise Seedance 2.0 prompts using the five-layer stack, @Tag delegation levels 1–4, quad-modal rules, and the JSON schema compiler. Use when constructing or debugging any T2V, I2V, V2V, or R2V prompt, or when output quality does not match the intended scene description.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["prompt", "t2v", "i2v", "v2v", "r2v", "openclaw", "antigravity", "gemini-cli", "codex", "cursor"]
metadata: {"version": "3.6.1", "updated": "2026-02-26", "openclaw": {"emoji": "✍️", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "parent": "seedance-20", "antigravity": {"emoji": "✍️", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "✍️", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-prompt

Prompt construction, @Tag reference system, JSON planning schema, and quad-modal protocol for Seedance 2.0.

## Scope

- Five-layer prompt structure (subject/action/camera/style/sound)
- Delegation levels 1–4 and when to use each
- @Tag role assignment and Universal Reference mode
- Quad-modal protocol rules and failure patterns
- JSON prompt schema and compile rules
- Prompt hygiene and anti-slop

## Out of scope

- Camera phrasing library — see [skill:seedance-camera]
- Character identity locking — see [skill:seedance-characters]
- VFX contracts — see [skill:seedance-vfx]
- Audio layers — see [skill:seedance-audio]

---

## The 6-Part Field Formula (cross-model validated)

From 10,000-generation practitioner data, this structure maps cleanly to the Five-Layer Stack:

```
[SHOT TYPE] + [SUBJECT] + [ACTION] + [STYLE] + [CAMERA MOVEMENT] + [AUDIO CUES]
```

This baseline works across thousands of generations. It is the field-validated form of the Five-Layer Stack.

> **Front-load rule**: The model weights early words more heavily. `"Beautiful woman dancing"` ≠ `"Woman, beautiful, dancing."` Order matters. Subject + action always first.

> **One action per prompt rule**: Multiple actions create AI confusion. `"Walking while talking while eating"` = chaos. One verb per shot.

---

## The Five-Layer Stack

Build prompts in this order. The model is motion-first; subject anchor before style.

```
1. SUBJECT  — who/what is central (identity anchor)
2. ACTION   — primary motion verb + physics/timing
3. CAMERA   — framing + movement + speed + angle
4. STYLE    — 1–3 tokens max (film language, not adjectives)
5. SOUND    — ambient + SFX + music + silence
+ CONSTRAINTS — what must stay consistent; what to avoid
```

First 20–30 words carry disproportionate weight. Subject + action always first.

---

## Delegation Levels

### Level 1 — Pure Intent (≤30 words)

Use when the model knows the domain (food, brands, sports, everyday life).

```
生成一个精美高级的兰州拉面广告，注意分镜编排
```

The model selects shots, music, pacing independently.

### Level 2 — Guided Direction (30–100 words)

Subject + action + environment + one camera note + one style anchor. Most common production mode.

### Level 3 — Time-Segmented (100–300 words)

Use explicit timestamps: `0–3s: ... 3–7s: ... 7–END: ...`

### Level 4 — Full Choreography (300–1000+ words)

Per-shot specifications. Use for fight scenes, lip-sync, product demos. See [skill:seedance-motion].

**Decision rule:** Does the model already know how to shoot this? Yes → Level 1–2. Novel/precise → Level 3–4.

---

## @Tag System

Entry modes:
- **First/Last Frame (首尾帧):** One image + text. For simple I2V.
- **Universal Reference (全能参考):** Multi-modal. Use for everything else.

Input limits: Images ×9, Videos ×3, Audio ×3, Total files ≤12 (Rule of 12).

### Role assignment patterns

Every @Tag needs one explicit role. A bare tag is weak.

```
@Image1's character as the subject
@Image2 as the first frame / @Image3 as the last frame
Scene references @Image2
Wearing the outfit from @Image3
Reference @Video1's camera movement throughout
BGM references @Audio1
Voice timbre references @Audio1
Match the visual style of @Video1
```

### Reference vs. Edit (critical)

- `参考@Video1的运镜` → generate new content using Video1's technique
- `将@Video1中的人物换成...` → modify Video1 directly

These trigger different model behaviors. Be explicit.

---

## Quad-Modal Rules

### T2V
- Subject + action first
- For known domains: Level 1–2, trust the model
- For novel content: Level 3–4 with explicit structure

### I2V
- `@Image1 as the first frame` for stability
- Add `@Image2 as the last frame` for motion-in-between
- Describe only the change from start image, not the whole scene

### V2V
- State what to keep and what to change
- Limit to 1–2 changes per generation
- Modes: reference (new content from technique) vs. edit (modify directly)

### R2V
- Each reference gets ONE job
- State all role assignments before any other content
- For multi-character: attribute every action by name

---

## JSON Schema v3

See [ref:json-schema] for complete schema, field reference, and compile function.

Minimal example (Level 2):

```json
{
  "v": "3.0",
  "meta": { "mode": "i2v", "level": 2, "dur": 10, "ar": "16:9", "res": "1080p" },
  "ref": { "char": "@Image1", "bg": "@Image2", "cam": "@Video1", "bgm": "@Audio1" },
  "shot": {
    "subj": "weathered woman, wool coat, rain platform",
    "act": "slow turn toward camera, breath misting",
    "cam": "dolly push MS→CU over 8s",
    "light": "overhead practical, warm key, low-fill",
    "style": ["anamorphic", "grain", "muted"],
    "snd": { "amb": "rain bed", "sfx": ["train hum at 1s"], "mx": "piano at 2s" }
  },
  "lock": ["stable exposure", "no drift"],
  "exit": "hold 0.8s"
}
```

**Never paste JSON into Seedance.** JSON = plan. Compile to plain text before submitting.

---

## Prompt Hygiene

Delete these words — they are unmeasurable:
`cinematic` `epic` `masterpiece` `ultra-real` `award-winning` `stunning` `8K`

Replace with observable controls:

| ❌ | ✅ |
|---|---|
| cinematic lighting | single hard key 45° camera-left, warm amber, deep shadow |
| epic | wide shot, slow push-in, rising wind, low drone, crescendo at 6s |
| high quality | stable exposure, no flicker, clean edges |

**Conflict check** — never combine:
- locked-off + handheld
- bright flat + low-key shadows
- rapid cuts + long-take

---

## ⚠️ Copyright & Content Policy

Full rules, substitution tables, and architecture/music/audio policy → [skill:seedance-copyright]

**Summary hard blocks**: real celebrity faces · named franchise characters (Iron Man, Naruto, Mario) · named game characters · brand logos · copyrighted scene recreations · named musical compositions.

**Core rule**: describe the *look*, never the *name*.

| ❌ Blocked | ✅ Safe substitute |
|---|---|
| Iron Man | red-and-gold powered exoskeleton, chest reactor glow |
| Naruto | blond spiky-haired shinobi, orange jumpsuit, whisker scars |
| Batman | dark armoured vigilante, scalloped cape |
| Eiffel Tower night lights | glass lattice tower with illuminated night display |
| Bohemian Rhapsody as score | operatic rock build, piano into power chords, multi-voice choir |

For living real persons: never generate by name or distinctive likeness. Use archetype: `"tech billionaire in black T-shirt"` not `"Elon Musk"`.

---

## 🚫 Anti-Slop Protocol

Full blacklist, decomposition patterns, and before/after repairs → [skill:seedance-antislop]

**The one test**: *Can a camera, light meter, or stopwatch measure this word?* If no → delete it.

**Instant-delete list**: `stunning` · `cinematic` · `epic` · `masterpiece` · `beautiful` · `breathtaking` · `8K` · `ultra-real` · `award-winning` · `immersive` · `ethereal` · `magical` · `otherworldly`

**Replace with observable controls**:

| ❌ Slop | ✅ Measurable |
|---|---|
| cinematic lighting | 45° hard key camera-left, amber gel, deep shadow camera-right |
| epic scene | wide shot, dolly pull reveals 200 soldiers, brass swell at 4 s |
| stunning sunset | warm backlight 3200K, 5 min post-horizon, long silhouette shadows |
| 8K ultra-real | stable exposure, no flicker, clean edges, no hallucinated geometry |
| ethereal forest | heavy fog, god rays through canopy, cool teal cast, dust motes |

---

## Routing

Copyright issues → [skill:seedance-copyright]  
Slop/quality audit → [skill:seedance-antislop]  
Camera phrasing → [skill:seedance-camera]  
Character identity → [skill:seedance-characters]  
VFX contracts → [skill:seedance-vfx]  
Audio layers → [skill:seedance-audio]

---

## Agent gotchas

1. Place subject + action in the first 20–30 words. Everything else is secondary.
2. One primary motion verb per shot. Competing verbs = chaos.
3. Positive specification beats long negative lists.
4. Budget discipline: every word must be verifiable in-frame or in-audio.
5. For Level 1: the delegation command `注意分镜编排` activates director intelligence. Add it and step back.
6. **Audio is not optional.** Practitioners with 10,000+ generations confirm: ignoring audio produces flat results regardless of visual quality. Always specify ambient + SFX + music/silence decision.
7. **Seed discipline.** Seed control is available at API level (seed=-1 for random; set integer for reproducibility). On the web platform, seed configurability is not confirmed. When API launches: test seeds 1000–1010 on same prompt, build a typed seed library.
8. **First frame obsession.** Generate 10 variants of just the first frame. First-frame quality predicts entire video outcome. Select best, then build.
9. **Post-Feb-15 content gate.** Any named character (franchise, anime, game, streamer original) or named real person will trigger refusal or degraded output. Run [skill:seedance-copyright] check before submission.

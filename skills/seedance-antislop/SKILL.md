---
name: seedance-antislop
description: 'Detect and remove hollow AI filler language, empty superlatives, and vague boosters that degrade Seedance 2.0 prompt quality. Use when a prompt feels generic, over-written, or ''AI-sounding'', or when generation output looks bland and needs a quality pass.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["writing", "quality", "slop-filter", "openclaw", "antigravity", "gemini-cli", "codex", "cursor"]
metadata: {"version": "3.3.0", "updated": "2026-02-25", "openclaw": {"emoji": "🚫", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "parent": "seedance-20", "antigravity": {"emoji": "🚫", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "🚫", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-antislop

Kill hollow language. Every word must earn its place.

---

## What Is AI Slop?

**AI Slop** is language that *feels* descriptive but contains zero measurable instruction.
It is the residue of training data averaging — words that appear near "good video" in text corpora but tell the model nothing it cannot already assume.

**AI Hum** is the self-congratulatory narration layer AI systems add by default:
*"Certainly! Here is a stunning, cinematic, breathtaking, high-quality prompt that masterfully captures..."*

Both degrade output. Slop wastes token budget. Hum triggers generic mode.

**Platform Slop** is a third type: generic, safe-for-all-audiences boilerplate that AI inserts to avoid refusal. It produces a "cat plays piano at 3 AM" clip when a writer wanted something story-driven. This is the dominant failure mode for creative users after Feb 2026 content-filter tightening.

---

## The One Test

> **"Can a camera, light meter, or stopwatch measure this?"**

If yes → keep it.
If no → delete it or replace with something measurable.

| Word | Measurable? | Verdict |
|---|---|---|
| `cinematic` | No | ❌ Delete or replace |
| `45° key light camera-left` | Yes | ✅ Keep |
| `stunning` | No | ❌ Delete |
| `slow push-in over 6 s` | Yes | ✅ Keep |
| `epic` | No | ❌ Delete or decompose |
| `18mm wide, dolly back 3 m` | Yes | ✅ Keep |
| `8K ultra-real` | No | ❌ Delete |
| `stable exposure, clean edges` | Yes | ✅ Keep |

---

## The Master Slop Blacklist

Delete these words on sight. They are **unmeasurable filler** that trigger generic output.

### Superlative Boosters
`stunning` · `breathtaking` · `incredible` · `amazing` · `beautiful` · `gorgeous` · `magnificent` · `spectacular` · `extraordinary` · `phenomenal` · `jaw-dropping` · `mind-blowing`

### Quality Assertions
`masterpiece` · `award-winning` · `professional` · `ultra-high-quality` · `top-quality` · `world-class` · `best-in-class` · `premium quality`

### Resolution Theater
`8K` · `4K ultra HD` · `super resolution` · `hyper-detailed` · `insanely detailed` · `extreme detail` · `photorealistic` (when used as a booster, not a specific style target)

### Vague Aesthetic Claims
`cinematic` · `epic` · `dramatic` · `artistic` · `creative` · `unique` · `immersive` · `captivating` · `engaging` · `compelling`

### AI Self-Praise (Hum layer — remove entirely)
`certainly` · `of course` · `here is` · `I will now create` · `masterfully` · `expertly crafted` · `carefully designed` · `thoughtfully composed` · `beautifully rendered`

### Empty Atmosphere Words
`magical` · `ethereal` · `transcendent` · `otherworldly` · `surreal` (unless surrealism is the deliberate style) · `mystical` · `enchanting` · `whimsical` (unless fairy-tale is the goal)

### Redundant Emphasis
`very` · `really` · `truly` · `so` · `extremely` · `super` · `highly` when preceding any descriptor

### Platform Safety Slop (new — Feb 2026)
These are added by over-cautious filter-avoidance patterns. They make content bland and generic:
`family-friendly` · `safe for all ages` · `fun and lighthearted` · `wholesome` · `uplifting` · `positive` · `heartwarming` — **unless these are actually your creative intent.**

---

## Decomposition Patterns

When a slop word is removed, replace it with observable components.

### `cinematic` → decompose into:

```
❌  cinematic lighting
✅  single hard key 45° camera-left, amber gel, deep shadow camera-right, no fill
```

```
❌  cinematic shot
✅  slow dolly push-in from MS to CU over 8 s, anamorphic 2.39:1, shallow DOF
```

```
❌  cinematic color
✅  teal shadows, orange-amber midtones, desaturated highlights, slight crush in blacks
```

### `epic` → decompose into:

```
❌  epic battle scene
✅  wide establishing shot, 200 soldiers clashing on a muddy plain,
    handheld low-angle, dramatic brass swell, slow-motion at impact 0.3×
```

```
❌  epic landscape
✅  extreme wide shot, mountain range at dusk, god rays through cloud break,
    drone descending from 800 m to 50 m over 12 s
```

### `stunning` → delete, then strengthen the noun:

```
❌  stunning sunset
✅  sunset, golden-red horizon, 5 min after sun has dipped, long shadows,
    warm backlight 3200K, silhouette of tree line
```

### `beautiful` → specify which property is attractive:

```
❌  beautiful woman
✅  woman, sharp cheekbones, calm expression, direct eye contact — [then add lighting that serves her]
```

### `8K ultra-real` → replace with output contract:

```
❌  8K ultra-real photorealistic
✅  stable exposure, no flicker, clean edge definition, no hallucinated geometry
```

### `masterpiece` → remove entirely:

```
❌  create a masterpiece video of a flower blooming
✅  flower blooming timelapse. Macro push-in. Soft diffused daylight. No camera movement.
```

### `ethereal` → specify the optical cause:

```
❌  ethereal forest scene
✅  forest, heavy morning fog, shafts of diffused light through canopy,
    floating dust motes, cool teal cast, static wide shot
```

### `magical` → specify the effect:

```
❌  magical atmosphere
✅  floating glowing particles, slow upward drift, warm amber light source below frame,
    gentle lens flare at 3 s
```

### `dramatic` → decompose into tension triggers:

```
❌  dramatic lighting
✅  hard single key from 60° above camera-left, deep shadow fill ratio 1:8, no bounce

❌  dramatic scene
✅  two figures, 1.5 m apart, both still. Static camera. Wind lifts coat at 3 s.
    No dialogue. Low-frequency drone audio.
```

---

## Before / After: Full Prompt Repairs

### Example 1 — Product ad

```
❌  Create a stunning, cinematic, ultra-high-quality advertisement for our amazing
    perfume bottle. Make it look incredibly beautiful and photorealistic. 8K quality.
    Breathtaking lighting. Masterpiece level.

✅  Glass perfume bottle on white marble. Camera slow orbit 90° over 8 s.
    Soft studio key top-left, rim light rear-right. Macro DOF on label.
    No text. No people.
```

*Removed:* 14 slop tokens. *Gained:* 3 measurable light instructions, 1 camera path, 2 constraints.

---

### Example 2 — Action scene

```
❌  An epic, breathtaking, jaw-dropping fight scene between two amazing warriors
    in a stunning mystical forest. Ultra-cinematic. World-class choreography.
    Make it feel truly extraordinary and immersive. 4K masterpiece.

✅  @Image1 warrior A (dark armour). @Image2 warrior B (white cloth).
    A charges → B sidesteps → B counter-kick to A's chest → A stumbles into tree.
    Ancient forest, fog, shafts of light. Handheld low-angle, whip-pan at impact 4 s.
    0–4 s real-time; 4–6 s 0.3× slow-motion; 6–10 s real-time.
    Impact sfx at 4 s, ambient forest wind throughout.
```

*Removed:* 16 slop tokens. *Gained:* full choreography, timing, camera move, audio cues.

---

### Example 3 — Mood piece

```
❌  A truly magical, ethereal, incredibly beautiful scene of a woman walking
    through an enchanting, mystical forest at night. Stunning visuals. Cinematic masterpiece.

✅  Woman in white dress walks slowly through night forest.
    Bioluminescent ground plants, cool blue ambient light, breath visible.
    Steadicam follow from behind, medium shot, slow pace.
    Quiet footstep sfx, distant owl, no music.
```

*Removed:* 12 slop tokens. *Gained:* specific light source, breath visibility, camera rig, audio design.

---

### Example 4 — Architecture

```
❌  Showcase our amazing, breathtaking, world-class skyscraper in a stunning
    cinematic drone shot. Ultra-high quality. Make it look absolutely incredible
    and awe-inspiring.

✅  Glass tower, 60 floors. Drone approach from south-east, altitude 300 m,
    slow descent to 80 m over 12 s. Golden hour, warm side light.
    Lens flare at apex. No people. No text.
```

---

### Example 5 — Chinese prompt repair

```
❌  美丽的、震撼的、史诗级的、超高质量的、电影感十足的、令人叹为观止的视频

✅  女性独自走在雨夜街道。霓虹反光，湿地面。
    缓慢跟拍，中景，肩后视角。
    雨声环境音，远处钢琴。低饱和蓝绿色调。
```

---

### Example 6 — Audio-ignored failure (field data from 10,000-generation study)

One of the top failure patterns from practitioner research: prompts with zero audio specification produce flat, lifeless results regardless of visual quality.

```
❌  Person walking through forest
    [no audio spec → model fills with generic ambient wash]

✅  Person walking through forest.
    Audio: leaves crunching underfoot, distant bird calls, gentle wind through branches.
    No music. Natural ambience only.
```

Audio context makes AI video feel real even when visually it's obviously AI-generated.
Always specify: ambient layer + SFX + music/silence decision.

---

### Example 7 — First-frame slop

Slop in first-frame description is the single highest-impact failure vector. The model weights the first 20–30 words heavily. Slop at position 1 poisons the entire generation.

```
❌  "A beautiful, cinematic, high-quality, stunning establishing shot of..."
    [all slop, no information, model gets 0 instruction from first 8 words]

✅  "Glass tower, 60 floors, south-east face, sunset side light."
    [5 words of actual information, model has strong first-frame anchor]
```

> **Rule**: Never let a slop word occupy one of your first 20 tokens.

---

### Example 8 — Platform-specific re-optimization (anti platform slop)

Practitioners making 10,000+ generations found platform-native optimization beats generic repurposing:

```
❌  [Make one good video, reformat for all platforms]

✅  TikTok version: 15–30 s, strong 3-second hook,
    emotionally absurd premise in first frame,
    AI aesthetic leaned-into, vertical 9:16.

    Instagram version: smooth transitions, colour-graded perfection,
    story-in-one-shot, vertical 9:16.

    YouTube Shorts: 30–60 s, educational framing,
    explicit visual thesis in first 3 s.
```

Aspect ratio, energy, hook timing, and duration are **platform measurables**, not slop.

---

## Hum Patterns — Strip on Sight

These are phrases AI systems (including this one when not monitored) insert automatically.
If you see them in a prompt draft, delete the entire sentence and rewrite with pure instruction.

| Hum phrase | What it actually says | Replace with |
|---|---|---|
| `Certainly! Here is your prompt:` | nothing | [delete] |
| `This prompt masterfully captures...` | nothing | [delete] |
| `The following expertly crafted prompt will...` | nothing | [delete] |
| `Beautifully rendered with attention to detail` | nothing | `stable exposure, clean edges` |
| `A thoughtfully composed scene that...` | nothing | [describe the scene directly] |
| `I'll now create a stunning...` | nothing | [delete the entire preamble] |
| `This immersive experience will...` | nothing | [delete] |

---

## Slop Density Audit

Before submitting, count slop tokens in your prompt.

- **0 slop tokens** → submit
- **1–2 slop tokens** → delete, tighten
- **3–5 slop tokens** → rewrite from SUBJECT down
- **5+ slop tokens** → discard and start from Five-Layer Stack

Run the audit: paste prompt, count any word on the blacklist.

---

## The Precision Ladder

From weakest to strongest description of the same concept:

```
Level 0 (slop):    "beautiful cinematic lighting"
Level 1 (genre):   "dramatic portrait lighting"
Level 2 (rig):     "three-point lighting setup"
Level 3 (angles):  "45° key, soft fill camera-right, hair light from above"
Level 4 (numbers): "key at 45° camera-left, 3200K, f/4 falloff; fill at 0.3× key power"
```

Aim for Level 3 minimum. Level 4 when consistency is critical.

---

## The Director's Three Laws (Anti-Slop Rules)

Derived from practitioner consensus and volume-generation data:

**Law 1: Volume over perfection.**
Generate 10 variants. Select the best. Systems beat divine inspiration.
```
❌ "Try to make one perfect prompt"
✅ "Generate 10 versions with seed variations 1000–1010. Keep the best."
```

**Law 2: One action per shot.**
Competing verbs create chaos. Each clip is one motion.
```
❌ "Walking while talking while eating while looking around"
✅ "Slow walk forward. Medium shot. No gestures."
```

**Law 3: Front-load information, never adjectives.**
The model weights early tokens. Spend them on substance.
```
❌ "Beautiful, cinematic, stunning, gorgeous woman walks..."
✅ "Woman, 30s, dark coat, rain-soaked street, walks toward camera..."
```

---

## Positive Constraints as Quality Control

⚠️ **Seedance 2.0 does NOT support negative prompts.** There is no `--no` syntax, no `negative:` field.
Use **positive constraints** — describe what you want, not what you don't want.

```
❌  --no watermark --no distorted hands --no blurry edges
✅  clean background, no overlaid text, stable hand positions,
    crisp edge definition, no hallucinated geometry
    [state as plain positive requirements]
```

The strategy: instead of listing what to exclude, specify the output contract you expect.
Same information, correct direction. Works with the model instead of against its architecture.

---

## Routing

For prompt construction → [skill:seedance-prompt]
For style without slop → [skill:seedance-style]
For QA / output review → [skill:seedance-troubleshoot]

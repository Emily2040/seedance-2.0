# seedance-2.0

**Comprehensive production pipeline for quad-modal AI filmmaking with Seedance 2.0 (ByteDance / Dreamina)**

---

## Metadata

- **Name:** seedance-2.0
- **Description:** Comprehensive production pipeline for quad-modal AI filmmaking with Seedance 2.0 (ByteDance / Dreamina). Covers the full spectrum from minimal-intent directing to frame-precise choreography. Handles @Tag references (I2V/V2V/R2V), multi-character workflows, storyboard methods, video extension chains, action choreography, audio design, and post-processing. Compiles final plain-text generation prompts optimized for the platform.
- **Version:** 3.1.0
- **Last Stress-Tested:** 2026-Q1
- **License:** MIT
- **Author:** Iamemily2050 (@iamemily2050 on X/IG)
- **Repository:** https://github.com/Emily2040/seedance-2.0-skill

---

## Table of Contents

- [Introduction](#introduction)
- [Architecture Map](#architecture-map)
- [Platform Overview](#platform-overview)
- [Platform Constraints](#platform-constraints)
- [Module 00: Foundational Philosophy](#module-00-foundational-philosophy)
- [Module 00A: Director's Vision](#module-00a-directors-vision)
- [Module 00B: When to Direct vs. Delegate](#module-00b-when-to-direct-vs-delegate)
- [Module 01: Prompt Architecture](#module-01-prompt-architecture)
- [Module 01A: Universal Reference System](#module-01a-universal-reference-system)
- [Module 01B: Platform Parameters & Access](#module-01b-platform-parameters--access)
- [Module 01C: JSON Prompt Technique](#module-01c-json-prompt-technique)
- [Module 02: Quad-Modal Protocol](#module-02-quad-modal-protocol)
- [Module 03: Camera Language Codex](#module-03-camera-language-codex)
- [Module 03B: Storyboard Reference Technique](#module-03b-storyboard-reference-technique)
- [Module 04: Motion & Temporal Control](#module-04-motion--temporal-control)
- [Module 04B: Action Choreography Protocol](#module-04b-action-choreography-protocol)
- [Module 04C: Sequential Extension Protocol](#module-04c-sequential-extension-protocol)
- [Module 05: Lighting & Atmosphere](#module-05-lighting--atmosphere)
- [Module 06: Subject & Character Fidelity](#module-06-subject--character-fidelity)
- [Module 06B: First-Frame Art Direction](#module-06b-first-frame-art-direction)
- [Module 07: Style & Aesthetic Control](#module-07-style--aesthetic-control)
- [Module 08: Edge Case Grimoire](#module-08-edge-case-grimoire)
- [Module 08B: Known Platform Behaviors](#module-08b-known-platform-behaviors)
- [Module 09: Quality Assurance](#module-09-quality-assurance)
- [Module 10: Maintenance Protocols](#module-10-maintenance-protocols)
- [Module 11: CGI Pipeline](#module-11-cgi-pipeline)
- [Module 12: VFX Integration](#module-12-vfx-integration)
- [Module 12B: Energy, Magic & Destruction VFX](#module-12b-energy-magic--destruction-vfx)
- [Module 13: Audio & Sonic Design](#module-13-audio--sonic-design)
- [Module 13B: Advanced Audio Techniques](#module-13b-advanced-audio-techniques)
- [Module 14: Final Director's Self-Check](#module-14-final-directors-self-check)
- [Module 15: Pipeline Integration](#module-15-pipeline-integration)
- [Module 16: Genre Recipe Book](#module-16-genre-recipe-book)
- [Appendix A: Compact Prompt Examples](#appendix-a-compact-prompt-examples)
- [Appendix C: Quick Reference Card](#appendix-c-quick-reference-card)
- [Appendix D: Chinese Cinematic & Photography Vocabulary](#appendix-d-chinese-cinematic--photography-vocabulary)
- [Contributing](#contributing)
- [Changelog](#changelog)

---

## Introduction

**SEEDANCE 2.0 — THE DIRECTOR'S GRIMOIRE (v3)**

The definitive pipeline standard for quad-modal AI filmmaking (T2V · I2V · V2V · R2V) with native audio-video joint generation.

Seedance 2.0 is not just a renderer — it is a co-director. It has world knowledge, narrative intelligence, and cinematographic instinct. Your job is to decide **when to direct precisely** and **when to delegate to its intelligence**.

This skill document represents the cumulative knowledge of 150+ prompt variations, stress-tested workflows, and verified platform behaviors as of Q1 2026.

---

## Architecture Map

| Module | Title | Purpose |
|-------:|-------|---------|
| **00** | Foundational Philosophy | How to think before prompting |
| **00A** | Director's Vision | Purpose-first directing (visual + sonic intent) |
| **00B** | When to Direct vs. Delegate | Choosing minimal-intent or full-specification mode |
| **01** | Prompt Architecture | Prompt structure, syntax, anti-slop, and budget |
| **01A** | Universal Reference System | @Tag roles, asset preparation, multi-character, props |
| **01B** | Platform Parameters & Access | Aspect ratio, duration, resolution, platform routes |
| **01C** | JSON Prompt Technique | Plan in JSON, compile to optimized plain text |
| **02** | Quad-Modal Protocol | Mode rules (T2V, I2V, V2V, R2V) + failure patterns |
| **03** | Camera Language Codex | Reliable camera phrasing, multi-shot, one-take |
| **03B** | Storyboard Reference Technique | Nine-grid method, visual storyboards as input |
| **04** | Motion & Temporal Control | Timing, pacing, stillness, continuity |
| **04B** | Action Choreography Protocol | Fight scenes, impact physics, grid method |
| **04C** | Sequential Extension Protocol | Video extension chains for long-form production |
| **05** | Lighting & Atmosphere | Light as narrative state + atmosphere contracts |
| **06** | Subject & Character Fidelity | Character cards, identity locks, hand safety |
| **06B** | First-Frame Art Direction | Composing reference images for I2V success |
| **07** | Style & Aesthetic Control | Style anchors, render-engine tokens, period control |
| **08** | Edge Case Grimoire | Failure modes + stepwise fixes |
| **08B** | Known Platform Behaviors | Living document of current-quarter observations |
| **09** | Quality Assurance | Pre-render checklist + compression ladder |
| **10** | Maintenance Protocols | Versioning + regression tests |
| **11** | CGI Pipeline | Materials, realism, avoiding plastic sheen |
| **12** | VFX Integration | FX physics contract + compositing language |
| **12B** | Energy, Magic & Destruction VFX | Particles, beams, explosions, environmental destruction |
| **13** | Audio & Sonic Design | Native audio, dialogue, lip-sync, mix intent |
| **13B** | Advanced Audio Techniques | Voice reference, emotion modification, beat-sync, multi-language |
| **14** | Final Director's Self-Check | Mandatory verification pass |
| **15** | Pipeline Integration | ComfyUI, API workflows, post-processing |
| **16** | Genre Recipe Book | Ready-to-use templates for common content types |

---

## Platform Overview

**Seedance 2.0** is developed by **ByteDance** and accessed primarily through:

- **Dreamina (即梦):** [jimeng.jianying.com](https://jimeng.jianying.com) — full web interface, two entry modes
- **CapCut / Jianying app:** Mobile integration
- **Xiaoyunque (小云雀) app:** Mobile-first access
- **Volcengine API:** Programmatic access (model string: `Doubao-Seedance-2.0`)
- **Doubao app:** Mobile with simplified interface

The platform uses a **Dual-Branch Diffusion Transformer** architecture for simultaneous video and audio generation.

---

## Platform Constraints

**VERIFIED Q1 2026**

| Parameter | Limit | Notes |
|-----------|-------|-------|
| **Generation duration** | 4–15 seconds (web), 5–10s (some mobile) | Adjustable slider |
| **Resolution** | 720p default, up to 1080p (2K for premium) | No native 4K |
| **Image inputs** | Up to 9 | JPG/PNG/WEBP, <30MB each |
| **Video inputs** | Up to 3 | <50MB each, <15s each |
| **Audio inputs** | Up to 3 (MP3) | Total ≤15s combined |
| **Total file inputs** | 12 maximum | The "Rule of 12" |
| **Audio output** | Dual-channel stereo | Synced to video length |
| **Aspect ratios** | 16:9 / 9:16 / 1:1 / 4:3 | 9:16 changes composition rules |

### Text Prompt Length

The exact character limit for text prompts is not officially documented with a hard number. In practice, Chinese-language creators routinely use prompts of **1000–3000+ Chinese characters** with success on the Dreamina web interface. The API may have different constraints. English prompts tend to require more characters for equivalent semantic density.

**Practical guidance:** Keep prompts as concise as possible — not because of a hard cutoff, but because shorter, structured prompts consistently outperform verbose ones. Research across 150+ prompt variations shows that **30–100 word English prompts** (or roughly 50–200 Chinese characters for simple scenes, up to 500–1000 for complex choreography) produce the best motion quality. Beyond that range, the model's attention dilutes and motion degrades.

**Budget discipline:** Even without a confirmed hard limit, treat prompt length as a scarce resource. Every word should be verifiable in-frame or in-audio. If you cannot point to what a phrase controls, delete it.

### Real-Face Restriction

Real human face references require identity verification or authorization on the platform. Workarounds include using AI-modified portraits (run through an image model first) or illustrated/3D character references.

---

## Module 00: Foundational Philosophy

### The Director's Three Laws

**Law I — Specificity is kindness.**  
Specify what is observable (frame), audible (sound), and temporal (when). But only specify what the model cannot infer on its own.

**Law II — The model reads left-to-right, early tokens weighted heavily.**  
The first 20–30 words carry disproportionate weight. Place your subject anchor and primary action there. Hard constraints early, emotional/stylistic polish last.

**Law III — Know the model's strengths; work with them.**  
Seedance 2.0 excels at:
- Atmosphere and environmental mood
- Organic human motion and physics
- Large-scale VFX and creature generation
- Cinematic lighting shifts
- Camera movement replication
- Multi-shot editing with sound
- Audio-video co-generation
- Brand/domain world knowledge
- Martial arts and fight choreography
- Beat-synced editing

It struggles with:
- Dense on-screen text and typography
- Perfect finger articulation in close-up
- Tiny mechanical precision
- Ultra-busy scenes with too many simultaneous moving parts
- Maintaining objects under high-speed motion

---

## Module 00A: Director's Vision

**A technically correct prompt that produces meaningless footage is still a failure.**

Before writing the technical prompt, answer five questions:

1. **What must the audience feel** (one emotion)?
2. **What changes by the end** (transformation)?
3. **What is the single most meaningful moment** (timestamp)?
4. **Why is the camera where it starts?**
5. **What is the sonic world** (even if implied)?

### 3-Second Rule

If you cannot describe what happens in any 3-second window, the shot is drifting.

### Exit Rule

Land the last frame and last second of audio together. If motion is mid-gesture at cutoff, the clip feels accidental. Specify "final frame holds for 0.5–1s" when appropriate.

---

## Module 00B: When to Direct vs. Delegate

**This is the most important strategic decision in Seedance 2.0 prompting.** The model has genuine director intelligence — world knowledge, narrative instinct, and cinematographic taste. Choosing the wrong level of specification wastes effort or suppresses the model's strengths.

### The Delegation Spectrum

#### Level 1 — Pure Intent (≤30 words)

**Use when:** The scene involves common knowledge domains (food, brands, sports, everyday activities), and you trust the model's editorial judgment.

**Pattern:** `[Subject/scenario], [one style/mood word], 注意分镜编排 (pay attention to shot arrangement).`

**Example:**  
```
生成一个精美高级的兰州拉面广告，注意分镜编排
(Generate an elegant premium Lanzhou ramen ad, pay attention to shot arrangement)
```

**Result:** The model independently chose slow-motion for noodle-pulling, arranged multiple shots, selected appropriate music, and made all cinematographic decisions. Total prompt: 18 Chinese characters.

**When this works:** The model knows how ramen is made, understands MUJI's brand philosophy, knows proper exercise form, understands film genre conventions. For these domains, **less is more**.

#### Level 2 — Guided Direction (30–100 words)

**Use when:** You have a specific vision but want the model to handle technical execution. **Most common mode for quality results.**

**Pattern:** Subject + action + environment + one camera note + one style anchor.

#### Level 3 — Time-Segmented Direction (100–300 words)

**Use when:** You need specific events at specific moments, multi-shot sequences, or narrative beats.

**Pattern:** Time-stamped segments (0–3s, 3–7s, 7–END) with camera and sound layers.

#### Level 4 — Full Choreography (300–1000+ words)

**Use when:** Fight scenes, precise product demos, frame-accurate lip-sync, or any scene requiring per-second control.

**Pattern:** Per-shot specifications with numbered cameras, impact physics, particle effects, and sound design per beat.

### Decision Framework

**Ask:** "Does the model already know how to shoot this?"  
- If yes → Level 1–2
- If you need something novel, unusual, or precisely timed → Level 3–4

**Ask:** "Am I better at this than the model?"  
- For common cinematography and editing → probably not, delegate
- For your specific creative vision → direct precisely

### Anti-Pattern

❌ Writing Level 4 prompts for Level 1 scenarios. Over-specification of common scenes often produces worse results than delegation because the model's trained instincts get overridden by your amateur shot-listing.

---

## Module 01: Prompt Architecture

### The Five-Layer Stack (Motion-First Order)

The model prioritizes motion coherence. Structure prompts to establish subject → define action → control camera → set style → add constraints.

1. **SUBJECT** — who/what is central (the anchor point for all motion)
2. **ACTION** — what changes (primary motion verb + physics/timing details)
3. **CAMERA** — framing + movement + speed + angle
4. **STYLE & LIGHT** — one strong visual anchor + named light source
5. **CONSTRAINTS** — what must stay consistent, what to avoid

**Optional Layer 6: SOUND** — ambient bed + key SFX + music + silence design.

### One Primary Motion Verb Per Shot

Multiple competing actions ("walks while turning and gesturing and looking around") create chaos. For complex choreography, break actions into sequential beats with timestamps or use a reference video.

### Syntax Conventions (Reliable)

- **Commas** sequence events within a beat: `"door opens, light spills in, dust rises."`
- **Periods** separate layers: new layer = new sentence.
- **Parentheses** for technical asides: `"(rack focus foreground→background)."`
- **Explicit temporal markers** for multi-scene: `"Scene 1: ... Scene 2: ... Scene 3: ..."`
- **Timestamps** for precise control: `"0–3s: ... 3–7s: ... 7–END: ..."`
- Avoid semicolons and long em-dash chains.
- Prefer positive specification over long negative lists.

### Prompt Hygiene and Anti-Slop

**Avoid empty filler:** "cinematic," "epic," "masterpiece," "ultra-real," "award-winning," "viral."

**Replace with controls:**
- ❌ "cinematic lighting" → ✅ "single hard key 45° camera-left, warm amber, deep shadow fill."
- ❌ "epic" → ✅ "wide shot, slow push-in, rising wind, sustained low drone, crescendo at 6s."
- ❌ "high quality" → ✅ "stable exposure, no flicker, consistent character design, clean edges."
- ❌ "8K" → (delete unless combined with a render-engine style token; see Module 07).

**Conflict check:** Never combine mutually exclusive instructions. Common conflicts:
- locked-off + handheld
- bright flat + low-key shadows
- rapid cuts + long-take
- slow graceful + energetic pacing

**Deletion rule:** If a word cannot be verified in-frame or in-audio, delete it or convert it into something observable.

### ⚠️ COPYRIGHT, IP, LIKENESS & SAFEGUARDS

Seedance 2.0 has strict content filters, tightened under pressure from the Motion Picture Association and Disney. The platform scans both text and uploaded images before generation.

**Hard blocks (will trigger rejection):**
- Celebrity faces/voices, politicians, influencers, private individuals without authorization
- Named franchise characters, IP keywords ("Iron Man," "Mickey Mouse," "Harry Potter")
- Scene recreations of copyrighted content
- Brand logos when the goal is replication
- Visual uploads of recognizable copyrighted characters (even without naming them)

**Do this instead:**
- Use original characters, original worlds, original props
- Use archetypes and film grammar (lens, light, pacing), not IP names
- Describe characters generically: "red armored robot suit" not "Iron Man"
- Use AI-generated or illustrated character references

**If blocked:** Remove named IP/real people. Redesign toward originality. Do not iterate toward "almost forbidden."

⚠️ This skill is not legal advice. Commercial use should receive professional legal review.

---

## Module 01A: Universal Reference System

### Paradigm Shift: Reference-Driven Workflow

Seedance 2.0's core breakthrough is **全能参考 (Universal Reference)**. The old workflow was "write detailed text → hope for the best." The new workflow is **"provide the right reference assets → write minimal orchestration text."**

Reference assets replace manual art direction. You don't need to manufacture keyframes if you have good reference materials. The model's aesthetic becomes **"your selection is the only standard."**

### Platform Entry Modes

Dreamina offers two entry points — choose the right one:

1. **First/Last Frame mode (首尾帧):** For single image + text. Use when you have one reference image and want to animate it.
2. **Universal Reference mode (全能参考):** For multi-modal combinations. Use whenever you have more than one image, or any video/audio references. **This is the mode that unlocks Seedance 2.0's full power.**

**Rule of thumb:** If your inputs are just one image + text → First/Last Frame. Everything else → Universal Reference.

### Input Limits

- **Images:** up to 9 (JPG/PNG/WEBP, <30MB each)
- **Videos:** up to 3 (<50MB each, <15s each)
- **Audio:** up to 3 (MP3, total ≤15s)
- **Total files:** 12 maximum (the "Rule of 12")

### @Tag Assignment (Critical)

Every uploaded asset gets a tag (`@Image1`, `@Video1`, `@Audio1`). **Always assign each tag an explicit role.** A bare tag with no role instruction is weak and leads to misinterpretation.

**How to invoke @Tags:** Type "@" in the input field to see your uploaded assets. Click to insert. Hover to preview and verify you're referencing the correct asset.

### Role Phrases (Copy/Paste Patterns)

**Identity and appearance:**
- `@Image1's character as the subject`
- `@Image1 for facial features and clothing`
- `Use @Image1 and @Image2 for the character's appearance from multiple angles`

**First/last frame:**
- `@Image1 as the first frame`
- `@Image2 as the last frame`

**Scene and environment:**
- `Scene references @Image2`
- `@Image3 as the background environment`

**Costume and props:**
- `Wearing the outfit from @Image3`
- `Holding the weapon from @Image2`

**Camera and motion transfer:**
- `Reference @Video1's camera movement throughout`
- `Fully replicate @Video1's camera movements and transitions`
- `Reference @Video1's action choreography`
- `Imitate the fighting choreography from @Video1`

**Audio:**
- `BGM references @Audio1`
- `Voice timbre references @Audio1`
- `Sync movements with the beat from @Audio1`

**Style transfer:**
- `Match the visual style and color grading of @Video1`
- `Apply @Image1's artistic style to the scene`

### The "Reference" vs. "Edit" Distinction (Critical)

These two phrasings trigger fundamentally different behaviors:

- ✅ **"参考@视频1的运镜" (Reference @Video1's camera movement)** = Generate new content that borrows the technique from the reference.
- ✅ **"将@视频1中的女生换成戏曲花旦" (Replace the girl in @Video1 with a Peking opera actress)** = Modify the reference directly.

Be explicit about which operation you intend. The model does not guess.

### Multi-Character Reference Patterns

For two-character interactions (fights, dialogue, dance), assign separate identity anchors:

**Pattern:** `"Character A references @Image1; Character B references @Image2."`

Then describe their interaction: `"Character A throws a right punch at Character B. Character B blocks with crossed arms."`

Keep each character's actions clearly attributed. Avoid ambiguous pronouns.

### Prop and Weapon Separation

Use separate references for character body and props/weapons:

**Pattern:** `"Character appearance references @Image1. Weapon design references @Image2."`

This prevents the model from blending prop details into the character's body.

### Reference Priority When Over Budget

If you have more references than the 12-file limit allows, prioritize:
1. Character identity images (most impact on consistency)
2. Camera/motion reference video (most impact on production quality)
3. Audio reference (most impact on pacing and mood)
4. Scene/environment images (can often be described in text)

---

## Module 01B: Platform Parameters & Access

Set these **before** writing the prompt:

- **Duration:** 4–15 seconds (web). Shorter = cheaper and faster.
- **Aspect ratio:** 16:9 (landscape), 9:16 (portrait/Douyin/TikTok), 1:1, 4:3.
- **Resolution:** 720p default, up to 1080p/2K tier-dependent.
- **Seed (if available):** Record for reproducibility.

**Portrait (9:16) changes composition rules:** Reduce horizontal pans/orbits, prefer centered subject hierarchy and vertical reveals.

### Extension Duration Rule

When extending a video, the duration setting refers to the **new segment length**, not total length. To add 5 seconds, set duration to 5 seconds.

---

## Module 01C: JSON Prompt Technique

### The Rule

**Never paste JSON into Seedance as the generation prompt.** JSON is for planning, versioning, and pipeline storage only. The final generation prompt must be **plain text**. JSON is the source-of-truth blueprint; the compiled plain-text output is what gets submitted to the platform.

---

### Schema Design Principles

- **Every key must map to exactly one output token in the compiled prompt.** If a key produces nothing, remove it.
- **Arrays only for multi-value fields** (style tokens, lock constraints, SFX list). Single-value fields are strings.
- **Null = field intentionally omitted** (not "to be filled later"). If you don't know a value, don't include the key.
- **Timestamps live in `seg` (segments), not in `shot`**. Mixing temporal logic with static description is the primary cause of bloated JSON.
- **`ref` keys are @Tag assignments only** — no description. Description lives in `shot`.
- **`lock` is a constraint array** — these become the CONSTRAINTS layer of the compiled prompt.

---

### Schema v3 — Full Field Reference

```json
{
  "v": "3.0",
  "meta": {
    "mode": "t2v|i2v|v2v|r2v",
    "level": "1|2|3|4",
    "dur": 10,
    "ar": "16:9|9:16|1:1|4:3",
    "res": "720p|1080p|2k",
    "seed": null
  },
  "ref": {
    "char": "@Image1",
    "char_b": "@Image2",
    "bg": "@Image3",
    "cam": "@Video1",
    "style": "@Video2",
    "bgm": "@Audio1",
    "voice": "@Audio2"
  },
  "shot": {
    "subj": "",
    "act": "",
    "cam": "",
    "light": "",
    "style": [],
    "snd": {
      "amb": "",
      "sfx": [],
      "mx": ""
    }
  },
  "seg": [],
  "lock": [],
  "exit": ""
}
```

**Field definitions — no optional fields listed unless needed:**

| Key | Type | Maps to | Notes |
|-----|------|---------|-------|
| `meta.mode` | enum | (planning only) | Does not compile into prompt text |
| `meta.level` | 1–4 | (planning only) | Sets compilation template |
| `meta.dur` | int | (platform setting) | Seconds; not in prompt |
| `meta.ar` | enum | (platform setting) | Not in prompt |
| `meta.res` | enum | (platform setting) | Not in prompt |
| `meta.seed` | int\|null | (platform setting) | Record after generation |
| `ref.char` | string | @Tag role: identity | "Character references @Image1" |
| `ref.char_b` | string | @Tag role: identity | Only for 2-character shots |
| `ref.bg` | string | @Tag role: environment | "Scene references @ImageN" |
| `ref.cam` | string | @Tag role: camera | "Reference @VideoN's camera movement" |
| `ref.style` | string | @Tag role: aesthetic | "Match style of @VideoN" |
| `ref.bgm` | string | @Tag role: music | "BGM references @AudioN" |
| `ref.voice` | string | @Tag role: voice | "Voice timbre references @AudioN" |
| `shot.subj` | string | SUBJECT layer | Who/what; identity anchor |
| `shot.act` | string | ACTION layer | Primary motion verb + physics |
| `shot.cam` | string | CAMERA layer | Framing + movement + speed |
| `shot.light` | string | LIGHT layer | Named source + contrast |
| `shot.style` | array | STYLE layer | Max 3 tokens |
| `shot.snd.amb` | string | SOUND: ambient bed | Continuous background |
| `shot.snd.sfx` | array | SOUND: event SFX | Event-locked, with timestamps |
| `shot.snd.mx` | string | SOUND: music cue | Entry time + arc |
| `seg` | array | Temporal segments | Only for Level 3–4 (see below) |
| `lock` | array | CONSTRAINTS layer | Consistency rules + avoidance |
| `exit` | string | Terminal beat | "hold Xs" or "fade" |

---

### `seg` Array — Level 3–4 Temporal Segments

Each segment object:

```json
{
  "t": "0-3s",
  "act": "lights flicker and die, red lamp activates",
  "cam": "handheld push",
  "sfx": ["buzz cut", "silence"]
}
```

`seg` fields:

| Key | Required | Description |
|-----|----------|-------------|
| `t` | yes | Time range: `"0-3s"`, `"3-7s"`, `"7-end"` |
| `act` | yes | What happens in this window |
| `cam` | no | Camera change for this segment only |
| `sfx` | no | SFX locked to this segment |

---

### Complete Examples

#### Level 1 — Minimal Intent

```json
{
  "v": "3.0",
  "meta": { "mode": "t2v", "level": 1, "dur": 8, "ar": "16:9", "res": "1080p" },
  "shot": {
    "subj": "premium sushi restaurant",
    "act": "elegant commercial showcase, multiple angles",
    "snd": { "amb": "subtle ambient", "mx": "grand atmospheric" }
  },
  "lock": ["注意分镜编排"]
}
```

**Compiled output:**
```
Premium sushi restaurant elegant commercial showcase, multiple angles. Grand atmospheric music.
注意分镜编排
```

---

#### Level 2 — Guided Direction

```json
{
  "v": "3.0",
  "meta": { "mode": "i2v", "level": 2, "dur": 10, "ar": "16:9", "res": "1080p", "seed": null },
  "ref": {
    "char": "@Image1",
    "bg": "@Image2",
    "cam": "@Video1",
    "bgm": "@Audio1"
  },
  "shot": {
    "subj": "weathered woman, heavy wool coat, rain-slick platform, breath misting",
    "act": "stands still, slow turn toward camera",
    "cam": "dolly push MS→CU over 8s",
    "light": "overhead practical hard key, warm amber, low-fill deep shadow",
    "style": ["anamorphic", "grain", "muted palette"],
    "snd": {
      "amb": "soft rain bed",
      "sfx": ["distant train hum at 1s"],
      "mx": "low piano enters 2s, resolves final frame"
    }
  },
  "lock": ["stable exposure", "no drift", "consistent coat texture"],
  "exit": "hold 0.8s"
}
```

**Compiled output:**
```
@Image1's character as the subject, placed in @Image2's environment.
Reference @Video1's camera movement. BGM references @Audio1.

Weathered woman, heavy wool coat, rain-slick platform, breath misting.
Stands still, slow turn toward camera.
Dolly push medium shot to tight close-up over 8 seconds.
Overhead practical hard key, warm amber, low-fill deep shadow.
Anamorphic, grain, muted palette.

Sound: soft rain bed. Train hum at 1s. Low piano enters 2s, resolves final frame.
Stable exposure, no drift, consistent coat texture.
Final frame holds 0.8s.
```

---

#### Level 3 — Time-Segmented

```json
{
  "v": "3.0",
  "meta": { "mode": "t2v", "level": 3, "dur": 10, "ar": "16:9", "res": "1080p" },
  "shot": {
    "subj": "young mechanic, grease-stained hands, workshop interior",
    "cam": "handheld tracking, settles to locked CU",
    "light": "red emergency practical key, cool rain spill from door as rim",
    "style": ["naturalistic", "grain"],
    "snd": { "amb": "rain bed", "mx": "silence on last frame" }
  },
  "seg": [
    { "t": "0-3s",  "act": "wipes grease, looks up as fluorescents flicker and die; red lamp activates", "sfx": ["fluorescent buzz", "buzz cut to silence at 2.5s"] },
    { "t": "3-7s",  "act": "walks toward open garage door, rain visible in lamp beam, silhouette fills frame", "cam": "tracking to medium" },
    { "t": "7-10s", "act": "stops, hears something outside, holds perfectly still", "cam": "locked CU", "sfx": ["distant thunder at 8.5s"] }
  ],
  "lock": ["no extra light sources", "rain stays visible at door", "no idle sway"],
  "exit": "hold 0.8s"
}
```

**Compiled output:**
```
Young mechanic, grease-stained hands, workshop interior.

0–3s: wipes grease, looks up as fluorescents flicker and die; red lamp activates.
SFX: fluorescent buzz, cuts to silence at 2.5s.
3–7s: walks toward open garage door, rain visible in lamp beam, silhouette fills frame.
Camera: handheld tracking to medium.
7–10s: stops, hears something outside, holds perfectly still.
Camera: locked close-up. SFX: distant thunder at 8.5s.

Camera overall: handheld tracking, settles to locked close-up.
Light: red emergency practical key, cool rain spill from door as rim.
Style: naturalistic, grain.
Sound: rain bed. Silence on last frame.
No extra light sources, rain stays visible at door, no idle sway.
Final frame holds 0.8s.
```

---

#### Level 4 — Action Choreography

```json
{
  "v": "3.0",
  "meta": { "mode": "r2v", "level": 4, "dur": 6, "ar": "16:9", "res": "1080p" },
  "ref": {
    "char": "@Image1",
    "char_b": "@Image2"
  },
  "shot": {
    "subj": "A: young martial artist, light robe; B: armored warrior, iron gauntlets",
    "cam": "tracking medium, handheld shake on impacts",
    "light": "overcast battlefield, diffused grey, dust-haze fill",
    "style": ["desaturated", "grain"],
    "snd": { "amb": "wind across sand", "mx": "no music" }
  },
  "seg": [
    { "t": "0-0.6s",   "act": "B right heavy punch toward A face, full extension", "cam": "full shot locked", "sfx": ["drum dong", "wind chase"] },
    { "t": "0.6-1.2s", "act": "A double-arm crossguard block, cloth tightens", "cam": "close-up", "sfx": ["impact peng", "cloth snap"] },
    { "t": "1.2-1.8s", "act": "A wrist flip counter-throw, B micro-sway", "cam": "medium", "sfx": ["bone crack", "dust puff"] },
    { "t": "1.8-2.4s", "act": "B shoulder charge into A chest, shockwave ripple visible", "cam": "medium-long", "sfx": ["heavy thud"] },
    { "t": "2.4-3.0s", "act": "A slides back 1m, recovers low stance, dust trail", "cam": "low angle", "sfx": ["scraping ci", "wind settle"] }
  ],
  "lock": ["A and B identities stay distinct", "armor consistency throughout", "weapon shape unchanged under motion"],
  "exit": "hold on recovery stance 0.5s"
}
```

**Compiled output:**
```
Character A references @Image1. Character B references @Image2.

A: young martial artist, light robe. B: armored warrior, iron gauntlets.
Arena: sand-covered ancient battlefield, stone debris.

Shot 1 (0–0.6s): Full shot locked. B right heavy punch toward A face, full extension.
SFX: drum "dong" + wind chase.
Shot 2 (0.6–1.2s): Close-up. A double-arm crossguard block, cloth tightens.
SFX: impact "peng" + cloth snap.
Shot 3 (1.2–1.8s): Medium. A wrist flip counter-throw, B micro-sway.
SFX: bone crack, dust puff.
Shot 4 (1.8–2.4s): Medium-long. B shoulder charge into A chest, shockwave ripple visible.
SFX: heavy thud.
Shot 5 (2.4–3.0s): Low angle. A slides back 1m, recovers low stance, dust trail.
SFX: scraping "ci" + wind settle.

Camera: tracking medium, handheld shake on impacts.
Light: overcast battlefield, diffused grey, dust-haze fill.
Style: desaturated, grain.
Sound: wind across sand. No music.
A and B identities stay distinct. Armor consistency throughout. Weapon shape unchanged under motion.
Hold on recovery stance 0.5s.
```

---

### Compile Function Logic (Pseudocode)

```
function compile(json):

  out = []

  // BLOCK 1: @Tag roles (always first)
  for each key in json.ref:
    out.append( role_phrase(key, json.ref[key]) )

  // BLOCK 2: Subject
  out.append( json.shot.subj )

  // BLOCK 3: Temporal segments OR single action
  if json.seg exists and len > 0:
    for each s in json.seg:
      line = s.t + ": " + s.act
      if s.cam: line += " Camera: " + s.cam
      if s.sfx: line += " SFX: " + join(s.sfx, " + ")
      out.append(line)
  else:
    out.append( json.shot.act )

  // BLOCK 4: Global camera (always present for L2+)
  if json.shot.cam: out.append( "Camera: " + json.shot.cam )

  // BLOCK 5: Light
  if json.shot.light: out.append( "Light: " + json.shot.light )

  // BLOCK 6: Style (join array, max 3)
  if json.shot.style: out.append( join(json.shot.style, ", ") )

  // BLOCK 7: Sound
  snd_parts = []
  if json.shot.snd.amb: snd_parts.append(json.shot.snd.amb)
  for sfx in json.shot.snd.sfx: snd_parts.append(sfx)
  if json.shot.snd.mx: snd_parts.append(json.shot.snd.mx)
  if snd_parts: out.append( "Sound: " + join(snd_parts, ". ") )

  // BLOCK 8: Lock constraints
  if json.lock: out.append( join(json.lock, ", ") )

  // BLOCK 9: Exit
  if json.exit: out.append( json.exit )

  return join(out, "\n")
```

---

### Budget Triage (When Compiled Prompt Is Too Long)

Cut in this strict order. Never skip ahead.

| Cut order | What to remove | Never remove |
|-----------|---------------|--------------|
| 1st | `shot.style` entries beyond first token | `shot.subj` |
| 2nd | `shot.snd.mx` description detail | `shot.act` |
| 3rd | Segment-level `cam` overrides | Global `shot.cam` |
| 4th | `shot.snd.sfx` entries beyond primary | All `seg[].act` |
| 5th | `shot.light` reduced to source only | `lock` array |
| 6th | `ref.bg`, `ref.style` (describe in text) | `ref.char` |

If the compiled prompt is still too long after all 6 cuts: **switch to Level 1 — delete `seg`, replace `shot.act` with one sentence, remove all `ref` except `ref.char`.**

---

## Module 02: Quad-Modal Protocol

### Universal Rules

- One prompt = one clip. Treat it as a shot or short sequence, not a screenplay.
- Prefer one hero subject per shot; two max if interaction is essential.
- If dialogue is present, plan around it — dialogue timing sets shot timing.
- Avoid dense on-screen text; if needed, keep to 1–3 words and accept imperfect typography.

### T2V (Text to Video)

**Best for:** Original worlds, atmosphere, controlled camera/light, scenarios where the model has domain knowledge.

- For known domains (food, brands, sports, common activities): use Level 1–2. Trust the model's built-in knowledge.
- For novel/unusual content: use Level 3–4 with explicit structure.
- Put SUBJECT + ACTION first (the subject anchor).
- Specify camera + timing explicitly.
- Keep environment precise but short.

**Common failures:** generic backgrounds, camera drift, adjective mush.  
**Fix:** shorten, add a named light source, lock camera, reduce adjectives.

### I2V (Image to Video)

**Best for:** Character/environment anchoring, product demos, bringing illustrations to life.

- Use `@Image1 as the first frame` for strong stability.
- Add `@Image2 as the last frame` for maximum control (motion-in-between).
- Describe only the change from the starting image — don't rewrite the entire scene.
- The first frame is your most important creative decision (see Module 06B).

**Common failures:** identity drift, costume drift, background warping.  
**Fix:** `"@Image1's character as the subject, wearing the outfit from @Image1."` Reduce motion. Lock camera.

### V2V (Video to Video)

**Best for:** Camera path transfer, action choreography transfer, style transformation.

**Two distinct operations:**
1. **Reference mode:** `"参考@Video1的运镜"` → generate new content using the reference's technique.
2. **Edit mode:** `"将@Video1中的人物换成..."` → modify the reference directly.

- Explicitly state what to keep and what to change.
- Limit changes to 1–2 per generation. Too many changes = loss of structure.

**Common failures:** change bleeds into everything, loss of structure.  
**Fix:** reduce edits to a single target; keep "what stays" explicit.

### R2V (Multi-Reference)

**Best for:** Professional pipelines requiring separate control of character, scene, camera, rhythm, and audio.

- Each reference gets ONE job. Don't give a single reference two conflicting roles.
- State role assignments before any other prompt content.
- When combining multiple characters from different references, attribute actions clearly.

**Common failures:** blended identities, camera mismatch, conflicting styles.  
**Fix:** simplify reference roles; drop the weakest reference.

---

## Module 03: Camera Language Codex

### Camera Contract (Always Include for Level 2+)

- **Framing:** wide / medium / close-up / extreme close-up / over-shoulder / full body
- **Movement:** locked-off / dolly (push/pull) / pan / tilt / orbit / handheld / crane / tracking
- **Speed:** slow / moderate / fast (or explicit timing: "over 8 seconds")
- **Angle:** eye level / low angle / high angle / bird's eye / Dutch angle

### Reliable Phrasing Library

- `locked-off static camera, no movement`
- `slow dolly push from medium shot to tight close-up over 8 seconds`
- `slow dolly pull back revealing the full environment`
- `slow pan left revealing [new element]`
- `slow tilt up from [foreground] to [sky/background]`
- `slow orbit left around the subject, constant distance`
- `handheld tracking following the subject, subtle shake, not chaotic`
- `rack focus foreground→background at 4 seconds`
- `shallow depth of field, eyes in sharp focus`
- `Hitchcock zoom (dolly out while zooming in)`
- `crane shot rising from ground level to overhead`
- `POV first-person perspective`
- `low angle looking up at the subject`

### Multi-Shot Within One Clip

Use explicit cut markers and restate the whole shot after each cut.

**Pattern:**
```
[Shot 1: Wide] Description. [Cut to: Close-up] Description. [Cut to: Medium] Description.
```
Or: `Shot 1: ... Lens switch. Shot 2: ... Lens switch. Shot 3: ...`

**Rules:**
- **2–3 shots** is the reliable sweet spot for most content.
- Advanced users can push to 4–8 micro-shots for action choreography (see Module 04B), but expect higher failure rates.
- Specify whether sound bridges the cut: `"ambient continues across all shots"` or `"music hits the cut."`

### One-Take (一镜到底) Technique

Seedance 2.0 is particularly strong at continuous one-take shots with spatial transitions.

**Pattern:** Upload 3–5 scene images in sequence + describe a continuous path.

**Example:**  
```
@Image1 @Image2 @Image3 @Image4 @Image5, one continuous tracking shot, following the runner from the street up stairs, through a corridor, onto the rooftop, ending with a city overlook.
```

The model transitions between referenced environments while maintaining spatial continuity. Each image represents a waypoint on the camera path.

**For POV one-takes:**  
```
First-person POV, walking through [environment], camera moves continuously without cuts.
```

### Anti-Drift Camera Locks

If the camera wanders:
- Add `"locked horizon, stable framing, no rolling shutter."`
- Remove extra camera adjectives.
- Choose ONE move only (don't combine pan + orbit + tilt).
- For characters stationary relative to camera (e.g., riding a vehicle): use `CAMERA MOUNTED ON [SUBJECT], LOCKED-ON SHOT, FIXED-TO-ACTOR` to prevent misinterpretation.

---

## Module 03B: Storyboard Reference Technique

### The Nine-Grid Method (九宫格)

Instead of writing complex per-shot descriptions, create a visual storyboard and let the model follow it.

### Workflow

1. **Generate a storyboard image:** Use an image model (Seedream, Nano Banana Pro, etc.) to create a nine-panel grid showing your shot sequence. Include brief text labels if needed.

**Example image-generation prompt for the storyboard:**
```
Create a 3x3 nine-panel storyboard for [scenario]. 
Panel 1: [description]. Panel 2: [description]. ... Panel 9: [description]. 
Professional storyboard illustration style, clear panel divisions.
```

2. **Upload to Seedance:** Upload the storyboard grid as `@Image1` alongside any character/environment reference images.

3. **Write a minimal prompt:**
```
Strictly follow the storyboard sequence from @Image1. [Character from @Image2] performs the actions shown. 
Match lighting and camera angles per panel. Smooth transitions between scenes.
```

### When to Use This

- Complex multi-shot sequences where text description becomes unwieldy.
- Interior walkthroughs (upload floor plan + storyboard panels).
- Action choreography with specific pose references.
- When working with non-filmmakers who can sketch/illustrate but can't write shot lists.

### Key Insight

The model is intelligent enough to read the storyboard's visual information without reproducing the storyboard's layout or text labels in the generated video. It extracts the sequential visual intent.

---

## Module 04: Motion & Temporal Control

### Beat Density

A clip is not a montage. Excessive beat density causes jitter, morphing, and incoherent physics.

**Guidelines for Level 2–3 prompts:**
- **4–6s:** 1 primary change
- **8–10s:** 1–2 changes
- **12–15s:** 2–3 changes (time-segmented)

For Level 4 (action choreography), see Module 04B for adjusted guidelines.

### Timing Language

- **Timestamps:** `0–3s: ... 3–6s: ... 6–8s: ...`
- **Relative:** `motion eases in over 2 seconds, then eases out`
- **Terminal:** `final frame holds for 0.8 seconds`
- **Sequential:** `starts walking slowly, then accelerates into a run while turning left`

**Respect chronological order.** Jumbled temporal descriptions break motion flow. Always describe events in the order they should occur.

### Stillness (Positive Constraints)

- `the subject is still, only subtle breathing`
- `no idle swaying, no camera drift`
- `wind is minimal, only small cloth movement`
- `locked body, only eyes moving`

### Continuity Anchors

- Keep at least one constant: lighting direction, camera height, or subject orientation.
- If motion jitters: reduce simultaneous moving parts. Rain + crowd + handheld + whip pan = stutter.
- For multi-shot: `"maintain character consistency across all shots, same lighting direction."`

---

## Module 04B: Action Choreography Protocol

### Why Action Deserves Its Own Module

Fight scenes, martial arts, and intense physical choreography are the dominant use case driving Seedance 2.0 adoption. The model handles surprisingly dense action when prompted correctly, exceeding the conservative beat-density guidelines of Module 04.

### The Per-Shot Micro-Choreography Approach

For dense action, use numbered camera/shot designators with timestamps, specific hit types, and reaction physics:

```
Shot 1 (00:00.0–00:00.6): Full shot, locked. B throws right heavy punch at A's face. 
SFX: drum hit "dong" + wind chase.

Shot 2 (00:00.6–00:01.2): Close-up. A blocks with crossed arms, guard stance. Cloth wraps tight. 
SFX: impact "peng" + cloth stretch.

Shot 3 (00:01.2–00:01.8): Medium shot. A flips wrist for counter-throw, body micro-sways. 
SFX: ground crack. Bone micro-sound.

Shot 4 (00:01.8–00:02.4): Medium long shot. B shoulder-checks A's chest. 
SFX: red shockwave disperses.
```

### Impact Physics Language

Every hit should specify:
- **Contact type:** punch, kick, block, throw, weapon strike
- **Force direction:** where does the energy go?
- **Reaction physics:** body recoil, stagger, guard break, knockback distance
- **Environmental response:** dust cloud, ground crack, debris scatter, shockwave
- **Sound per impact:** use onomatopoeia or descriptive SFX

### The Grid Method (25宫格)

For maximum choreographic control, create a grid where each cell is one beat:

| Beat | Camera | Action | SFX |
|------|--------|--------|-----|
| 1 | Full shot, locked | B right punch → A face | drum "dong" + wind |
| 2 | Close-up | A crossguard block | impact "peng" |
| 3 | Medium | A wrist flip counter | ground crack |
| ... | ... | ... | ... |

Convert each row to one sentence in the prompt. This method is used by advanced Chinese creators to choreograph 6–10 beats within 5 seconds.

### Multi-Character Fight With Separate References

```
Characters: A references @Image1; B references @Image2.

Choreography: A throws right hook at B's jaw. B ducks, sweeps A's legs. 
A jumps, lands spinning back kick to B's shoulder. B staggers backward 2 steps.

Camera: Medium shot tracking, slight handheld shake on impacts.

Sound: wet impact on each hit, dust puff from ground, heavy breathing between exchanges.
```

### Tips From Practitioners

- Object integrity degrades under high-speed motion. Reinforce weapon/prop consistency: `"weapon shape stays consistent throughout."`
- The model's fight choreography comprehension improves with precision. The more precise the prompt, the better the result.
- Use reference video for overall choreography style + text for specific modifications.

---

## Module 04C: Sequential Extension Protocol

### The Extension Workflow for Long-Form Production

Seedance 2.0 clips max at 15 seconds, but video extension enables theoretically unlimited length.

### Basic Extension

```
Extend @Video1 by [X] seconds. New content: [description of what happens next].
```

Set generation duration to match the extension length (e.g., extend 5 seconds → set duration to 5s).

### Continuity Rules for Extension

1. **Re-upload character reference images** when extending — don't rely solely on the previous clip's last frame. This prevents identity drift ("morphing").
2. Set creativity/hallucination low (if the slider is available, 0.3–0.4) to stay close to the source material.
3. Describe the continuation, not the whole scene over again.
4. Maintain sonic continuity: specify whether music continues, changes, or bridges.

### Forward Extension

To add content BEFORE an existing clip:
```
Extend @Video1 forward by [X] seconds. Preceding content: [description of what comes before].
```

### Bridging Two Clips

To generate a transition between two existing clips:
```
Generate a [X]-second bridge between @Video1 and @Video2. [Description of transition content].
```

### Novel-Text-to-Video Chain

For adapting long-form text (novels, scripts) into sequential video:

1. Generate the first 15s clip from the opening text passage + style reference.
2. Extend with subsequent text:  
   ```
   Extend @Video1 by 15s. Content: [paste next paragraph of novel text].
   ```
3. Repeat, always referencing the previous clip and any character/style anchors.

This technique works because Seedance 2.0 has strong text comprehension. It can parse narrative prose — not just production-formatted prompts — and generate appropriate cinematography.

---

## Module 05: Lighting & Atmosphere

### Always Name a Source

❌ Bad: `"dramatic lighting."`  
✅ Good: `"single overhead practical as hard key, 5600K, deep shadow fill."`

### Replace Vague Light Words With Physical Descriptions

- `window backlight casting long shadows`
- `neon sign as key light, pink and blue`
- `firelight flicker, warm and unstable`
- `overcast diffused daylight, soft shadows`
- `single bare bulb swinging`
- `red emergency lamp as sole light source`

### Core Lighting Parameters

- **Key direction:** camera-left/right, above/below, behind (rim/backlight)
- **Contrast:** low-key (deep shadows) / high-key (bright, minimal shadows)
- **Color temperature:** warm amber / cool blue (simple words work; Kelvin numbers optional)
- **Shadow behavior:** hard-edged / soft wrap / no shadows

### Atmosphere Contracts (Measurable)

- `thin fog catching the backlight`
- `dust motes in a sunbeam`
- `light rain visible in the key light`
- `breath misting in cold air`
- `heat shimmer rising from asphalt`

**If fog becomes a blur:** reduce density, increase backlight specificity, simplify background.

### Light Transitions

For lighting changes within a clip:
```
0–3s: warm golden light. 3–5s: lights flicker and die. 5–end: only red emergency lamp remains.
```

---

## Module 06: Subject & Character Fidelity

### Character Card (Reusable Identity Line)

Write a short, stable identity description and reuse across prompts:
- Age range, build, skin tone, hair style, defining features, wardrobe.

**Example:**  
```
Woman mid-40s, weathered face, dark eyes, short black hair, heavy wool coat, tired but controlled expression.
```

### Consistency Techniques

- Keep the same nouns for the same things across prompts. Don't rename wardrobe.
- One hero subject per shot; two max if interaction is essential.
- If identity drifts: anchor with `@Image1's character as the subject` and reduce motion.
- **360° consistency test:** Generate the same character from multiple angles across several generations. Place results side by side to verify identity stability.

### Hands & Fingers

**If hands are not essential:** frame waist-up or keep hands out of frame.  
**If hands are essential:** specify one simple action only (pick up, place down, open palm). Avoid complex finger articulation.

### Face Stability

- Prefer medium close-up with steady camera for dialogue.
- Avoid rapid head turns or extreme close-ups.
- Re-upload face reference images when extending clips.

---

## Module 06B: First-Frame Art Direction

### Why the First Frame Is Your Most Important Creative Decision

For I2V workflows, the first frame is not just a "starting image" — it is the **primary creative contract**. The model builds everything from this foundation. A well-composed first frame produces dramatically better results than a detailed text prompt with a mediocre reference image.

### Composition Rules for I2V First Frames

1. **Bake the camera angle into the image.** If you want a low-angle shot, compose the first frame from a low angle. Don't fight the reference with contradictory camera instructions.
2. **Bake the lighting direction into the image.** The model will maintain the established lighting. If you want dramatic side-lighting, the first frame must show it.
3. **Pose the character at the START of their motion.** If the character will swing a sword, pose them in the wind-up, not mid-swing.
4. **Keep the background clean and depth-appropriate.** Cluttered backgrounds lead to warping. Simple, depth-separated backgrounds give the model room to animate.
5. **Match aspect ratio.** Generate the first-frame image in the same aspect ratio as your target video.

### What to Put in the Image vs. the Prompt

**In the image:** Character identity, costume, pose, camera angle, lighting direction, environment composition, color palette.

**In the prompt:** Motion (what changes), timing (when), camera movement (how the frame evolves), sound.

### Common First-Frame Mistakes

- ❌ Wrong lighting direction (forces the model to re-light, causing flicker)
- ❌ Character posed mid-action (leaves no room for the prompt's motion description)
- ❌ Background too complex (leads to background morphing during camera movement)
- ❌ Resolution too low (loses detail that the model needs for consistency)

---

## Module 07: Style & Aesthetic Control

### Style Anchors That Work

Anchor style with physical film language, not trend words:

- **Lens feel:** anamorphic, vintage softness, spherical, fisheye
- **Texture:** subtle film grain, digital clean, noise/grain as character
- **Palette:** muted / desaturated / warm highlights / cold shadows / neon-saturated
- **Contrast:** low-key / high-key / deep blacks / crushed shadows

### Render-Engine References as Style Tokens

Render-engine names may function as legitimate style biases in Seedance 2.0, unlike pure filler words. Use them deliberately when you want specific material/lighting looks:

- `"Unreal Engine 5 rendering"` — biases toward game-engine realism, ray-traced reflections, specific subsurface scattering.
- `"Blender render"` — biases toward 3D animation aesthetics.
- `"Octane render"` — biases toward high-end material rendering.

These are not confirmed to work consistently — test and document results. They are most useful when combined with specific material descriptions (Module 11).

**Still avoid:** "8K" alone (empty filler), "masterpiece," "award-winning," "ultra-real" (unmeasurable).

### Style Compression (When Prompt Is Too Long)

Keep only 2–3 style tokens: `"anamorphic feel, subtle grain, muted palette."`

### Animation / Anime Control

Use concrete production descriptors:
- `clean linework, limited shading, 2D animation, motion on twos, smear frames on fast turns`
- `watercolor wash backgrounds, ink outline characters`
- `3D cel-shaded, bold outlines`

Avoid naming studios or series.

### Period / Historical Control

Specify materials and lighting of the era:
- `oil lamp practicals, soot-stained walls, handwoven wool, iron hardware`
- `1970s film stock, warm yellows, faded contrast, wide collars`

### Style Transfer via Reference

The most reliable way to control style is to upload a reference:
- `Match the visual style, color grading, and film texture of @Video1`
- `Apply @Image1's artistic style and color palette to the scene`

The model excels at extracting and replicating: color grade, contrast, film grain, lighting mood, compositional style, and editing rhythm from references.

---

## Module 08: Edge Case Grimoire

### Master Troubleshooting Ladder (Use in Order)

1. Shorten prompt (remove adjectives, keep contracts).
2. Remove conflicts (one camera move, one lighting idea, one primary action).
3. Reduce beat density (fewer changes per second).
4. Lock camera (or simplify to slow dolly only).
5. Anchor subject with @Image reference.
6. Add time segmentation.
7. Switch to Level 1 (minimal intent) and let the model direct.

### Common Failures and Fixes

| Problem | Fix |
|---------|-----|
| **Extra limbs / warped hands** | Reframe hands out of shot; simplify action; specify "hands not visible." |
| **Face melt mid-clip** | Reduce motion; avoid extreme close-up; lock lighting; avoid rapid expression changes; re-upload face reference. |
| **Camera drift / float** | Use "locked-off static camera"; remove "cinematic" filler; specify "no drift, no floating." |
| **Flicker / exposure pumping** | Specify "stable exposure, no flicker"; reduce flickering light sources. |
| **Stutter / jitter motion** | Simplify choreography; remove simultaneous moving elements (rain + crowd + handheld + whip pan = stutter). |
| **Background morphing** | Add environment reference @Image; reduce orbit/pan moves; simplify background description. |
| **Bad text / watermarks** | Avoid on-screen text generation; if required, keep 1–3 words maximum. |
| **Audio desync** | Shorten dialogue; use medium close-up; specify clear pauses; reduce visual complexity. |
| **Identity drift during extension** | Re-upload original character reference images; lower creativity slider; describe continuation, not the whole scene. |
| **Object disappearing under fast motion** | Reinforce object description; add "weapon/prop stays consistent throughout"; reduce motion speed. |
| **Content policy violation** | Remove real-person references, IP names, copyrighted characters. Redesign toward originality. |

---

## Module 08B: Known Platform Behaviors

**LIVING DOCUMENT — Q1 2026**

Record observed behaviors here and update quarterly.

### Current Observations

- The model has strong **"director intelligence"** — for common domains, minimal prompts outperform over-specification.
- Character consistency via @Image reference is remarkably strong, even across lighting changes and camera angles. The model achieves **near-perfect lighting fusion** when placing characters into new environments.
- The model independently selects appropriate camera techniques, shot sizes, and editing rhythms when given freedom (Level 1–2 prompts).
- Fight choreography with per-second specifications works at surprising density (6–8 beats per 5 seconds achievable).
- **Audio emotion can be modified** — the model can make a flat voice reference sound "more excited" when instructed.
- 720p output quality is aesthetically sufficient for most social media and content marketing use cases. Film grain and natural softness at this resolution often look more "real" than artificially sharp upscaled content.
- The model can read and follow novel/prose text directly, generating appropriate cinematography without production-formatted prompts.
- **Object integrity degrades under high-speed motion** (weapons, small props). Explicit reinforcement helps.
- The storyboard-as-reference technique works well — the model extracts sequential visual intent without reproducing the storyboard format.

---

## Module 09: Quality Assurance

### Pre-Render QA Checklist

- [ ] Prompt is structured (subject → action → camera → style → constraints).
- [ ] Appropriate delegation level chosen (Level 1–4).
- [ ] @Tag roles are explicit (each reference has one job).
- [ ] No IP/celebrity/real-person targeting.
- [ ] Camera: framing + movement + timing specified (Level 2+).
- [ ] Light: named source + contrast specified (Level 2+).
- [ ] Motion: beat density appropriate for duration.
- [ ] Exit: final frame holds 0.5–1s (if applicable).
- [ ] Sound: either designed or intentionally delegated.
- [ ] No conflicting instructions (checked for mutual exclusivity).
- [ ] For extensions: character reference images re-uploaded.

### Compression Ladder (When Prompt Feels Too Long)

Cut in this order:
1. Remove filler adjectives ("beautiful," "amazing," "stunning").
2. Collapse environment into one sentence.
3. Reduce style to 2–3 tokens.
4. Reduce sound to ambient + one cue.
5. Remove secondary props/extra characters.
6. Consider switching to a reference-based approach (upload a style reference instead of describing it).

**Never cut:** subject identity, core action, camera timing.

---

## Module 10: Maintenance Protocols

### Versioning

- Increment version when templates or constraints change.
- Keep last-stress-tested quarter and rerun tests each quarter.
- Track platform changes (Dreamina updates, API changes, new features).

### Regression Test Pack (Run After Major Platform Changes)

Generate 8 short clips:

1. **Level 1:** Minimal-intent food/product ad (test director intelligence).
2. **Level 2:** Locked-off portrait dialogue close-up with lip-sync.
3. **Level 2:** Slow dolly push in low-key light.
4. **Level 3:** Orbit move around a static subject.
5. **Level 3:** I2V first+last frame transformation.
6. **Level 3:** V2V camera transfer with one controlled change.
7. **Level 3:** Multi-shot lens switch with sound continuity.
8. **Level 4:** Dense fight choreography (4+ beats in 5 seconds).

**Record:** prompt text, prompt length, delegation level, seed, aspect ratio, pass/fail notes, observed behaviors.

---

## Module 11: CGI Pipeline

### CGI Fails When Materials Are Unspecified

Leading to "plastic sheen."

### Material Contract (Use 2–4 Properties)

- **Base:** metal / painted metal / glass / ceramic / rubber / fabric / wood / stone
- **Roughness:** matte / satin / glossy / mirror
- **Imperfection:** micro-scratches, dust, fingerprints, wear marks, patina
- **Edge behavior:** slightly beveled / razor sharp / rounded / chipped

**Example:** `"brushed aluminum, satin roughness, fine micro-scratches, subtle edge wear."`

### Motion Physics

- Heavy objects accelerate slowly and decelerate slowly.
- Cloth lags behind motion, then catches up.
- Glass reflections shift with camera movement.
- Liquid sloshes with inertia.
- State mass/weight when needed: `"feels heavy, slow inertia."`

---

## Module 12: VFX Integration

### FX Contract (Every Effect Needs These)

- **Source:** where does it originate?
- **Scale:** size relative to subject
- **Behavior:** drift / burst / swirl / dissipate / grow / shrink
- **Interaction:** casts light, casts shadows, affects air, displaces other elements
- **Duration:** when does it start, peak, and fade?

### Examples

```
Sparks burst from the sword impact point, arc downward with gravity, cool and fade within 1 second.
```

```
Smoke rises from the crater, curls in the wind, thins as it rises; backlight makes edges glow.
```

### Compositing Language

- `"Foreground subject stays clean, FX behind subject only."`
- `"Light from the explosion briefly overexposes the frame, then recovers in 0.3s."`
- `"Dust settles on the character's shoulders after the debris cloud passes."`

---

## Module 12B: Energy, Magic & Destruction VFX

### Energy Effects Vocabulary

**Beams/rays:**
```
concentrated energy beam, [color], fired from [source] to [target], [width], illuminates surrounding surfaces
```

**Auras/fields:**
```
glowing aura surrounds the character, [color], pulsing with breath rhythm, casting colored light on nearby surfaces
```

**Shields/barriers:**
```
translucent energy barrier, hexagonal pattern, ripples on impact, [color]
```

**Explosions:**
```
energy collision produces [size] explosion, shockwave expands outward, [debris type] launched radially
```

### Particle System Language

- **Density:** `"sparse / moderate / dense particle field"`
- **Emission:** `"particles emit from [source point], [direction], [speed]"`
- **Scale with force:** `"particle density increases with swing speed, up to [threshold]"`
- **Color temperature:** `"cold blue particles / hot orange embers / electric white sparks"`
- **Lifecycle:** `"particles spawn bright, dim over 0.5s, fade completely"`

### Destruction Physics

- **Cracking:** `"ground cracks radiate from impact point, [pattern: spider-web / linear / concentric]"`
- **Shattering:** `"stone wall shatters into fragments, large chunks fall with gravity, small debris sprays outward"`
- **Debris trajectory:** `"fragments launch upward from impact, arc with gravity, scatter across [radius]"`
- **Dust/smoke:** `"dust cloud erupts from destruction, [color], [density], settles over [time]"`
- **Shockwave:** `"visible shockwave distorts air, expands at [speed], rustles loose objects within [radius]"`

### Combining Multiple VFX Systems

When multiple effects interact, specify the hierarchy:

```
Primary: sword slash emits ice-blue particle trail, 360° spiral per swing.
Secondary: particles scatter on impact with enemy, burst into smaller sparks.
Tertiary: ground freezes where particles land, ice crystals spreading.
Environment: cold mist rises from frozen ground, backlit by the blue glow.
```

---

## Module 13: Audio & Sonic Design

### Seedance 2.0 Generates Audio and Video Jointly

Audio descriptions influence pacing and cut feel.

### Sound Layer Structure

- **Ambient bed:** continuous environmental sound
- **Foreground SFX:** 1–2 event-locked sounds
- **Music cue:** entry time + arc (rising/falling/steady)
- **Silence design:** where absence matters

### Compact Syntax

```
Sound: rain bed + distant train hum. SFX: chess piece click at 2s. 
Music: low piano note enters at 3s, resolves on last frame. Silence holds for final 0.5s.
```

### Dialogue and Lip-Sync

- Short lines only. Long dialogue reduces visual stability.
- Put dialogue in quotes: `Character says: "We leave at dawn."`
- Specify framing: `medium close-up, locked-off camera.`
- Specify pauses: `"brief pause at 2s."`
- Lip-sync is phoneme-accurate in multiple languages.

### Mix Intent

- **Dialogue scenes:** `"dialogue clean and prominent, music low, ambient subtle."`
- **Music-driven:** `"music leads, ambient secondary, no dialogue."`
- **SFX-driven:** `"environmental sounds prominent, no music."`

---

## Module 13B: Advanced Audio Techniques

### Voice Reference and Cloning

Upload a video or audio clip and Seedance adopts the speaker's voice timbre:

```
Voice timbre references @Audio1. Character speaks with this voice quality.
```

Or from a video reference:
```
Narration voice references @Video1's speaker.
```

### Emotion Modification

The model can modify the emotional delivery of a voice reference:

```
Voice references @Audio1, but make the delivery more excited and energetic.
```

This actually works — the model preserves the voice identity while adjusting emotional expression.

### Multi-Language Generation

Characters can speak Chinese, English, Spanish, Korean, and other languages with appropriate lip-sync:

```
Character speaks in [target language]: "[dialogue text]."
```

Dialect support has been confirmed for regional Chinese dialects (e.g., Sichuan dialect).

### Multi-Character Dialogue

Multiple characters with distinct voices in one generation:

```
Character A (deep male voice) says: "..." Character B (high female voice) responds: "..."
```

### Beat-Sync / Music Scoring (卡点)

For music-synced visual editing:

1. Upload multiple scene images + one music reference video.
2. Write:
```
@Image1 through @Image7 are scene images. Reference @Video1's rhythm and beat structure. 
Cut scene transitions on downbeats. Characters move with energy matching the music tempo.
```

The model aligns visual cuts and motion beats to the musical rhythm.

### Sound-Driven Timing

Use audio cues to anchor visual events:

```
Sound: thunder crack at 3s. Visual: lightning illuminates the scene exactly at the thunder crack. 
Character flinches at the sound.
```

This technique uses the audio description to drive visual choreography rather than the other way around.

### Impact Sound Layering (For Fight Scenes)

Each hit should have layered sound:

```
SFX per impact: wet thud (contact) + bone crack undertone (damage) + dust puff whoosh (environmental response) + brief silence (recovery).
```

Use phonetic/onomatopoeic descriptions for specific sonic textures: `"heavy drum 'dong'"`, `"metallic ring 'clang'"`, `"scraping 'ci'"`, `"explosive 'boom'."`

---

## Module 14: Final Director's Self-Check

### Before Generating, Complete This Sentence:

> "This shot makes the audience feel **[EMOTION]** by showing **[SUBJECT]** undergoing **[TRANSFORMATION]** through **[ACTION]**, captured with **[CAMERA]** under **[LIGHT]**, in **[STYLE]**, with **[SOUND]**, at delegation Level **[1/2/3/4]**."

If the sentence cannot be completed, the shot is not directed yet.

### Then Verify:

- [ ] Is the delegation level appropriate? (Am I over-specifying something the model knows?)
- [ ] Are my @Tag roles explicit and non-conflicting?
- [ ] Is my prompt structured (subject → action → camera → style → constraints)?
- [ ] Have I checked for mutually exclusive instructions?

---

## Module 15: Pipeline Integration

### ComfyUI Workflows

Advanced users can orchestrate Seedance 2.0 via ComfyUI nodes (when available) for:
- Pre-processing reference images (upscaling, relighting, pose correction)
- Batch generation with parameter sweeps
- Post-processing (frame interpolation, color grading, compositing)
- Multi-reference assembly pipelines

### Volcengine API

The Seedance 2.0 API (model string: `Doubao-Seedance-2.0`) supports full multi-modal input programmatically.

**Key API considerations:**
- All reference capabilities (images, videos, audio) are available via API.
- The API may have different text length limits than the Dreamina web UI — test and document.
- API access enables Agent-based automation pipelines.

### Post-Processing Pipeline

Raw Seedance output benefits from post-processing:

1. **Upscaling:** AI upscalers (specialized for AI-generated video faces) can bring 720p to 4K while preserving identity. Generic upscalers may distort AI faces.
2. **Frame interpolation:** Smooths motion for higher effective frame rate.
3. **Color grading:** Professional color correction for broadcast/cinema standards.
4. **Compositing:** Multiple Seedance clips can be composited for complex scenes.
5. **Metadata cleaning:** Remove AI generation metadata for commercial white-label use.

### Agent Automation Patterns

Seedance 2.0 + API enables automated content pipelines:

- **Product promo agent:** Product update → screenshot → image model → Seedance → final video.
- **Talking-head agent:** News feed → script → TTS audio → character image → Seedance → video podcast.
- **Novel-to-series agent:** Novel text → chapter splitting → sequential Seedance extensions → compiled episode.

---

## Module 16: Genre Recipe Book

### Recipe 1 — Product / E-Commerce Ad

**Delegation level:** 1–2  
**References:** Product images (2–3 angles), optional music reference

**Template:**
```
Commercially showcase @Image1's [product], referencing @Image2 for side view and @Image3 for material texture detail. 
Display all product details across multiple angles. Background music: grand and atmospheric.
```

**Tips:** The model knows how to shoot products commercially. Trust its instinct for rotation, close-ups, and material highlighting.

---

### Recipe 2 — Fight / Martial Arts Scene

**Delegation level:** 4  
**References:** Character A image, Character B image, optional choreography reference video

**Template:**
```
Characters: A @Image1, B @Image2.
Fight scene on [environment], [ground type].

Shot 1 (0–1.5s): [Camera], [Action A→B], [SFX].
Shot 2 (1.5–3s): [Camera], [Reaction B], [Counter], [SFX].
Shot 3 (3–5s): [Camera], [Climax exchange], [SFX].

Camera: medium shot tracking, slight handheld shake on impacts.
Sound: [impact sounds], [ambient], [music cue if any].

@tips: reinforce weapon/prop consistency under fast motion.
```

---

### Recipe 3 — Brand / Corporate Film

**Delegation level:** 1  
**References:** Optional brand imagery, optional voice reference

**Template:**
```
Generate a [duration]-second brand film about [brand/product description], capturing its core identity and values. 
Pay attention to shot arrangement, pacing, and appropriate music.
```

**Tips:** For well-known brands, the model understands brand DNA. For unknown brands, add 1–2 sentences describing the brand's tone and aesthetic.

---

### Recipe 4 — Atmospheric / Mood Piece

**Delegation level:** 2  
**References:** One environment/mood reference image

**Template:**
```
@Image1 as the first frame. [Subject] stands/sits [where], [one subtle action]. 
Slow dolly [direction] over [duration]. [Named light source], [contrast type], [atmosphere detail]. 
[One style anchor]. Sound: [ambient bed], [one foreground SFX], [music or silence].
```

---

### Recipe 5 — Dialogue / Character Scene

**Delegation level:** 2–3  
**References:** Character face image, optional scene image

**Template:**
```
@Image1's character as the subject. Medium close-up, locked-off camera.
Character says: "[Short dialogue line]."
Phoneme-accurate lip-sync. [Expression change description].
Light: [named source], [mood]. Style: [anchor].
Sound: dialogue clean and prominent, ambient low.
```

---

### Recipe 6 — One-Take Spatial Journey

**Delegation level:** 2  
**References:** 3–5 scene/environment images in sequence

**Template:**
```
@Image1 @Image2 @Image3 @Image4 @Image5, one continuous tracking shot. 
[Camera follows subject] from [start] through [waypoint 1], [waypoint 2], [waypoint 3], ending at [destination]. 
Maintain spatial continuity, no cuts. Natural lighting transitions between spaces. 
Sound: footsteps + ambient shift per environment.
```

---

### Recipe 7 — Music Video / Beat-Sync Edit

**Delegation level:** 2–3  
**References:** Multiple scene/character images + music reference video

**Template:**
```
@Image1 through @Image6 are scene images. @Video1 provides rhythm and beat reference. 
Cut scene transitions on musical downbeats. Characters have dynamic energy matching the tempo. 
Visual style matches @Video1's color grading. Beat-sync all major transitions.
```

---

### Recipe 8 — Novel / Story Adaptation

**Delegation level:** 1–2  
**References:** Style reference video (optional), character reference images (optional)

**Template:**
```
[Optional: Match the visual style and animation quality of @Video1.]
[Optional: Character appearance references @Image1.]

Generate cinematic animation from the following story text:

[Paste novel/story paragraph directly.]
```

**Tips:** The model parses narrative prose and generates appropriate cinematography. For style consistency across multiple extensions, always include the same style reference.

---

### Recipe 9 — Interior / Architecture Walkthrough

**Delegation level:** 2  
**References:** Floor plan image + nine-grid storyboard of rooms

**Template:**
```
Reference @Image1 (floor plan) for spatial layout and @Image2 (storyboard) for room sequence. 
Generate an immersive walkthrough video following a natural viewing path through each room. 
Smooth transitions between spaces. Natural light variations. Material textures visible. Warm atmospheric BGM.
```

---

### Recipe 10 — Action Transfer (Real Video → Fantasy)

**Delegation level:** 3  
**References:** Self-recorded action video + character face image

**Template:**
```
@Image1's character performs the exact actions from @Video1. Scene: [fantasy/sci-fi environment]. 
Maintain @Video1's motion and camera relationship exactly. Add [VFX: dragons/magic/explosions] to the environment. 
Camera mounted on character, locked-on shot.
SFX: [environment-appropriate sounds].
```

**Tips:** For characters stationary relative to camera (riding/flying), use: `"CAMERA MOUNTED ON [SUBJECT], LOCKED-ON SHOT, FIXED-TO-ACTOR."`

---

## Appendix A: Compact Prompt Examples

### Example 1 — Level 1 (Minimal Intent, 14 words)

```
Generate an elegant premium sushi restaurant ad. Pay attention to shot arrangement and pacing.
```

---

### Example 2 — Level 2 (Guided Direction, ~60 words)

```
@Image1's character as the subject, placed in @Image2's environment. Reference @Video1's camera movement throughout. 
BGM references @Audio1. A weathered woman in a heavy wool coat stands alone on a rain-slick platform, breath misting. 
Slow dolly push mid-shot to tight close-up over 8s. Single overhead practical as hard key, low-key contrast. 
Anamorphic feel, subtle grain. Sound: soft rain bed, distant train hum; low piano note enters at 2s.
```

---

### Example 3 — Level 3 (Time-Segmented, ~90 words)

```
A young mechanic wipes grease from her hands and looks up as the workshop power dies. 
0–3s: fluorescent lights buzz, then flicker out; only a red emergency lamp remains. 
3–7s: she walks toward the open garage door, rain visible in the lamp beam; her silhouette fills the frame. 
7–10s: she stops, hears something outside, holds still. 
Camera: handheld tracking, settles into locked close-up; final frame holds 0.8s. 
Light: red practical key, cool rain spill from outside as rim. 
Sound: rain bed, fluorescent buzz cut at blackout, distant thunder at 6s, silence on last frame.
```

---

### Example 4 — Level 4 (Action Choreography, ~150 words)

```
Characters: A @Image1 (young martial artist), B @Image2 (armored warrior).
Arena: sand-covered ancient battlefield, stone debris.

Shot 1 (0–0.6s): Full shot, locked. B heavy right punch toward A's face. SFX: drum "dong" + wind whoosh.
Shot 2 (0.6–1.2s): Close-up. A double-arm crossguard block. Cloth tightens. SFX: impact "peng" + cloth snap.
Shot 3 (1.2–1.8s): Medium. A wrist flip counter-throw. B's body micro-sway. SFX: bone crack, ground dust.
Shot 4 (1.8–2.4s): Medium-long. B shoulder charge into A's chest. SFX: heavy thud, shockwave ripple.
Shot 5 (2.4–3.0s): Low angle. A slides back, recovers stance. Dust trail. SFX: scraping "ci", wind settle.

Camera: tracking with slight handheld shake on impacts.
Sound: combat ambient, no music. Heavy breathing between exchanges.

@tips: weapon and armor consistency critical under fast motion.
```

---

### Example 5 — Novel Text Direct Input (~80 words)

```
Match @Video1's animation style and color palette throughout.
Character appearance references @Image1.

Generate cinematic animation from this passage:

The third arrow left the mountain. A point of light leaped from the master's body, attaching itself to the blade, 
flying by sword-flight through the sky. The third arrow arrived at the crumbling mountain in an instant. 
The priest flicked his fingers, releasing two tadpole-shaped lights—one black, one white—spiraling together, 
forming a tai chi symbol, which expanded into an octagonal bronze mirror. The mirror flew out, releasing divine light, 
blocking the giant arrow's path.
```

---

## Appendix C: Quick Reference Card

### Before You Start

1. Choose delegation level (1–4).
2. Select entry mode (First/Last Frame or Universal Reference).
3. Prepare reference assets (max 12 files).
4. Set duration, aspect ratio, resolution.

### Prompt Structure

```
[@Tag roles]. SUBJECT anchor. ACTION (primary verb + timing). 
CAMERA (framing + movement + speed). STYLE (1–3 tokens). 
CONSTRAINTS (consistency + avoidance). SOUND (ambient + SFX + music).
```

### Emergency Fixes

| Problem | Solution |
|---------|----------|
| Output too chaotic | Shorten prompt, lock camera, reduce beat density |
| Character drifting | Add @Image reference, reduce motion |
| Camera wandering | "locked-off static camera, no movement" |
| Background morphing | Add environment @Image, reduce camera moves |
| Audio desynced | Shorten dialogue, use medium close-up |
| Content blocked | Remove real faces, remove IP names, redesign original |

### Extension Formula

```
Extend @Video1 by [X]s. [Re-upload character @Image]. 
New content: [description]. Set generation duration to [X]s.
```

---

## Appendix D: Chinese Cinematic & Photography Vocabulary

The model is trained heavily on Chinese-language film production data. Using precise Chinese terminology — or knowing its English equivalent — unlocks more accurate, production-grade results. This appendix is the complete bilingual glossary for Seedance 2.0 directing.

**How to use:** Chinese terms can be used directly in prompts (they carry higher semantic weight). English equivalents are provided for cross-reference and for English-language prompts.

---

### D.1 景别 — Shot Sizes

| Chinese | Pinyin | English | Description |
|---------|--------|---------|-------------|
| 大远景 | dà yuǎnjǐng | Extreme wide shot (EWS) | Vast landscape; subject is tiny or absent |
| 远景 | yuǎnjǐng | Wide shot (WS) / Establishing shot | Full environment visible, subject small |
| 全景 | quánjǐng | Full shot (FS) | Subject head-to-toe, environment present |
| 中景 | zhōngjǐng | Medium shot (MS) | Waist-up; conversational distance |
| 中近景 | zhōng jìnjǐng | Medium close-up (MCU) | Chest-up; most common for dialogue |
| 近景 | jìnjǐng | Close-up (CU) | Face or key object; emotional intensity |
| 特写 | tèxiě | Close-up / Detail shot | Single feature: eye, hand, lip |
| 大特写 | dà tèxiě | Extreme close-up (ECU) | Pore-level detail; extreme emotional emphasis |
| 过肩镜头 | guò jiān jìntóu | Over-the-shoulder (OTS) | POV from behind one character facing another |
| 双人镜头 | shuāng rén jìntóu | Two-shot | Both subjects in frame, equally weighted |
| 插入镜头 | chārù jìntóu | Insert shot | Cutaway to detail (clock, object, reaction) |
| 空镜头 | kōng jìntóu | Cutaway / B-roll | No main subject; environment or object only |
| 主观镜头 | zhǔguān jìntóu | POV shot | Camera = character's eyes |
| 客观镜头 | kèguān jìntóu | Objective shot | Neutral third-person observation |

---

### D.2 运镜 — Camera Movements

| Chinese | Pinyin | English | Prompt Usage |
|---------|--------|---------|--------------|
| 推镜头 | tuī jìntóu | Dolly push / Push in | Camera moves toward subject |
| 拉镜头 | lā jìntóu | Dolly pull / Pull back | Camera moves away; reveals environment |
| 摇镜头 | yáo jìntóu | Pan | Horizontal pivot on fixed axis |
| 移镜头 | yí jìntóu | Tracking / Lateral move | Camera translates sideways |
| 跟镜头 | gēn jìntóu | Follow shot | Camera follows moving subject |
| 环绕镜头 | huánrào jìntóu | Orbit / Arc shot | Camera circles subject |
| 升降镜头 | shēngjiàng jìntóu | Crane shot | Vertical rise or descent |
| 手持镜头 | shǒuchí jìntóu | Handheld | Natural shake; documentary feel |
| 稳定器镜头 | wěndìngqì jìntóu | Gimbal / Steadicam | Smooth floating movement |
| 甩镜头 | shuǎi jìntóu | Whip pan | Fast pan creating motion blur |
| 一镜到底 | yī jìng dào dǐ | One-take / Oner | Continuous shot without cuts |
| 变焦推拉 | biànjiāo tuīlā | Hitchcock zoom / Dolly zoom | Zoom + dolly simultaneously (vertigo effect) |
| 俯拍 | fǔ pāi | High angle / Top-down | Camera looks down on subject |
| 仰拍 | yǎng pāi | Low angle | Camera looks up at subject |
| 鸟瞰 | niǎokàn | Bird's eye / Overhead | Directly overhead, 90° down |
| 斜角镜头 | xié jiǎo jìntóu | Dutch angle / Canted frame | Tilted frame; disorientation, tension |
| 过肩跟拍 | guò jiān gēn pāi | Over-shoulder tracking | Follows subject from behind at shoulder height |

---

### D.3 镜头光学 — Lens & Optics

| Chinese | Pinyin | English | Notes |
|---------|--------|---------|-------|
| 焦距 | jiāojù | Focal length | Short = wide angle; long = telephoto |
| 广角镜头 | guǎngjiǎo jìntóu | Wide-angle lens | Distorts perspective; exaggerates space |
| 长焦镜头 | chángjiāo jìntóu | Telephoto lens | Compresses distance; isolates subject |
| 标准镜头 | biāozhǔn jìntóu | Standard lens (~50mm) | Closest to human eye perception |
| 变形宽银幕 | biànxíng kuān yínmù | Anamorphic | Oval bokeh, horizontal lens flares |
| 鱼眼镜头 | yúyǎn jìntóu | Fisheye lens | Extreme wide, spherical distortion |
| 景深 | jǐngshēn | Depth of field (DOF) | Range of sharp focus |
| 浅景深 | qiǎn jǐngshēn | Shallow DOF | Soft background; subject isolated |
| 深景深 | shēn jǐngshēn | Deep DOF | Everything in focus |
| 焦外虚化 | jiāo wài xūhuà | Bokeh | Out-of-focus blur quality |
| 拉焦 | lā jiāo | Rack focus | Focus shifts between planes during shot |
| 追焦 | zhuī jiāo | Follow focus | Focus tracks moving subject |
| 失焦 | shī jiāo | Out of focus / Defocus | Intentional blur; dreamlike, disoriented |
| 镜头眩光 | jìntóu xuànguāng | Lens flare | Light artifact; can be stylistic |
| 色差 | sèchā | Chromatic aberration | Color fringing on high-contrast edges |

---

### D.4 构图法 — Composition Techniques

| Chinese | Pinyin | English | Usage |
|---------|--------|---------|-------|
| 黄金分割 | huángjīn fēngē | Golden ratio | Compositional harmony; ~1.618 ratio |
| 三分法 | sānfēnfǎ | Rule of thirds | Subject on 1/3 grid intersections |
| 对称构图 | duìchèn gòutú | Symmetrical composition | Mirror balance; formality, tension |
| 引导线 | yǐndǎo xiàn | Leading lines | Lines that direct gaze to subject |
| 框架构图 | kuàngjià gòutú | Frame within a frame | Doorways, windows framing subject |
| 负空间 | fù kōngjiān | Negative space | Empty area emphasizing subject |
| 前景叠加 | qiánjǐng diéjiā | Foreground layering | Depth via near/far elements |
| 纵深感 | zòngshēn gǎn | Depth cue | Perspectival distance in frame |
| 中心构图 | zhōngxīn gòutú | Center composition | Subject at frame center; stable, commanding |
| 对角线构图 | duìjiǎoxiàn gòutú | Diagonal composition | Dynamic energy; instability, motion |
| 留白 | liúbái | Empty space / Ma | Intentional void; minimalism, breathing room |
| 层次感 | céngcì gǎn | Layering / Depth staging | Foreground / midground / background separation |

---

### D.5 灯光术语 — Lighting Terminology

| Chinese | Pinyin | English | Notes |
|---------|--------|---------|-------|
| 主光 | zhǔ guāng | Key light | Primary, dominant light source |
| 辅光 | fǔ guāng | Fill light | Softens shadows from key light |
| 轮廓光 | lúnkuò guāng | Rim light / Back light | Edge glow separating subject from BG |
| 背景光 | bèijǐng guāng | Background light | Illuminates background independently |
| 顶光 | dǐng guāng | Top light / Overhead | Dramatic; hollows face |
| 底光 | dǐ guāng | Under light / Bottom light | Eerie, horror; illuminates from below |
| 侧光 | cè guāng | Side light | Half-face lit; dramatic split |
| 逆光 | nì guāng | Backlight / Contre-jour | Subject silhouetted or rimmed |
| 散射光 | sǎnshè guāng | Diffused light | Soft, shadowless; overcast daylight |
| 硬光 | yìng guāng | Hard light | Sharp-edged shadows; directional |
| 软光 | ruǎn guāng | Soft light | Gentle shadows; flattering |
| 自然光 | zìrán guāng | Natural light | Sunlight, daylight, practical sources |
| 人工光 | réngōng guāng | Artificial light | Studio lights, practical lamps |
| 实景灯光 | shíjǐng dēngguāng | Practical light | Light source visible in frame (lamp, candle) |
| 色温 | sèwēn | Color temperature | Kelvin; warm (~3200K) to cool (~6500K) |
| 暖调 | nuǎn diào | Warm tone | Amber, gold, orange; intimacy |
| 冷调 | lěng diào | Cool tone | Blue, grey, silver; distance, tension |
| 高调布光 | gāodiào bùguāng | High-key lighting | Bright, low-contrast; cheerful, commercial |
| 低调布光 | dīdiào bùguāng | Low-key lighting | Dark, high-contrast; mystery, drama |
| 丁达尔效应 | dīng dá'ěr xiàoyìng | Tyndall effect / God rays | Light beams through particles (fog, dust) |
| 光比 | guāng bǐ | Lighting ratio | Key-to-fill contrast ratio |

---

### D.6 色彩控制 — Color & Tone Control

| Chinese | Pinyin | English | Prompt Usage |
|---------|--------|---------|--------------|
| 色调 | sèdiào | Color tone / Hue | Overall color character of the image |
| 饱和度 | bǎohédù | Saturation | Richness of color; desaturated = muted |
| 对比度 | duìbǐdù | Contrast | Light-to-dark range |
| 曝光 | bàoguāng | Exposure | Overall brightness |
| 过曝 | guò bào | Overexposed | Blown-out highlights |
| 欠曝 | qiàn bào | Underexposed | Crushed shadows, dark image |
| 色彩分级 | sècǎi fēnjí | Color grading | Post-production color treatment |
| 电影感色调 | diànyǐng gǎn sèdiào | Cinematic color grade | Teal-and-orange or film-stock look |
| 复古色调 | fùgǔ sèdiào | Vintage / Retro grade | Faded, lifted blacks, warm highlights |
| 黑白 | hēibái | Black and white | Monochrome; timeless, stark |
| 高对比黑白 | gāo duìbǐ hēibái | High-contrast B&W | Deep blacks, bright whites, no mid-tones |
| 青橙色调 | qīng chéng sèdiào | Teal and orange | Hollywood blockbuster standard grade |
| 胶片颗粒 | jiāopiàn kēlì | Film grain | Analog texture; reduces digital harshness |
| 晕影 | yūnyǐng | Vignette | Darkened edges; focus to center |
| 色调映射 | sèdiào yìngshè | Tone mapping | HDR to SDR compression; controls clipping |
| 褪色 | tuìsè | Faded / Desaturated | Low saturation, lifted blacks; nostalgic |

---

### D.7 时间与运动 — Time, Pacing & Motion

| Chinese | Pinyin | English | Notes |
|---------|--------|---------|-------|
| 升格 | shēnggé | Slow motion / Overcranking | High frame rate; smooth, graceful |
| 降格 | jiànggé | Undercranking / Fast motion | Low frame rate; frantic, comedic |
| 正常速度 | zhèngcháng sùdù | Normal speed | 24/25/30fps |
| 极限慢动作 | jíxiàn màn dòngzuò | Ultra slow-motion | 120fps+; impact detail, drop, splash |
| 定格 | dìnggé | Freeze frame | Motion stops; emphasis |
| 延时摄影 | yánshí shèyǐng | Time-lapse | Compressed time; clouds, city, growth |
| 流光摄影 | liúguāng shèyǐng | Long exposure light trails | Light streaks; traffic, stars |
| 卡点 | kǎ diǎn | Beat-sync | Visual cuts locked to music beats |
| 转场 | zhuǎnchǎng | Transition / Scene change | Cut, dissolve, wipe, match cut |
| 硬切 | yìng qiē | Hard cut | Abrupt direct cut between shots |
| 溶解 | róngjiě | Dissolve / Cross-fade | Gradual overlap between shots |
| 叠化 | dié huà | Superimpose / Double exposure | Two images overlaid |
| 闪白 | shǎn bái | Flash cut / White flash | Sudden white-out; shock, impact |
| 闪黑 | shǎn hēi | Black flash | Sudden black-out; cut to darkness |
| 运动模糊 | yùndòng móhú | Motion blur | Trailing smear on fast movement |
| 惯性 | guànxìng | Inertia | Physics of heavy objects |
| 缓入缓出 | huǎn rù huǎn chū | Ease in / Ease out | Smooth acceleration and deceleration |
| 节奏 | jiézòu | Rhythm / Pacing | Tempo of cuts and motion |
| 张力 | zhānglì | Tension | Narrative tightening before release |

---

### D.8 音频术语 — Audio & Sound Design

| Chinese | Pinyin | English | Notes |
|---------|--------|---------|-------|
| 音效 | yīnxiào | Sound effects (SFX) | Event-locked non-music sounds |
| 环境音 | huánjìng yīn | Ambient sound / Atmos | Continuous background soundscape |
| 配乐 | pèiyuè | Score / Background music (BGM) | Composed or selected music track |
| 对白 | duìbái | Dialogue | Character speech |
| 独白 | dúbái | Monologue / Voiceover | Single speaker; internal or narration |
| 旁白 | pángbái | Narration / Voice-over (VO) | Off-screen narrator |
| 音画同步 | yīn huà tóngbù | Audio-visual sync | Sound locked to visual event |
| 音画对位 | yīn huà duìwèi | Audio-visual counterpoint | Sound contrasts with image meaning |
| 嘴形同步 | zuǐxíng tóngbù | Lip sync | Mouth movement matches phonemes |
| 音调 | yīndiào | Pitch / Tone | High/low frequency of voice or SFX |
| 音量 | yīnliàng | Volume / Level | Loudness |
| 混音 | hùnyīn | Audio mix | Balancing all sound layers |
| 主音轨 | zhǔ yīnguǐ | Main audio track | Dominant sound layer |
| 声景 | shēngjǐng | Soundscape | Full sonic environment of a scene |
| 静默 | jìngmò | Silence | Intentional absence of sound |
| 回声 | huíshēng | Echo / Reverb | Spatial reflection of sound |
| 节拍 | jiépāi | Beat | Rhythmic pulse in music |
| 低频 | dīpín | Bass / Low frequency | Deep rumble, weight, impact |
| 音色 | yīnsè | Timbre / Tone color | Unique character of a voice or instrument |
| 拟音 | nǐyīn | Foley | Recorded SFX synced to physical action |
| 现场音 | xiànchǎng yīn | Location sound / Diegetic | Sound that exists within the story world |
| 非现场音 | fēi xiànchǎng yīn | Non-diegetic | Sound only audience hears (score, VO) |

---

### D.9 叙事结构 — Narrative & Story Structure

| Chinese | Pinyin | English | Notes |
|---------|--------|---------|-------|
| 分镜 | fēnjìng | Shot breakdown / Storyboard | Pre-planned shot sequence |
| 故事板 | gùshì bǎn | Storyboard | Visual sequence of planned shots |
| 场景 | chǎngjǐng | Scene | Single location/time story unit |
| 段落 | duànluò | Sequence | Group of scenes with unified purpose |
| 开篇 | kāipiān | Opening / Exposition | Establishes world and character |
| 高潮 | gāocháo | Climax | Peak tension or action point |
| 转折 | zhuǎnzhé | Plot twist / Turn | Unexpected narrative direction change |
| 结局 | jiéjú | Resolution / Ending | Final narrative state |
| 悬念 | xuánniàn | Suspense | Withheld information creating tension |
| 伏笔 | fúbǐ | Foreshadowing | Early hint of later event |
| 蒙太奇 | méngtàiqí | Montage | Sequence of images creating new meaning |
| 平行剪辑 | píngxíng jiǎnjí | Parallel editing / Cross-cutting | Alternating between simultaneous events |
| 主观视角 | zhǔguān shìjiǎo | Subjective POV | Camera = character's perception |
| 客观视角 | kèguān shìjiǎo | Objective POV | Neutral third-person observation |
| 视点 | shìdiǎn | Point of view (POV) | Whose perspective the shot represents |
| 情绪弧线 | qínxù hūxiàn | Emotional arc | Character's emotional journey over time |

---

### D.10 特效与视效 — VFX & Visual Effects

| Chinese | Pinyin | English | Notes |
|---------|--------|---------|-------|
| 特效 | tèxiào | Special effects (SFX/VFX) | Any non-realistic visual element |
| 视觉特效 | shìjué tèxiào | Visual effects (VFX) | Post-production digital effects |
| 粒子效果 | lìzǐ xiàoguǒ | Particle effects | Sparks, dust, smoke, magic |
| 冲击波 | chōngjí bō | Shockwave | Expanding pressure wave from impact |
| 能量光柱 | néngliàng guāngzhù | Energy beam / Light pillar | Concentrated directed energy effect |
| 光晕 | guāngyùn | Glow / Halo | Soft light emanating from source |
| 爆炸 | bàozhà | Explosion | Detonation with shockwave and debris |
| 烟雾 | yānwù | Smoke / Fog | Volumetric atmospheric effect |
| 火焰 | huǒyàn | Fire / Flame | Combustion VFX |
| 碎片 | suìpiàn | Debris / Fragments | Broken object particles |
| 地面龟裂 | dìmiàn guīliè | Ground crack | Impact fracture spreading across surface |
| 残影 | cányǐng | Motion trail / After-image | Ghosting trail behind fast movement |
| 电弧 | diànhú | Electric arc | Lightning/electricity VFX |
| 冰晶 | bīngjīng | Ice crystal | Frost / ice formation effect |
| 合成 | héchéng | Compositing | Combining multiple visual elements |
| 绿幕 | lǜmù | Green screen / Chroma key | Background replacement technique |
| 数字替身 | shùzì tìshēn | Digital double | CGI copy of a character |

---

### D.11 动作与武打 — Action & Fight Choreography

| Chinese | Pinyin | English | Notes |
|---------|--------|---------|-------|
| 武打 | wǔdǎ | Martial arts / Fight choreography | Choreographed combat sequences |
| 招式 | zhāoshì | Move / Technique | Single martial arts maneuver |
| 拳法 | quánfǎ | Striking technique | Punching system/style |
| 腿法 | tuǐfǎ | Kicking technique | Kicking system/style |
| 格挡 | gédǎng | Block / Parry | Defensive deflection |
| 闪躲 | shǎn duǒ | Dodge / Evade | Avoidance movement |
| 反击 | fǎnjī | Counter-attack | Strike following a defense |
| 摔投 | shuāi tóu | Throw / Takedown | Grappling/wrestling move |
| 击飞 | jī fēi | Launch / Knockback | Hit that sends opponent airborne |
| 踉跄 | liàngqiàng | Stagger | Off-balance stumble from hit |
| 蓄力 | xùlì | Wind-up / Charge | Building energy before strike |
| 出拳 | chū quán | Throw a punch | Extending a punch toward target |
| 收势 | shōushì | Recovery stance | Return to guard after move |
| 气劲 | qì jìn | Qi / Energy force | Internal energy expressed externally |
| 弹反 | tán fǎn | Recoil / Bounce-back | Body physics after absorbing impact |
| 25宫格法 | 25 gōnggé fǎ | Grid method (25-cell) | Advanced beat-by-beat fight notation |
| 打击感 | dǎjī gǎn | Impact feel | Physical weight and consequence of a hit |

---

### D.12 后期制作 — Post-Production

| Chinese | Pinyin | English | Notes |
|---------|--------|---------|-------|
| 后期制作 | hòuqī zhìzuò | Post-production | Everything after filming |
| 剪辑 | jiǎnjí | Editing | Cutting and assembling footage |
| 粗剪 | cū jiǎn | Rough cut | First assembly without fine editing |
| 精剪 | jīng jiǎn | Fine cut | Polished final edit |
| 调色 | tiáosè | Color correction / Grading | Technical and creative color work |
| 混音 | hùnyīn | Sound mixing | Balancing audio tracks |
| 音效合成 | yīnxiào héchéng | Sound design | Creating and integrating all sound |
| 字幕 | zìmù | Subtitles | On-screen text captions |
| 片头 | piāntóu | Title sequence / Intro | Opening credits/visual |
| 片尾 | piānwěi | End sequence / Outro | Closing credits/visual |
| 转场特效 | zhuǎnchǎng tèxiào | Transition effect | Visual effect between scenes |
| 超分辨率 | chāo fēnbiànlǜ | Upscaling / Super-resolution | AI-enhanced resolution increase |
| 帧插值 | zhēng chāzhí | Frame interpolation | AI-generated in-between frames for smooth motion |
| 去噪 | qù zào | Denoising | Removing digital noise/grain |
| 稳像 | wěn xiàng | Image stabilization | Reducing camera shake in post |

---

### D.13 平台专用术语 — Seedance / Dreamina Platform Terms

| Chinese | Pinyin | English | Platform Usage |
|---------|--------|---------|----------------|
| 即梦 | jí mèng | Dreamina | Primary Seedance web interface |
| 全能参考 | quánnéng cānkǎo | Universal Reference mode | Multi-modal input mode; unlocks full power |
| 首尾帧 | shǒu wěi zhēn | First/Last Frame mode | Single image + text animation mode |
| 首帧 | shǒu zhēn | First frame | Starting reference image |
| 尾帧 | wěi zhēn | Last frame | Ending reference image |
| 参考图 | cānkǎo tú | Reference image | Any uploaded image used as @Tag |
| 参考视频 | cānkǎo shìpín | Reference video | Any uploaded video used as @Tag |
| 参考音频 | cānkǎo yīnpín | Reference audio | Any uploaded audio used as @Tag |
| 运镜参考 | yùnjìng cānkǎo | Camera reference | Video uploaded specifically for camera movement |
| 风格迁移 | fēnggé qiānyí | Style transfer | Applying one clip's visual style to new content |
| 分镜编排 | fēnjìng biānpái | Shot arrangement | Model independently selects shot sequence (Level 1 command) |
| 生成时长 | shēngchéng shícháng | Generation duration | Clip length setting (seconds) |
| 创意程度 | chuàngyì chéngdù | Creativity slider | Hallucination/deviation control |
| 视频续写 | shìpín xùxiě | Video extension | Extending an existing clip |
| 前向延伸 | qiánxiàng yánshēn | Forward extension | Adding content before existing clip |
| 双通道扩散 | shuāng tōngdào kuòsàn | Dual-branch diffusion | Model architecture; joint audio-video generation |
| 豆包 | dòu bāo | Doubao | ByteDance app with simplified Seedance access |
| 火山引擎 | huǒshān yǐnqíng | Volcengine | ByteDance cloud API platform |

---

### D.14 摄影基础 — Photography Fundamentals

| Chinese | Pinyin | English | Notes |
|---------|--------|---------|-------|
| 曝光三角 | bàoguāng sānjiǎo | Exposure triangle | ISO + aperture + shutter speed |
| 光圈 | guāngquān | Aperture | Controls DOF and exposure |
| 快门速度 | kuàimén sùdù | Shutter speed | Controls motion blur and exposure |
| 感光度 | gǎnguāngdù | ISO | Sensor sensitivity; high ISO = grain |
| 白平衡 | báipínghéng | White balance | Color temperature calibration |
| 对焦 | duìjiāo | Focus | Sharp subject rendering |
| 自动对焦 | zìdòng duìjiāo | Autofocus (AF) | Camera-driven focus tracking |
| 手动对焦 | shǒudòng duìjiāo | Manual focus (MF) | Operator-controlled focus |
| 微距 | wēijù | Macro | Extreme close-up photography |
| 长曝光 | cháng bàoguāng | Long exposure | Slow shutter; motion blur, light trails |
| 包围曝光 | bāowéi bàoguāng | Exposure bracketing | Multiple exposures for HDR |
| 高动态范围 | gāo dòngtài fànwéi | HDR (High Dynamic Range) | Preserving both highlights and shadows |
| 原生分辨率 | yuánshēng fēnbiànlǜ | Native resolution | Sensor's base pixel output |

---

### D.15 Prompt Construction Patterns — Chinese Direct-Use Phrases

These are complete phrase units that can be inserted directly into Chinese-language Seedance prompts. Each is verified to activate specific model behaviors.

**Shot size commands:**
```
使用大特写拍摄         → Shoot in extreme close-up
全景展示环境           → Establish environment in wide shot
中景对话场景           → Medium shot dialogue scene
过肩视角拍摄           → Shoot over-the-shoulder
```

**Camera movement commands:**
```
缓慢推镜，持续8秒       → Slow dolly push over 8 seconds
环绕主体一圈           → Complete orbit around subject
手持跟拍，轻微抖动      → Handheld follow, subtle shake
一镜到底，无剪辑        → One continuous take, no cuts
甩镜转场               → Whip pan transition
俯拍全景               → Top-down establishing shot
仰拍展现气势           → Low angle to convey power
```

**Lighting commands:**
```
单点硬光，45度侧位      → Single hard key, 45° side
低调布光，深阴影        → Low-key lighting, deep shadows
逆光，人物轮廓发光      → Backlight, subject rim glow
暖调烛光氛围            → Warm candlelight atmosphere
冷色调，蓝调打光        → Cool tone, blue-tinted light
丁达尔光效，雾中光束    → Tyndall rays, light beams through fog
```

**Motion & time commands:**
```
升格拍摄，极致慢动作    → Overcranked, ultra slow-motion
卡点剪辑，跟随节拍      → Beat-sync edit, follow the rhythm
定格强调关键瞬间        → Freeze frame on key moment
缓入缓出，自然运动      → Ease in/out, natural motion
```

**Delegation command (Level 1):**
```
注意分镜编排            → Pay attention to shot arrangement
注意节奏与剪辑          → Pay attention to rhythm and editing
自主选择合适的运镜      → Independently select appropriate camera movement
```

---
## Contributing

This skill document is a living artifact. Contributions are welcome:

1. **Platform behavior updates:** Document new observations with the current quarter.
2. **Recipe additions:** Submit new genre templates with delegation level and success rate.
3. **Failure pattern documentation:** Add edge cases with verified fixes.
4. **Translation improvements:** Refine Chinese-English term mappings.

**Contribution format:**
- Fork the repository
- Create a branch: `feature/your-addition`
- Submit a pull request with:
  - Clear description of the addition
  - Test results (if applicable)
  - Quarter tested

---

## Changelog

### v3.1.0 (2026-Q1)
- Complete rebuild of Module 01C: JSON Prompt Technique
  - New Schema v3 with zero-waste field design
  - Full field reference table with compile mapping
  - `seg` array for temporal segments (Level 3–4)
  - Four complete worked examples: Level 1–4 with compiled output
  - Pseudocode compile function for pipeline automation
  - Budget triage table with strict cut order
- Added Appendix D: Chinese Cinematic & Photography Vocabulary
  - D.1 景别 Shot Sizes (14 terms)
  - D.2 运镜 Camera Movements (18 terms)
  - D.3 镜头光学 Lens & Optics (14 terms)
  - D.4 构图法 Composition Techniques (12 terms)
  - D.5 灯光术语 Lighting Terminology (20 terms)
  - D.6 色彩控制 Color & Tone Control (16 terms)
  - D.7 时间与运动 Time, Pacing & Motion (19 terms)
  - D.8 音频术语 Audio & Sound Design (22 terms)
  - D.9 叙事结构 Narrative Structure (16 terms)
  - D.10 特效与视效 VFX & Visual Effects (17 terms)
  - D.11 动作与武打 Action & Fight Choreography (17 terms)
  - D.12 后期制作 Post-Production (15 terms)
  - D.13 平台专用术语 Seedance/Dreamina Platform Terms (18 terms)
  - D.14 摄影基础 Photography Fundamentals (13 terms)
  - D.15 Direct-use Chinese prompt construction phrases

### v3.0.0 (2026-Q1)
- Complete rewrite with delegation spectrum framework
- Added Module 00B: When to Direct vs. Delegate
- Added Module 03B: Storyboard Reference Technique
- Added Module 04B: Action Choreography Protocol
- Added Module 06B: First-Frame Art Direction
- Added Module 12B: Energy, Magic & Destruction VFX
- Added Module 13B: Advanced Audio Techniques
- Expanded Recipe Book to 10 templates
- Added Appendix B: Language Considerations
- Documented 150+ prompt variations research findings

### v2.x (Historical)
- Initial modular structure
- Basic quad-modal protocols
- Camera language codex

---

## License

MIT License

Copyright (c) 2026 Iamemily2050 (@iamemily2050)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR DEALINGS IN THE SOFTWARE.

---

## Acknowledgments

This skill document synthesizes knowledge from:
- ByteDance Seedance 2.0 research team
- Chinese AI filmmaking practitioner community
- 150+ prompt variation stress tests
- Q1 2026 platform behavior verification

**Maintainers:** Iamemily2050 (@iamemily2050)  
**Contact:** @iamemily2050 on X/IG  
**Repository:** https://github.com/Emily2040/seedance-2.0-skill

---


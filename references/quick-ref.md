# quick-ref · Seedance 2.0

One-page cheat sheet. Print or keep pinned.

---

## Modes

| Code | Name | Input |
|---|---|---|
| T2V | Text to Video | prompt only |
| I2V | Image to Video | prompt + images |
| V2V | Video to Video | prompt + video |
| R2V | Reference to Video | prompt + mixed refs |

---

## Delegation Levels

| Level | Words (EN) | Use when |
|---|---|---|
| 1 | ≤ 30 | Pure atmosphere, model freestyle |
| 2 | 30–80 | Clear subject + action + camera |
| 3 | 80–200 | Time-segmented, multi-beat |
| 4 | 200–1000+ | Full choreography, fight, complex |

---

## Five-Layer Prompt Stack

```
1. SUBJECT   — who/what, identity (@Tag)
2. ACTION    — verb + timing
3. CAMERA    — framing + movement + speed
4. STYLE     — 1–3 tokens
5. SOUND     — ambient + sfx + music  (optional)
```

Early tokens carry heavy weight. Subject + Action in first 20–30 words.

---

## @Tag Roles

| Tag | Typical use |
|---|---|
| @Image1 | Character identity / hero subject |
| @Image2 | Background / environment lock |
| @Image3 | Prop / secondary character |
| @Video1 | Motion reference / extension source |
| @Audio1 | BGM / dialogue |

---

## Platform Limits (Q1 2026)

- Duration: 4–15 s (no confirmed mobile-specific cap)
- Files: max 12 total (Rule of 12)
- Images: 9 × 30 MB (JPG/PNG/WEBP)
- Videos: 3 clips, **combined ≤ 15 s total**
- Audio: 3 MP3, total ≤ 15 s
- Aspect: 16:9 · 9:16 · 4:3 · 3:4 · 21:9 · 1:1

---

## Key Chinese Terms

`推` push · `拉` pull · `摇` pan · `跟` follow · `环绕` orbit  
`升格` slow-mo · `卡点` beat-sync · `一镜到底` oner  
`大远景` EWS · `全景` FS · `中景` MS · `近景` CU · `特写` ECU  
`黄金时刻` golden hour · `丁达尔` god rays · `轮廓光` rim light

---

## Emergency Fixes

| Problem | Fix |
|---|---|
| Chaotic output | Shorten prompt; add `locked-off static camera` |
| Character drift | Add @Image reference |
| Camera wanders | Specify movement explicitly |
| Background morphs | Add environment @Image |
| Audio desyncs | Trim audio < 10 s |
| Content blocked | Remove real faces / IP names |

---

## Compression Order (over budget)

Remove: SFX → style tokens → environment → camera detail  
**Never remove**: SUBJECT · ACTION · @Tags

---

## Skill Map

```
seedance-20 (router)
├── seedance-interview     ← start here for new projects
├── seedance-prompt       ← Five-Layer Stack, @Tags, JSON
├── seedance-camera       ← framing, storyboard
├── seedance-motion       ← speed, fight, extension
├── seedance-lighting     ← light, color, atmosphere
├── seedance-characters   ← identity, multi-char
├── seedance-style        ← aesthetic, CGI, period
├── seedance-vfx          ← magic, destruction, energy
├── seedance-audio        ← voice, music, sync
├── seedance-pipeline     ← API, ComfyUI, post
├── seedance-recipes      ← genre templates
├── seedance-troubleshoot ← QA, errors, fixes
├── seedance-copyright    ← IP rules, safe substitutions
├── seedance-antislop     ← kill hollow language
├── seedance-filter       ← content filter navigation
├── seedance-vocab-zh     ← 中文影视术语 (320+ terms)
├── seedance-vocab-ja     ← 日本語映画術語 (280+ terms)
├── seedance-vocab-ko     ← 한국어 영화 용어 (270+ terms)
├── seedance-vocab-es     ← Vocabulario cinemático (270+ terms)
└── seedance-vocab-ru     ← Русская кинотерминология (270+ terms)
```

---

## ⚠️ Feb 2026 Content Policy Quick-Check

Run before every generation:

| Gate | Check | If fail |
|---|---|---|
| 1. Name | Real person named? | Remove name → use archetype |
| 2. IP | Franchise/character named? | Use descriptor from [skill:seedance-copyright] |
| 3. Scene | Specific copyrighted scene? | Reframe generically |
| 4. Audio | Named song/composer? | Describe texture/tempo/instrumentation |
| 5. Building | Named protected building? | Use architectural descriptor |
| 6. Logo | Recognizable logo in output? | Describe geometry only |

**Current hard-blocked entities** (post-Feb-15 filter tightening):
Spider-Man · Darth Vader · Iron Man · Deadpool · Shrek · SpongeBob · Eleven (Stranger Things) · Squid Game guard · all named anime characters · all named real actors

**API status**: Official API delayed (was Feb 24). **No public API exists yet.** Web platform (jimeng.jianying.com) is live. Third-party proxies available but unofficial.

---

## 6-Part Field Formula

```
[SHOT TYPE] + [SUBJECT] + [ACTION] + [STYLE] + [CAMERA MOVEMENT] + [AUDIO CUES]
```

Cross-validated on 10,000+ generations. Maps directly to Five-Layer Stack.

**Top 3 practitioner laws:**
1. Volume over perfection: generate 10, select 1
2. One action per prompt: no competing verbs
3. Front-load substance: subject+action in first 20 tokens, never adjectives

---

## Audio / Lip-Sync Quick Reference (v4.0)

### Hard Constraints
| Constraint | Value |
|---|---|
| Audio format | **MP3 only** (WAV/AAC/OGG/FLAC/M4A → silent failure) |
| Max audio duration | **≤ 15 s** per clip (optimal: 3–8 s for best sync) |
| Max audio clips | **3** per generation (Rule of 12) |
| Audio bitrate | 128–320 kbps |
| Max audio file size | 10 MB |
| Faces per generation | **1 only** — multi-face images break detection |

### Platform Clarification
| Tool | Model | Lip-Sync Modes |
|---|---|---|
| **Video Generation 视频生成** | **Seedance 2.0** | No modes — audio reference via @Audio1 |
| **Digital Human 数字人** | OmniHuman-1 | Master / Quick / Standard (separate tool) |

**Seedance 2.0 video generation has no Master/Quick/Standard modes. Those belong to the Jimeng Digital Human tool.**

### Multi-Character Dialogue Workflow
1. Split dialogue audio by character (A lines / B lines → separate MP3s)
2. Generate Character A alone (single image + A audio)
3. Generate Character B alone (single image + B audio)
4. Composite in CapCut/Jianying: PiP + Linear Mask (15–20% feather)
5. A speaks → A layer is video, B layer is static image. Swap for B.

### Top Silent Failure Causes
1. Wrong audio format (not MP3)
2. Multiple faces in reference image
3. Video uploaded instead of image (locks out Master/Quick)
4. Audio >15 s
5. Noisy/reverb-heavy audio

### Timestamp Anchoring (fixes model rewriting your audio)
Add to prompt: `Audio @Audio1 plays exactly as uploaded from 0s to end. Do not modify or replace the audio content.`

### Suspended Features (Feb 2026)
- Voice cloning / Face-to-Voice — suspended
- Real person face uploads — blocked (Feb 15)

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

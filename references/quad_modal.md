
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

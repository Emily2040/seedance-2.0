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


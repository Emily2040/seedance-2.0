---
name: seedance-lighting
description: 'Specify lighting, atmosphere, and light transitions for Seedance 2.0 prompts using named light sources, core parameters, and atmosphere contracts. Use when the scene needs a specific mood, time of day, or lighting style, or when lighting is flat, inconsistent across shots, or clipping.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["lighting", "atmosphere", "color-grade", "openclaw", "antigravity", "gemini-cli", "codex", "cursor"]
metadata: {"version": "3.3.0", "updated": "2026-02-25", "openclaw": {"emoji": "💡", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "parent": "seedance-20", "antigravity": {"emoji": "💡", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "💡", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-lighting

Lighting as narrative state. Measurable atmosphere contracts for Seedance 2.0.

## Scope

- Named light source specification (always required)
- Core lighting parameters (key direction, contrast, color, shadows)
- Atmosphere contracts (fog, dust, rain, mist)
- Light transitions within a clip
- Replacing vague light words with physical descriptions

## Out of scope

- Style and color grading — see [skill:seedance-style]
- CGI material reflections — see [skill:seedance-style]

---

## The Rule: Always Name a Source

```
❌  dramatic lighting
✅  single overhead practical as hard key, 5600K, deep shadow fill
```

---

## Physical Light Descriptions (copy-paste)

```
window backlight casting long shadows toward camera
neon sign as key light, pink and blue, no fill
firelight flicker, warm amber, unstable
overcast diffused daylight, soft wrap shadows
single bare bulb swinging overhead
red emergency lamp as sole light source
candle practical, warm gold, deep shadow beyond 1m
streetlamp sodium key, cool fill from ground reflection
```

---

## Core Parameters

```
Key direction:  camera-left / camera-right / above / below / behind (rim)
Contrast:       low-key (deep shadows) / high-key (bright, minimal shadows)
Color temp:     warm amber / cool blue / neutral white (Kelvin optional)
Shadow edge:    hard-edged / soft wrap / no shadows
```

---

## Atmosphere Contracts (Measurable)

Every atmospheric effect must be describable in physical terms.

```
thin fog catching the backlight, visibility 5m
dust motes suspended in a sunbeam from camera-left
light rain visible against the key light, not heavy
breath misting in cold air at each exhale
heat shimmer rising from asphalt, subtle
smoke drifting from off-screen right, backlit
```

If fog becomes a blur: reduce density → increase backlight specificity → simplify background.

---

## Lighting Vocabulary

| Chinese | English | Usage |
|---------|---------|-------|
| 主光 | Key light | Primary dominant source |
| 辅光 | Fill light | Softens key shadows |
| 轮廓光 | Rim light | Edge separation from background |
| 逆光 | Backlight / Contre-jour | Subject silhouetted or rimmed |
| 低调布光 | Low-key | Dark, high-contrast; drama |
| 高调布光 | High-key | Bright, low-contrast; commercial |
| 实景灯光 | Practical light | Visible source in frame |
| 丁达尔效应 | Tyndall rays / God rays | Light beams through particles |

---

## Light Transitions Within a Clip

Use timestamps for in-clip light changes:

```
0–3s: warm golden overhead light.
3–5s: lights flicker and die.
5–end: only red emergency lamp remains; cool rain spill from open door as rim.
```

---

## Agent gotchas

1. "Dramatic lighting" generates nothing specific. Always name a physical source.
2. Kelvin numbers (3200K, 5600K) are optional — simple warm/cool works. Use Kelvin only when precision matters.
3. Never combine contradictory contrast instructions: "bright and vibrant" + "deep shadows" = the model picks one.
4. Atmosphere in motion: if rain appears in the key light but not elsewhere, specify "rain visible in the key light beam only."
5. Practical lights (candles, lamps, neon) in frame create the most natural-looking AI video. Prefer them over invisible studio lighting.

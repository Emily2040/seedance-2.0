---
name: seedance-prompt-short
description: 'Build, validate, and compress Seedance 2.0 prompts to a hard 2000-character limit using the Five-Layer Stack, @Tag delegation, and the new Compression Engine. Use when constructing or debugging any T2V, I2V, V2V, or R2V prompt for the short-form workflow.'
license: MIT
user-invocable: true
tags: [prompt, compression, t2v, i2v, v2v, r2v, character-limit, openclaw, antigravity, gemini-cli]
metadata: {
  "version": "3.8.0",
  "updated": "2026-02-27",
  "openclaw": {"emoji": "⚡️", "homepage": "https://github.com/Emily2040/seedance-2.0"},
  "parent": "seedance-20",
  "author": "Emily (@iamemily2050)",
  "repository": "https://github.com/Emily2040/seedance-2.0"
}
---

# seedance-prompt-short

This skill enforces a hard **2000-character limit** for Seedance 2.0 prompts, based on practitioner data showing superior performance with short, dense prompts.

## The 2000-Character Budget

| Layer | Budget (chars) | Purpose |
|:---|:---:|:---|
| **1. Core Intent** | 400 | Subject + Action. The emotional and narrative heart. |
| **2. Visuals** | 600 | Camera + Lighting + Style. The cinematic eye. |
| **3. Audio** | 300 | Music + SFX + Ambience. The soundscape. |
| **4. Technical** | 400 | @Tags + Constraints + Physics. The rules. |
| **5. Flex** | 300 | Reserve for the most important layer. |
| **Total** | **2000** | **Maximum** |

## The Compression Engine

- **Verbs > Adjectives**: `A woman's face, catching the last light` not `A beautiful, stunning shot`.
- **Show, Don't Tell Emotion**: `His shoulders slump` not `He is sad`.
- **Use Film Language**: `Dolly shot, camera-left` not `The camera moves smoothly`.
- **Trust the Model**: `Gourmet hamburger ad, macro shot` not a long description of a hamburger.

---

For a guided workflow that builds a 2000-char prompt, use [skill:seedance-interview-short].

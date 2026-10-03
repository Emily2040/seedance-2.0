---
name: seedance-prompt-short
description: "This skill should be used when the user wants a short, dense Seedance 2.0 prompt, Chinese prompt compression, a 30-100 word prompt, or a concise prompt that preserves subject, action, camera, lighting, reference tags, and audio cues."
license: MIT
user-invocable: true
user-invokable: true
tags:
  - seedance-20
  - video-generation
  - prompt
  - short
metadata:
  version: "5.1.0"
  updated: "2026-04-27"
  parent: "seedance-20"
  author: "Emily (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: ""
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-prompt-short

This skill helps construct and compress prompts for Seedance 2.0, with a recommended target of **30-100 words**.

## The 30-100 Word Target

| Layer | Budget (chars) | Purpose |
|:---|:---:|:---|
| **1. Core Intent** | ~20-40 words | Subject + Action. The emotional and narrative heart. |
| **2. Visuals** | ~20-30 words | Camera + Lighting + Style. The cinematic eye. |
| **3. Audio** | ~10-20 words | Music + SFX + Ambience. The soundscape. |
| **4. Technical** | ~10-20 words | @Tags + Constraints + Physics. The rules. |

| **Total** | **~30-100 words** | **Recommended Target** |

## The Compression Engine

- **Verbs > Adjectives**: `A woman's face, catching the last light` not `A beautiful, stunning shot`.
- **Show, Don't Tell Emotion**: `His shoulders slump` not `He is sad`.
- **Use Film Language**: `Dolly shot, camera-left` not `The camera moves smoothly`.
- **Trust the Model**: `Gourmet hamburger ad, macro shot` not a long description of a hamburger.

## Copyright & Policy Gate (Required)

Before finalizing any prompt, run a safety pass:

- If the request includes a celebrity, real person, recognizable likeness, brand, franchise, logo, or copyrighted character/style, route to [skill:seedance-copyright] first.
- If the prompt is blocked or likely to trigger a policy filter, route to [skill:seedance-filter] and preserve user intent with safer wording.

---

For a guided workflow that builds a prompt, use [skill:seedance-interview].

---
name: seedance-characters
description: 'Lock character identity, assign @Tag references, and maintain face and hand consistency across multi-character scenes in Seedance 2.0. Covers 360-degree consistency testing and first-frame art direction for image-to-video. Use when a character changes appearance between shots, when building multi-person scenes, or when hands or faces are distorting.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["characters", "identity-lock", "multi-character", "openclaw", "antigravity", "gemini-cli", "codex", "cursor"]
metadata: {"version": "3.8.0", "updated": "2026-02-27", "openclaw": {"emoji": "🎭", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "parent": "seedance-20", "antigravity": {"emoji": "🎭", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "🎭", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-characters

Character fidelity, identity anchoring, and first-frame art direction for Seedance 2.0.

## Scope

- Reusable character card format
- Identity anchoring via @Tag
- Multi-character separate reference pattern
- Prop/weapon separation from character body
- Hand and face safety
- 360° consistency testing
- First-frame composition rules for I2V

## Out of scope

- Style and visual aesthetic — see [skill:seedance-style]
- Camera positioning — see [skill:seedance-camera]
- Fight choreography — see [skill:seedance-motion]

---

## Character Card Format

Write once. Reuse across all prompts for this character. Never change nouns mid-project.

```
[Name]: [age range], [build], [skin tone], [hair style/color], 
[defining features], [wardrobe description], [emotional energy].

Example:
Maya: woman mid-30s, lean build, warm brown skin, short natural hair,
sharp eyes, leather jacket over white tank, calm and precise energy.
```

---

## Identity Anchoring

For I2V and R2V, always assign the character reference explicitly:

```
@Image1's character as the subject
@Image1 for facial features and clothing
Use @Image1 and @Image2 for the character's appearance from multiple angles
```

A bare `@Image1` with no role instruction is weak.

---

## Multi-Character Patterns

For two characters, use separate identity anchors:

```
Character A references @Image1.
Character B references @Image2.

Character A throws a right punch at Character B.
Character B blocks with crossed arms.
```

Attribute every action by name. Never use ambiguous pronouns in multi-character prompts.

---

## Prop and Weapon Separation

Upload character body and prop/weapon as separate references:

```
Character appearance references @Image1.
Weapon design references @Image2.
```

This prevents the model from blending weapon details into the character's body geometry.

---

## Hand Safety

If hands are not essential to the action: frame waist-up or specify `"hands not in frame."`

If hands are essential: specify one simple action only.

```
✅  picks up the glass with right hand
✅  places hand flat on the table
✅  open palm facing camera
❌  intricate finger gestures
❌  typing on keyboard (close-up)
```

---

## Face Stability

- Prefer medium close-up with steady, locked camera for dialogue
- Avoid rapid head turns combined with extreme close-up
- Re-upload the original face reference when extending clips
- Never rely solely on the last frame of a previous clip to maintain face identity

---

## 360° Consistency Test

Before committing to a character reference, generate the same character from multiple angles (front, side, three-quarter, back). Place results side by side.

If identity holds across all angles → the reference is production-ready.
If identity drifts at any angle → improve the reference or generate from a better image.

---

## First-Frame Art Direction (I2V)

The first frame is the primary creative contract for I2V. Everything follows from it.

### Composition rules for I2V first frames

1. **Bake the camera angle.** If you want low angle, compose the first frame from low angle. Do not contradict it in the prompt.
2. **Bake the lighting direction.** The model maintains established lighting. If you want side-lighting, the first frame must show it.
3. **Pose at the START of motion.** If the character swings a sword, pose them at wind-up, not mid-swing.
4. **Clean, depth-separated background.** Cluttered backgrounds warp during camera moves.
5. **Match aspect ratio.** Generate the first-frame image in the same AR as the target video.

### What goes in the image vs. the prompt

| In the first-frame image | In the prompt |
|--------------------------|---------------|
| Character identity + costume | Motion (what changes) |
| Pose at start of action | Timing (when things happen) |
| Camera angle + lighting | Camera movement (how frame evolves) |
| Environment composition | Sound |
| Color palette | Constraints |

### Common first-frame mistakes

```
❌  Wrong lighting direction → forces re-light → causes flicker
❌  Character mid-action → no room for motion in prompt
❌  Complex cluttered background → warp during camera movement
❌  Low resolution → model loses detail for consistency
```

---

## Real-Face Restriction

Real human face references require identity verification on the Dreamina platform. Use AI-generated portraits or illustrated/3D character references instead. See [skill:seedance-prompt] for content policy.

---

## Agent gotchas

1. If identity drifts mid-clip: add `"@Image1's character as the subject"` and reduce motion complexity.
2. Character card nouns are contractual. Renaming "wool coat" to "heavy jacket" mid-project breaks consistency.
3. One hero subject per shot. Two max if interaction is essential.
4. When extending a clip, always re-upload the face reference image. The last frame is not enough.
5. The 360° consistency test is cheap insurance. Run it before committing to a production pipeline.

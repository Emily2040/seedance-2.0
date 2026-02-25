
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

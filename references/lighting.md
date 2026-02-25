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

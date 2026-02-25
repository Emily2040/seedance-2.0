
### Agent Automation Patterns

Seedance 2.0 + API enables automated content pipelines:

- **Product promo agent:** Product update → screenshot → image model → Seedance → final video.
- **Talking-head agent:** News feed → script → TTS audio → character image → Seedance → video podcast.
- **Novel-to-series agent:** Novel text → chapter splitting → sequential Seedance extensions → compiled episode.

---

## Module 16: Genre Recipe Book

### Recipe 1 — Product / E-Commerce Ad

**Delegation level:** 1–2  
**References:** Product images (2–3 angles), optional music reference

**Template:**
```
Commercially showcase @Image1's [product], referencing @Image2 for side view and @Image3 for material texture detail. 
Display all product details across multiple angles. Background music: grand and atmospheric.
```

**Tips:** The model knows how to shoot products commercially. Trust its instinct for rotation, close-ups, and material highlighting.

---

### Recipe 2 — Fight / Martial Arts Scene

**Delegation level:** 4  
**References:** Character A image, Character B image, optional choreography reference video

**Template:**
```
Characters: A @Image1, B @Image2.
Fight scene on [environment], [ground type].

Shot 1 (0–1.5s): [Camera], [Action A→B], [SFX].
Shot 2 (1.5–3s): [Camera], [Reaction B], [Counter], [SFX].
Shot 3 (3–5s): [Camera], [Climax exchange], [SFX].

Camera: medium shot tracking, slight handheld shake on impacts.
Sound: [impact sounds], [ambient], [music cue if any].

@tips: reinforce weapon/prop consistency under fast motion.
```

---

### Recipe 3 — Brand / Corporate Film

**Delegation level:** 1  
**References:** Optional brand imagery, optional voice reference

**Template:**
```
Generate a [duration]-second brand film about [brand/product description], capturing its core identity and values. 
Pay attention to shot arrangement, pacing, and appropriate music.
```

**Tips:** For well-known brands, the model understands brand DNA. For unknown brands, add 1–2 sentences describing the brand's tone and aesthetic.

---

### Recipe 4 — Atmospheric / Mood Piece

**Delegation level:** 2  
**References:** One environment/mood reference image

**Template:**
```
@Image1 as the first frame. [Subject] stands/sits [where], [one subtle action]. 
Slow dolly [direction] over [duration]. [Named light source], [contrast type], [atmosphere detail]. 
[One style anchor]. Sound: [ambient bed], [one foreground SFX], [music or silence].
```

---

### Recipe 5 — Dialogue / Character Scene

**Delegation level:** 2–3  
**References:** Character face image, optional scene image

**Template:**
```
@Image1's character as the subject. Medium close-up, locked-off camera.
Character says: "[Short dialogue line]."
Phoneme-accurate lip-sync. [Expression change description].
Light: [named source], [mood]. Style: [anchor].
Sound: dialogue clean and prominent, ambient low.
```

---

### Recipe 6 — One-Take Spatial Journey

**Delegation level:** 2  
**References:** 3–5 scene/environment images in sequence

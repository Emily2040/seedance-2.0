
**Shields/barriers:**
```
translucent energy barrier, hexagonal pattern, ripples on impact, [color]
```

**Explosions:**
```
energy collision produces [size] explosion, shockwave expands outward, [debris type] launched radially
```

### Particle System Language

- **Density:** `"sparse / moderate / dense particle field"`
- **Emission:** `"particles emit from [source point], [direction], [speed]"`
- **Scale with force:** `"particle density increases with swing speed, up to [threshold]"`
- **Color temperature:** `"cold blue particles / hot orange embers / electric white sparks"`
- **Lifecycle:** `"particles spawn bright, dim over 0.5s, fade completely"`

### Destruction Physics

- **Cracking:** `"ground cracks radiate from impact point, [pattern: spider-web / linear / concentric]"`
- **Shattering:** `"stone wall shatters into fragments, large chunks fall with gravity, small debris sprays outward"`
- **Debris trajectory:** `"fragments launch upward from impact, arc with gravity, scatter across [radius]"`
- **Dust/smoke:** `"dust cloud erupts from destruction, [color], [density], settles over [time]"`
- **Shockwave:** `"visible shockwave distorts air, expands at [speed], rustles loose objects within [radius]"`

### Combining Multiple VFX Systems

When multiple effects interact, specify the hierarchy:

```
Primary: sword slash emits ice-blue particle trail, 360° spiral per swing.
Secondary: particles scatter on impact with enemy, burst into smaller sparks.
Tertiary: ground freezes where particles land, ice crystals spreading.
Environment: cold mist rises from frozen ground, backlit by the blue glow.
```

---

## Module 13: Audio & Sonic Design

### Seedance 2.0 Generates Audio and Video Jointly

Audio descriptions influence pacing and cut feel.

### Sound Layer Structure

- **Ambient bed:** continuous environmental sound
- **Foreground SFX:** 1–2 event-locked sounds
- **Music cue:** entry time + arc (rising/falling/steady)
- **Silence design:** where absence matters

### Compact Syntax

```
Sound: rain bed + distant train hum. SFX: chess piece click at 2s. 
Music: low piano note enters at 3s, resolves on last frame. Silence holds for final 0.5s.
```

### Dialogue and Lip-Sync

- Short lines only. Long dialogue reduces visual stability.
- Put dialogue in quotes: `Character says: "We leave at dawn."`
- Specify framing: `medium close-up, locked-off camera.`
- Specify pauses: `"brief pause at 2s."`
- Lip-sync is phoneme-accurate in multiple languages.

### Mix Intent

- **Dialogue scenes:** `"dialogue clean and prominent, music low, ambient subtle."`
- **Music-driven:** `"music leads, ambient secondary, no dialogue."`
- **SFX-driven:** `"environmental sounds prominent, no music."`

---

## Module 13B: Advanced Audio Techniques

### Voice Reference and Cloning

Upload a video or audio clip and Seedance adopts the speaker's voice timbre:

```
Voice timbre references @Audio1. Character speaks with this voice quality.
```

Or from a video reference:
```
Narration voice references @Video1's speaker.
```

### Emotion Modification

The model can modify the emotional delivery of a voice reference:

```
Voice references @Audio1, but make the delivery more excited and energetic.
```


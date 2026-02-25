
### Multi-Language Generation

Characters can speak Chinese, English, Spanish, Korean, and other languages with appropriate lip-sync:

```
Character speaks in [target language]: "[dialogue text]."
```

Dialect support has been confirmed for regional Chinese dialects (e.g., Sichuan dialect).

### Multi-Character Dialogue

Multiple characters with distinct voices in one generation:

```
Character A (deep male voice) says: "..." Character B (high female voice) responds: "..."
```

### Beat-Sync / Music Scoring (卡点)

For music-synced visual editing:

1. Upload multiple scene images + one music reference video.
2. Write:
```
@Image1 through @Image7 are scene images. Reference @Video1's rhythm and beat structure. 
Cut scene transitions on downbeats. Characters move with energy matching the music tempo.
```

The model aligns visual cuts and motion beats to the musical rhythm.

### Sound-Driven Timing

Use audio cues to anchor visual events:

```
Sound: thunder crack at 3s. Visual: lightning illuminates the scene exactly at the thunder crack. 
Character flinches at the sound.
```

This technique uses the audio description to drive visual choreography rather than the other way around.

### Impact Sound Layering (For Fight Scenes)

Each hit should have layered sound:

```
SFX per impact: wet thud (contact) + bone crack undertone (damage) + dust puff whoosh (environmental response) + brief silence (recovery).
```

Use phonetic/onomatopoeic descriptions for specific sonic textures: `"heavy drum 'dong'"`, `"metallic ring 'clang'"`, `"scraping 'ci'"`, `"explosive 'boom'."`

---

## Module 14: Final Director's Self-Check

### Before Generating, Complete This Sentence:

> "This shot makes the audience feel **[EMOTION]** by showing **[SUBJECT]** undergoing **[TRANSFORMATION]** through **[ACTION]**, captured with **[CAMERA]** under **[LIGHT]**, in **[STYLE]**, with **[SOUND]**, at delegation Level **[1/2/3/4]**."

If the sentence cannot be completed, the shot is not directed yet.

### Then Verify:

- [ ] Is the delegation level appropriate? (Am I over-specifying something the model knows?)
- [ ] Are my @Tag roles explicit and non-conflicting?
- [ ] Is my prompt structured (subject → action → camera → style → constraints)?
- [ ] Have I checked for mutually exclusive instructions?

---

## Module 15: Pipeline Integration

### ComfyUI Workflows

Advanced users can orchestrate Seedance 2.0 via ComfyUI nodes (when available) for:
- Pre-processing reference images (upscaling, relighting, pose correction)
- Batch generation with parameter sweeps
- Post-processing (frame interpolation, color grading, compositing)
- Multi-reference assembly pipelines

### Volcengine API

The Seedance 2.0 API (model string: `Doubao-Seedance-2.0`) supports full multi-modal input programmatically.

**Key API considerations:**
- All reference capabilities (images, videos, audio) are available via API.
- The API may have different text length limits than the Dreamina web UI — test and document.
- API access enables Agent-based automation pipelines.

### Post-Processing Pipeline

Raw Seedance output benefits from post-processing:

1. **Upscaling:** AI upscalers (specialized for AI-generated video faces) can bring 720p to 4K while preserving identity. Generic upscalers may distort AI faces.
2. **Frame interpolation:** Smooths motion for higher effective frame rate.
3. **Color grading:** Professional color correction for broadcast/cinema standards.
4. **Compositing:** Multiple Seedance clips can be composited for complex scenes.

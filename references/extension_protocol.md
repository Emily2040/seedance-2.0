
Convert each row to one sentence in the prompt. This method is used by advanced Chinese creators to choreograph 6–10 beats within 5 seconds.

### Multi-Character Fight With Separate References

```
Characters: A references @Image1; B references @Image2.

Choreography: A throws right hook at B's jaw. B ducks, sweeps A's legs. 
A jumps, lands spinning back kick to B's shoulder. B staggers backward 2 steps.

Camera: Medium shot tracking, slight handheld shake on impacts.

Sound: wet impact on each hit, dust puff from ground, heavy breathing between exchanges.
```

### Tips From Practitioners

- Object integrity degrades under high-speed motion. Reinforce weapon/prop consistency: `"weapon shape stays consistent throughout."`
- The model's fight choreography comprehension improves with precision. The more precise the prompt, the better the result.
- Use reference video for overall choreography style + text for specific modifications.

---

## Module 04C: Sequential Extension Protocol

### The Extension Workflow for Long-Form Production

Seedance 2.0 clips max at 15 seconds, but video extension enables theoretically unlimited length.

### Basic Extension

```
Extend @Video1 by [X] seconds. New content: [description of what happens next].
```

Set generation duration to match the extension length (e.g., extend 5 seconds → set duration to 5s).

### Continuity Rules for Extension

1. **Re-upload character reference images** when extending — don't rely solely on the previous clip's last frame. This prevents identity drift ("morphing").
2. Set creativity/hallucination low (if the slider is available, 0.3–0.4) to stay close to the source material.
3. Describe the continuation, not the whole scene over again.
4. Maintain sonic continuity: specify whether music continues, changes, or bridges.

### Forward Extension

To add content BEFORE an existing clip:
```
Extend @Video1 forward by [X] seconds. Preceding content: [description of what comes before].
```

### Bridging Two Clips

To generate a transition between two existing clips:
```
Generate a [X]-second bridge between @Video1 and @Video2. [Description of transition content].
```

### Novel-Text-to-Video Chain

For adapting long-form text (novels, scripts) into sequential video:

1. Generate the first 15s clip from the opening text passage + style reference.
2. Extend with subsequent text:  
   ```
   Extend @Video1 by 15s. Content: [paste next paragraph of novel text].
   ```
3. Repeat, always referencing the previous clip and any character/style anchors.

This technique works because Seedance 2.0 has strong text comprehension. It can parse narrative prose — not just production-formatted prompts — and generate appropriate cinematography.

---

## Module 05: Lighting & Atmosphere

### Always Name a Source

❌ Bad: `"dramatic lighting."`  
✅ Good: `"single overhead practical as hard key, 5600K, deep shadow fill."`

### Replace Vague Light Words With Physical Descriptions

- `window backlight casting long shadows`
- `neon sign as key light, pink and blue`
- `firelight flicker, warm and unstable`
- `overcast diffused daylight, soft shadows`
- `single bare bulb swinging`
- `red emergency lamp as sole light source`

### Core Lighting Parameters

- **Key direction:** camera-left/right, above/below, behind (rim/backlight)
- **Contrast:** low-key (deep shadows) / high-key (bright, minimal shadows)
- **Color temperature:** warm amber / cool blue (simple words work; Kelvin numbers optional)
- **Shadow behavior:** hard-edged / soft wrap / no shadows

### Atmosphere Contracts (Measurable)


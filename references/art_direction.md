3. Reduce style to 2–3 tokens.
4. Reduce sound to ambient + one cue.
5. Remove secondary props/extra characters.
6. Consider switching to a reference-based approach (upload a style reference instead of describing it).

**Never cut:** subject identity, core action, camera timing.

---

## Module 10: Maintenance Protocols

### Versioning

- Increment version when templates or constraints change.
- Keep last-stress-tested quarter and rerun tests each quarter.
- Track platform changes (Dreamina updates, API changes, new features).

### Regression Test Pack (Run After Major Platform Changes)

Generate 8 short clips:

1. **Level 1:** Minimal-intent food/product ad (test director intelligence).
2. **Level 2:** Locked-off portrait dialogue close-up with lip-sync.
3. **Level 2:** Slow dolly push in low-key light.
4. **Level 3:** Orbit move around a static subject.
5. **Level 3:** I2V first+last frame transformation.
6. **Level 3:** V2V camera transfer with one controlled change.
7. **Level 3:** Multi-shot lens switch with sound continuity.
8. **Level 4:** Dense fight choreography (4+ beats in 5 seconds).

**Record:** prompt text, prompt length, delegation level, seed, aspect ratio, pass/fail notes, observed behaviors.

---

## Module 11: CGI Pipeline

### CGI Fails When Materials Are Unspecified

Leading to "plastic sheen."

### Material Contract (Use 2–4 Properties)

- **Base:** metal / painted metal / glass / ceramic / rubber / fabric / wood / stone
- **Roughness:** matte / satin / glossy / mirror
- **Imperfection:** micro-scratches, dust, fingerprints, wear marks, patina
- **Edge behavior:** slightly beveled / razor sharp / rounded / chipped

**Example:** `"brushed aluminum, satin roughness, fine micro-scratches, subtle edge wear."`

### Motion Physics

- Heavy objects accelerate slowly and decelerate slowly.
- Cloth lags behind motion, then catches up.
- Glass reflections shift with camera movement.
- Liquid sloshes with inertia.
- State mass/weight when needed: `"feels heavy, slow inertia."`

---

## Module 12: VFX Integration

### FX Contract (Every Effect Needs These)

- **Source:** where does it originate?
- **Scale:** size relative to subject
- **Behavior:** drift / burst / swirl / dissipate / grow / shrink
- **Interaction:** casts light, casts shadows, affects air, displaces other elements
- **Duration:** when does it start, peak, and fade?

### Examples

```
Sparks burst from the sword impact point, arc downward with gravity, cool and fade within 1 second.
```

```
Smoke rises from the crater, curls in the wind, thins as it rises; backlight makes edges glow.
```

### Compositing Language

- `"Foreground subject stays clean, FX behind subject only."`
- `"Light from the explosion briefly overexposes the frame, then recovers in 0.3s."`
- `"Dust settles on the character's shoulders after the debris cloud passes."`

---

## Module 12B: Energy, Magic & Destruction VFX

### Energy Effects Vocabulary

**Beams/rays:**
```
concentrated energy beam, [color], fired from [source] to [target], [width], illuminates surrounding surfaces
```

**Auras/fields:**
```
glowing aura surrounds the character, [color], pulsing with breath rhythm, casting colored light on nearby surfaces

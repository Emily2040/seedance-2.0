---
name: seedance-vfx
description: 'Specify VFX physics contracts, energy effects, particle systems, destruction physics, and multi-layer VFX hierarchies for Seedance 2.0. Use when adding explosions, fire, water, lightning, magic effects, or any physically simulated element to a scene.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["vfx", "particles", "destruction", "physics", "openclaw", "antigravity", "gemini-cli", "codex", "cursor"]
metadata: {"version": "3.3.0", "updated": "2026-02-25", "openclaw": {"emoji": "✨", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "parent": "seedance-20", "antigravity": {"emoji": "✨", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "✨", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-vfx

VFX integration, energy effects, particle systems, and destruction physics for Seedance 2.0.

## Scope

- FX contract (source, scale, behavior, interaction, duration)
- Compositing language (foreground/background separation)
- Energy effects (beams, auras, shields, explosions)
- Particle system language
- Destruction physics (cracks, shattering, debris, shockwaves)
- Multi-VFX hierarchy for combined effects

## Out of scope

- Impact SFX sounds — see [skill:seedance-audio]
- CGI material properties — see [skill:seedance-style]
- Camera response to explosions — see [skill:seedance-camera]

---

## FX Contract (Required for Every Effect)

Every VFX element needs all five:

```
Source:      where does it originate?
Scale:       size relative to subject
Behavior:    drift / burst / swirl / dissipate / grow / shrink
Interaction: casts light / casts shadows / affects air / displaces objects
Duration:    when does it start, peak, and fade?
```

**Example:**
```
Sparks burst from the sword impact point, arc downward with gravity,
cool from white-orange to dark red, fade within 1 second.
```

---

## Compositing Language

Control foreground/background separation:

```
Foreground subject stays clean, FX behind subject only.
Light from the explosion briefly overexposes the frame, recovers in 0.3s.
Dust settles on the character's shoulders after the debris cloud passes.
FX casts colored light onto the character's face and hands.
```

---

## Energy Effects

### Beams / Rays

```
concentrated energy beam, [color], fired from [source] to [target],
[width: pencil-thin / fist-width / meter-wide], illuminates surrounding surfaces
```

### Auras / Fields

```
glowing aura surrounds the character, [color], pulsing with breath rhythm,
casting colored light on nearby surfaces, 30cm radius
```

### Shields / Barriers

```
translucent energy barrier, hexagonal lattice pattern,
ripples outward on impact point, [color], 2m diameter
```

### Explosions

```
energy collision produces [car-sized / building-sized] explosion,
shockwave expands radially at high speed, [debris type] launched outward,
fireball rises and cools from white to orange-red over 2 seconds
```

---

## Particle System Language

```
Density:    sparse / moderate / dense particle field
Emission:   particles emit from [source point], [direction: upward / radially / trailing], [speed: slow drift / fast burst]
Scale:      particle density increases with swing speed
Color temp: cold blue particles / hot orange embers / electric white sparks / acid green
Lifecycle:  particles spawn bright, dim over 0.5s, fade completely at 1s
```

---

## Destruction Physics

### Ground cracking

```
ground cracks radiate from impact point in [spider-web / linear / concentric] pattern,
cracks extend 3m radius, edges lift slightly
```

### Shattering

```
stone wall shatters into fragments, large chunks fall with gravity,
small debris sprays outward 5m, dust cloud erupts on impact
```

### Debris trajectory

```
fragments launch upward from impact, arc with gravity,
scatter across [2m / 5m / 10m] radius, embed in ground on landing
```

### Shockwave

```
visible shockwave distorts air, expands outward at [slow / fast] speed,
rustles loose objects and cloth within [3m / 10m] radius,
[crushes / bends] vegetation in path
```

---

## Multi-VFX Hierarchy

When multiple effects interact, specify the hierarchy to prevent visual chaos:

```
Primary:     sword slash emits ice-blue particle trail, 360° spiral per swing.
Secondary:   particles scatter on impact with enemy, burst into smaller sparks.
Tertiary:    ground freezes where particles land, ice crystals spread 1m radius.
Environment: cold mist rises from frozen ground, backlit by the blue glow.
```

---

## Agent gotchas

1. Never describe an effect without stating its duration. Open-ended VFX never resolves — the model loops or extends it randomly.
2. Specify whether VFX cast light on the subject. Explosions that don't light the foreground look composited and fake.
3. For fight impact effects: tie each VFX to a specific beat timestamp. Unanchored effects appear at wrong moments.
4. Multi-VFX beyond 3 simultaneous systems degrades coherence. Use the hierarchy format to prioritize.
5. Particle density and debris scale relative to subject: always state size relative to the character's body, not in abstract units.

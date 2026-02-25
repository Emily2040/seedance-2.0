---
name: seedance-motion
description: 'Control motion timing, beat density, action choreography, and sequential video extension chains for Seedance 2.0. Covers fight-scene physics, per-shot motion contracts, and multi-clip continuation techniques. Use when motion is too fast, too slow, or jittery, when choreographing action sequences, or when extending a video across multiple clips.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["motion", "choreography", "physics", "openclaw", "antigravity", "gemini-cli", "codex", "cursor"]
metadata: {"version": "3.3.0", "updated": "2026-02-25", "openclaw": {"emoji": "🏃", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "parent": "seedance-20", "antigravity": {"emoji": "🏃", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "🏃", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-motion

Temporal control, motion physics, action choreography, and video extension for Seedance 2.0.

## Scope

- Beat density guidelines per clip duration
- Timing language (timestamps, easing, stillness)
- Action choreography protocol (fight scenes, martial arts)
- Per-shot impact physics and grid method
- Sequential extension chains for long-form production

## Out of scope

- Camera framing and movement — see [skill:seedance-camera]
- VFX tied to impacts — see [skill:seedance-vfx]
- Audio per impact — see [skill:seedance-audio]

---

## Beat Density (Level 2–3)

Excessive beats cause jitter and morphing.

| Duration | Max changes |
|----------|-------------|
| 4–6s | 1 primary change |
| 8–10s | 1–2 changes |
| 12–15s | 2–3 changes (time-segmented) |

For Level 4 fight choreography: 6–8 beats per 5 seconds is achievable with precise specification.

---

## Timing Language

```
Timestamps:   0–3s: ... 3–6s: ... 6–8s: ...
Relative:     motion eases in over 2 seconds, then eases out
Terminal:     final frame holds for 0.8 seconds
Sequential:   starts walking slowly, then accelerates into a run while turning left
```

Always describe events in the order they occur. Jumbled temporal order breaks motion flow.

---

## Stillness Contracts

```
the subject is still, only subtle breathing
no idle swaying, no camera drift
wind is minimal, only small cloth movement
locked body, only eyes moving
```

---

## Action Choreography Protocol

### Per-shot micro-choreography

Number every shot with timestamps. Specify hit type, force direction, reaction physics, and sound per beat.

```
Shot 1 (0–0.6s): Full shot, locked. B throws right heavy punch at A's face.
SFX: drum "dong" + wind chase.

Shot 2 (0.6–1.2s): Close-up. A double-arm crossguard block, cloth tightens.
SFX: impact "peng" + cloth snap.

Shot 3 (1.2–1.8s): Medium. A wrist flip counter-throw, B micro-sway.
SFX: bone crack, ground dust puff.

Shot 4 (1.8–2.4s): Medium-long. B shoulder charge into A's chest, shockwave ripple.
SFX: heavy thud.

Shot 5 (2.4–3.0s): Low angle. A slides back, recovers low stance, dust trail.
SFX: scraping "ci" + wind settle.
```

### Impact physics — every hit specifies

- Contact type: punch / kick / block / throw / weapon strike
- Force direction: where does energy go?
- Reaction: body recoil / stagger / knockback distance / guard break
- Environment: dust cloud / ground crack / debris scatter / shockwave
- Sound: see [skill:seedance-audio] for layering

### The Grid Method (25宫格)

For maximum choreographic control, plan each beat as a table row:

| Beat | Camera | Action | SFX |
|------|--------|--------|-----|
| 1 | Full shot, locked | B right punch → A face | drum "dong" + wind |
| 2 | Close-up | A crossguard block | impact "peng" |
| 3 | Medium | A wrist flip counter | ground crack |

Convert each row to one sentence in the final prompt.

### Multi-character fight pattern

```
Characters: A references @Image1; B references @Image2.

Choreography:
A throws right hook at B's jaw.
B ducks, sweeps A's legs.
A jumps, lands spinning back kick to B's shoulder.
B staggers backward 2 steps.

Camera: medium shot tracking, slight handheld shake on impacts.
Sound: wet impact each hit, dust puff from ground, heavy breathing between exchanges.
```

---

## Sequential Extension Protocol

### Basic extension

```
Extend @Video1 by [X] seconds. New content: [description of what happens next].
```

Set generation duration = extension length (not total length).

### Continuity rules for extension

1. Re-upload character @Image references — don't rely on last frame alone (prevents identity drift)
2. Set creativity slider low (0.3–0.4) to stay close to source
3. Describe the continuation, not the whole scene again
4. Specify audio continuity: continues / changes / bridges

### Forward extension

```
Extend @Video1 forward by [X] seconds. Preceding content: [what comes before].
```

### Bridge between two clips

```
Generate a [X]-second bridge between @Video1 and @Video2. [Transition description].
```

### Novel-text chain

For adapting prose to sequential video:

1. Generate clip 1 from opening passage + style reference
2. For each subsequent clip: `Extend @VideoN by 15s. Content: [paste next paragraph].`
3. Always include same character @Image and style @Video references

The model reads narrative prose directly — no need to reformat as shot lists.

---

## Agent gotchas

1. Object integrity degrades under high-speed motion. Always add: `"weapon/prop shape stays consistent throughout."`
2. Describe events in chronological order. The model processes sequences left to right.
3. When extending: re-upload character references every time. Do not assume the last frame holds identity.
4. Beat density beyond guidelines causes jitter. For fight scenes, use the numbered shot format — it handles density better than prose.
5. `"slowly"` is not a timing word. Use `"over 3 seconds"` or `"eases in over 2s, holds for 1s."`

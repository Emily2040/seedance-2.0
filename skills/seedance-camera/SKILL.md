---
name: seedance-camera
description: 'Specify camera movement, shot framing, multi-shot sequences, and anti-drift locks for Seedance 2.0. Covers dolly, crane, orbit, push-in, one-take, and storyboard reference methods. Use when writing camera instructions, shooting a scene with a specific angle or movement, or fixing a wandering or locked camera.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["camera", "cinematography", "framing", "openclaw", "antigravity", "gemini-cli", "codex", "cursor"]
metadata: {"version": "3.7.0", "updated": "2026-02-26", "openclaw": {"emoji": "🎥", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "parent": "seedance-20", "antigravity": {"emoji": "🎥", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "🎥", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-camera

Camera movement, framing, multi-shot, one-take, and storyboard reference technique for Seedance 2.0.

## Scope

- Camera contract (framing + movement + speed + angle)
- Reliable phrasing for every camera move
- Multi-shot within one clip
- One-take (一镜到底) spatial journey technique
- Nine-grid storyboard reference method
- Anti-drift locks

## Out of scope

- Motion timing and beat density — see [skill:seedance-motion]
- Character staying consistent across shots — see [skill:seedance-characters]
- Fight choreography camera — see [skill:seedance-motion]

---

## Camera Contract (include for Level 2+)

Every shot needs all four:

```
Framing:   wide / medium / close-up / ECU / over-shoulder / full body
Move:      locked-off / dolly push / dolly pull / pan / tilt / orbit /
           handheld / crane / tracking
Speed:     slow / moderate / fast / "over 8 seconds"
Angle:     eye level / low angle / high angle / bird's eye / Dutch angle
```

---

## Reliable Phrasing Library

```
locked-off static camera, no movement
slow dolly push from medium shot to tight close-up over 8 seconds
slow dolly pull back revealing the full environment
slow pan left revealing [new element]
slow tilt up from [foreground] to [sky]
slow orbit left around the subject, constant distance
handheld tracking following the subject, subtle shake, not chaotic
rack focus foreground→background at 4 seconds
shallow depth of field, eyes in sharp focus
Hitchcock zoom (dolly out while zooming in)
crane shot rising from ground level to overhead
POV first-person perspective
low angle looking up at the subject
```

---

## Multi-Shot Within One Clip

2–3 shots is the reliable sweet spot. 4–8 is achievable for action (see [skill:seedance-motion]).

**Pattern:**
```
[Shot 1: Wide] Description. [Cut to: Close-up] Description. [Cut to: Medium] Description.
```

Rules:
- Restate the full shot after each cut marker
- Specify sound continuity: `"ambient continues across all shots"` or `"music hits the cut"`

---

## One-Take Technique (一镜到底)

Upload 3–5 scene images in sequence. Each = a waypoint on the camera path.

```
@Image1 @Image2 @Image3 @Image4 @Image5, one continuous tracking shot,
following the runner from the street up stairs, through a corridor, 
onto the rooftop, ending with a city overlook.
```

For POV one-takes:
```
First-person POV, walking through [environment], camera moves continuously without cuts.
```

---

## Nine-Grid Storyboard Method (九宫格)

When text descriptions become unwieldy, generate a storyboard image and use it as @Image1.

**Step 1 — Generate the storyboard:**
```
Create a 3×3 nine-panel storyboard for [scenario].
Panel 1: [description]. Panel 2: [description]. ... Panel 9: [description].
Professional storyboard illustration style, clear panel divisions.
```

**Step 2 — Upload and reference:**
```
Strictly follow the storyboard sequence from @Image1.
[Character from @Image2] performs the actions shown.
Match lighting and camera angles per panel. Smooth transitions between scenes.
```

The model reads sequential visual intent without reproducing the storyboard's layout or labels.

**Best for:** Complex multi-shot sequences, interior walkthroughs, action poses, non-filmmakers who can sketch.

---

## Portrait (9:16) Composition Rules

Changing aspect ratio changes composition logic:
- Reduce horizontal pans and orbit moves
- Prefer centered subject hierarchy
- Use vertical reveals instead of horizontal pans

---

## Anti-Drift Locks

If the camera wanders or floats:

```
locked horizon, stable framing, no rolling shutter
```

- Remove extra camera adjectives
- Choose ONE move only — never combine pan + orbit + tilt
- For subjects stationary relative to camera (riding, flying): `CAMERA MOUNTED ON [SUBJECT], LOCKED-ON SHOT, FIXED-TO-ACTOR`

---

## Agent gotchas

1. Never combine mutually exclusive moves: `locked-off + handheld`, `orbit + pan`, `tilt + dolly push` simultaneously.
2. Specify timing as duration, not speed word: `"over 8 seconds"` not `"slowly."` Speed words are vague.
3. For vehicle/mount shots: "CAMERA MOUNTED ON [SUBJECT]" prevents the model from misreading a moving subject as camera movement.
4. The word "cinematic" does nothing. Replace it with a physical camera description.
5. Horizontal pans in 9:16 portrait mode create ugly compositions. Always check aspect ratio before planning moves.


### R2V (Multi-Reference)

**Best for:** Professional pipelines requiring separate control of character, scene, camera, rhythm, and audio.

- Each reference gets ONE job. Don't give a single reference two conflicting roles.
- State role assignments before any other prompt content.
- When combining multiple characters from different references, attribute actions clearly.

**Common failures:** blended identities, camera mismatch, conflicting styles.  
**Fix:** simplify reference roles; drop the weakest reference.

---

## Module 03: Camera Language Codex

### Camera Contract (Always Include for Level 2+)

- **Framing:** wide / medium / close-up / extreme close-up / over-shoulder / full body
- **Movement:** locked-off / dolly (push/pull) / pan / tilt / orbit / handheld / crane / tracking
- **Speed:** slow / moderate / fast (or explicit timing: "over 8 seconds")
- **Angle:** eye level / low angle / high angle / bird's eye / Dutch angle

### Reliable Phrasing Library

- `locked-off static camera, no movement`
- `slow dolly push from medium shot to tight close-up over 8 seconds`
- `slow dolly pull back revealing the full environment`
- `slow pan left revealing [new element]`
- `slow tilt up from [foreground] to [sky/background]`
- `slow orbit left around the subject, constant distance`
- `handheld tracking following the subject, subtle shake, not chaotic`
- `rack focus foreground→background at 4 seconds`
- `shallow depth of field, eyes in sharp focus`
- `Hitchcock zoom (dolly out while zooming in)`
- `crane shot rising from ground level to overhead`
- `POV first-person perspective`
- `low angle looking up at the subject`

### Multi-Shot Within One Clip

Use explicit cut markers and restate the whole shot after each cut.

**Pattern:**
```
[Shot 1: Wide] Description. [Cut to: Close-up] Description. [Cut to: Medium] Description.
```
Or: `Shot 1: ... Lens switch. Shot 2: ... Lens switch. Shot 3: ...`

**Rules:**
- **2–3 shots** is the reliable sweet spot for most content.
- Advanced users can push to 4–8 micro-shots for action choreography (see Module 04B), but expect higher failure rates.
- Specify whether sound bridges the cut: `"ambient continues across all shots"` or `"music hits the cut."`

### One-Take (一镜到底) Technique

Seedance 2.0 is particularly strong at continuous one-take shots with spatial transitions.

**Pattern:** Upload 3–5 scene images in sequence + describe a continuous path.

**Example:**  
```
@Image1 @Image2 @Image3 @Image4 @Image5, one continuous tracking shot, following the runner from the street up stairs, through a corridor, onto the rooftop, ending with a city overlook.
```

The model transitions between referenced environments while maintaining spatial continuity. Each image represents a waypoint on the camera path.

**For POV one-takes:**  
```
First-person POV, walking through [environment], camera moves continuously without cuts.
```

### Anti-Drift Camera Locks

If the camera wanders:
- Add `"locked horizon, stable framing, no rolling shutter."`
- Remove extra camera adjectives.
- Choose ONE move only (don't combine pan + orbit + tilt).
- For characters stationary relative to camera (e.g., riding a vehicle): use `CAMERA MOUNTED ON [SUBJECT], LOCKED-ON SHOT, FIXED-TO-ACTOR` to prevent misinterpretation.

---

## Module 03B: Storyboard Reference Technique

### The Nine-Grid Method (九宫格)

Instead of writing complex per-shot descriptions, create a visual storyboard and let the model follow it.

### Workflow

1. **Generate a storyboard image:** Use an image model (Seedream, Nano Banana Pro, etc.) to create a nine-panel grid showing your shot sequence. Include brief text labels if needed.

**Example image-generation prompt for the storyboard:**
```
Create a 3x3 nine-panel storyboard for [scenario]. 
Panel 1: [description]. Panel 2: [description]. ... Panel 9: [description]. 
Professional storyboard illustration style, clear panel divisions.
```


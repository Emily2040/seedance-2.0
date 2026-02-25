
3. **Write a minimal prompt:**
```
Strictly follow the storyboard sequence from @Image1. [Character from @Image2] performs the actions shown. 
Match lighting and camera angles per panel. Smooth transitions between scenes.
```

### When to Use This

- Complex multi-shot sequences where text description becomes unwieldy.
- Interior walkthroughs (upload floor plan + storyboard panels).
- Action choreography with specific pose references.
- When working with non-filmmakers who can sketch/illustrate but can't write shot lists.

### Key Insight

The model is intelligent enough to read the storyboard's visual information without reproducing the storyboard's layout or text labels in the generated video. It extracts the sequential visual intent.

---

## Module 04: Motion & Temporal Control

### Beat Density

A clip is not a montage. Excessive beat density causes jitter, morphing, and incoherent physics.

**Guidelines for Level 2–3 prompts:**
- **4–6s:** 1 primary change
- **8–10s:** 1–2 changes
- **12–15s:** 2–3 changes (time-segmented)

For Level 4 (action choreography), see Module 04B for adjusted guidelines.

### Timing Language

- **Timestamps:** `0–3s: ... 3–6s: ... 6–8s: ...`
- **Relative:** `motion eases in over 2 seconds, then eases out`
- **Terminal:** `final frame holds for 0.8 seconds`
- **Sequential:** `starts walking slowly, then accelerates into a run while turning left`

**Respect chronological order.** Jumbled temporal descriptions break motion flow. Always describe events in the order they should occur.

### Stillness (Positive Constraints)

- `the subject is still, only subtle breathing`
- `no idle swaying, no camera drift`
- `wind is minimal, only small cloth movement`
- `locked body, only eyes moving`

### Continuity Anchors

- Keep at least one constant: lighting direction, camera height, or subject orientation.
- If motion jitters: reduce simultaneous moving parts. Rain + crowd + handheld + whip pan = stutter.
- For multi-shot: `"maintain character consistency across all shots, same lighting direction."`

---

## Module 04B: Action Choreography Protocol

### Why Action Deserves Its Own Module

Fight scenes, martial arts, and intense physical choreography are the dominant use case driving Seedance 2.0 adoption. The model handles surprisingly dense action when prompted correctly, exceeding the conservative beat-density guidelines of Module 04.

### The Per-Shot Micro-Choreography Approach

For dense action, use numbered camera/shot designators with timestamps, specific hit types, and reaction physics:

```
Shot 1 (00:00.0–00:00.6): Full shot, locked. B throws right heavy punch at A's face. 
SFX: drum hit "dong" + wind chase.

Shot 2 (00:00.6–00:01.2): Close-up. A blocks with crossed arms, guard stance. Cloth wraps tight. 
SFX: impact "peng" + cloth stretch.

Shot 3 (00:01.2–00:01.8): Medium shot. A flips wrist for counter-throw, body micro-sways. 
SFX: ground crack. Bone micro-sound.

Shot 4 (00:01.8–00:02.4): Medium long shot. B shoulder-checks A's chest. 
SFX: red shockwave disperses.
```

### Impact Physics Language

Every hit should specify:
- **Contact type:** punch, kick, block, throw, weapon strike
- **Force direction:** where does the energy go?
- **Reaction physics:** body recoil, stagger, guard break, knockback distance
- **Environmental response:** dust cloud, ground crack, debris scatter, shockwave
- **Sound per impact:** use onomatopoeia or descriptive SFX

### The Grid Method (25宫格)

For maximum choreographic control, create a grid where each cell is one beat:

| Beat | Camera | Action | SFX |
|------|--------|--------|-----|
| 1 | Full shot, locked | B right punch → A face | drum "dong" + wind |
| 2 | Close-up | A crossguard block | impact "peng" |
| 3 | Medium | A wrist flip counter | ground crack |

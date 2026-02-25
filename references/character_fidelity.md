### Style Compression (When Prompt Is Too Long)

Keep only 2–3 style tokens: `"anamorphic feel, subtle grain, muted palette."`

### Animation / Anime Control

Use concrete production descriptors:
- `clean linework, limited shading, 2D animation, motion on twos, smear frames on fast turns`
- `watercolor wash backgrounds, ink outline characters`
- `3D cel-shaded, bold outlines`

Avoid naming studios or series.

### Period / Historical Control

Specify materials and lighting of the era:
- `oil lamp practicals, soot-stained walls, handwoven wool, iron hardware`
- `1970s film stock, warm yellows, faded contrast, wide collars`

### Style Transfer via Reference

The most reliable way to control style is to upload a reference:
- `Match the visual style, color grading, and film texture of @Video1`
- `Apply @Image1's artistic style and color palette to the scene`

The model excels at extracting and replicating: color grade, contrast, film grain, lighting mood, compositional style, and editing rhythm from references.

---

## Module 08: Edge Case Grimoire

### Master Troubleshooting Ladder (Use in Order)

1. Shorten prompt (remove adjectives, keep contracts).
2. Remove conflicts (one camera move, one lighting idea, one primary action).
3. Reduce beat density (fewer changes per second).
4. Lock camera (or simplify to slow dolly only).
5. Anchor subject with @Image reference.
6. Add time segmentation.
7. Switch to Level 1 (minimal intent) and let the model direct.

### Common Failures and Fixes

| Problem | Fix |
|---------|-----|
| **Extra limbs / warped hands** | Reframe hands out of shot; simplify action; specify "hands not visible." |
| **Face melt mid-clip** | Reduce motion; avoid extreme close-up; lock lighting; avoid rapid expression changes; re-upload face reference. |
| **Camera drift / float** | Use "locked-off static camera"; remove "cinematic" filler; specify "no drift, no floating." |
| **Flicker / exposure pumping** | Specify "stable exposure, no flicker"; reduce flickering light sources. |
| **Stutter / jitter motion** | Simplify choreography; remove simultaneous moving elements (rain + crowd + handheld + whip pan = stutter). |
| **Background morphing** | Add environment reference @Image; reduce orbit/pan moves; simplify background description. |
| **Bad text / watermarks** | Avoid on-screen text generation; if required, keep 1–3 words maximum. |
| **Audio desync** | Shorten dialogue; use medium close-up; specify clear pauses; reduce visual complexity. |
| **Identity drift during extension** | Re-upload original character reference images; lower creativity slider; describe continuation, not the whole scene. |
| **Object disappearing under fast motion** | Reinforce object description; add "weapon/prop stays consistent throughout"; reduce motion speed. |
| **Content policy violation** | Remove real-person references, IP names, copyrighted characters. Redesign toward originality. |

---

## Module 08B: Known Platform Behaviors

**LIVING DOCUMENT — Q1 2026**

Record observed behaviors here and update quarterly.

### Current Observations

- The model has strong **"director intelligence"** — for common domains, minimal prompts outperform over-specification.
- Character consistency via @Image reference is remarkably strong, even across lighting changes and camera angles. The model achieves **near-perfect lighting fusion** when placing characters into new environments.
- The model independently selects appropriate camera techniques, shot sizes, and editing rhythms when given freedom (Level 1–2 prompts).
- Fight choreography with per-second specifications works at surprising density (6–8 beats per 5 seconds achievable).
- **Audio emotion can be modified** — the model can make a flat voice reference sound "more excited" when instructed.
- 720p output quality is aesthetically sufficient for most social media and content marketing use cases. Film grain and natural softness at this resolution often look more "real" than artificially sharp upscaled content.
- The model can read and follow novel/prose text directly, generating appropriate cinematography without production-formatted prompts.
- **Object integrity degrades under high-speed motion** (weapons, small props). Explicit reinforcement helps.
- The storyboard-as-reference technique works well — the model extracts sequential visual intent without reproducing the storyboard format.

---

## Module 09: Quality Assurance

### Pre-Render QA Checklist

- [ ] Prompt is structured (subject → action → camera → style → constraints).
- [ ] Appropriate delegation level chosen (Level 1–4).
- [ ] @Tag roles are explicit (each reference has one job).
- [ ] No IP/celebrity/real-person targeting.
- [ ] Camera: framing + movement + timing specified (Level 2+).
- [ ] Light: named source + contrast specified (Level 2+).
- [ ] Motion: beat density appropriate for duration.
- [ ] Exit: final frame holds 0.5–1s (if applicable).
- [ ] Sound: either designed or intentionally delegated.
- [ ] No conflicting instructions (checked for mutual exclusivity).
- [ ] For extensions: character reference images re-uploaded.

### Compression Ladder (When Prompt Feels Too Long)

Cut in this order:
1. Remove filler adjectives ("beautiful," "amazing," "stunning").

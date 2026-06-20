# Field-Observed Tips

last_verified: 2026-05-30

These are practitioner patterns gathered from public community material. Treat them as field-observed, not official platform guarantees.

## Stable Workflow

1. Draft short before long: test 3-5 seconds before spending on a 10-15 second clip.
2. Change one variable per retry: camera, lighting, motion, or reference role.
3. Bind every reference asset to one job.
4. Use locked framing for fragile identity, product logos, readable text, lip-sync, hands, or complex VFX.
5. Use video references for motion rhythm or camera behavior, not unauthorized identity transfer.
6. Use audio references for tempo, mood, or ambience unless the voice/music is owned, licensed, or authorized.
7. Prefer edit, extend, or segment replacement over regenerating a whole clip when only one beat fails.
8. For continuation, save the returned last frame when the surface supports it and use it as the next first-frame anchor.
9. If an audio reference should control timing, mute competing reference videos before upload or explicitly lower their role to camera/motion only.
10. For sequences, write down the observed final state before asking for the next prompt; do not assume the planned endpoint occurred.

## Prompt Discipline

| Weak pattern | Stronger pattern |
|---|---|
| `cinematic, epic, beautiful` | `soft side backlight, wet asphalt reflections, locked medium shot, quiet room tone` |
| `make it move naturally` | `shoulders rise once with breathing, hand releases the cup, final pose holds for one second` |
| `use this video as style` | `[Video1] provides only side-tracking camera rhythm; do not transfer performer identity or background` |
| `make product luxury` | `narrow warm light sweep across the label, black acrylic table reflection, no label redesign` |

## High-Risk Areas

- Fast hand gestures.
- Small text, signs, logos, labels, and subtitles.
- Multi-character action without tags.
- Multiple simultaneous camera moves.
- Product transformations when identity must stay fixed.
- Real-person faces, voices, celebrity likeness, and protected characters.
- Long script-like prompts that ask for too many cuts, locations, and character turns in one generation.
- Extension chains without a last-frame anchor; quality and continuity can degrade across retries.
- Sequence chains where completed beats, reserved beats, or exact reference tags are not logged.

## Safe Hidden Trick

The best "trick" is not bypassing filters. It is making intent legible: source, role, action path, camera endpoint, light source, sound cue, and constraint.

# Cinematography Shot Language

Use this reference when a user needs director/DP-grade shot design instead of generic cinematic adjectives.

## Shot Contract

Every professional shot should declare:

| Field | Prompt decision |
|---|---|
| Shot size | extreme wide, wide, medium wide, medium, medium close-up, close-up, extreme close-up, macro |
| Angle | eye-level, low angle, high angle, overhead, profile, over-shoulder, insert, product three-quarter |
| Lens feel | wide spatial energy, natural 35mm perspective, portrait compression, macro material detail |
| Camera support | locked-off, handheld, slider, dolly, crane, drone, gimbal, virtual product table |
| Movement | push-in, pull-back, lateral track, orbit, pan, tilt, pedestal, crane up, reveal, rack focus |
| Subject relation | camera follows, leads, discovers, holds, observes, or blocks with the subject |
| Start frame | first readable composition |
| End frame | changed state, pose, reveal, product hero, or continuity handoff |
| Fragile anchors | face, hands, logo, text, product shape, wardrobe, prop position |

Prompt pattern:

`Shot: [size/angle/lens feel]. Camera starts [composition], [one movement] at [speed] while [subject action], ending on [clear endpoint]. Preserve [fragile anchors].`

## Ending Profiles

`[clear endpoint]` is not one thing. Pick the ending by what happens to the clip **next**, then write the last beat to deliver it. Choosing before drafting is what stops a clip that has to be extended from resolving into stillness, and a clip that has to stand alone from trailing off mid-gesture.

| Profile | Final state | Use when |
|---|---|---|
| Resolve | action completes, motion settles, result readable | standalone clips, demos, anything that has to feel finished |
| Extension anchor | motion, gaze, camera, and ambience still directionally live | the next clip continues this shot — see `[ref:continuation-handoff]` |
| Loop seam | position, motion phase, exposure, and audio can rejoin the opening | social loops, ambient backgrounds, hero product spins |
| Hero hold | subject stable, unobstructed, and legible long enough to read | products, logos, packshots, anything a viewer must actually see |
| Edit point | visual and audio land on a clean boundary | the clip is a cut, insert, or replacement in a larger edit |
| Reveal or punch | the peak intentionally lands on the final frame | scares, jokes, title handoffs, transformation payoffs |

**A good ending is not always a moving ending — and where it is, the motion has to be the right motion.** Two profiles need movement through the final frame and two are damaged by it:

- **Extension anchor:** motion continues and stays directionally live, because the next clip picks it up.
- **Loop seam:** motion continues and must be *phase-matched* to the opening — same velocity, same point in the cycle. A hero product spin that decelerates to a stop hitches just as visibly as one whose phase is wrong. Stopping is a defect here, not a safe default.
- **Hero hold** and **reveal or punch:** trailing motion blurs the thing the viewer came to read, or softens the beat the clip was built for. Settle.
- **Resolve** and **edit point:** settle, cleanly.

So the error is not motion as such; it is *unmatched* motion — movement at the final frame that nothing downstream consumes. Adding drift by reflex to make an ending feel alive is the more common mistake than ending too still, but prescribing stillness everywhere breaks loops.

Two consequences worth stating. An extension anchor must leave `open motion` explicit, because that is what the next clip opens from. A loop seam must match the opening state on all four of position, motion phase, exposure, and audio — three out of four reads as a visible jump.

## Shot Size Use

| Shot size | Use for | Seedance caution |
|---|---|---|
| Extreme wide | scale, arrival, environment | small faces/logos will drift; do not demand facial acting |
| Wide | blocking, dance, movement, product-in-environment | keep action simple and readable |
| Medium | dialogue, product use, handoff | good default for character commercials |
| Close-up | emotion, texture, lip-sync, product detail | keep camera stable and action small |
| Macro | material, food, jewelry, mechanics | avoid large motion and text redraw |

## Camera Movement Grammar

- **Locked-off:** use for lip-sync, product identity, text, logos, precise VFX, and continuity anchors.
- **Dolly/push-in:** use for discovery, realization, intimacy, product reveal.
- **Lateral track:** use for travel, procession, choreography, passing foreground layers.
- **Orbit:** use for product hero and statuesque subjects; avoid if identity must remain stable from one angle only.
- **Crane/drone:** use for scale, arrival, geography, reveal; avoid for dialogue or tiny product text.
- **Handheld:** use for realism or tension; keep movement subtle when identity matters.
- **Rack focus:** use for attention shift between two anchored objects; avoid stacking with complex camera moves.

## Blocking and Coverage

For multi-shot scenes, keep camera grammar motivated:

1. Establish geography and screen direction.
2. Move to character/product action.
3. Use close detail only when the detail changes the story.
4. End each clip with a frame that can become the next first-frame reference.

Coverage pattern:

`Shot 1 wide establishes [space/screen direction]. Shot 2 medium follows [action]. Shot 3 close-up reveals [consequence]. Continuity: same wardrobe, prop, light direction, and eyeline.`

## Professional Avoid List

Avoid: `cinematic camera`, `dynamic shot`, `epic zoom`, `film look`, `Hollywood style`, `beautiful composition` without physical shot choices.

Replace with: shot size, support, movement, subject relation, motivated light, endpoint, and fragile anchors.

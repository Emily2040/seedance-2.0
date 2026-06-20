---
name: seedance-motion
description: "This skill should be used when the user asks for body action, choreography, physics, object movement, movement timing, action continuity, stunt direction, or motion-reference mapping in Seedance 2.0."
license: MIT
user-invocable: true
tags:
  - motion
  - choreography
  - physics
  - seedance-20
metadata:
  version: "6.0.0"
  updated: "2026-06-20"
  parent: "seedance-20"
  author: "Iamemily2050 (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: "🎬"
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-motion

Use physical verbs and consequences. Motion should be observable on screen, timed within the clip, and assigned to a subject or object. Prefer one strong action with a visible endpoint over several vague actions competing for attention.

Load `[ref:reference-workflow]` for video-motion references, `[ref:shot-list-continuity]` for action handoffs across shots, and `[ref:examples-by-mode]` for safe edit, extend, and R2V patterns.

## Intent

Motion is the verb of the user's story - the thing they came to see HAPPEN. The soul here is consequence: motion that begins, lands, and changes something feels lived; motion that loops feels generated. Every action carries the story one beat forward, or it doesn't belong in the clip.

## Motion Contract

State: actor/object, action, force level, timing, physical consequence, continuity requirement, and endpoint.

| Motion type | Strong phrase | Weak phrase |
|---|---|---|
| Subtle acting | `Character A inhales, grips the cup tighter, then sets it down without looking away` | `she feels nervous` |
| Product material | `condensation beads gather, merge, and slide down the bottle neck` | `the product looks refreshing` |
| Choreography | `Character B ducks under the swinging bag, pivots left, and stops in a guarded stance` | `fast action fight scene` |
| Object physics | `paper receipt lifts in the fan breeze, flips once, and lands face-up` | `papers move dynamically` |
| Environmental motion | `rain streaks diagonally across the backlight while puddle ripples spread from footsteps` | `stormy weather atmosphere` |

## Physics-Forward Pattern

Official material claims strong physics; extract it by writing causes and letting the model compute consequences (field-observed emphasis - test before promising results). State mass, force, and material, then name one consequence the camera can see: `the heavy oak door swings shut and the candle flames bend toward it` beats `the door closes dramatically`. Consequences prove the action: weight shows in landing compression, momentum in overshoot and recovery, friction in skid length, wind in what it displaces. One physical cause with two or three visible consequences reads stronger than three separate actions.

## Timing Pattern

Use a three-beat structure for short clips: setup, action, changed end state. Example: `0-2s: candle flame steady; 2-4s: door opens and flame bends; 4-6s: smoke trail curls toward the hallway`. Time segmentation is useful for action, VFX, lip-sync, and product demonstrations, but avoid frame-perfect overload unless the user truly needs it.

When sound drives the motion, pair each visible change with one beat or SFX: `door click at 2s, light pulse on the downbeat, hand releases the cup on the final chime`. Do not ask for many cuts, locations, and micro-actions inside one short clip.

## Reference Motion Rules

For reference footage, use only owned, licensed, public-domain, stock, mocap, rehearsal, or self-recorded material. Map `[Video1]` to motion, camera, timing, or blocking, not identity, unless the identity is authorized. If a reference contains a real person, transfer only general motion or camera behavior and explicitly exclude likeness transfer.

## Stability Rules

Hands, faces, logos, and product geometry drift when too many actions occur. Reduce motion around fragile details: lock the camera for lip-sync, keep hands in simple poses, ask product parts to remain rigid, and move light or environment instead of the core identity anchor.

## Sequence State

When sequence state is present, inherit the observed action phase, open motion vector, current clip scope, continuity locks, exact reference tags, and reserved future beats. Do not replay actions marked already happened or completed. Do not perform a reserved beat early; carry unfinished motion from the accepted end state into the next clip.

## Output Contract

Return the motion phrase, timing pattern, reference role map if any, and repaired prompt language.

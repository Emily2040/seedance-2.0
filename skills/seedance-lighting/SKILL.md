---
name: seedance-lighting
description: "This skill should be used when the user asks for lighting design, atmosphere, time of day, color temperature, shadow, reflections, weather light, practical lights, or mood transitions in Seedance 2.0."
license: MIT
user-invocable: true
tags:
  - lighting
  - atmosphere
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

# seedance-lighting

Lighting should describe physical sources and transitions, not abstract beauty. A useful lighting prompt tells the model where the light comes from, its color temperature, how shadows behave, what atmosphere catches the light, and whether the light changes during the clip.

Load `[ref:color-pipeline-aces]` when the user asks for ACES, HDR/SDR, show look, grade, LUT, CDL, product color, or professional color handoff.

## Intent

When users say mood words, they are almost always asking for light. This skill's purpose is to take "cozy," "lonely," or "electric" and answer with a sun, a lamp, or a window - because that is where feeling physically lives in a frame. Give them their emotion back as a light source they can point to.

## Lighting Contract

State: key source, direction, color temperature, atmosphere, shadow behavior, reflective behavior, and any transition.

| Mood or task | Prompt-ready lighting | Why it works |
|---|---|---|
| Product luxury | `narrow warm strip light sweeps across brushed metal, black acrylic reflection remains clean` | Material and reflection are controlled. |
| Night drama | `warm practical lamp from frame left, blue moonlight rim on shoulders, soft hallway shadows` | Uses motivated sources. |
| Discovery | `door crack opens and a thin white beam widens across dust in the air` | Light changes with the action. |
| Food realism | `large soft window light from the right, gentle bounce on the plate, no harsh specular glare` | Keeps texture readable. |
| Storm atmosphere | `cool overcast daylight, intermittent lightning flashes briefly sharpen the silhouette` | Weather affects contrast. |

## Source Selection

Use **practical lamps** for interiors, intimacy, and visible motivation. Use **window light** for naturalism and food or lifestyle scenes. Use **rim light** when separation matters. Use **hard light** for noir, harsh sun, or graphic shadows. Use **soft light** for beauty, skin, product polish, and children or family scenes. Use **moving light** when the scene needs a visible change.

## Color and Atmosphere

Name color temperature only when it matters: warm tungsten, cool moonlight, green fluorescent, sodium streetlight, neutral overcast daylight. Add atmosphere sparingly: mist, dust, rain streaks, smoke, or condensation should interact with the light and the subject, not merely decorate the frame.

## Failure Fixes

If an output looks flat, add a motivated key source, rim separation, and one material-specific highlight. If it looks over-processed, remove broad style claims and specify softer contrast. If flicker or lighting jumps appear, make the light source stable and remove competing transitions.

## Sequence State

When sequence state is present, inherit persistent practical sources, key direction, lighting phase, current clip scope, continuity locks, exact reference tags, and reserved future beats. Do not reset day/night, practical lamps, or weather light unless the transition or allowed changes explicitly permit it.

## Output Contract

Return a compact lighting block, a transition note if needed, and one prompt-ready integrated sentence.

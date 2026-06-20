---
name: seedance-characters
description: "This skill should be used when the user asks for character consistency, character tags, identity lock, multi-character blocking, wardrobe continuity, hand safety, expression control, or likeness-sensitive character guidance."
license: MIT
user-invocable: true
tags:
  - characters
  - identity
  - consistency
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

# seedance-characters

Use this for identity, consistency, multi-character blocking, wardrobe continuity, hand safety, expression control, and likeness-sensitive character guidance. Character prompting must remove ambiguity before adding style.

Load `[ref:shot-list-continuity]` when character identity, wardrobe, props, eyeline, screen direction, or emotional state must survive across multiple shots.

## Intent

The user is protecting someone here - a character they invented, a product they built, or a person they love. Identity is trust: when a face drifts, the user feels it as betrayal, not as a rendering artifact. Treat every recurring character as a continuing cast member with memory and a contract, never as a stranger re-cast for each clip.

## Character Contract

Assign each character a stable tag: `Character A`, `Character B`, `[Image1] subject`, or a user-provided original name. After more than one character appears, do not use ambiguous pronouns. Keep tag, role, appearance, wardrobe, position, action, and emotional beat consistent.

| Field | Prompt use |
|---|---|
| Tag | `Character A` or `[Image1] subject` |
| Identity anchor | Age range, silhouette, hair, wardrobe, or authorized reference role |
| Position | Foreground/background, left/right, seated/standing |
| Action | One assigned verb and endpoint |
| Expression | Observable behavior such as blink, glance, smile, grip, pause |
| Constraint | What must stay unchanged |

## Multi-Character Blocking

Assign actions separately: `Character A lowers the envelope; Character B remains in the doorway`. Do not write `they argue dramatically` when the model must decide who moves. If contact occurs, describe the contact point and endpoint. For crowd scenes, identify the hero subject and keep background motion simple.

## Three-Tier Action Hierarchy

Field-observed from Chinese production practice; the strongest known stabilizer for multi-person scenes. Give every visible person an action from exactly one tier:

1. **Persistent micro-motion** - breathing, blinks, slight shoulder movement, hair drift, drifting gaze. Continuous, no gaps; this is the default tier for everyone who is not the focus.
2. **One focused response** - a single person gets one small reaction with an explicit time window: `Character B's lip corner lifts and she holds a half-second glance`.
3. **Large actions - prohibited by default.** In multi-person shots, explicitly exclude standing, walking, turning, posture changes, and object pickup unless one of them is the shot's single beat. Character-to-prop physics (lifting a glass, passing an object) is fragile with multiple people on screen - keep contact simple or move it off-screen.

## Hand and Face Stability

Hands and faces degrade under complex choreography. Keep hands visible but simple, avoid rapid finger actions, avoid face-touching during dialogue, and lock the camera for lip-sync or portrait preservation. Use props to show emotion when facial precision is fragile.

## Likeness Rule

For real-person likeness, do not infer consent from an uploaded asset. Treat portrait, face, and voice workflows as authorization-dependent and surface-specific. If authorization is unclear, rewrite to an original character archetype while preserving the scene function.

## Sequence State

When sequence state is present, inherit wardrobe, hair, screen geography, eyeline, pose, emotional state, current clip scope, continuity locks, exact reference tags, and reserved future beats. Canonical identity references control identity; accepted footage controls transient opening state. Do not let a motion or continuity source overwrite immutable character locks.

## Output Contract

Return a character card, tag map, action assignments, continuity constraints, and any safety or authorization note.

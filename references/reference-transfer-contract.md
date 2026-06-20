# Reference Transfer Contract

Use this reference when images, videos, audio, previous clips, final frames, or interface tags appear in a sequence.

## Exact Tag Rule

Preserve every user-supplied reference tag exactly. Never invent, normalize, translate, reformat, renumber, correct spacing, or change case in tags such as `@Image1`, `@Image 1`, `[Image1]`, `[Video 1]`, or interface-provided equivalents.

## Role Separation

Assign each reference one primary role:

- image: identity, product, pose, costume, environment, first frame, or last frame;
- video: source clip, motion, camera, timing, blocking, or continuity source;
- audio: tempo, ambience, music phase, rhythm, delivery tone, or active dialogue source;
- final frame: observed state or target endpoint.

State what transfers and what must not transfer. R2V and continuation work fail when identity, motion, camera, environment, and audio roles bleed together.

## Continuity Source Versus Motion Reference

A canonical identity reference controls immutable identity. An accepted previous clip or final frame controls transient opening state. A donor video can control motion or camera only when explicitly allowed. Do not let a motion reference overwrite character identity, wardrobe, product geometry, or accepted state.

## Multi-Subject Selector

When a reference contains multiple subjects, identify the intended subject by position, tag, role, or visible feature. Do not assume the central or largest subject is correct when the user has not said so.

## Transfer And Ignore Clause

Every role-bound reference should be expressed as:

`[ReferenceTag] controls [role] only; ignore [identity/environment/logo/audio/camera/motion] from that reference.`

Use only owned, licensed, public-domain, stock, self-recorded, or clearly authorized references for protected identity, voice, brand, logo, or performance transfer.

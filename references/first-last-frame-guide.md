# First/Last Frame Guide

last_verified: 2026-08-01

Use this guide for FLF2V, first-frame/last-frame transitions, Chinese `首帧/尾帧`, or requests to generate the motion between two images.

Reviewed 2026-08-01. The endpoint-lock craft below is unchanged and model-independent. One boundary was added: these are Seedance 2.0 surface behaviours, and the newer 2.5 line is reported to offer region-level editing — a different tool for a different job, not a replacement for first/last-frame control. Do not assume either mode exists on the other line without checking the active surface. See [api-status](api-status.md).

Source boundary: official ByteDance material supports multimodal references, editing, extension, and R2V examples. Volcengine now documents first-frame and last-frame roles on its video-generation surface. The exact `FLF2V` label is still product-surface vocabulary, so use the active surface's field names when implementing.

## Core Principle

The first frame defines where the clip begins. The last frame defines the target state. The prompt should describe only the transition logic, camera behavior, lighting continuity, audio intent, and what must stay unchanged.

## Reference Roles

| Role | English wording | Chinese wording | Russian wording |
|---|---|---|---|
| First frame | `@Image1 is the first frame.` | `@图片1 为首帧。` | `@Image1 как первый кадр.` |
| Last frame | `@Image2 is the last frame.` | `@图片2 为尾帧。` | `@Image2 как последний кадр.` |
| Identity lock | `Preserve the same subject identity, outfit, shape, and scene logic.` | `保持同一主体、服装、形状和场景逻辑。` | `Сохранить того же персонажа, одежду, форму и логику сцены.` |
| Transition only | `Generate only the motion between the two frames.` | `只生成两帧之间的连续动作。` | `Сгенерировать только переход между кадрами.` |

## Surface Field Notes

| Surface | Practical wording |
|---|---|
| Volcengine/Ark | Use current docs to verify `first_frame`, `last_frame`, `image_with_roles`, duration, resolution, and whether video/audio references can be mixed with first/last-frame mode. |
| Runway | Use `promptImage` positions such as `first` or `last` on the Runway surface, and recheck the current API docs before assuming field parity with Volcengine. |
| ComfyUI / partner workflows | `FLF2V` is useful workflow shorthand, but still confirm the node's exact inputs and face/portrait policy. |

## Prompt Template

```text
@Image1 is the first frame. @Image2 is the last frame.
Preserve [subject/product/character], [outfit/logo/shape], and scene layout.
Generate a continuous transition from [starting state] to [ending state].
Motion: [one physical action path].
Camera: [one controlled move or locked frame].
Lighting: [source and continuity].
Sound: [ambience/dialogue/SFX/music/silence].
Constraints: no new text, no watermark, no identity change, no object redesign.
```

## Product-Safe Transition

`@Image1 is the first frame and @Image2 is the last frame. Preserve the bottle logo, label, glass shape, cap geometry, and color exactly. Only the condensation and light change: droplets gather at the shoulder, slide toward the label, and a narrow warm highlight travels left to right. Camera stays locked in a medium product shot. Sound: low room tone, one soft glass tick at the end.`

## Character-Safe Transition

`@Image1 is the first frame and @Image2 is the last frame. Preserve the original character's face structure, hairstyle, jacket, and room layout. The character slowly stands from the chair, turns toward the window, and stops in the final pose. Camera: locked medium shot with a slight push-in. Lighting: same cool window light, warmer lamp glow at the end. Sound: quiet room tone and soft floor creak.`

## Transformation Method

Field-observed technique; test before promising results. Transformations succeed when the prompt names the two endpoint states plus the persisting carrier - the element that survives the change and carries continuity: a logo, a silhouette, a light source, a camera position.

- State A, state B, and the carrier: `the paper crane unfolds into a flat sheet; the red wax seal stays fixed at center frame throughout.`
- Let the carrier own the eye-line: the viewer tracks the unchanged element while everything around it transforms, which hides intermediate-frame weirdness.
- Hard cases decompose into first/last-frame steps: generate A → carrier-stable midpoint, then midpoint → B as a second FLF2V pass, and cut them together.
- Match-cut variant: hold the carrier's screen position and scale across the cut and let the surroundings swap.

## Common Failures

| Failure | Repair |
|---|---|
| Subject morphs | Lock only the identity anchors that matter; remove extra style changes. |
| Product/logo redraws | Use locked camera and say only light/weather moves. |
| Jump cut | Add "continuous transition" and one physical action path. |
| Camera chaos | Replace multiple moves with locked frame or one slow push-in. |
| Ending misses target | State that `@Image2` is the final visual target, not just mood reference. |

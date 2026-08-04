---
name: seedance-vocab-zh
description: "This skill should be used when the user asks for Chinese Seedance 2.0 prompt wording, Mandarin cinematic vocabulary, Chinese prompt compression, or translation of camera, lighting, action, VFX, audio, and production terms into Chinese."
license: MIT
user-invocable: true
tags:
  - chinese
  - vocabulary
  - seedance-20
metadata:
  version: "6.7.0"
  updated: "2026-08-01"
  parent: "seedance-20"
  author: "Iamemily2050 (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: "🎬"
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-vocab-zh

Before producing prompt text, a prompt-ready block, a rewrite, an example, or a compiled clip, load the [Director's Read](../../references/directors-read.md), classify the brief, and complete its canonical narrative or non-narrative record. Translate that record into visible or audible carriers and keep its internal labels out of final generation prose.

Use Chinese vocabulary when the user asks for Chinese prompts, Mandarin cinematic wording, role binding, first/last-frame workflow, or maximum compactness. Chinese prompt wording is often efficient, but it must still preserve mode, reference tags, action, camera, lighting, audio, and constraints.

## Intent

Chinese production wording can use compact compounds, but compression is useful only when the shot instruction remains explicit. Keep each concise phrase tied to a visible action, camera behavior, light source, sound, or preservation constraint. The shipped independent review artifact is empty, so treat these choices as working production wording pending locale-specialist review.

## Usage Rule

Do not translate reference tags. Keep `@Image1`, `@Video1`, and `@Audio1` unchanged. Use short production phrases instead of abstract adjectives.

Load [vocab/zh](../../references/vocab/zh.md) for dense role-binding, first/last-frame, camera, lighting, audio, edit/extend, constraint, and safety vocabulary.

| Function | Chinese wording |
|---|---|
| Camera | `缓慢推镜`, `横向跟拍`, `固定中景`, `低角度`, `特写`, `从剪影到正面四分之三角度` |
| Lighting | `侧逆光`, `柔和窗光`, `暖色实用灯`, `冷色月光`, `轮廓光`, `体积光` |
| Motion | `慢慢转身`, `快速掠过画面`, `水珠沿表面下滑`, `薄雾贴地扩散` |
| Audio | `安静环境声`, `一句短对白`, `轻微金属声`, `无配乐`, `脚步声卡点` |
| First/last frame | `@图片1 为首帧`, `@图片2 为尾帧`, `自然过渡到尾帧`, `中间动作连续，不跳切` |
| Constraints | `严格保持logo、标签、形状和颜色不变` |

## Compact Pattern

`@Image1为参考，严格保持[主体/产品/脸部/标志]不变；仅加入[动作/光线/镜头变化]。镜头：[一个动作]。声音：[音效或环境声]。`

## Script Variant Rule

When the deliverable targets 台灣, 香港, or any Traditional-script audience, load Script Variant (简繁) in [Chinese vocabulary](../../references/vocab/zh.md) before writing subtitle or delivery text. Prompt in Simplified; declare the delivery script separately - and never convert between them by find-and-replace (头发 → 頭髮, not 頭發).

## De-Slop Rule

When the prompt leans on `电影感`, `氛围感`, `高级感`, `大片感`, or bare `质感`, load the Slop Traps table in [Chinese vocabulary](../../references/vocab/zh.md) and decompose each into the physical elements that produce it - 材质, 光线, 色彩, 空气.

## Output Contract

Return concise Chinese prompt text, optional English gloss when useful, and preserve reference tags exactly.

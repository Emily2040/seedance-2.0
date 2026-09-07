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

Preserve actual reference tags exactly; their spelling is independent of the prompt language. Use short production phrases instead of abstract adjectives.

Before adapting a reference example below, load [Using Reference Examples](../../references/surface-prompt-profiles.md#using-reference-examples). Bind its placeholders to real assets by the requested role, then preserve the actual token, including its script, case, spacing and punctuation. A written example token does not attach a file.

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

When choosing or adapting Chinese prompt or delivery text, load Script Variant (简繁) in [Chinese vocabulary](../../references/vocab/zh.md). Preserve the user's chosen prompt script, subtitle script, locale and intended voice as separate decisions. Do not force Simplified prompting or infer a voice from written script. Keep exact dialogue and reference tags unchanged; convert or localize only the text the user asked to adapt. If a missing choice materially affects that deliverable, ask one focused question or use the user's delegated choice. Never convert by find-and-replace (头发 → 頭髮, not 頭發).

## De-Slop Rule

When an adjective leaves the intended shot unclear, load Slop Traps in [Chinese vocabulary](../../references/vocab/zh.md). Preserve a useful style or aesthetic term and add only the scene-specific action, framing, light, or sound needed to clarify it. The table offers authored options, not a default look or a proven model-performance rule. Keep the user's chosen energy, dialogue, reference tags, and settings. Offer distinct choices only when the ambiguity changes the scene; if the user delegated the choice, decide within that scope.

## Output Contract

Return concise Chinese prompt text, optional English gloss when useful, and preserve reference tags exactly.

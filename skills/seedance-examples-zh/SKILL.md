---
name: seedance-examples-zh
description: "This skill should be used when the user asks for Chinese Seedance 2.0 examples, Chinese prompt patterns, example rewrites, or safe versions of working Chinese video-generation prompts."
license: MIT
user-invocable: true
tags:
  - chinese
  - examples
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

# seedance-examples-zh

Use examples as patterns, not as content to copy blindly. Chinese prompts should stay compact, concrete, and production-oriented. Keep reference tags such as `[Image1]`, `[Video1]`, and `[Audio1]` unchanged.

## Intent

Some users learn by rule, but the ones who come here learn by seeing. The purpose of these examples is recognition - a working prompt close enough to their idea that they can feel the gap and close it themselves. An example that teaches is worth ten instructions.

## Example Labels

| Label | Meaning |
|---|---|
| `safe` | Original concept, no protected identity. |
| `needs-owned-reference` | Requires user-owned, licensed, public-domain, or authorized asset. |
| `surface-specific` | Depends on the active web, API, or workflow surface. |
| `rewrite-required` | Mentions protected identity, brand, celebrity, exact scene, song, or voice. |

## Safe Example Patterns

**Product I2V:** `[Image1]为产品参考，严格保持logo、标签、瓶身形状和颜色不变。镜头缓慢推进到标签特写；左侧暖光扫过玻璃，水珠沿瓶身下滑，背景保持暗色静止。声音：轻微环境声，结尾一声清脆玻璃音。`

**Character drama:** `原创角色A站在狭窄走廊，缓慢放下信封，目光停在紧闭的门上。镜头为稳定中近景并轻微推进。暖色顶灯微微闪烁，墙面有冷色雨光反射。声音：远处雨声，无配乐。`

**Action:** `原创快递员在雨夜屋顶奔跑，跃过一道狭窄缝隙，落地后单膝撑住并冲向即将关闭的铁门。低机位手持跟拍，冷色屋顶灯和湿地反光。声音：急促呼吸、雨声、铁门提示音。`

**Safe animation:** `原创二维动画沙漠信使，夸张围巾，驾驶小型风力木车穿过浅色沙丘。手绘背景质感，圆润角色造型，柔和粉彩色调，车轮带出细小沙尘。镜头侧向稳定跟拍。`

**First/last frame:** `@图1为首帧，@图2为尾帧。保持同一原创角色、服装和房间布局，角色从椅子上缓慢站起，走到窗边并停在尾帧姿势。动作连续自然，不跳切，不改变脸部、衣服或房间结构。镜头固定中景，仅轻微推镜。声音：安静室内环境声。`

**Camera-reference R2V:** `@图1锁定原创角色造型和服装，@视频1仅参考运镜节奏和侧向跟拍方式，不复制人物、场景或品牌。角色在雨夜街道从画面左侧跑入，停在路灯下回头。镜头横向稳定跟拍，最后固定中景。冷色雨光，地面反射霓虹。声音：雨声、脚步声，无配乐。`

**Dialogue:** `原创角色A坐在厨房桌前，固定中近景。对白期间头部保持稳定，只做轻微表情变化。角色轻声说：“我找到钥匙了。”柔和窗光来自画面右侧，背景有暖色台灯。声音：清晰短对白、低室内环境声、无配乐。`

## Rewrite Pattern

If the prompt contains protected names, translate the intent into original descriptors: `知名IP角色` becomes `原创蒙面屋顶信使`; `某导演风格` becomes `低饱和胶片质感、硬侧光、长焦压缩空间、静默表演`.

## Output Contract

Return the Chinese example, label, risk note, and a safer Chinese variant if needed.

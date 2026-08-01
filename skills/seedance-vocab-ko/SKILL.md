---
name: seedance-vocab-ko
description: "This skill should be used when the user asks for Korean Seedance 2.0 prompt wording, Korean cinematic vocabulary, or translation of camera, lighting, action, VFX, audio, and production terms into Korean."
license: MIT
user-invocable: true
tags:
  - korean
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

# seedance-vocab-ko

Before producing prompt text, a prompt-ready block, a rewrite, an example, or a compiled clip, load the [Director's Read](../../references/directors-read.md), classify the brief, and complete its canonical narrative or non-narrative record. Translate that record into visible or audible carriers and keep its internal labels out of final generation prose.

Use Korean cinematic vocabulary when the user asks for Korean prompt wording, bilingual delivery, compact translation, or production vocabulary for camera, lighting, action, VFX, audio, and constraints. Preserve reference tags exactly: `@Image1`, `@Video1`, and `@Audio1` must not be translated.

## Intent

Korean prompt direction should convert mood words into observable light, framing, blocking, and timing instead of treating a label as sufficient direction. Keep the relationship and speech level explicit whenever dialogue is added. The shipped independent review artifact is empty, so treat these choices as working production wording pending locale-specialist review.

## Usage Rule

Translate the production intention rather than every English word. Keep the Korean prompt compact and concrete: subject, action, camera, light, sound, and preservation constraint.

| Function | Korean wording |
|---|---|
| Camera | `느린 돌리 인`, `측면 트래킹 샷`, `고정된 미디엄 샷`, `로우 앵글`, `클로즈업` |
| Lighting | `역광`, `부드러운 창문 빛`, `따뜻한 프랙티컬 조명`, `차가운 달빛`, `림 라이트` |
| Motion | `천천히 돌아선다`, `프레임을 빠르게 가로지른다`, `물방울이 아래로 흐른다`, `연기가 얇게 퍼진다` |
| Audio | `조용한 환경음`, `짧은 대사`, `부드러운 금속음`, `음악 없음` |
| Constraints | `로고, 라벨, 형태를 정확히 유지한다` |

## Compact Pattern

`@Image1은 참조 이미지이며 얼굴/제품 형태/로고를 정확히 유지한다. 변화는 [동작/조명/카메라]만 적용한다. 카메라: [한 가지 움직임]. 사운드: [음향 지시].`

## Speech Level Rule

The moment a prompt contains dialogue, load Speech Level (말투) in [Korean vocabulary](../../references/vocab/ko.md) and declare one level per speaker - 합니다체, 해요체, or 반말. Korean has no neutral register, and the syllable cost differs enough to break the sync budget (고마워 3 → 감사합니다 5).

## De-Slop Rule

When the prompt leans on `영화 같은`, `감성적인`, `분위기 있는`, `웅장한`, or `고퀄리티`, load the Slop Traps table in [Korean vocabulary](../../references/vocab/ko.md) and decompose each into the physical elements that produce it - 카메라 동사+속도+시점, 광원+방향+행동.

## Output Contract

Return Korean prompt wording, optional English gloss when useful, and unchanged reference tags.

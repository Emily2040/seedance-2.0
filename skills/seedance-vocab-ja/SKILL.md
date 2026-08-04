---
name: seedance-vocab-ja
description: "This skill should be used when the user asks for Japanese Seedance 2.0 prompt wording, Japanese cinematic vocabulary, or translation of camera, lighting, action, VFX, audio, and production terms into Japanese."
license: MIT
user-invocable: true
tags:
  - japanese
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

# seedance-vocab-ja

Before producing prompt text, a prompt-ready block, a rewrite, an example, or a compiled clip, load the [Director's Read](../../references/directors-read.md), classify the brief, and complete its canonical narrative or non-narrative record. Translate that record into visible or audible carriers and keep its internal labels out of final generation prose.

Use Japanese cinematic vocabulary when the user asks for Japanese prompt wording, bilingual delivery, compact translation, or production vocabulary for camera, lighting, motion, VFX, and audio. Preserve reference tags exactly: `@Image1`, `@Video1`, and `@Audio1` remain in English brackets.

## Intent

Japanese prompt direction can combine concise clauses with established production loanwords. Choose one readable clause order, keep each term attached to a concrete shot instruction, and avoid literal English syntax where a shorter production construction is available. The shipped independent review artifact is empty, so treat these choices as working production wording pending locale-specialist review.

## Usage Rule

Prefer concise production Japanese over literal translation. Keep the structure readable: subject, action, camera, lighting, sound, and preservation constraint.

| Function | Japanese wording |
|---|---|
| Camera | `ゆっくりドリーイン`, `横移動のトラッキング`, `固定の中景`, `低いアングル`, `クローズアップ` |
| Lighting | `逆光`, `柔らかい窓光`, `暖かいプラクティカルライト`, `冷たい月明かり`, `輪郭光` |
| Motion | `ゆっくり振り返る`, `画面を素早く横切る`, `水滴が下へ流れる`, `煙が薄く広がる` |
| Audio | `静かな環境音`, `短い台詞`, `金属音`, `音楽なし` |
| Constraints | `ロゴ、ラベル、形状を正確に維持する` |

## Compact Pattern

`@Image1を参照として、被写体の顔/商品形状/ロゴを正確に維持する。変化は[動き/光/カメラ]のみ。カメラ：[一つの動き]。音：[音声指示]。`

## Register Rule

The moment a prompt contains dialogue, load Register (文体) in [Japanese vocabulary](../../references/vocab/ja.md) and declare one register per speaker - 敬語, です・ます体, or 普通体 - with a first-person pronoun that matches it. An unstated register is a decision handed to the model, and the mora cost differs enough to break the sync budget (ありがとう 5 → ありがとうございます 10).

## De-Slop Rule

When the prompt leans on `映画のような`, `エモい`, `雰囲気のある`, `壮大な`, or `高画質`, load the Slop Traps table in [Japanese vocabulary](../../references/vocab/ja.md) and decompose each into the physical elements that produce it - 動作動詞＋速度＋視点, 光源＋方向＋挙動.

## Output Contract

Return Japanese prompt wording, optional English gloss when useful, and unchanged reference tags.

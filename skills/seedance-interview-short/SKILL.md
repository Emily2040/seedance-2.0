---
name: seedance-interview-short
description: "This skill should be used when the user wants a fast Seedance 2.0 creative brief, a short interview, a compressed intake flow, or a quick director-style clarification before prompt writing."
license: MIT
user-invocable: true
tags:
  - creative-direction
  - brief
  - compression
  - seedance-20
metadata:
  version: "5.4.7"
  updated: "2026-06-11"
  parent: "seedance-20"
  author: "Iamemily2050 (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: "🎬"
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-interview-short

Use this when speed matters more than exhaustive creative discovery. The goal is to turn a vague idea into a compact director brief with no more than three questions, then route to prompt writing.

## Process

Ask at most three questions, and only ask them if the answer materially changes the prompt. Assume no film background: ask in everyday words, give pickable options, and attach a default so "I don't know" never stalls the brief. Prioritize:

1. What happens in the video, and what is different at the end? `(not sure? I'll pick one simple action with a visible ending)`
2. What should it feel like - pick one: polished ad, movie drama, funny, real-life phone clip, cartoon, or moody atmosphere? `(not sure? I'll go calm and warm)`
3. Do you have photos, clips, or sound of the real thing - and should each one keep the look, the motion, or the sound? `(none is fine)`

If the user already supplied enough information, do not ask. Produce a brief immediately. If the user speaks production language fluently, drop the plain phrasing and ask in director terms.

## Compact Brief Pattern

`Mode: [T2V/I2V/V2V/R2V]. Subject: [anchor]. Beat: [before -> action -> final state]. Camera: [one move]. Light/style: [physical source and safe descriptor]. Sound: [dialogue/ambience/SFX/music/silence]. Constraints: [identity, IP, safety, product, prompt budget].`

## Routing Rule

Route to `[skill:seedance-prompt]` for a full production prompt, `[skill:seedance-prompt-short]` for a compact prompt, `[skill:seedance-copyright]` for IP/likeness risk, or `[skill:seedance-troubleshoot]` when the user starts from a bad result.

## Output Contract

Return one compact brief under 150 words, any missing high-impact question, and a recommended skill route.

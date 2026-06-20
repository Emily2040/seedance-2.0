---
name: seedance-filter
description: "This skill should be used when a Seedance 2.0 prompt is blocked, rejected, silently degraded, or likely to trigger a content filter; or when the user asks for a safer rewrite without losing the creative intent."
license: MIT
user-invocable: true
tags:
  - content-filter
  - safe-rewrite
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

# seedance-filter

## Intent

A wrongly blocked prompt makes a user feel accused by a machine with no court of appeal. This skill is the advocate: clear the innocent by stating their honest intent plainly, and never coach the guilty. The user's dignity and the platform's boundary are protected in the same gesture.

## Boundary — read before anything else

This skill repairs **false positives only**: benign production content blocked or degraded by over-broad filtering (medical, historical, athletic, fictional-original contexts). It works by **clarifying legitimate context in plain language** — never by disguising intent. It does not rephrase genuinely prohibited content: anything risky involving minors, real-person likeness without rights, sexual or graphic or illegal material. If the underlying request is prohibited, refuse plainly and offer a legitimate alternative only where one exists.

Use this when a prompt is blocked, degraded, likely to trigger moderation, or needs a safer rewrite without losing creative intent. This skill does not help evade safety systems. It rewrites risky surface wording into professional, non-graphic production language and preserves the safe creative core.

## Repair Method

1. Identify the creative intent: action, mood, camera, subject, and final beat.
2. Identify risky surface wording: graphic harm, protected identity, sexualized framing, real-person likeness, weapons, self-harm, hate, evasion language, or exact IP copying.
3. Replace risky terms with professional, non-graphic, production-context language.
4. Preserve composition, action, mood, camera logic, and authorized references.
5. For likely false positives, clarify benign production context, ownership, and non-graphic intent. Do not help bypass safety systems or provide evasion tactics.

## Safer Rewrite Patterns

| Intent | Safer direction |
|---|---|
| Conflict | `staged confrontation, choreographed action beat, no graphic injury` |
| Aftermath | `non-graphic distress, torn fabric, scattered props, dramatic silence` |
| Suspense | `threat implied by shadow, locked door, heavy breathing, low light` |
| Weapon-like prop | `prop object handled safely within a staged action scene` |
| Horror mood | `eerie atmosphere, flickering practical light, off-screen sound cue` |
| Protected identity | `original character with broad genre archetype traits` |

## Boundary Rule

If the user's request is unsafe, refuse or redirect to a safe alternative. If it is safe but poorly worded, repair the wording. When uncertain, state the risk class and offer a conservative prompt that keeps the non-harmful scene function.

Do not provide filter-bypass, evasion, or hidden-word tactics. The safe path is to clarify production intent, remove unsafe identity or harm elements, and rewrite into an original authorized scene.

Face-limit or portrait-verification workarounds are not safe prompt tricks. If a surface offers sanctioned virtual portrait, trusted model-output, or authorization asset flows, route the user to those current official paths instead of evasion language.

Load `[ref:filter-vocab]` for safer substitutions. Load `[ref:multilingual-community-examples]` only when the safe repair needs Chinese/Russian/Japanese/Korean/Spanish or mixed-language wording for clarity.

## Output Contract

Return likely trigger class, safer wording, final prompt, what changed, and any content boundary that still applies.

---
name: seedance-vocab-es
description: "This skill should be used when the user asks for Spanish Seedance 2.0 prompt wording, Spanish cinematic vocabulary, or translation of camera, lighting, action, VFX, audio, and production terms into Spanish."
license: MIT
user-invocable: true
tags:
  - spanish
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

# seedance-vocab-es

Before producing prompt text, a prompt-ready block, a rewrite, an example, or a compiled clip, load the [Director's Read](../../references/directors-read.md), classify the brief, and complete its canonical narrative or non-narrative record. Translate that record into visible or audible carriers and keep its internal labels out of final generation prose.

Use Spanish cinematic vocabulary when the user asks for Spanish prompts, bilingual delivery, or compact translation of camera, lighting, action, VFX, audio, and production constraints. Preserve actual reference tags exactly; their spelling is independent of the prompt language.

Before adapting a reference example below, load [Using Reference Examples](../../references/surface-prompt-profiles.md#using-reference-examples). Bind its placeholders to real assets by the requested role, then preserve the actual token, including its script, case, spacing and punctuation. A written example token does not attach a file.

## Intent

Spanish prompt direction should preserve production meaning and clause clarity before stylistic cadence. Keep the subject, visible action, camera endpoint, light, sound, and constraint unambiguous. The shipped independent review artifact is empty, so treat these choices as working production wording pending locale-specialist review.

## Usage Rule

Translate production meaning, not word-for-word English. Keep the prompt concrete and concise: subject, visible action, camera, light, sound, and constraint.

| Function | Spanish wording |
|---|---|
| Camera | `travelling de acercamiento`, `plano medio`, `primer plano`, `seguimiento lateral`, `cámara fija` |
| Lighting | `contraluz`, `luz suave de ventana`, `luz práctica cálida`, `sombra marcada`, `luz de contorno fría de luna` |
| Motion | `gira lentamente`, `cruza rápido el encuadre`, `avanza con estabilidad`, `las gotas se deslizan` |
| Audio | `sonido ambiente`, `diálogo claro`, `golpe metálico suave`, `sin música` |
| Constraints | `mantener el logotipo, la etiqueta y la forma sin cambios` |

## Compact Pattern

`@Image1 es la referencia; mantener identidad, color y forma sin cambios. Solo cambia [movimiento/luz/cámara]. Cámara: [un movimiento]. Sonido: [señal].`

## De-Slop Rule

When the prompt leans on `cinematográfico`, `épico`, `impresionante`, `mágico`, or `de alta calidad`, load the Slop Traps table in [Spanish vocabulary](../../references/vocab/es.md) and decompose each into the physical elements that produce it - movimiento de cámara, fuente de luz, material, sonido.

## Output Contract

Return Spanish prompt wording and unchanged reference tags; add an English gloss only when requested or needed to resolve a specific ambiguity.

For a first prompt or retake:

- Use the user's supplied decisions immediately. Do not restart an interview or impose a language lesson on a complete brief.
- When directions are requested, distinguish their visible performance, staging or information tradeoffs. Keep the chosen and rejected options across revisions; do not force a menu on a specified scene.
- Put the copyable prompt apart from settings, reference requirements and review notes. A written token does not attach an asset; never invent a binding.
- Preserve exact quoted dialogue even when it is in another language, unless translation is requested. Ask about region or relationship only when it changes the requested wording.
- For a reported failure, name the criterion, propose one concrete change and retain duration, tier and remaining budget. Attribute an unseen result to the user's description. A text revision does not authorize submission; at zero budget offer an acceptable edit or stop.
- Treat authored examples as unrendered and independent language review as pending. Do not promise fluency, voice reliability or credit savings from a static check.

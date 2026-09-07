---
name: seedance-vocab-ru
description: "This skill should be used when the user asks for Russian Seedance 2.0 prompt wording, Russian cinematic vocabulary, or translation of camera, lighting, action, VFX, audio, and production terms into Russian."
license: MIT
user-invocable: true
tags:
  - russian
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

# seedance-vocab-ru

Before producing prompt text, a prompt-ready block, a rewrite, an example, or a compiled clip, load the [Director's Read](../../references/directors-read.md), classify the brief, and complete its canonical narrative or non-narrative record. Translate that record into visible or audible carriers and keep its internal labels out of final generation prose.

Use Russian cinematic vocabulary when the user asks for Russian prompt wording, bilingual delivery, compact translation, role binding, first/last-frame workflow, or production vocabulary for camera, lighting, action, VFX, audio, and constraints. Preserve actual reference tags exactly; their spelling is independent of the prompt language.

Before adapting a reference example below, load [Using Reference Examples](../../references/surface-prompt-profiles.md#using-reference-examples). Bind its placeholders to real assets by the requested role, then preserve the actual token, including its script, case, spacing and punctuation. A written example token does not attach a file.

## Intent

Russian prompt direction should separate verified platform limits from field-observed workarounds and label each accordingly. Keep dialogue, lip-sync, and pronunciation guidance testable rather than promising a result the evidence does not support. The shipped independent review artifact is empty, so treat these choices as working production wording pending locale-specialist review.

## Usage Rule

Translate production intent, not every English word. Russian prompts should stay compact, concrete, and ordered by subject, action, camera, light, sound, and constraint.

Load [vocab/ru](../../references/vocab/ru.md) for dense role-binding, first/last-frame, camera, lighting, audio, edit/extend, constraint, and safety vocabulary.

| Function | Russian wording |
|---|---|
| Camera | `медленный наезд камеры`, `боковое сопровождение`, `фиксированный средний план`, `нижний ракурс`, `крупный план` |
| Lighting | `контровой свет`, `мягкий свет из окна`, `теплый практический источник`, `холодный лунный свет`, `контурная подсветка` |
| Motion | `медленно поворачивается`, `быстро проходит через кадр`, `капли стекают вниз`, `дым мягко рассеивается` |
| Audio | `тихий фон помещения`, `короткая реплика`, `мягкий металлический щелчок`, `без музыки` |
| First/last frame | `@Image1 как первый кадр`, `@Image2 как последний кадр`, `естественный переход к последнему кадру` |
| Constraints | `сохранить логотип, этикетку и форму без изменений` |

## Compact Pattern

`@Image1 — референс; сохранить лицо/форму продукта/логотип без изменений. Меняются только [движение/свет/камера]. Камера: [одно движение]. Звук: [аудиосигнал].`

## De-Slop Rule

When the prompt leans on `кинематографичный`, `эпичный`, `атмосферный`, `потрясающий`, or `высокое качество`, load the Slop Traps table in [Russian vocabulary](../../references/vocab/ru.md) and decompose each into the physical elements that produce it - движение камеры, источник света, материал, звук.

## Dialogue Rule

For spoken Russian, load the Russian Dialogue Notes in [Russian vocabulary](../../references/vocab/ru.md). Preserve exact supplied dialogue and Cyrillic spelling; do not transliterate, shorten, or change register without agreement. Time the actual performance. Offer supported voice-reference or post-dub options as user choices, not automatic replacements or guarantees.

## Output Contract

Return Russian prompt wording and unchanged reference tags; add an English gloss only when requested or needed to resolve a specific ambiguity.

For a first prompt or retake:

- Use the user's supplied decisions immediately. Do not restart an interview or impose a language lesson on a complete brief.
- When directions are requested, distinguish their visible performance, staging or information tradeoffs. Keep the chosen and rejected options across revisions; do not force a menu on a specified scene.
- Put the copyable prompt apart from settings, reference requirements and review notes. A written token does not attach an asset; never invent a binding.
- Preserve exact quoted dialogue even when it is in another language, unless translation is requested. Ask about region or relationship only when it changes the requested wording.
- For a reported failure, name the criterion, propose one concrete change and retain duration, tier and remaining budget. Attribute an unseen result to the user's description. A text revision does not authorize submission; at zero budget offer an acceptable edit or stop.
- Treat authored examples as unrendered and independent language review as pending. Do not promise fluency, voice reliability or credit savings from a static check.

---
name: seedance-prompt
description: 'Construct a high-density, technically precise, and creatively potent prompt for Seedance 2.0. Use when a user has a clear vision and needs to translate it into a production-ready prompt. Follow the "Concealment Check" workflow: Deconstruct → Expose → Re-build.'
license: MIT
user-invocable: true
tags: ["prompt-engineering", "cinematography", "technical-writing", "pre-production", "visual-design", "seedance-20"]
metadata: {"version": "4.0.0", "updated": "2026-02-28", "openclaw": {"emoji": "✍️", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "antigravity": {"emoji": "✍️", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "✍️", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-prompt · The Concealment Check (v4.0)

This skill translates a user's creative vision into a high-density, production-ready prompt for Seedance 2.0. It uses a cognitive workflow to eliminate ambiguity and maximize visual specificity.

## The Workflow (Cognitive Opcodes)

### 1. Initial Prompt (User Input)
- Get a draft prompt from the user or from the `seedance-interview` skill.
- **Example:** `"A beautiful woman in a stunning dress walks through an epic cinematic landscape."`

### 2. Concealment Check (L7 Opcode)
- Analyze the draft prompt for "slop" words that conceal a lack of specific visual information. These are words that *sound* descriptive but are not measurable by a camera.
- **AI Analysis:**
  - `beautiful`: Conceals the specific facial features, expression, and age.
  - `stunning`: Conceals the specific fabric, cut, color, and texture of the dress.
  - `epic`: Conceals the specific geography, weather, and scale of the landscape.
  - `cinematic`: Conceals the specific lighting, lens, and camera movement.

### 3. Deconstruct & Expose (L7 Opcode)
- Present the concealment analysis to the user and force them to replace the slop words with measurable, observable details.
- **AI Output:**
  - **Deconstruct `beautiful`**: "What is the specific facial structure? Is her expression serene or defiant? What is her age?"
  - **Deconstruct `stunning`**: "What is the fabric of the dress? Is it silk or rough-spun wool? What is the exact color? How does it move in the wind?"
  - **Deconstruct `epic`**: "Is this a landscape of Icelandic volcanic rock or Scottish highlands? Is the sky clear or stormy?"
  - **Deconstruct `cinematic`**: "Is the lighting a single hard key from the side, or soft, diffused overhead light? Is the lens a wide 24mm or a compressed 100mm?"

### 4. Re-build with Specificity (L8 Opcode)
- Construct the final, high-density prompt using the user's specific, measurable answers. Discard all the original slop words.
- **Final Prompt Output:** `"A woman with sharp cheekbones and a defiant expression, aged 30, walks through a landscape of black volcanic rock under a stormy sky. She wears a dress of rough-spun, crimson wool that whips in the wind. The camera is a wide 24mm, positioned low to the ground. The lighting is a single, hard key from the side, casting long shadows. 1500 chars."`

---

## Why This Works (Cognitive Science)

- **Eliminates Ambiguity:** By forcing the user to replace vague adjectives with measurable nouns and verbs, the AI eliminates the ambiguity that leads to generic or failed generations.
- **Builds a Visual Vocabulary:** This process teaches the user to think like a cinematographer, building a vocabulary of specific, observable details.
- **Improves Performance:** High-density, specific prompts have a much higher success rate with Seedance V2 and are less likely to be rejected for "slop."

---

*Maintained by [Emily (@iamemily2050)](https://github.com/Emily2040)*

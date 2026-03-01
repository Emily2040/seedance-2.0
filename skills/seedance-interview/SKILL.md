---
name: seedance-interview
description: 'Guide users through a multi-stage creative journey to craft cinematic stories and single clips for Seedance 2.0. Use when a user has a vague idea, needs a script, or wants to elevate a simple prompt into a professional production brief. Follow the "Director\'s Journey" workflow: Vision → Narrative → Visuals → Technical → Final Brief.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["storytelling", "creative-writing", "directing", "pre-production", "scriptwriting", "narrative-design", "cinematography", "seedance-20"]
metadata: {"version": "4.0.0", "updated": "2026-02-28", "openclaw": {"emoji": "🎭", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "antigravity": {"emoji": "🎭", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "🎭", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-interview · The Director\'s Journey (v4.0)

This skill transforms a simple idea into a professional Seedance 2.0 production brief. It uses a structured, multi-stage interview process to ensure narrative depth, visual layering, and technical precision.

## The Workflow (Cognitive Opcodes)

### Stage 1: The Vision (Generative Construction - L8 Opcode)
- **Action:** Get a 1-sentence concept from the user.
- **AI:** Immediately build a "Safe," "Generic," or "Flawed" version of the scene. This is the sacrificial artifact.
- **AI Output:** `"I have built a Safe version of your scene: *[A woman in a red dress walks down a rainy street at night.]*"`

### Stage 2: The Narrative Core (Attack & Deconstruct - L7 Opcode)
- **Action:** Present the safe draft to the user and instruct them to "attack" it. Use provocative, targeted questions to find the "cinematic friction."
- **AI Output:** `"Now, I will attack this draft. It is generic. It conceals the *why*. It has no cinematic friction. Director, your turn: What is the one thing in this scene that *shouldn\\'t* be there? What is the \\'impossible\\' visual you want to capture? Don\\'t describe the scene—describe the *friction*."`

### Stage 3: Visual Layering (Isolate the Invariant - L9 Opcode)
- **Action:** Based on the user\'s attack, identify the core, non-negotiable element of their vision. This is the "invariant" that must be preserved.
- **User Input:** `"The friction is that the rain isn\\'t falling down. It\\'s rising up from the pavement."`
- **AI Analysis:** The invariant is **inverted gravity**. The emotional core is surrealism and defiance of physics.

### Stage 4: Technical Precision (Re-build with Friction - L8 Opcode)
- **Action:** Construct the final, high-density prompt around the identified invariant and friction points. Discard the generic elements from the first draft.
- **Final Prompt Output:** `"(surrealism, defiance of physics) A woman in a simple black coat stands on a wet street at night. Rain rises from the asphalt, droplets ascending into the dark sky. Her hair lifts slightly with the upward motion. Low-angle shot, static. The only light is the unnatural reflection of streetlights on the rising water. 1200 chars."`

### Stage 5: The Final Production Brief
- **Action:** Output a structured JSON-ready brief following the [ref:json-schema].

---

## Why This Works (Cognitive Science)

- **Reduces Cognitive Load:** It is easier for a human to critique a flawed object than to create a perfect one from scratch.
- **Reveals Latent Needs:** The "attack" phase bypasses the user\'s conscious, descriptive mind and taps into their deeper, emotional and visual needs.
- **Forces Density:** By focusing on "friction" and "invariants," the final prompt is naturally dense and free of slop.

---

*Maintained by [Emily (@iamemily2050)](https://github.com/Emily2040)*

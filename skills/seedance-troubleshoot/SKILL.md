---
name: seedance-troubleshoot
description: "Diagnose and fix failing or low-quality Seedance 2.0 prompts using a cognitive, first-principles approach. Use when a prompt is consistently failing, producing generic output, or being rejected. Follow the \"Conservation Law\" workflow: Isolate → Invert → Re-build."
license: MIT
user-invocable: true
tags: ["debugging", "troubleshooting", "prompt-engineering", "quality-control", "root-cause-analysis", "seedance-20"]
metadata: {"version": "4.0.0", "updated": "2026-02-28", "openclaw": {"emoji": "🔧", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "antigravity": {"emoji": "🔧", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "🔧", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-troubleshoot · The Conservation Law (v4.0)

This skill diagnoses and fixes failing Seedance 2.0 prompts. Instead of a checklist of common fixes, it identifies the fundamental, unbreakable trade-off in a failing prompt and then "inverts" the design to find a creative escape route.

## The Workflow (Cognitive Opcodes)

### 1. Failing Prompt (User Input)
- Get a prompt that is consistently failing, producing low-quality output, or being rejected.
- **Example:** `"A hyper-detailed character with intricate facial tattoos performs a fast, 360-degree spinning aerial kick in a dark, moody alley."`

### 2. Identify the Conservation Law (L11-C Opcode)
- Analyze the prompt to find the two competing demands that are creating a "conservation law" — a trade-off where you can have one or the other, but not both at maximum quality.
- **AI Analysis:**
  - **Demand 1 (Sensitivity):** "hyper-detailed character with intricate facial tattoos" requires high model attention to fine, static detail.
  - **Demand 2 (Absorption):** "fast, 360-degree spinning aerial kick" requires high model attention to complex, high-velocity motion.
  - **The Conservation Law:** `Sensitivity (Detail) x Absorption (Movement) = Constant`. To maximize one, you must strategically sacrifice the other. The prompt is failing because it demands maximum detail *and* maximum movement, which exceeds the model's capacity.

### 3. Expose the Trade-off & Invert the Design (L11-C Opcode)
- Present the conservation law to the user and propose an "inversion" of the design that preserves the creative intent while respecting the trade-off.
- **AI Output:**
  - **Expose:** "This prompt is failing because of a Conservation Law: you can have the intricate detail or the fast motion, but not both at once. We must choose which is more important to the story."
  - **Invert:** "Instead of a fast, 360-degree kick that loses the tattoo detail, let's try a **slow-motion, 180-degree arc** where the camera **tracks the face**, keeping the tattoos in sharp focus. We can use lighting and motion blur on the background to *imply* speed, preserving the feeling of action without sacrificing the detail."

### 4. Re-build with Inversion (L8 Opcode)
- Construct the final, high-density prompt based on the inverted design.
- **Final Prompt Output:** `"slow-motion, 180-degree arc kick. The camera tracks the face of a character with intricate facial tattoos, keeping them in sharp focus. The background is a dark alley with motion blur to imply speed. Use a single, hard rim light to highlight the tattoos. 1800 chars."`

---

## Why This Works (Cognitive Science)

- **Makes Invisible Constraints Visible:** The AI exposes the hidden, fundamental trade-offs in the model's architecture that the user cannot see.
- **Provides Creative Escape Routes:** Instead of just saying "this is not possible," the AI "inverts" the design to find a creative solution that achieves the same emotional impact through a different technical path.
- **Builds a Deeper Mental Model:** This process teaches the user to think in terms of trade-offs and conservation laws, leading to more effective and sophisticated prompt design in the future.

---

*Maintained by [Emily (@iamemily2050)](https://github.com/Emily2040)*

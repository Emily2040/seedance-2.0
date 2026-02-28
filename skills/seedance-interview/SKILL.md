---
name: seedance-interview
description: 'Guide users through a multi-stage creative journey to craft cinematic stories and single clips for Seedance 2.0. Use when a user has a vague idea, needs a script, or wants to elevate a simple prompt into a professional production brief. Follow the "Director''s Journey" workflow: Vision → Narrative → Visuals → Technical → Final Brief.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["storytelling", "creative-writing", "directing", "pre-production", "scriptwriting", "narrative-design", "cinematography", "seedance-20"]
metadata: {"version": "3.8.0", "updated": "2026-02-27", "openclaw": {"emoji": "🎭", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "antigravity": {"emoji": "🎭", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "🎭", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-interview · The Director's Journey

This skill transforms a simple idea into a professional Seedance 2.0 production brief. It uses a structured, multi-stage interview process to ensure narrative depth, visual layering, and technical precision.

## The Workflow

### Stage 1: The Vision (The "What")
Identify the core intent. Is it a **Single Cinematic Clip** or a **Narrative Story**?
- **Single Clip**: Focus on a specific moment, texture, or visual effect (e.g., a luxury product shot, a nature time-lapse).
- **Narrative Story**: Focus on characters, conflict, and emotional arc (e.g., a mecha launch, a quiet confession).

### Stage 2: The Narrative Core (The "Why")
Establish the emotional anchor and hook.
- **The Hook**: What is the first thing that grabs the viewer?
- **The Conflict/Tension**: What is the central struggle or mystery?
- **The Resolution**: How does the scene or story conclude?

### Stage 3: Visual Layering (The "How")
Build the scene in layers using the [ref:storytelling-framework].
- **Subject Layer**: Primary and secondary subjects with specific attributes.
- **Action Layer**: Primary motion + secondary micro-movements (breathing, touch, debris).
- **Environmental Layer**: Atmosphere, weather, and props that react to the action.

### Stage 4: Technical Precision
Define the "eye" of the camera and the "ear" of the scene.
- **Camera Language**: Specific lenses (e.g., 100mm macro), shots (e.g., crane rise), and movements.
- **Audio Design**: Music mood, specific SFX (e.g., crisp cap-twist), and dialogue.
- **Physics & Constraints**: How should elements behave? (e.g., "liquid must obey fluid dynamics").

### Stage 5: The Final Production Brief
Output a structured JSON-ready brief following the [ref:json-schema].

## Creative Prompts for the Interviewer

When interviewing the user, use these "Director's Questions" to pull out creative details:
- "What is the **emotional temperature** of this scene? Is it cold and sterile, or warm and intimate?"
- "If we were to zoom in on a **micro-detail**, what would we see? A single drop of amber liquid? A trembling hand?"
- "How does the **environment react** to the main action? Does the wind move the hair? Does the shockwave disperse the clouds?"
- "What is the **sound of the silence** in this scene? Is it a low ambient hum or a distant temple bell?"

## Example Output Structure

The final brief should include:
- **Caption (Short & Long)**: Descriptive and evocative.
- **Director Notation**: Time-stamped breakdown of the action.
- **Subject/Action/Scene/Camera/Style/Audio**: Layered technical details.
- **Constraints & Physics**: Rules for the AI to follow.
- **Quality Tags**: Standardized Seedance 2.0 tags.

---
*Maintained by [Emily (@iamemily2050)](https://github.com/Emily2040)*

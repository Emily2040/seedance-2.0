---
name: seedance-interview-short
description: "This skill should be used when the user wants a compressed Seedance 2.0 interview, quick creative intake, brief-first workflow, or fast transformation of a loose idea into a 30-100 word production brief."
license: MIT
user-invocable: true
user-invokable: true
tags:
  - seedance-20
  - video-generation
  - interview
  - short
metadata:
  version: "5.1.0"
  updated: "2026-04-27"
  parent: "seedance-20"
  author: "Emily (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: ""
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-interview-short (v5.0)

This skill transforms a simple idea into a professional, **sub-2000-character** Seedance 2.0 production brief, with a target of **30-100 words**.

## The Workflow

1.  **The Vision & Genre**: Ask for a 1-sentence concept and a genre from [ref:genre-guides].
2.  **Reference Media**: Ask if the user has any `@Image`, `@Video`, or `@Audio` references.
3.  **"Quick Mode" Exit**: If the user has strong references, offer to switch to the [skill:seedance-prompt] skill to build a prompt directly.
4.  **Narrative Core**: If needed, ask 1-2 questions to find the emotional anchor.
5.  **Build & Compress**: Construct the prompt using the Director's Formula, keeping a live character count.
6.  **Safety Gate (Required)**: If there is celebrity/real-person likeness, brand, franchise, logo, or copyrighted character/style risk, route to [skill:seedance-copyright] before final output. If wording is likely to be filtered, route to [skill:seedance-filter].

## The Interviewer's Craft

-   Prioritize action verbs and physics over descriptive adjectives.
-   Explain that shorter, denser prompts perform better.
-   Use the character budget as a creative constraint, not just a technical one.

### Final Output Format

```
**Final Prompt (185/2000 chars):**

[PROMPT TEXT]

---

**Director's Notes:**
- **Genre:** [User's chosen genre]
- **Core Intent:** [Summary of emotional goal]
- **References:** [@Image1, @Video1]
```

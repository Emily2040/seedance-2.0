# Progressive Disclosure Plan

The root skill should route. Sub-skills should decide. References should carry dense tables and volatile facts.

| Content | Location | Load condition |
|---|---|---|
| Routing, high-level rules | `SKILL.md` | Always |
| Prompt construction | `skills/seedance-prompt/SKILL.md` | Prompt-writing tasks |
| Platform/API facts | `references/api-status.md` | Platform or API tasks |
| Vocabulary lists | Language skills + references | Translation/compression tasks |
| Safety and IP | `seedance-copyright` + `platform-constraints` | Protected identity or safety-sensitive tasks |
| Long examples | `seedance-examples-zh` or future `examples/` | User asks for examples |

Do not move large databases back into active sub-skill bodies.

## V6 Sequence Disclosure

Root `SKILL.md` owns only the Sequence Gate and invariants. `skills/seedance-sequence` owns global planning and current-clip compilation. `skills/seedance-continuation` owns accepted-footage continuation and re-anchoring. Dense state details live in `references/sequence-project-state.md`, `references/continuation-handoff.md`, and `references/prompt-compiler.md`.

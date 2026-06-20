# Prompt Compiler

The compiler turns internal project state into one natural-language Seedance prompt for the current clip only. JSON or YAML can organize planning, but the final prompt sent to Seedance stays readable prose unless the user explicitly asks for structured output.

## Inputs

- project state;
- current clip contract;
- surface prompt profile;
- reference transfer contract;
- observed source state for continuations;
- completed and reserved beats;
- continuity locks and allowed changes;
- prompt budget.

## Compile Order

1. Lineage: name `project_id`, `clip_id`, and parent only in the user-facing contract or capsule, not necessarily in the final prompt if it wastes prompt budget.
2. Source role: identify the active reference tags and what each controls.
3. Actual opening state: use observed footage for continuations and planned state only for first clips.
4. Current clip action: one narrative job with an endpoint.
5. Camera and motion phase: include inherited vectors when continuity matters.
6. Light, environment, style, and audio: include only state-critical or mood-critical clauses.
7. Exclusions: completed beats and reserved future beats.
8. Endpoint: the completed state this clip must reach.

## Natural-Language Prompt Rules

Do not emit internal JSON to Seedance. Do not include all future clips. Do not describe a planned ending as if it happened. Do not replay completed actions. Do not perform reserved later actions. Do not invent deterministic guarantees.

Use clip-scope language:

- "Begin with..." for observed opening state.
- "Continue the same..." only when source footage exists.
- "This clip only..." for the current narrative job.
- "Stop when..." for endpoint control.
- "Do not yet..." for reserved future beats.

## Compression

When the prompt must shrink, preserve in this order:

1. Exact reference tags and role boundaries.
2. Actual opening state.
3. Current action and endpoint.
4. Continuity locks.
5. Completed beat exclusions.
6. Reserved beat exclusions.
7. Camera or open motion vector.
8. Audio phase.

Delete generic style boosters, duplicate adjectives, future story summary, background visible in references, secondary actions, and speculative internal notes first.

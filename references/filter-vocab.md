# Prompt Clarification and Content Alternatives

Use this reference after assessing the underlying request through [seedance-filter](../skills/seedance-filter/SKILL.md). A rejection alone does not prove a false positive or identify the rejected word. Use available operation/error information and the actual scene context; leave an unknown cause unknown. These examples are editorial guidance, not tested filter triggers or guarantees of acceptance.

## Faithful Clarification

Clarify only a meaning supported by the brief. Do not add facts such as permission, consent, an adult age or prop status merely to make a request sound acceptable. Preserve exact dialogue unless the user requests its revision.

| Known benign meaning | Clarification | What stays unchanged |
|---|---|---|
| Recording a scene | `film the scene` | The filming task and its subject |
| Switching off room lights | `switch off the room lights` | The requested lighting action |
| Increasing image display size | `enlarge the image` | The depicted content; output resolution is a separate requirement |
| Describing a red lamp | `deep red light from the lamp` | The light source and color; do not add fabric, injury or other scene content |

If the intended meaning is unclear and affects the boundary or the shot, ask one focused question. If the meaning is already clear, keep the brief moving. In particular, quiet ambience and a muted audio track are different: neither is a universal replacement for “dead silence”.

## A Different Content Proposal

Replacing a depicted element is a content change, not a synonymous repair. Identify what would change and offer a legitimate alternative for the user to choose; do not present it as the same scene or as a way around a restriction. If the user already requested or delegated that change, draft within that scope and state the change without asking again.

| Possible alternative | Disclose the change |
|---|---|
| Show a non-graphic aftermath through abandoned belongings | Visible injury is removed and different evidence carries the aftermath |
| Develop an original fictional character | The requested real-person likeness is not retained; do not claim that renaming a person changes their identity |
| Use an unbranded object | The requested mark is removed; do not claim this preserves the exact product branding |

These alternatives require their own context and boundary assessment. If a required element cannot be retained, say so. Do not conceal prohibited intent with euphemisms, translate it to avoid controls, or probe repeated synonym variants for acceptance. A rewrite does not authorize an upload, a retry, a provider switch or additional spending; follow the user's remaining budget and [retake protocol](retake-protocol.md).

## Multilingual Clarity

Use the user's chosen language, with technical terms from another language only when they help that brief or collaborator. There is no universal language-mixing advantage established here. Preserve exact dialogue and all actual reference tokens, regardless of the surrounding language; follow [Using Reference Examples](surface-prompt-profiles.md#using-reference-examples).

State ownership or authorization only when supported by the supplied context. If it matters and is missing, ask for that information instead of inserting “authorized” into the prompt. Switching languages does not change the underlying content or its applicable boundary.

# Capability Map — design into strengths, around limits

*What Seedance 2.0 is best at, how to extract each strength, and what to design around. Load before prompt planning. Labels: [official] = ByteDance/fal/Ark docs · [field] = practitioner-reported · [heuristic] = default to test. Last verified 2026-06-09. The mechanics behind these rows live in `model-mechanics.md`.*

## Four layers, verified separately

A row below being marked [official] answers one question, not four. Keep these apart, because provider documentation routinely establishes one and says nothing about the rest:

| Layer | The question it answers | What a source can prove |
|---|---|---|
| Model capability | can the model do this at all? | a model-level doc can describe a modality without saying which product exposes it |
| Surface access | does this surface, in this operation, expose it? | availability is per operation; a sibling operation on the same surface proves nothing |
| Request syntax | how is it expressed in the request? | an example demonstrates an authored form; it does not make that form universal |
| Returned adherence | did the output actually follow it? | only an observed take answers this, and one take is an observation, not a guarantee |

The practical rule: never promise a deliverable on the strength of a capability claim alone, and never treat a provider's example as evidence that the result will obey it. A returned take is evidence about that take. It is not proof of the model's internals, and not a promise about the next one.

The rows below are compressed for scanning, so a single `[official]` label sits over several claims at different layers. Split the row before relying on it. The multi-shot row reads:

| Element | Layer | Actually established by |
|---|---|---|
| multi-shot in one call | model capability | provider docs |
| `Shot 1:/2:/3:` labels | request syntax | provider docs, **surface-specific** — Chinese surfaces use a `【时间轴】` timeline instead, see `multishot-grammar.md` |
| Standard tier | surface access | practitioner reports, **not** provider docs |
| 10–15s or `auto` | surface access | provider docs |
| shots × seconds budget | heuristic | a planning default to test, not a documented limit |

One row, four layers, and two different evidence grades. The provenance label on a row is the strongest claim in it, never a guarantee about every element — which is why the tier claims below carry their own `[field]` marker.

## Design INTO these

| Capability | Extraction move |
|---|---|
| Multi-shot in one call [official] | `Shot 1:/2:/3:` labels · one action + one camera each · Standard tier [field] · 10–15s/`auto` · shots×seconds budget |
| Native synced audio [official] | name specific sounds; dialogue as a natural quoted line on-screen; short lines; clean front face ref; SFX>music>dialogue — test dialogue first |
| Role-separated references [official] | per-asset role **+ exclusion** ("motion only, no appearance") |
| Motion transfer via @Video [official/field] | donor clip for choreography/camera rhythm + identity @Image |
| Audio-as-clock via @Audio [field] | "cut on the beat of @Audio1; the turn lands on the drop" |
| First/last frame [official] | lock endpoints; prompt initiate→travel→resolve; transformations & match-cuts |
| Literal camera verbs [official] | one motivated move per shot |
| Physics [official claim] | physical verbs & consequences, not pose adjectives |
| Slow motion [official] | Standard tier [field]; on the single key action |
| Transformation [field] | endpoint states + the persisting carrier; hard cases → FLF decomposition |
| 2D/anime [field] | medium grammar: cel over painted bg, sakuga vs held frames, impact frames/speed lines/smears; no lens/DOF talk — full grammar in `[ref:2d-anime-grammar]` |
| Formats & `auto` [official] | 21:9 for cinema; `auto` sizes duration to complexity |
| Multilingual [official/field] | zh anchors for texture/mood; keep reference tags exact |

## Design AROUND these

For connected generations, design around continuity drift by keeping each clip small, recording accepted observed state, preserving exact reference roles, and re-anchoring on schedule at the scene's chain-depth cap instead of waiting for visible drift. This is workflow guidance, not a deterministic platform guarantee.

Surface duration caps are active-surface facts, not universal Seedance facts; audio is not continuous across separate calls, so score in post when needed [official] · on-screen text → post [official] · negation summons — exclude compositionally [field] · tiny detail (distant faces, hands, logos) degrades [field] · facial micro-acting weakest — stage emotion in body/staging, ration CUs [heuristic] · visible drift after repeated chained generations — re-anchor original refs [field] · character↔prop physics fragile in multi-person shots — keep contact simple or off-screen, use the three-tier action hierarchy [field] · Fast tier behavior is surface-specific [field] · seed = stabilizer, not lock [official].

## Competitive Context *(2026-06-14)*

Native audio is no longer a Seedance-unique differentiator — as of mid-2026 Veo 3.1, Sora 2, Kling 3.0, Runway Gen-4.5, Hailuo 2.3, and Vidu Q3 all ship it [tech-press]. Lead with what is still distinctive in combination — single-pass multimodal references (text+image+video+audio together), multi-shot from one prompt, and multilingual lip-sync — rather than selling native audio as a headline. The official native resolution is 480p/720p; 1080p is surface-specific (see `api-status.md`).

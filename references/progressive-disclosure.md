# Progressive Disclosure Plan

The root skill should route. Sub-skills should decide. References should carry dense tables and volatile facts. The active context stays small because weight is loaded only when a task earns it.

## The real file set

| Layer | Files | Load condition |
|---|---|---|
| Root router | `SKILL.md` | Always. Owns the Fast Lane, the gates, the Sequence Gate, and the Load Map - nothing dense. |
| Sub-skills | 28 `skills/seedance-*/SKILL.md` | When the task is that skill's job. Each is medium-weight: intent, contracts, and routing, not databases. |
| References | 59 `references/*.md` | On demand, named by a gate or a Load Map row. Most are cheap; a few are heavy (below). |

Do not move large databases back into active sub-skill bodies, and do not load a heavy reference by default.

## Heavy vs cheap references

Most references are small lookup tables loaded freely. A few are heavy and must be loaded only when the task needs them, never preemptively:

- [`directors-read.md`](directors-read.md) is the cheap exception to on-demand disclosure: every brief route loads this canonical classification and pre-compilation contract. Narrative work completes the full read; non-narrative work records the utility refusal without fabricated drama.
- [`directing-engine.md`](directing-engine.md) - the deeper directorial reasoning layer (the Coherence Principle, instrument choices, Director's Voice, and long-form spine). Loaded after the canonical Director's Read when scenes need distinct treatment, a setup is unclear, or a voice must hold across clips.
- [`directing-engine-genre-library.md`](directing-engine-genre-library.md) - 33 fully worked genre examples. Loaded only when the user wants a worked example in a specific genre, via the genre/examples Load Map row, never by the always-on Direction step.
- [`api-status.md`](api-status.md), [`platform-surface-matrix.md`](platform-surface-matrix.md), [`api-workflow.md`](api-workflow.md) - dated, volatile platform facts. Loaded only behind the source gate, and kept fresh (see the freshness rule below).
- [`pro-filmmaking-standards.md`](pro-filmmaking-standards.md) - the professional production spine. Loaded only behind the professional gate.

## Genre-content ownership

Genre craft appears in three places; each owns one job so they stop diverging:

- `directing-engine.md` / `directing-engine-genre-library.md` own the **derivation** - why a genre is shot, lit, and performed the way it is (read -> intention -> voice -> setup).
- `genre-guides.md` owns the **priorities** - what each genre most needs protected (product identity, lip-sync, beat-sync).
- `seedance-recipes` + `examples-by-mode.md` own the **skeletons** - copy-ready starting patterns.

A genre fact's single source of truth is its derivation file; the others reference it rather than restating it.

## Freshness rule

Dated platform references must not drift far behind `api-status.md`'s `last_verified` date. If `api-status.md` advances and a freshness-critical reference still cites an old verification date, re-verify and re-stamp it (or confirm it is still accurate) before release. Intentionally frozen snapshots such as `research-2026-05-30.md` are exempt; their date is part of their identity.

## V6 Sequence Disclosure

Root `SKILL.md` owns only the Sequence Gate and invariants. `skills/seedance-sequence` owns global planning and current-clip compilation. `skills/seedance-continuation` owns accepted-footage continuation and re-anchoring. Dense state details live in `references/sequence-project-state.md`, `references/continuation-handoff.md`, and `references/prompt-compiler.md`.

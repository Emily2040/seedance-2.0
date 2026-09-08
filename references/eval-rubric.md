# Eval Rubric

Each eval case should verify activation, output structure, safety behavior, and prompt usefulness.

Score each case from 0 to 3:

- 0: wrong skill or unsafe output.
- 1: partial skill match but poor structure.
- 2: correct structure with minor omissions.
- 3: correct activation, concise output, safety-aware, prompt-ready.

A release passes when every legacy case scores at least 2 and the legacy average score is at least 2.6.

This model-judge score is evidence about the sampled response against declared assertions, not a language, culture, authorship, reviewer, or rendering certification. Chinese, Japanese, and Korean language-quality claims require the independent human protocol in [`multilingual-native-review.md`](multilingual-native-review.md); its canonical fixture remains pending until that review happens.

## V6 Sequence Rubric

Use a 0-4 scale for sequence-state evals:

- 0: fails the behavior or creates a safety/continuity regression.
- 1: mentions the right idea but misses operational requirements.
- 2: partially satisfies the behavior with important gaps.
- 3: satisfies the behavior with minor omissions.
- 4: fully satisfies the behavior and preserves all relevant constraints.

Dimensions: routing correctness, story architecture, clip-scope control, actual-state grounding, continuity integrity, reference binding, mode and surface selection, endpoint quality, prompt architecture, uncertainty handling, safety and rights.

Release threshold: all critical continuation cases score 4, no dimension scores below 3, overall average is at least 3.5, and existing standalone behavior does not regress.

For `scripts/prompt_architecture_stress.py --strict`, “no dimension below 3”
means every applicable blocking dimension on every `skill_formula` case, not
an average dimension score across the arm. The v3 gate excludes `slop_free` and
`length_fit` from both dimension floors and its overall average; lexical flags
and fixed length bands remain advisory. The arm average must also remain at least 3.5,
and cross-case duplicate or near-duplicate prompts fail when their briefs are
materially different. This deterministic gate catches structural, relevance,
explicit contradiction, and repetition failures only. It does not judge
creativity or originality; comparative creative quality requires blinded model
evaluation and native-language human review.

## Advisory Lexical Score and Context Review

The architecture report's `lexical_v1` column retains the JSON dimension name
`slop_free` for compatibility. It is a fixed lexical proxy, not a judgment that
the matched words are filler. Its existing formula is `max(0, 4 - 1.25 * U - E)`,
where `U` counts distinct listed terms matched in the prompt and `E` counts those
also matched in its first 25 words. The reported density is distinct matched
terms per 100 tokenizer words, not occurrence frequency. The extra early-word
penalty is a historical test weight, not measured model token importance.

Each JSON result includes `lexical_review` with metric `legacy-lexical-v1`,
matched terms, early matched terms and that density. `context_assessed: false`
means the scanner has not decided whether a phrase is useful in this brief.
`rewrite_recommended: false` means the scanner itself recommends no rewrite;
it does not certify that the prompt needs no editing. An empty match list only
means none of the listed terms matched, not that the prompt is original or good.

| Context to inspect | Why a lexical penalty is insufficient |
|---|---|
| A chosen cinematic or ultra-realistic look | A style label can carry intent even when it appears on the list |
| Exact dialogue containing "beautiful" | A word in required speech is not automatically redundant praise |
| An explicit 8K delivery requirement | Keep the target in supported settings or state the gap; do not delete it to improve a score |
| Unspecified "beautiful, cinematic, masterpiece" praise | A match can prompt review of missing decisions, but the scanner cannot determine intent or authorize replacement details |

Review flagged language against the brief and [anti-slop-lexicon](anti-slop-lexicon.md).
Preserve exact speech, reference bindings, useful style choices and delivery
requirements. The matcher does not exempt quoted text or infer intent; keyword
exceptions alone would not create a contextual creative judge.

## Previous Gate: architecture-v2-nonlexical

The v2 migration left the keyword list, lexical formula and every individual
dimension score unchanged. JSON `overall` retained the legacy average including
the lexical proxy. Its gate excluded only `slop_free`, so fixed word bands still
affected the average and dimension floors. The current report preserves that
comparison in `previous_gate`, described below.

V2 used non-lexical floors of 3 and an arm mean of at least 3.5. Duplicate and
near-duplicate checks remained blocking, with reference integrity included for
modes where it applies. Excluding a dimension changed the aggregate even though
the numeric thresholds stayed fixed.

A useful style label, quoted line or delivery target cannot fail the gate solely
because it matches the lexical list. Equally, a generic adjective bank attached
to an otherwise structurally valid brief can pass: this gate does not judge its
creative usefulness. Irrelevance, explicit contradictions, repetition and missing
reference bindings remain separate failures. Review lexical flags in context;
passing the gate is not an instruction to retain redundant praise or a quality
certification.

The frozen corpus is retained for before/after comparison. Migration tests cover
useful flagged contexts, unchanged legacy values, the remaining dimension floors,
irrelevant or repeated padding, and real CLI behavior. This is a change to the
role of a diagnostic, not a semantic classifier or evidence of improved rendering.

## Current Gate: architecture-v3-advisory-length

The fixed `length_fit` bands describe a frozen regression heuristic, not a
universal Seedance prompt budget or a test of completeness. The legacy function
awards 4 for 60-100 tokenizer words, 3 for 40-59 or 101-110, 1.5 below 40 or at
111-140, and 0 above 140. These scores and their historical notes remain unchanged
for comparison. Labels such as "under-specified" and "over budget" are historical
labels, not findings about the current brief. Do not pad a complete short brief or
delete required dialogue to satisfy them.

Each JSON result adds `length_review` with metric `legacy-word-bands-v1`, `count`
and `unit`. The count splits text on whitespace; it is neither a model token
count nor a multilingual word count. A Chinese or Japanese sentence without
spaces counts as one chunk, as does an attached reference tag. Do not use it to compare
language efficiency or set localized limits. `context_assessed`,
`user_limit_assessed`, `operation_limit_assessed`, `dialogue_timing_assessed` and
`rewrite_recommended` are all false: no completeness, compliance, timing or
rewrite judgment has been performed.

| Decision outside the fixed-band gate | Required handling |
|---|---|
| A user asks for a brief under 40 words | Respect that request using its stated unit; retain the necessary action and constraints without padding |
| Exact dialogue makes the draft longer | Preserve the requested speech; check timing and clip scope, and discuss splitting or an authorized edit if it cannot fit |
| A selected operation has a documented input cap | Verify the current operation and its counting unit; resolve an overrun before submission |
| A complete brief has no stated length constraint | Review relevance and clarity; a word-band score alone authorizes neither expansion nor deletion |

The static evaluator does not enforce these user or platform limits and cannot
certify generation readiness. Passing it does not permit ignoring a limit,
silently shortening speech, uploading assets or spending credits.

`gate_version` is now `architecture-v3-advisory-length`. `gate_dimensions`
contains the applicable dimensions other than `slop_free` and `length_fit`;
`gate_overall` is their mean rounded to three decimals. `previous_gate` retains
the v2 `version`, `dimensions` and `overall` (excluding only `slop_free`). JSON
`overall` and all individual dimension scores and notes retain their legacy
meaning. The CLI shows `gate_v3`, `prior_v2` and `legacy` averages separately.
Consumers must check the version rather than compare differently defined means.

Every case and applicable blocking dimension must score at least 3; the mean
of rounded case gate scores for an arm must remain at least 3.5. Reference,
relevance, explicit contradiction, structure, coverage, opening and repetition
checks remain blocking, as do cross-brief duplicate/near-duplicate checks. These
are unchanged heuristics with their own limits. Removing the length floor and
its contribution to the mean changes acceptance behavior even though the numeric
thresholds stay fixed; the prior-v2 average is a comparison, not a second gate.

Migration tests include a complete brief below 40 words, a supplied dialogue
specimen above 140, incomplete short text, repeated long padding, frozen band
edges and CLI boundaries. The dialogue specimen is an offline regression case,
not evidence that a platform can deliver that passage in one clip. Neither the
fixtures nor the frozen corpus are model, native-language or rendered evaluation.

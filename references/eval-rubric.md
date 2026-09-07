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
means every applicable non-lexical dimension on every `skill_formula` case, not
an average dimension score across the arm. The v2 gate excludes `slop_free` from
both dimension floors and its overall average; lexical flags remain advisory. The arm average must also remain at least 3.5,
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

## Gate Migration: architecture-v2-nonlexical

The keyword list, lexical formula and every individual dimension score remain
unchanged. JSON `overall` still contains the legacy average including the lexical
proxy. New fields identify the actual release gate: `gate_version`,
`gate_dimensions` (the applicable dimensions other than `slop_free`) and
`gate_overall` (their mean, rounded to three decimals). The CLI displays both
`gate_v2` and `legacy` averages so they cannot be mistaken for the same baseline.

Strict validation now uses only `gate_overall` and non-lexical floors. Every case
and applicable non-lexical dimension must still score at least 3, and the arm's
mean gate score must remain at least 3.5. Duplicate/near-duplicate checks remain
blocking. Reference integrity is included for modes where it applies. No threshold
was lowered, but excluding a dimension changes the aggregate; compare the two
averages explicitly rather than calling them equivalent.

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

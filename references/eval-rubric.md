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
means every applicable dimension on every `skill_formula` case, not an average
dimension score across the arm. The arm average must also remain at least 3.5,
and cross-case duplicate or near-duplicate prompts fail when their briefs are
materially different. This deterministic gate catches structural, relevance,
explicit contradiction, and repetition failures only. It does not judge
creativity or originality; comparative creative quality requires blinded model
evaluation and native-language human review.

## Legacy Lexical Score and Context Review

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

This reporting change keeps the term list, numeric scores, aggregate calculations,
frozen corpus and strict thresholds unchanged. Consequently, the legacy gate can
still fail a useful phrase on this dimension. Treat that as a limitation to review,
not an instruction to erase the phrase. Any later scoring migration must explicitly
compare old and new results, retain regression evidence and document threshold
changes; this release does not claim that contextual scoring has been solved.

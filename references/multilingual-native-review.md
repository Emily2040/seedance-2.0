# Multilingual Native-Review Boundary

This rubric asks whether the Chinese, Japanese, and Korean prompt specimens use differentiated, idiomatic production language for their declared locales. It does not identify who wrote them or prove the author's background. The canonical review inputs live in [`evals/multilingual-native-review.json`](../evals/multilingual-native-review.json).

The fixture is deliberately marked `pending_native_review`. Its text and three creative-lens choices are hypotheses for review, not certified examples or definitions of a culture.

## Claim boundary

A static check can establish fixture structure, source-path existence, literal cross-locale realization overlap, candidate and review-input hashes, canonical common-brief and reference-binding integrity, byte-for-byte reference-token preservation, and the canonical disclaimer's exact path, LF-normalized bytes, unique top-level placement, and digest. Semantic differentiation, reference-role correctness, reviewer reasoning, and the absence of arbitrary prose overclaims remain human judgments.

Static validation cannot establish native fluency, native-language quality, cultural authenticity, native authorship, author provenance, reviewer identity or qualifications, model-output quality, or generated-video quality;
independent human review remains required.

The disclaimer is the hard public-claim contract: its path, exact LF-normalized bytes, unique top-level rendered placement, and SHA-256 are versioned in `evals/multilingual-native-review.json`. Only CRLF-to-LF line-ending normalization is permitted. Tabs, altered spacing, Markdown hard breaks, blockquotes, code blocks, comments, metadata, punctuation changes, prefixes, and suffixes are different bytes and fail validation.

A separate best-effort English known-phrase linter scans tracked or unignored regular UTF-8 files outside the explicitly internal or binary roots `.git`, `.seedance_backups`, `__pycache__`, `assets`, `evals`, `scripts`, and `tests`; each candidate is capped at 2,000,000 bytes. It is not a semantic classifier, does not cover every paraphrase or language, and cannot prove that arbitrary prose contains no overclaim. The `public-claim-dashes-v1` repertoire is exactly `U+002D U+00AD U+058A U+05BE U+1400 U+1806 U+2010 U+2011 U+2012 U+2013 U+2014 U+2015 U+2043 U+2053 U+207B U+208B U+2212 U+2E17 U+2E1A U+2E3A U+2E3B U+2E40 U+2E43 U+2E5D U+301C U+3030 U+30A0 U+FE31 U+FE32 U+FE58 U+FE63 U+FF0D U+10EAD`; it is regression documentation for that lint, not a universal language boundary. Human review remains responsible for semantic claims in every supported locale.

The machine gate must therefore say that the fixture is structurally valid and still pending human review. It must never convert a parser pass, keyword count, script detector, or exact-string comparison into a quality claim. A model-judge score is not a language-mastery certification. The fixture is repository-authored; it is not a captured Seedance response and it is not a rendered-video benchmark.

## Reviewer boundary

Use exactly two independent reviewers per locale, one in each role:

1. A target-locale language editor judges idiom, cadence, language register, relationship wording, and calques.
2. A target-locale culture and production reviewer judges the creative-lens hypothesis, directing usefulness, and stereotype risk.

Reviewers disclose their role, stable reviewer ID, authorship, and conflicts. Neither reviewer may have authored the specimen or have a material conflict. Reviewer IDs use visible canonical ASCII so format controls, zero-width characters, and Unicode lookalikes cannot evade duplicate detection. Tooling still cannot prove that two IDs belong to different people or verify experience or cultural standing; maintainers verify those facts manually before accepting the records.

Do not average a material disagreement into a pass. Revise the specimen, keep both reviewers' quoted evidence in version history, increment `fixture_revision` and `review_round`, refresh `candidate_sha256`, `common_brief_sha256`, and `review_input_sha256`, and start a new independent round. If a reviewer rejects the creative-lens hypothesis, change it; the fixture is not ground truth about a culture.

## Review setup

- Review one locale at a time. Show the common brief, production contract, external controls, reference bindings, declared locale/script, and that locale's specimen. Hide the other two specimens until independent notes are complete.
- Keep `@Image1`, `@Video1`, and `@Audio1` byte-for-byte identical to the source brief and keep their roles fixed: identity/wardrobe, camera rhythm only, and tempo only. Reordering, duplicating, translating, full-width substitution, localizing, or role-swapping a token is a hard failure. The machine pins the full common brief, its hash, the canonical candidate spans, and the complete review-input hash; the language editor still verifies that the localized wording expresses each role naturally.
- Duration is an external surface setting fixed at eight seconds. Do not fault a specimen for omitting duration from prompt prose; do fault a review that silently changes that ownership.
- Judge the written production direction, not imagined model behavior. Do not infer that Seedance will follow the prompt or that a rendered clip will be good.
- Quote the exact localized `candidate_prompt` phrase behind every material score, including brief fidelity. The common brief is hash-bound review context, not evidence of specimen quality. Each quote must equal one of that criterion's pinned `criterion_evidence_anchors` phrases, contain at least eight target-script characters, and differ from the reviewer's other criterion quotes. Begin each reason with `<criterion_id>: ` and write at least 32 characters. After that required prefix, the reason body must contain at least 12 Unicode alphanumeric characters and no Unicode control or format characters. CI compares the NFKC- and case-folded sequence of alphanumeric tokens, ignoring punctuation and its count, so punctuation variants cannot disguise one reused lexical body across criteria. These are structural safeguards for criterion-specific evidence, not a machine judgment that the reasoning is true or adequate.
- Suggest a concrete localized replacement containing at least eight target-script characters for every `revise` or `fail` finding. A score of 3 must leave `proposed_revision` empty. Preserve the brief, production contract, external controls, and reference tokens in the revision.
- Bind every completed review to `case_id`, locale, evidence and fixture schema versions, `fixture_revision`, `review_round`, `candidate_sha256`, `common_brief_sha256`, `review_input_sha256`, `rubric_sha256`, `review_protocol_sha256`, and the reference-token byte manifest. The fixture root and every locale case use exact accepted-key schemas; unknown keys are rejected. The canonical review-input object contains every accepted case field except the self-referential `review_input_sha256` and the pending/result `review_record`, and its digest therefore cannot silently ignore another accepted input field. CI compares that complete digest, revision, and round with a non-derived canonical pin included in the protocol hash. Recomputing fixture and evidence hashes together is not an advance: any review-input edit must visibly advance the pinned revision, round, and digest as one protocol change. Any review-input, rubric, scoring-policy, dimension-contract, exact-schema, or dash-repertoire edit invalidates evidence carrying the old binding.
- Record completed evidence only in [`evals/multilingual-native-review-evidence.json`](../evals/multilingual-native-review-evidence.json). CI parses every submitted set, derives its verdict, and rejects stale, incomplete, conflicted, author-written, duplicate-reviewer, ungrounded, or disagreement-hidden evidence. The shipped empty artifact means no completed review exists.

## Scoring

Each reviewer scores only dimensions owned by that role. `both` means both reviewers submit separate evidence. This fixture does not allow `N/A`: a silent prompt still makes choices about relationship wording, production language, and social distance.

For every owned dimension, score 0 to 3. A 1 has a major repair; a 2 is usable with a localized repair; the dimension-specific 0 and 3 anchors are below.

| Dimension | Owner | 0 anchor | 3 anchor | Hard failure |
|---|---|---|---|---|
| Brief and reference fidelity | both | Changes the scene job, external duration owner, a reference role, or a required production invariant. | Every production-contract and reference-binding span is present, coherent, and faithful to the common brief. | Any missing, extra, reordered, byte-changed, or role-swapped reference token. |
| Idiomatic production language | target-locale language editor | Syntax or collocation requires mental retranslation to recover the direction. | Clauses, rhythm, and production vocabulary read naturally for the declared locale. | The intended instruction cannot be recovered reliably. |
| Language register and relationship | target-locale language editor | Wording contradicts the age, familiarity, social distance, or declared no-dialogue mode. | Relationship language and cadence are consistent; any later dialogue dependency is called out. | A contradiction changes the implied relationship or performance. |
| Creative-lens realization | target-locale culture and production reviewer | A bare label, semantic copy of another locale, or generic shorthand does all the work. | Visible, audible, temporal, material, and relational choices make the hypothesis specific to this beat without needing the label in prompt prose. | A copied pan-CJK template is presented as cultural differentiation. |
| Production directability | target-locale culture and production reviewer | Action, camera, light, or sound directions conflict or lack a playable endpoint. | One action, one distinct camera move and endpoint, motivated practical light, room tone, and textless delivery are immediately playable. | The action or camera endpoint is indeterminate. |
| Representation and stereotype risk | both | Props, class markers, costume, architecture, or media shorthand essentialize the locale. | Every locale-marked detail has a causal job in this beat and avoids exoticizing or demeaning shorthand. | Essentializing, exoticizing, or demeaning treatment. |

A locale passes only when each required owner scores every owned dimension at least 2, both reviewers score `brief_and_reference_fidelity` and `representation_and_stereotype_risk` at 3, there is no hard failure or unresolved disagreement on any dimension scored by more than one reviewer, and every score carries a criterion-anchored localized candidate quote of at least eight target-script characters plus a criterion-prefixed reason. Otherwise the overall state remains `pending_native_review` until a revised, re-hashed specimen completes a new round.

## Locale lenses

These are review questions, not automatic answers. The label is metadata for a creative-lens hypothesis; it is not required in candidate prompt prose, and deleting it must not weaken the physical direction. A qualified reviewer may reject the label, the realization, or both.

### zh-CN · Hans · handoff-pause hypothesis

- Do the wiped counter mark, held hand, two-hand composition, two-beat hold, and room tone make the handoff pause legible without a generic warm grade?
- Does the specimen remain a small food counter rather than drifting into an unrelated market, restaurant, or prestige set?
- Is the Simplified-script and mainland-locale choice explicit, with no silent claim that it also covers zh-Hant, Taiwan, Hong Kong, or Macau delivery?
- Are measure words, action endpoints, and compact production clauses idiomatic rather than English clauses with Chinese nouns substituted?
- Reject decorative red lanterns, dragons, calligraphy, or luxury objects when they do no work in this specific beat.

### ja-JP · Jpan · two-beat-hold hypothesis

- Do the hand leaving frame, stopped camera, two-beat hold, silence, and room tone make the temporal pause without relying on a prestige label?
- Does the lateral counter move have a natural endpoint, and does the held duration read as a production instruction rather than literary narration?
- Does the warm hand-towel gesture read as situated care in this exact relationship, or as an imported stereotype? Quote the span behind the decision.
- If dialogue is added later, review pronoun, relationship, speech level, and mora budget together.
- Reject generic slow motion, wistful grading, cherry blossoms, or `侘び寂び` vocabulary pasted onto material that does not support it.

### ko-KR · Kore · glove-return-endpoint hypothesis

- Does returning the forgotten gloves in a paper bag read as one practical gesture rather than a contrived cultural signal? Quote the span behind the decision.
- Does the tilt-down end on one clear handoff state without turning the beat into several actions?
- Is the paper-bag sound a motivated material cue rather than decorative sentiment?
- If dialogue is added later, lock one speech level and verify that age, familiarity, and social relation license it.
- Reject drama shorthand, hanbok, palace imagery, tears, sentimental backlight, or music when the beat does not motivate them.

## Adversarial review

Run these attacks before recording a verdict:

1. Replace `@Image1` with `＠Image1`, `@画像1`, or `@이미지1`. The machine gate must fail before human review.
2. Keep all three token strings but swap their declared roles. The reference-binding gate must fail.
3. Copy one locale's physical realizations into another locale. Literal identical strings must fail the fixture check. A translated, structurally copied, or lightly paraphrased template remains an independent-review question because static comparison cannot establish semantic differentiation; CI must not claim otherwise.
4. Delete the concrete realizations and leave only a lens label, or add the label to otherwise generic prose. Independent review must fail creative-lens realization; the label itself earns no credit.
5. Add a stereotyped prop or class marker that has no causal role in the beat. Independent review must fail representation and stereotype risk.
6. Edit a candidate, common brief, contract, lens realization, revision, or review round without refreshing every review-input binding. The machine gate must reject the stale completed evidence.
7. Mark the fixture as linguistically certified, model-evaluated, or video-evaluated because the static checker passes. The claim boundary must fail.
8. Submit a `pass` with one reviewer, duplicate IDs, an author or conflicted reviewer, missing owned criteria, invented quoted spans, a below-threshold score, or unresolved disagreement. The evidence gate must fail.
9. Cite the common brief, a bare reference token, fewer than eight target-script characters, the wrong criterion anchor, or one recycled quote/reason as evidence. The evidence gate must fail because the citation does not demonstrate criterion-specific localized specimen evidence.

## Evidence record

Create one review set per locale and current round. The two reviewer records live inside that set so CI can derive disagreement and the overall verdict:

```text
case_id:
locale:
review_evidence_schema_version: "1.0"
fixture_schema_version:
fixture_revision:
review_round:
candidate_sha256:
common_brief_sha256:
review_input_sha256:
rubric_sha256:
review_protocol_sha256:
reference_token_bytes:
reviewers:
  - reviewer_id:
    reviewer_role:
    authorship_disclosure: not_specimen_author
    is_specimen_author: false
    conflict_disclosure: none
    has_material_conflict: false
    criterion_results:
      - criterion_id:
        score_0_to_3:
        quoted_source: candidate_prompt
        quoted_span:
        reason:
        proposed_revision:
    verdict: pass | revise | fail
disagreement:
  status: none | unresolved
  summary:
verdict: pass | revise | fail
```

Keep the canonical fixture pending and unscored. Completed evidence is valid only through the CI-checked evidence artifact, bound to the exact current revision, round, candidate, common brief, token manifest, complete review-input hash, rubric bytes, and review-policy/dimension hash. A valid evidence record proves only that the declared review process was recorded consistently; it does not establish who the reviewers or authors are, universal linguistic mastery, or cultural authority.

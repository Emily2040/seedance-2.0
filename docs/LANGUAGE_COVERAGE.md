# Language coverage: available is not reviewed

English, Chinese, Japanese, Korean, Spanish and Russian have quickstarts and
production vocabulary. Their coverage differs. **No completed independent native
review or rendered-language pilot is claimed by this matrix.** The existing
[CJK review protocol](../references/multilingual-native-review.md) applies to its
three named specimens, not every page written in those languages.

| Language | Quickstart | Vocabulary | Full README | Independent review |
|---|---|---|---|---|
| EN | [Available](QUICKSTART.md) | [Available](../references/vocab/en.md) | [English source](../README.md) | Pending |
| ZH | [Available](QUICKSTART.zh.md) | [Available](../references/vocab/zh.md) | [Available](README.zh.md) | Pending; fixture scope zh-CN / Hans only |
| JA | [Available](QUICKSTART.ja.md) | [Available](../references/vocab/ja.md) | [Available](README.ja.md) | Pending; fixture scope ja-JP only |
| KO | [Available](QUICKSTART.ko.md) | [Available](../references/vocab/ko.md) | [Available](README.ko.md) | Pending; fixture scope ko-KR only |
| ES | [Available](QUICKSTART.es.md) | [Available](../references/vocab/es.md) | Not provided | Pending; locale/register must be declared |
| RU | [Available](QUICKSTART.ru.md) | [Available](../references/vocab/ru.md) | Not provided | Pending; locale/register must be declared |

An available README is not proof of full semantic parity with the English source.
English also needs independent production-language review; being the source
language is not a quality verdict. Regional variants and mixed-language dialogue
need their own declared scope. Avoid ranking languages by model reliability from
these files or extrapolating a three-specimen review to whole-language support.

## Shared concepts to preserve

These stable IDs bind review discussions to meaning, not a preferred literal
translation. Consult each vocabulary file for candidate wording; a qualified
reviewer may replace it while preserving the invariant.

| Concept ID | Required meaning | Review probe |
|---|---|---|
| REF-ROLE | A real asset has one declared role; preserve the user's exact token spelling. | Keep `@Image1`, `@图片1` and `[Image 1]` unchanged when they are supplied; never invent bindings. |
| STATE-OBSERVED | Continue from what the accepted frame shows. | Door already open, hand off latch: do not reopen it in translation. |
| ACTION-ENDPOINT | Name a visible action and its completion. | Fold the final pleat, release the paper fan, hold the settled fan. |
| CONTROL-OWNER | Surface settings and prompt prose have separate owners. | Keep a locked duration/aspect ratio in the settings field; do not silently change either. |
| DIALOGUE-EXACT | Exact dialogue stays verbatim unless translation is requested. | Keep “It still ticks.” verbatim for an exact-English-line brief; distinguish a requested translation. |
| AUDIO-MODE | Speech, ambience, music and silence are explicit choices. | Preserve “no music” without removing clock ticks or adding narration. |
| USER-CHOICE | Honor the user's chosen treatment and revision budget. | A joyful observational scene must not gain a mandatory dramatic conflict. |
| SPEND-BOUNDARY | Preparing a prompt does not authorize a paid request. | Preserve a remaining one-attempt budget; do not propose unbounded retries. |

## Source and translation drift

The repository's `evals/language-coverage.json` records a source commit and
LF-normalized SHA-256 snapshots. Run `python scripts/language_coverage.py` from
a repository checkout to inspect current drift. It tracks the root, prompt,
interview and audio guidance plus all six quickstarts and vocabulary pages.
README entries are availability-only; their full parity is not checked. This
declared scope is a starting contract, not all repository documentation.

Any tracked source or target byte change produces `stale_review_required` for
the affected languages (a source change affects all six). That conservative flag
can include wording-only edits; the tool cannot decide whether meaning changed.
No change produces `unchanged_unreviewed`, never “current translation” or “fluent.”
CI checks the contract and reports flags; a stale flag is review work, not a
reason to block unrelated repository fixes. Missing paths or malformed snapshots
remain structural failures.

For a source meaning change, list affected concept IDs and source commit, inspect
all relevant translations, and retain exact before/after wording. Do not clear a
flag by refreshing hashes alone. Record reviewer, rationale and scoped parity
decision in the PR, then update the affected snapshots and source revision.
Record a non-semantic change with its rationale too. These are maintainer review
requirements; hashes establish byte identity, not honesty of a review.

## Native and dialogue review next

For each locale, commission a language editor and a production-language reviewer
independent of the specimen author. Declare region, script, intended relationship,
formality and audience before evaluating idiom. Review a technical instruction,
a compact action prompt, exact dialogue and a conversational alternate register.
Keep supplied reference tokens and quoted exact lines byte-for-byte intact.

Use concept IDs to report omissions, calques and meaning changes. For dialogue,
check speaker relationship, pronouns, speech level, cadence, pronunciation and
timing against the declared surface duration. Reading aloud is timing evidence,
not rendered lip-sync evidence. Rendered speech needs a separately authorized
pilot with retained audio/video and cost records.

Retain independent scores, exact quotes, localized replacements, source hashes,
reviewer IDs/conflicts and disagreement. The existing CJK evidence schema must
not be repurposed to certify EN/ES/RU or unrelated specimens. Extend its scope in
a separate reviewed change before accepting those completed records. Until then,
this contract stays pending even if all availability and drift checks pass.

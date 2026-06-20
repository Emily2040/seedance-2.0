# Community Source Methodology

last_verified: 2026-05-30

Use this when mining prompt corpora, forums, Reddit posts, Chinese guides, Russian guides, or wrapper documentation.

## Allowed Extraction

- Prompt structure.
- Timing syntax.
- Camera, lighting, motion, audio, VFX, and constraint vocabulary.
- Reference-role language.
- Failure modes and safe repairs.
- Source metadata: URL, author handle, language, date, and surface.

## Disallowed Extraction

- Protected characters, franchises, exact scenes, studios, or songs as reusable examples.
- Celebrity, public-figure, private-person, or voice imitation prompts.
- Filter bypass or evasion instructions.
- Wrapper pricing as general Seedance pricing.
- Private-channel claims that cannot be rechecked.

## Corpus Labels

| Label | Meaning |
|---|---|
| `safe-example-candidate` | Can be rewritten into active docs with minor cleanup. |
| `safe-structure-only` | Mine structure/vocab only; do not copy prompt content. |
| `ip-risk` | Contains protected character, franchise, studio, exact scene, or song. |
| `real-person-risk` | Contains real face, public figure, celebrity, or voice imitation risk. |
| `brand-risk` | Contains brand/logo/product identity requiring authorization. |
| `violence-risk` | Needs non-graphic staged-action rewrite or exclusion. |
| `low-quality` | Too generic, incoherent, or slop-heavy to mine. |

## Transformation Rule

Raw community prompts should become original safe examples. Replace protected names with archetypes, named brands with user-owned/product placeholders, and real-person references with authorization-gated language.

## Sequence Example Rule

Do not copy commercial creators' continuation prompts as golden examples. Extract reusable structure only: actual ending, completed action, current clip job, reserved future action, reference-transfer boundary, and endpoint. Rewrite into original sequence examples with synthetic project IDs and clearly synthetic fixtures.

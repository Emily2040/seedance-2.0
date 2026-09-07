# Surface Prompt Profiles

Use this reference to keep platform behavior surface-specific. Do not hardcode duration, prompt length, reference counts, tag syntax, edit support, extension support, audio behavior, regions, pricing, or authorization requirements as universal Seedance facts.

## Profile Fields

For the active surface, resolve:

- exact reference-tag convention;
- verified duration range;
- prompt budget;
- supported reference roles;
- timeline syntax;
- edit or extension availability;
- audio behavior;
- known constraints;
- source and verification date.

If the surface is unknown, state that the profile is conservative and avoid unsupported numbers.

## Using Reference Examples

Vocabulary tables and templates illustrate wording. Their `@Image1`, `@图片1`, `@Video1` and similar tokens do not attach files or establish that an operation supports those assets or roles.

Before adapting a reference example:

- Identify the real asset and its requested role, then check the active operation's binding convention and role support. Match by the agreed role, not by upload order, filename or the example's number.
- Substitute the confirmed binding for the example placeholder. Preserve that actual token exactly, including script, case, spaces and punctuation; translate only the surrounding prose. Follow the [Exact Tag Rule](reference-transfer-contract.md#exact-tag-rule). A user-supplied token with unverified attachment status remains unverified, even when its spelling is preserved.
- If an asset or binding is missing or ambiguous, name the missing information and ask only what is needed. A planning example may keep clearly labeled placeholders outside submission-ready text. Do not fabricate an attachment or silently switch a reference-based request to text-only generation.
- If the operation uses structured asset fields rather than inline tags, use its documented binding mechanism. When moving to another surface, resolve a new mapping explicitly; translation alone is not permission to normalize existing tokens.

For example, if the confirmed identity asset is `[Image 1]`, retain both brackets and the space when writing Japanese or Chinese direction. If it is `@图片1`, do not replace it with `@Image1` merely because the surrounding prompt is English. These are conditional examples, not a claim that every surface accepts either form. If two assets appear to share a token, resolve the ambiguity before compiling; do not guess from their numbers.

## Conservative Generic Profile

Use only when no surface is known:

- plan one compact generation-sized clip at a time;
- keep prompt concise;
- preserve exact user-supplied tags;
- avoid asserting native extend, prompt limits, or reference counts;
- ask for the actual clip or final frame before continuation;
- prefer role-bound references over unsupported feature claims.

## Volatile Claim Rule

For current model names, pricing, upload limits, reference counts, regions, endpoint names, or authorization requirements, load source-gated references and verify with dated primary sources before making operational claims.

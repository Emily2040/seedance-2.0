# V6 Release Readiness

Use this document when checking the active front page before merge.

## Current Release Surface

- README badge, update line, changelog pointer, and active skill metadata must show `6.0.0`.
- Active docs should describe v6 sequence-state architecture, prompt compiler behavior, and multilingual reader paths.
- Historical version details belong in `CHANGELOG.md`, `references/migrated/`, or Git history, not the active README surface.

## Front Page Checks

- The README has a visible native-language start section for English, Chinese, Japanese, and Korean readers.
- Chinese, Japanese, and Korean rows link to active skill files and active vocabulary references.
- The old planning documents are no longer part of the active docs directory.
- The design doc describes current v6 front-page requirements.

## Validation

Run the repository validation suite from the README before publishing a release or merging a front-page update.

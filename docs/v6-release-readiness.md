# V6 Release Readiness

Use this document when checking the active front page before merge.

## Current Release Surface

- README badge, update line, changelog pointer, eval metadata, validator expectations, examples, and active skill metadata must show `6.0.1`.
- Active docs should describe v6 sequence-state architecture, prompt compiler behavior, and multilingual reader paths.
- Historical version details belong in older `CHANGELOG.md` entries, `references/migrated/`, or Git history, not the active README surface.

## Front Page Checks

- The README has a visible native-language start section for English, Chinese, Japanese, and Korean readers.
- The README links to full native reader guides: `docs/README.zh.md`, `docs/README.ja.md`, and `docs/README.ko.md`.
- Chinese, Japanese, and Korean rows link to active skill files and active vocabulary references.
- Japanese and Korean have active examples skills, not only vocabulary skills.
- The old planning documents are no longer part of the active docs directory.
- The design doc describes current v6 front-page requirements.

## Validation

Run the repository validation suite from the README before publishing a release or merging a front-page update.

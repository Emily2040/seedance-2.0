# Check an installation before replacing it

Run this read-only command from a reviewed source checkout:

```sh
python scripts/install_doctor.py
python scripts/install_doctor.py --client codex --scope user --json
python scripts/install_doctor.py --dest /path/to/skills --json
```

`--dest` names the skills parent directory, exactly as for the installer. The
doctor appends `seedance-20`. It does not install, update, back up, delete,
recover transactions, contact providers or read credentials. It is a source
checkout tool, not part of the installed runtime payload.

The [client and scope options](INSTALL_SCOPES.md) are shared with the installer.
Use the same options for both commands. With no destination options, both retain
the historical `$CODEX_HOME/skills` or `~/.codex/skills` path; neither searches for
another installed copy. Text output names the selected target, and JSON includes
its absolute `destination`. Redact that path before sharing a report publicly.

| Status | Meaning and next action |
|---|---|
| `current` | Checked bytes and completion contract match this checkout. No replacement needed. |
| `missing` | No target exists. Run the installer when ready. |
| `different_payload` | The managed record differs from this checkout. Review differences and back up before upgrading. This alone does not establish which version is newer. |
| `modified` | Checked managed files changed or disappeared since the recorded installation. Preserve local edits before replacing. |
| `unmanaged` | No completion marker exists. Matching files do not establish ownership or a safe upgrade. Review its origin and make a backup. |
| `unsafe` | A marker, path, file type, budget or concurrent change prevented inspection. Inspect manually; no repair was attempted. |

Exit codes: `0` for current, `1` for a status needing review, `2` for an unsafe
or incomplete inspection (also used for invalid CLI arguments). JSON includes
all changed source-declared paths; text shows up to 20 per category. File
contents and raw marker errors are never printed. `newline_only` compares UTF-8
CRLF/CR/LF spelling; it does not silently accept byte drift in a managed record.

The doctor reads only paths declared by the current checkout plus completion
metadata. Extra notes, caches, secrets and old-only payload files are not
enumerated or read. `recorded_paths_not_checked` counts old-only paths; their
integrity is unknown. The command does not certify an entire directory, host
discovery or model behavior. Avoid running it during an installation or edit.
Per-file stable reads and marker/root checks detect changes, but this is not an
atomic snapshot of a concurrently changing directory. Normal OS access-time
updates may occur when files are read; the command does not write file bytes,
change permissions or create directories or lock files.

Version labels come from `SKILL.md` frontmatter and are descriptive, not proof
of integrity. Existing completion markers do not record a commit, so
`installed_commit` is unknown rather than guessed from the current checkout.
The comparison is bound to the source's installed-payload contract hash.

When replacement is intentional, first copy the entire existing directory to a
separate backup location and review it. Then follow the installer's documented
replacement flow. The doctor does not construct or execute a force command.

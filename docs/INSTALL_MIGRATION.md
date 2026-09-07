# Change install location without losing the old copy

Use this when Seedance is installed in an older directory, appears twice, or loads a different revision than the one you just installed. Work from a reviewed source checkout. The commands below use `--dest`, so they also work before the explicit client/scope options were added.

## Choose the copy you want to use

Record the old and new skills **parent** directories. The installer and doctor append `seedance-20/`; do not supply that final directory as `--dest`.

| Intended use | Codex parent | Claude Code parent |
|---|---|---|
| Available across your projects | `~/.agents/skills` | `~/.claude/skills` |
| Available in one project | `/path/to/project/.agents/skills` | `/path/to/project/.claude/skills` |

The source-backed paths above were reviewed on 2026-09-07: [Codex scopes and duplicate names](https://learn.chatgpt.com/docs/build-skills), [Claude Code locations and precedence](https://code.claude.com/docs/en/skills). Confirm the locations for the client version you use. Project scope means the existing project where you will work, outside this source checkout.

Older no-option installations used `$CODEX_HOME/skills`, or `~/.codex/skills` when `CODEX_HOME` was unset. Use the actual historical destination if that environment setting has changed. An ordinary install does not relocate any existing copy.

## Inspect, preserve, install, verify

1. **Inspect the known old parent.** Run `python scripts/install_doctor.py --dest /path/to/old/skills --json` from the reviewed source checkout. Keep the report and the source commit you compared against. `different_payload` does not establish which revision is newer. `modified` or `unmanaged` calls for reviewing local edits and origin; `unsafe` means stop and inspect the path manually.
2. **Preserve the old directory.** Back up the entire `seedance-20/` directory, including hidden files and local additions, to a clearly named location outside every client skills directory. Verify the backup before any replacement. The doctor does not inspect extra files, and the installer's temporary transaction backup is not a retained personal backup.
3. **Inspect the intended new parent.** Run the doctor against it too. If it already contains a copy, reconcile that copy before replacing anything. If old and new parents resolve to the same directory, this is an in-place update, not a migration; follow the [replacement guidance](INSTALL_DOCTOR.md).
4. **Install into an empty target.** Use the command below without `--force`. If it refuses an existing target, investigate that target instead of adding force automatically. Do not copy the whole repository or overlay two payload revisions.
5. **Check the new payload and its discovery.** Run the doctor from the same source checkout against the new parent. Refresh the client and verify the exact source path for `seedance-20`. A correct name, version label or `current` doctor result alone does not establish that the client chose the new copy.

For example, these commands select the current Codex user parent explicitly:

```sh
python scripts/install_doctor.py --dest ~/.agents/skills --json
python scripts/install_codex_skill.py --dest ~/.agents/skills
python scripts/install_doctor.py --dest ~/.agents/skills --json
```

The first command returns exit code `1` when the install is missing; inspect the status rather than treating every nonzero exit as permission to install. In PowerShell, use `"$HOME/.agents/skills"` if your shell does not expand `~`. Quote paths containing spaces.

## Resolve duplicate discovery deliberately

**Codex:** its documentation says same-name skills are not merged and can both appear in selectors. Review their exact paths. To retire a known old entry without deleting it, Codex documents a path-specific entry in `~/.codex/config.toml`:

```toml
[[skills.config]]
path = "/absolute/path/to/old/seedance-20/SKILL.md"
enabled = false
```

Use the actual old path, preferably forward slashes in TOML on Windows. If your profile uses a custom configuration location, identify that active file first; do not assume the default file controls the session. Back up the client configuration and update an existing entry for that path rather than appending a conflicting duplicate. Preserve other settings. Restart Codex and confirm that the intended new path is enabled and the old path is disabled. This is a manual client configuration choice; neither repository script makes it for you. The guide has not tested retirement in your personal configuration.

**Claude Code:** its documentation gives enterprise precedence over personal, and personal over project. A new project copy can therefore be shadowed by an older personal copy. Verify the source before blaming the prompt or reinstalling. If you own the old copy and choose to retire it, preserve a verified backup outside all scanned skill directories, then move only that identified directory out of discovery. Do not change organization-managed files; have their owner reconcile the duplicate. Refresh the client and verify the selected source again.

Merely renaming a backup folder inside a scanned skills directory is not a reliable way to retire it. Keep backups outside those directories. Do not assume that changing a skill's frontmatter name safely migrates its references or invocation metadata.

## Keep a way back

Retain the old backup, its source revision when known, and the new doctor's report until both the short-prompt and continuation checks in the [host smoke protocol](HOST_COMPATIBILITY.md) have passed. Those text checks may use host model quota; they do not authorize video generation. Record discovery or behavior as untested if you cannot observe it.

If the new copy fails, preserve its diagnostics, disable or move only that new copy out of discovery, restore the old copy to its recorded location if it was moved, and undo only the path-specific disablement you added. Refresh the client and verify the restored source. Do not overlay the old files onto the new directory or restore an entire stale client configuration over unrelated changes.

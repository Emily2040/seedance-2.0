# Choose where the skill is available

Run these commands from a reviewed source checkout. The installer and read-only doctor accept the same destination options. Each parent below receives one `seedance-20/` directory.

| Choice | Options | Skills parent |
|---|---|---|
| Codex, across projects | `--client codex --scope user` | `~/.agents/skills` |
| Codex, one project | `--client codex --scope project --project-root /path/to/project` | `/path/to/project/.agents/skills` |
| Claude Code, across projects | `--client claude-code --scope user` | `~/.claude/skills` |
| Claude Code, one project | `--client claude-code --scope project --project-root /path/to/project` | `/path/to/project/.claude/skills` |
| Custom client directory | `--dest /path/to/client/skills` | The parent you supply |
| Existing no-option workflow | No destination options | `$CODEX_HOME/skills`, otherwise `~/.codex/skills` |

The client paths follow the [Codex documentation](https://learn.chatgpt.com/docs/build-skills) and [Claude Code documentation](https://code.claude.com/docs/en/skills), reviewed 2026-09-07. Directory guidance is separate from [observed host behavior](HOST_COMPATIBILITY.md).

For a new Codex user installation:

```sh
python scripts/install_codex_skill.py --client codex --scope user
python scripts/install_doctor.py --client codex --scope user --json
```

For a project, create or select its directory first, outside the source checkout. Quote paths containing spaces. For example, in PowerShell:

```powershell
python scripts/install_codex_skill.py --client claude-code --scope project --project-root "C:\Projects\My Film"
python scripts/install_doctor.py --client claude-code --scope project --project-root "C:\Projects\My Film" --json
```

The project root must already exist. The command neither searches Git ancestors nor assumes the checkout containing the installer is your target project. Existing path, link, payload and transaction guards still apply.

`--client` requires an explicit `--scope`. Do not combine it with `--dest`; custom destinations also reject `--scope` and `--project-root`. This prevents a typo from silently choosing between conflicting targets.

An explicit Codex user scope uses `~/.agents/skills` even when `CODEX_HOME` is set. The no-option form retains the old environment-sensitive path for compatibility. Neither form searches for, moves, deletes or disables another installed copy. A successful install can therefore coexist with an older copy. Review the exact source your client discovers; seeing the name alone does not establish which revision it loads.

Run the doctor with the same options before replacing a selected install. Its `destination` field identifies the inspected directory; remove private paths before sharing the report. A `current` result compares the checked bytes with the source checkout and does not prove host discovery. Use `--force` only for an intentional replacement after preserving local edits and a separate backup.

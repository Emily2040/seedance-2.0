# Transfer the prepared skill, not the checkout

The repository contains authoring and evaluation tools as well as the skill. The installer copies an explicit allowlist, checks its contents, writes a completion record, and removes README asset links whose images are not installed. Copying or zipping the entire checkout bypasses that packaging step.

For a client on this computer, prefer installing directly into its documented skills parent directory:

```sh
python /path/to/source/scripts/install_codex_skill.py --dest /path/to/client/skills
```

For an import dialog or transfer to another machine:

1. From a reviewed checkout, run the installer with `--dest /path/to/new-staging/skills`. Use a new directory outside the source checkout.
2. Transfer only the resulting `seedance-20/` directory, preserving relative paths, hidden files and the completion record. Follow the destination client's documented import format; a ZIP format is not universal.
3. On the destination, where a matching source checkout and Python are available, run `python /path/to/source/scripts/install_doctor.py --dest /path/to/client/skills --json`. A `current` result verifies the checked payload against that source. A client may strip metadata or transform content; investigate a different result rather than manufacturing a completion record.
4. Restart or refresh the client and verify discovery separately. The doctor does not prove skill loading or prompt behavior.

Before replacing an existing installation, use the doctor, preserve local edits and keep a separate backup. A manual copy does not provide the installer's transaction recovery or rollback, so use the installer for replacement whenever possible.

Changing locations or seeing duplicate entries? Follow the [installation migration guide](INSTALL_MIGRATION.md) to inspect both destinations, verify the new source in the client, and retain a way back before retiring the old copy.

Direct GitHub installation remains a client-specific packaging route. Review the files it imports; do not assume it applies `validation/install-payload.txt`. The filtered payload excludes the network evaluator and optional provider runners. Keeping the full source checkout separately is useful for maintenance, but it is not the offline installed payload described by [SECURITY.md](../SECURITY.md).

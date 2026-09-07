# Seedance 2.0 Skill OS — Quickstart

> Version 6.7.0 · A 5-minute path from install to your first directed prompt.
> Full documentation: [README](../README.md).

## What this is

Seedance 2.0 Skill OS is an agent skill that directs Seedance 2.0 like a filmmaker instead of stacking adjectives. Its one rule: **direct the model, don't micro-manage the frame.** You describe what a scene is *doing*; the skill compiles that intent into a production-ready prompt.

## 1. Install one root skill

Download and unzip the repository, or run:

```sh
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
```

From that folder, choose **one** destination. Each receives one `seedance-20/` folder; do not install the sub-skills separately.

```sh
# Codex: available to your user
python scripts/install_codex_skill.py --client codex --scope user

# Claude Code: available to your user
python scripts/install_codex_skill.py --client claude-code --scope user

# Codex: one existing project outside this source checkout
python scripts/install_codex_skill.py --client codex --scope project --project-root "/path/to/project"
```

Replace `/path/to/project` with an existing project outside this source checkout; keep paths with spaces in quotes. These commands run from the source folder.

For another client or a customized profile, use `--dest /path/to/client/skills`. Do not combine it with client/scope options. With no destination options, the historical `$CODEX_HOME/skills` or `~/.codex/skills` path remains in use; an explicit user scope does not move or disable older copies.

Check **the same destination** with the doctor. After the first option, for example:

```sh
python scripts/install_doctor.py --client codex --scope user --json
```

`current` means the checked payload matches this source checkout. Restart or refresh the client and verify the discovered skill path separately; the doctor does not prove which copy your client loads. Before intentional replacement with `--force`, preserve local edits and a separate backup. [Destination options](https://github.com/Emily2040/seedance-2.0/blob/main/docs/INSTALL_SCOPES.md) · [Migration and duplicates](https://github.com/Emily2040/seedance-2.0/blob/main/docs/INSTALL_MIGRATION.md).

For manual transfer, run the installer with `--dest /path/to/new-staging/skills` in a new location outside this checkout. Copy **only the resulting `seedance-20/` directory**, preserving hidden files and the completion record. A direct GitHub import may package different files; inspect what the client imports. Do not assume it applies this installer’s allowlist. [Manual transfer instructions](https://github.com/Emily2040/seedance-2.0/blob/main/docs/MANUAL_INSTALL.md).

<details>
<summary>Replacement and recovery details</summary>

The transaction keeps a temporary backup during promotion. If promotion fails and the required records remain valid, it restores the previous complete copy. After successful promotion, that backup is quarantined and deleted. It is not your retained personal backup. Automatic recovery is limited to authenticated transaction states; unknown or invalid files and records are preserved for review. See the [full recovery boundary](../README.md#install).

</details>

## 2. Pick the skill for your situation

| You have… | Load first |
|---|---|
| a vague idea | `seedance-interview` |
| a clear scene | `seedance-prompt` |
| a multi-clip story | `seedance-sequence` |
| an accepted clip to continue | `seedance-continuation` |
| a bad or blocked result | `seedance-troubleshoot` |
| a character, brand, celebrity, or real person | `seedance-copyright` |

## 3. Direct before you write — four questions

1. **What is the scene doing?** A turn, a reveal, a feeling, a demonstration?
2. **How does the camera say it?** Wide for isolation, close for a face, a push-in for a realization.
3. **What does light do?** Time of day, hard vs soft, warm vs cool — in service of the intent.
4. **What does sound do?** Near-silence, one ambient detail, or a line of dialogue.

## 4. One example

**Decorated (weak):**

```
epic cinematic shot of a woman reading a letter, emotional, beautiful lighting, 4K
```

**Directed (strong):**

```
A woman in a wool cardigan sits at a kitchen table and reads a single sheet of paper. Her eyes track one line twice, then her hands lower the page to the table and go still. Camera holds a medium close-up at eye level and pushes in slowly, settling when her hands stop. Overcast window light from frame left keeps her face plain. Sound: room tone, one chair scrape, then near-silence.
```

Read the order, not just the words. The subject and what she is doing come **first**, and the camera, light, and sound follow — because the opening of a prompt is where the model locks in who the shot is about. Leading with `Medium close-up, eye-level` spends that opening on framing metadata and makes the model infer the subject afterwards. Same craft, weaker hierarchy.

Length matters the same way: this is 71 words. Aim for roughly **40–110 words** for a single clip. Much shorter and the model fills the gaps for you; much longer and the later clauses stop landing.

## 5. Two rules that save takes

- **Keep reference tags exactly as written** — `@Image1`, `@Video1`, `@Audio1`, `@图片1`, `@视频1`. Never translate or reformat them.
- **Don't ask for the whole story in one generation.** Generate Clip 01, observe how it *actually* ended, then write Clip 02 from that real ending (`seedance-continuation`).

## 6. Safety

- **Content safety:** if your idea uses a protected character, celebrity, brand, logo, song, or a real person's face or voice, don't hide it in another language — rewrite it into an original, licensed, or post-production equivalent with `seedance-copyright`.
- **Agent safety:** the **installed payload** makes no network calls and ships no telemetry; its installed scripts run locally without contacting external services. A repository checkout also contains the development-only `scripts/eval_run.py`, which can contact a model provider and is excluded by the installer. Never paste API keys, account cookies, or private footage into an agent you don't trust. See [SECURITY.md](../SECURITY.md).

## 7. Go deeper

- `references/directing-engine.md` — read the scene, choose one intention (33 worked genre examples).
- `references/capability-map.md` — design into model strengths and around known limits.
- `references/api-workflow.md` — API, providers, pricing, model IDs (source-dated).
- `references/examples-by-mode.md` — T2V, I2V, V2V, R2V, FLF2V, edit, and extend examples.

---

Other languages: [中文](QUICKSTART.zh.md) · [日本語](QUICKSTART.ja.md) · [한국어](QUICKSTART.ko.md) · [Español](QUICKSTART.es.md) · [Русский](QUICKSTART.ru.md)

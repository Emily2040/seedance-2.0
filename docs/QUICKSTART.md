# Seedance 2.0 Skill OS — Quickstart

> Version 6.7.0 · A 5-minute path from install to your first directed prompt.
> Full documentation: [README](../README.md).

## What this is

Seedance 2.0 Skill OS is an agent skill that directs Seedance 2.0 like a filmmaker instead of stacking adjectives. Its one rule: **direct the model, don't micro-manage the frame.** You describe what a scene is *doing*; the skill compiles that intent into a production-ready prompt.

## 1. Install (about 5 minutes)

Install this repository as **one** root skill named `seedance-20`; its sub-skills and references load by relative path.

**First, get the files.** Every command below runs from inside a local copy:

```bash
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
```

No `git`? Use **Code → Download ZIP** on the repository page, unzip, and `cd` into the folder.

**Then install it.** One command works for any client that reads a skills directory — `--dest` picks which one:

```bash
# Codex (default: ~/.codex/skills)
python scripts/install_codex_skill.py

# Claude Code (personal install, every project)
python scripts/install_codex_skill.py --dest ~/.claude/skills

# Install into another project — run from that project
python /path/to/seedance-2.0/scripts/install_codex_skill.py --dest .claude/skills
```

It prints where the skill landed. Restart your client, then call `seedance-20`. Add `--force` only when replacing an existing install — it deletes the old copy first. A destination inside this repository is refused, since copying the tree into itself would recurse until the path length fails.

**Install from GitHub (if your client supports repo-URL install):**

```text
https://github.com/Emily2040/seedance-2.0
```

**Manual copy (any other client):** copy this folder into your client's skills directory, keeping the name `seedance-20`. Common targets — verify in your own client, these are not a support guarantee — are in the [Install table of the README](../README.md#install): e.g. Claude Code `.claude/skills/`, Cursor `.cursor/skills/`, GitHub Copilot `.github/skills/`, Windsurf `.windsurf/skills/`.

> Security first: only install into agent clients you trust. Read [SECURITY.md](../SECURITY.md) before using this skill inside a third-party or unfamiliar agent.

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
- **Agent safety:** this package makes **no network calls and ships no telemetry**; its scripts are deterministic and offline. Never paste API keys, account cookies, or private footage into an agent you don't trust. See [SECURITY.md](../SECURITY.md).

## 7. Go deeper

- `references/directing-engine.md` — read the scene, choose one intention (33 worked genre examples).
- `references/capability-map.md` — design into model strengths and around known limits.
- `references/api-workflow.md` — API, providers, pricing, model IDs (source-dated).
- `references/examples-by-mode.md` — T2V, I2V, V2V, R2V, FLF2V, edit, and extend examples.

---

Other languages: [中文](QUICKSTART.zh.md) · [日本語](QUICKSTART.ja.md) · [한국어](QUICKSTART.ko.md) · [Español](QUICKSTART.es.md) · [Русский](QUICKSTART.ru.md)

# Seedance 2.0 Skill OS — Quickstart

> Version 6.7.0 · From installation to a first directed prompt.
> Full documentation: [README](../README.md).

## What this is

Seedance 2.0 Skill OS helps turn a scene idea into a prompt with visible actions, camera direction and sound. It prepares instructions; a separate video service renders them.

**Review status:** these are unrendered teaching examples, not measured quality or credit-saving results. Language and rendered review remain pending in the [coverage record](LANGUAGE_COVERAGE.md).

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

It prints where the skill landed. Restart your client, then call `seedance-20`.
Installs are staged and validated, and concurrent installers sharing one
destination are serialized. Add `--force` only when replacing a complete
existing install. Automatic retry applies only when every authority record
required by the phase reached exists and validates: an exact empty stage before
provenance; after complete provenance, exact final payload files plus the one
transaction-derived in-progress copy sibling; exact torn prefixes of expected
stage markers; and externally journaled deletion workspaces can be recovered.
Payload bytes are synced and digest-checked under that sibling name before an
atomic rename, so an expected final stage pathname is absent or complete, never
partially written. The copy-sibling basename is capped at 34 ASCII bytes and
shortens further on POSIX when the stage reports a smaller component limit; a
shortened transaction/path digest is accepted only when it is unique within the
authenticated payload namespace. This is a bound on copy siblings, not a claim
that the installer's longer stage and authority names fit unusually small
component limits. The exact empty
terminal workspace left after journal removal is also recoverable. A truncated
expected final file, an unbound temp-like file, malformed or swapped records,
unexpected bytes, an unmarked
quarantine, and a nonempty unjournaled deletion workspace are preserved fail
closed. Windows handles exclude writable/deletion sharing through the consuming
action. On POSIX, a mode-`0700` workspace excludes other OS accounts, but
advisory `flock` and owner permissions cannot exclude a hostile same-account
process from existing or new writable opens or namespace mutation. See the
[README install notes](../README.md#install)
for the full recovery boundary. The previous complete copy is retained for
rollback until promotion succeeds.
On POSIX, authority files and transaction namespace changes are directory-
`fsync`ed. Each payload file is `fsync`ed before its atomic rename and its stage
directory is `fsync`ed afterward. The supplied skills-directory ancestry is
assumed durable rather than recursively flushed.
A destination inside this repository is refused, since copying the tree into
itself would recurse until the path length fails.

**Install from GitHub (if your client supports repo-URL install):**

```text
https://github.com/Emily2040/seedance-2.0
```

**Manual copy (any other client):** copy this folder into your client's skills directory, keeping the name `seedance-20`. Common targets — verify in your own client, these are not a support guarantee — are in the [Install table of the README](../README.md#install): e.g. Claude Code `.claude/skills/`, Cursor `.cursor/skills/`, GitHub Copilot `.github/skills/`, Windsurf `.windsurf/skills/`.

> Security first: only install into agent clients you trust. Read [SECURITY.md](../SECURITY.md) before using this skill inside a third-party or unfamiliar agent.

## 2. Pick the skill for your situation

Call `seedance-20` and describe what you already know. For a vague single clip, expect a draft or one blocking question. A complete brief can go straight to a prompt; you do not need to repeat your answers or learn route names.

| You have… | Load first |
|---|---|
| a vague idea for one clip | `seedance-interview-short` |
| a clear scene | `seedance-prompt` |
| a multi-clip story | `seedance-sequence` |
| an accepted clip to continue | `seedance-continuation` |
| a bad or blocked result | `seedance-troubleshoot` |
| a character, brand, celebrity, or real person | `seedance-copyright` |

If you want alternatives, ask for up to three directions with different staging, attention or performance, then choose one or say “choose for me.” A menu is optional. Keep the camera, sound, duration and rejected directions you have already decided.

## 3. Direct before you write — four questions

1. **What is the scene doing?** A turn, a reveal, a feeling, a demonstration?
2. **How does the camera say it?** Wide for isolation, close for a face, a push-in for a realization.
3. **What does light do?** Time of day, hard vs soft, warm vs cool — in service of the intent.
4. **What does sound do?** Near-silence, one ambient detail, or a line of dialogue.

## 4. One example

**Vague brief:**

```
epic cinematic shot of a woman reading a letter, emotional, beautiful lighting, 4K
```

**Directed draft — unrendered:**

```
A woman in a wool cardigan sits at a kitchen table and reads a single sheet of paper. Her eyes track one line twice, then her hands lower the page to the table and go still. Camera holds a medium close-up at eye level and pushes in slowly, settling when her hands stop. Overcast window light from frame left keeps her face plain. Sound: room tone, one chair scrape, then near-silence.
```

Subject and action come first here so a reader can find the shot’s purpose quickly. That is an editorial choice, not a verified mechanism for how Seedance interprets opening words. Camera-first wording can be appropriate when framing is the main decision.

Use a compact brief that preserves the necessary action, ending, references and exact dialogue. The skill’s roughly **40–110 English words** is a drafting heuristic, not a tested model limit or guarantee that later clauses will appear. Do not apply that English word range as a character or syllable limit in another language.

For this unrendered example, check whether the gaze repeats the line, the hands lower the letter and stop, and the camera settles with them. These are intended review criteria, not observed results.

If the camera keeps moving, a revision can change only the camera instruction to a fixed medium close-up, **if you choose to give up the push-in**. Keep the other decisions and remaining budget. If no video was supplied, describe the failure as user-reported. With no attempts left, stop or assess whether an acceptable edit is possible; do not call a failed shot approved. Writing a revision does not authorize generation, an upload, or a change of provider, tier or duration.

## 5. References and continuation

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

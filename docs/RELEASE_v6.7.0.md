# Seedance 2.0 Skill OS — v6.7.0

A modular agent-skill operating system for directing ByteDance **Seedance 2.0** video. It turns vague ideas into production-ready prompts, **directs each scene like a filmmaker**, keeps platform facts source-dated, rewrites unsafe IP, and plans long-form stories across many clips — with native-reader paths for English, 中文, 日本語, and 한국어.

## What's new in v6.7.0 — the outside world moved

v6.6.0 closed the sequence loop. v6.7.0 is about everything that drifted while the loop was being closed: a newer model line shipped, the front page's type was resolving differently on every reader's machine, and the path a first-time user walks was broken in four places.

### A newer model line exists, and the skill now knows it

Seedance 2.5 was announced 2026-06-23 and launched on consumer surfaces on **2026-07-31**. The previous verification stamp was 2026-06-20 — three days before the announcement — so every platform statement in the package was presenting a superseded picture as current, with no signal that a newer line existed at all.

The fix is a boundary, not a rewrite:

- **`api-status` opens with the 2.5 section.** Announcement and launch dates, reported capabilities (≈30-second native single-shot, up to 50 references, 4K, region-level editing), reported BytePlus API access from mid-July, and the reported 4K upgrade to the 2.0 line.
- **Everything about 2.5 is labeled `tech-press`, not `confirmed`.** The primary ByteDance and Volcengine pages were unreachable in this pass, and `source-registry` records that as a known gap in its own hierarchy rather than quietly upgrading press coverage to primary evidence.
- **The root skill's source gate now establishes the model line, not just the surface.** A user can be on 2.5 without saying so.
- **`model-name-map` gains 2.5 and 2.0-4K rows** and a standing rule: never normalize "2.5" to "2.0". That normalization would apply 2.0 durations, reference ceilings, and resolutions to a model reported to differ on all three — the highest-cost naming error the file exists to prevent.

The rule underneath all of it: **craft transfers across model lines; platform numbers never do.** Direction, shot contracts, reference roles, continuity, and anti-slop remain correct on any line. Durations, reference counts, resolutions, model IDs, and mode availability are 2.0 values and stay 2.0 values.

One consequence worth flagging for sequence work: if the reported 30-second single-shot ceiling holds, the shot budgeting in `multishot-grammar` and `seedance-sequence` — which assumes a ~15s generation — becomes a floor rather than a ceiling on 2.5. Re-derive it from the active surface.

### The masthead now renders the same for everyone

The design system specifies a "high-contrast editorial serif". The stack it used — `Didot, 'Bodoni MT', 'Hoefler Text', Baskerville, 'Palatino Linotype', Georgia, serif` — delivers Didot only on macOS. Windows fell through to Bodoni MT or Palatino Linotype. Linux, including the machine this repository is built and validated on, has **none of the six** and fell all the way to a default system serif.

This is precisely the failure the script wordmark was retired for in v6.6.0 ("a design that only resolves on the author's machine is not a design"). The serif stack had the same disease and outlasted the fix.

The wordmark and tagline are now **glyph outlines** — real vector geometry, shaped with HarfBuzz kerning from Bodoni Moda (SIL OFL; attribution, version, and instance axes recorded in `assets/masthead-outlines.json`). Optical size tracks rendered size, so the hairlines are drawn for the size they appear at. No font needs to be installed by anyone, and every reader sees identical type. Specification values moved to the monospace stack, so the only serif on the canvas is outlined and nothing can silently fall back.

### The first ten minutes work

Five defects on the path a first-time user actually walks, all found by checking the repository rather than the feedback:

- **There was no `git clone` anywhere in the documentation.** Every install path began at step two, inside a copy of the repository nothing told the reader to obtain.
- **The installer looked Codex-only.** It has always accepted `--dest`; Claude Code and every other listed client had a one-command install and were being sent to copy the folder by hand. It also told every user to "Restart Codex" regardless of destination.
- **A validator reported gitignored files as committed.** Running the tests before the validators — the order the README lists — produced a wall of "must not be committed" errors naming files that were gitignored and never committed. CI never saw it because the workflow sets `PYTHONDONTWRITEBYTECODE`.
- **An in-tree `--dest` copied the repository into itself** until the path length failed — 757 directories deep.
- **The beginner example taught against the doctrine.** The "Directed (strong)" prompt was 29 words, below the root skill's own 40–110 band, and opened on `Medium close-up, eye-level` — the exact inversion `seedance-prompt` warns against when it says to put the subject and primary action first.

### Prompt architecture is now a CI gate

`scripts/prompt_architecture_stress.py` scores a 102-prompt corpus over 34 briefs and every mode, written three ways: the Director Formula, the shape the old beginner example taught, and untrained/listicle style. The doctrine arm scores **3.92/4** against `eval-rubric`; the other two fail. It runs with `--strict` in CI, so a change that degrades the doctrine fails the build instead of arriving later as "the prompts feel average".

### CJK reaches parity

Japanese gained **Register (文体)** — 敬語 / です・ます体 / 普通体 with script-verified mora costs, and the first-person pronoun as a register axis — closing the asymmetry that left Chinese with Script Variant and Korean with Speech Level while Japanese had neither. All three languages gained dialogue-format lines, aesthetic-register sections mined from the legacy archive, and wrapper-level discoverability for features that previously existed only in reference files.

`references/sync-budget-protocol.md` makes the two remaining "not separately measured" cells fillable: fixed shot conditions, script-verified sentence ladders in morae and syllables, a Mandarin control ladder, a three-defect scoring rule, and write-back rules that keep the `[field]` label and per-surface scope.

## Upgrading

Nothing to migrate. Re-run the installer for your client:

```bash
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
python scripts/install_codex_skill.py --dest ~/.claude/skills --force
```

## Verification

17 validators and 52 unit tests, all green, including the masthead design-rule suite, the prompt-architecture gate, and `source_registry_check --strict --enforce-freshness`.

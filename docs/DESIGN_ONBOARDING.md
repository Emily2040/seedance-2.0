# Design: onboarding for people who do not live in a terminal

Status: design, 2026-09-26. Answers the report that people download the
skill, do not know how to use it, find the instructions written for
developers, and have no tasteful set of options to pick from.

## What the readers found

Eight repository readers checked what a non-technical person meets. The
verdict was consistent: the front page's Start Here block is good, and then
the path collapses.

- Install requires git or a ZIP, a terminal, Python and a choice among
  `--client`, `--scope`, `--project-root` and `--dest`. The old front page then
  opened into about ninety lines of transaction and file-system prose.
- Every skill and reference file is maintainer-grade: T2V, I2V, V2V, R2V,
  FLF2V, "surface", "operation", "binding token", "continuity locks",
  "fidelity budget", `project_id`, `prompt_carriers`, a nine-tier authority
  order. There is no glossary anywhere.
- The interview skills are written for beginners and would work: a
  blank-slate user is supposed to get a menu of up to three starting points
  or one drafted concept, at most five plain questions each with a default,
  and no parameter questions. Nothing surfaces that behaviour at first run,
  so the person never learns the agent will meet them halfway.
- Nothing exists outside the terminal: no start page, no template gallery,
  no sentence to paste.

The design therefore has three parts: what the agent says first, a designed
surface outside the terminal, and an install story for people who will never
run git.

## Part 1: the first sixty seconds inside the agent

Trigger: the first time `seedance-20` is invoked in a session with a message
that contains no scene yet ("hi", "what can you do", "help", or the bare
skill name), or whenever the user says they are new.

The agent answers with one paragraph and three doors, in the user's language.
English wording:

> I write directed prompts for Seedance 2.0 videos. Tell me a scene in plain
> words and I'll turn it into a prompt you can paste into 即梦, Dreamina or
> your API tool. I don't generate the video and I don't spend your credits.
>
> Where would you like to start?
>
> **1. I have an idea.** Describe it in one or two sentences. I'll write one
> prompt and tell you why it's built that way.
> **2. Show me three directions.** Give me a subject and a feeling; I'll offer
> three treatments and you pick.
> **3. I have a story.** Tell me how it ends. I'll plan it as connected
> clips and write the first one.
>
> Or paste a prompt you already have and I'll make it stronger.

Rules for this screen:

- Three doors, never more. Each door names what the person gives and what
  they get back. No mode codes, no tag syntax, no surface names.
- The doors map to routes the repository already has: door 1 is the fast lane
  to `seedance-interview-short` then `seedance-prompt-short`; door 2 is the
  interview's Starting Points menu; door 3 is `seedance-sequence`.
- The first draft arrives after at most one question. The interview skills
  already say this; the first screen promises it out loud.
- Jargon appears only after the first draft, and only as a translation: "I
  kept the camera still, what a film crew calls a locked shot." The agent
  introduces one term per turn at most.
- The agent never asks the person to choose a surface, mode or aspect ratio
  before a draft exists. It writes the draft, then says which settings belong
  in the tool's own panel.

Register adaptation: the root skill already says to speak plainly to a
beginner and in director language to a professional. Add the rule that the
agent switches only when the user uses production vocabulary first, and
switches back if the user asks what a term means.

## Part 2: a start page outside the terminal

A single static page under GitHub Pages, `docs/start/index.html`, built with
the repository's design system (warm paper and ink, outlined wordmark, one
amber accent, hairlines, no badges, no camera costume). It does three things
and nothing else.

**A. Pick your tool, get the two lines to paste.** Six tiles: Claude Code,
Codex, Cursor, Claude app, ChatGPT, "something else". Each tile shows the
exact install command or import steps for that tool and a copy button. The
page never asks the person to understand scopes; it chooses the personal
scope and says "this installs it for you, on this computer".

**B. Pick a template, get the sentence to say.** A gallery of twelve cards,
each a real brief the repository already teaches, one image per card (the
existing teaching art where it exists, the editorial typographic card where
it does not), and a copy button that yields the sentence to paste into the
agent, for example:

> Use seedance-20. A person finishes a paper fan at a workbench. Keep it
> quiet, one static shot, no music. Give me the prompt only.

Cards are grouped the way people arrive: one clip; a product; a person
talking; a continuation; a short story; a Chinese, Japanese or Korean prompt.
Every card states "unrendered teaching example" in small type, because the
repository's honesty rules do not bend for a landing page.

**C. Read the six pages.** The language switcher, identical to the READMEs.

The page is generated from a small JSON of cards by a script in `scripts/`,
so the copy stays in one place and the design audit can check the SVGs and
the byte budget. No analytics, no fonts fetched from a third party, no
JavaScript beyond the copy buttons.

## Part 3: installing without git

Three paths, in order of how many people they serve:

1. **Download ZIP, then one command.** Already works. The README's first
   install block should show the ZIP route first for the non-technical
   reader, with the git route beneath it, not the other way round.
2. **Client-native import.** For clients that import a skill folder or a ZIP
   directly (the Claude app's skill upload, Codex plugin import), the start
   page's tile shows the click path and a screenshot-free numbered list. The
   font rename in pull request #209 removes the one filename that could make
   a ZIP import fail.
3. **A packaged release asset.** Each release attaches `seedance-20.zip`
   containing exactly the installer's filtered payload, built by
   `scripts/install_codex_skill.py --dest` in CI and hash-recorded in the
   release notes. People who will never run Python get the same bytes the
   installer would have produced.

The installer's own printed messages are already good; keep them. Add a
final line: "Now open your agent and type: Use seedance-20. Then describe a
scene."

## Part 4: a glossary, once

`docs/GLOSSARY.md`, one line per term, in the six languages as separate
files (`GLOSSARY.zh.md` and so on), linked from every language page and from
the first-run screen's "what a term means" reply. Terms: prompt, clip,
reference, tag, first frame, last frame, continuation, take, locked shot,
push-in, room tone, surface (renamed on the user-facing side to "your video
tool"), credits.

## Files

| File | Change |
|---|---|
| `SKILL.md` | Add the first-run screen as a short section before the Fast Lane: trigger, three doors, one-question promise, one-term-per-turn rule. |
| `skills/seedance-interview-short/SKILL.md` | Reference the three doors; door 2 uses the existing Starting Points menu wording. |
| `references/interview-starters.md` | Add the three-door invitation in all six languages beside the existing invitation table. |
| `docs/start/index.html`, `docs/start/cards.json`, `scripts/build_start_page.py` | The start page and its generator; design audit extended to check it. |
| `README.md` | ZIP route first in the install block; one line pointing to the start page. |
| `docs/GLOSSARY*.md` | Six glossary files. |
| `.github/workflows/release.yml` | Build and attach `seedance-20.zip` with its SHA-256 on tag. |
| `evals/evals.json` | New cases: a bare invocation receives three doors and no parameter questions; a beginner's first draft arrives after at most one question; a professional's request receives no menu. |

## What this does not change

The skill's standards do not soften for beginners: the same anti-slop rule,
the same evidence posture, the same refusal to spend credits. Only the order
in which a person meets those standards changes: first a result, then a
reason, then a term.

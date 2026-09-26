# Design: time structure for one Seedance 2.0 generation

Status: design, 2026-09-26, implemented the same day in the files listed under
Repository changes; the rendered calibration pilot remains open. Answers the customer report that the skill
"always writes four segments for a 15-second limit while the model can
sometimes take five or six". Evidence tiers are stated on every threshold;
sources are in `docs/EVIDENCE_NOTES_2026-09-26.md`.

## The finding that reframes the question

The customer's frame, and most of the internet's, is "how many timestamped
segments". The official Seedance 2.0 material answers a different question.

- Seedance 2.0 keys on **shot order**, written as 镜头1 / 镜头2 / 镜头3 in the
  order events happen, with no forced per-shot duration. Its support for
  precise time ranges such as 0–3 s is unstable, and forcing durations can
  produce abnormal output. (Official: Volcengine 2.0 prompt guide; repeated in
  ByteDance's own troubleshooting file; the 2.5 guide states outright that 2.0
  does not respond to timestamps.)
- No official document gives a shot ceiling. The official worked examples use
  three shots per 15-second clip. (Official.)
- The only official mechanism for choosing how much to put in a clip is
  **density**: too little content for the duration and the model improvises;
  too many shots or too much dialogue for the duration and content and lines
  garble. The official remedy is to split, for example four shots into two
  videos. (Official.)
- Volcengine's own prompt optimizer chooses between **one paragraph** (single
  scene, single continuous action, even with a long line of dialogue) and a
  **numbered-shot storyboard** (several events or locations) by that density,
  not by clip length or asset count. (Official.)
- Two first-party artefacts still use second ranges (the tutorial's showcase
  prompt; the agentkit skill's time-sliced storyboard). The official corpus is
  not perfectly consistent, which is why seconds survive below as an internal
  budget rather than as prompt syntax. (Official inconsistency, recorded.)

So the repository's current behaviour has the right instinct (few beats,
conservative) and the wrong vocabulary (segments and timestamps). The
customer's "the model can take five or six" is true for low-load beats and
false for dialogue, and the six-shot prompts that circulate are 2.5 material
or simple montages.

## What the skill should do instead

### Step 1: classify the clip's shape (official rule)

| Shape | When | What the prompt looks like |
|---|---|---|
| **Continuous** | One scene, one continuous action or state change, one speaker at most, even with a long line | One paragraph in the official order: subject and action, scene, light, one camera move, sound, constraints. No shot labels. |
| **Storyboard** | Several events, a location change, a reveal that needs a cut, or a comparison | Numbered shot blocks in event order. Each block: camera move or cut type first, then subject action and expression, then position or space change, then audio. |

This is the sd2-pe rule, and it removes the first source of confusion: a
storyboard is a content decision, not a duration decision. A 15-second clip of
one woman reading a letter is one paragraph.

### Step 2: score the load (authored heuristic, to be calibrated)

For a storyboard clip, list the beats the user wants, then add load points per
beat:

| Element in a beat | Load | Why |
|---|---|---|
| A camera move within the shot (a locked frame scores 0; a cut to a new locked framing scores 0, because the cut is already the beat boundary) | 0.5 | Official: one move per shot; a move needs time to read |
| A spoken line | 1 per 8 English words or 12 Chinese characters, minimum 1 | Speech needs its own seconds; rate constants are unmeasured on 2.0 and stated as such |
| Each additional person in frame beyond one | 1 | Multi-subject omission and duplication are documented continuation defects; more people, more to hold |
| Physical contact between bodies or between a body and a prop that must land | 1 | Fragile physics; needs a visible cause and endpoint |
| A location or setting change | 2 | A new space is a new composition and light |
| A sound cue that must land on an action | 0.5 | Sync is probabilistic |

A reaction shot or an insert (no new action, no line, no move) counts half a
beat; this was added on 2026-09-26 after the first gallery drafts showed the
full-beat count pushing every scene to two or three master shots. Total load
L. Available seconds D come from the surface parameter (4–15 on 2.0,
official). Seconds per load point S = D ÷ (beats + L). The thresholds:

| S | Reading | Ladder position |
|---|---|---|
| ≥ 3.0 | Comfortable | This beat count is **Safe** |
| 2.0 to 3.0 | Tight; dialogue and contact at risk | **Stretch** |
| < 2.0 | Official density warning territory | **Ambitious**; recommend splitting into two generations instead |

The constants 3.0 and 2.0 are authored heuristics. They are consistent with the
official three-shots-per-15-s examples (one move each: S = 3.3, Safe) and with the
field-reported 2–4 sub-shots per 8–15 s. They are the first thing the 480p
calibration pilot should measure.

### Step 3: present the ladder, then defer (the maintainer's design)

For a storyboard clip whose shot count is open, the skill names up to three
rungs with the trade in one line each, recommends one, and writes one finished
prompt at the recommended or chosen rung; other rungs are written on request,
and "choose for me" means draft the recommendation. When the user has fixed
the count, the skill writes it and states its rung in one line. Menus stay
optional, as the interview skills already require. Wording the agent uses:

> **Safe, 3 shots.** About 4 seconds per load point; the line "It still
> ticks" has room to land and settle.
> **Stretch, 4 shots.** About 2.5 seconds per load point; the reaction after
> the line may get cut short.
> **Ambitious, 5 shots.** Under 2 seconds per load point with a spoken line,
> which is where the official guidance says lines start to garble. If you want
> five beats, two generations of 8 seconds are the better spend.
> Pick one, mix two, or say "choose for me". Six-shot prompts you see online
> are usually simple montages with no dialogue, or Seedance 2.5.

Rules:

- Recommend Safe on a first attempt or when the user's remaining budget is
  one; recommend Stretch when the user says they have room to iterate.
- Never present Ambitious as broken; present the split as the better spend.
- Always state the evidence tier once: "no official shot ceiling exists; the
  official examples use three; the thresholds are this skill's heuristics."

### Step 4: emit the official syntax, not timestamps

- Shot blocks are numbered in event order. In Chinese prompts use 镜头1 /
  镜头2 / 镜头3; in English prompts use Shot 1 / Shot 2 / Shot 3 as the same
  device. (Official for Chinese; the English page's wording should be
  rechecked, see evidence notes.)
- Write the cut inside the block, in words: "cut to a low angle", 镜头切至,
  硬切. A bare label is not a cut command. (Provider-documented structure;
  community field reports.)
- Do not write absolute seconds inside shot blocks on 2.0. Seconds live in the
  internal budget above and in the duration parameter. When a beat needs a
  felt length, write it as behaviour: "hold on the settled fan for one beat",
  not "hold 2 s". (Official guidance; the repository's existing endpoint
  discipline already does this.)
- Set duration as the surface parameter; optionally echo it in prose at the
  start or end as 时长：X秒 (Chinese 秒, not "s") on Chinese-facing surfaces.
  (Official tip.)
- One camera move per shot. A locked camera is written in prose because
  `camera_fixed` is not supported on the 2.0 series. (Official.)
- Constraints stay to the three documented sentences (no subtitles, no logo,
  no watermark) plus the repository's existing preservation clauses.

### Step 5: learn inside the session

After a take review, adjust the user's ladder, not the constants:

- A Stretch take that returned clean moves the user's default to Stretch for
  clips of equal or lower load in this project. Say so: "Your four-shot take
  held; I'll start at four for similar scenes."
- A take that dropped or merged a beat records which beat and why (the retake
  protocol's one-variable rule), and the next draft offers the merge or the
  split rather than the same count again.
- Calibration data, when the rendered pilot runs, changes the constants for
  everyone; session learning changes the recommendation for one user.

## Worked examples

**Calm product shot, 8 s, no dialogue.** One scene, one action: a bottle,
condensation, one light sweep. Shape: continuous. Load irrelevant; one
paragraph. The agent does not offer a ladder, and says why in one clause.

**Dialogue scene, 15 s, two people, two lines of six words each.** Shape:
storyboard (the cut between speakers is a content decision). Beats: line A,
line B, reaction. Load: one person beyond the first (1), two lines (2) = 3;
the cuts are free. S = 15 ÷ (3 + 3) = 2.5, Stretch. Safe is two shots, with
the reaction held in line B's framing (S = 3.0), or two generations; five
beats would be Ambitious (S = 1.9). The agent recommends Safe on a first
attempt, names the model card's multi-speaker lip-sync caveat, and writes
the Safe prompt unless the user has room to iterate.

**Foot chase, 15 s.** Beats: sprint through a market, vault a stall, land and
look back. Load: three moves (1.5), one contact (1) = 2.5. S = 15 ÷ 5.5 = 2.7,
Stretch. Safe is two beats (sprint; vault and land, S = 3.75); four beats is
still Stretch (S = 2.1) and five is Ambitious (S = 1.8). The agent recommends
Stretch if the user has budget, and notes that the official guide itself says
fast action and turning points do better as separate clips edited together.

**Three-beat gag, 12 s.** Setup, escalation, payoff; one person; locked
camera; no lines. Load: contact in the payoff (1). S = 12 ÷ 4 = 3.0. Safe at
three. The agent writes the three-shot storyboard and offers a four-shot
Stretch only if the user asks for a fourth beat.

## Repository changes

Every row below was implemented on 2026-09-26 in the same pull request as this
document, with two additions the table did not foresee: a mirror-read section
in `references/source-registry.md` and a regression test,
`tests/test_time_structure_contract.py`. The rendered pilot is the only open
item.

| File | Change |
|---|---|
| `references/multishot-grammar.md` | Replace the neutral notation paragraphs with the official ruling: shot order, no forced per-shot seconds, precise ranges unstable on 2.0; cite the guide, the 2.5 version-difference statement and the agentkit troubleshooting file with dates and a recheck note. Add the four-part block order and the "write the cut inside the block" rule. Add the shape classifier (continuous versus storyboard) and the load table with its heuristic label. |
| `references/event-density.md` | Add the official density warning verbatim, the split remedy, and the S thresholds. |
| `references/vocab/zh.md`, `ja.md`, `ko.md` | Keep the 【时间轴】 skeleton only as a labelled community convention with the official counter-statement beside it, or replace it with a 镜头1/2/3 skeleton. The zh trigger "约 8 秒以上时使用" goes. |
| `skills/seedance-prompt/SKILL.md` and `skills/seedance-prompt-short/SKILL.md` | Add the ladder to the output contract for storyboard clips: up to three drafts, one trade-off line each, a recommendation, the evidence-tier sentence. |
| `references/prompt-compiler.md` | Emit shot blocks in the official order; forbid absolute seconds inside blocks on 2.0; duration parameter first, prose echo optional. |
| `references/capability-map.md` | Update the multi-shot row: "shots × seconds budget" becomes "load per beat"; note the 2.5 timestamp difference. |
| `references/retake-protocol.md` | Add the session-learning rule for ladder position. |
| `references/api-status.md` | Record the 2.0 versus 2.5 timing difference with its source and date. |
| `evals/evals.json` | New cases: a continuous-shape brief must not receive shot labels; a dialogue brief must receive the ladder with a split recommendation; a Chinese brief must not receive 0-3s ranges; a 2.5 timestamp brief must be redirected to the boundary. |
| `docs/QUICKSTART*.md` | One paragraph in each language: why the skill offers three versions and what "shot order, not seconds" means. |

## What the rendered pilot must measure

Same brief, same references, same surface, 480p: continuous paragraph versus
three, four and five numbered shots, for the four briefs above; two takes
each. Score beat completion, line completion and legibility of the cut. That
is 4 briefs × 4 structures × 2 takes = 32 generations, inside the repository's
existing 48-attempt protocol, with a credit ceiling set by the maintainer
before the first request. The result calibrates the two thresholds and
replaces "authored heuristic" with "measured on N takes" in the files above.

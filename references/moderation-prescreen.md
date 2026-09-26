# Moderation Pre-Screen — run before a prompt is delivered

Every platform that renders Seedance 2.0 runs an automated classifier on the
prompt text, and some run one on the output. The classifiers react to words,
not to intent. A mother holding a kitchen knife in her own hallway, a divorce
agreement on a table, a boxer with a cut brow: benign scenes that a human would
pass and a classifier will refuse. Recorded 2026-09-26 after two of this
repository's own gallery prompts were refused on the 即梦 surface before a
single frame rendered. No platform publishes its trigger list, so everything
below is field-observed or heuristic; a hit is a reason to rewrite, and it is
never a verdict about the platform.

## Boundary

This screen clarifies benign scenes so they are not refused for their wording.
It does not disguise prohibited content, and it is not a bypass list. The rule
from [seedance-filter](../skills/seedance-filter/SKILL.md) holds unchanged: assess
the underlying request; if it is prohibited, refuse plainly and offer a
legitimate alternative only where one exists. Switching language, misspelling
a cue word, or splitting it across sentences is evasion and is never done here.
The craft below keeps the drama and removes the cue; it never keeps the cue and
hides it.

## When it runs

- **Before delivery, on every route.** After the Director's Read and the
  anti-slop pass, before the prompt is handed over. The fast lane runs it too.
- **After a block.** The seedance-filter route runs it again against the actual
  rejection information, rewrites once, and does not probe synonyms.
- **On shipped prompts.** `scripts/moderation_prescreen.py` scans the example
  cards and the front-page gallery data with the same cue lists; with
  `--fail-on-high` it fails on a high-severity hit, and the unit tests run it
  that way, so a refusable prompt cannot be published as an example.

## The cue classes

The word lists live in `data/moderation-cues.json`, per class and per language
(English, Chinese, Japanese, Korean, Russian). The classes, what they react to,
and the craft that keeps the scene:

| Class | Severity | What reacts | Keep the scene by |
|---|---|---|---|
| Weapon | high | a named weapon in a hand, above all in a home or a street | carrying the threat in stillness, sound and light: the scraping key, the held breath, the chain; an object out of frame or unnamed (a hand closes on something on the counter); for costume genres, the sheathed object named once and the strike shown as motion and result, never as the weapon entering a body |
| Injury | high | blood, wounds, a fresh mark on a face, a body called dead | aftermath through wet hair, a torn sleeve, a missing shoe, a limp, a hand held against the ribs; a swelling instead of a cut; never a wound |
| Crime | high | a named crime or violence against a person, and the words that frame one | the same fear through ambiguity: an unexpected key, a wrong knock, a light that should not be on; never name the crime |
| Minor | medium | a child or teenager together with danger, night, injury, a weapon or adult conflict | make the character an adult, or remove the peril, or keep the child as an off-screen presence; never state an age under eighteen inside a threatening scene; in animation, a young swordfighter without an age |
| Institution | medium | named legal, police, medical or custodial settings and documents; signatures on named legal papers; uniforms | unnamed papers in an envelope or folder, a generic office at night, a corridor without signage; the power of the scene stays in who moves first, who looks up, who leaves |
| Substance | medium | smoking, drunkenness, drugs, gambling as action | the empty glass, the ashtray already full, the deck of cards face down; the state shown by its trace |
| Horror | medium | gore and the undead named as such | horror by absence: the chair that was empty, the second set of footsteps, the door that opens on its own, room tone dropping out |
| Identity and symbols | high | real people, brands, logos, flags, currency, insignia | route to [seedance-copyright](../skills/seedance-copyright/SKILL.md); original characters, unbranded objects, no flags or notes in frame |

Three medium hits stacked in one prompt behave like one high hit. Clip 03 of
the first gallery draft is the record: a divorce agreement, a lawyer's office, a
signature on the document and a child's surname, none alarming alone, refused
together.

## The method, in one pass

1. List every noun and verb in the draft that names a weapon, an injury, a
   crime, a minor, an institution, a substance, a horror figure, or a real
   identity. Read the list, not the paragraph; the paragraph always sounds
   innocent to its author.
2. For each item decide one of three things: remove it, move it off frame, or
   replace it with its consequence. The drama lives in the turn, the suppressed
   behaviour and the non-transferable detail of the Director's Read; none of
   those need the cue word.
3. Re-read for stacking. A dark hallway at two in the morning is fine; a dark
   hallway at two in the morning with a teenager and a torn lip is not.
4. Keep the exact dialogue unless a line itself carries a cue, and say so if it
   does.
5. Tell the user what changed and why, in one line. Never call the result
   approved, never promise acceptance, and never present the rewrite as a way
   around a rule.

## Two rewrites from the record

**Refused.** *A woman in a T-shirt stands very still with a kitchen knife held
low along her thigh. A key scrapes in the lock. In the gap, a teenage boy soaked
with rain, a split lip.*

**Passes the screen.** *A woman in a T-shirt stands very still in the dark
hallway, one hand closed around something below the frame line, the chain on
the door. A key scrapes in the lock, misses, tries again. In the gap, her son,
rain running off his hair, one sleeve torn, no bag, his eyes on her hand.*

What survived: the threat, the stillness, the key, the chain, the boy's eyes on
the hand. What went: the named object, the injury, the age.

**Refused.** *一份离婚协议摊在律师事务所的会议桌上，钢笔在“女方”一栏签下名字……“孩子的姓，改回来。”*

**Passes the screen.** *深夜的会议室，一只牛皮纸文件袋摊开在桌上，钢笔签下名字，笔尖停顿一下再收；签完，一枚婚戒被摘下来，放在签名上面。……“房子我不要。我妈那套的钥匙，还我。”*

What survived: the signature, the pause, the ring on the name, the flat
delivery, the power reversal. What went: the named document, the named office,
the child.

## After a block

Read what the surface actually returned. Some API surfaces distinguish a
rejected input text from a rejected output video; a web surface usually shows a
generic notice. An output rejection after a clean prompt is a different problem
from an input rejection and is not solved by rewording. Rewrite once with the
method above, record the change in the take log, and follow the user's
remaining budget in [retake-protocol](retake-protocol.md). Repeated synonym
attempts are evasion, not repair.

## What this screen cannot do

It cannot see the classifier, so it cannot promise a pass, and it cannot prove
that a hit was the cause of a refusal. It does not assess whether the underlying
request is allowed; that assessment comes first, in the filter and copyright
routes. It is a word-level check written from observed refusals, kept in one
data file so the lists can be corrected as the record grows.

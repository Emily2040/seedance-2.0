# Anti-Slop Lexicon

Use concrete production language to resolve ambiguity while preserving the user's style and intent. This is an editorial heuristic for interpreting and reviewing a brief. The repository has not measured a universal improvement in generation stability from removing abstract words. A lexical match in a static evaluator does not establish that a word is useless in context or predict a rendered result.

## The Six Slop Classes

These are review cues, not automatic deletion rules. Inspect the phrase's role in the actual brief before editing.

| Class | Looks like | Conditional repair |
|---|---|---|
| Empty evaluators | `cinematic, epic, stunning, beautiful, dramatic` | Keep a useful style or mood cue; clarify only the missing decision, using the intended effect and existing scene |
| Borrowed image-model tokens | `8K, masterpiece, award-winning, trending on ArtStation, Unreal Engine, RAW` | Separate delivery requirements, intended render style and unsupported praise; these terms do not all serve the same role |
| Tag salad | comma-separated keywords with unclear relationships | Connect existing subject, action and timing when their relationship is unclear; concise lists are acceptable when already unambiguous |
| Negation slop | `no blur, no artifacts, no distortion, no extra fingers` | Clarify the desired state when useful; retain necessary explicit exclusions and preservation boundaries |
| Adjective stacking | `gorgeous, breathtaking, mesmerizing sunset` | Remove repetition that adds no distinct intent; retain the desired mood and any meaningful distinction |
| Feel-suffix words | `电影感 · 雰囲気のある · 감성적인 · atmosférico · атмосферный · vibey` | Interpret in context; keep the mood cue and clarify its intended expression only if needed |

## Replacement Table

The following are questions to resolve, not a menu of mandatory camera moves, lighting setups or visual effects. Use established choices first. When creative decisions are delegated, make a brief-specific proposal and disclose material assumptions; otherwise ask only about a necessary unresolved choice.

| Phrase to review | Decision to preserve or clarify |
|---|---|
| cinematic | Keep the intended film language; clarify framing, pacing or light only where the brief leaves a relevant ambiguity |
| epic | Preserve the ambition; determine whether the user means physical scale, emotional stakes or another kind of intensity |
| beautiful | Preserve the aesthetic preference; clarify the relevant color, texture, composition or performance |
| stunning / breathtaking | Identify the intended impact or reveal without inventing a new event |
| dynamic | Identify what changes over time; do not add camera movement to an intentionally locked shot |
| dramatic | Preserve the requested tension or performance; do not automatically add shadows, silence or camera pressure |
| ultra-realistic | Keep the chosen realism target; add relevant material or motion detail only when it helps, without promising photorealism |
| cool transition | Determine the intended relationship between shots before choosing a transition |
| magical | Preserve a fantasy or wonder direction; particles and glow are optional implementations |
| professional | Identify the intended production standard for this genre; product lighting and clean backgrounds are not universal |
| masterpiece / award-winning | Remove unsupported outcome claims when merely praise; retain any actual reference role and concrete requirement |
| 8K / ultra-HD | Preserve the delivery target under the rule below; do not treat prompt text as a resolution control |
| high quality / hyper-detailed | Clarify relevant review criteria or important details; do not conflate detail with output dimensions |
| Unreal Engine / RAW | Distinguish an intended render look from a requested tool or file format; wording does not establish that tool or format was used |
| atmosphere of mystery | Preserve what should remain uncertain; use the existing scene before proposing concealment, fog or darkness |
| visually striking | Clarify what the viewer should notice or remember in this brief |
| trending / viral style | Clarify any intended format or reference; do not assume vertical framing, rapid cuts or promise engagement |

## Delivery Requirements

Retain an explicit resolution requirement even when moving it out of scene prose. Use the selected operation's supported setting where available; if support is unknown, mark it unverified. If unavailable, state the mismatch and offer a supported output or a separate finishing step as an option. Do not silently downgrade, switch providers, upscale or spend credits. Honor choices already delegated within their scope.

Do not turn "8K" into a promise that the generated file is 8K, or turn "hyper-detailed" into an invented numeric resolution. Preserve requested aspect ratio, duration and other settings too. Apply only a user-requested or operation-documented length limit; disclose a conflict with required content instead of silently dropping it.

## Put the important instruction where a reader can find it

Open with the subject and action when that makes the brief clearer. Preserve exact dialogue, references, and continuity constraints even when they need more words. This is a drafting convention, not a measured token-weight law: one early adjective has no established numerical cost relative to later clauses. See [model-mechanics](model-mechanics.md) for the evidence boundary.

## Tag Salad Repair

A list of subject, sunset, resolution and style tags may leave action and timing undecided; it may also be an intentional mood board awaiting direction. Determine which task the user wants. Reconnect information already supplied and keep useful tags. If action is missing, use delegated creative scope or ask for the necessary choice. Do not silently invent a railing, a head turn, a slow push-in or surf ambience just to make a list resemble a shooting brief. Follow the calling skill's Director's Read before drafting generation prose.

## Negation Rule

Prefer a concrete desired state when a negative quality slogan is vague: `hands rest on the table` describes blocking but is only a suitable clarification when that pose matches the brief. It does not guarantee anatomical correctness. Keep useful literal constraints such as `no cuts` when they express the user's intent. Negation is not proven to summon an object, and this skill does not assume every provider has a special constraint slot. Never remove a safety or preservation boundary merely to shorten the prompt.

Observable detail helps resolve a missing decision; useful genre, medium, era, palette and mood labels can remain. Preserve exact dialogue, actual reference tokens and chosen sound states throughout the edit. A clarification is not permission for a new submission.

The Slop Traps tables in `references/vocab/` provide contextual examples in English, Chinese, Japanese, Korean, Spanish and Russian. They are editorial guidance, not evidence of language-wide model behavior.

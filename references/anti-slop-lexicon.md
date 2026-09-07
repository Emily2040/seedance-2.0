# Anti-Slop Lexicon

Replace empty evaluation language with observable production language. This is an editorial heuristic: it makes a brief easier to interpret and review. This repository has not measured a universal improvement in generation stability from removing abstract words.

## The Six Slop Classes

| Class | Looks like | Repair |
|---|---|---|
| Empty evaluators | `cinematic, epic, stunning, beautiful, dramatic` | convert each to the one observable detail that earns it |
| Borrowed image-model tokens | `8K, masterpiece, award-winning, trending on ArtStation, Unreal Engine, RAW` | delete; resolution and quality are settings or outcomes, never prose |
| Tag salad | comma-separated keyword dumps ported from image prompting | rewrite as shooting-brief prose: one sentence per element - subject, action, camera, light, sound |
| Negation slop | `no blur, no artifacts, no distortion, no extra fingers` | describe the desired composition; retain necessary explicit exclusions |
| Adjective stacking | `gorgeous, breathtaking, mesmerizing sunset` | three synonyms make one weak claim; pick the single detail that matters |
| Feel-suffix words | `电影感 · 雰囲気のある · 감성적인 · atmosférico · атмосферный · vibey` | name the physical cause of the feeling; every vocab file has a language-specific Slop Traps table |

## Replacement Table

| Weak phrase | Replace with |
|---|---|
| cinematic | shot scale, camera move, lighting, grade |
| epic | physical scale, stakes, crowd size, lens distance |
| beautiful | color, texture, composition, material, light behavior |
| stunning / breathtaking | visible contrast, reveal, movement, or detail |
| dynamic | specific movement, speed, and endpoint |
| dramatic | blocking, shadow, silence, or camera pressure |
| ultra-realistic | material behavior, skin texture, lens artifacts, natural motion |
| cool transition | match cut, whip pan, dissolve, hard cut, object wipe |
| magical | particle behavior, glow source, motion path, interaction |
| professional | product lighting setup, clean background, controlled camera |
| masterpiece / award-winning | delete; quality is not a request |
| 8K / ultra-HD / high quality | delete; resolution is a render setting, not prose |
| atmosphere of mystery | what is hidden, by what: doorway, shadow, fog |
| insanely / highly detailed | the two details that matter, named |
| visually striking | the one frame the viewer remembers, described |
| trending / viral style | the actual format: vertical, fast hook, caption-safe framing |

## Put the important instruction where a reader can find it

Open with the subject and action when that makes the brief clearer. Preserve exact dialogue, references, and continuity constraints even when they need more words. This is a drafting convention, not a measured token-weight law: one early adjective has no established numerical cost relative to later clauses. See [model-mechanics](model-mechanics.md) for the evidence boundary.

## Tag Salad Repair

Image-model habits port badly: `girl, sunset, 8K, cinematic, beautiful light, masterpiece, detailed face` gives a video model no action, no camera, no time axis. Rewrite as a brief: `A woman turns from the railing at sunset; the low sun flares behind her hair. Camera: slow push-in to a medium close-up. Sound: wind and distant surf.` One sentence per element beats twenty comma fragments.

## Negation Rule

Prefer a concrete desired state when a negative quality slogan is vague: `hands rest on the table` describes blocking more clearly than `no bad hands`. Keep useful literal constraints such as `no cuts` when they express the user's intent. Negation is not proven to summon an object, and this skill does not assume every provider has a special constraint slot. Never remove a safety or preservation boundary merely to shorten the prompt.

Rule: if a camera, microphone, light meter, or stopwatch cannot detect it, rewrite it.

Each language file in `references/vocab/` carries a Slop Traps table for its own community's empty words: English (`vocab/en.md`), Chinese (`vocab/zh.md`), Japanese (`vocab/ja.md`), Korean (`vocab/ko.md`), Spanish (`vocab/es.md`), Russian (`vocab/ru.md`).

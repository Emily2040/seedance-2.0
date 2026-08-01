# Anti-Slop Lexicon

Replace empty evaluation language with observable production language. Field-confirmed across prompting communities in every supported language: abstract quality words destabilize generation because the model cannot tell which element to emphasize; decomposing them into physical elements (camera verb + speed + viewpoint, light source + direction + behavior, material + texture + motion) stabilizes it.

## The Six Slop Classes

| Class | Looks like | Repair |
|---|---|---|
| Empty evaluators | `cinematic, epic, stunning, beautiful, dramatic` | convert each to the one observable detail that earns it |
| Borrowed image-model tokens | `8K, masterpiece, award-winning, trending on ArtStation, Unreal Engine, RAW` | delete; resolution and quality are settings or outcomes, never prose |
| Tag salad | comma-separated keyword dumps ported from image prompting | rewrite as shooting-brief prose: one sentence per element - subject, action, camera, light, sound |
| Negation slop | `no blur, no artifacts, no distortion, no extra fingers` | negation summons; exclude compositionally - describe what IS there instead |
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

## Position Costs More Than Count

Slop is not evenly expensive. Early clauses take a larger share of the conditioning budget (`model-mechanics.md`, mechanism 1: attention is a budget), so the same word costs more at the front of the prompt than at the back. One empty evaluator in the opening clause outranks three in the constraint tail.

Two consequences for drafting:

- **Never let a slop word hold an opening position.** `Cinematic shot of a woman reading a letter` has already spent its most valuable clause before naming what changes on screen.
- **Give that opening to the subject and its action instead.** This is the same rule the `seedance-prompt` Director Formula states as "put the subject and primary action first"; the lexicon is where it gets enforced.

Public prompting guides for Seedance 2.0 converge on the same practice, describing the opening of the prompt as where the subject and core action get locked in [field]. Treat that as field-observed corroboration of the mechanism, not a platform guarantee — the mechanism is the reason to follow it.

## Tag Salad Repair

Image-model habits port badly: `girl, sunset, 8K, cinematic, beautiful light, masterpiece, detailed face` gives a video model no action, no camera, no time axis. Rewrite as a brief: `A woman turns from the railing at sunset; the low sun flares behind her hair. Camera: slow push-in to a medium close-up. Sound: wind and distant surf.` One sentence per element beats twenty comma fragments.

## Negation Rule

Naming a flaw plants it. Instead of `no blur, no extra fingers, no watermark text`, lock the positive: `hands rest still on the table`, `clean unbroken label`, `empty sky above the skyline`. Use negation only in the constraint slot where the platform expects it (`no on-screen text, no watermark`), never as quality insurance.

Rule: if a camera, microphone, light meter, or stopwatch cannot detect it, rewrite it.

Each language file in `references/vocab/` carries a Slop Traps table for its own community's empty words: English (`vocab/en.md`), Chinese (`vocab/zh.md`), Japanese (`vocab/ja.md`), Korean (`vocab/ko.md`), Spanish (`vocab/es.md`), Russian (`vocab/ru.md`).

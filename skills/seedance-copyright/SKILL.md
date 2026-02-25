---
name: seedance-copyright
description: 'Check prompts against Seedance 2.0 content policy, apply safe IP substitutions, and navigate real-person and brand restrictions. Updated with live Feb 2026 enforcement data from Disney, Paramount, MPA, and SAG-AFTRA actions. Use before every generation that involves named characters, franchise IP, celebrity likenesses, brand logos, or streaming originals.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["copyright", "content-policy", "ip", "openclaw", "antigravity", "gemini-cli", "codex", "cursor"]
metadata: {"version": "3.3.0", "updated": "2026-02-25", "openclaw": {"emoji": "⚖️", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "parent": "seedance-20", "antigravity": {"emoji": "⚖️", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "⚖️", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-copyright

Content policy and IP protection rules for Seedance 2.0.
Every generation must clear this checklist before submission.

---

## ⚠️ Feb 2026 Enforcement Context

> **What happened (Feb 12–25, 2026):**
> ByteDance launched Seedance 2.0 on Feb 12. Within days, Disney, Paramount Skydance, Netflix, the Motion Picture Association (MPA), and SAG-AFTRA all sent cease-and-desist letters. Disney's letter called it a "virtual smash-and-grab" of IP. Netflix labelled it a "high-speed piracy engine." The Japanese government opened a regulatory investigation.
>
> ByteDance's response (Feb 15): "We are taking steps to strengthen current safeguards as we work to prevent the unauthorised use of intellectual property and likeness by users."
>
> **API global release was delayed** from the planned Feb 24 date. No new release date set (as of Feb 25).
>
> **What this means for prompts:** Hard blocks are stricter than v3.0. Many character/likeness filters have been tightened. Assume any named franchise character, actor, or streamer-original content will be refused or silently degraded.

---

## The Core Principle

Seedance blocks content that references specific protected intellectual property.
The model does not block *concepts*, *aesthetics*, or *archetypes* — only named, owned identities.
Your job: describe the idea without naming its owner.

---

## Hard Blocks (Always Refused)

These will trigger a content refusal regardless of framing:

| Category | Examples | Why blocked |
|---|---|---|
| Real human face by name | "Elon Musk", "Taylor Swift", "Obama", "Tom Cruise" | Right of publicity / likeness rights |
| Named franchise characters | "Iron Man", "Spider-Man", "Darth Vader", "Deadpool" | Disney/Marvel IP (cease-and-desist active) |
| Named Pixar / Disney Animation | "Elsa", "Woody", "Wall-E", "Simba" | Disney IP |
| Named anime characters | "Naruto", "Goku", "Luffy", "Levi", "Demon Slayer" | Studio/publisher IP + Japan gov investigation |
| Named game characters | "Mario", "Master Chief", "Geralt", "Kratos" | Nintendo/Microsoft/Sony/CD Projekt IP |
| Named streaming originals | "Stranger Things characters", "Squid Game guard", "Bridgerton" | Netflix IP (cease-and-desist active) |
| Paramount IP | "Shrek", "SpongeBob", "Dora", "Mission Impossible" | Paramount Skydance cease-and-desist active |
| Named DC characters | "Batman", "Superman", "Wonder Woman", "Joker" | WB/DC IP |
| Brand logo visible | Nike swoosh, Apple logo, Coca-Cola script | Trademark infringement |
| Copyrighted scene recreation | Exact shot from a named film | Film studio copyright |
| Named musical composition | "Play Bohemian Rhapsody as the score" | Music publishing rights |
| Deepfake / face-swap request | "Replace @Image1's face with [celeb]" | Deepfake policy + ByteDance upload block |
| Military / government insignia | Specific armed forces uniforms with unit insignia | Regulation + potential policy |

---

## Live Enforcement Examples (Feb 2026)

These were specifically cited in MPA and Disney legal letters as blocked examples:

| Prompt type | What triggered the block |
|---|---|
| "Spider-Man fighting Captain America on the streets of New York" | Named Marvel characters |
| "Anakin Skywalker and Rey battling with lightsabres" | Named Star Wars characters |
| "Stranger Things characters in a new scene" | Named Netflix original |
| "Deadpool and Wolverine fight sequence" | Named Marvel characters |
| "Shrek walks through a swamp" | Named Paramount character |
| "Tom Cruise and Brad Pitt fight scene" | Named real actors (viral refusal after Feb 15) |

> **Note:** The viral Tom Cruise / Brad Pitt fight clip that launched the controversy was generated before the Feb 15 tightening. Post-Feb 15, named real-person requests fail silently or return a generic refused message.

---

## Soft Blocks (Context-Dependent)

These may pass or fail depending on framing and visual specificity:

| Category | Risk level | Notes |
|---|---|---|
| Real building exteriors | Low–Medium | Eiffel Tower = public domain. Sydney Opera House = copyrighted until 2067. |
| Historical figures | Medium | Dead + 70+ years = usually safe. Recent historical = elevated risk. |
| Generic superhero aesthetic | Low | Red-and-gold armored suit = OK. "Iron Man suit" = blocked. |
| Fashion / brand color schemes | Low | Tiffany blue dress = OK. "Tiffany & Co. branding" = blocked. |
| Cultural / religious imagery | Medium | Context-sensitive. Avoid sacred symbols in commercial contexts. |
| Violence near real locations | High | Avoid generating violent content referencing real named locations. |
| Anime-style characters (unnamed) | Low-Medium | Original character designs OK; visual similarity to named character = risk. |
| Netflix / streamer UI elements | High | Show logos, episode cards, interface = blocked. |

---

## Safe Substitution Table

Replace named IP with descriptive archetypes. Always think: *what does it look like, not what is it called?*

### Film & Screen Characters

| ❌ Named IP | ✅ Safe descriptor |
|---|---|
| Iron Man | red-and-gold powered exoskeleton, chest reactor glow |
| Batman | dark armored vigilante, scalloped cape, bat emblem absent |
| Spider-Man | red-and-blue spandex web-shooter acrobat |
| Darth Vader | black full-helmet respirator suit, red energy blade |
| Deadpool | red-and-black tactical suit, masked mercenary, dual katanas on back |
| Terminator | chrome endoskeleton humanoid, single red eye |
| The Joker | smeared clown makeup, green hair, purple coat |
| Thanos | large purple-skinned humanoid with golden gauntlet |
| Elsa (Frozen) | platinum-haired woman in ice-blue gown, frost particles emanating from hands |
| Shrek | large green-skinned ogre, brown vest, Scottish accent implied in gesture |

### Netflix / Streaming Original Characters

| ❌ Named IP | ✅ Safe descriptor |
|---|---|
| Stranger Things – Eleven | young girl, buzzed head, nosebleed, telekinetic gesture |
| Stranger Things – Demogorgon | multi-petaled faceless biped, tall, dark biomass skin |
| Squid Game guard | hot-pink coverall figure, black circle/triangle/square mask |
| Bridgerton aesthetic | Regency-era ballroom, empire-waist gowns, string quartet |

### Anime Characters

| ❌ Named IP | ✅ Safe descriptor |
|---|---|
| Naruto | blond spiky-haired shinobi, orange jumpsuit, whisker scars |
| Goku | dark spiky-haired martial artist, orange gi, muscular |
| Luffy | straw-hat pirate, red vest, scar under left eye |
| Sailor Moon | blonde twin-tailed girl, white sailor uniform, crescent moon |
| Evangelion Unit-01 | purple-and-green giant mecha, single horn, four eyes |
| Totoro | large grey forest spirit, pointed ears, cat-like body |
| Demon Slayer – Tanjiro | dark-haired boy, checkered haori, box on back |
| Attack on Titan – Levi | short dark-haired soldier, vertical maneuvering gear, green cape |

### Game Characters

| ❌ Named IP | ✅ Safe descriptor |
|---|---|
| Master Chief | green full-body military power armor, golden visor |
| Link (Zelda) | green-tunic elf warrior, pointed hat, triangular shield |
| Geralt | white-haired witcher, dual swords on back, amber eyes |
| Kratos | bald grey-skinned warrior, red facial tattoo, chain blades |
| Aloy | red-haired hunter, tribal leather armor, focus device on ear |
| 2B (NieR) | blindfolded android, black gothic dress, white hair |

### Brand & Logo Substitutions

| ❌ Brand reference | ✅ Safe descriptor |
|---|---|
| Nike swoosh | curved checkmark logo on athletic wear |
| Apple logo | silver bitten-fruit icon on laptop |
| McDonald's arches | golden M arches, fast food restaurant |
| Coca-Cola script | red can, white cursive brand lettering |
| Ferrari horse | rearing black horse emblem on red sports car hood |
| Louis Vuitton print | repeating tan-and-brown monogram canvas |

---

## Real Person Policy

### Deceased public figures (70+ years)
Generally safe for historical depictions. Use period-accurate costume and setting.
```
✅ Victorian-era inventor in a laboratory, period suit, white beard, working on electrical coils
```

### Living public figures
**Never generate** by name or with distinctive likeness. (Feb 15 filter tightening blocks most name-based requests.)
```
❌ "Elon Musk standing next to a rocket"
✅ "tech billionaire in casual black T-shirt, standing on launch pad"

❌ "Tom Cruise in a fight scene"
✅ "athletic 50s male actor type, sharp jaw, cropped brown hair, grey blazer, fighting stance"
```

### Historical figures (recent, < 70 years deceased)
Elevated risk. Use archetype language.
```
❌ "Martin Luther King Jr. giving a speech"
✅ "civil rights leader at a podium, crowd in Washington Mall, 1960s period dress"
```

### Fictional actor likenesses
Never use an actor's face even when playing a fictional role.
```
❌ "Robert Downey Jr. as Tony Stark"
✅ "genius billionaire in a red-gold suit, goatee, reactor in chest"
```

### Real person upload (face in @Image)
ByteDance paused user image uploads of real faces as of Feb 15, 2026.
```
❌ Upload photo of Tom Cruise → "Generate as action hero"
✅ Upload original character art → "Generate as action hero"
```

---

## Architecture & Buildings

Some buildings are still under active copyright.

| Building | Status | Notes |
|---|---|---|
| Eiffel Tower (daytime) | Public domain | Safe |
| Eiffel Tower (night illumination) | Copyrighted | The light show design is protected |
| Sydney Opera House | Protected until ~2067 | Use "iconic white shell-roof opera house" |
| Guggenheim Bilbao | Protected | Use "titanium-clad curvilinear museum" |
| Louvre Pyramid | Protected until 2029 | Use "glass pyramid in courtyard of classical stone palace" |
| Empire State Building | Some restrictions | General exterior usually fine; exact replica risky |
| Most pre-1900 buildings | Public domain | Safe |

---

## Music & Audio

| ❌ Blocked | ✅ Safe |
|---|---|
| "Play Stairway to Heaven as the score" | "electric guitar power chord progression, rising tempo" |
| "BGM similar to Hans Zimmer's Inception theme" | "deep brass sting, slow bwaaah, building tension" |
| "Use a Drake beat" | "trap hi-hats 140 BPM, 808 bass, minimalist" |
| "Beethoven's 5th Symphony" | "dramatic orchestral opening, four-note fate motif, strings" |
| "John Williams Star Wars march" | "heroic brass fanfare, snare drum march, rising French horns" |

Pre-1928 compositions are public domain in the US. Describe texture, tempo, instrumentation — not titles.

---

## Aesthetic Borrowing vs. Direct Copy

You **can** borrow a film's visual grammar. You **cannot** recreate named scenes.

### Safe: aesthetic reference
```
✅ "washed-out teal-orange color grade, anamorphic lens flare, handheld shake"
   (describes the look without naming the film)
```

### Blocked: scene recreation
```
❌ "Recreate the Pulp Fiction diner scene with @Image1 as Vincent"
✅ "1970s diner, two men in black suits at a booth, morning light,
   16mm grain, conversation framing"
```

### Safe: genre grammar
```
✅ "neon-drenched rain-soaked street, flying cars overhead, Asian signage,
   cyberpunk dystopia" — describes Blade Runner's world without naming it
```

### Blocked: streamer-specific world-building
```
❌ "Stranger Things-style retro-80s supernatural horror with practical monsters"
✅ "1980s American suburb, flickering lights, child protagonists in Halloween
   costumes, practical rubber creature design, warm Super-8 grain"
```

---

## The Post-Feb-15 Practical Checklist

Before every generation, run all six gates:

1. **Name check** — Does the prompt contain any real person's name? → Remove.
2. **IP check** — Does it name a franchise, character, or brand? → Substitute with descriptor.
3. **Scene check** — Is it a recreation of a specific copyrighted scene or show? → Reframe generically.
4. **Audio check** — Does it request a named song or composer's work? → Describe musically.
5. **Building check** — Does it name a potentially protected building? → Use architectural descriptor.
6. **Logo check** — Would the output contain a recognizable logo? → Describe geometry without brand name.

All six clear → safe to generate.

---

## Why This Matters (for developers)

The Feb 2026 enforcement events changed the API landscape:
- **API release delayed** — planning around an integration date is impossible until ByteDance issues a new schedule.
- **Filter tightening will continue** — MPA demanded a Feb 27 response. Expect further content-filter updates.
- **Platform viability model** — ByteDance may follow the OpenAI/Disney path: licensing deals with studios as the path to re-enabling character content.
- **Open-source alternatives** — Community discussion (r/comfyui) points to WAN 2.2 and local OSS models as filter-free alternatives, but with lower output quality.

---

## Routing

For prompt structure → [skill:seedance-prompt]
For style transfer without IP → [skill:seedance-style]
For character identity → [skill:seedance-characters]
For QA/blocked output → [skill:seedance-troubleshoot]

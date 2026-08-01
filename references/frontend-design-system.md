# Frontend Design System

This repository has no application frontend. The user-facing frontend is the GitHub README, generated bitmap assets, and SVG support assets.

## The philosophy: Call Sheet

A call sheet is the document a film crew reads before anyone touches a camera. It is dense, unglamorous, and absolutely precise: who, where, when, in what order. Nobody decorates a call sheet. Its beauty is a by-product of the fact that a hundred people have to act on it correctly at five in the morning, on a phone, in the dark.

That is the aesthetic this project earns. The skill exists to make intent legible *before* generation begins, so the surface should look like the paperwork of a working production — not like the interface of a camera. Every mark is a decision already made. The page should read as though it were set by someone who has laid out a thousand of these and has stopped needing to prove anything.

**Restraint is the accent.** One family for structure, one for voice, one hue that appears exactly once. Where an ordinary layout reaches for a second colour, this one reaches for space. The eye travels down a single vertical spine, meets one warm mark, and understands the hierarchy without being told. If a reader notices the design before the information, the design has failed.

**Rules carry the composition.** Hairlines do the work that boxes, cards, shadows, and gradients do elsewhere. A rule states where one idea ends and the next begins, so it is placed to the pixel and never repeated for texture. Negative space is not leftover; it is the majority material, measured as carefully as the type.

**Type is the image.** The display serif is set large enough to be architecture rather than a label. Monospace appears only where the grid of the letterforms does real work — tabular specification fields. Nothing is centred that could be aligned to a spine. Nothing is bold that could be larger. Nothing is uppercase that is not a field label.

**Refuse the costume.** No viewfinder chrome, no record dots, no timecode strips, no aspect badges, no lens diagrams. Those signal *camera* when the subject is *judgement*, and they are the visual cliché of every AI-video product. Depicting the tool substitutes for having a point of view. The work here is planning, so the artifact is a document.

The result should look meticulously crafted — the product of deep expertise and painstaking attention, where measure, alignment, and interval have been laboured over until nothing remains to remove.

## Design goals

- Clean, cinematic, high-contrast presentation.
- No collapsed Markdown.
- No overloaded neon copy.
- Usable on GitHub mobile and dark mode.
- Clear start-here decision path.
- Validation commands visible above the fold after the skill map.

## Asset rules

- Use SVG for simple structural support diagrams.
- Use generated bitmap images for the README hero, operating-system infographic, skill-map infographic, capability map, CDN delivery map, reference-role map, production-delivery map, and QC stack when the asset needs cinematic texture, real scene depth, or visual storytelling.
- Bitmap hero/infographic/map assets should be logo-free, watermark-free, and readable at GitHub README width.
- Text-rich infographics are allowed when labels are large, short, corrected, and repeated in accessible Markdown next to the image.
- SVG assets must include `<title>` and `<desc>`.
- No external scripts, images, fonts, or tracking in SVG assets.
- Avoid generic lens dashboards, dense decorative noise, and unreadable micro labels.
- Inspect generated text manually; reject garbled words, ugly font treatment, low contrast, noisy decoration, and placeholder-looking panels.

## README rules

- No line longer than 500 characters.
- Tables should have real newlines.
- Every major section should answer a user decision: what is it, where do I start, what skills exist, how do I validate, what changed.
- Bitmap hero art should avoid watermarks and tiny text. Text-rich infographic labels must also be represented in Markdown for accessibility and search.
- **The README body obeys the same law as the assets.** One left spine; nothing centered. A `<div align="center">` above the fold is the costume of every template README, and it contradicts "centre nothing" the moment the masthead ends.
- **No badge chrome.** shields.io rows are the most ubiquitous element on GitHub - the exact opposite of an ownable page - and count badges bake staleness into the front page the same way baked counts do in vector assets. Version, license, and date are typographic facts on one quiet line; the CI badge earns its place only if it reports live state, not a number someone must remember to update.
- **The masthead speaks once.** No H1 or bold tagline restating what the wordmark and its alt text already say; the first Markdown text on the page is the sentence the masthead does not contain. Repeating the title within one screen is the opposite of editorial confidence.
- **Release prose lives in the changelog.** The front page carries the version, the date, and a link - not a paragraph of shipped features that duplicates `CHANGELOG.md` and goes stale beside it.

## Editorial Design Tokens (v6 front page)

The front page uses a studio spec-sheet system. Apply these tokens to every hand-built vector asset; never reintroduce gradients, glow blobs, or multi-hue accent ramps.

| Token | Dark | Light |
|---|---|---|
| Background | `#100E0A` warm ink | `#F7F3EA` warm paper |
| Foreground | `#EDE6D6` | `#1C1914` |
| Muted | `#9A917D` | `#6F6757` |
| Hairline | `#2E2A22` | `#D8D0BE` |
| Accent (single) | `#E2A75E` amber | `#A86F24` amber |

- **Display type is outlined, never a font stack.** The wordmark, the tagline, and the operating diagram's root label ship as vector glyph outlines generated by `scripts/build_masthead_outlines.py` from Bodoni Moda (SIL OFL; attribution, version, and instance axes recorded in `assets/masthead-outlines.json`). Optical size tracks the rendered size, clamped to the axis range, because a didone drawn for 96px has hairlines that vanish at 26px.
- **Why outlines and not a stack.** The previous specification was `Didot, 'Bodoni MT', 'Hoefler Text', Baskerville, 'Palatino Linotype', Georgia, serif`. That resolves to Didot only on macOS; Windows falls through to Bodoni MT or Palatino Linotype, and Linux — including the machine that builds and validates this repository, which has none of the six — falls all the way to a default system serif. The "high-contrast editorial serif" specified here was what a minority of readers actually saw. Outlines depend on no installed font and render identically for everyone.
- This is the same rule that retired the script face: a design that only resolves on the author's machine is not a design. The script font was caught; the serif stack had the identical defect and outlived the fix by a release. When a face matters, outline it.
- **Live text is monospace only.** Specification labels and values stay live text because they carry CJK, which a Latin outline set cannot supply — so they use the monospace stack. `design_audit.py` resolves every family an asset declares, in both the `font-family` attribute and the CSS `font:` shorthand, and requires each to be the monospace stack. It is written as a requirement rather than a list of banned serifs, because a denylist silently passes `font-family="Arial"` or a bare generic — which is the same platform-dependent rendering the outlines were adopted to end.
- The accent is carried by colour rather than by a second typeface. One family, two sizes.
- Specification type: `ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, monospace` - weight 400, smaller sizes, generous letter-spacing (6-7px on eyebrows); labels whisper, the wordmark speaks.
- Motifs: hairlines, a single registration tick, and label-over-value specification fields - the marks a production document carries. Explicitly retired: sprocket strips, viewfinder corner marks, crosshairs, timecode, record dots, aspect badges, waveform ticks. Those depict a camera; this project is about the judgement made before one rolls, and they are the visual cliche of every AI-video product.
- Masthead structure (1200x470): a single left spine at the outer margin, an eyebrow above a hairline, the wordmark given the whole middle of the canvas, and a specification strip below a second hairline. Two hairlines, no more. Centre nothing. The canvas height exists to let the wordmark breathe, not to be filled.
- One amber gesture per composition, and the script `Skill OS` carries it. Nothing else is amber - never a second hue, and never a second amber mark competing with the wordmark.
- The masthead ships as a theme-aware pair (`hero-dark.svg`, `hero-light.svg`) behind a `prefers-color-scheme` picture element; the operating diagram (`skill-map.svg`) carries its own background so it reads on both themes.
- Do not bake version numbers or counts into vector assets; they go stale. Use timeless labels (ROUTE / VERIFY / DIRECT / DELIVER).
- Generated bitmap art is gallery-only. The working interface of the README is vector.

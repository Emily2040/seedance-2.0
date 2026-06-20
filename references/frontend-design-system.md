# Frontend Design System

This repository has no application frontend. The user-facing frontend is the GitHub README, generated bitmap assets, and SVG support assets.

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

## Editorial Design Tokens (v6 front page)

The front page uses a studio spec-sheet system. Apply these tokens to every hand-built vector asset; never reintroduce gradients, glow blobs, or multi-hue accent ramps.

| Token | Dark | Light |
|---|---|---|
| Background | `#100E0A` warm ink | `#F7F3EA` warm paper |
| Foreground | `#EDE6D6` | `#1C1914` |
| Muted | `#9A917D` | `#6F6757` |
| Hairline | `#2E2A22` | `#D8D0BE` |
| Accent (single) | `#E2A75E` amber | `#A86F24` amber |

- Display type: `Didot, 'Bodoni MT', 'Hoefler Text', Baskerville, 'Palatino Linotype', Georgia, serif` - high-contrast editorial serif where the system provides one, Georgia as the universal fallback; weight 400, no external fonts. The tagline is set as a serif italic aphorism in sentence case, not monospace.
- Specification type: `ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, monospace` - weight 400, smaller sizes, generous letter-spacing (6-7px on eyebrows); labels whisper, the wordmark speaks.
- Motifs: sprocket strips, viewfinder corner marks, crosshairs, timecode, waveform ticks - drawn as fine line work.
- The masthead ships as a theme-aware pair (`hero-dark.svg`, `hero-light.svg`) behind a `prefers-color-scheme` picture element; the operating diagram (`skill-map.svg`) carries its own background so it reads on both themes.
- Do not bake version numbers or counts into vector assets; they go stale. Use timeless labels (ROUTE / VERIFY / DIRECT / DELIVER).
- Generated bitmap art is gallery-only. The working interface of the README is vector.

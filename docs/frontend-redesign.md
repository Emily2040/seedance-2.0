# V6 Front Page Design

The repository does not currently contain a standalone web app. The public frontend is the GitHub README, generated bitmap hero/infographic assets, and SVG support diagrams.

## V6 Design Goals

- Lead with the v6 sequence-state promise: one story state, one current clip contract, one compiled Seedance prompt.
- Make the README useful to native English, Chinese, Japanese, and Korean readers before they reach the install section, including full native-reader docs and active example skills.
- Show Seedance's practical range: references, first/last-frame continuity, continuation, product reveal, timeline control, audio, and camera direction.
- Use generated cinematic infographics for the operating-system overview, skill map, skill capability map, CDN delivery map, reference role map, production delivery map, and QC stack.
- Allow text-rich infographics when the text is large, corrected, visually balanced, and repeated in nearby searchable Markdown.
- Keep SVG assets as support diagrams, not the primary emotional surface.
- Validate README completeness, gallery coverage, PNG dimensions, and asset presence with `scripts/design_audit.py`.

## Native Reader Requirements

- The first screen must say the project is current v6 work.
- The README must include visible Chinese, Japanese, and Korean copy, not only English labels saying those languages exist.
- Native-language rows must link to active skill files and active vocabulary references, not migrated legacy files.
- Japanese and Korean must have active example-skill routes equal in status to Chinese examples.
- Reference tags such as `[Image1]`, `[Video1]`, `[Audio1]`, `@图1`, and `@视频1` must be shown exactly so readers do not translate them away.
- Localization guidance must keep subtitles, legal copy, and market copy in post-production unless the user explicitly asks for simple on-screen generated text.

## Assets

- `assets/hero-command-center.png`
- `assets/hero-global-filmmaker-mode.png`
- `assets/infographic-skill-capabilities.png`
- `assets/infographic-cdn-delivery-map.png`
- `assets/infographic-reference-role-map.png`
- `assets/infographic-production-delivery.png`
- `assets/infographic-professional-qc-stack.png`
- `assets/hero-cinematic.png`
- `assets/skill-os-infographic.png`
- `assets/skill-map-cinematic.png`
- `assets/hero-dark.svg`
- `assets/hero-light.svg`
- `assets/skill-map.svg`

## Design Rules

- No external fonts or scripts in SVG.
- Every SVG needs `<title>` and `<desc>`.
- README should stay readable on mobile and dark mode.
- Avoid dense badge walls and noisy decorative text.
- Use text-rich generated infographics only for big, short labels that remain legible at README width.
- Inspect every generated text image; reject garbled words, ugly typography, poor contrast, or placeholder-looking panels before commit.
- Keep equivalent Markdown explanation beside every text-rich image so the repo remains accessible and searchable.

## V6 Editorial System

The masthead moved from generated bitmap art to a hand-built editorial system: serif display over monospace specification labels, warm ink/paper themes with a single amber accent, film sprocket and viewfinder line work, and zero gradients. `assets/hero-dark.svg` and `assets/hero-light.svg` are served through a `prefers-color-scheme` picture element so the hero matches the viewer's GitHub theme; `assets/skill-map.svg` was rebuilt as a specification diagram (gates -> root -> clusters -> reference library -> validation). Badges were unified to flat-square ink/amber. Generated bitmaps - the hero shots and text-rich infographics, including assets/infographic-cdn-delivery-map.png - remain in the curated Visual Gallery with searchable alt text, plus the operating-system art relocated from the body. Tokens live in `references/frontend-design-system.md`.

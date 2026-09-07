# README design acceptance

The public surface is a GitHub README, not a standalone application. Its first
job is to explain the skill, show one useful prompt and make installation easy
to find. Keep the deterministic light/dark masthead. Put generation provenance
beside any teaching art, and keep captions and instructions as searchable text.

## Automated checks

Run `python scripts/design_audit.py` from the repository root. It checks the
supported inline Markdown/HTML link subset, local file and heading destinations,
case-correct paths, six quickstart links, Start Here and Install destinations,
nonempty image descriptions, supported PNG/SVG media and explicit byte ceilings.
PNG checks inspect signatures and dimensions, not full pixel decoding or craft.
Every embedded SVG is parsed as XML and checked for accessible title/description,
scripts and external resources. The three canonical SVG assets also retain
their outlined-typography and editorial constraints.
The separate deterministic masthead build check remains mandatory.

There is no minimum README length, bitmap byte count, picture count or gallery
quota. A small optimized image is allowed; a large image is not evidence of
quality. The front page has a 4 MiB aggregate embedded-asset ceiling after
the gallery was moved to an optional archive. Count all local
embedded assets once, including both picture-theme alternatives; this is a
conservative asset-size bound, not a measured network trace or load-time score.
Remote embedded images cannot be bounded by this offline check and are rejected.

This parser supports the repository's inline links and ATX headings; it is not
a complete GitHub Markdown renderer or accessibility certification. Reference
links, rich HTML, unusual heading punctuation and browser behavior still need
rendered inspection. Never treat a passing structural check as visual approval.

## Manual acceptance before publishing a redesign

Inspect light and dark themes at 390, 768 and 1280 CSS pixels. Record which
surface was actually tested: real GitHub or a local approximation. Test:

1. With optional sections closed, identify the skill, reach a usable example and
   find installation without scrolling past a gallery or maintainer commands.
2. At 390px, read the prompt and evidence caption without horizontal page
   scrolling. Wide technical tables may scroll inside their own region.
3. Use Tab and Enter to follow entry links and open/close each details summary.
   Confirm visible focus and a meaningful summary name.
4. Follow all six language entry links. Distinguish available docs from pending
   native review and avoid claiming full README parity for ES/RU.
5. With images unavailable, the example still teaches its action and endpoint.
   Keep art labels outside the bitmap; no fake UI, metrics or certification.
6. Review generated image hands, objects, contact, light and scene intent at
   full size and mobile size. No still image establishes motion or lip-sync.
7. Run the installation tests: source-only art and evaluator material must not
   create broken dependencies or change the installed trust boundary.

Archive illustrations may remain available through a link. They need not load
on the front page. Do not remove audit history or relabel old concept art as a
product screenshot, rendered benchmark or verified production workflow.

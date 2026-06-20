# Golden Prompt: Dense 2D Storyboard

## Source Brief

Create a short 2D animation board with three cuts.

## Internal Prompt Specification

Medium: 2d_animation. Shot structure: dense_multishot. Use animation layout vocabulary and avoid live-action lens behavior.

## Compiled Natural-Language Prompt

Shot 1: hand-drawn cel animation, foreground rain layer slides downward while the background street holds still; the courier silhouette enters frame and stops under the sign. Shot 2: close character layout, two-frame blink hold, scarf smear as wind pulls left-to-right, ending with her gaze locked on the case. Shot 3: top-down animation layout, puddle reflection layer ripples once and settles around the case. No photographic lens or sensor language.

## Lint Result

lint: pass

## Control-Critical Sentences

why this remains: `foreground rain layer` and `background street holds` use animation-layer grammar.

why this remains: `No photographic lens or sensor language` protects the 2D medium contract.

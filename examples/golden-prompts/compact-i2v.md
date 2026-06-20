# Golden Prompt: Compact I2V

## Source Brief

Animate a product still without changing the product.

## Internal Prompt Specification

Mode: I2V. Reference: `[Image1]` controls product identity. Current clip action: one light sweep. Endpoint: logo remains readable.

## Compiled Natural-Language Prompt

[Image1] is the product identity reference; preserve its logo, shape, color, and material exactly. Only a narrow warm light sweep moves across the glass, ending with the label cleanly readable. Camera stays locked. Sound: one soft chime at the final highlight.

## Lint Result

lint: pass

## Control-Critical Sentences

why this remains: `[Image1] is the product identity reference` binds the still to identity only.

why this remains: `Only a narrow warm light sweep moves` prevents static product details from being regenerated.

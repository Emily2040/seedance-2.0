# Golden Prompt: First Last Frame Transition

## Source Brief

Move from one known product state to another.

## Internal Prompt Specification

Mode: FLF2V. `[Image1]` is first frame. `[Image2]` is final visual target. No unrelated story beats.

## Compiled Natural-Language Prompt

[Image1] is the first frame and [Image2] is the final visual target. Preserve the same product identity, logo, label, and tabletop geometry. Generate only the continuous transition: condensation forms on the bottle, slides once down the front glass, and stops with the product aligned exactly to [Image2]. Camera remains locked; sound is a single soft glass tick at the endpoint.

## Lint Result

lint: pass

## Control-Critical Sentences

why this remains: `[Image2] is the final visual target` locks the endpoint role.

why this remains: `Generate only the continuous transition` prevents extra story from leaking in.

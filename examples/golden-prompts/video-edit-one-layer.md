# Golden Prompt: Video Edit One Layer

## Source Brief

Fix lighting in an otherwise good clip.

## Internal Prompt Specification

Mode: edit. `[Video1]` is source clip. Change one layer only.

## Compiled Natural-Language Prompt

[Video1] is the source clip. Preserve the existing subject, timing, camera path, background layout, and action exactly. Change only the lighting layer: add a soft warm practical lamp from frame left and a faint blue rim on the shoulder, keeping the same motion and endpoint. Do not regenerate wardrobe, face, props, dialogue, or camera movement.

## Lint Result

lint: pass

## Control-Critical Sentences

why this remains: `Change only the lighting layer` enforces one-layer edit discipline.

why this remains: `Do not regenerate wardrobe, face, props, dialogue, or camera movement` protects accepted continuity.

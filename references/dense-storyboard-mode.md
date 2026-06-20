# Dense Storyboard Mode

Use this reference when a request contains many panels, storyboard beats, animation boards, or multi-shot descriptions.

## Classifier

Choose `dense_multishot` only when the user explicitly wants cuts inside one generation and the active surface/profile supports that structure. Choose `phased_single_take` when the action should remain continuous. Do not combine "single continuous take" with hard shot labels.

## Dense Multishot Rules

- Use shot labels.
- Give each shot one action and one endpoint.
- Keep continuity locks visible across shot boundaries.
- Do not overload a short generation with too many locations, large actions, or character changes.
- Later generation prompts remain provisional until the previous accepted clip is reviewed.

## Continuous Take Rules

Use Beginning / Then / Finally. Do not use shot labels or hard cuts. Describe phases of one camera path, one geography, and one physical action chain.

## 2D Animation

For 2D, anime, or cel work, use animation-layout vocabulary: layers, parallax, holds, smear frames, impact frames, cel shadow, line boil, background pan, and compositing. Avoid photographic sensor, lens, bokeh, ISO, and shallow-focus language unless the user explicitly wants a hybrid simulated-camera style.

## Endpoint Discipline

Every dense storyboard beat must end in a completed visual state. If the endpoint is not visible, the next clip cannot inherit it safely.

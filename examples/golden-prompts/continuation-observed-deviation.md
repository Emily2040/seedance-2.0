# Golden Prompt: Continuation Observed Deviation

## Source Brief

The plan said the subject reached the door, but the accepted clip ended two steps away.

## Internal Prompt Specification

Use observed_end_state, not planned_end_state. Carry unfinished beat into current clip.

## Compiled Natural-Language Prompt

Start with the accepted final frame: the traveler is still two steps from the open rear door, mid-stride, suitcase behind her. Complete only those two steps first, then let her reach the door handle. Keep the same left-to-right travel, black sedan, rain reflections, and tracking camera. Do not assume she is already at the door. Do not place her inside the car until after the two steps are completed.

## Lint Result

lint: pass

## Control-Critical Sentences

why this remains: `still two steps from the open rear door` preserves the observed deviation.

why this remains: `Do not assume she is already at the door` prevents planned-state leakage.

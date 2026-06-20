# Golden Prompt: Sequence Continuation

## Source Brief

Continue Clip 02 of the airport sequence after accepted Clip 01.

## Internal Prompt Specification

Sequence relation: seamless_continuation. Source: accepted `[Video 1]`. Opening state: observed traveler two steps from open car door. Exclude terminal exit and vehicle departure.

## Compiled Natural-Language Prompt

[Video 1] is the accepted continuity source; @Image 1 preserves the traveler identity and charcoal coat. Begin from the observed final frame: she is two steps from the open rear door, still moving left-to-right with the suitcase rolling behind. Continue the same lateral camera and rainy curb ambience. This clip only finishes the two steps, lets her enter the rear seat, and closes the door. Do not replay the terminal exit. Do not show the car departing yet.

## Lint Result

lint: pass

## Control-Critical Sentences

why this remains: `Begin from the observed final frame` uses actual accepted footage, not the plan.

why this remains: `Do not replay the terminal exit` blocks a completed beat.

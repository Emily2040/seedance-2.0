# Sequence Plan: Airport Arrival

## Project Summary

The traveler exits the airport and reaches a waiting black sedan through rain and crowd pressure. The complete story resolves only when the sedan leaves traffic with the traveler inside.

## Story Spine

Initial condition: terminal exit and crowd pressure.
Objective: reach the waiting car.
Escalation: rain, crowd, and distance slow the approach.
Final outcome: traveler is inside the sedan and the car departs.

## Sequence Map

Clip 01: Exit terminal and approach the open rear door. Planned endpoint was beside the open door. Accepted observed endpoint is two steps away.

Clip 02: Start two steps away, finish the approach, enter the car, and close the door. Do not replay the terminal exit. Do not show vehicle departure.

Clip 03: Vehicle leaves the curb and disappears into traffic. This remains provisional until Clip 02 is accepted.

## Project State Capsule

PROJECT ID: seq_airport_arrival
STORY GOAL: traveler reaches waiting car and escapes airport crowd
FINAL OUTCOME: black sedan leaves traffic with traveler inside
SURFACE: unknown conservative generic profile
REFERENCE TAGS: @Image 1, [Video 1]
CANONICAL REFERENCES: @Image 1 controls traveler identity and wardrobe
ACCEPTED CLIPS: clip_01 accepted_with_deviation
SCENE MAP: scene_01 current - terminal exit to vehicle departure
CURRENT SCENE: scene_01, release
CURRENT ACTUAL STATE: traveler is two steps from the open rear car door
OPEN MOTION: traveler and camera continue left-to-right
COMPLETED BEATS: terminal exit
NEXT CLIP JOB: finish approach, enter car, close door
NEXT CLIP INTENT: the door thump cuts the curb noise and ends public access to her
NEXT CLIP DIRECTOR'S READ LANE: narrative
NEXT CLIP AUTHORING STATE: INTERNAL - DO NOT COPY LABELS INTO THE GENERATION PROMPT
DRAMATIC FUNCTION: Convert shelter from a visible promise into a boundary she closes herself.
TURN: Public endurance continues two steps from the car, then curb noise and exposure are cut off by the shut door.
POV: The traveler; the camera stays at her wet shoulder until the closed door removes the curb from her sensory field.
POWER SHIFT: The curb controls her exposure at the start; she controls the boundary when her hand pulls the door shut.
HIDDEN WANT/OBJECTIVE: Get behind closed glass without giving the curbside crowd a readable release.
OBSTACLE/TACTIC: Two exposed steps and rain on her face invite a visible reaction; she redirects the wiping impulse into folding the tag under the suitcase handle before entering.
SUBTEXT/CONTRADICTION: She accepts shelter through an exact practical gesture while her face continues to deny that she needed it.
VISIBLE SUPPRESSED BEHAVIOR: Her fingers start toward the rain on her cheek, then redirect to fold the creased tag beneath the suitcase handle.
NON-TRANSFERABLE DETAIL: A creased paper airline tag looped around the suitcase handle is folded beneath the handle only after the car can shield the action.
NON-TRANSFERABLE DETAIL PROVENANCE: authored_choice
NON-TRANSFERABLE DETAIL SOURCE: null
STOCK SOLUTION REFUSED: No shoulder drop, backward glance, or relieved smile; replace them with the redirected hand, inward-facing tag, and the door thump cutting curb noise.
VALUE BEFORE: shelter is within two steps while public endurance continues
VALUE AFTER: the closed door severs public exposure without a performed release
NEXT CLIP VISIBLE CARRIERS: Her fingers start toward the rain on her cheek, then redirect to fold the creased airline tag beneath the suitcase handle. | She keeps the suitcase upright until the rear door shuts, then turns it so the folded tag faces the seatback. | The door thump cuts the curb noise while her face and shoulders remain level.
CONTINUITY LOCKS: identity, wardrobe, creased paper airline tag, travel direction, sedan, curbside environment
ALLOWED CHANGES: traveler may enter rear seat and close door
RESERVED FUTURE BEATS: vehicle departure
EXTENSION DEPTH: 1
UNRESOLVED UNCERTAINTIES: exact active surface limits

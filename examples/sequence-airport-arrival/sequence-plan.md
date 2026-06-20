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
CURRENT ACTUAL STATE: traveler is two steps from the open rear car door
OPEN MOTION: traveler and camera continue left-to-right
COMPLETED BEATS: terminal exit
NEXT CLIP JOB: finish approach, enter car, close door
CONTINUITY LOCKS: identity, wardrobe, travel direction, sedan, curbside environment
ALLOWED CHANGES: traveler may enter rear seat and close door
RESERVED FUTURE BEATS: vehicle departure
EXTENSION DEPTH: 1
UNRESOLVED UNCERTAINTIES: exact active surface limits

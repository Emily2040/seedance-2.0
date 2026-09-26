# Failure Atlas

Use this reference when sequence or continuation output fails.

| Symptom | Likely cause | Primary repair variable |
|---|---|---|
| Continuation begins from planned ending | Parent observed state was not reviewed. | Replace opening with observed end state. |
| Action restarts | Completed beat was not marked already happened. | Add completed beat exclusion. |
| Future event appears early | Reserved beat leaked into prompt. | Remove future beat from prompt and endpoint. |
| Identity drifts through extensions | Continuity source displaced canonical identity reference. | Re-anchor identity from canonical image. |
| Screen direction flips | Axis was not locked or reset intentionally. | State screen direction or declare axis reset. |
| Open motion stops | Motion vector was not inherited. | Carry subject/camera speed and direction. |
| Camera phase restarts | Camera endpoint from parent was missing. | Start from observed camera phase. |
| Prop contradicts prior clip | Prop owner/position/condition was not tracked. | Add prop state handoff. |
| Dialogue repeats | Completed dialogue was not logged. | Mark line completed and continue audio phase. |
| Extension quality degrades | Extension depth and drift were ignored. | Re-anchor or create intentional next shot. |
| Reference roles contaminate | Transfer/ignore clauses were absent. | Split reference roles and exclusions. |
| Event density is too high | Several beats were compiled into one prompt. | Reassign future beats to later clips. |
| Character performs the accident on purpose | An involuntary outcome (a coat caught in a door, a slip, a spill) was written as the endpoint. | Write the deliberate action, or leave the consequence off screen. |
| A face or object changes colour, or an idiom appears as a picture | Figurative wording ("his face fell", 脸沉下来) was rendered literally. | Write the expression as muscles and objects; colour only as material. |
| Only one of several actions in a shot appears | Several actions were stacked in one shot block. | One action per shot; split or cut the rest. |
| Light or a face changes between cuts | The lock line was written once, not in every shot. | Repeat light and identity in the same words at the end of every block. |
| The ending never lands on the intended frame | The endpoint was outside the shot's framing with no move or cut. | Write the move that reaches it, or the next shot. |
| Prompt refused before rendering | Cue words stacked: a weapon, an injury, a crime, a minor in peril, a named institution. | Run the moderation pre-screen; remove, move off frame, or replace with the consequence. |

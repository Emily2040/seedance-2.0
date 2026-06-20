# Reference Workflow

## Asset Role Map

Before writing prompt prose, assign every uploaded asset a role. Role mapping prevents accidental transfer of identity, logos, scene ownership, or incompatible camera and motion instructions.

| Asset | Good Roles | Avoid |
|---|---|---|
| Image | identity, product, pose, costume, environment, first frame, last frame | asking it to define unseen motion |
| Video | motion, camera, pacing, blocking, timing, gesture rhythm | copying protected identity, logo, or scene ownership |
| Audio | rhythm, tempo, mood, ambience, delivery tone, music texture | assuming voice, song, or likeness authorization |
| Text brief | action, genre, camera plan, constraints | replacing concrete reference roles with vague mood words |

## Rules

- Preserve reference tags exactly.
- Give every reference one primary role before writing style language.
- Do not ask one reference to control incompatible roles unless the tradeoff is explicit.
- Use owned, licensed, public-domain, or clearly authorized references.
- Write what should transfer and what should not transfer.
- When authorization is unclear, transfer broad motion, tempo, mood, or production function rather than protected identity.
- Treat multimodal reference generation, video edit, video extend, and first/last-frame generation as separate tasks. They can share assets, but the prompt should name the active workflow.
- If audio and video references compete, make the video silent when audio timing must dominate, or state that the video controls camera/motion only and `[Audio1]` controls tempo.
- In sequences, separate canonical references from accepted continuity sources: canonical identity/product references control immutable design, while accepted previous footage controls transient opening state.
- Never let a motion reference overwrite continuity locks, completed beats, reserved beats, or exact reference tags.

## Workflow-Specific Patterns

| Workflow | Use this wording | Avoid |
|---|---|---|
| Multimodal reference | `[Image1] controls product identity; [Video1] controls camera rhythm; [Audio1] controls tempo only.` | `Use all references for style.` |
| Video edit | `[Video1] is the source clip; preserve composition and timing, change only [lighting/background/VFX].` | Regenerating the whole concept from scratch. |
| Video extend | `[Video1] is the previous clip; continue the same shot for [duration] and preserve last-frame continuity.` | Starting a new scene with no continuity anchor. |
| First/last frame | `[Image1] is first frame; [Image2] is final visual target; generate the continuous transition only.` | Asking the last frame to be only "mood." |
| Audio reference | `[Audio1] controls tempo and energy; do not copy protected voice, song, or performance identity.` | Treating audio as authorization proof. |

## Role Examples

| Situation | Strong map |
|---|---|
| Product ad | `[Image1] controls product identity; [Audio1] controls tempo only.` |
| Motion transfer | `[Video1] controls side-step choreography only; do not transfer performer, costume, room, or logo.` |
| Style reference | `[Image2] controls warm bar atmosphere only; product identity remains from [Image1].` |
| First-last frame | `[Image1] is first frame; [Image2] is target end frame; transition occurs through light sweep, not product deformation.` |
| Edit/extend | `[Video1] is the source clip; preserve subject and camera path, replace only the failed lighting beat from 3s to 5s.` |

## Motion Transfer

Field-observed technique; test before promising results. Probably the most under-used reference capability: a donor video drives choreography or camera rhythm while an image keeps identity.

- Pair one donor `[Video1]` with one identity anchor `[Image1]`, and write the exclusion explicitly: `[Video1] controls the choreography only - nothing of its appearance, performer, costume, room, or logo transfers.`
- Pick donor clips with one clear action, a clean silhouette, and a steady camera. Busy multi-person footage transfers noise, not motion.
- Mute the donor clip before upload unless its sound should drive timing; if it keeps sound, state which reference owns the clock.
- Transfers well: choreography, gesture timing, camera rhythm, blocking. Transfers poorly: fine hand detail, multi-person sync, facial performance.
- Use only owned, licensed, stock, mocap, rehearsal, or self-recorded donor footage; real-person donors transfer general motion only, never likeness.

## Template

`[Image1] controls product identity. [Video1] controls camera pace only. [Audio1] controls tempo only. Preserve the subject from [Image1]; do not copy characters, logos, music, voice, or environment from [Video1]/[Audio1].`

## Sequence Transfer Template

`[Video 1] is the accepted previous clip and controls only the actual opening state, camera phase, motion phase, ambience, and environment arrangement. @Image 1 controls canonical identity. Preserve both tags exactly. Do not copy unrelated identity, costume, logo, or future action from any reference.`

# Reference and continuity: keep each source in its role

These cards are authored concepts with no attached media. They teach reference authority, editorial order and a continuation boundary; they do not establish that an active surface supports a particular operation. Check the surface before choosing an input mode. A conceptual final frame or planned pose is never an accepted source.

Reference tokens shown here are teaching placeholders. Before using a conditional prompt, replace them in both its binding record and prose with the active surface's exact bound tokens, preserving the user's supplied spelling. Do not submit a literal placeholder or invent a binding; leave the prompt conditional if the actual asset or token is unavailable.

## Card: Borrow the steps, keep the new performer

**Evidence:** Concept; not generated or inspected.

**Brief:** Transfer a simple two-step rhythm to an original adult performer in a plain studio. Keep donor identity, wardrobe, setting and sound out of the new clip.

**Choice:** Borrow motion timing but hold the new camera still. Borrowing the donor camera too might preserve its staging but would make it harder to isolate the motion; choose the narrow role.

**Bindings:** Required; not attached. @Video1 must be an authorized, inspected motion donor that actually shows two sideways steps followed by a left pivot and raised right hand. It controls only that motion/timing; exclude face, costume, background, camera and audio. If the donor differs, rewrite the action to match the accepted source or choose another authorized source.

**Settings:** Video-reference mode only where the active surface supports motion guidance; plan a duration that fits the inspected donor phrase at normal speed. Model, tier and resolution are unselected.

**Why this direction:** Separating motion from identity and camera is intended to make the transfer request and its failure checks specific. An exclusion clause is not a guarantee against leakage.

**Conditional prompt:**

```text
Use @Video1 only for the timing of two sideways steps, a left pivot and a raised right hand. The new subject is an original adult performer in plain blue practice clothes in an empty cream studio. Do not transfer the donor's face, costume, setting, camera movement or sound. Hold a full-body eye-level view at normal speed. Keep the performer inside the frame and finish on the raised-hand pose. Soft overhead studio light. Sound: new footfalls and room tone only, no donor audio.
```

**Check:** Compare step order and timing with the inspected donor; separately check the new identity, clothing, room, camera and audio for leakage. Correct motion alone is insufficient acceptance.

**Fallback:** If role separation fails, offer a self-contained description of the selected steps or an approved motion-only preparation workflow. Either loses some donor specificity; do not silently upload a replacement or reuse an uncertain source.

## Card: Show the pour, then the settling surface

**Evidence:** Concept; not generated or inspected.

**Brief:** A two-shot editorial study of tea poured into one unbranded white cup. Show the action first, then its immediate result; no second pour or product claim.

**Choice:** Cut once from the serving action to the tea surface after the pour ends. A continuous move would retain uninterrupted space but make the surface detail harder to frame; choose the editorial contrast.

**Bindings:** None. T2V with an invented cup and setting. This is one conceptual two-shot request, not two independently generated clips with assumed continuity.

**Settings:** T2V; plan eight seconds total, first shot longer than the second. Verify whether the surface accepts the intended multishot request. Model, tier and resolution are unselected; prose shot order is not a guaranteed cut control.

**Why this direction:** Showing the pour before the surface gives the close-up a visible cause and prevents the second shot from repeating the action.

**Prompt:**

```text
Begin in a held medium side view of one white cup on a dark wooden table. A hand tilts a small brown teapot and pours tea until the cup is half full, then rights the teapot and moves it clear. Cut once to a close overhead view of that same half-full cup immediately after the pour. Hold as the surface ripples settle; do not pour again. Keep the cup, tea level and soft window light consistent across the cut. Sound: the pour ends before the cut, followed by quiet room tone.
```

**Check:** Exactly one pour precedes one cut; cup design and fill level agree across it; the second shot starts with settling ripples. Reject a restarted pour, new cup or unexplained time jump.

**Fallback:** If the cut or continuity fails, propose separate shots assembled in post. Bind the second shot to an accepted actual first-shot endpoint before generating it; do not claim two unrelated outputs match. More clips require remaining authorization.

## Card: Continue after the latch has lifted

**Evidence:** Concept; not generated or inspected.

**Brief:** Continue a workshop-door action after its latch has already lifted. The next beat is pushing the door open a hand's width; entering the room is reserved for later. The state below is a hypothetical teaching condition, not an observed result.

**Choice:** Continue from the approved actual final frame to preserve the hand and door relationship. Reconstructing the pose from text would allow a new angle but weaken the boundary; choose the accepted-frame continuation.

**Bindings:** Required; not attached. @Image1 must be the extracted actual final frame of an accepted prior clip, inspected to show a red-gloved right hand holding a raised brass latch on a still-closed wooden door. The source clip must show the camera already held still and its reviewed audio must end on a low ventilation hum, with no unfinished speech or music. @Image2 must be the authorized canonical identity/wardrobe reference; it controls those features only, not current pose. If picture, motion or audio differs, reconcile the observed state before drafting. Keep the source clip locator and acceptance review in the project record; do not invent either.

**Settings:** First-frame I2V continuation only on a surface supporting the required image roles; plan six seconds. This is a new continuation clip, not an assumed native extend endpoint. Model, tier and resolution are unselected. If multiple roles are unsupported, revise the reference plan before submission.

**Why this direction:** Using the actual accepted endpoint is intended to preserve what is already completed while giving the next clip one new action.

**Conditional prompt:**

```text
Start from @Image1, the accepted prior clip's actual final frame: the red-gloved right hand already holds the brass latch raised on the closed wooden door. Preserve that opening pose, door arrangement and held camera position. @Image2 controls canonical identity and wardrobe only; do not reset the pose from it. Keeping the latch raised, the hand pushes the door open one hand's width, then holds. Do not lift the latch again or enter the room. Preserve the source lighting. Sound: low ventilation hum under a short hinge creak, then the hum alone through the held endpoint; no speech or music.
```

**Check:** Compare the opening with the actual accepted frame; the latch does not relift, the glove and hand stay consistent, and the door opens only the intended distance. Check picture and audio across the join; a still frame does not itself supply prior ambience.

**Fallback:** If the join breaks, inspect the actual boundary and correct only the failed state or reference role. An image cannot carry sound: describe or use authorized audio separately when supported. Do not promote a repair plan to accepted footage, restart the latch action, or consume the reserved entrance beat.

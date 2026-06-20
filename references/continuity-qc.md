# Continuity QC

Use this reference before finalizing a sequence prompt and after reviewing a generated take.

## Hard-Fail Without Explanation

Do not silently change:

- canonical identity;
- wardrobe;
- product identity;
- product geometry;
- prop ownership;
- location;
- vehicle identity;
- persistent environment;
- exact reference tag;
- accepted completed beat status;
- parent clip lineage.

## Warn Unless Declared

Warn on unexplained changes in pose, frame position, screen direction, motion vector, camera phase, focus state, lighting phase, emotional state, ambience, music phase, or active dialogue.

Allow changes only when declared under transition, allowed changes, accepted deviation, intentional axis reset, or intentional next shot.

## Boundary Check

Before a successor prompt ships, verify:

- predecessor accepted status;
- successor `parent_clip_id`;
- predecessor `observed_end_state`;
- successor `planned_start_state`;
- completed beats excluded;
- future beats excluded;
- exact tags preserved;
- current prompt covers only current clip.

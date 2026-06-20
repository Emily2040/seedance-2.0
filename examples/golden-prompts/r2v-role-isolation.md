# Golden Prompt: R2V Role Isolation

## Source Brief

Use an image for identity, a video for camera rhythm, and audio for tempo.

## Internal Prompt Specification

Mode: R2V. `[Image1]` controls original character identity. `[Video1]` controls camera rhythm only. `[Audio1]` controls tempo only. Endpoint: character reaches the doorway.

## Compiled Natural-Language Prompt

[Image1] controls the original character identity and wardrobe. [Video1] controls camera rhythm only; ignore its performer, room, logo, and costume. [Audio1] controls tempo only; do not copy voice or song identity. The character walks toward the doorway in three steady steps as the camera matches the reference rhythm and stops when her hand reaches the handle.

## Lint Result

lint: pass

## Control-Critical Sentences

why this remains: `controls camera rhythm only` prevents video identity transfer.

why this remains: `ignore its performer, room, logo, and costume` states the non-transfer boundary explicitly.

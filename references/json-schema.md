# Seedance Prompt JSON Schema

Use this schema when the user wants structured output or when an automation pipeline needs stable fields.

```json
{
  "mode": "t2v | i2v | v2v | r2v | flf2v | edit | extend | audio-led",
  "duration": "string",
  "aspect_ratio": "string",
  "references": [
    {"tag": "Image1", "role": "identity | product | pose | environment | style | first_frame | last_frame | reference_image"},
    {"tag": "Video1", "role": "motion | camera | pacing | blocking | source_clip | reference_video"},
    {"tag": "Audio1", "role": "voice | rhythm | ambience | music | tempo | reference_audio"}
  ],
  "characters": [],
  "production": {
    "phase": "brief | preproduction | generation | review | post | localization | delivery",
    "role": "director | dp | producer | editor | colorist | sound | localization | qc",
    "delivery_surface": "web | broadcast | social | theatrical | client_review | archive",
    "approval_owner": ""
  },
  "shot_list": [
    {
      "shot_id": "S01_SH01",
      "purpose": "establish | reveal | demonstrate | emotional_turn | end_card",
      "shot_contract": "shot size, angle, lens feel, camera move, endpoint",
      "start_frame": "",
      "end_frame": "",
      "risks": []
    }
  ],
  "continuity_anchors": {
    "character": [],
    "product": [],
    "wardrobe": [],
    "props": [],
    "location": "",
    "screen_direction": "",
    "eyeline": "",
    "lighting_state": "",
    "audio_state": ""
  },
  "scene": "",
  "camera": "",
  "motion": "",
  "lighting": "",
  "style": "",
  "audio": "",
  "color_pipeline": {
    "look_intent": "",
    "working_assumption": "",
    "output_transform": "SDR Rec.709 | HDR PQ | theatrical | social",
    "show_lut_or_cdl_notes": "",
    "qc_notes": []
  },
  "subtitle_plan": {
    "subtitles": false,
    "sdh": false,
    "forced_narrative": false,
    "dubbing": false,
    "textless_required": false,
    "languages": []
  },
  "audio_deliverables": {
    "full_mix": true,
    "stems": [],
    "m_and_e": false,
    "loudness_target": "",
    "sync_cues": []
  },
  "delivery": {
    "frame_rate": "",
    "resolution": "",
    "aspect_ratio": "",
    "safe_area": "",
    "version_name": "",
    "qc_checks": []
  },
  "safety_notes": [],
  "final_prompt": ""
}
```

The JSON wrapper is for planning. The final prompt still needs to read naturally. For professional work, keep the production, shot-list, continuity, localization, audio, color, and delivery fields as handoff metadata; do not cram all of them into the prompt.

## Sequence-State Schemas

Version 6 adds machine-valid state fixtures under `schemas/`:

- `project-state.schema.json` for project state, story, beats, clip lineage, take history, canon revision, and reference registry.
- `clip-contract.schema.json` for the current clip production task.
- `take-review.schema.json` for observed start/end state, accepted deviations, completed beats, and rejection/repair verdicts.
- `prompt-spec.schema.json` for internal prompt compilation metadata.
- `generation-run.schema.json` for synthetic benchmark and local run records.

These schemas are planning artifacts. The final Seedance prompt remains natural language unless the user explicitly requests structured output.

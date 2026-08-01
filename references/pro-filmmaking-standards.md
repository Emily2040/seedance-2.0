# Professional Filmmaking Standards

last_verified: 2026-08-01

Reviewed 2026-08-01: unchanged. The standards here come from film-industry practice — shot lists, continuity, colour, audio post, localization, delivery QC — and are deliberately independent of which model generated the footage. A new Seedance line does not move them; that is the point of keeping them in a separate file from the platform facts.

Use this reference when Seedance work must support directors, cinematographers, editors, producers, localization teams, commercial agencies, or delivery/QC teams. Treat these standards as workflow guidance, not as a promise that a video-generation surface can render or export every technical deliverable directly.

## Source Boundaries

| Area | Preferred source type | Use in this skill | Boundary |
|---|---|---|---|
| Shot design | ASC, cinematography education, production shot-list practice | Translate creative intent into shot contracts. | Do not over-specify frame-perfect camera physics for short AI clips. |
| Continuity | Script supervision and production continuity practice | Track wardrobe, props, screen direction, eyelines, lighting state, and final-frame handoff. | AI continuity is probabilistic; use references and smaller shots for fragile anchors. |
| Color | ACES docs, AMF, delivery partner guidance | Track color intent, show look, LUT/CDL/LMT notes, HDR/SDR expectations. | A prompt can request a look; finishing must still be verified in color tools. |
| Aspect ratio | Delivery partner specs, DCI/ISDCF, platform specs | Separate creative framing from delivery containers and safe areas. | Do not assume every surface supports every ratio or crop. |
| Audio | ITU BS.1770, EBU R128, ATSC A/85, delivery partner mix specs | Plan dialogue, ambience, SFX, music, M&E/stems, loudness, and sync checks. | Seedance prompt audio is not a certified final mix. |
| Subtitles | Netflix timed text, WebVTT, accessibility and caption rules | Plan subtitles, SDH, forced narratives, reading time, placement, and localization notes. | Do not rely on generated burned-in text as final deliverable subtitles. |
| Delivery/QC | SMPTE IMF, DPP, Netflix delivery specs, DCI | Create preflight checks for frame rate, resolution, color, audio, captions, textless, metadata, and human QC. | Always follow the buyer/platform spec actually contracted for the job. |

## Professional Operating Spine

1. **Brief:** define client/creative goal, audience, territory, duration, aspect ratio, deliverables, references, rights, approval owner, and hard constraints.
2. **Pre-production:** create treatment, reference map, shot list, continuity ledger, color/audio/localization intent, and risk log.
3. **Generation plan:** split into stable shots. Assign one visible beat, one camera idea, and one endpoint per Seedance clip.
4. **Review loop:** evaluate identity, product, action, camera, continuity, audio sync, text, safety, and rights before extending or editing.
5. **Post plan:** edit, conform, stabilize, sound, color, captions, versioning, textless, and archival metadata.
6. **Delivery/QC:** check spec, naming, frame rate, resolution, color pipeline, loudness, captions, safe areas, rights notes, and human review.

## When To Load Detailed References

| User need | Load |
|---|---|
| Treatment, production plan, client brief, campaign | `shot-list-continuity.md`, `delivery-qc.md` |
| Camera, lens, shot size, blocking | `cinematography-shot-language.md` |
| Multi-shot continuity, scene handoff | `shot-list-continuity.md` |
| ACES, HDR/SDR, LUT/CDL/look language | `color-pipeline-aces.md` |
| 16:9, 9:16, 1.85, 2.39, social cutdowns | `aspect-ratio-delivery.md` |
| Dialogue, mix, stems, M&E, loudness | `audio-post-delivery.md` |
| Subtitles, dubbing, captions, forced narrative | `subtitles-localization.md` |
| IMF/DCP/social export, QC checklist | `delivery-qc.md` |

## Professional Answer Contract

For professional filmmaker requests, return:

- production phase and role: director, DP, editor, producer, sound, localization, or delivery;
- assumptions and source-date caveats for volatile platform claims;
- shot contract or workflow checklist;
- reference and rights map;
- continuity anchors;
- post/delivery notes when the output will leave the prompt stage.

Avoid giving only a final prompt when the user is asking for a film, commercial, campaign, localization package, or delivery-ready workflow.

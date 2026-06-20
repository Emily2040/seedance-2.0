# Quick Reference

## Default route

- Vague idea: `seedance-interview`.
- Clear idea: `seedance-prompt`.
- Long story or connected clips: `seedance-sequence`.
- Continue, extend, repair tail, or re-anchor accepted footage: `seedance-continuation`.
- Short prompt: `seedance-prompt-short`.
- Bad result: `seedance-troubleshoot`.
- IP or real-person risk: `seedance-copyright`.
- Blocked prompt: `seedance-filter`.
- Camera, light, motion, style, VFX, audio, or character-specific work: load the matching specialist sub-skill.

## Prompt checklist

| Gate | Pass condition |
|---|---|
| Mode | T2V, I2V, V2V, or R2V is explicit. |
| References | Each asset has exactly one primary role unless deliberately layered. |
| Subject | Main subject appears in the first clause and has stable tags if needed. |
| Action | One visible beat has an observable endpoint. |
| Camera | One primary move has start, speed, subject relationship, and endpoint. |
| Lighting | Source, direction, color, atmosphere, or transition is physical. |
| Audio | Dialogue, ambience, SFX, music, or silence is intentional. |
| Safety | Protected identity, IP, and unsafe wording are rewritten or authorization-gated. |
| Anti-slop | Hollow boosters are replaced by observable production language. |
| Budget | Final prompt fits the verified active-surface prompt budget. |
| Sequence lineage | Sequence prompts have `project_id`, `clip_id`, and parent when continuing. |
| Actual state | Continuations start from accepted observed state, not planned state. |
| Clip scope | Completed beats are excluded and reserved future beats stay out. |

## Fast repair phrases

| Failure | Add or replace with |
|---|---|
| I2V drift | `preserve [Image1] subject/product exactly; only motion, light, and camera change` |
| Generic look | `physical light source + material behavior + specific camera endpoint` |
| Camera chaos | `one controlled [move] from [start frame] to [end frame]` |
| Weak action | `actor + verb + timing + consequence + final state` |
| Lip-sync instability | `locked medium close-up, short quoted line, no head turn during dialogue` |
| Noisy VFX | `source + material + path + interaction + dissipation endpoint` |
| Style/IP risk | `medium + texture + palette + composition + motion rhythm` |
| Planned ending mismatch | `begin from the observed final frame: [actual visible state]` |
| Future beat leakage | `this clip stops at [endpoint]; do not show [reserved future beat] yet` |

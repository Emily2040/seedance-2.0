---
name: seedance-troubleshoot
description: 'Diagnose and fix Seedance 2.0 generation failures, quality issues, and content blocks using a pre-generation checklist and error-specific remedies. Use when generation fails, output is wrong aspect ratio, motion is chaotic, characters drift, audio desyncs, or a copyright filter triggers.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["troubleshoot", "qa", "debug", "openclaw", "antigravity", "gemini-cli", "codex", "cursor"]
metadata: {"version": "3.5.0", "updated": "2026-02-25", "openclaw": {"emoji": "🔧", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "parent": "seedance-20", "antigravity": {"emoji": "🔧", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "🔧", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-troubleshoot

Diagnose and fix Seedance 2.0 generation problems.

## Pre-Generation Checklist

- [ ] Prompt is plain text (no raw JSON)
- [ ] Subject + primary action in first 20–30 words
- [ ] Total files ≤ 12 (Rule of 12)
- [ ] Each image < 30 MB (JPG/PNG/WEBP)
- [ ] Videos: 3 clips total, **combined ≤ 15 s** (not 15 s each)
- [ ] Audio total ≤ 15 s MP3
- [ ] No real celebrity faces or brand logos
- [ ] No copyrighted character names (use archetypes)
- [ ] Duration within platform range (4–15 s; no confirmed mobile-specific cap)
- [ ] Aspect ratio declared (16:9 / 9:16 / 4:3 / 3:4 / 21:9 / 1:1)

---

## Error Lookup

### Output: chaotic / incoherent motion
**Cause**: prompt overloaded, competing actions.  
**Fix**: shorten to ≤ 50 words. Lock camera: `locked-off static camera`. One action per clip.

### Output: character drifting / inconsistent face
**Cause**: no reference image.  
**Fix**: upload character photo as `@Image1`. Add `maintain character identity from @Image1`.

### Output: camera wandering unintentionally
**Cause**: no camera instruction.  
**Fix**: add `locked-off static camera` or explicit movement (`slow push-in`, `dolly right`).

### Output: background morphing mid-clip
**Cause**: no environment anchor.  
**Fix**: add environment reference `@Image2`. Add `environment locked: [location]`.

### Output: audio desync / lip mismatch
**Cause**: audio too long, noisy audio, fast speech rate, or prompt motion tokens conflict with lip engine.  
**Fix**:
- Trim audio to < 10 s (10–15 s range is unreliable for sync).
- Remove ALL head/face motion tokens from prompt (nodding, turning, shaking).
- Slow speech recording to ~80% natural pace before uploading.
- Clean audio: remove background noise, reverb, and crowd sound before uploading.
- Add to prompt: `camera locked, neutral expression, lip-sync matches @Audio1 exactly`.
- See [skill:seedance-audio] → Failure Mode 2 for full diagnostic.

### Output: audio replaced / model rewrites uploaded audio (音频被乱改)
**Cause**: Seedance's generative audio engine overrides the reference when it detects sounds it can replicate, especially when competing motion tokens are present.  
**Fix (timestamp anchoring method — field-tested on Douyin)**:
- Add to prompt: `Audio @Audio1 plays exactly as uploaded from 0s to end. Do not modify or replace the audio content.`
- Remove all ambient/music/SFX tokens from the prompt (they invite audio generation).
- Reduce prompt complexity to under 50 words total.
- See [skill:seedance-audio] → Failure Mode 1.

### Output: no character detected / lip-sync not activating
**Note**: Master/Quick/Standard mode selection belongs to the Jimeng **Digital Human (数字人)** tool, which uses OmniHuman-1 — NOT Seedance 2.0 video generation. Do not mix the two.  
For Seedance 2.0 video generation:  
**Cause A**: Face reference image has multiple people — audio routing fails.  
**Fix**: Use single-person reference image in the character prompt. Include explicit lip-sync instruction.  
**Cause B**: Audio is wrong format (not MP3).  
**Fix**: Convert to MP3, 128–320 kbps, ≤15 s. Silent failure if wrong format.  
**Cause C**: Prompt has no lip-sync instruction.  
**Fix**: Add `lip-sync matches @Audio1 exactly` or explicit dialogue in quotes.

### Output: multi-character lip-sync — wrong or both characters broken
**Cause**: Officially confirmed open problem in Seedance 2.0. ByteDance's own release blog states: "Seedance 2.0 仍需继续解决多人口型匹配" (still needs to solve multi-person lip-sync matching). This is not a configuration error — it is an unresolved model limitation as of Q1 2026.  
**Fix**: Do not attempt two-character lip-sync in a single generation.
Use the separate generation + compositing pipeline:
1. Generate character A alone with A's audio segment
2. Generate character B alone with B's audio segment
3. Composite in CapCut/Jianying: PiP layout + linear mask (15–20% feather)
4. When A speaks: A layer = video / B layer = static image. Swap for B.
Full workflow: [skill:seedance-audio] → Multi-Character Lip-Sync Workaround.

### Output: lip-sync generation fails silently (no error, no sync)
**Cause**: Audio format is not MP3. WAV, AAC, OGG, FLAC, M4A all fail silently — no error message shown.  
**Fix**: Convert audio to MP3 (128–320 kbps, ≤15 s, ≤10 MB) before uploading. This is the #1 silent failure cause.

### Feature: voice cloning / Face-to-Voice not available
**Status**: Suspended Feb 2026 (ByteDance enforcement — privacy/copyright).  
**Fix**: Pre-record audio with desired voice, or use external TTS (ElevenLabs, Minimax TTS) to generate the voice, then upload that MP3. Do not reference voice clone features in prompts.

### Output: blocked / refused — IP / copyright
**Cause**: real face reference, brand name, copyrighted IP, or policy violation.  
**Fix**: remove real person references. Replace brand names with descriptors. Use original archetypes.  
**Post-Feb-15 note**: filter thresholds raised. Named franchise characters (Disney, Netflix, Paramount), named real actors, and anime character names now fail even with paraphrasing. Use full descriptor substitution from [skill:seedance-copyright].

### Output: blocked / refused — deepfake / likeness
**Cause**: face upload of real person; `replace face with [name]` pattern.  
**Fix**: ByteDance suspended real-person face uploads Feb 15. Upload original character art only. Remove any `face-swap` or `replace @Image1's face` language.

### API: release delayed / integration unstable
**Cause**: Feb 2026 copyright enforcement. Global API release was delayed from planned Feb 24 date.  
**Fix**: Do not build production integrations against Seedance API until ByteDance issues a new release schedule. For stable production, use WAN 2.2 or local OSS models as interim fallback. Poll ByteDance official channels for new date.

### Output: character falls into generic type
**Cause**: content filter stripping the specific character descriptor.  
**Fix**: verify descriptor does not contain any named franchise term. Check [skill:seedance-copyright] substitution table. Add more specific original design details (outfit, hair, scar pattern, body build).

### Output: wrong aspect ratio
**Cause**: platform default applied.  
**Fix**: state aspect ratio explicitly in prompt tail: `[16:9]` or set in platform UI before generating.

### Output: motion too slow / static
**Cause**: heavy style tokens suppressing motion.  
**Fix**: cut style tokens to 1–2. Add `dynamic motion`, `continuous movement`.

### Output: motion too fast / shaky
**Cause**: over-specified action frequency.  
**Fix**: add `smooth`, `stabilized`, `cinematic pace`. Reduce action density.

### Output: lighting inconsistent
**Cause**: no lighting anchor.  
**Fix**: load [skill:seedance-lighting]. Add single key-light descriptor: `soft side key`, `golden backlight`.

### Output: style inconsistent across chain
**Cause**: no style reference carried forward.  
**Fix**: re-upload first-shot frame as `@Image1` in each extension clip. Repeat style token.

### Output: extension breaks continuity
**Cause**: missing subject re-anchor.  
**Fix**: use extension formula: `Extend @Video1 by [X] s. [Re-upload @Image1 character]. New action: [desc].`

### API: status stuck at `processing`
**Cause**: timeout or server queue.  
**Fix**: poll at 5 s intervals. If no response after 120 s, cancel and retry with same seed.

### API: no endpoint available (2026-02-25 status)
**Cause**: Seedance 2.0 official API launch was delayed from Feb 24 due to copyright dispute. No public API exists as of this date.  
**Fix**: Use the Dreamina/Jimeng web platform (jimeng.jianying.com) for generation. For automated workflows, use third-party proxy APIs (AtlasCloud, APIYI) at your own risk — they are unofficial. Do not build production integrations until ByteDance announces an official API release date.

### API: 400 Bad Request
**Cause**: raw JSON in prompt field, or invalid parameter value.  
**Fix**: compile JSON to plain text. Check `duration` is integer within range, `aspect_ratio` is valid string.

---

## Compression Ladder (prompt budget exceeded)

Remove in this order — stop when within budget:

1. Remove filler phrases (`beautiful`, `amazing`, `stunning`)
2. Collapse environment to 3-word anchor (`misty mountain road`)
3. Cut style to 1 token (`cinematic` or `documentary`)
4. Drop SOUND layer entirely
5. Merge CAMERA + STYLE into single phrase
6. **Never cut**: SUBJECT · ACTION · @Tag assignments

---

## Quality Upgrade Checklist

| Symptom | Upgrade |
|---|---|
| Flat lighting | Add key light + rim light descriptor |
| Lifeless motion | Add verb specificity (`lunges`, `spirals`, `snaps`) |
| Generic look | Add 1 cinematographer / film reference token |
| No atmosphere | Add weather or particle effect (`dust motes`, `light fog`) |
| Weak audio | Load [skill:seedance-audio] → add ambient + sfx layers |

---

## Routing

Prompt construction errors → [skill:seedance-prompt]  
Camera / storyboard issues → [skill:seedance-camera]  
API / post-processing → [skill:seedance-pipeline]  
Character consistency → [skill:seedance-characters]  
Audio issues → [skill:seedance-audio]

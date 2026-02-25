---
name: seedance-20
description: 'Generate and direct cinematic AI videos with Seedance 2.0 (ByteDance/Dreamina/Jimeng). Covers text-to-video, image-to-video, video-to-video, and reference-to-video workflows with @Tag asset references, multi-character scenes, audio design, and post-processing. Use when making AI video, writing Seedance prompts, directing a scene, fixing generation errors, or building an AI short film, product ad, or music video.'
license: MIT
user-invocable: true
user-invokable: true
tags: ["ai-video", "filmmaking", "bytedance", "seedance", "multimodal", "lip-sync", "openclaw", "antigravity", "gemini-cli", "firebase", "codex", "cursor", "windsurf", "opencode"]
metadata: {"version": "3.6.0", "updated": "2026-02-25", "openclaw": {"emoji": "🎬", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "antigravity": {"emoji": "🎬", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "gemini-cli": {"emoji": "🎬", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "firebase": {"emoji": "🎬", "homepage": "https://github.com/Emily2040/seedance-2.0"}, "author": "Emily (@iamemily2050)", "repository": "https://github.com/Emily2040/seedance-2.0"}
---

# seedance-20

Seedance 2.0 quad-modal AI filmmaking (T2V · I2V · V2V · R2V).

Start: [skill:seedance-interview] — reads story/script, asks gap-fill questions, outputs production brief.

> **⚠️ Feb 2026 Status**: Seedance 2.0 API global release was delayed (from planned Feb 24) due to copyright enforcement actions by Disney, Paramount Skydance, Netflix, MPA, and SAG-AFTRA. ByteDance paused real-person face uploads Feb 15. Content filters for named franchise characters, anime IPs, and streaming originals have been tightened. The [skill:seedance-copyright] module reflects the current post-enforcement state. Run it before every generation.


## Platform Compatibility

| Platform | Install path | Scope |
|---|---|---|
| **Antigravity** | `.agent/skills/seedance-20/` | workspace |
| **Gemini CLI** | `.gemini/skills/seedance-20/` | workspace |
| **Firebase Studio** | `.idx/skills/seedance-20/` | workspace |
| **Claude Code** | `.claude/skills/seedance-20/` | workspace |
| **OpenClaw / ClawHub** | `.claude/skills/seedance-20/` | workspace |
| **GitHub Copilot** | `.github/skills/seedance-20/` | workspace |
| **Codex** | `.agents/skills/seedance-20/` | workspace |
| **Cursor** | `.cursor/skills/seedance-20/` | workspace |
| **Windsurf** | `.windsurf/skills/seedance-20/` | workspace |
| **OpenCode** | `.opencode/skills/seedance-20/` | workspace |

### One-liner installs

```bash
# Antigravity / Gemini CLI / Firebase Studio
antigravity skills install https://github.com/Emily2040/seedance-2.0
gemini skills install https://github.com/Emily2040/seedance-2.0
# Claude Code / OpenClaw
claude skills install https://github.com/Emily2040/seedance-2.0
# Codex
codex skills install https://github.com/Emily2040/seedance-2.0
# Cursor
cursor skills install https://github.com/Emily2040/seedance-2.0
# Windsurf
windsurf skills install https://github.com/Emily2040/seedance-2.0
# OpenCode
opencode skills install https://github.com/Emily2040/seedance-2.0
```

## Skills

**Core pipeline**
[skill:seedance-prompt] · [skill:seedance-camera] · [skill:seedance-motion] · [skill:seedance-lighting] · [skill:seedance-characters] · [skill:seedance-style] · [skill:seedance-vfx] · [skill:seedance-audio] · [skill:seedance-pipeline] · [skill:seedance-recipes] · [skill:seedance-troubleshoot]

**Content quality**
[skill:seedance-copyright] · [skill:seedance-antislop]

**Vocabulary**
[skill:seedance-vocab-zh] · [skill:seedance-vocab-ja] · [skill:seedance-vocab-ko] · [skill:seedance-vocab-es] · [skill:seedance-vocab-ru]

## References

[ref:platform-constraints] · [ref:json-schema] · [ref:prompt-examples] · [ref:quick-ref]

## Version history

| Version | Date | Changes |
|---|---|---|
| 3.3.0 | 2026-02-25 | Rewrote seedance-interview v4.0: A/B/C/D/E guided stages, 5-flow types (image/video/audio/one-liner/script), 3-option prompt output, language selection |
| 3.2.1 | 2026-02-25 | **Accuracy corrections**: removed negative-prompt support claim (not supported), corrected API availability (no public API yet), fixed aspect ratios (added 3:4 and 21:9), fixed video input limit (15s combined not per-file), removed mobile-only duration claim |
| 3.1.0 | 2026-02-25 | Added copyright, antislop, vocab-ja/ko/es/ru modules. 24 files. |
| 3.0.0 | 2026-02-25 | Initial 12-skill core pipeline. |

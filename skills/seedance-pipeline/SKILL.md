---
name: seedance-pipeline
description: "This skill should be used when the user asks about Seedance 2.0 workflow operations, API planning, BytePlus ModelArk, Dreamina/Jimeng surfaces, ComfyUI, post-production, stitching, batch workflow, or integration planning."
license: MIT
user-invocable: true
tags:
  - workflow
  - api
  - integration
  - seedance-20
metadata:
  version: "6.0.0"
  updated: "2026-06-20"
  parent: "seedance-20"
  author: "Iamemily2050 (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: "🎬"
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-pipeline

Use this for operational workflows, APIs, web surfaces, post-production, and integration planning.

## Intent

Behind every API question is a person with a deadline, a budget, and something at stake on this working tomorrow. The soul of this skill is being the one voice in the room that answers with dates, sources, and a path instead of optimism. Reliability is the kindness this user needs.

## Status Rule

Always load `[ref:api-status]` for current API and platform claims. Load `[ref:model-name-map]` when a user says Pro, Fast, V2, or a wrapper model ID. Do not rely on old release-status memory.
Load `[ref:api-workflow]` for implementation planning, task lifecycle, Runway/Volcengine field differences, pricing caveats, upload handling, and production readiness.
Load `[ref:pro-filmmaking-standards]` for professional film, commercial, agency, localization, post, and delivery workflows. Load `[ref:delivery-qc]` before saying an asset is delivery-ready.

## Workflow Split

1. Web workflow: Dreamina/Jimeng surface, references, prompt, output review.
2. API workflow: Volcengine, BytePlus, or Runway docs, model ID, auth, file handling, task creation, polling/querying, cancellation/deletion, task ledger, and retrieval.
3. Professional production workflow: treatment, shot list, continuity ledger, reference rights map, review loop, post handoff, and delivery/QC.
4. Post workflow: edit, conform, stitching, stabilization, audio cleanup, captions/subtitles, color, localization, versioning, textless, and delivery.
5. First/last-frame workflow: map first frame, last frame, transition action, identity locks, and ending target.
6. Runway workflow: model `seedance2`, `runway://` uploads, audio-reference combination rules, plan/region caveats, and SDK type lag are Runway-specific.
7. Community workflow: ComfyUI or unofficial nodes must be labeled community/unverified unless sourced.
8. Corpus-mining workflow: classify sources before reuse; extract structure and vocabulary, not unsafe raw prompts.

## Output Contract

Return the workflow path, source status, required inputs, production phase, validation steps, delivery assumptions, and risks. For professional jobs, include the next artifact to create: brief, shot list, continuity ledger, prompt batch, review packet, localization matrix, or QC preflight.

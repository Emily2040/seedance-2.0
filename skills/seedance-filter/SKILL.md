---
name: seedance-filter
description: "This skill should be used when a Seedance 2.0 prompt is blocked or rejected, when moderation is a suspected cause of a problem, or when the user asks for a content-boundary review or safer alternative. Assess the actual request before offering a clarification."
license: MIT
user-invocable: true
tags:
  - content-filter
  - safe-rewrite
  - seedance-20
metadata:
  version: "6.7.0"
  updated: "2026-08-01"
  parent: "seedance-20"
  author: "Iamemily2050 (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: "🎬"
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-filter

Before producing prompt text, a prompt-ready block, a rewrite, an example, or a compiled clip, load the [Director's Read](../../references/directors-read.md), classify the brief, and complete its canonical narrative or non-narrative record. Translate that record into visible or audible carriers and keep its internal labels out of final generation prose.

## Intent

Assess the actual scene and available rejection information before proposing a rewrite. Keep legitimate creative intent clear without assuming that every rejection is a false positive or every output defect is moderation.

## Boundary — read before anything else

This skill clarifies benign requests; it does not disguise prohibited content or help bypass safety systems. Evaluate the underlying request and relevant context, including age, consent, identity, rights and harm. Do not invent those facts or infer a content violation from a topic word alone. If the underlying request is prohibited, refuse plainly and offer a legitimate alternative only where one exists.

## Repair Method

1. Identify the requested scene, its must-haves and the actual error or rejection information available. Separate the provider's stated reason, the user's report and an unverified hypothesis. Leave the cause unknown when the evidence does not establish it.
2. Assess the underlying content. Ask only for missing context that materially affects the boundary or requested output; do not turn a complete benign brief into another interview.
3. For an ambiguous phrase with a known benign meaning, clarify that meaning faithfully. Preserve exact dialogue, reference tokens, authorized roles, sound, framing and settings unless their revision was requested.
4. If a proposal removes or replaces content, describe that change and offer it as an alternative, or draft within the user's already delegated scope. Do not label a different scene an equivalent wording repair or claim that adding “prop”, “original” or “authorized” establishes those facts.
5. Do not promise acceptance or submit repeated synonym probes. A text revision is not authorization for an upload, retry, provider change or spending. Follow the user's budget and [retake protocol](../../references/retake-protocol.md).

## Boundary Rule

When context is uncertain, state what is unresolved. When content is prohibited, refuse or offer a legitimate alternative rather than disguising it. Do not provide filter-bypass, evasion or hidden-word tactics. A language change does not change the underlying content.

Face-limit or portrait-verification workarounds are not safe prompt tricks. If a surface offers sanctioned virtual portrait, trusted model-output, or authorization asset flows, route the user to those current official paths instead of evasion language.

Load [filter-vocab](../../references/filter-vocab.md) for conditional wording examples and clearly labeled content alternatives. Load [multilingual-community-examples](../../references/multilingual-community-examples.md) only when a benign clarification needs those language patterns; do not treat them as evidence of acceptance or permission.

## Output Contract

Return the relevant observation or stated rejection reason, any unresolved hypothesis, and a faithful clarification or explicitly labeled alternative when appropriate. Explain material changes and any remaining boundary. Keep copyable text separate from those notes and do not describe an unsubmitted draft as approved.

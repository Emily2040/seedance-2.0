# V7 stack: independent integration review

**Reviewed:** 2026-07-25 · **Subject:** the unmerged V7 branch stack (PRs #78–#88)
**Real tip:** `agent/v7-audio-multishot-v2` @ `512b5fe` — 25 commits ahead of `main`, 297 files, +56,325 / −1,343
**Verdict:** the research is sound and the engineering is strong, but the stack is **not mergeable as-is**. One mechanical blocker (CI is red today) and one strategic blocker (incomplete + duplicated contract surface). Both are fixable without discarding the work.

> **Remediation status.** Of the P0 findings that apply to `main` — §3 and §6 item 0 — two parts are **on `main` now**: the wall-clock staleness gate no longer fails pull-request validation, and `--enforce-freshness` blocks a stale registry in the release checklist. A **weekly scheduled review job is not on `main`**; it ships in a companion pull request, and until that merges there is no automated alert between releases. The findings about the V7 stack itself (§6 items 1–10) are **not implemented**; they have to land on `agent/v7-audio-multishot-v2`, where those files live. Dates and failure counts below are as observed on 2026-07-25 and are kept as a point-in-time record rather than rewritten, because they are the evidence for the conclusions.

---

## 1. What was actually built

Ten feature PRs (V7-01 … V7-10) landing an *evidence control plane* and a *typed surface-binding pipeline*:

| Area | Added |
|---|---|
| Evidence registry | `research/evidence/` — 6 sources, 6 captures, 17 claims, authorities, release policy, runtime map |
| Surface profiles | `profiles/` — model profile + 3 surface profiles (BytePlus, fal, Volcengine) |
| Contracts | 38 new JSON Schemas + 33 validation fixtures |
| Tooling | 22 new scripts, `tools/evidence_registry.py`, `tools/runtime_package.py` |
| Tests | **6 → 489 tests**; CI steps **17 → 40**, plus a 3-OS × 2-Python portability matrix |

---

## 2. Verification performed

Everything below was executed, not read.

- Installed `requirements-validation.lock` under CPython 3.12 (matches CI) — clean, hash-verified.
- Replicated all 40 steps of the `validate` job locally.
- Ran the full 489-test suite.
- Bisected the failure to an exact calendar date.
- Cross-checked against GitHub Actions run history.

---

## 3. The blocking finding: CI is a time bomb, and it has already detonated

**33 of 40 CI steps pass. 7 fail. 13 of 489 tests fail. 100% of the failures share one root cause: evidence TTL expiry.**

```
FAILED: evidence_registry --enforce-freshness      FAILED: source_registry_check
FAILED: profile_check                              FAILED: render_surface_bindings --self-test
FAILED: test_surface_bindings                      FAILED: unittest discover (13 failures)
FAILED: test_semantic_lint + test_prompt_compile
```

Every failure message is the same class:

```
fal.binding.at-ordinal: evidence expired at UTC date 2026-07-18
binding-render error: PROFILE_EVIDENCE_EXPIRED at /profile_id
```

### Proof that nothing but the calendar changed

| Evidence | Result |
|---|---|
| GitHub Actions, commit `512b5fe`, 2026-07-13 | **success** |
| Same commit, run locally 2026-07-25 | **failure** |
| `evidence_registry --as-of 2026-07-17` | **passes** |
| `evidence_registry --as-of 2026-07-18` | **fails** |

The renderer itself is provably correct and deterministic — only the date gates it:

```
2026-07-17: OK      -> '@Image1 controls product geometry.'  expires=2026-07-18
2026-07-25: BLOCKED -> PROFILE_EVIDENCE_EXPIRED
```

### Why it happened

`TTL_LIMITS["api_field"] = 7`. Six claims were verified 2026-07-11 and expired 2026-07-18. A **7-day TTL** means a human must re-verify provider documentation *every week, forever*, or the repository goes red. That is not an operable policy.

The remaining claims (30-day TTL) **expire 2026-08-10**. Fixing only the six expired claims buys 16 days.

### Impact on `main` — and the same bug is already there

`main` has no `research/` or `tools/` directory, so it cannot fail from *evidence* expiry. But **`main` is already red for the same underlying reason**, discovered when this review's own PR ran CI:

```
Source registry errors:
- source-registry.md last_verified is 35 days old
```

`scripts/source_registry_check.py` hard-fails when `references/source-registry.md`'s `last_verified` is more than 30 days old. It reads `2026-06-20`, so `main` went red on **2026-07-21** and has been red for four days. Verified by running the check on a pristine `main` checkout — it is not caused by any change in this branch.

So the time-bomb pattern is **not a V7 invention**. V7 inherited it and amplified it: 30-day wall-clock staleness on `main` became a 7-day TTL enforced across six tools. Merging V7 today would add a second, faster-firing instance of a failure mode the repository already has.

**This also exposes the perverse incentive.** The cheapest way to make either gate green is to edit the date — to assert that sources were re-verified when nobody looked at them. A gate whose easiest fix is falsifying the evidence record actively undermines the honesty the evidence registry exists to protect. That date should not be bumped without a real re-verification pass.

### Root design error

Freshness — a *monitoring* concern — was wired into *build correctness*. The two are separable, and the repo already has the right mechanisms for both:

- `tools/evidence_registry.py --release` **independently blocks on `:expired`** (line ~1453).
- `.github/workflows/evidence-freshness.yml` already runs daily and opens a draft review PR.

So removing `--enforce-freshness` from PR CI **loses no safety whatsoever**. Release is still gated; humans are still alerted.

A second, narrower error: the tools hard-fail on expiry **even in `--preview-candidate` offline mode**. Preview exists precisely to exercise a disabled candidate profile with no provider contact; blocking it on staleness conflates "too old to act on" with "too old to test".

---

## 4. What is genuinely good — keep all of it

1. **The core research finding is real and it corrects a live bug in `main`.** Reference binding is *surface-specific*, not universal:
   - fal → `@Image1` · Volcengine → `图片1` · BytePlus → spaced `@Image 1`, example-scoped only.

   `main` treats `@Image1` as universal across 367 occurrences. That is wrong for Volcengine and unproven for BytePlus.

   **This does not contradict the @-tag migration in PRs #74/#76.** For fal, the V7 renderer emits exactly `@Image1`. What V7 corrects is the *universality assumption*, and it does so without making guidance vague — `references/surface-prompt-profiles.md` gives concrete per-surface tokens and a worked example. The 53 surviving `@`-tags are correctly scoped to archived originals, fixtures, and fal-specific examples. **This is a well-executed correction, not a regression.**

2. **Evidence architecture.** Claims → sources → captures with sha256 pinning, TTL by claim class, lineage roots, criticality, and — unusually — claims bound to their affected tests via `path#exact-id`, *validated to actually resolve*.

3. **Rights posture.** Captures retain bounded paraphrases plus structural locators, never the provider document, with an explicit `rights_note`. Legally careful.

4. **Fail-closed discipline.** Unknown profile fails; missing formatter fails; candidate profiles require explicit `--preview-candidate`; and a test asserts the renderer exposes **no `--as-of` flag** so the clock cannot be spoofed from the CLI.

5. **Supply-chain hygiene, better than most production repos.** Actions pinned to SHAs, `--require-hashes` lockfile, `persist-credentials: false`, least-privilege tokens, base64+sha256 handoff between jobs, `--force-with-lease`, bot-authorship assertions, and path allowlisting on the automation branch.

6. **Test quality.** Determinism across 10 fresh processes and 10 `PYTHONHASHSEED`s, metamorphic tests, and a dependency-free (`python -S -B`) runtime boundary enforced on 3 OSes × 2 Python versions.

7. **Honest debt reporting.** `--release` surfaces 11 blockers including 81 `legacy_blocked` files instead of hiding them, and the migration doc states plainly: *"It is not a V7-04 exit criterion to make the release gate green."* That is rare discipline.

---

## 5. The other real problems

### 5.1 v1/v2 duplication of contracts that never shipped

| Contract | v1 created | v2 created |
|---|---|---|
| `scene-ir` | 2026-07-12 | 2026-07-13 |
| `prompt-render` | 2026-07-13 | 2026-07-13 |
| `surface-binding-set` | 2026-07-13 | 2026-07-13 |
| `prompt-program` | 2026-07-13 | 2026-07-13 |

Three pairs were created **the same day**; `scene-ir` was superseded **one day** after being written — on a branch that has never shipped. Versioning exists to protect existing consumers. There were none.

The paired scripts are independent forks, not layers — `semantic_lint_v2.py` does **not** import `semantic_lint.py`:

```
semantic_lint.py=1442   semantic_lint_v2.py=769   ~18% verbatim duplication
prompt_compile.py=1555  prompt_compile_v2.py=396  ~25% verbatim duplication
scene_ir_check.py=701   scene_ir_v2_check.py=996  ~22% verbatim duplication
```

Both halves are wired into CI, so every future change costs double.

### 5.2 Golden fixtures byte-pin the toolchain source

`validation/fixtures/prompt-render.valid.json` embeds `compiler_toolchain_sha256`, computed over **five** script files. Editing a comment in any of them invalidates the fixture. Combined with 5.1, routine maintenance is very expensive.

### 5.3 The integration branch integrates nothing

`v7-integration` contains only PR #78 — **2 commits**, 24 behind the real tip. PRs #79–#88 were merged *backwards* (child branch → parent branch), so the newest work accumulated on `agent/v7-audio-multishot-v2` instead. `agent/v7-frontend-design-system-v2` is a stale duplicate pointer to `agent/v7-evaluation-coverage-v2`.

### 5.4 The stack is 10 of 12 steps complete

V7-11 (frontend rebuild) and V7-12 (activation/release) were never started. Until V7-12, every profile is `runtime_enabled: false` and `activation_enabled: false` — **the work is inert by design and delivers no user-visible value yet.**

### 5.5 The root of trust is a human paraphrase

Captures are researcher-written paraphrases. The sha256 proves the paraphrase has not been *edited since* — not that it faithfully reflects the source. `raw_document_sha256` cannot recover this, because the raw document is deliberately not retained and provider pages change constantly, so the hash will nearly always mismatch on re-fetch. The cryptographic rigor sits *downstream* of an unverifiable step, which risks conveying more confidence than the evidence supports.

### 5.6 Lockfile is Linux/CPython-3.12 only

`rpds-py` is pinned to a single compiled-wheel hash, so `--require-hashes` install fails on macOS or Python 3.11 (confirmed). Documented in the file header, but it blocks local contribution.

---

## 6. Recommendations, in priority order

**P0 — unblock CI (no safety lost)**

0. ~~**Fix `main` first, independently of V7.**~~ **Implemented.** `source_registry_check.py` had `main` red since 2026-07-21. The >30-day staleness condition is now a warning by default, with `--enforce-freshness` preserving the hard failure in the release checklist. A weekly scheduled job that asks the question between releases is a separate pull request and is **not yet on `main`**. The adjacent drift check stays fatal because it compares two checked-in dates and is reproducible on any day. `last_verified` was deliberately **not** bumped — that would assert a re-verification that did not happen.
1. Drop `--enforce-freshness` from `validate-skills.yml`. Structural validation stays; `--release` still blocks on `:expired`; the daily workflow still raises the review PR.
2. Make expiry non-fatal under `--preview-candidate`; stamp `evidence_expired: true` into the output, which already carries `preview` and `evidence_expires_at`. Keep the hard fail for activation.
3. Pin `today` inside the `_self_test()` paths so self-tests are hermetic. The functions already thread a `today` parameter end-to-end — the self-tests simply don't pass it. Negative tests already pin their dates and are unaffected.
4. Raise `api_field` TTL from 7 days to 30–90, or reclassify these claims. Weekly manual re-verification is not sustainable.

**P1 — before merge**

5. Collapse every v1/v2 pair. Nothing shipped, so evolve v1 in place and delete the forks. Roughly halves the schema, script, and test surface.
6. Fast-forward `v7-integration` to `agent/v7-audio-multishot-v2` (or cut a fresh integration branch) and delete the stale pointer branches.
7. Re-verify the six expired fal/Volcengine claims against live first-party docs and record successor claims per the documented refresh procedure.

**P2 — strategic**

8. Either commit to V7-11/V7-12, or descope: land the evidence registry + surface profiles as one reviewed PR — that is the high-value, low-risk core — and defer the rest.
9. Add a fixture-regeneration script to offset the toolchain byte-pinning friction.
10. Document explicitly that captures are paraphrases, and record a reviewer attestation per capture so the paraphrasing step is auditable.

---

## 7. Bottom line

The V7 stack is **high-quality work built on a correct and valuable insight**. The evidence registry, surface profiles, fail-closed posture, and CI hygiene are all above the bar for most production repositories, and the finding that reference binding is surface-specific is a genuine correction to `main`.

It should not be merged today. Recommended path: apply P0 (about half a day, mechanical), then P1.5 — collapse the v1/v2 duplication — then merge the evidence registry and surface profiles as a single reviewed PR, leaving activation to a later, deliberate change.

The single most important lesson: **freshness policy must never gate build correctness.** A test that passes on Monday and fails on Saturday with no code change is not a test — it is a scheduled outage.

That lesson applies to the repository as a whole, not just to V7. When this review was written `main` had been red since 2026-07-21 for exactly this reason — before the review began, and unrelated to V7. **That half is now fixed**: staleness no longer gates per-pull-request validation, and enforcement moved to the release checklist. Scheduled monitoring between releases is a separate pull request still in flight.

What remains is the V7 half. The stack did not invent the pattern; it inherited it and made it fire four times faster, across six tools instead of one. Fixing it there is §6 items 1–4.

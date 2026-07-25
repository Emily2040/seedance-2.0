# Security Policy

## Scope

Seedance 2.0 Skill OS is an **offline agent-skill and reference package**: Markdown skill/reference files plus deterministic local Python validation scripts. It is not a hosted service, an API wrapper, or a runtime that executes on its own. It stores no credentials and ships no telemetry.

One script is an exception and is called out below: `scripts/eval_run.py` is a development-only evaluator that contacts a model provider and reads a credential from the environment. It is not part of the installed skill, and no skill or reference file invokes it.

## Reporting a vulnerability

Please report suspected vulnerabilities privately rather than in a public issue:

- Use GitHub's **private vulnerability reporting** on this repository (the **Security** tab → **Report a vulnerability**).

Include what you found, where, and how to reproduce it. We aim to acknowledge reports within a reasonable time and will credit reporters who want it once a fix ships.

## Security posture of this package

- **No telemetry, and no network calls from anything you install.** The skill content is text. Every script the CI gate runs is a deterministic, offline validator that needs no credentials — read them before running.
- **One development-only exception, and it is live by default.** `scripts/eval_run.py` sends eval prompts to `https://api.anthropic.com/v1/messages` and reads `ANTHROPIC_API_KEY` from the environment. Running it with no arguments performs live calls; `--self-test` is the offline wiring check, and it is the only mode CI runs. It honours `HTTPS_PROXY` and `SSL_CERT_FILE`. Nothing in `skills/` or `references/` invokes it, so installing the skill never causes a network call.
- **Evaluator output carries model-derived text.** A live run prints each case's verdict to the console and, with `--ledger`, writes a table of scores plus truncated judge notes. Full prompts and full model responses are held in memory and are not written to disk, but the notes are model output, so review a ledger before sharing or committing one. The credential is never serialised: it travels in a request header and is written nowhere. `eval-runs/` is ignored so ad-hoc output cannot be committed by accident.
- **No secrets in the repo.** API keys, account cookies, and private prompt corpora are never stored here (see `references/agent-compatibility.md`). Do not add them in a fork or PR.
- **CI validates structure, not just prose.** Every push and pull request runs the checks in `.github/workflows/validate-skills.yml`.

## Using this skill safely inside an agent

This package is only as safe as the **agent client** you load it into. The skill itself does nothing on its own; the agent that reads it can do whatever that agent is allowed to do. Treat the agent — not this skill — as your trust boundary.

- **Install only into agent clients you trust** and keep them updated. Do not install into unknown or unvetted agents just because they accept the skill format.
- **Never paste secrets into an untrusted agent.** This skill never asks for API keys, tokens, account cookies, or private/client footage. If an agent — or a modified copy of this skill — asks for them, stop.
- **Prefer clients that sandbox or scan skills on install** (for example, Hermes runs a security scan on `hermes skills install`). Verify install paths in your own client; the cross-agent matrix in `references/agent-compatibility.md` is labeled "verify in your client," not a guarantee.
- **Review before you load.** Any skill from any source is Markdown that an agent will read as instructions. Review third-party skills — including forks of this one — before loading them into a privileged agent; prompt-injection-style text can hide in innocent-looking docs.
- **Keep the content boundaries.** The `seedance-copyright` and `seedance-filter` skills rewrite unsafe requests into safe, original equivalents and repair false-positive filtering by clarifying legitimate production context. They are not tools to defeat any platform's safety systems — do not use this package to evade provider moderation.

## What this project will not do

- It will not add telemetry, network calls, or credential prompts to the installable skill or to any script on the CI gate. Development-only network tools must stay excluded from the package, explicit about when they transmit, and documented here.
- It will not claim that every agent client can install directly from the repository URL, or that any registry lists this skill unless it has actually been published there.

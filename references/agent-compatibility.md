# Agent Compatibility

last_verified: 2026-06-12

Use this file when reviewing whether this repository is shaped correctly as an Agent Skill package. This is about packaging and agent behavior, not Seedance model capability.

## Current Agent-Skill Shape

Codex's current Agent Skills documentation describes a skill as a directory with a required `SKILL.md` file plus optional `scripts/`, `references/`, `assets/`, and `agents/` folders. It also describes progressive disclosure: the agent sees the name, description, and path first, then loads the full `SKILL.md` only when the skill matches the task.

This repository follows that pattern:

| Agent-skill expectation | Repository location | Status |
|---|---|---|
| Root skill metadata and routing | `SKILL.md` | Present |
| Task-specific sub-skills | `skills/*/SKILL.md` | Present |
| Dense reference material | `references/*.md` | Present |
| Validation and maintenance scripts | `scripts/*.py` | Present |
| README-facing visual resources | `assets/*` | Present |
| Codex UI metadata | `agents/openai.yaml` | Present |
| Behavioral evals | `evals/evals.json` | Present |
| CI validation | `.github/workflows/validate-skills.yml` | Present |
| Local Codex installer | `scripts/install_codex_skill.py` | Present |

## Compatibility Rules

- Keep every active `description` in third-person activation wording so tools can match it from a shortened skill list.
- Keep the root `SKILL.md` small. Route to sub-skills and references instead of copying long tables into the root.
- Keep volatile facts in dated references such as `api-status.md` and `source-registry.md`.
- Keep generated bitmap images inside `assets/` if they are referenced by README.
- Keep `agents/openai.yaml` aligned with the root skill name and make the default prompt invoke `$seedance-20`.
- Use `scripts/install_codex_skill.py --force` to install or refresh the local user-level Codex copy at `$CODEX_HOME/skills/seedance-20` or `~/.codex/skills/seedance-20`.
- Keep scripts deterministic and local. They should validate structure, schema, design, and source metadata without requiring private credentials.
- Do not store API keys, account cookies, or private prompt corpora in the skill package.

## Cross-Agent Matrix

Verified 2026-06-12 from each agent's public docs; install paths are volatile - recheck the active client before promising behavior. Install this repository as ONE root skill (`seedance-20`); sub-skills and references load by relative path from the root.

| Agent | Skills location | Install route | Notes |
|---|---|---|---|
| Claude Code / claude.ai | `.claude/skills/` (workspace), managed skills | copy or marketplace | Origin platform of the SKILL.md shape. |
| Codex | `.agents/skills/` upward scan + user/system dirs | `scripts/install_codex_skill.py --force` | `agents/openai.yaml` supplies UI metadata. |
| Google Antigravity | `.agents/skills/` (workspace), `~/.gemini/antigravity-cli/skills/` (global) | copy the folder, restart the session | Same directory convention as Codex workspaces; SKILL.md + scripts/references/assets shape matches this repo. |
| OpenClaw | workspace `skills/`, `~/.openclaw/skills/` (global) | `openclaw skills install` (git/local expect `SKILL.md` at source root - this repo qualifies) | ClawHub is the public registry (`clawhub` CLI to publish). Every skill here already carries `openclaw:` metadata. |
| Hermes Agent (Nous Research) | project `skills/`, `~/.hermes/skills/` | `hermes skills install` (runs a security scan) | Activates on the frontmatter `description` - this repo's third-person activation wording is exactly what it matches. |
| Gemini CLI / Cursor / Windsurf / Copilot | `.gemini/`, `.cursor/`, `.windsurf/`, `.github/` + `skills/` | copy the folder | Treat as installation targets, not separate source trees. |

## Chinese-ecosystem agents (verified 2026-07-06)

Both clients implement the same Agent Skills open standard (`SKILL.md` folder, on-demand progressive disclosure) as the rest of this matrix, so this repository installs into them as the single `seedance-20` root skill. Verified 2026-07-06 from each project's public docs; install paths stay volatile, so recheck the active build.

| Agent | What it is | Skills location | Install route |
|---|---|---|---|
| Trae (ByteDance) | AI IDE from ByteDance, the same company as Seedance 2.0 | `.trae/skills/` (project); managed under Settings -> Rules & Skills | Copy the folder as `seedance-20`; the SKILL.md loads on demand. A Trae MCP connector to Seedance, if used, is a separate surface from this skill package. |
| Qwen Code (Alibaba) | Open-source terminal agent forked from the Gemini CLI line | `.qwen/skills/` (project), `~/.qwen/skills/` (personal) | Copy the folder as `seedance-20`; each skill needs a SKILL.md. The `/skills` command lists installed skills. |

## More Agent-Skills clients (verified 2026-07-06)

`.agents/skills/` is emerging as the shared cross-agent convention: Codex, Google Antigravity, OpenCode, Amp, and Goose all read it, so one install under `.agents/skills/seedance-20/` serves them together, and `.claude/skills/` is read by several as a compatibility path. Verified 2026-07-06 from each project's public docs; paths stay volatile, so recheck the active build.

| Agent | What it is | Skills location | Notes |
|---|---|---|---|
| OpenCode | Open-source terminal coding agent | `.opencode/skills/` (project), `~/.config/opencode/skills/` (personal) | Also reads `.claude/skills/` and `.agents/skills/`; skills load on demand through the native skill tool. |
| Amp (Sourcegraph) | Sourcegraph's coding agent | `.agents/skills/` (workspace), `~/.config/agents/skills/` (user) | Also reads `.claude/skills/` for compatibility. |
| Goose (Block) | Block's open-source agent | `.agents/skills/` (project), `~/.config/agents/skills/` (global) | Also reads `.goose/skills/` and `.claude/skills/`. |
| Junie (JetBrains) | JetBrains' IDE coding agent | `.junie/skills/<name>/` (project), `~/.junie/skills/<name>/` (user) | Scans project and user scopes and matches on the SKILL.md description. |

As of 2026-07-06, Cursor ships native Agent-Skills discovery from `.cursor/skills/` (project-scoped; invoke with `/` in the agent) - treat its row above as verified native support, not copy-only. Gemini CLI and VS Code / GitHub Copilot also list Agent-Skills support on their paths above; verify the exact behavior in your build.

## Cross-Client Notes

Different agent clients scan different local paths. Codex documentation says Codex scans `.agents/skills` locations from the current directory upward, plus user/admin/system skill locations. A repository root with `SKILL.md` has the right skill-folder shape, but it is not automatically discovered as a repository skill unless installed under a scanned skill directory or packaged through the relevant plugin/distribution path. Other agent clients may use `.claude/skills`, `.gemini/skills`, `.github/skills`, `.cursor/skills`, or `.windsurf/skills`. Treat those as installation targets, not separate source trees.

Runway MCP is a separate agent connector surface. It can expose Seedance 2.0 through Runway inside MCP-compatible agents, but it does not make this repository a Runway plugin and does not change Codex skill installation rules.

## Source Signals

- OpenAI Codex Agent Skills docs: https://developers.openai.com/codex/skills
- OpenAI Codex Plugins docs: https://developers.openai.com/codex/plugins
- OpenAI Academy plugins and skills explainer: https://openai.com/academy/codex-plugins-and-skills/
- OpenAI skills catalog: https://github.com/openai/skills
- Agent Skills open standard overview: https://agentskills.io/
- Google Antigravity skills docs: https://antigravity.google/docs/cli-plugins and https://codelabs.developers.google.com/getting-started-with-antigravity-skills
- OpenClaw skills docs: https://docs.openclaw.ai/tools/skills
- Hermes Agent skills docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- Runway MCP announcement: https://runwayml.com/news/mcp
- Trae Agent Skills docs: https://docs.trae.ai/ide/agent
- Qwen Code Agent Skills docs: https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/ and https://github.com/QwenLM/qwen-code
- OpenCode Agent Skills docs: https://opencode.ai/docs/skills
- Cursor Agent Skills docs: https://cursor.com/docs/context/skills
- Amp (Sourcegraph) Agent Skills: https://ampcode.com/news/agent-skills
- Goose (Block) Agent Skills docs: https://block.github.io/goose/docs/mcp/skills-mcp/
- JetBrains Junie Agent Skills docs: https://junie.jetbrains.com/docs/agent-skills.html

## Do Not Claim

- Do not claim every agent client can install directly from this repository URL.
- Do not claim ClawHub or any registry lists this skill unless it has actually been published there.
- Do not claim every client honors the same metadata fields beyond `name` and `description`.
- Do not claim this repository provides a live Seedance API wrapper. It is an agent-skill workflow and reference package.
- Do not claim that an agent has hidden cross-session memory of a sequence project. Use the Project State Capsule to restore story goal, final outcome, accepted clips, scene map and current scene, current actual state, open motion, completed beats, next clip job, continuity locks, allowed changes, reserved future beats, extension depth, and unresolved uncertainties.

## Inspection Honesty

Media inspection is a client capability, not a property of this skill. Hosts differ widely: many read still images, fewer read video, fewer still read audio, and some read only the filename.

Never state or imply that you viewed, watched, heard, played, measured, verified, or tested media you did not actually inspect. This holds even when the description would be a reasonable guess, and even when the user seems to expect it.

When inspection is unavailable:

- say so plainly, once, without apologising at length;
- work from the user's description, the filename, and any supplied transcript or metadata;
- record those details as reported rather than seen, using the fields the take-review contract already carries: `observation_confidence: low`, `requires_user_confirmation: true`, and every unverified category named in `uncertainties`;
- ask for a short description only when the missing detail actually blocks routing, a reference role, or a continuity decision.

This does not block a valid take review. `observed_end_state` stays populated — a sequence cannot continue without it, and `project_state_check.py` rejects an accepted clip that lacks it. What changes is that a state you were told rather than saw never travels at `medium` or `high` confidence, and it carries an explicit confirmation flag, so the next clip inherits a marked assumption instead of a fact.

Note the honest limit of that arrangement: `observation_confidence` is a confidence axis, not a provenance one, so "I saw it, but the frame was ambiguous" and "I never saw it" both land on `low`. The pairing with `requires_user_confirmation` and `uncertainties` distinguishes them in practice. A dedicated provenance field would be cleaner and is worth considering, but it changes a shipped schema, its checker, and its fixtures, so it belongs in its own reviewed change rather than being smuggled in here.

This is not a stylistic preference. Three of this repository's workflows consume observations as canon: `observed end state` in `[ref:continuation-handoff]`, take triage in `[ref:retake-protocol]`, and reference roles inferred from an attachment in `[ref:reference-workflow]`. A fabricated observation enters the project state as fact, and every later clip in the sequence inherits it. The error compounds silently, which is what makes it worse than admitting the limitation.

The same rule covers provider facts: if the current limits, syntax, or model IDs were not retrieved during this session, they are unverified — say which, rather than presenting a remembered value as current.

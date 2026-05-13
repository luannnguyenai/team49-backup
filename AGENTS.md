# Agent Guidelines

ALWAYS USE UTF-8 ENCODING WHEN READ-WRITE FILES!

## Mandatory Rules When Using AI Coding Agents

### 1. AI Prompt Logging (Automatic)

Prompts are **automatically logged** via hooks when you use any supported AI tool.
You do **not** need to manually update `PROMPT_LOG.md`.

Supported tools and their hook configs:
| Tool | Config file |
|---|---|
| Claude Code | `.claude/settings.json` |
| Cursor | `.cursor/hooks.json` |
| OpenAI Codex | `.codex/hooks.json` |
| Gemini CLI | `.gemini/settings.json` |
| GitHub Copilot | `.github/hooks/hooks.json` |
| Antigravity | `.antigravity/settings.json` |


Logs are saved to `.ai-log/session.jsonl` and submitted automatically on `git push`.

### 2. Setup (One-time)

```bash
# Install git pre-push hook
bash scripts/setup_hooks.sh
```

`AI_LOG_SERVER` and `AI_LOG_API_KEY` are already set in `.env.example`.

### 3. Pull Request Requirements

- **Title**: Short description of the change
- **Description**: Must include:
  - Summary of changes
  - List of changed files

PR description format:

```
## Summary
<description of changes>

## Changes
- <list of changed files>
```

### 4. Rules for AI Agents

If you are an AI coding agent (Claude Code, Cursor, Copilot, Codex, Gemini, etc.):

- **MUST NOT** create a PR without first ensuring `bash scripts/setup_hooks.sh` has been run
- **MUST** include a clear PR description with summary and changed files
- **DO NOT** commit `.ai-log/*.jsonl` files (they are gitignored)
- Logging happens automatically — do not ask users to log prompts manually

## Active Technologies
- Python 3.12 backend, TypeScript 5 frontend + FastAPI, SQLAlchemy, Pydantic, Next.js 14 App Router, React 18, Zustand, Axios (001-course-first-refactor)
- PostgreSQL for authoritative application data, server-managed object storage for binary course assets, repository `data/` files for bootstrap/import only (001-course-first-refactor)

# Skill: Maintainable & Debuggable AI Prompt Design

## Mục tiêu
Thiết kế prompt AI theo hướng:
- Dễ bảo trì (maintainable)
- Dễ cập nhật (updatable)
- Dễ debug (debuggable)
- Có cấu trúc rõ ràng, dễ mở rộng

---

## Keyword cốt lõi

### 1. Kiến trúc prompt
- modular prompt
- structured prompt
- prompt decomposition
- prompt pipeline
- component-based prompt

### 2. Nguyên tắc thiết kế
- separation of concerns
- single responsibility principle (SRP)
- low coupling
- high cohesion
- config-driven design
- template-based design

### 3. Khả năng vận hành
- versioned prompt
- reproducible output
- observable prompt
- prompt traceability
- prompt logging

### 4. Debug & testing
- step-by-step reasoning
- intermediate outputs
- evaluation-friendly prompt
- testable prompt design
- A/B prompt testing

---

## Best Practices

### 1. Tách prompt thành module
- System instruction
- Context layer
- Task layer
- Output format layer

---

### 2. Ưu tiên cấu trúc hơn tự do
❌ Prompt dài, lẫn lộn nhiều nhiệm vụ  
✅ Prompt chia rõ từng phần có trách nhiệm riêng

---

### 3. Luôn có khả năng debug
- Log intermediate steps
- Có chế độ “explain mode”
- Có output structured (JSON / YAML khi cần)

---

### 4. Version hóa prompt
- prompt_v1, v2, v3
- ghi rõ changelog

---

## Output Pattern gợi ý

```text
[INPUT]
...

[CONTEXT]
...

[TASK]
...

[RULES]
...

[OUTPUT FORMAT]
...

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **A20-App-049** (20659 symbols, 31807 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/A20-App-049/context` | Codebase overview, check index freshness |
| `gitnexus://repo/A20-App-049/clusters` | All functional areas |
| `gitnexus://repo/A20-App-049/processes` | All execution flows |
| `gitnexus://repo/A20-App-049/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

````md
# CLAUDE.md

Unified operating guidelines for coding and prompt-agent tasks.  
Designed to reduce common LLM mistakes while producing maintainable, debuggable, and high-quality outputs.

**Principle:** Prefer clarity, correctness, and simplicity over speed.  
For trivial tasks, use judgment.

---

# 1. Think Before Acting

**Do not assume. Surface uncertainty early.**

Before implementing or answering:

- State assumptions explicitly.
- If multiple interpretations exist, list them instead of silently choosing one.
- If requirements are unclear, stop and ask clarifying questions.
- If a simpler solution exists, propose it.
- Push back on unnecessary complexity when appropriate.

## Decision Standard

Good agents clarify *before* making mistakes, not after.

---

# 2. Goal-Driven Execution

**Convert vague requests into verifiable success criteria.**

Examples:

- “Fix the bug” → Reproduce issue, implement fix, verify expected result.
- “Improve prompt” → Define quality metrics, revise prompt, compare outputs.
- “Refactor module” → Preserve behavior, improve structure, verify tests pass.

For multi-step work, use a short execution plan:

```text
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
````

## Rule

Weak goals create confusion.
Strong goals enable autonomous execution.

---

# 3. Simplicity First

**Use the minimum solution that fully solves the request.**

* No speculative features.
* No unnecessary abstractions.
* No configurability unless requested.
* No overengineering for one-time use cases.
* No handling impossible scenarios unless needed.
* If 200 lines can be 50, rewrite it.

Ask:

> Would a senior engineer consider this unnecessarily complex?

If yes, simplify.

---

# 4. Surgical Changes

**Change only what is required.**

When editing existing systems:

* Do not refactor unrelated code.
* Do not reformat untouched sections.
* Match existing conventions unless instructed otherwise.
* Mention adjacent problems, do not silently fix them.

When your changes create unused code:

* Remove imports, variables, functions made obsolete by **your** changes.
* Do not delete pre-existing dead code unless asked.

## Test

Every changed line should trace directly to the user request.

---

# 5. Prompt Architecture First

**Prompts should be engineered like maintainable software.**

Use modular prompt design with clear responsibilities.

## Recommended Layers

```text
[SYSTEM]
Global behavior / identity / hard constraints

[CONTEXT]
Relevant background information

[TASK]
What must be done now

[RULES]
Specific operating constraints

[OUTPUT FORMAT]
Exact response schema

[VALIDATION]
How success is checked
```

## Rules

* Separate concerns.
* One section = one responsibility.
* Prefer reusable components over monolithic prompts.
* Keep coupling low and cohesion high.

---

# 6. Structured Over Freeform

**Prefer explicit structure over ambiguous prose.**

Avoid:

* Long prompts mixing multiple objectives
* Hidden constraints
* Loose output expectations

Prefer:

* Numbered steps
* Clear sections
* Explicit rules
* Defined output schema
* Examples when useful

---

# 7. Debuggable by Design

**Every prompt and workflow should be diagnosable.**

Include when useful:

* Intermediate reasoning checkpoints
* Step-by-step outputs
* Explain mode
* Traceable decisions
* Structured outputs (JSON / YAML / Markdown tables)
* Logging of inputs / versions / settings

If output quality drops, debugging should be fast.

---

# 8. Version Everything

**Treat prompts like code.**

Use versions:

```text
prompt_v1
prompt_v2
prompt_v3
```

Track:

* What changed
* Why it changed
* Expected improvement
* Regression risks

Small controlled iterations beat full rewrites.

---

# 9. Testability & Evaluation

**Good prompts can be measured.**

Use repeatable test cases.

Examples:

* Normal case
* Edge case
* Adversarial case
* Missing context case
* Ambiguous request case

Methods:

* A/B prompt comparisons
* Output scoring rubrics
* Regression checks
* Consistency checks

---

# 10. Output Discipline

**Responses should be immediately usable.**

Unless asked otherwise:

* Be concise.
* Be complete.
* Use clean formatting.
* Prefer actionable outputs over theory.
* If code is requested, provide runnable code.
* If strategy is requested, provide executable steps.

Do not bury key answers in long explanations.

---

# 11. Escalation Rules

Stop and ask when:

* Requirements conflict
* Information is missing
* Constraints are unrealistic
* Security / privacy risk exists
* Multiple valid paths materially differ

Smart clarification is better than confident guessing.

---

# 12. Success Signals

These guidelines are working when there are:

* Fewer unnecessary edits
* Fewer rewrites caused by overengineering
* Faster debugging
* More consistent outputs
* Easier prompt maintenance
* Better reproducibility
* Clarifying questions before mistakes
* High signal, low noise responses

---

# Default Operating Mode

Think clearly.
Plan briefly.
Build simply.
Change surgically.
Structure prompts well.
Debug systematically.
Verify results.

```
```

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **A20-App-049** (7617 symbols, 12311 relationships, 267 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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

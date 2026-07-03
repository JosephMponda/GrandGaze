# MUST–GSL EMR Innovation Challenge — Working Docs

This folder is the single source of truth for the build. Read in this order:

1. **`AGENTS.md`** — project charter. Every human and every AI coding agent (Codex, Claude Code) reads this first, always. It defines the stack, the non-negotiables, the module boundaries, and the "do not reinvent" list.
2. **`backend/engineer-X-*/`** — one folder per backend engineer. Each has exactly 3 files:
   - `01_MODULE_SPEC.md` — what to build, data model, API contract, brief-clause traceability.
   - `02_BUILD_PLAN.md` — day-by-day plan, dependencies on other engineers, Django app scaffold.
   - `03_AGENT_INSTRUCTIONS.md` — the prompt-ready operating rules for Codex/Claude Code on that module.
3. **`frontend/`** — 4 files shared by the 3 frontend engineers + 2 designers:
   - `01_DESIGN_SYSTEM.md`, `02_FRONTEND_ARCHITECTURE.md`, `03_FRONTEND_BUILD_PLAN.md`, `04_FRONTEND_AGENT_INSTRUCTIONS.md`.

## Timeline anchor (read this before anything else)

Today is **Wed 1 July 2026**. The brief's "Week 0" was 1 June, so per the brief's own table:

- Stage 6 (final prototype submission) = **Week 6 → w/c 13 Jul**
- Stage 7 (demo day & judging) = **Week 6–7 → 13–24 Jul**

That gives us **~16 working days to a submittable build** and **~20 to demo day**. This is tight. `AGENTS.md` and every `02_BUILD_PLAN.md` are built against this exact calendar — do not silently slip it. If a task is going to blow the calendar, flag it in standup the same day, don't discover it on day 14.

## One rule above all others

**Ship the MVP list in section 12 of the brief, fully working end-to-end, before touching anything else.** Everything else (Dialysis, FHIR export, offline sync polish) is scored bonus and only gets engineering time once the MVP chain — register patient → vitals → clinical note → lab order/result → prescription/dispense → bill → dashboard, all audit-logged, all role-gated — works without a human explaining it away.

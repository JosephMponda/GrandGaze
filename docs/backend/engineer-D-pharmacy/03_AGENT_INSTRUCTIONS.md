# Engineer D - AI Agent Instructions

Read root `AGENTS.md` first. Scope: `apps/pharmacy` only.

## Scope lock
Do not implement allergy recording (that's `encounters.AllergyRecord`, owned by Engineer B) - you only read it via `encounters.services.get_patient_allergies()`. Do not implement inventory/stock management as a full system - `DispensingRecord.stock_note` is intentionally a lightweight field for MVP; a real inventory module is Engineer E's stretch scope, not yours, and duplicating it wastes both your time budgets.

## Do not reinvent
- **Drug interaction/allergy checking**: this is deliberately a **keyword-matching function against a small seeded table** (`DrugAllergyMap`), not a call to an external drug-interaction API and not a rules-engine dependency. There is no time budget in this competition for integrating a real clinical decision support API, and doing so would also violate the "minimize dependencies" mandate for an external service with its own auth/reliability/cost profile. Build the honest, simple, transparent version - and say so plainly in the UI copy and documentation ("simplified safety check for demonstration; not a substitute for clinical judgment or a certified drug interaction database").
- **Age calculation**: use Python's `dateutil.relativedelta` only if already allowlisted elsewhere; otherwise plain date arithmetic (`today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))`) is sufficient and avoids a new dependency for one calculation.

## Non-negotiables specific to this module
- **Critical warnings must be a hard stop in the server-side view, not just styled differently in the template.** If an agent is asked to "make the warning more subtle" or "let it through faster," the correct response is to push back - a critical allergy warning that can be silently bypassed via a disabled button re-enabled by a browser devtools tweak is a real safety failure, not a hypothetical one. The block must be enforced in the view/form logic, with the override path requiring an explicit reason field that gets validated non-empty server-side.
- **`safety_override_reason` is mandatory, not optional, whenever a warning (of any level) was shown and the user proceeded.** Do not let this field be skippable "to speed up the demo" - if the demo needs speed, seed realistic override reasons in advance, don't remove the requirement.
- Keep `pharmacy/safety.py` as pure, dependency-free functions returning plain data structures (`SafetyWarning` dataclass) - this makes it trivial to unit test every branch, and it's the piece of code most likely to be scrutinized by a technically literate judge.

## When generating code, prefer
- A `SafetyWarning` dataclass (not a Django model) for check results that don't need persistence - only the final logged override reason needs to live in the DB.
- Explicit, named check functions (`_check_allergy`, `_check_duplicate_therapy`, `_check_pediatric_dose`, `_check_pregnancy_renal`) composed inside `check_prescription_safety()`, rather than one long conditional block - this is both easier for a judge to audit and easier for a second agent/engineer to extend later (e.g. adding a real interaction database post-competition).

## Test expectations for every PR in this module
- Full unit coverage of `pharmacy/safety.py` - every check function, every branch (positive and negative), independent of Django's test client.
- Integration test: seeded patient with a recorded penicillin allergy attempting to prescribe amoxicillin → blocked, override with reason → succeeds and is logged.
- Integration test: pediatric patient, dose over threshold → blocked.
- Integration test: duplicate active prescription → warned, not blocked, acknowledgeable.

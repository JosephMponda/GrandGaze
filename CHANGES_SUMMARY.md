# Changes Summary — for the team

**This is a historical snapshot from the Engineer A/B handoff, not a live
status doc.** For current status, use `docs/COMPLETED_FEATURES.md` (the
maintained traceability matrix). Items 1–10 below are still accurate as
engineering history/gotchas worth knowing (the encrypted-field lookup-hash
pattern in particular, item 4, is a real pattern later modules should
follow) — it's specifically the "Not yet built" section at the end that has
since gone stale and should not be trusted.

Ten things to know about the state of the codebase as of the Engineer A/B
handoff, in the order they mattered at the time. Full detail on each is in
`README.md`'s "Reconciliation note" section — this is the short version.

1. **Engineer A foundation is done and merged**: `accounts` (login, RBAC
   groups, role-based dashboard, audit trail) + `patients` (registration,
   search, profile, duplicate detection). This is the contract everyone
   else's models FK into — treat `Patient`/`User`/`Profile` as frozen per
   `AGENTS.md` §4; changes go through a 1-line PR everyone's tagged on.

2. **Engineer B (`encounters` + `vitals`) is done and merged**: outpatient
   clinical documentation with sign-and-lock (signed encounters are
   read-only, further notes are addenda — not silent rewrites), allergy
   records (the exact model Pharmacy will query at prescribing time via
   `encounters.services.get_patient_allergies(patient)`), vital signs entry
   with auto-computed BMI and Early Warning Score, and hard-threshold
   abnormal-vital alerting in the same request/response cycle.

3. **`django-cryptography` (originally allowlisted for field encryption) is
   dead — don't use it.** It's unmaintained and doesn't import on Django
   ≥5.0. Replaced with `core/encrypted_fields.py`, a small Fernet-based
   field. Zero new dependencies added. `national_id`, `phone_number`, and
   `address_line` on `Patient` are encrypted at rest with this.

4. **Encrypted fields need a "lookup hash" column for exact-match
   queries.** Fernet encryption is non-deterministic by design, so you
   cannot `filter(national_id=...)` against the encrypted column directly —
   it will never match. Pattern: a companion `<field>_lookup` column stores
   an HMAC of the plaintext, and queries filter on that instead. See
   `patients/models.py` `Patient.save()` and `core/encrypted_fields.py`
   `hash_lookup_value()`. **If Pharmacy or Billing need exact lookups on an
   encrypted field, use this same pattern — don't filter the encrypted
   column directly.**

5. **A patient-safety bug was found and fixed in duplicate detection**:
   earlier code let a forged/partial "confirmed not duplicate" value bypass
   the check for *other* real duplicate candidates. Fixed — the confirmation
   must match an actual candidate from the real duplicate set, and the
   system still blocks if other unconfirmed duplicates remain. There's a
   regression test for this (`patients/tests.py
   test_forged_confirmation_id_does_not_bypass_duplicate_check`) — don't
   remove it.

6. **All of this is verified against a real Postgres instance, not just
   sqlite.** Several real bugs (the one in #5, plus a queryset-combination
   bug in fuzzy duplicate matching) only surfaced once the actual HTTP views
   were exercised against Postgres with `pg_trgm` enabled — sqlite silently
   skips that code path entirely, which hid the bugs in earlier testing.
   **Test against Postgres before trusting sqlite-passing tests**, especially
   for anything touching `patients` or encrypted fields.

7. **20 automated tests currently pass** (`patients`, `encounters`,
   `vitals`), each covering a happy path, a permission-denied path, and a
   validation-failure path per `AGENTS.md` §9's Definition of Done. Run with
   `pytest` (needs Postgres — see root `README.md`).

8. **`ALLOWED_PACKAGES.md` now exists** (it was referenced by `AGENTS.md`
   §5 but missing from the repo). It documents the `django-cryptography`
   swap and the current dependency list. Check it before adding anything new.

9. **Dashboard widgets are a registry, not hardcoded links.** Each app
   registers its own widget in its `apps.py` `ready()` via
   `accounts.dashboard_widgets.register_widget()` — see `vitals/apps.py` for
   the pattern. The dashboard template just loops over
   `widgets_for_user(request.user)`. Engineers C/D/E: register your own
   widgets there rather than editing `accounts/views.py` or the dashboard
   template directly.

10. **Frontend integration guide is in `FRONTEND_INTEGRATION.md`** — exact
    field names for the registration form, the duplicate-warning flow's
    non-negotiable requirements, the dashboard widget-loop contract, and how
    to run this locally against real Postgres. Read that before touching
    `templates/patients/register.html` or `templates/accounts/dashboard.html`.

## Not yet built (stale — see docs/COMPLETED_FEATURES.md instead)

Everything that was listed here as not-yet-built at the time of the
Engineer A/B handoff — `laboratory`/`imaging`, `pharmacy`,
`billing`/`reporting`, `syncapi`/offline sync, and the Tailwind/HTMX/Alpine
frontend — has since been built. `dialysis` remains a stretch goal and is
not built. For the current, maintained list of what's outstanding, use
`docs/COMPLETED_FEATURES.md`'s "Not Yet Built (Phase-2 Candidates)" table.

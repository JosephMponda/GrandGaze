# Handoff: Mobile guides, Control Panel, and Sign-in branding

## Completed

- Added an always-accessible **Guide** control in the mobile workspace header and navigation drawer.
- Made onboarding tour cards mobile-safe: they use a readable bottom sheet layout, scroll when needed, and retain touch-sized buttons.
- Fixed the Control Panel initial-load issue. The staff-directory fragment now renders only for an explicit HTMX directory-filter request; opening the Control Panel always returns the complete dashboard.
- Kept the role-chart filter working with the updated directory request.
- Increased the MUST and GSL sign-in logos responsively from `2–3.5rem` to `3–4.5rem`, with a matching divider height.
- Added a regression test that distinguishes a complete Control Panel response from an explicit staff-directory fragment response.

## Verification

- `git diff --check` passed.
- The targeted test run was started with `.venv/bin/python -m pytest accounts/tests.py config/tests.py -q`.

## Remaining follow-up

- Perform a brief visual check on a real phone (or device emulator) after deployment: open the Guide from the header and nav drawer, step through a long tour, open the Control Panel from every entry point, and confirm the larger sign-in logos align with the SARIS reference at the intended breakpoints.

# Frontend 04 - AI Agent Instructions

Paste-ready operating rules for Codex / Claude Code when working on templates, static assets, or any client-side code. Read root `AGENTS.md` first, and `02_FRONTEND_ARCHITECTURE.md` for the technical pattern this file assumes.

## Scope lock
Frontend agents work in `templates/`, `static/`, and the HTMX/Alpine-related view logic (the `if request.htmx:` branching, which may live in a backend engineer's view file - that's fine, it's a shared touchpoint, coordinate rather than unilaterally restructure). Frontend agents do not design new data models, do not add new Django apps, and do not change a backend engineer's `services.py` contract - if a page needs data that isn't exposed yet, that's a message to the owning backend engineer, not a direct model import.

## Do not reinvent - and do not "upgrade" the stack
This is the section most likely to get overridden by an AI agent's default instincts, so it's stated plainly:

- **Do not introduce React, Vue, Svelte, Next.js, or any SPA framework**, even for "just one complex page." If a page feels like it needs one, it's a sign the page needs to be re-scoped into smaller HTMX-swapped fragments, not a sign the stack is wrong. Raise it with the team instead of solving it by adding a framework.
- **Do not run `npm install` for anything.** No bundler, no `node_modules`, no `package.json` beyond what the Tailwind CLI setup script itself needs (which should be zero - the CLI is a standalone binary). If a task seems to need an npm package, the answer is almost always "vendor a single file, pinned, reviewed" per root `AGENTS.md` §5, not "npm install it."
- **Do not pull HTMX, Alpine.js, Chart.js, or any other script from a CDN URL in a template `<script src="https://...">` tag.** These are vendored, version-pinned files in `static/js/`, referenced with Django's `{% static %}` tag. A CDN outage or DNS block during the live demo would visibly break the app - this is a real, specific risk being deliberately engineered around, not an arbitrary rule.
- **Do not build a custom client-side router or client-side templating engine.** Django renders HTML; HTMX swaps it. That's the entire routing/rendering story.
- **Do not use `localStorage`/`sessionStorage`/cookies to store clinical data.** The offline outbox is IndexedDB specifically because it can hold larger structured data reliably - see `02_FRONTEND_ARCHITECTURE.md` §4. Session/auth state stays server-side in Django's session, not duplicated into client storage.

## Non-negotiables specific to frontend work

- **Every status/severity indicator carries a text label, never color alone** - design system §6, this is an accessibility requirement, not a style preference, and it's directly checkable in code review (does the badge component render text, or just a colored dot?).
- **Every form uses the shared `_field.html` partial** - an agent generating a new form should include this partial per field, not hand-write `<input>` markup with ad-hoc classes. This is what keeps five different backend engineers' forms visually consistent without a frontend engineer manually fixing each one.
- **Offline-capable forms are explicitly marked** (`data-offline-capable="true"`) and only the specific MVP forms named in root `AGENTS.md` §6 get this treatment - an agent should not add offline-queueing behavior to every form "for consistency," since untested offline-queue behavior on, say, the billing/payment form is a correctness risk (double-charging risk on replay) that hasn't been designed for, not a free win.
- **CSRF tokens are present on every form and every HTMX POST/PUT/DELETE** - Django's `{% csrf_token %}` template tag for standard forms, and the `hx-headers` or a global HTMX config injecting the CSRF header for HTMX requests (there's a documented standard pattern for this - use it, don't disable CSRF protection to make an HTMX request "just work," ever, under any time pressure).
- **Every page must render something meaningful with JavaScript disabled** (except the specific offline-queue interactivity, which necessarily requires JS) - this is both a resilience property and a genuine test of whether a page is really server-rendered-first or has silently become JS-dependent.

## When generating code, prefer

- Semantic HTML first (`<table>` for tabular data, `<button>` for actions, proper `<label for>` associations) - this is both an accessibility win and, not incidentally, exactly what makes a page work well with minimal CSS/JS, which serves the performance budget too.
- Small, single-purpose Alpine `x-data` components scoped to the DOM element they control - not one large global Alpine store trying to manage state across the whole page.
- Tailwind utility classes composed directly in templates for one-off styling; only promote a repeated utility combination into a named component class (in `input.css`'s `@layer components`) once it's used in 3+ places - don't prematurely abstract a style used once.

## Test/verification expectations for every PR touching frontend
- Manual check against the design system component inventory (does this reuse `_status_badge.html`/`_field.html`/etc., or does it invent new markup?).
- Contrast check for any new color usage (design system §6, WCAG AA).
- Page-weight check for any new page or significant asset addition (design system §6, 150KB budget) - note it in the PR description.
- For any offline-capable form: manual test of the actual offline→queue→reconnect→sync flow, not just "the form submits when online."
- Keyboard-only navigation check for any new interactive component.

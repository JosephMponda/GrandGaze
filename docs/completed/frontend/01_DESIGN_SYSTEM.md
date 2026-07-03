# Frontend 01 - Design System

Owner: 3 frontend engineers + 2 UI/UX designers, jointly. This is the visual and interaction contract every page must follow - read it before styling anything, and update it (with team agreement) rather than drifting from it page by page.

## 1. Direction: what "Laravel-docs-fast, minimalist, professional" means in practice

The brief explicitly asks for something that loads fast and feels responsive, with minimal visual distraction, in a Malawi-context, professional-looking clinical tool. Concretely:

- **Server-rendered HTML is the default state of every page** - no loading spinner where a page could just already contain the content. HTMX swaps small fragments, it doesn't hide the whole page behind a JS-rendered shell.
- **Typography carries the design**, not decoration. One serif-free type family, a small number of weight/size steps, generous line-height for dense clinical text.
- **Whitespace and hierarchy over color** - color is used sparingly and functionally (status, severity, action), not decoratively. A clinician scanning a ward list under time pressure needs instant visual hierarchy, not a colorful dashboard.
- **No unnecessary motion.** Transitions are short (150–200ms) and only on state changes that need one (a panel opening, an alert appearing) - never decorative page-load animation.

Reference points worth studying directly (open them and look, don't just take the vibe from memory): the Laravel documentation site (docs.laravel.com) and the Stripe API docs - both are dense, information-heavy, and still feel instant and calm. That's the target, not a typical "hospital dashboard" template with heavy card shadows and gradient icons.

## 2. Color system

Functional, restrained palette - define as Tailwind theme tokens, don't hardcode hex values in templates.

| Token | Use | Notes |
|---|---|---|
| `ink` (near-black, e.g. `#111827`) | Primary text | Never pure `#000` - too harsh on long reading. |
| `paper` (off-white, e.g. `#FAFAF9`) | Page background | Never pure `#FFF` - reduces glare on low-quality/reused screens common in low-resource settings. |
| `brand` (a single deep, desaturated blue or teal - pick one, commit to it) | Primary actions, links, active nav | This is your one "personality" color - everything else stays neutral so this reads clearly. |
| `neutral-100…900` (grayscale ramp) | Borders, secondary text, backgrounds, disabled states | Most of the UI lives here. |
| `success` (muted green) | Confirmations, "resulted"/"paid"/"verified" statuses | Not used for anything except genuine positive status. |
| `warning` (amber) | Non-critical alerts, "pending", duplicate-therapy warnings | |
| `critical` (a clear, desaturated red - not neon) | Critical alerts, allergy blocks, critical lab/imaging results | This color must be visually unmistakable and used **nowhere else** in the UI - its meaning must never be diluted by decorative use. |

Do not add more than these 6 functional colors. If a designer wants a 7th, the bar is: "does this represent a genuinely distinct clinical/system state," not "does this look nice here."

## 3. Typography

- One font family for the whole app. Recommend a system-font stack first (`ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`) - zero load cost, renders instantly, matches the "loads fast" mandate directly. If the team wants a custom webfont, it must be self-hosted (not Google Fonts CDN - that's an external dependency and a privacy/offline concern) and subset to only the weights actually used.
- Scale: 4–5 steps is enough (e.g. 12/14/16/20/28px). Body text at 16px minimum for clinical readability, never smaller, especially for anyone reading on a phone screen.
- Line height 1.5 for body/paragraph text, 1.3 for headings.

## 4. Layout & spacing

- 8px base spacing unit, Tailwind defaults are fine - don't invent a custom spacing scale.
- Max content width for text-heavy pages (clinical notes, system design doc pages) around 720–800px - dense clinical free-text is unreadable at full-bleed widths on a desktop monitor.
- Data-dense pages (patient lists, lab queues, dashboards) can go full-width but must use a real table/grid, not cards-for-everything - cards are the wrong pattern for scanning 30 rows of patients quickly.

## 5. Component inventory (build these once, reuse everywhere - do not restyle per page)

- **Nav shell**: role-aware top or side nav, persistent, server-rendered, one template partial.
- **Buttons**: primary (brand-colored, one per view max), secondary (outline/neutral), destructive (critical-colored, confirmation required before firing).
- **Form field**: label + input + inline validation error state - one Django template snippet (`_field.html`) every form includes, not hand-copied markup per form.
- **Status badge**: small pill component parameterized by the 3 severity tokens (`success`/`warning`/`critical`) plus a neutral "info" variant - this is what renders lab/imaging/prescription statuses and EWS risk levels everywhere in the app. Build it once.
- **Alert banner**: for the HTMX-driven safety-warning flows (pharmacy) and abnormal-vital/critical-result notices - critical variant is visually distinct enough that a busy clinician cannot mistake it for a routine notice.
- **Table**: dense, sortable-by-click-where-useful, zebra-striped only if it measurably helps scanning (test with real seed data, don't assume).
- **Tabs**: used on the patient profile page (Encounters/Vitals/Labs/Imaging/Medications/Billing) - HTMX-loaded content per tab, URL-addressable (so a direct link to "Patient X, Labs tab" works, which also helps the offline-cache story).
- **Empty state**: every list/table needs one - "No lab orders yet" beats a blank white box, and matters more than usual here because a lot of demo/seed scenarios will legitimately be empty.

## 6. Accessibility & low-resource considerations (these are explicitly judged - Malawi Context Fit, 15%)

- Sufficient color contrast (WCAG AA minimum) - check the `critical` red and `warning` amber against `paper` background specifically, these are the two most safety-relevant colors in the app.
- All interactive elements keyboard-navigable - clinical staff on shared/older hardware may not always have a smoothly working mouse/trackpad.
- No content or function that depends on color alone - status badges carry text, not just a colored dot (a clinician with color vision deficiency must be able to tell "critical" from "resulted" from the label, not the hue).
- Design for a **1366×768 laptop screen and a mid-range Android phone** as the two primary targets, not a large desktop monitor - this is genuinely what most Malawian health facility hardware looks like, and it directly informs component sizing and information density decisions above.
- Total page weight budget: **under 150KB per page (HTML+CSS+JS, excluding images), first load.** This is a hard target the whole frontend team should measure against, not an aspiration - it's what makes "loads fast on intermittent connectivity" a true claim rather than a slogan in the pitch deck.

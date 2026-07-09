# Frontend Navigation & Page Flow Debug Guide

## 🔴 Problem Identified: Duplicate Headers

### What's Happening

The patient profile page has **HTMX-driven tabs** that load content from backend endpoints:

```html
<!-- From templates/patients/profile.html -->
<div id="tp-encounters" 
     hx-get="{% url 'encounters:patient_tab' patient.pk %}" 
     hx-trigger="load" 
     hx-target="this">
</div>
```

But when these endpoints return content, **some views extend `base.html`** which includes the full `<header>` + footer, causing:

1. **Main page header** (from patient profile base.html) 
2. **Duplicate header** (from fragment template extending base.html)

---

## 📋 Page Architecture (CORRECT Pattern)

### Full-Page Views (extend base.html)
These are navigated to directly (not HTMX):
- `accounts/login.html` ✓
- `accounts/dashboard.html` ✓
- `patients/profile.html` ✓ (main patient view)
- `patients/register.html` ✓

### Fragment Views (DON'T extend base.html)
These are loaded via HTMX into a parent page tab/panel:
- `encounters/patient_tab.html` ❌ (currently missing or incorrectly extends base.html)
- `vitals/patient_tab.html` ❌
- `laboratory/patient_tab.html` ❌
- `imaging/patient_tab.html` ❌
- `pharmacy/patient_tab.html` ❌
- `billing/patient_tab.html` ❌

---

## 🛠️ How to Fix

### Step 1: Identify Fragment Templates
Each backend module that serves a `patient_tab` endpoint needs **TWO templates**:

```
encounters/
  ├── patient_tab.html      (fragment - NO header/footer)
  ├── detail.html           (full page - extends base.html)
  └── views.py
```

### Step 2: HTMX-Aware Views
Your view should detect HTMX requests and return appropriate template:

```python
@login_required
def patient_encounters_tab(request, patient_id):
    """Load encounters fragment for profile page tab (HTMX)"""
    encounters = Encounter.objects.filter(patient_id=patient_id)
    # Always return fragment (no base.html wrapper)
    return render(request, "encounters/patient_tab.html", {
        "encounters": encounters,
        "patient_id": patient_id,
    })

@login_required  
def encounter_detail(request, pk):
    """Full encounter page (direct navigation)"""
    encounter = Encounter.objects.get(pk=pk)
    # Returns full page WITH header/footer
    return render(request, "encounters/detail.html", {
        "encounter": encounter,
    })
```

### Step 3: Fragment Template Pattern
Never include `{% load static %}`, never extend base.html:

```django
{# encounters/patient_tab.html - FRAGMENT, NO extends base.html #}
<div class="space-y-4">
    <h3 class="font-bold text-gray-900">Encounters</h3>
    
    {% if encounters %}
        <table class="w-full text-sm">
            <tbody>
                {% for enc in encounters %}
                <tr class="border-b hover:bg-gray-50">
                    <td class="py-2">{{ enc.date|date:"M d, Y" }}</td>
                    <td><a href="{% url 'encounters:detail' enc.pk %}" class="text-brand hover:underline">View</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    {% else %}
        {% include "components/_empty_state.html" with title="No Encounters" message="No clinical encounters recorded yet." %}
    {% endif %}
</div>
```

---

## 🗺️ Complete Page Flow

### User Story: Register Patient → View Encounter

```
1. User at dashboard (full page, extends base.html)
   ↓
2. Click "Register" link (hx-boost bypasses, full page load)
   → GET /patients/register/ → templates/patients/register.html (extends base.html)
   ↓
3. Submit form
   → POST /patients/register/ → redirect to patient profile
   ↓
4. Patient profile loads (full page, extends base.html)
   → GET /patients/<id>/ → templates/patients/profile.html (extends base.html)
   ↓
   [Profile page has 6 HTMX tabs]
   ↓
5. HTMX loads "Encounters" tab (FRAGMENT)
   → GET /encounters/patient/<id>/tab/ → templates/encounters/patient_tab.html (NO extends)
   ↓
6. User clicks "New Encounter" or "View" link
   → GET /encounters/<id>/ → templates/encounters/detail.html (extends base.html) [FULL PAGE]
   ↓
7. Encounter detail page loads with full header/footer
```

---

## ✅ URL Routing Check

| Endpoint | Template | Type | Extends base.html? |
|----------|----------|------|-------------------|
| /accounts/login/ | accounts/login.html | Full Page | ✓ |
| /accounts/dashboard/ | accounts/dashboard.html | Full Page | ✓ |
| /patients/register/ | patients/register.html | Full Page | ✓ |
| /patients/\<id\>/ | patients/profile.html | Full Page | ✓ |
| /encounters/patient/\<id\>/tab/ | encounters/patient_tab.html | Fragment | ✗ |
| /encounters/\<id\>/ | encounters/detail.html | Full Page | ✓ |
| /vitals/patient/\<id\>/tab/ | vitals/patient_tab.html | Fragment | ✗ |
| /vitals/new/ | vitals/form.html | Full Page | ✓ |

---

## ✅ Implementation Status: ALL COMPLETE

All fragment templates and views are **already correctly implemented**:

### Fragment Templates ✅
- ✅ `templates/encounters/_patient_tab.html` (returns via `patient_encounters_tab` view)
- ✅ `templates/vitals/_patient_tab.html` (returns via `patient_vitals_tab` view)
- ✅ `templates/laboratory/_patient_tab.html` (returns via `patient_tab` view)
- ✅ `templates/imaging/_patient_tab.html` (returns via `patient_tab` view)
- ✅ `templates/pharmacy/_patient_tab.html` (returns via `patient_tab` view)
- ✅ `templates/billing/_patient_tab.html` (returns via `patient_tab` view)

### Views ✅
All views correctly distinguish and return:
- **Tab Fragment** (HTMX): `render(..., "_patient_tab.html", ...)` - NO header/footer
- **Full Page** (direct nav): `render(..., "detail.html", ...)` - extends base.html

### URL Routing ✅
All modules configured:
```python
path("patient/<int:patient_id>/tab/", views.patient_tab, name="patient_tab")  # Fragment
path("<int:pk>/", views.encounter_detail, name="detail")  # Full page
```

### Patient Profile Tab Loading ✅
Profile correctly calls HTMX endpoints:
```django
hx-get="{% url 'encounters:patient_tab' patient.pk %}"
hx-get="{% url 'vitals:patient_tab' patient.pk %}"
hx-get="{% url 'laboratory:patient_tab' patient.pk %}"
hx-get="{% url 'imaging:patient_tab' patient.pk %}"
hx-get="{% url 'pharmacy:patient_tab' patient.pk %}"
hx-get="{% url 'billing:patient_tab' patient.pk %}"
```

---

## 🚦 Testing Checklist

- [ ] Load patient profile page → should have ONE header
- [ ] Click each tab (Encounters, Vitals, Labs, etc.) → content loads, NO duplicate header
- [ ] Click "View Encounter" link from tab → full encounter page loads with header
- [ ] Click browser back → returns to patient profile
- [ ] Inspect network tab → tab requests return HTML fragments only, no `<html>` tag

---

## 📝 Design System Notes

**Fragment templates should:**
- Use the same component partials (`_field.html`, `_status_badge.html`, etc.)
- Never include `<html>`, `<head>`, `<body>`, or `{% static %}` tags
- Be pure content wrapped in semantic `<div>` or `<section>` tags
- Work within the parent page's existing Tailwind/CSS context

**Full-page templates:**
- Must extend `base.html`
- Include navigation context
- Can have their own structured layout


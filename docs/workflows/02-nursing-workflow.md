# Workflow 11.2 — Nursing Workflow

```mermaid
flowchart TD
    A([Patient Arrives at Ward/Clinic]) --> B[Triage Assessment]
    B --> C[Vital Signs Recording]
    C --> D{NEWS2 Score}
    D -->|0-4 Low Risk| E[Routine Monitoring]
    D -->|5-6 Medium Risk| F[Increased Frequency]
    D -->|7+ High Risk| G[Immediate Clinician Review]
    F --> H[Nursing Care Plan]
    G --> H
    E --> H
    H --> I[Nursing Notes & Observations]
    I --> J[MAR - Medication Administration]
    J --> K{Patient Condition Changed?}
    K -->|Yes| L[Escalation to Clinician]
    K -->|No| M[Continue Monitoring]
    L --> N[Updated Orders]
    N --> O[Nursing Handover]
    M --> O
    O --> P{Shift Change?}
    P -->|Yes| Q[Structured Handover Report]
    P -->|No| B
    Q --> B
```
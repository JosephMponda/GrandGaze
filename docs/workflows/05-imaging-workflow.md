# Workflow 11.5 — Medical Imaging Workflow

```mermaid
flowchart TD
    A([Imaging request created]) --> B[Linked to patient, modality, encounter]
    B --> C{Modality requires pregnancy check?}
    C -->|Yes| D[Pregnancy status must be checked before submit]
    C -->|No| E[Proceed]
    D --> F{Checked?}
    F -->|No| G[Request blocked]
    F -->|Yes| E
    E --> H[Request enters worklist]
    H --> I{Radiographer or admin?}
    I -->|Yes| J[Enter report]
    I -->|No| K[Request remains pending]
    J --> L[Findings and impression recorded]
    L --> M{Critical finding?}
    M -->|Yes| N[Critical alert raised]
    M -->|No| O[Report finalized]
    N --> O
    O --> P[Status set to reported]
    P --> Q[Report visible in EMR and patient tab]
    Q --> R[Clinician reviews report]
```

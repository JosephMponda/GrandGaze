# Workflow 11.1 — Patient Journey

```mermaid
flowchart TD
    A([Patient Arrives]) --> B{Existing patient?}
    B -->|No| C[Registration & Demographics]
    C --> D{Possible duplicate?}
    D -->|Yes| E[Show duplicate warning + require explicit confirmation]
    D -->|No| F[Profile Created]
    E --> F
    B -->|Yes| G[Open Patient Profile]
    F --> G
    G --> H[Search / Visit / Encounter Context]
    H --> I{Urgent or emergency presentation?}
    I -->|Yes| J[Triage or rapid register + triage]
    I -->|No| K[Routine review]
    J --> L[Review Vitals / EWS / History]
    K --> L
    L --> M{Needs investigations?}
    M -->|Lab| N[Lab order -> collection -> result -> verify]
    M -->|Imaging| O[Imaging request -> report]
    M -->|Both| P[Lab and imaging orders]
    M -->|None| Q[Treatment plan]
    N --> Q
    O --> Q
    P --> Q
    Q --> R{Medication needed?}
    R -->|Yes| S[Prescribe -> safety checks -> pharmacy queue]
    R -->|No| T[Proceed]
    S --> T
    T --> U{Disposition}
    U -->|Discharge| V[Discharge summary]
    U -->|Admit| W[Admission to ward/bed]
    U -->|Refer| X[Referral record]
    U -->|Death| Y[Death documentation]
    V --> Z([Exit / follow-up])
    W --> Z
    X --> Z
    Y --> Z
```

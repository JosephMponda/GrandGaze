# Workflow 11.7 — Billing Workflow

```mermaid
flowchart TD
    A([Service Provided]) --> B[Service Item Selected]
    B --> C{Patient Category}
    C -->|Private| D[Set Price]
    C -->|NHIS/Insurance| E[Verify Coverage]
    C -->|Waiver/Exempt| F[Check Approval]
    E --> G[Apply Co-pay / Direct Bill]
    D --> H[Generate Invoice]
    F --> H
    G --> H
    H --> I[Print / Show Invoice]
    I --> J{Payment Method}
    J -->|Cash| K[Receive Payment]
    J -->|Mobile Money| L[Initiate Mobile Payment]
    J -->|Insurance| M[Submit Claim]
    L --> N[Confirm Payment]
    K --> O[Issue Receipt]
    N --> O
    M --> P[Claim Acknowledged]
    O --> Q[Update Revenue Ledger]
    P --> Q
    Q --> R[Daily Reconciliation]
    R --> S[Revenue Reports]
```
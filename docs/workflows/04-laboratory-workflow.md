# Workflow 11.4 — Laboratory Workflow

```mermaid
flowchart TD
    A([Clinician Orders Lab]) --> B[Order Received in Lab]
    B --> C[Print Labels & Requisition]
    C --> D[Sample Collection]
    D --> E{Sample Adequate?}
    E -->|No| F[Request New Sample]
    F --> D
    E -->|Yes| G[Sample Registered & Tracked]
    G --> H[Assigned to Lab Section]
    H --> I[Hematology]
    H --> J[Biochemistry]
    H --> K[Microbiology]
    H --> L[Other]
    I --> M[Result Entry]
    J --> M
    K --> M
    L --> M
    M --> N[Technician Verification]
    N --> O{Critical Value?}
    O -->|Yes| P[Critical Alert to Clinician]
    O -->|No| Q[Pathologist Review]
    P --> Q
    Q --> R[Result Authorized]
    R --> S[Result Available in EMR]
    S --> T{Result Requested?}
    T -->|Yes| U[Push Notification]
    T -->|No| V[Available on Dashboard]
```
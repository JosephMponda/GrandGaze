# Laboratory Ordering and Result Review

```mermaid
flowchart TD
    A[Place lab order] --> B[Collect sample]
    B --> C[Process test]
    C --> D[Record result]
    D --> E{Critical / abnormal?}
    E -- Yes --> F[Alert clinician]
    E -- No --> G[Make result available]
    F --> G
```

Implemented in:
- `laboratory`
- `templates/laboratory/*`


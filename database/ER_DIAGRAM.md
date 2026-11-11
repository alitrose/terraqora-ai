# TerraQora AI — Database Entity-Relationship Diagram

```mermaid
erDiagram
    USERS ||--o| FARMER_PROFILES : "has profile"
    USERS ||--o{ FARMS : "owns"
    USERS ||--o{ CROP_PREDICTIONS : "requests"
    USERS ||--o{ DISEASE_DETECTIONS : "uploads"
    USERS ||--o{ FERTILIZER_RECOMMENDATIONS : "requests"
    USERS ||--o{ IRRIGATION_RECOMMENDATIONS : "requests"
    USERS ||--o{ CROP_RECOMMENDATIONS : "requests"
    USERS ||--o{ CHAT_SESSIONS : "opens"
    USERS ||--o{ GENERATED_REPORTS : "exports"

    FARMS ||--o{ CROP_PREDICTIONS : "scoped to"
    FARMS ||--o{ DISEASE_DETECTIONS : "scoped to"
    FARMS ||--o{ FERTILIZER_RECOMMENDATIONS : "scoped to"
    FARMS ||--o{ IRRIGATION_RECOMMENDATIONS : "scoped to"
    FARMS ||--o{ CROP_RECOMMENDATIONS : "scoped to"
    FARMS ||--o{ CHAT_SESSIONS : "provides context"
    FARMS ||--o{ GENERATED_REPORTS : "summarizes"

    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : "contains"

    CROP_PREDICTIONS ||--o{ GENERATED_REPORTS : "referenced in"
    FERTILIZER_RECOMMENDATIONS ||--o{ GENERATED_REPORTS : "referenced in"
    IRRIGATION_RECOMMENDATIONS ||--o{ GENERATED_REPORTS : "referenced in"
```

## Integrity & Authorization Rules
- Every user-owned domain row carries `user_id` (`NOT NULL`, `ON DELETE CASCADE`), enforced at API level so farmers can only read/export their own records (`admin` endpoints verify `role == 'admin'`).
- Check constraints enforce valid roles (`farmer | admin`), supported assistant languages (`en | ta | ml | hi | te`), non-negative agricultural quantities, valid `soil_ph` (`0..14`), and bounded probabilities (`0..1`).
- `irrigation_recommendations.is_sensor_backed` explicitly records `false` when recommendations derive from meteorological API estimates rather than physical soil probes.

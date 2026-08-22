# EcoBuddy AI Portable Sustainability Profile — JSON Schema v1.0

## Document envelope

Every portable profile is a UTF-8 JSON object with these required fields:

| Field | Type | Required | Description |
|---|---|---:|---|
| `schema_version` | string | yes | Currently `"1.0"`. Future versions must not be imported until a migration path exists. |
| `exported_at` | ISO-8601 string | yes | UTC timestamp for the export. |
| `application` | string | yes | Must be `"EcoBuddy AI"`. |
| `profile` | object | yes | Non-credential account profile fields. Password hashes are never exported. |
| `assessments` | array | yes | User assessment history. |
| `goals` | array | yes | Reduction-goal history. |
| `habits` | array | yes | Persistent habit-tracker state. |
| `recommendations` | array | yes | Recommendation feedback history. |
| `metadata` | object | yes | Export bookkeeping and privacy metadata. |

## Supported record sources

- **Assessments:** `assessments`
- **Goals:** `reduction_goals`
- **Habits:** `user_habits` (one JSON state record per user)
- **Recommendations:** `recommendation_feedback`

Only records belonging to the exporting user are included. The implementation filters records by `user_id` and never exports `password_hash`.

## Validation rules

Imports are rejected before any database write when:

- required envelope fields are missing;
- the schema version is unsupported;
- the application identifier is wrong;
- dates/timestamps are not valid ISO-8601 values;
- records are not JSON objects/arrays of the expected shape;
- duplicate record IDs occur within a record collection;
- numeric fields are outside safe application ranges;
- the target user does not exist.

Unknown top-level extension fields are tolerated for forward-compatible metadata, but unknown record fields are not written to SQLite.

## Conflict and transaction semantics

The importer supports three explicit strategies:

- `skip` — default and conservative; existing records are retained.
- `merge` — conflicting records are updated with fields supplied by the import.
- `replace` — conflicting records are replaced by the imported record.

The complete import runs inside one SQLite transaction. Any validation or insertion exception rolls back the entire import; there is no partial-import success state.

## Migration architecture

`migrate_export()` is the single migration entry point. Future schema versions should add functions such as `migrate_v1_to_v2()` and register a migration path before accepting that version. Unsupported future versions are rejected safely rather than guessed at.

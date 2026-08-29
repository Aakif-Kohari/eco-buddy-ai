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

## Conflict-aware assessment merge

Assessment records carry stable metadata so they can be matched across devices instead of relying on the local autoincrement `id`:

| Field | Description |
|---|---|
| `client_uuid` | Stable identifier assigned on the device the assessment was created on. Used to match a record across exports/imports. |
| `updated_at` | Last-modification timestamp for the record. |
| `source_device` | Identifier of the device/client the record was created or last modified on. |

During import, each assessment with a `client_uuid` is classified as one of:

- **new** — no local assessment shares this `client_uuid`; it is added.
- **unchanged** — content is identical to the local record; the import is a no-op, which keeps re-importing the same backup idempotent.
- **updated** — content differs and the incoming record's `updated_at` is not older than the local one; it is applied automatically.
- **conflicting** — content differs and the local record is newer than the incoming one; the local copy is kept unless the caller explicitly resolves the conflict (see below).
- **duplicate** — the same `client_uuid` appears more than once within the same import; only the first occurrence is considered.

Assessment records without a `client_uuid` (older exports) fall back to the original `id`-based strategy behavior for backward compatibility.

`merge_imported_data()` / `import_user_profile()` accept an optional `resolutions` mapping of `client_uuid -> "keep_incoming"` to let a user pick the imported version for a specific conflicting record; any conflict without an explicit `"keep_incoming"` resolution keeps the local (newer) copy rather than being silently overwritten. `create_import_preview()` reports counts per status under `assessment_status_counts` so a UI can show conflicts before anything is written.
## Migration architecture

`migrate_export()` is the single migration entry point. Future schema versions should add functions such as `migrate_v1_to_v2()` and register a migration path before accepting that version. Unsupported future versions are rejected safely rather than guessed at.

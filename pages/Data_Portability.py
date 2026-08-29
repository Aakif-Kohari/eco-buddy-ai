"""Streamlit UI for safe, versioned sustainability profile portability."""
import json
import streamlit as st

from src.data.data_portability import (
    CONFLICT_STRATEGIES,
    EXPORT_SCHEMA_VERSION,
    create_import_preview,
    export_profile_json,
    import_user_profile,
    validate_export_document,
)

st.title("💾 Portable Sustainability Profile")
st.caption(f"Versioned JSON schema {EXPORT_SCHEMA_VERSION} — no external upload is used.")

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please sign in before exporting or importing your sustainability profile.")
    st.stop()

st.info(
    "🔐 **Privacy warning:** your export can contain personal sustainability information "
    "such as assessment history, goals, habits, and recommendation feedback. Keep the JSON file secure. "
    "EcoBuddy does not upload the file to a third-party service."
)

st.header("📤 Export")
if st.button("Generate portable JSON", type="primary"):
    st.session_state["portable_export"] = export_profile_json(user_id)

if st.session_state.get("portable_export"):
    st.download_button(
        "⬇️ Download sustainability profile",
        data=st.session_state["portable_export"],
        file_name="ecobuddy_sustainability_profile_v1.json",
        mime="application/json",
    )
    st.caption("The export intentionally excludes password credentials.")

st.divider()
st.header("📥 Import")
st.warning(
    "Import only JSON files you trust. The file is validated before any database write, "
    "and the import is transactional. No changes are made until you confirm."
)

uploaded = st.file_uploader("Upload a JSON profile", type=["json"])
strategy_label = st.selectbox(
    "Conflict strategy",
    ["skip", "merge", "replace"],
    index=0,
    help="Skip keeps existing data. Merge updates conflicting records with imported fields. Replace replaces conflicting records."
)

if uploaded is not None:
    try:
        raw = uploaded.getvalue().decode("utf-8")
        document = json.loads(raw)
        valid, errors = validate_export_document(document)
        if valid:
            st.success(f"Valid EcoBuddy AI profile — schema {document['schema_version']}")
            preview = create_import_preview(document, user_id)
            st.subheader("Import preview")
            cols = st.columns(4)
            labels = [("Assessments", "assessments"), ("Goals", "goals"), ("Habits", "habits"), ("Recommendations", "recommendations")]
            for col, (label, key) in zip(cols, labels):
                col.metric(label, preview["records_found"][key])
            st.markdown("**New records:** " + ", ".join(f"{k}: {v}" for k, v in preview["new_records"].items()))
            st.markdown("**Conflicting records:** " + ", ".join(f"{k}: {v}" for k, v in preview["conflicts"].items()))
            st.caption(f"Selected strategy: `{strategy_label}`. No data is modified yet.")

            if st.button("Confirm and import", type="primary"):
                try:
                    result = import_user_profile(document, user_id, strategy=strategy_label)
                    st.success(
                        f"Import complete: {result['imported']} imported, {result['merged']} merged, "
                        f"{result['skipped']} skipped."
                    )
                    st.session_state.pop("portable_export", None)
                except Exception as exc:
                    st.error(f"Import rolled back: {exc}")
        else:
            st.error("The file failed validation. Nothing was imported.")
            for error in errors:
                st.write(f"- {error}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        st.error(f"Invalid JSON file: {exc}")

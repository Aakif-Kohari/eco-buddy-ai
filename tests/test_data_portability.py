import json
import sqlite3
from pathlib import Path

import pytest

from src.data.data_portability import (
    EXPORT_SCHEMA_VERSION,
    create_import_preview,
    export_profile,
    export_profile_json,
    import_user_profile,
    migrate_v1_to_v2,
    validate_export_document,
)


def make_db(path: Path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT, password_hash TEXT, anonymous_leaderboard INTEGER, created_at TEXT);
        CREATE TABLE assessments (id INTEGER PRIMARY KEY, user_id INTEGER, date TEXT, created_at TEXT, transport TEXT, distance REAL, electricity REAL, diet TEXT, flights INTEGER, footprint REAL, eco_score INTEGER, trip_id TEXT);
        CREATE TABLE reduction_goals (id INTEGER PRIMARY KEY, user_id INTEGER, baseline_kg REAL, target_kg REAL, start_date TEXT, target_date TEXT, status TEXT, created_at TEXT);
        CREATE TABLE user_habits (user_id INTEGER PRIMARY KEY, data_json TEXT, updated_at TEXT);
        CREATE TABLE recommendation_feedback (id INTEGER PRIMARY KEY, user_id INTEGER, recommendation_id TEXT, category TEXT, feedback_type TEXT, difficulty TEXT, created_at TEXT);
        CREATE UNIQUE INDEX idx_test_trip_id ON assessments(trip_id);
        """
    )
    conn.execute("INSERT INTO users VALUES (1,'alice','alice@example.com','SECRET',0,'2026-01-01T00:00:00Z')")
    conn.execute("INSERT INTO assessments VALUES (1,1,'2026-01-02T00:00:00Z','2026-01-02T00:00:00Z','Bike',5,100,'Vegetarian',0,120,90,'trip-1')")
    conn.execute("INSERT INTO reduction_goals VALUES (1,1,500,350,'2026-01-01','2026-12-31','active','2026-01-01T00:00:00Z')")
    conn.execute("INSERT INTO user_habits VALUES (1,?, '2026-01-03T00:00:00Z')", (json.dumps({'active_habits':['Walk for short trips']}),))
    conn.execute("INSERT INTO recommendation_feedback VALUES (1,1,'rec-1','Transport','helpful','easy','2026-01-04T00:00:00Z')")
    conn.commit(); conn.close()


def test_valid_export_and_schema(tmp_path):
    db = tmp_path/'eco.db'; make_db(db)
    doc = export_profile(1, str(db))
    assert doc['schema_version'] == EXPORT_SCHEMA_VERSION
    assert doc['profile']['username'] == 'alice'
    assert 'password_hash' not in doc['profile']
    assert len(doc['assessments']) == len(doc['goals']) == len(doc['habits']) == len(doc['recommendations']) == 1
    assert validate_export_document(doc)[0]


def test_json_round_trip(tmp_path):
    db = tmp_path/'eco.db'; make_db(db)
    text = export_profile_json(1, str(db))
    assert validate_export_document(json.loads(text))[0]


def test_empty_profile_exports_valid(tmp_path):
    db = tmp_path/'eco.db'; make_db(db)
    conn=sqlite3.connect(db); conn.execute('DELETE FROM assessments'); conn.execute('DELETE FROM reduction_goals'); conn.execute('DELETE FROM user_habits'); conn.execute('DELETE FROM recommendation_feedback'); conn.commit(); conn.close()
    doc=export_profile(1,str(db)); assert validate_export_document(doc)[0]


def test_invalid_json_is_rejected(tmp_path):
    db=tmp_path/'eco.db'; make_db(db)
    with pytest.raises(ValueError, match='Invalid JSON'):
        import_user_profile('{not json',1,str(db))


def test_missing_schema_version():
    doc={'exported_at':'2026-01-01T00:00:00Z','application':'EcoBuddy AI','profile':{},'assessments':[],'goals':[],'habits':[],'recommendations':[],'metadata':{}}
    assert not validate_export_document(doc)[0]


def test_future_schema_rejected():
    doc=export_profile(1, str((Path(__file__).parent/'test_data_portability.db'))) if False else {'schema_version':'99.0','exported_at':'2026-01-01T00:00:00Z','application':'EcoBuddy AI','profile':{},'assessments':[],'goals':[],'habits':[],'recommendations':[],'metadata':{}}
    ok, errors=validate_export_document(doc); assert not ok; assert any('Unsupported' in e for e in errors)


def test_invalid_types_dates_and_ranges():
    base={'schema_version':'1.0','exported_at':'2026-01-01T00:00:00Z','application':'EcoBuddy AI','profile':{},'goals':[],'habits':[],'recommendations':[],'metadata':{},'assessments':[{'id':1,'date':'bad','distance':-1}]}
    ok, errors=validate_export_document(base); assert not ok; assert any('ISO' in e for e in errors); assert any('between' in e for e in errors)


def test_duplicate_records_rejected():
    doc={'schema_version':'1.0','exported_at':'2026-01-01T00:00:00Z','application':'EcoBuddy AI','profile':{},'assessments':[{'id':1},{'id':1}],'goals':[],'habits':[],'recommendations':[],'metadata':{}}
    ok, errors=validate_export_document(doc); assert not ok; assert any('duplicated' in e for e in errors)


def test_preview_counts_conflicts_and_new(tmp_path):
    db=tmp_path/'eco.db'; make_db(db); doc=export_profile(1,str(db)); doc['assessments'].append({'id':2,'user_id':1,'date':'2026-02-01T00:00:00Z','created_at':'2026-02-01T00:00:00Z','transport':'Walk','distance':1,'electricity':50,'diet':'Vegan','flights':0,'footprint':20,'eco_score':98,'trip_id':'trip-2'})
    preview=create_import_preview(doc,1,str(db)); assert preview['valid']; assert preview['conflicts']['assessments'] >= 1; assert preview['new_records']['assessments'] >= 1


def test_skip_conflicts(tmp_path):
    db=tmp_path/'eco.db'; make_db(db); doc=export_profile(1,str(db)); before=sqlite3.connect(db).execute('select count(*) from assessments').fetchone()[0]; result=import_user_profile(doc,1,'skip',str(db)); after=sqlite3.connect(db).execute('select count(*) from assessments').fetchone()[0]; assert after==before; assert result['skipped'] >= 1


def test_merge_conflict(tmp_path):
    db=tmp_path/'eco.db'; make_db(db); doc=export_profile(1,str(db)); doc['assessments'][0]['eco_score']=42; result=import_user_profile(doc,1,'merge',str(db)); score=sqlite3.connect(db).execute('select eco_score from assessments where id=1').fetchone()[0]; assert score==42; assert result['merged'] >= 1


def test_replace_conflict(tmp_path):
    db=tmp_path/'eco.db'; make_db(db); doc=export_profile(1,str(db)); doc['assessments'][0]['eco_score']=11; result=import_user_profile(doc,1,'replace',str(db)); score=sqlite3.connect(db).execute('select eco_score from assessments where id=1').fetchone()[0]; assert score==11; assert result['imported'] >= 1


def test_atomic_rollback_on_insert_failure(tmp_path):
    db=tmp_path/'eco.db'; make_db(db); doc=export_profile(1,str(db))
    # Valid record that violates the database's unique trip_id constraint.
    doc['assessments'].append({'id':999,'user_id':1,'date':'2026-02-01T00:00:00Z','created_at':'2026-02-01T00:00:00Z','transport':'Walk','distance':1,'electricity':50,'diet':'Vegan','flights':0,'footprint':20,'eco_score':80,'trip_id':'trip-1'})
    with pytest.raises(sqlite3.IntegrityError): import_user_profile(doc,1,'skip',str(db))
    assert sqlite3.connect(db).execute('select count(*) from assessments').fetchone()[0]==1


def test_invalid_user_never_imports(tmp_path):
    db=tmp_path/'eco.db'; make_db(db); doc=export_profile(1,str(db));
    with pytest.raises(ValueError, match='Target user'):
        import_user_profile(doc,999,'skip',str(db))


def test_migration_hook():
    doc={'schema_version':'1.0','metadata':{}}
    migrated=migrate_v1_to_v2(doc); assert migrated['schema_version']=='2.0'; assert migrated['metadata']['migrated_from']=='1.0'


def test_supported_fields_only_and_no_external_dependency(tmp_path):
    db=tmp_path/'eco.db'; make_db(db); doc=export_profile(1,str(db)); doc['unexpected']='ignored-by-validation'
    assert validate_export_document(doc)[0]


def test_large_history(tmp_path):
    db=tmp_path/'eco.db'; make_db(db); conn=sqlite3.connect(db)
    for i in range(2,502): conn.execute('INSERT INTO assessments VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(i,1,f'2026-01-01T00:00:00Z',f'2026-01-01T00:00:00Z','Walk',i,100,'Vegan',0,10,95,str(i)))
    conn.commit(); conn.close(); assert len(export_profile(1,str(db))['assessments'])==501

import unittest
import sqlite3
import os
from datetime import datetime, timedelta

# Import models and core functions
from sustainability_roadmap import (
    init_roadmap_db,
    SustainabilityRoadmap,
    RoadmapMilestone,
    create_roadmap,
    get_roadmap,
    get_active_roadmap_for_user,
    create_milestone,
    get_milestone,
    add_dependency,
    update_milestone_status,
    update_milestone_progress,
    evaluate_roadmap_statuses,
    update_roadmap_overall_progress,
    estimate_completion_dates,
    detect_missed_milestones,
    reschedule_missed_milestones,
    generate_personalized_roadmap,
    get_roadmap_graph_data,
    CircularDependencyError,
    MilestoneDependencyError,
    STATUS_LOCKED,
    STATUS_ACTIONABLE,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_MISSED,
    STATUS_SKIPPED,
    ROADMAP_ACTIVE,
    ROADMAP_COMPLETED,
    DEP_BLOCKING,
    DEP_SOFT
)

# For testing, we mock DB_NAME or set an environment variable. We'll patch database_connection.
from unittest.mock import patch
import sustainability_roadmap

TEST_DB = "test_roadmap.db"

class TestSustainabilityRoadmap(unittest.TestCase):
    
    def setUp(self):
        import uuid
        self.db_name = f"test_roadmap_{uuid.uuid4().hex}.db"
        sustainability_roadmap.DB_NAME = self.db_name
        
        init_roadmap_db(self.db_name)
        
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT)")
            conn.execute("INSERT INTO users (id, username) VALUES (1, 'test_user')")
            conn.commit()

    def tearDown(self):
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass

    def test_create_and_get_roadmap(self):
        roadmap = create_roadmap(1, "Test Roadmap")
        self.assertIsNotNone(roadmap)
        self.assertEqual(roadmap.title, "Test Roadmap")
        self.assertEqual(roadmap.user_id, 1)
        self.assertEqual(roadmap.status, ROADMAP_ACTIVE)
        
        fetched = get_roadmap(roadmap.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, roadmap.id)

    def test_create_and_get_milestone(self):
        rm = create_roadmap(1, "RM 1")
        ms = create_milestone(rm.id, "Milestone 1", "Desc", 10.0, "kg", 5, 10.0, None, "Energy")
        
        self.assertIsNotNone(ms)
        self.assertEqual(ms.title, "Milestone 1")
        self.assertEqual(ms.status, STATUS_LOCKED)
        
        fetched = get_milestone(ms.id)
        self.assertEqual(fetched.id, ms.id)
        
    def test_milestone_dependencies_and_circular_rejection(self):
        rm = create_roadmap(1, "RM deps")
        m1 = create_milestone(rm.id, "M1", "")
        m2 = create_milestone(rm.id, "M2", "")
        m3 = create_milestone(rm.id, "M3", "")
        
        add_dependency(m2.id, m1.id, DEP_BLOCKING)
        add_dependency(m3.id, m2.id, DEP_BLOCKING)
        
        ms3_fetched = get_milestone(m3.id)
        self.assertEqual(len(ms3_fetched.dependencies), 1)
        self.assertEqual(ms3_fetched.dependencies[0]["depends_on_id"], m2.id)
        
        # Test circular dependency detection
        with self.assertRaises(ValueError):
            add_dependency(m1.id, m3.id, DEP_BLOCKING)

    def test_evaluate_roadmap_statuses(self):
        rm = create_roadmap(1, "RM statuses")
        m1 = create_milestone(rm.id, "M1", "")
        m2 = create_milestone(rm.id, "M2", "")
        m3 = create_milestone(rm.id, "M3", "")
        
        add_dependency(m2.id, m1.id, DEP_BLOCKING)
        add_dependency(m3.id, m2.id, DEP_BLOCKING)
        
        evaluate_roadmap_statuses(rm.id)
        
        m1_f = get_milestone(m1.id)
        m2_f = get_milestone(m2.id)
        m3_f = get_milestone(m3.id)
        
        self.assertEqual(m1_f.status, STATUS_ACTIONABLE)
        self.assertEqual(m2_f.status, STATUS_LOCKED)
        self.assertEqual(m3_f.status, STATUS_LOCKED)
        
        # Complete M1
        update_milestone_progress(m1.id, 100.0)
        
        m1_f = get_milestone(m1.id)
        m2_f = get_milestone(m2.id)
        self.assertEqual(m1_f.status, STATUS_COMPLETED)
        self.assertEqual(m2_f.status, STATUS_ACTIONABLE)

    def test_alternative_pathways(self):
        rm = create_roadmap(1, "RM Alt Paths")
        m_root = create_milestone(rm.id, "Root", "")
        
        alt_group = "group1"
        m_alt1 = create_milestone(rm.id, "Alt 1", "", is_alternative_group=True, alternative_group_id=alt_group)
        m_alt2 = create_milestone(rm.id, "Alt 2", "", is_alternative_group=True, alternative_group_id=alt_group)
        
        add_dependency(m_alt1.id, m_root.id)
        add_dependency(m_alt2.id, m_root.id)
        
        # Start by completing root
        evaluate_roadmap_statuses(rm.id)
        update_milestone_progress(m_root.id, 100.0)
        
        # Start alt1
        update_milestone_progress(m_alt1.id, 10.0)
        
        m_alt1_f = get_milestone(m_alt1.id)
        m_alt2_f = get_milestone(m_alt2.id)
        
        self.assertEqual(m_alt1_f.status, STATUS_IN_PROGRESS)
        self.assertEqual(m_alt2_f.status, STATUS_SKIPPED)

    def test_detect_and_reschedule_missed_milestones(self):
        rm = create_roadmap(1, "RM Missed")
        now = datetime.now()
        past_date = now - timedelta(days=10) # 10 days ago, grace period is 7
        
        m1 = create_milestone(rm.id, "M1", "", target_date=past_date)
        evaluate_roadmap_statuses(rm.id) # makes it ACTIONABLE
        
        missed = detect_missed_milestones(rm.id)
        self.assertEqual(len(missed), 1)
        self.assertEqual(missed[0].id, m1.id)
        
        m1_f = get_milestone(m1.id)
        self.assertEqual(m1_f.status, STATUS_MISSED)
        
        reschedule_missed_milestones(rm.id, shift_days=14)
        m1_f2 = get_milestone(m1.id)
        
        self.assertEqual(m1_f2.status, STATUS_ACTIONABLE)
        self.assertTrue(m1_f2.target_date > now)

    def test_overall_progress_calculation(self):
        rm = create_roadmap(1, "RM Progress")
        m1 = create_milestone(rm.id, "M1", "", target_value=100.0, impact_score=10.0)
        m2 = create_milestone(rm.id, "M2", "", target_value=50.0, impact_score=30.0)
        
        evaluate_roadmap_statuses(rm.id)
        update_roadmap_overall_progress(rm.id)
        
        rm_f = get_roadmap(rm.id)
        self.assertEqual(rm_f.overall_progress, 0.0)
        
        update_milestone_progress(m1.id, 100.0) # 100% of m1 -> 10 / 40 impact -> 25% overall
        rm_f = get_roadmap(rm.id)
        self.assertAlmostEqual(rm_f.overall_progress, 25.0)
        
        update_milestone_progress(m2.id, 25.0) # 50% of m2 -> 15 / 40 impact -> 25 + 37.5 = 62.5%
        rm_f = get_roadmap(rm.id)
        self.assertAlmostEqual(rm_f.overall_progress, 62.5)
        
    def test_estimate_completion_dates(self):
        rm = create_roadmap(1, "RM Est")
        m1 = create_milestone(rm.id, "M1", "", difficulty=3)
        m2 = create_milestone(rm.id, "M2", "", difficulty=5)
        add_dependency(m2.id, m1.id, DEP_BLOCKING)
        
        estimate_completion_dates(rm.id)
        m1_f = get_milestone(m1.id)
        m2_f = get_milestone(m2.id)
        
        self.assertIsNotNone(m1_f.estimated_completion_date)
        self.assertIsNotNone(m2_f.estimated_completion_date)
        self.assertTrue(m2_f.estimated_completion_date > m1_f.estimated_completion_date)
        
    def test_generate_personalized_roadmap(self):
        # We'll just verify it runs and generates a valid roadmap with milestones
        rm = generate_personalized_roadmap(1)
        self.assertIsNotNone(rm)
        self.assertTrue(len(rm.milestones) > 0)
        
        graph = get_roadmap_graph_data(rm.id)
        self.assertTrue(len(graph["nodes"]) > 0)
        
    def test_edge_cases_empty_goals(self):
        # Even with no data, generate should fall back to defaults
        rm = generate_personalized_roadmap(999)
        self.assertIsNotNone(rm)
        self.assertTrue(len(rm.milestones) >= 3)
        
    def test_roadmap_completion_status(self):
        rm = create_roadmap(1, "RM Finish")
        m1 = create_milestone(rm.id, "M1", "")
        evaluate_roadmap_statuses(rm.id)
        update_milestone_progress(m1.id, 100.0)
        rm_f = get_roadmap(rm.id)
        self.assertEqual(rm_f.status, ROADMAP_COMPLETED)

if __name__ == '__main__':
    unittest.main()

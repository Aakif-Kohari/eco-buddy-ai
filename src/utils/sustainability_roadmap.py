"""
Sustainability Roadmap System

This module provides a comprehensive engine for generating, managing, and tracking
personalized sustainability roadmaps for users. It integrates with existing user goals,
habits, recommendations, and assessments to build a multi-stage dependency-aware graph
of milestones.

Features:
- Personalized roadmap generation
- Dependency resolution and circular dependency detection
- Target date and estimated completion calculations
- Difficulty and impact scoring models
- Alternative pathway simulation
- Missed milestone handling and rescheduling
"""

import sqlite3
import json
import logging
import math
import uuid
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Set, Tuple, Union

from src.core.database_connection import database_connection
import os
DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

logger = logging.getLogger(__name__)

# --- Enums and Constants ---
STATUS_LOCKED = "LOCKED"
STATUS_ACTIONABLE = "ACTIONABLE"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_COMPLETED = "COMPLETED"
STATUS_MISSED = "MISSED"
STATUS_SKIPPED = "SKIPPED"

ROADMAP_ACTIVE = "ACTIVE"
ROADMAP_COMPLETED = "COMPLETED"
ROADMAP_ABANDONED = "ABANDONED"
ROADMAP_ON_HOLD = "ON_HOLD"

DEP_BLOCKING = "BLOCKING"
DEP_SOFT = "SOFT"
DEP_RECOMMENDED = "RECOMMENDED"

CAT_TRANSPORT = "Transport"
CAT_ENERGY = "Energy"
CAT_DIET = "Diet"
CAT_WASTE = "Waste"
CAT_WATER = "Water"
CAT_GENERAL = "General"

DIFFICULTY_TRIVIAL = 1
DIFFICULTY_EASY = 3
DIFFICULTY_MODERATE = 5
DIFFICULTY_HARD = 8
DIFFICULTY_EXTREME = 10

DEFAULT_ROADMAP_DURATION_DAYS = 365
DEFAULT_MILESTONE_DURATION_DAYS = 30
MISSED_GRACE_PERIOD_DAYS = 7


class CircularDependencyError(ValueError):
    pass


class MilestoneDependencyError(ValueError):
    pass


# --- Models ---

class RoadmapMilestone:
    def __init__(
        self,
        id: Optional[int],
        roadmap_id: int,
        title: str,
        description: str,
        target_value: float,
        current_value: float,
        unit: str,
        difficulty: int,
        impact_score: float,
        status: str,
        target_date: Optional[datetime],
        estimated_completion_date: Optional[datetime],
        category: str,
        is_alternative_group: bool = False,
        alternative_group_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.roadmap_id = roadmap_id
        self.title = title
        self.description = description
        self.target_value = target_value
        self.current_value = current_value
        self.unit = unit
        self.difficulty = difficulty
        self.impact_score = impact_score
        self.status = status
        self.target_date = target_date
        self.estimated_completion_date = estimated_completion_date
        self.category = category
        self.is_alternative_group = is_alternative_group
        self.alternative_group_id = alternative_group_id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.dependencies: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "roadmap_id": self.roadmap_id,
            "title": self.title,
            "description": self.description,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "unit": self.unit,
            "difficulty": self.difficulty,
            "impact_score": self.impact_score,
            "status": self.status,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "estimated_completion_date": self.estimated_completion_date.isoformat() if self.estimated_completion_date else None,
            "category": self.category,
            "is_alternative_group": self.is_alternative_group,
            "alternative_group_id": self.alternative_group_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "dependencies": self.dependencies
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoadmapMilestone":
        def parse_date(d: Optional[str]) -> Optional[datetime]:
            if not d: return None
            try: return datetime.fromisoformat(d)
            except ValueError: return None

        milestone = cls(
            id=data.get("id"),
            roadmap_id=data.get("roadmap_id", 0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            target_value=data.get("target_value", 0.0),
            current_value=data.get("current_value", 0.0),
            unit=data.get("unit", ""),
            difficulty=data.get("difficulty", 5),
            impact_score=data.get("impact_score", 0.0),
            status=data.get("status", STATUS_LOCKED),
            target_date=parse_date(data.get("target_date")),
            estimated_completion_date=parse_date(data.get("estimated_completion_date")),
            category=data.get("category", CAT_GENERAL),
            is_alternative_group=data.get("is_alternative_group", False),
            alternative_group_id=data.get("alternative_group_id"),
            created_at=parse_date(data.get("created_at")),
            updated_at=parse_date(data.get("updated_at"))
        )
        milestone.dependencies = data.get("dependencies", [])
        return milestone


class SustainabilityRoadmap:
    def __init__(
        self,
        id: Optional[int],
        user_id: int,
        title: str,
        status: str,
        overall_progress: float,
        target_date: Optional[datetime],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.status = status
        self.overall_progress = overall_progress
        self.target_date = target_date
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.milestones: List[RoadmapMilestone] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "status": self.status,
            "overall_progress": self.overall_progress,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "milestones": [m.to_dict() for m in self.milestones]
        }


def init_roadmap_db(db_name: str = DB_NAME) -> None:
    with database_connection(db_name) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roadmaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                overall_progress REAL DEFAULT 0.0,
                target_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roadmap_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roadmap_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                target_value REAL DEFAULT 0.0,
                current_value REAL DEFAULT 0.0,
                unit TEXT,
                difficulty INTEGER DEFAULT 5,
                impact_score REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                target_date TIMESTAMP,
                estimated_completion_date TIMESTAMP,
                category TEXT,
                is_alternative_group INTEGER DEFAULT 0,
                alternative_group_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roadmap_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                milestone_id INTEGER NOT NULL,
                depends_on_id INTEGER NOT NULL,
                dependency_type TEXT DEFAULT 'BLOCKING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(milestone_id) REFERENCES roadmap_milestones(id) ON DELETE CASCADE,
                FOREIGN KEY(depends_on_id) REFERENCES roadmap_milestones(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_roadmap_user ON roadmaps(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_milestone_roadmap ON roadmap_milestones(roadmap_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dep_milestone ON roadmap_dependencies(milestone_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dep_depends_on ON roadmap_dependencies(depends_on_id)")
        
        conn.commit()


def _validate_no_circular_dependencies(dependencies: List[Tuple[int, int]]) -> None:
    graph: Dict[int, List[int]] = {}
    for ms_id, dep_id in dependencies:
        if dep_id not in graph: graph[dep_id] = []
        if ms_id not in graph: graph[ms_id] = []
        graph[dep_id].append(ms_id)
        
    visited: Set[int] = set()
    rec_stack: Set[int] = set()
    
    def is_cyclic(node: int) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if is_cyclic(neighbor): return True
            elif neighbor in rec_stack: return True
        rec_stack.remove(node)
        return False
        
    for node in graph:
        if node not in visited:
            if is_cyclic(node):
                raise CircularDependencyError(f"Circular dependency detected involving milestone {node}")


def _topological_sort(milestones: List[RoadmapMilestone], dependencies: List[Tuple[int, int]]) -> List[RoadmapMilestone]:
    _validate_no_circular_dependencies(dependencies)
    
    graph: Dict[int, List[int]] = {m.id: [] for m in milestones if m.id is not None}
    in_degree: Dict[int, int] = {m.id: 0 for m in milestones if m.id is not None}
    
    for ms_id, dep_id in dependencies:
        if dep_id in graph and ms_id in in_degree:
            graph[dep_id].append(ms_id)
            in_degree[ms_id] += 1
            
    queue = [n for n in in_degree if in_degree[n] == 0]
    sorted_order = []
    
    while queue:
        u = queue.pop(0)
        sorted_order.append(u)
        for v in graph.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                
    ms_map = {m.id: m for m in milestones if m.id is not None}
    return [ms_map[m_id] for m_id in sorted_order]


def get_roadmap_graph_data(roadmap_id: int) -> Dict[str, Any]:
    milestones = get_milestones_for_roadmap(roadmap_id)
    nodes = []
    edges = []
    for ms in milestones:
        nodes.append({
            "id": ms.id,
            "label": ms.title,
            "title": f"Status: {ms.status}\\nDifficulty: {ms.difficulty}/10",
            "group": ms.status,
            "category": ms.category,
            "value": ms.impact_score
        })
        for dep in ms.dependencies:
            edges.append({
                "from": dep["depends_on_id"],
                "to": ms.id,
                "label": dep["dependency_type"],
                "dashes": dep["dependency_type"] == DEP_SOFT
            })
    return {"nodes": nodes, "edges": edges}


def create_roadmap(user_id: int, title: str, target_date: Optional[datetime] = None) -> SustainabilityRoadmap:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        now = datetime.now()
        target = target_date or (now + timedelta(days=DEFAULT_ROADMAP_DURATION_DAYS))
        
        cursor.execute("""
            INSERT INTO roadmaps (user_id, title, status, target_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, title, ROADMAP_ACTIVE, target.isoformat(), now.isoformat(), now.isoformat()))
        roadmap_id = cursor.lastrowid
        conn.commit()
    return get_roadmap(roadmap_id)


def get_roadmap(roadmap_id: int) -> Optional[SustainabilityRoadmap]:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, title, status, overall_progress, target_date, created_at, updated_at
            FROM roadmaps WHERE id = ?
        """, (roadmap_id,))
        row = cursor.fetchone()
        if not row: return None
        
        def parse_dt(s): return datetime.fromisoformat(s) if s else None
        
        roadmap = SustainabilityRoadmap(
            id=row[0], user_id=row[1], title=row[2], status=row[3],
            overall_progress=row[4], target_date=parse_dt(row[5]),
            created_at=parse_dt(row[6]), updated_at=parse_dt(row[7])
        )
        roadmap.milestones = get_milestones_for_roadmap(roadmap_id)
        return roadmap


def get_active_roadmap_for_user(user_id: int) -> Optional[SustainabilityRoadmap]:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM roadmaps WHERE user_id = ? AND status = ? ORDER BY created_at DESC LIMIT 1", 
                       (user_id, ROADMAP_ACTIVE))
        row = cursor.fetchone()
        if not row: return None
        return get_roadmap(row[0])


def create_milestone(
    roadmap_id: int, 
    title: str, 
    description: str,
    target_value: float = 100.0,
    unit: str = "%",
    difficulty: int = 5,
    impact_score: float = 10.0,
    target_date: Optional[datetime] = None,
    category: str = CAT_GENERAL,
    is_alternative_group: bool = False,
    alternative_group_id: Optional[str] = None
) -> RoadmapMilestone:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute("""
            INSERT INTO roadmap_milestones (
                roadmap_id, title, description, target_value, current_value, unit,
                difficulty, impact_score, status, target_date, category,
                is_alternative_group, alternative_group_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            roadmap_id, title, description, target_value, unit,
            difficulty, impact_score, STATUS_LOCKED, 
            target_date.isoformat() if target_date else None,
            category, int(is_alternative_group), alternative_group_id,
            now.isoformat(), now.isoformat()
        ))
        ms_id = cursor.lastrowid
        conn.commit()
    return get_milestone(ms_id)


def get_milestone(milestone_id: int) -> Optional[RoadmapMilestone]:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, roadmap_id, title, description, target_value, current_value,
                   unit, difficulty, impact_score, status, target_date, 
                   estimated_completion_date, category, is_alternative_group, 
                   alternative_group_id, created_at, updated_at
            FROM roadmap_milestones WHERE id = ?
        """, (milestone_id,))
        row = cursor.fetchone()
        if not row: return None
        
        def parse_dt(s): return datetime.fromisoformat(s) if s else None
        
        ms = RoadmapMilestone(
            id=row[0], roadmap_id=row[1], title=row[2], description=row[3],
            target_value=row[4], current_value=row[5], unit=row[6],
            difficulty=row[7], impact_score=row[8], status=row[9],
            target_date=parse_dt(row[10]), estimated_completion_date=parse_dt(row[11]),
            category=row[12], is_alternative_group=bool(row[13]),
            alternative_group_id=row[14], created_at=parse_dt(row[15]),
            updated_at=parse_dt(row[16])
        )
        
        cursor.execute("""
            SELECT depends_on_id, dependency_type FROM roadmap_dependencies WHERE milestone_id = ?
        """, (milestone_id,))
        for dep_row in cursor.fetchall():
            ms.dependencies.append({
                "depends_on_id": dep_row[0],
                "dependency_type": dep_row[1]
            })
        return ms


def get_milestones_for_roadmap(roadmap_id: int) -> List[RoadmapMilestone]:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM roadmap_milestones WHERE roadmap_id = ?", (roadmap_id,))
        milestone_ids = [row[0] for row in cursor.fetchall()]
    return [get_milestone(ms_id) for ms_id in milestone_ids if get_milestone(ms_id)]


def add_dependency(milestone_id: int, depends_on_id: int, dep_type: str = DEP_BLOCKING) -> None:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        ms1 = get_milestone(milestone_id)
        ms2 = get_milestone(depends_on_id)
        if not ms1 or not ms2: raise ValueError("Invalid milestone IDs.")
        if ms1.roadmap_id != ms2.roadmap_id: raise ValueError("Cannot add dependencies between milestones in different roadmaps.")
        
        cursor.execute("""
            SELECT m1.id, d.depends_on_id 
            FROM roadmap_milestones m1
            JOIN roadmap_dependencies d ON m1.id = d.milestone_id
            WHERE m1.roadmap_id = ?
        """, (ms1.roadmap_id,))
        
        existing_deps = cursor.fetchall()
        test_deps = existing_deps + [(milestone_id, depends_on_id)]
        
        try:
            _validate_no_circular_dependencies(test_deps)
        except CircularDependencyError as e:
            raise ValueError(f"Adding this dependency would create a circular reference: {e}")
            
        cursor.execute("""
            INSERT INTO roadmap_dependencies (milestone_id, depends_on_id, dependency_type)
            VALUES (?, ?, ?)
        """, (milestone_id, depends_on_id, dep_type))
        conn.commit()


def update_milestone_status(milestone_id: int, status: str) -> None:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute("""
            UPDATE roadmap_milestones 
            SET status = ?, updated_at = ? 
            WHERE id = ?
        """, (status, now.isoformat(), milestone_id))
        conn.commit()
    ms = get_milestone(milestone_id)
    if ms: evaluate_roadmap_statuses(ms.roadmap_id)


def update_milestone_progress(milestone_id: int, progress: float) -> None:
    ms = get_milestone(milestone_id)
    if not ms: return
    if ms.status == STATUS_LOCKED:
        raise MilestoneDependencyError("Cannot update progress on a locked milestone.")
        
    new_val = min(progress, ms.target_value)
    new_val = max(0.0, new_val)
    
    new_status = ms.status
    if new_val >= ms.target_value: new_status = STATUS_COMPLETED
    elif new_val > 0 and ms.status == STATUS_ACTIONABLE: new_status = STATUS_IN_PROGRESS
        
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute("""
            UPDATE roadmap_milestones
            SET current_value = ?, status = ?, updated_at = ?
            WHERE id = ?
        """, (new_val, new_status, now.isoformat(), milestone_id))
        conn.commit()
        
    evaluate_roadmap_statuses(ms.roadmap_id)
    update_roadmap_overall_progress(ms.roadmap_id)


def evaluate_roadmap_statuses(roadmap_id: int) -> None:
    milestones = get_milestones_for_roadmap(roadmap_id)
    deps = []
    for ms in milestones:
        for dep in ms.dependencies:
            deps.append((ms.id, dep["depends_on_id"]))
            
    try:
        sorted_ms = _topological_sort(milestones, deps)
    except CircularDependencyError:
        logger.error(f"Circular dependency detected in roadmap {roadmap_id}")
        return
        
    ms_dict = {m.id: m for m in milestones}
    alt_groups_active = {}
    for m in milestones:
        if m.alternative_group_id and m.status in [STATUS_IN_PROGRESS, STATUS_COMPLETED]:
            alt_groups_active[m.alternative_group_id] = True
            
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        now = datetime.now()
        
        for m in sorted_ms:
            if m.status in [STATUS_COMPLETED, STATUS_SKIPPED, STATUS_MISSED]:
                continue
            if m.alternative_group_id and m.status in [STATUS_LOCKED, STATUS_ACTIONABLE]:
                if alt_groups_active.get(m.alternative_group_id, False):
                    cursor.execute("UPDATE roadmap_milestones SET status = ?, updated_at = ? WHERE id = ?",
                                   (STATUS_SKIPPED, now.isoformat(), m.id))
                    continue
            is_blocked = False
            for dep in m.dependencies:
                if dep["dependency_type"] == DEP_BLOCKING:
                    parent = ms_dict.get(dep["depends_on_id"])
                    if parent and parent.status not in [STATUS_COMPLETED, STATUS_SKIPPED]:
                        is_blocked = True
                        break
            new_status = STATUS_LOCKED if is_blocked else STATUS_ACTIONABLE
            if m.status != new_status and m.status != STATUS_IN_PROGRESS:
                cursor.execute("UPDATE roadmap_milestones SET status = ?, updated_at = ? WHERE id = ?",
                               (new_status, now.isoformat(), m.id))
                m.status = new_status
        conn.commit()


def update_roadmap_overall_progress(roadmap_id: int) -> None:
    milestones = get_milestones_for_roadmap(roadmap_id)
    if not milestones: return
    total_impact = 0.0
    achieved_impact = 0.0
    
    for ms in milestones:
        if ms.status != STATUS_SKIPPED:
            total_impact += ms.impact_score
            if ms.target_value > 0:
                progress_ratio = ms.current_value / ms.target_value
                achieved_impact += ms.impact_score * progress_ratio
                
    overall_progress = (achieved_impact / total_impact * 100.0) if total_impact > 0 else 0.0
    status = ROADMAP_ACTIVE
    all_done = all(m.status in [STATUS_COMPLETED, STATUS_SKIPPED] for m in milestones)
    if all_done and milestones: status = ROADMAP_COMPLETED
        
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE roadmaps SET overall_progress = ?, status = ?, updated_at = ?
            WHERE id = ?
        """, (overall_progress, status, datetime.now().isoformat(), roadmap_id))
        conn.commit()


def estimate_completion_dates(roadmap_id: int) -> None:
    milestones = get_milestones_for_roadmap(roadmap_id)
    deps = []
    for ms in milestones:
        for dep in ms.dependencies:
            deps.append((ms.id, dep["depends_on_id"]))
            
    try: sorted_ms = _topological_sort(milestones, deps)
    except CircularDependencyError: return
        
    estimated_dates = {}
    now = datetime.now()
    days_per_difficulty_point = 3.0
    
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        for m in sorted_ms:
            if m.status in [STATUS_COMPLETED, STATUS_SKIPPED]:
                estimated_dates[m.id] = m.updated_at
                continue
                
            latest_dep_date = now
            for dep in m.dependencies:
                if dep["dependency_type"] == DEP_BLOCKING:
                    parent_est = estimated_dates.get(dep["depends_on_id"])
                    if parent_est and parent_est > latest_dep_date:
                        latest_dep_date = parent_est
                        
            effort_days = m.difficulty * days_per_difficulty_point
            if m.status == STATUS_IN_PROGRESS and m.target_value > 0:
                remaining = 1.0 - (m.current_value / m.target_value)
                effort_days *= remaining
                
            est_date = latest_dep_date + timedelta(days=effort_days)
            estimated_dates[m.id] = est_date
            
            cursor.execute("""
                UPDATE roadmap_milestones SET estimated_completion_date = ? WHERE id = ?
            """, (est_date.isoformat(), m.id))
        conn.commit()


def detect_missed_milestones(roadmap_id: int) -> List[RoadmapMilestone]:
    milestones = get_milestones_for_roadmap(roadmap_id)
    now = datetime.now()
    missed = []
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        for m in milestones:
            if m.status in [STATUS_ACTIONABLE, STATUS_IN_PROGRESS, STATUS_LOCKED]:
                if m.target_date:
                    grace_date = m.target_date + timedelta(days=MISSED_GRACE_PERIOD_DAYS)
                    if now > grace_date:
                        cursor.execute("UPDATE roadmap_milestones SET status = ? WHERE id = ?",
                                       (STATUS_MISSED, m.id))
                        m.status = STATUS_MISSED
                        missed.append(m)
        conn.commit()
    if missed: evaluate_roadmap_statuses(roadmap_id)
    return missed


def reschedule_missed_milestones(roadmap_id: int, shift_days: int = 14) -> None:
    milestones = get_milestones_for_roadmap(roadmap_id)
    now = datetime.now()
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        for m in milestones:
            if m.status == STATUS_MISSED:
                new_date = now + timedelta(days=shift_days)
                cursor.execute("""
                    UPDATE roadmap_milestones 
                    SET status = ?, target_date = ?, updated_at = ?
                    WHERE id = ?
                """, (STATUS_LOCKED, new_date.isoformat(), now.isoformat(), m.id))
        conn.commit()
    evaluate_roadmap_statuses(roadmap_id)
    estimate_completion_dates(roadmap_id)


def generate_personalized_roadmap(user_id: int) -> SustainabilityRoadmap:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        active = get_active_roadmap_for_user(user_id)
        if active: return active
        
        # Determine priority categories based on assessment footprint
        try:
            cursor.execute("SELECT transport, distance, electricity, diet, flights FROM assessments WHERE user_id = ? ORDER BY date DESC LIMIT 1", (user_id,))
            assessment = cursor.fetchone()
        except sqlite3.OperationalError:
            assessment = None

        priorities = {CAT_TRANSPORT: 0, CAT_ENERGY: 0, CAT_DIET: 0, CAT_WASTE: 0, CAT_WATER: 0}
        if assessment:
            transport_type, distance, electricity, diet, flights = assessment
            if electricity and electricity > 300: priorities[CAT_ENERGY] += 5
            if transport_type in ['Car', 'SUV'] and distance and distance > 50: priorities[CAT_TRANSPORT] += 5
            if diet in ['Meat Heavy', 'Average']: priorities[CAT_DIET] += 3
        else:
            priorities = {CAT_TRANSPORT: 3, CAT_ENERGY: 3, CAT_DIET: 3, CAT_WASTE: 3, CAT_WATER: 3}
            
    rm_title = f"Sustainability Journey {datetime.now().year}"
    roadmap = create_roadmap(user_id, rm_title)
    now = datetime.now()
    
    # Generate generic Phase 1 (Awareness)
    m_audit = create_milestone(roadmap.id, "Conduct Home Energy Audit", "Identify power drains in your home.", 1.0, "audit", 2, 5.0, now + timedelta(days=7), CAT_ENERGY)
    m_diet1 = create_milestone(roadmap.id, "Meatless Mondays", "Commit to one plant-based day per week.", 4.0, "weeks", 3, 4.0, now + timedelta(days=30), CAT_DIET)
    m_waste = create_milestone(roadmap.id, "Setup Recycling Station", "Organize waste streams at home.", 1.0, "station", 1, 2.0, now + timedelta(days=14), CAT_WASTE)
    
    # Energy path
    if priorities[CAT_ENERGY] >= 3:
        m_led = create_milestone(roadmap.id, "Switch to LED Lighting", "Replace all major bulbs with LEDs.", 100.0, "%", 4, 8.0, now + timedelta(days=45), CAT_ENERGY)
        add_dependency(m_led.id, m_audit.id, DEP_BLOCKING)
        
        alt_group = str(uuid.uuid4())
        m_solar = create_milestone(roadmap.id, "Install Solar Panels", "Invest in residential solar.", 1.0, "system", 9, 25.0, now + timedelta(days=180), CAT_ENERGY, True, alt_group)
        m_green_grid = create_milestone(roadmap.id, "Switch to Green Tariff", "Opt-in to a 100% renewable energy plan.", 1.0, "plan", 3, 15.0, now + timedelta(days=60), CAT_ENERGY, True, alt_group)
        add_dependency(m_solar.id, m_audit.id, DEP_BLOCKING)
        add_dependency(m_green_grid.id, m_audit.id, DEP_BLOCKING)
        
    # Transport path
    if priorities[CAT_TRANSPORT] >= 3:
        m_commute = create_milestone(roadmap.id, "Optimize Commute", "Use public transit or carpool twice a week.", 8.0, "trips", 5, 12.0, now + timedelta(days=30), CAT_TRANSPORT)
        
        alt_group2 = str(uuid.uuid4())
        m_ev = create_milestone(roadmap.id, "Transition to EV", "Purchase or lease an electric vehicle.", 1.0, "vehicle", 8, 30.0, now + timedelta(days=365), CAT_TRANSPORT, True, alt_group2)
        m_ebike = create_milestone(roadmap.id, "Commute via E-Bike", "Purchase an E-Bike for local transport.", 1.0, "bike", 4, 15.0, now + timedelta(days=90), CAT_TRANSPORT, True, alt_group2)
        add_dependency(m_ev.id, m_commute.id, DEP_SOFT)
        add_dependency(m_ebike.id, m_commute.id, DEP_SOFT)
        
    evaluate_roadmap_statuses(roadmap.id)
    estimate_completion_dates(roadmap.id)
    update_roadmap_overall_progress(roadmap.id)
    
    return get_roadmap(roadmap.id)


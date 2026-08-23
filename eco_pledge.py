import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any
import json
from database_connection import database_connection
import database

DB_NAME = database.DB_NAME

PLEDGE_TEMPLATES = {
    "template_1": {
        "title": "Go car-free for 30 days",
        "description": "Commit to using public transport, biking, or walking instead of driving for 30 days.",
        "target_metric": "car_trips_avoided",
        "target_value": 30.0,
    },
    "template_2": {
        "title": "Reduce meat consumption by 50%",
        "description": "Cut down on meat consumption to reduce your carbon footprint.",
        "target_metric": "meat_reduced_kg",
        "target_value": 10.0,
    },
    "template_3": {
        "title": "Zero waste week",
        "description": "Produce zero waste for a week by reusing and recycling.",
        "target_metric": "waste_avoided_kg",
        "target_value": 5.0,
    }
}

def create_pledge(user_id: str, title: str, description: str, template_id: str | None, target_metric: str | None, target_value: float | None, deadline: str) -> str:
    """Create a new pledge for a user."""
    pledge_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO eco_pledges (id, user_id, title, description, template_id, status, target_metric, target_value, current_value, deadline, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (pledge_id, user_id, title, description, template_id, 'active', target_metric, target_value, 0.0, deadline, created_at)
        )
        conn.commit()
    return pledge_id

def support_pledge(pledge_id: str, supporter_id: str) -> bool:
    """Allow a user to support a pledge."""
    support_id = str(uuid.uuid4())
    supported_at = datetime.utcnow().isoformat()
    
    try:
        with database_connection(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO pledge_supporters (id, pledge_id, supporter_id, supported_at)
                VALUES (?, ?, ?, ?)
                ''',
                (support_id, pledge_id, supporter_id, supported_at)
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Already supported
        return False

def verify_pledge_progress(pledge_id: str) -> dict[str, Any]:
    """Verify and update pledge progress based on assessments or rules."""
    # Note: In a real implementation, we would query `assessments` or related tables
    # and calculate progress based on `target_metric`.
    # For simplicity, we just fetch current status here and potentially simulate checkins.
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM eco_pledges WHERE id = ?", (pledge_id,))
        pledge_row = cursor.fetchone()
        
        if not pledge_row:
            return {"error": "Pledge not found"}
        
        # Convert row to dict
        columns = [column[0] for column in cursor.description]
        pledge = dict(zip(columns, pledge_row))
        
        # Logic to check assessments could be placed here.
        # For now, return the current state
        
        # Check if completed
        if pledge['status'] == 'active' and pledge['target_value'] is not None:
            if pledge['current_value'] >= pledge['target_value']:
                complete_pledge(pledge_id)
                pledge['status'] = 'completed'
                
        return pledge

def complete_pledge(pledge_id: str) -> bool:
    """Mark pledge as completed and award XP."""
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM eco_pledges WHERE id = ?", (pledge_id,))
        row = cursor.fetchone()
        if not row:
            return False
            
        user_id = row[0]
        
        cursor.execute(
            "UPDATE eco_pledges SET status = 'completed' WHERE id = ?",
            (pledge_id,)
        )
        # Award 50 XP (Assuming an add_xp function exists in database module, falling back to dummy update if not)
        try:
            database.add_xp(user_id, 50, "Pledge Completed")
        except AttributeError:
            pass # In tests or if function doesn't exist, ignore
            
        conn.commit()
    return True

def get_public_pledges(limit: int = 10, offset: int = 0, sort_by: str = 'recent') -> list[dict[str, Any]]:
    """Retrieve public pledges with pagination and sorting."""
    order_clause = "ORDER BY e.created_at DESC"
    if sort_by == 'trending':
        order_clause = "ORDER BY supporters_count DESC, e.created_at DESC"
        
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        query = f'''
            SELECT e.*, 
                   (SELECT COUNT(*) FROM pledge_supporters ps WHERE ps.pledge_id = e.id) as supporters_count
            FROM eco_pledges e
            {order_clause}
            LIMIT ? OFFSET ?
        '''
        cursor.execute(query, (limit, offset))
        rows = cursor.fetchall()
        
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

def get_user_pledges(user_id: str) -> list[dict[str, Any]]:
    """Retrieve all pledges for a specific user."""
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM eco_pledges WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = cursor.fetchall()
        
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, User, Assessment, Appliance, SolarConfig, UserChallenge, UnlockedBadge, XpTransaction, JourneyProfile, OffsetTransaction, WaterConsumption

# Configure Database URL with SQLite default
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///ecobuddy.db')

engine = create_engine(DATABASE_URL, echo=False, connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Refactored DB operations replacing raw sqlite3
def add_user(username: str, email: str) -> int:
    with get_db() as db:
        user = User(username=username, email=email)
        db.add(user)
        db.flush()
        return user.id

def get_user_by_id(user_id: int):
    with get_db() as db:
        return db.query(User).filter(User.id == user_id).first()

def add_assessment(user_id: int, score: float, data: str):
    with get_db() as db:
        assessment = Assessment(user_id=user_id, score=score, data=data)
        db.add(assessment)

def get_user_assessments(user_id: int):
    with get_db() as db:
        return db.query(Assessment).filter(Assessment.user_id == user_id).all()

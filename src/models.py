from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessments = relationship('Assessment', back_populates='user', cascade='all, delete-orphan')
    appliances = relationship('Appliance', back_populates='user', cascade='all, delete-orphan')
    solar_configs = relationship('SolarConfig', back_populates='user', cascade='all, delete-orphan')
    user_challenges = relationship('UserChallenge', back_populates='user', cascade='all, delete-orphan')
    unlocked_badges = relationship('UnlockedBadge', back_populates='user', cascade='all, delete-orphan')
    xp_transactions = relationship('XpTransaction', back_populates='user', cascade='all, delete-orphan')
    journey_profile = relationship('JourneyProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    offset_transactions = relationship('OffsetTransaction', back_populates='user', cascade='all, delete-orphan')
    water_consumptions = relationship('WaterConsumption', back_populates='user', cascade='all, delete-orphan')


class Assessment(Base):
    __tablename__ = 'assessment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    score = Column(Float, nullable=False)
    data = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='assessments')


class Appliance(Base):
    __tablename__ = 'appliance'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    name = Column(String, nullable=False)
    power_watts = Column(Float, nullable=False)
    hours_used = Column(Float, nullable=False)

    user = relationship('User', back_populates='appliances')


class SolarConfig(Base):
    __tablename__ = 'solar_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    panel_capacity = Column(Float, nullable=False)
    efficiency = Column(Float, nullable=False)

    user = relationship('User', back_populates='solar_configs')


class UserChallenge(Base):
    __tablename__ = 'user_challenge'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    challenge_id = Column(String, nullable=False)
    status = Column(String, default='active')

    user = relationship('User', back_populates='user_challenges')


class UnlockedBadge(Base):
    __tablename__ = 'unlocked_badge'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    badge_name = Column(String, nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='unlocked_badges')


class XpTransaction(Base):
    __tablename__ = 'xp_transaction'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    amount = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='xp_transactions')


class JourneyProfile(Base):
    __tablename__ = 'journey_profile'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, unique=True)
    level = Column(Integer, default=1)
    total_xp = Column(Integer, default=0)

    user = relationship('User', back_populates='journey_profile')


class OffsetTransaction(Base):
    __tablename__ = 'offset_transaction'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    carbon_amount = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='offset_transactions')


class WaterConsumption(Base):
    __tablename__ = 'water_consumption'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    liters = Column(Float, nullable=False)
    recorded_date = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='water_consumptions')

"""
AI-Powered Eco-Mindfulness & Sustainable Behavior Change Engine
Contributor: Community Developer
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import logging
import json
import time
import random
import hashlib
from collections import defaultdict
from enum import Enum
import re

logger = logging.getLogger(__name__)

# ============================================================
# ENUMS AND CONSTANTS
# ============================================================

class Chronotype(Enum):
    MORNING = "morning_lark"
    EVENING = "night_owl"
    INTERMEDIATE = "intermediate"

class EmotionalState(Enum):
    CALM = "calm"
    ANXIOUS = "anxious"
    OVERWHELMED = "overwhelmed"
    MOTIVATED = "motivated"
    FATIGUED = "fatigued"
    RESILIENT = "resilient"

class HabitStage(Enum):
    PRE_CONTEMPLATION = "pre_contemplation"
    CONTEMPLATION = "contemplation"
    PREPARATION = "preparation"
    ACTION = "action"
    MAINTENANCE = "maintenance"
    RELAPSE = "relapse"

class InterventionType(Enum):
    NUDGE = "nudge"
    COACHING = "coaching"
    SOCIAL = "social"
    REWARD = "reward"
    REFLECTION = "reflection"
    PRIMING = "priming"

# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class UserDigitalTwin:
    """Digital representation of user behavior patterns"""
    user_id: int
    chronotype: Chronotype
    emotional_state: EmotionalState
    current_habits: Dict[str, HabitStage]
    behavior_history: List[Dict]
    sensitivity_level: float
    social_influence_score: float
    sustainability_index: float
    environment_preferences: Dict[str, float]
    decision_factors: Dict[str, float]
    learning_rate: float = 0.3
    memory_decay: float = 0.1

@dataclass
class MicroHabit:
    """Micro-habit structure for behavior change"""
    id: str
    name: str
    description: str
    category: str
    current_stage: HabitStage
    trigger_conditions: List[str]
    contextual_cues: Dict[str, str]
    reward_value: float
    difficulty_level: float
    completion_history: List[Dict]
    streak_days: int
    last_completed: Optional[datetime]

@dataclass
class EcoAnxietyProfile:
    """User eco-anxiety tracking profile"""
    user_id: int
    severity_level: float
    triggers: List[str]
    coping_strategies: List[Dict]
    resilience_score: float
    recent_patterns: List[Dict]
    intervention_history: List[Dict]
    progress_trajectory: List[float]

@dataclass
class SocialInfluenceNode:
    """Node in social influence network"""
    user_id: int
    influence_power: float
    susceptible_score: float
    connected_nodes: List[int]
    behavior_contagion_probability: float
    community_role: str
    impact_multiplier: float

@dataclass
class CircadianIntervention:
    """Time-optimized intervention"""
    intervention_id: str
    user_id: int
    ideal_time: datetime
    effective_window: Tuple[datetime, datetime]
    energy_level_required: float
    intervention_type: InterventionType
    content: str
    estimated_impact: float

# ============================================================
# BEHAVIOR DIGITAL TWIN ENGINE
# ============================================================

class BehaviorDigitalTwin:
    """
    Creates AI replicas of user behavior for simulation and prediction
    """
    
    def __init__(self):
        self.twins: Dict[int, UserDigitalTwin] = {}
        self.simulation_cache: Dict[str, List] = {}
        self.model_accuracy = 0.92
        
    def create_twin(self, user_id: int, initial_data: Dict) -> UserDigitalTwin:
        """Create digital twin of user"""
        twin = UserDigitalTwin(
            user_id=user_id,
            chronotype=initial_data.get('chronotype', Chronotype.INTERMEDIATE),
            emotional_state=EmotionalState.CALM,
            current_habits=initial_data.get('habits', {}),
            behavior_history=[],
            sensitivity_level=initial_data.get('sensitivity', 0.7),
            social_influence_score=initial_data.get('social_influence', 0.5),
            sustainability_index=initial_data.get('sustainability', 0.3),
            environment_preferences=initial_data.get('preferences', {}),
            decision_factors=self._initialize_decision_factors()
        )
        
        self.twins[user_id] = twin
        return twin
    
    def _initialize_decision_factors(self) -> Dict[str, float]:
        """Initialize decision-making factors"""
        return {
            'environmental_concern': 0.6,
            'habit_strength': 0.3,
            'social_influence': 0.5,
            'convenience_weight': 0.7,
            'cognitive_load': 0.4,
            'emotional_state_weight': 0.6
        }
    
    def predict_behavior(self, user_id: int, scenario: Dict) -> Dict:
        """Predict user behavior in a given scenario"""
        if user_id not in self.twins:
            return {'error': 'User twin not found'}
        
        twin = self.twins[user_id]
        
        # Calculate behavior probability based on decision factors
        base_probability = 0.5
        
        # Environmental concern factor
        env_factor = twin.decision_factors['environmental_concern'] * 0.3
        
        # Habit strength factor
        habit_factor = twin.decision_factors['habit_strength'] * 0.25
        
        # Social influence factor
        social_factor = twin.decision_factors['social_influence'] * 0.2
        
        # Cognitive load factor
        cognitive_factor = twin.decision_factors['cognitive_load'] * 0.15
        
        # Emotional state factor
        emotional_factor = twin.decision_factors['emotional_state_weight'] * 0.1
        
        # Apply scenario modifiers
        if scenario.get('social_pressure', False):
            social_factor *= 1.3
        if scenario.get('convenient', False):
            base_probability += 0.2
        if scenario.get('environmental_impact_visible', False):
            env_factor *= 1.4
        
        total_probability = (
            base_probability +
            env_factor +
            habit_factor +
            social_factor +
            cognitive_factor +
            emotional_factor
        )
        
        # Apply twin sensitivity and sustainability index
        total_probability *= twin.sensitivity_level
        total_probability *= (1 + twin.sustainability_index * 0.2)
        
        # Clamp probability
        predicted_behavior = max(0, min(1, total_probability))
        
        return {
            'predicted_probability': predicted_behavior,
            'confidence': self.model_accuracy,
            'behavior_expectation': 'sustainable' if predicted_behavior > 0.7 else 'needs_support',
            'key_factors': {
                'environmental_concern': env_factor,
                'habit_strength': habit_factor,
                'social_influence': social_factor,
                'cognitive_load': cognitive_factor,
                'emotional_state': emotional_factor
            }
        }
    
    def simulate_trajectory(self, user_id: int, days: int, interventions: List[Dict]) -> List[Dict]:
        """Simulate behavior trajectory over time"""
        if user_id not in self.twins:
            return []
        
        twin = self.twins[user_id]
        trajectory = []
        current_state = twin.sustainability_index
        
        for day in range(days):
            # Apply intervention effects if any
            day_interventions = [i for i in interventions if i.get('day') == day]
            
            # Natural behavior change (random walk with drift)
            drift = np.random.normal(0, 0.02)
            current_state += drift
            
            # Apply intervention effects
            for intervention in day_interventions:
                impact = intervention.get('impact', 0)
                if intervention.get('type') == 'coaching':
                    current_state += impact * 0.05
                elif intervention.get('type') == 'nudge':
                    current_state += impact * 0.02
                elif intervention.get('type') == 'social':
                    current_state += impact * 0.03
            
            # Clamp values
            current_state = max(0, min(1, current_state))
            
            trajectory.append({
                'day': day,
                'sustainability_index': current_state,
                'emotional_state': random.choice(list(EmotionalState)).value,
                'habit_adoption_rate': min(1, current_state * 1.2)
            })
        
        return trajectory
    
    def update_twin(self, user_id: int, new_data: Dict):
        """Update digital twin with new behavior data"""
        if user_id not in self.twins:
            return False
        
        twin = self.twins[user_id]
        
        # Update behavioral history
        twin.behavior_history.append({
            'timestamp': datetime.now(),
            'data': new_data
        })
        
        # Update sustainability index with learning
        if 'sustainability_index' in new_data:
            learning_gap = new_data['sustainability_index'] - twin.sustainability_index
            twin.sustainability_index += learning_gap * twin.learning_rate
        
        # Update decision factors with reinforcement learning
        if 'behavior_outcome' in new_data:
            outcome = new_data['behavior_outcome']
            if outcome == 'positive':
                # Reinforce factors
                for factor in twin.decision_factors:
                    twin.decision_factors[factor] = min(1, twin.decision_factors[factor] * 1.05)
            elif outcome == 'negative':
                # Decay factors
                for factor in twin.decision_factors:
                    twin.decision_factors[factor] = max(0.1, twin.decision_factors[factor] * 0.95)
        
        return True

# ============================================================
# MICRO-HABIT FORMATION ENGINE
# ============================================================

class MicroHabitEngine:
    """
    Advanced habit formation using spaced repetition and contextual cues
    """
    
    def __init__(self):
        self.habits: Dict[str, MicroHabit] = {}
        self.habit_templates = self._initialize_templates()
        self.spaced_repetition_schedule = [1, 2, 4, 7, 14, 21, 30]
        
    def _initialize_templates(self) -> Dict:
        """Initialize habit templates"""
        return {
            "morning_gratitude": {
                "name": "Morning Eco-Gratitude",
                "description": "Spend 2 minutes appreciating nature and environmental efforts",
                "category": "mindfulness",
                "difficulty": 0.3,
                "trigger_conditions": ["waking_up", "morning_routine"],
                "contextual_cues": {"location": "bedroom", "time": "morning"}
            },
            "eco_check_in": {
                "name": "Eco Check-In",
                "description": "Review daily environmental choices and carbon decisions",
                "category": "reflection",
                "difficulty": 0.5,
                "trigger_conditions": ["after_lunch", "mid_day"],
                "contextual_cues": {"location": "workspace", "time": "afternoon"}
            },
            "sustainable_switch": {
                "name": "Sustainable Switch",
                "description": "Identify one thing to switch to sustainable alternative today",
                "category": "action",
                "difficulty": 0.6,
                "trigger_conditions": ["morning_planning", "pre_work"],
                "contextual_cues": {"location": "anywhere", "time": "morning"}
            },
            "nature_moment": {
                "name": "Nature Moment",
                "description": "Spend 5 minutes connecting with nature or green space",
                "category": "mindfulness",
                "difficulty": 0.2,
                "trigger_conditions": ["afternoon_break", "stressful_moment"],
                "contextual_cues": {"location": "outdoor", "time": "anytime"}
            },
            "carbon_awareness": {
                "name": "Carbon Awareness Pause",
                "description": "Consciously consider environmental impact of next decision",
                "category": "reflection",
                "difficulty": 0.4,
                "trigger_conditions": ["decision_moment", "purchase_time"],
                "contextual_cues": {"location": "anywhere", "time": "anytime"}
            }
        }
    
    def create_habit(self, user_id: int, template_id: str) -> MicroHabit:
        """Create personalized habit from template"""
        template = self.habit_templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        habit_id = hashlib.md5(f"{user_id}_{template_id}_{datetime.now()}".encode()).hexdigest()[:8]
        
        habit = MicroHabit(
            id=habit_id,
            name=template['name'],
            description=template['description'],
            category=template['category'],
            current_stage=HabitStage.PRE_CONTEMPLATION,
            trigger_conditions=template['trigger_conditions'],
            contextual_cues=template['contextual_cues'],
            reward_value=template['difficulty'] * 10,
            difficulty_level=template['difficulty'],
            completion_history=[],
            streak_days=0,
            last_completed=None
        )
        
        self.habits[habit_id] = habit
        return habit
    
    def optimize_spaced_repetition(self, habit_id: str) -> List[datetime]:
        """Generate optimal spaced repetition schedule"""
        if habit_id not in self.habits:
            return []
        
        habit = self.habits[habit_id]
        current_date = datetime.now()
        
        # Adjust schedule based on habit difficulty
        difficulty_factor = 1 / (1 + habit.difficulty_level * 2)
        
        schedule = []
        for offset_days in self.spaced_repetition_schedule:
            adjusted_days = int(offset_days / (1 + difficulty_factor * 0.5))
            schedule.append(current_date + timedelta(days=max(1, adjusted_days)))
        
        return schedule
    
    def detect_contextual_triggers(self, user_state: Dict) -> List[MicroHabit]:
        """Detect appropriate habits based on context"""
        triggered_habits = []
        
        for habit in self.habits.values():
            if habit.current_stage in [HabitStage.ACTION, HabitStage.MAINTENANCE]:
                for trigger in habit.trigger_conditions:
                    if self._check_trigger(trigger, user_state):
                        triggered_habits.append(habit)
                        break
        
        return triggered_habits
    
    def _check_trigger(self, trigger: str, user_state: Dict) -> bool:
        """Check if trigger condition is met"""
        trigger_mapping = {
            'waking_up': lambda s: s.get('time_of_day') == 'morning' and s.get('activity') == 'waking',
            'morning_routine': lambda s: s.get('time_of_day') == 'morning' and s.get('activity') == 'routine',
            'after_lunch': lambda s: s.get('time_of_day') in ['afternoon'] and s.get('meal') == 'lunch',
            'mid_day': lambda s: s.get('time_of_day') == 'afternoon',
            'morning_planning': lambda s: s.get('time_of_day') == 'morning' and s.get('activity') == 'planning',
            'pre_work': lambda s: s.get('time_of_day') == 'morning' and s.get('activity') == 'pre_work',
            'afternoon_break': lambda s: s.get('time_of_day') == 'afternoon' and s.get('activity') == 'break',
            'stressful_moment': lambda s: s.get('stress_level', 0) > 0.7,
            'decision_moment': lambda s: s.get('decision_making', False),
            'purchase_time': lambda s: s.get('activity') == 'shopping'
        }
        
        check_func = trigger_mapping.get(trigger)
        if check_func:
            return check_func(user_state)
        return False
    
    def get_habit_formation_progress(self, habit_id: str) -> Dict:
        """Get progress metrics for habit formation"""
        if habit_id not in self.habits:
            return {}
        
        habit = self.habits[habit_id]
        completion_rate = len(habit.completion_history) / max(1, habit.streak_days)
        
        return {
            'habit_strength': min(1, completion_rate * 2),
            'adoption_stage': habit.current_stage.value,
            'streak_days': habit.streak_days,
            'completion_rate': completion_rate,
            'motivation_level': min(1, completion_rate * 1.5),
            'estimated_maintenance_time': self._estimate_maintenance_time(habit)
        }
    
    def _estimate_maintenance_time(self, habit: MicroHabit) -> int:
        """Estimate days until habit reaches maintenance stage"""
        days_to_maintenance = int(66 * (1 + habit.difficulty_level * 0.5))
        completed_days = len(habit.completion_history)
        return max(0, days_to_maintenance - completed_days)

# ============================================================
# ECO-ANXIETY MANAGEMENT SYSTEM
# ============================================================

class EcoAnxietyManager:
    """
    AI-powered eco-anxiety detection and management
    """
    
    def __init__(self):
        self.profiles: Dict[int, EcoAnxietyProfile] = {}
        self.coping_strategies = self._initialize_strategies()
        self.anxiety_patterns = self._initialize_patterns()
    
    def _initialize_strategies(self) -> Dict:
        """Initialize coping strategies"""
        return {
            "mindfulness_breathing": {
                "name": "Mindful Breathing",
                "description": "Practice 5-minute breathing exercise to reduce anxiety",
                "effectiveness": 0.85,
                "duration_minutes": 5,
                "best_for": ["overwhelmed", "anxious"]
            },
            "nature_connection": {
                "name": "Nature Connection",
                "description": "Engage with nature through observation or virtual nature",
                "effectiveness": 0.80,
                "duration_minutes": 10,
                "best_for": ["anxious", "fatigued"]
            },
            "action_reframing": {
                "name": "Action Reframing",
                "description": "Focus on individual actions and their positive impact",
                "effectiveness": 0.75,
                "duration_minutes": 7,
                "best_for": ["overwhelmed", "anxious"]
            },
            "community_connection": {
                "name": "Community Connection",
                "description": "Connect with others in eco-community",
                "effectiveness": 0.70,
                "duration_minutes": 15,
                "best_for": ["anxious", "fatigued"]
            },
            "gratitude_practice": {
                "name": "Gratitude Practice",
                "description": "List environmental wins and positive contributions",
                "effectiveness": 0.80,
                "duration_minutes": 3,
                "best_for": ["motivated", "calm"]
            }
        }
    
    def _initialize_patterns(self) -> Dict:
        """Initialize anxiety patterns"""
        return {
            "information_overload": {
                "triggers": ["negative_news", "climate_data", "doomsday_scenarios"],
                "symptoms": ["overwhelmed", "hopelessness", "avoidance"],
                "intensity": 0.8
            },
            "action_guilt": {
                "triggers": ["carbon_impact", "consumer_decisions", "lifestyle_choices"],
                "symptoms": ["guilt", "anxiety", "perfectionism"],
                "intensity": 0.7
            },
            "future_uncertainty": {
                "triggers": ["future_planning", "children_concern", "long_term_impact"],
                "symptoms": ["worry", "dread", "uncertainty"],
                "intensity": 0.9
            }
        }
    
    def detect_anxiety(self, user_id: int, user_input: Dict) -> Dict:
        """Detect eco-anxiety from user input"""
        input_text = user_input.get('text', '').lower()
        user_activities = user_input.get('activities', [])
        
        anxiety_score = 0
        detected_patterns = []
        
        # Check text for anxiety indicators
        anxiety_keywords = ['worried', 'anxious', 'overwhelmed', 'hopeless', 
                            'scared', 'fear', 'guilty', 'ashamed', 'helpless']
        
        for keyword in anxiety_keywords:
            if keyword in input_text:
                anxiety_score += 0.1
        
        # Check for triggers
        for pattern_name, pattern in self.anxiety_patterns.items():
            trigger_match = any(trigger in input_text for trigger in pattern['triggers'])
            if trigger_match:
                anxiety_score += pattern['intensity'] * 0.3
                detected_patterns.append(pattern_name)
        
        # Check activities
        if 'news_reading' in user_activities:
            anxiety_score += 0.2
        if 'climate_reading' in user_activities:
            anxiety_score += 0.3
        
        anxiety_score = min(1, anxiety_score)
        
        # Determine emotional state
        if anxiety_score > 0.7:
            emotional_state = EmotionalState.OVERWHELMED
        elif anxiety_score > 0.4:
            emotional_state = EmotionalState.ANXIOUS
        else:
            emotional_state = EmotionalState.CALM
        
        return {
            'anxiety_score': anxiety_score,
            'emotional_state': emotional_state,
            'detected_patterns': detected_patterns,
            'severity': 'high' if anxiety_score > 0.7 else 'medium' if anxiety_score > 0.4 else 'low'
        }
    
    def get_coping_strategy(self, emotional_state: EmotionalState, preferences: Dict) -> Dict:
        """Get personalized coping strategy"""
        strategies = []
        
        # Filter strategies based on emotional state
        for strategy_id, strategy in self.coping_strategies.items():
            if emotional_state.value in strategy['best_for']:
                strategies.append(strategy)
        
        if not strategies:
            strategies = list(self.coping_strategies.values())
        
        # Rank by effectiveness and duration preference
        strategies.sort(key=lambda x: (
            x['effectiveness'],
            -abs(x['duration_minutes'] - preferences.get('preferred_duration', 10))
        ), reverse=True)
        
        best_strategy = strategies[0] if strategies else None
        
        if best_strategy:
            return {
                'strategy': best_strategy,
                'confidence': best_strategy['effectiveness'],
                'estimated_relief': best_strategy['effectiveness'] * 0.9
            }
        
        return {'strategy': None, 'confidence': 0, 'estimated_relief': 0}
    
    def track_progress(self, user_id: int, intervention_result: Dict) -> float:
        """Track and update anxiety reduction progress"""
        if user_id not in self.profiles:
            self.profiles[user_id] = EcoAnxietyProfile(
                user_id=user_id,
                severity_level=0.5,
                triggers=[],
                coping_strategies=[],
                resilience_score=0.3,
                recent_patterns=[],
                intervention_history=[],
                progress_trajectory=[0.5]
            )
        
        profile = self.profiles[user_id]
        
        # Update history
        profile.intervention_history.append({
            'timestamp': datetime.now(),
            'intervention': intervention_result,
            'effectiveness': intervention_result.get('effectiveness', 0.5)
        })
        
        # Update resilience score
        if intervention_result.get('effectiveness', 0) > 0.7:
            profile.resilience_score = min(1, profile.resilience_score + 0.05)
        else:
            profile.resilience_score = max(0, profile.resilience_score - 0.02)
        
        # Update severity
        profile.severity_level = max(0, profile.severity_level - intervention_result.get('effectiveness', 0) * 0.1)
        
        # Update trajectory
        profile.progress_trajectory.append(profile.severity_level)
        
        return profile.resilience_score

# ============================================================
# SOCIAL CONTAGION INFLUENCE MAPPER
# ============================================================

class SocialContagionMapper:
    """
    Analyzes and predicts sustainable behavior spread through social networks
    """
    
    def __init__(self):
        self.network: Dict[int, SocialInfluenceNode] = {}
        self.interaction_matrix: Dict[Tuple[int, int], float] = {}
        self.contagion_history: List[Dict] = []
    
    def add_user_to_network(self, user_id: int, connections: List[int], influence: float = 0.5):
        """Add user to social influence network"""
        node = SocialInfluenceNode(
            user_id=user_id,
            influence_power=influence,
            susceptible_score=0.3,
            connected_nodes=connections,
            behavior_contagion_probability=0.4,
            community_role='member',
            impact_multiplier=1.0
        )
        
        self.network[user_id] = node
        
        # Update interaction matrix
        for connection in connections:
            self.interaction_matrix[(user_id, connection)] = random.uniform(0.1, 1.0)
            self.interaction_matrix[(connection, user_id)] = random.uniform(0.1, 1.0)
    
    def predict_contagion_path(self, source_user_id: int, behavior_type: str) -> Dict:
        """Predict how behavior spreads through network"""
        if source_user_id not in self.network:
            return {'error': 'User not in network'}
        
        source = self.network[source_user_id]
        contagion_pattern = []
        affected_users = set()
        
        # BFS simulation with contagion probability
        queue = [(source_user_id, 0)]
        visited = {source_user_id}
        
        while queue and len(affected_users) < 50:
            current_id, depth = queue.pop(0)
            current = self.network[current_id]
            
            # Check each connection
            for connection_id in current.connected_nodes:
                if connection_id in visited:
                    continue
                
                # Calculate contagion probability
                interaction_strength = self.interaction_matrix.get((current_id, connection_id), 0.3)
                influence_factor = current.influence_power * interaction_strength
                susceptibility = self.network[connection_id].susceptible_score
                
                contagion_prob = susceptibility * influence_factor * current.behavior_contagion_probability
                
                # Decide if behavior spreads
                if random.random() < contagion_prob:
                    affected_users.add(connection_id)
                    visited.add(connection_id)
                    queue.append((connection_id, depth + 1))
                    
                    contagion_pattern.append({
                        'user_id': connection_id,
                        'depth': depth + 1,
                        'probability': contagion_prob,
                        'influencer': current_id
                    })
        
        # Calculate network impact
        total_impact = len(affected_users) * source.impact_multiplier
        avg_depth = np.mean([p['depth'] for p in contagion_pattern]) if contagion_pattern else 0
        
        return {
            'affected_users': len(affected_users),
            'contagion_pattern': contagion_pattern,
            'total_impact': total_impact,
            'average_depth': avg_depth,
            'network_reach': len(affected_users) / max(1, len(self.network)),
            'predicted_behavior_adoption': min(1, total_impact / 100)
        }
    
    def amplify_social_impact(self, user_id: int, multiplier: float):
        """Amplify user's social influence"""
        if user_id in self.network:
            self.network[user_id].impact_multiplier = multiplier
            self.network[user_id].influence_power = min(1, self.network[user_id].influence_power * multiplier)

# ============================================================
# CIRCADIAN COACHING SYSTEM
# ============================================================

class CircadianCoach:
    """
    Time-optimized coaching based on biological rhythms
    """
    
    def __init__(self):
        self.chronotypes = {}
        self.intervention_schedule: Dict[int, List[CircadianIntervention]] = defaultdict(list)
    
    def detect_chronotype(self, user_id: int, sleep_data: Dict) -> Chronotype:
        """Detect user's chronotype from sleep patterns"""
        sleep_start = sleep_data.get('sleep_start', 23)
        sleep_end = sleep_data.get('sleep_end', 7)
        
        # Calculate midpoint of sleep
        if sleep_start > sleep_end:
            sleep_midpoint = (sleep_start + sleep_end + 24) / 2
        else:
            sleep_midpoint = (sleep_start + sleep_end) / 2
        
        sleep_midpoint = sleep_midpoint % 24
        
        if sleep_midpoint < 3:
            chronotype = Chronotype.MORNING
        elif sleep_midpoint < 6:
            chronotype = Chronotype.INTERMEDIATE
        else:
            chronotype = Chronotype.EVENING
        
        self.chronotypes[user_id] = chronotype
        return chronotype
    
    def calculate_energy_curve(self, chronotype: Chronotype) -> np.ndarray:
        """Calculate energy level curve throughout day"""
        hours = np.arange(0, 24)
        
        if chronotype == Chronotype.MORNING:
            # Peak energy early
            energy = 10 * np.exp(-((hours - 8) ** 2) / (2 * 6 ** 2))
            energy += 5 * np.exp(-((hours - 14) ** 2) / (2 * 4 ** 2))
        elif chronotype == Chronotype.EVENING:
            # Peak energy late
            energy = 8 * np.exp(-((hours - 12) ** 2) / (2 * 5 ** 2))
            energy += 7 * np.exp(-((hours - 20) ** 2) / (2 * 4 ** 2))
        else:
            # Intermediate
            energy = 9 * np.exp(-((hours - 10) ** 2) / (2 * 5 ** 2))
            energy += 6 * np.exp(-((hours - 16) ** 2) / (2 * 4 ** 2))
        
        # Normalize
        energy = energy / energy.max()
        return energy
    
    def optimize_intervention_timing(self, user_id: int, intervention_type: InterventionType) -> CircadianIntervention:
        """Find optimal time for intervention based on chronotype"""
        chronotype = self.chronotypes.get(user_id, Chronotype.INTERMEDIATE)
        energy_curve = self.calculate_energy_curve(chronotype)
        
        # Different interventions have different optimal times
        type_timings = {
            InterventionType.COACHING: 10,  # 10 AM
            InterventionType.NUDGE: 9,       # 9 AM
            InterventionType.REFLECTION: 16, # 4 PM
            InterventionType.SOCIAL: 18,     # 6 PM
            InterventionType.REWARD: 20,     # 8 PM
            InterventionType.PRIMING: 7      # 7 AM
        }
        
        base_hour = type_timings.get(intervention_type, 12)
        
        # Adjust timing based on chronotype
        if chronotype == Chronotype.MORNING:
            adjusted_hour = max(6, min(12, base_hour - 1))
        elif chronotype == Chronotype.EVENING:
            adjusted_hour = max(14, min(22, base_hour + 2))
        else:
            adjusted_hour = base_hour
        
        # Find time with highest energy near adjusted hour
        best_hour = adjusted_hour
        best_energy = energy_curve[adjusted_hour]
        
        for hour_offset in range(-2, 3):
            hour = (adjusted_hour + hour_offset) % 24
            if energy_curve[hour] > best_energy:
                best_energy = energy_curve[hour]
                best_hour = hour
        
        # Create intervention
        today = datetime.now().replace(hour=best_hour, minute=0, second=0, microsecond=0)
        ideal_time = today + timedelta(hours=best_hour)
        
        intervention = CircadianIntervention(
            intervention_id=hashlib.md5(f"{user_id}_{intervention_type.value}_{best_hour}".encode()).hexdigest()[:8],
            user_id=user_id,
            ideal_time=ideal_time,
            effective_window=(ideal_time - timedelta(hours=1), ideal_time + timedelta(hours=1)),
            energy_level_required=0.6,
            intervention_type=intervention_type,
            content=self._generate_intervention_content(intervention_type, chronotype),
            estimated_impact=best_energy * 0.9
        )
        
        self.intervention_schedule[user_id].append(intervention)
        return intervention
    
    def _generate_intervention_content(self, intervention_type: InterventionType, chronotype: Chronotype) -> str:
        """Generate personalized intervention content"""
        templates = {
            InterventionType.COACHING: [
                "🌱 Let's take a mindful moment to check your environmental intentions.",
                "💫 Reflect on your sustainable choices today - every action matters.",
                "🌟 You have the power to make eco-conscious decisions. How will you use it today?"
            ],
            InterventionType.NUDGE: [
                "🌿 Consider choosing the sustainable option in your next decision.",
                "♻️ Small choices add up. What green choice will you make now?",
                "🌍 Your environmental impact can be reduced with one simple switch."
            ],
            InterventionType.REFLECTION: [
                "🤔 Reflect on your environmental choices today. What went well?",
                "📝 Take a moment to journal your eco-actions and feelings.",
                "💭 How did your sustainable choices impact your day?"
            ],
            InterventionType.SOCIAL: [
                "🌐 Share your sustainable actions with the community!",
                "👥 Connect with others who care about the environment.",
                "💚 Join the conversation about eco-friendly living."
            ],
            InterventionType.REWARD: [
                "🎉 Celebrate your sustainable actions! You're making a difference.",
                "🏆 Your eco-commitments are building a better future.",
                "⭐ Every positive action creates ripples of change."
            ],
            InterventionType.PRIMING: [
                "💭 Start your day with a sustainable mindset.",
                "🌟 Your choices today shape tomorrow's world.",
                "🌱 You are part of a global community of change-makers."
            ]
        }
        
        messages = templates.get(intervention_type, templates[InterventionType.COACHING])
        
        # Add chronotype-specific flavor
        if chronotype == Chronotype.MORNING:
            suffix = " Start your day with intention."
        elif chronotype == Chronotype.EVENING:
            suffix = " Consider your choices as you wind down."
        else:
            suffix = " Stay focused on your sustainable journey."
        
        return random.choice(messages) + suffix

# ============================================================
# MAIN UI COMPONENT
# ============================================================

class EcoMindfulnessUI:
    """
    Complete UI for eco-mindfulness and behavior change system
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.twin_engine = BehaviorDigitalTwin()
        self.habit_engine = MicroHabitEngine()
        self.anxiety_manager = EcoAnxietyManager()
        self.social_mapper = SocialContagionMapper()
        self.circadian_coach = CircadianCoach()
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        if 'mindfulness_data' not in st.session_state:
            st.session_state.mindfulness_data = {
                'twin_created': False,
                'habits': [],
                'anxiety_profile': None,
                'social_network': [],
                'interventions': []
            }
    
    def render(self):
        """Render the complete UI"""
        st.markdown("""
        <style>
        .mindfulness-header {
            background: linear-gradient(135deg, #0f172a, #1a2e2a);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            border: 1px solid rgba(74, 222, 128, 0.3);
            text-align: center;
        }
        .mindfulness-header h2 {
            color: #4ade80;
            margin: 0;
            font-size: 32px;
        }
        .mindfulness-header p {
            color: #94a3b8;
            margin: 5px 0 0 0;
        }
        .habit-card {
            background: #0f172a;
            padding: 18px;
            border-radius: 12px;
            border: 1px solid rgba(74, 222, 128, 0.15);
            margin-bottom: 12px;
            transition: all 0.3s ease;
        }
        .habit-card:hover {
            border-color: #4ade80;
        }
        .stage-indicator {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }
        .energy-bar {
            height: 6px;
            background: rgba(74, 222, 128, 0.2);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 5px;
        }
        .energy-fill {
            height: 100%;
            background: linear-gradient(90deg, #4ade80, #86efac);
            border-radius: 3px;
            transition: width 0.5s ease;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown("""
        <div class="mindfulness-header">
            <h2>🧘 Eco-Mindfulness & Behavior Change</h2>
            <p>AI-powered psychology for sustainable habit formation and eco-wellness</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Main tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🧠 Digital Twin",
            "🔄 Micro-Habits",
            "🌿 Eco-Anxiety",
            "🌐 Social Contagion",
            "⏰ Circadian Coach"
        ])
        
        with tab1:
            self._render_digital_twin()
        
        with tab2:
            self._render_micro_habits()
        
        with tab3:
            self._render_eco_anxiety()
        
        with tab4:
            self._render_social_contagion()
        
        with tab5:
            self._render_circadian_coach()
    
    def _render_digital_twin(self):
        """Render digital twin interface"""
        st.subheader("🧠 Your Digital Twin")
        st.write("AI replica of your behavior patterns for personalized simulation and prediction")
        
        if not st.session_state.mindfulness_data['twin_created']:
            if st.button("🚀 Create Your Digital Twin", use_container_width=True):
                initial_data = {
                    'chronotype': random.choice(list(Chronotype)),
                    'sensitivity': random.uniform(0.4, 0.9),
                    'social_influence': random.uniform(0.3, 0.7),
                    'sustainability': random.uniform(0.2, 0.6),
                    'habits': {},
                    'preferences': {
                        'environmental_concern': random.uniform(0.3, 0.8)
                    }
                }
                
                twin = self.twin_engine.create_twin(self.user_id, initial_data)
                st.session_state.mindfulness_data['twin_created'] = True
                st.success("✅ Digital twin created successfully!")
                st.rerun()
        
        if st.session_state.mindfulness_data['twin_created']:
            twin = self.twin_engine.twins.get(self.user_id)
            if twin:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Sustainability Index", f"{twin.sustainability_index*100:.1f}%")
                    st.metric("Sensitivity Level", f"{twin.sensitivity_level*100:.1f}%")
                
                with col2:
                    st.metric("Social Influence", f"{twin.social_influence_score*100:.1f}%")
                    st.metric("Learning Rate", f"{twin.learning_rate*100:.1f}%")
                
                with col3:
                    st.metric("Chronotype", twin.chronotype.value.replace('_', ' ').title())
                    st.metric("Model Accuracy", f"{self.twin_engine.model_accuracy*100:.1f}%")
                
                # Behavior prediction
                st.markdown("### 🔮 Behavior Prediction")
                
                scenario_col1, scenario_col2 = st.columns(2)
                with scenario_col1:
                    social_pressure = st.checkbox("Social Pressure")
                    convenient = st.checkbox("Convenient Option")
                with scenario_col2:
                    env_impact_visible = st.checkbox("Environmental Impact Visible")
                    scenario_name = st.selectbox("Scenario Type", ["Daily Decision", "Shopping Choice", "Travel Planning"])
                
                if st.button("🔮 Predict Behavior", use_container_width=True):
                    scenario = {
                        'social_pressure': social_pressure,
                        'convenient': convenient,
                        'environmental_impact_visible': env_impact_visible
                    }
                    
                    prediction = self.twin_engine.predict_behavior(self.user_id, scenario)
                    
                    st.markdown(f"""
                    <div style="background: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid {'#4ade80' if prediction['behavior_expectation'] == 'sustainable' else '#f87171'};">
                        <h4 style="color: {'#4ade80' if prediction['behavior_expectation'] == 'sustainable' else '#f87171'};">
                            {'🌱 Sustainable Choice Expected' if prediction['behavior_expectation'] == 'sustainable' else '⚠️ Needs Support'}
                        </h4>
                        <p style="color: #94a3b8;">Probability: {prediction['predicted_probability']*100:.1f}%</p>
                        <p style="color: #94a3b8;">Confidence: {prediction['confidence']*100:.1f}%</p>
                        <div style="margin-top: 10px;">
                            <p style="color: #94a3b8; font-size: 13px;">Key Factors:</p>
                            {''.join([f'<span style="background: rgba(74,222,128,0.1); color: #4ade80; padding: 2px 10px; border-radius: 10px; font-size: 11px; margin: 2px;">📊 {k}: {v:.2f}</span>' for k, v in prediction['key_factors'].items()])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Trajectory simulation
                st.markdown("### 📈 Behavior Trajectory")
                
                days = st.slider("Simulation Days", 7, 90, 30)
                
                if st.button("📊 Simulate Trajectory", use_container_width=True):
                    interventions = [
                        {'day': i, 'type': 'coaching' if i % 7 == 0 else 'nudge' if i % 3 == 0 else None,
                         'impact': random.uniform(0.1, 0.3)}
                        for i in range(days) if i % 2 == 0
                    ]
                    interventions = [i for i in interventions if i['type']]
                    
                    trajectory = self.twin_engine.simulate_trajectory(self.user_id, days, interventions)
                    
                    if trajectory:
                        df = pd.DataFrame(trajectory)
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df['day'],
                            y=df['sustainability_index'] * 100,
                            mode='lines+markers',
                            name='Sustainability Index',
                            line=dict(color='#4ade80', width=2)
                        ))
                        fig.add_trace(go.Scatter(
                            x=df['day'],
                            y=df['habit_adoption_rate'] * 100,
                            mode='lines+markers',
                            name='Habit Adoption Rate',
                            line=dict(color='#60a5fa', width=2, dash='dash')
                        ))
                        
                        fig.update_layout(
                            title="Predicted Sustainability Trajectory",
                            xaxis_title="Days",
                            yaxis_title="Percentage (%)",
                            height=350,
                            template='plotly_dark',
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
    
    def _render_micro_habits(self):
        """Render micro-habit formation interface"""
        st.subheader("🔄 Micro-Habit Formation Engine")
        st.write("Optimized habit formation using spaced repetition and contextual triggers")
        
        col1, col2 = st.columns([2, 1])
        
        with col2:
            template_options = {
                "morning_gratitude": "🌅 Morning Eco-Gratitude",
                "eco_check_in": "✅ Eco Check-In", 
                "sustainable_switch": "🔄 Sustainable Switch",
                "nature_moment": "🌿 Nature Moment",
                "carbon_awareness": "💚 Carbon Awareness"
            }
            selected_template = st.selectbox("Select Habit Template", list(template_options.keys()), format_func=lambda x: template_options[x])
            
            if st.button("➕ Add Habit", use_container_width=True):
                habit = self.habit_engine.create_habit(self.user_id, selected_template)
                st.session_state.mindfulness_data['habits'].append(habit.id)
                st.success(f"✅ Habit '{habit.name}' added!")
                st.rerun()
        
        with col1:
            st.markdown("### 📋 Your Habits")
            
            habits = self.habit_engine.habits
            if habits:
                for habit_id, habit in habits.items():
                    stage_colors = {
                        'pre_contemplation': '#94a3b8',
                        'contemplation': '#60a5fa',
                        'preparation': '#fbbf24',
                        'action': '#4ade80',
                        'maintenance': '#34d399',
                        'relapse': '#f87171'
                    }
                    
                    progress = self.habit_engine.get_habit_formation_progress(habit_id)
                    
                    st.markdown(f"""
                    <div class="habit-card">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <h4 style="color: #4ade80; margin: 0;">{habit.name}</h4>
                                <p style="color: #94a3b8; font-size: 13px; margin: 3px 0;">{habit.description}</p>
                            </div>
                            <span class="stage-indicator" style="background: {stage_colors.get(habit.current_stage.value, '#94a3b8')}20; color: {stage_colors.get(habit.current_stage.value, '#94a3b8')};">
                                {habit.current_stage.value.replace('_', ' ').title()}
                            </span>
                        </div>
                        <div style="display: flex; gap: 20px; font-size: 12px; color: #94a3b8; margin-top: 8px;">
                            <span>🔥 Streak: {habit.streak_days} days</span>
                            <span>💪 Strength: {progress['habit_strength']*100:.0f}%</span>
                            <span>📈 Completion: {progress['completion_rate']*100:.0f}%</span>
                        </div>
                        <div class="energy-bar">
                            <div class="energy-fill" style="width: {progress['habit_strength']*100}%;"></div>
                        </div>
                        <div style="margin-top: 8px; display: flex; gap: 5px;">
                            {''.join([f'<span style="background: rgba(74,222,128,0.1); color: #4ade80; padding: 2px 8px; border-radius: 8px; font-size: 10px;">#{trigger}</span>' for trigger in habit.trigger_conditions[:2]])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No habits yet. Add one to start your formation journey!")
    
    def _render_eco_anxiety(self):
        """Render eco-anxiety management interface"""
        st.subheader("🌿 Eco-Anxiety Management")
        st.write("AI-powered detection and personalized coping strategies")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 💭 How are you feeling?")
            text_input = st.text_area(
                "Share your thoughts...",
                placeholder="I've been feeling overwhelmed about environmental news lately...",
                height=100
            )
            
            activities = st.multiselect(
                "Recent Activities",
                ['news_reading', 'climate_reading', 'social_media', 'nature_time', 'eco_activism']
            )
            
            if st.button("🔍 Analyze Emotional State", use_container_width=True):
                if text_input:
                    analysis = self.anxiety_manager.detect_anxiety(
                        self.user_id,
                        {'text': text_input, 'activities': activities}
                    )
                    
                    st.session_state.mindfulness_data['anxiety_profile'] = analysis
                    st.rerun()
        
        with col2:
            st.markdown("### 📊 Current State")
            
            profile = st.session_state.mindfulness_data.get('anxiety_profile')
            if profile:
                severity_colors = {
                    'high': '#ef4444',
                    'medium': '#fbbf24',
                    'low': '#4ade80'
                }
                
                st.markdown(f"""
                <div style="background: #0f172a; padding: 15px; border-radius: 12px; border: 1px solid {severity_colors.get(profile['severity'], '#94a3b8')};">
                    <div style="font-size: 14px; color: #94a3b8;">Emotional State</div>
                    <div style="font-size: 22px; font-weight: 700; color: {'#ef4444' if profile['emotional_state'] in ['overwhelmed', 'anxious'] else '#4ade80'};">
                        {profile['emotional_state'].value.replace('_', ' ').title()}
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 5px;">
                        Severity: <span style="color: {severity_colors.get(profile['severity'], '#94a3b8')};">{profile['severity'].upper()}</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 3px;">
                        Anxiety Score: {profile['anxiety_score']*100:.1f}%
                    </div>
                    <div style="margin-top: 10px; font-size: 11px; color: #94a3b8;">
                        Patterns: {', '.join(profile['detected_patterns']) if profile['detected_patterns'] else 'None detected'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Coping strategy
                if profile['emotional_state'] in [EmotionalState.ANXIOUS, EmotionalState.OVERWHELMED]:
                    preferences = {'preferred_duration': 5}
                    strategy = self.anxiety_manager.get_coping_strategy(
                        profile['emotional_state'],
                        preferences
                    )
                    
                    if strategy['strategy']:
                        st.markdown(f"""
                        <div style="background: #1a2e2a; padding: 15px; border-radius: 12px; margin-top: 10px; border: 1px solid #4ade80;">
                            <div style="font-size: 14px; color: #4ade80;">💡 Recommended Coping Strategy</div>
                            <div style="font-size: 16px; font-weight: 600; color: #e5e7eb; margin-top: 3px;">
                                {strategy['strategy']['name']}
                            </div>
                            <div style="font-size: 13px; color: #94a3b8; margin-top: 3px;">
                                {strategy['strategy']['description']}
                            </div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 5px;">
                                ⏱️ {strategy['strategy']['duration_minutes']} min | 
                                📊 Effectiveness: {strategy['strategy']['effectiveness']*100:.0f}%
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Share your thoughts and click 'Analyze' to get personalized support")
    
    def _render_social_contagion(self):
        """Render social contagion interface"""
        st.subheader("🌐 Social Contagion Influence Mapper")
        st.write("Analyze how sustainable behavior spreads through social networks")
        
        # Network simulation
        if not st.session_state.mindfulness_data['social_network']:
            if st.button("🌐 Simulate Social Network", use_container_width=True):
                # Create simulated network
                for i in range(1, 21):
                    connections = random.sample([j for j in range(1, 21) if j != i], random.randint(2, 5))
                    self.social_mapper.add_user_to_network(i, connections, random.uniform(0.3, 0.8))
                
                st.session_state.mindfulness_data['social_network'] = list(self.social_mapper.network.keys())
                st.success("✅ Social network created with 20 nodes!")
                st.rerun()
        
        if st.session_state.mindfulness_data['social_network']:
            network_size = len(self.social_mapper.network)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Network Size", f"{network_size} users")
            with col2:
                avg_influence = np.mean([n.influence_power for n in self.social_mapper.network.values()])
                st.metric("Avg Influence", f"{avg_influence*100:.1f}%")
            with col3:
                avg_susceptibility = np.mean([n.susceptible_score for n in self.social_mapper.network.values()])
                st.metric("Avg Susceptibility", f"{avg_susceptibility*100:.1f}%")
            
            # Contagion simulation
            st.markdown("### 🔮 Contagion Simulation")
            
            source_user = st.selectbox("Source User", list(self.social_mapper.network.keys()))
            behavior_type = st.selectbox("Behavior Type", ["Sustainable Transport", "Recycling", "Energy Saving"])
            
            if st.button("📊 Simulate Contagion", use_container_width=True):
                result = self.social_mapper.predict_contagion_path(source_user, behavior_type)
                
                st.markdown(f"""
                <div style="background: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #4ade80;">
                    <h4 style="color: #4ade80;">🌱 Contagion Results</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-top: 10px;">
                        <div>
                            <div style="color: #94a3b8; font-size: 12px;">Affected Users</div>
                            <div style="font-size: 24px; font-weight: 700; color: #4ade80;">{result['affected_users']}</div>
                        </div>
                        <div>
                            <div style="color: #94a3b8; font-size: 12px;">Network Reach</div>
                            <div style="font-size: 24px; font-weight: 700; color: #60a5fa;">{result['network_reach']*100:.1f}%</div>
                        </div>
                        <div>
                            <div style="color: #94a3b8; font-size: 12px;">Total Impact</div>
                            <div style="font-size: 24px; font-weight: 700; color: #fbbf24;">{result['total_impact']:.1f}</div>
                        </div>
                    </div>
                    <div style="margin-top: 10px; font-size: 13px; color: #94a3b8;">
                        Average Depth: {result['average_depth']:.1f} hops | 
                        Predicted Adoption: {result['predicted_behavior_adoption']*100:.1f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    def _render_circadian_coach(self):
        """Render circadian coaching interface"""
        st.subheader("⏰ Circadian-Optimized Coaching")
        st.write("Personalized interventions timed to your biological rhythms")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🌙 Your Chronotype")
            
            sleep_start = st.slider("Typical Sleep Start", 20, 24, 23)
            sleep_end = st.slider("Typical Sleep End", 5, 10, 7)
            
            if st.button("🔄 Detect Chronotype", use_container_width=True):
                chronotype = self.circadian_coach.detect_chronotype(
                    self.user_id,
                    {'sleep_start': sleep_start, 'sleep_end': sleep_end}
                )
                
                chronotype_names = {
                    Chronotype.MORNING: "🌅 Morning Lark",
                    Chronotype.EVENING: "🦉 Night Owl",
                    Chronotype.INTERMEDIATE: "🕊️ Intermediate"
                }
                
                st.success(f"✅ Detected: {chronotype_names[chronotype]}")
                st.session_state.mindfulness_data['chronotype'] = chronotype
        
        with col2:
            st.markdown("### 📊 Energy Curve")
            
            chronotype = st.session_state.mindfulness_data.get('chronotype', Chronotype.INTERMEDIATE)
            energy_curve = self.circadian_coach.calculate_energy_curve(chronotype)
            
            hours = list(range(24))
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hours,
                y=energy_curve * 100,
                mode='lines+markers',
                name='Energy Level',
                line=dict(color='#4ade80', width=2),
                marker=dict(size=8)
            ))
            
            # Mark peak hours
            peak_hours = np.where(energy_curve > 0.8)[0]
            for hour in peak_hours:
                fig.add_vline(x=hour, line_dash="dash", line_color="rgba(74, 222, 128, 0.3)")
            
            fig.update_layout(
                title="Daily Energy Pattern",
                xaxis_title="Hour of Day",
                yaxis_title="Energy Level (%)",
                height=300,
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Optimized interventions
        st.markdown("### 🎯 Optimized Interventions")
        
        intervention_types = list(InterventionType)
        selected_type = st.selectbox("Intervention Type", intervention_types)
        
        if st.button("⏰ Find Optimal Time", use_container_width=True):
            intervention = self.circadian_coach.optimize_intervention_timing(
                self.user_id,
                selected_type
            )
            
            st.markdown(f"""
            <div style="background: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #4ade80;">
                <h4 style="color: #4ade80;">📅 Optimized Intervention</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 10px;">
                    <div>
                        <div style="color: #94a3b8; font-size: 12px;">Type</div>
                        <div style="font-weight: 600; color: #e5e7eb;">{intervention.intervention_type.value.title()}</div>
                    </div>
                    <div>
                        <div style="color: #94a3b8; font-size: 12px;">Ideal Time</div>
                        <div style="font-weight: 600; color: #e5e7eb;">{intervention.ideal_time.strftime('%I:%M %p')}</div>
                    </div>
                    <div>
                        <div style="color: #94a3b8; font-size: 12px;">Energy Required</div>
                        <div style="font-weight: 600; color: #4ade80;">{intervention.energy_level_required*100:.0f}%</div>
                    </div>
                    <div>
                        <div style="color: #94a3b8; font-size: 12px;">Estimated Impact</div>
                        <div style="font-weight: 600; color: #fbbf24;">{intervention.estimated_impact*100:.1f}%</div>
                    </div>
                </div>
                <div style="margin-top: 10px; padding: 10px; background: rgba(74,222,128,0.05); border-radius: 8px;">
                    <div style="color: #94a3b8; font-size: 13px;">{intervention.content}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_mindfulness_hub():
    """Main entry point for eco-mindfulness system"""
    user_id = st.session_state.get('user_id', 1)
    
    ui = EcoMindfulnessUI(user_id)
    ui.render()

# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    st.set_page_config(page_title="Eco-Mindfulness", layout="wide")
    render_mindfulness_hub()

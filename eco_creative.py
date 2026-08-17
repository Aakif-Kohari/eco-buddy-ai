"""
AI-Powered Eco-Creative Expression & Environmental Art Therapy Module
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
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import os

logger = logging.getLogger(__name__)

# ============================================================
# ENUMS AND CONSTANTS
# ============================================================

class ArtTheme(Enum):
    RENEWAL = "renewal"
    RESILIENCE = "resilience"
    HOPE = "hope"
    TRANSFORMATION = "transformation"
    CONNECTION = "connection"
    GROWTH = "growth"
    HEALING = "healing"
    HARMONY = "harmony"

class EmotionPalette(Enum):
    CALM = "calm"
    ANXIOUS = "anxious"
    HOPEFUL = "hopeful"
    OVERWHELMED = "overwhelmed"
    PEACEFUL = "peaceful"
    URGENT = "urgent"
    GRATEFUL = "grateful"
    DETERMINED = "determined"

class CreativeMedium(Enum):
    VISUAL = "visual"
    NARRATIVE = "narrative"
    MUSICAL = "musical"
    COLLABORATIVE = "collaborative"
    MIXED = "mixed"

class SoundscapeType(Enum):
    FOREST = "forest"
    OCEAN = "ocean"
    RAINFOREST = "rainforest"
    DESERT = "desert"
    MOUNTAIN = "mountain"
    WETLAND = "wetland"
    URBAN = "urban"

# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class EcoArtwork:
    """Environmental art piece data structure"""
    id: str
    title: str
    creator_id: int
    theme: ArtTheme
    medium: CreativeMedium
    created_at: datetime
    image_data: Optional[str] = None
    story: Optional[str] = None
    audio_url: Optional[str] = None
    emotion_signature: Dict[str, float] = field(default_factory=dict)
    environmental_data: Dict[str, float] = field(default_factory=dict)
    community_contributors: List[int] = field(default_factory=list)
    likes: int = 0
    views: int = 0

@dataclass
class TherapeuticPrompt:
    """Therapeutic journaling prompt"""
    id: str
    prompt_text: str
    category: str
    difficulty: float
    estimated_duration: int
    emotional_focus: List[str]
    sustainability_theme: str
    guided_questions: List[str]

@dataclass
class Soundscape:
    """Generated nature soundscape"""
    id: str
    type: SoundscapeType
    user_id: int
    created_at: datetime
    duration: int
    binaural_beats: bool
    environment_data: Dict[str, float]
    mood_rating: float
    audio_parameters: Dict[str, Any]

@dataclass
class ARProjection:
    """Augmented reality projection data"""
    id: str
    user_id: int
    location: Tuple[float, float]
    timestamp: datetime
    projection_type: str
    environmental_scenario: str
    visual_elements: List[Dict]
    interaction_data: Dict[str, Any]

@dataclass
class CommunityCanvas:
    """Collaborative art project"""
    id: str
    name: str
    description: str
    created_by: int
    created_at: datetime
    participants: List[int]
    contributions: List[Dict]
    current_theme: str
    art_style: str
    completion_status: float
    collaborations: int

# ============================================================
# GENERATIVE ART ENGINE
# ============================================================

class GenerativeArtEngine:
    """
    AI-powered environmental art generation using diffusion models
    """
    
    def __init__(self):
        self.art_templates = self._initialize_templates()
        self.style_mappings = self._initialize_styles()
        self.generation_history: List[EcoArtwork] = []
        
    def _initialize_templates(self) -> Dict:
        """Initialize art generation templates"""
        return {
            "renewal": {
                "description": "Themes of environmental renewal and restoration",
                "color_palette": ["#4ade80", "#34d399", "#6ee7b7", "#a7f3d0"],
                "shapes": ["circular", "flowing", "expanding"],
                "mood": "hopeful"
            },
            "resilience": {
                "description": "Themes of environmental resilience and strength",
                "color_palette": ["#fbbf24", "#f59e0b", "#d97706", "#b45309"],
                "shapes": ["angular", "structured", "grounded"],
                "mood": "determined"
            },
            "hope": {
                "description": "Themes of environmental hope and optimism",
                "color_palette": ["#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8"],
                "shapes": ["ascending", "light", "expansive"],
                "mood": "optimistic"
            },
            "transformation": {
                "description": "Themes of environmental transformation",
                "color_palette": ["#a78bfa", "#8b5cf6", "#7c3aed", "#6d28d9"],
                "shapes": ["changing", "evolving", "dynamic"],
                "mood": "reflective"
            }
        }
    
    def _initialize_styles(self) -> Dict:
        """Initialize artistic styles"""
        return {
            "impressionist": {"color_saturation": 0.8, "texture": "soft", "detail": 0.6},
            "abstract": {"color_saturation": 1.2, "texture": "bold", "detail": 0.3},
            "realistic": {"color_saturation": 0.9, "texture": "detailed", "detail": 0.9},
            "expressionist": {"color_saturation": 1.5, "texture": "intense", "detail": 0.5}
        }
    
    def generate_art(self, theme: ArtTheme, environmental_data: Dict, style: str = "abstract") -> EcoArtwork:
        """Generate environmental art based on theme and data"""
        
        # Get theme template
        template = self.art_templates.get(theme.value, self.art_templates["renewal"])
        
        # Create base image
        width, height = 800, 600
        image = Image.new('RGB', (width, height), '#0f172a')
        draw = ImageDraw.Draw(image)
        
        # Map environmental data to art parameters
        carbon_level = environmental_data.get('carbon_level', 0.5)
        biodiversity = environmental_data.get('biodiversity', 0.5)
        pollution = environmental_data.get('pollution', 0.3)
        conservation = environmental_data.get('conservation', 0.7)
        
        # Generate elements based on theme
        if theme == ArtTheme.RENEWAL:
            elements = self._generate_renewal_elements(draw, width, height, carbon_level, biodiversity)
        elif theme == ArtTheme.RESILIENCE:
            elements = self._generate_resilience_elements(draw, width, height, conservation, pollution)
        elif theme == ArtTheme.HOPE:
            elements = self._generate_hope_elements(draw, width, height, carbon_level, conservation)
        elif theme == ArtTheme.TRANSFORMATION:
            elements = self._generate_transformation_elements(draw, width, height, biodiversity, pollution)
        else:
            elements = self._generate_default_elements(draw, width, height)
        
        # Convert to base64 for display
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Create artwork object
        artwork = EcoArtwork(
            id=hashlib.md5(f"{datetime.now()}{random.random()}".encode()).hexdigest()[:8],
            title=f"{theme.value.title()} - {datetime.now().strftime('%b %d')}",
            creator_id=1,
            theme=theme,
            medium=CreativeMedium.VISUAL,
            created_at=datetime.now(),
            image_data=img_str,
            environmental_data=environmental_data,
            emotion_signature=self._calculate_emotion_signature(environmental_data, theme)
        )
        
        self.generation_history.append(artwork)
        return artwork
    
    def _generate_renewal_elements(self, draw, width, height, carbon_level, biodiversity):
        """Generate renewal-themed elements"""
        colors = ['#4ade80', '#34d399', '#6ee7b7', '#a7f3d0']
        
        # Create circular renewal patterns
        center_x, center_y = width // 2, height // 2
        
        for i in range(8):
            radius = 50 + i * 30
            x1 = center_x - radius
            y1 = center_y - radius
            x2 = center_x + radius
            y2 = center_y + radius
            
            color_index = i % len(colors)
            draw.ellipse([x1, y1, x2, y2], outline=colors[color_index], width=3)
        
        # Add growth elements
        for i in range(15):
            x = random.randint(50, width - 50)
            y = random.randint(50, height - 50)
            size = 10 + random.randint(0, 20) * biodiversity
            draw.ellipse([x, y, x + size, y + size], fill='#4ade80', outline='#34d399')
        
        return True
    
    def _generate_resilience_elements(self, draw, width, height, conservation, pollution):
        """Generate resilience-themed elements"""
        colors = ['#fbbf24', '#f59e0b', '#d97706', '#b45309']
        
        # Create angular resilience patterns
        points = []
        for i in range(12):
            angle = i * (360 / 12)
            radius = 100 + (1 - conservation) * 80
            x = width // 2 + radius * np.cos(np.radians(angle))
            y = height // 2 + radius * np.sin(np.radians(angle))
            points.append((x, y))
        
        # Draw structure
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill='#fbbf24', width=3)
        
        # Add protection elements
        for i in range(10):
            x = random.randint(30, width - 30)
            y = random.randint(30, height - 30)
            size = 15 + random.randint(0, 15) * conservation
            draw.rectangle([x, y, x + size, y + size], outline='#f59e0b', width=2)
        
        return True
    
    def _generate_hope_elements(self, draw, width, height, carbon_level, conservation):
        """Generate hope-themed elements"""
        colors = ['#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8']
        
        # Create ascending hope patterns
        for i in range(20):
            x = random.randint(20, width - 20)
            y = height - random.randint(20, height - 20)
            height_ratio = 30 + random.randint(0, 60) * conservation
            
            draw.line([x, y, x, y - height_ratio], fill='#60a5fa', width=3)
        
        # Add light elements
        for i in range(30):
            x = random.randint(10, width - 10)
            y = random.randint(10, height - 10)
            size = 5 + random.randint(0, 10) * conservation
            draw.ellipse([x, y, x + size, y + size], fill='#3b82f6')
        
        return True
    
    def _generate_transformation_elements(self, draw, width, height, biodiversity, pollution):
        """Generate transformation-themed elements"""
        colors = ['#a78bfa', '#8b5cf6', '#7c3aed', '#6d28d9']
        
        # Create dynamic transformation patterns
        for i in range(30):
            x1 = random.randint(20, width - 20)
            y1 = random.randint(20, height - 20)
            x2 = x1 + random.randint(-50, 50)
            y2 = y1 + random.randint(-50, 50)
            
            draw.line([x1, y1, x2, y2], fill='#a78bfa', width=2 + biodiversity * 3)
        
        # Add transformation nodes
        for i in range(15):
            x = random.randint(30, width - 30)
            y = random.randint(30, height - 30)
            size = 8 + random.randint(0, 12) * biodiversity
            draw.ellipse([x, y, x + size, y + size], fill='#8b5cf6')
        
        return True
    
    def _generate_default_elements(self, draw, width, height):
        """Generate default elements"""
        for i in range(30):
            x = random.randint(10, width - 10)
            y = random.randint(10, height - 10)
            size = random.randint(5, 15)
            color = random.choice(['#4ade80', '#60a5fa', '#fbbf24', '#a78bfa'])
            draw.ellipse([x, y, x + size, y + size], fill=color)
        
        return True
    
    def _calculate_emotion_signature(self, environmental_data: Dict, theme: ArtTheme) -> Dict[str, float]:
        """Calculate emotional signature from environmental data"""
        signature = {
            'hope': 0.0,
            'concern': 0.0,
            'determination': 0.0,
            'peace': 0.0,
            'urgency': 0.0
        }
        
        # Map environmental indicators to emotions
        carbon = environmental_data.get('carbon_level', 0.5)
        biodiversity = environmental_data.get('biodiversity', 0.5)
        conservation = environmental_data.get('conservation', 0.7)
        
        signature['hope'] = conservation * 0.8 + (1 - carbon) * 0.2
        signature['concern'] = (1 - conservation) * 0.6 + carbon * 0.4
        signature['determination'] = conservation * 0.5 + (1 - carbon) * 0.5
        signature['peace'] = biodiversity * 0.7 + conservation * 0.3
        signature['urgency'] = carbon * 0.8 + (1 - conservation) * 0.2
        
        # Normalize
        total = sum(signature.values())
        if total > 0:
            for key in signature:
                signature[key] /= total
        
        return signature

# ============================================================
# NARRATIVE THERAPY ENGINE
# ============================================================

class NarrativeTherapyEngine:
    """
    AI-powered therapeutic storytelling and journaling
    """
    
    def __init__(self):
        self.prompts = self._initialize_prompts()
        self.stories = []
        self.journal_entries = []
        
    def _initialize_prompts(self) -> Dict[str, TherapeuticPrompt]:
        """Initialize therapeutic prompts"""
        prompts = {
            "nature_reflection": TherapeuticPrompt(
                id="nature_reflection",
                prompt_text="Reflect on a moment in nature that inspired you. What did you see, feel, and learn?",
                category="reflection",
                difficulty=0.3,
                estimated_duration=10,
                emotional_focus=["peace", "gratitude"],
                sustainability_theme="connection",
                guided_questions=[
                    "Where were you?",
                    "What did you notice?",
                    "How did it make you feel?",
                    "What did you learn from this experience?"
                ]
            ),
            "climate_emotions": TherapeuticPrompt(
                id="climate_emotions",
                prompt_text="Write a letter to the Earth about your feelings regarding climate change.",
                category="emotional_processing",
                difficulty=0.7,
                estimated_duration=20,
                emotional_focus=["concern", "determination", "hope"],
                sustainability_theme="action",
                guided_questions=[
                    "What worries you most?",
                    "What gives you hope?",
                    "What would you say to future generations?",
                    "What action can you take?"
                ]
            ),
            "sustainable_journey": TherapeuticPrompt(
                id="sustainable_journey",
                prompt_text="Describe your personal sustainability journey. Where did you start and where are you now?",
                category="reflection",
                difficulty=0.5,
                estimated_duration=15,
                emotional_focus=["determination", "gratitude", "hope"],
                sustainability_theme="progress",
                guided_questions=[
                    "What prompted your sustainability journey?",
                    "What changes have you made?",
                    "What has been challenging?",
                    "What are you proud of?"
                ]
            ),
            "eco_vision": TherapeuticPrompt(
                id="eco_vision",
                prompt_text="Imagine a sustainable future 20 years from now. Describe what you see, hear, and feel.",
                category="visioning",
                difficulty=0.6,
                estimated_duration=25,
                emotional_focus=["hope", "peace", "determination"],
                sustainability_theme="future",
                guided_questions=[
                    "What does the environment look like?",
                    "How do people live?",
                    "What changes have been made?",
                    "How does this vision make you feel?"
                ]
            ),
            "gratitude": TherapeuticPrompt(
                id="gratitude",
                prompt_text="List 5 environmental things you're grateful for today.",
                category="gratitude",
                difficulty=0.2,
                estimated_duration=5,
                emotional_focus=["gratitude", "peace"],
                sustainability_theme="appreciation",
                guided_questions=[
                    "What natural beauty did you notice?",
                    "What environmental progress have you seen?",
                    "What sustainable actions are you grateful for?"
                ]
            )
        }
        return prompts
    
    def get_daily_prompt(self) -> TherapeuticPrompt:
        """Get daily therapeutic prompt"""
        prompts = list(self.prompts.values())
        return random.choice(prompts)
    
    def get_prompt_by_theme(self, theme: str) -> Optional[TherapeuticPrompt]:
        """Get prompt by theme"""
        for prompt in self.prompts.values():
            if prompt.sustainability_theme == theme:
                return prompt
        return None
    
    def generate_story_seed(self, theme: ArtTheme, mood: str) -> Dict:
        """Generate story seed based on theme and mood"""
        seeds = {
            "renewal": {
                "beginnings": [
                    "In the quiet space between yesterday and tomorrow, the Earth began to heal...",
                    "Where once there was only concrete, new life emerged...",
                    "The seeds of change had been planted long ago, and now they were ready to grow..."
                ],
                "elements": ["green shoots", "clean water", "fresh air", "new life"],
                "characters": ["the gardener", "the protector", "the pioneer", "the healer"]
            },
            "resilience": {
                "beginnings": [
                    "Standing firm against the storm, the community found strength in unity...",
                    "The Earth had weathered many challenges, and would weather many more...",
                    "In the face of adversity, the most resilient among them found a way..."
                ],
                "elements": ["strong roots", "ancient forests", "enduring spirit", "community bond"],
                "characters": ["the survivor", "the leader", "the wise elder", "the determined"]
            },
            "hope": {
                "beginnings": [
                    "A single ray of light broke through the clouds, illuminating the path forward...",
                    "In every dark night, there was a promise of dawn...",
                    "The flicker of hope spread from heart to heart, growing brighter with each passing moment..."
                ],
                "elements": ["golden light", "warmth", "new beginning", "connections"],
                "characters": ["the dreamer", "the believer", "the guide", "the inspired"]
            },
            "transformation": {
                "beginnings": [
                    "Everything was changing, and nothing would ever be the same...",
                    "From the ashes of the old, something new was being born...",
                    "The transformation had already begun, whether anyone noticed or not..."
                ],
                "elements": ["flux", "new patterns", "evolution", "emergence"],
                "characters": ["the transformer", "the witness", "the catalyst", "the evolved"]
            }
        }
        
        theme_data = seeds.get(theme.value, seeds["renewal"])
        
        return {
            'beginning': random.choice(theme_data['beginnings']),
            'elements': random.sample(theme_data['elements'], 3),
            'characters': random.sample(theme_data['characters'], 2),
            'mood': mood
        }
    
    def save_journal_entry(self, user_id: int, prompt_id: str, entry: str, emotional_state: Dict):
        """Save journal entry with emotional context"""
        entry_data = {
            'user_id': user_id,
            'prompt_id': prompt_id,
            'entry': entry,
            'emotional_state': emotional_state,
            'timestamp': datetime.now(),
            'id': hashlib.md5(f"{user_id}_{datetime.now()}".encode()).hexdigest()[:8]
        }
        
        self.journal_entries.append(entry_data)
        return entry_data

# ============================================================
# SOUNDSCAPE GENERATION ENGINE
# ============================================================

class SoundscapeEngine:
    """
    AI-generated nature soundscapes from environmental data
    """
    
    def __init__(self):
        self.sound_profiles = self._initialize_profiles()
        self.generated_soundscapes: List[Soundscape] = []
        
    def _initialize_profiles(self) -> Dict:
        """Initialize sound profiles"""
        return {
            SoundscapeType.FOREST: {
                "description": "Birds singing, leaves rustling, gentle breeze",
                "base_frequency": 440,
                "layers": ["birds", "leaves", "wind", "water"],
                "tempo": 60
            },
            SoundscapeType.OCEAN: {
                "description": "Waves crashing, seagulls, gentle tides",
                "base_frequency": 220,
                "layers": ["waves", "birds", "wind", "water"],
                "tempo": 40
            },
            SoundscapeType.RAINFOREST: {
                "description": "Dripping water, exotic birds, dense vegetation",
                "base_frequency": 520,
                "layers": ["birds", "water", "insects", "leaves"],
                "tempo": 70
            },
            SoundscapeType.MOUNTAIN: {
                "description": "Wind howling, eagles, distant streams",
                "base_frequency": 350,
                "layers": ["wind", "birds", "water", "echo"],
                "tempo": 50
            },
            SoundscapeType.WETLAND: {
                "description": "Frogs, crickets, flowing water, waterfowl",
                "base_frequency": 480,
                "layers": ["frogs", "crickets", "water", "birds"],
                "tempo": 80
            },
            SoundscapeType.URBAN: {
                "description": "City sounds with green spaces, filtered through nature",
                "base_frequency": 380,
                "layers": ["city", "birds", "wind", "water"],
                "tempo": 65
            }
        }
    
    def generate_soundscape(self, sound_type: SoundscapeType, environmental_data: Dict) -> Soundscape:
        """Generate nature soundscape from environmental data"""
        profile = self.sound_profiles.get(sound_type, self.sound_profiles[SoundscapeType.FOREST])
        
        # Adjust parameters based on environmental data
        carbon_level = environmental_data.get('carbon_level', 0.5)
        biodiversity = environmental_data.get('biodiversity', 0.5)
        conservation = environmental_data.get('conservation', 0.7)
        
        # Create soundscape
        soundscape = Soundscape(
            id=hashlib.md5(f"{datetime.now()}{random.random()}".encode()).hexdigest()[:8],
            type=sound_type,
            user_id=1,
            created_at=datetime.now(),
            duration=300,  # 5 minutes
            binaural_beats=True,
            environment_data=environmental_data,
            mood_rating=self._calculate_mood_rating(carbon_level, biodiversity),
            audio_parameters={
                'base_frequency': profile['base_frequency'] + (1 - conservation) * 20,
                'tempo': profile['tempo'] + (1 - carbon_level) * 5,
                'layers_active': len(profile['layers']),
                'biodiversity_score': biodiversity
            }
        )
        
        self.generated_soundscapes.append(soundscape)
        return soundscape
    
    def _calculate_mood_rating(self, carbon_level: float, biodiversity: float) -> float:
        """Calculate mood rating from environmental data"""
        rating = (1 - carbon_level) * 0.6 + biodiversity * 0.4
        return max(0, min(1, rating))
    
    def get_relaxation_audio(self, mood: str) -> Soundscape:
        """Get relaxation audio based on mood"""
        mood_mapping = {
            'anxious': SoundscapeType.FOREST,
            'overwhelmed': SoundscapeType.OCEAN,
            'calm': SoundscapeType.WETLAND,
            'hopeful': SoundscapeType.MOUNTAIN,
            'determined': SoundscapeType.RAINFOREST,
            'peaceful': SoundscapeType.FOREST
        }
        
        sound_type = mood_mapping.get(mood, SoundscapeType.FOREST)
        environmental_data = {
            'carbon_level': 0.3,
            'biodiversity': 0.8,
            'conservation': 0.9
        }
        
        return self.generate_soundscape(sound_type, environmental_data)

# ============================================================
# COMMUNITY CANVAS ENGINE
# ============================================================

class CommunityCanvasEngine:
    """
    Collaborative art creation through community data aggregation
    """
    
    def __init__(self):
        self.canvases: Dict[str, CommunityCanvas] = {}
        self.art_collections: Dict[str, List[EcoArtwork]] = defaultdict(list)
        self.collaboration_sessions: Dict[str, Dict] = {}
    
    def create_canvas(self, name: str, description: str, creator_id: int, theme: str) -> CommunityCanvas:
        """Create a new community canvas"""
        canvas_id = hashlib.md5(f"{name}_{datetime.now()}".encode()).hexdigest()[:8]
        
        canvas = CommunityCanvas(
            id=canvas_id,
            name=name,
            description=description,
            created_by=creator_id,
            created_at=datetime.now(),
            participants=[creator_id],
            contributions=[],
            current_theme=theme,
            art_style="collaborative",
            completion_status=0.0,
            collaborations=0
        )
        
        self.canvases[canvas_id] = canvas
        return canvas
    
    def add_contribution(self, canvas_id: str, user_id: int, contribution: Dict) -> bool:
        """Add contribution to community canvas"""
        if canvas_id not in self.canvases:
            return False
        
        canvas = self.canvases[canvas_id]
        
        if user_id not in canvas.participants:
            canvas.participants.append(user_id)
        
        contribution_data = {
            'user_id': user_id,
            'timestamp': datetime.now(),
            'data': contribution,
            'type': contribution.get('type', 'visual')
        }
        
        canvas.contributions.append(contribution_data)
        canvas.collaborations += 1
        
        # Update completion status
        canvas.completion_status = min(1.0, len(canvas.contributions) / 20)
        
        return True
    
    def generate_collective_art(self, canvas_id: str) -> Optional[EcoArtwork]:
        """Generate collective art from community contributions"""
        if canvas_id not in self.canvases:
            return None
        
        canvas = self.canvases[canvas_id]
        
        if not canvas.contributions:
            return None
        
        # Aggregate contributions
        aggregated_data = self._aggregate_contributions(canvas.contributions)
        
        # Generate artwork
        theme_mapping = {
            'renewal': ArtTheme.RENEWAL,
            'resilience': ArtTheme.RESILIENCE,
            'hope': ArtTheme.HOPE,
            'transformation': ArtTheme.TRANSFORMATION
        }
        
        theme = theme_mapping.get(canvas.current_theme, ArtTheme.RENEWAL)
        
        artwork = EcoArtwork(
            id=hashlib.md5(f"{canvas_id}_{datetime.now()}".encode()).hexdigest()[:8],
            title=f"Community Canvas: {canvas.name}",
            creator_id=canvas.created_by,
            theme=theme,
            medium=CreativeMedium.COLLABORATIVE,
            created_at=datetime.now(),
            community_contributors=[c['user_id'] for c in canvas.contributions],
            environmental_data=aggregated_data,
            emotion_signature=self._calculate_community_emotion(canvas.contributions),
            likes=0,
            views=0
        )
        
        self.art_collections[canvas_id].append(artwork)
        return artwork
    
    def _aggregate_contributions(self, contributions: List[Dict]) -> Dict:
        """Aggregate contribution data"""
        aggregated = {
            'carbon_level': 0,
            'biodiversity': 0,
            'conservation': 0,
            'pollution': 0,
            'participant_count': len(set(c['user_id'] for c in contributions))
        }
        
        if not contributions:
            return aggregated
        
        for contrib in contributions:
            data = contrib.get('data', {})
            for key in ['carbon_level', 'biodiversity', 'conservation', 'pollution']:
                if key in data:
                    aggregated[key] += data[key]
        
        # Average values
        for key in ['carbon_level', 'biodiversity', 'conservation', 'pollution']:
            aggregated[key] /= len(contributions)
        
        return aggregated
    
    def _calculate_community_emotion(self, contributions: List[Dict]) -> Dict[str, float]:
        """Calculate community emotional signature"""
        emotion_signature = {
            'hope': 0,
            'concern': 0,
            'determination': 0,
            'peace': 0,
            'urgency': 0
        }
        
        if not contributions:
            return emotion_signature
        
        for contrib in contributions:
            data = contrib.get('data', {})
            if 'emotion_signature' in data:
                for key in emotion_signature:
                    if key in data['emotion_signature']:
                        emotion_signature[key] += data['emotion_signature'][key]
        
        # Average
        for key in emotion_signature:
            emotion_signature[key] /= len(contributions)
        
        return emotion_signature

# ============================================================
# MAIN UI COMPONENT
# ============================================================

class EcoCreativeUI:
    """
    Complete UI for eco-creative expression module
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.art_engine = GenerativeArtEngine()
        self.narrative_engine = NarrativeTherapyEngine()
        self.soundscape_engine = SoundscapeEngine()
        self.community_engine = CommunityCanvasEngine()
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        if 'creative_data' not in st.session_state:
            st.session_state.creative_data = {
                'artworks': [],
                'journal_entries': [],
                'soundscapes': [],
                'canvas_participations': [],
                'current_theme': ArtTheme.HOPE.value
            }
    
    def render(self):
        """Render the complete UI"""
        st.markdown("""
        <style>
        .creative-header {
            background: linear-gradient(135deg, #0f172a, #1a2e2a);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            border: 1px solid rgba(74, 222, 128, 0.3);
            text-align: center;
        }
        .creative-header h2 {
            color: #4ade80;
            margin: 0;
            font-size: 32px;
        }
        .creative-header p {
            color: #94a3b8;
            margin: 5px 0 0 0;
        }
        .artwork-card {
            background: #0f172a;
            padding: 18px;
            border-radius: 12px;
            border: 1px solid rgba(74, 222, 128, 0.15);
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        .artwork-card:hover {
            border-color: #4ade80;
            transform: translateY(-2px);
        }
        .prompt-card {
            background: linear-gradient(135deg, #0f172a, #1a2e2a);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(74, 222, 128, 0.2);
            margin-bottom: 15px;
        }
        .soundscape-player {
            background: #0f172a;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid rgba(96, 165, 250, 0.2);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown("""
        <div class="creative-header">
            <h2>🎨 Eco-Creative Expression & Art Therapy</h2>
            <p>Transform environmental emotions into art, stories, and sound</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Main tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎨 Generate Art",
            "📝 Narrative Therapy",
            "🎵 Soundscapes",
            "🤝 Community Canvas",
            "📚 Gallery"
        ])
        
        with tab1:
            self._render_art_generation()
        
        with tab2:
            self._render_narrative_therapy()
        
        with tab3:
            self._render_soundscapes()
        
        with tab4:
            self._render_community_canvas()
        
        with tab5:
            self._render_gallery()
    
    def _render_art_generation(self):
        """Render art generation interface"""
        st.subheader("🎨 Generate Environmental Art")
        st.write("Transform environmental data and emotions into visual art")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            theme_options = [t.value.capitalize() for t in ArtTheme]
            selected_theme = st.selectbox("Select Theme", theme_options)
            
            style_options = ["Abstract", "Impressionist", "Expressionist", "Realistic"]
            selected_style = st.selectbox("Select Artistic Style", style_options)
            
            # Environmental data sliders
            st.markdown("### 🌍 Environmental Data")
            carbon_level = st.slider("Carbon Level", 0.0, 1.0, 0.5)
            biodiversity = st.slider("Biodiversity", 0.0, 1.0, 0.6)
            conservation = st.slider("Conservation Effort", 0.0, 1.0, 0.7)
            pollution = st.slider("Pollution Level", 0.0, 1.0, 0.3)
        
        with col2:
            st.markdown("### 🎨 Art Preview")
            
            if st.button("✨ Generate Art", use_container_width=True):
                theme_map = {
                    'Renewal': ArtTheme.RENEWAL,
                    'Resilience': ArtTheme.RESILIENCE,
                    'Hope': ArtTheme.HOPE,
                    'Transformation': ArtTheme.TRANSFORMATION
                }
                theme = theme_map.get(selected_theme, ArtTheme.HOPE)
                
                env_data = {
                    'carbon_level': carbon_level,
                    'biodiversity': biodiversity,
                    'conservation': conservation,
                    'pollution': pollution
                }
                
                artwork = self.art_engine.generate_art(theme, env_data, selected_style.lower())
                
                # Display generated art
                if artwork.image_data:
                    st.image(f"data:image/png;base64,{artwork.image_data}", use_column_width=True)
                    
                    st.markdown(f"""
                    <div style="background: #0f172a; padding: 15px; border-radius: 12px; margin-top: 10px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #4ade80; font-weight: 600;">{artwork.title}</span>
                            <span style="color: #94a3b8; font-size: 12px;">🎨 {selected_style}</span>
                        </div>
                        <div style="display: flex; gap: 15px; margin-top: 8px;">
                            {''.join([f'<span style="background: rgba(74,222,128,0.1); color: #4ade80; padding: 2px 10px; border-radius: 10px; font-size: 11px;">❤️ {emotion}: {value:.2f}</span>' for emotion, value in artwork.emotion_signature.items() if value > 0.1])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Save to session
                    st.session_state.creative_data['artworks'].append({
                        'id': artwork.id,
                        'title': artwork.title,
                        'theme': artwork.theme.value,
                        'created_at': artwork.created_at,
                        'image_data': artwork.image_data
                    })
    
    def _render_narrative_therapy(self):
        """Render narrative therapy interface"""
        st.subheader("📝 Eco-Narrative Therapy")
        st.write("Therapeutic journaling and storytelling for environmental emotions")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            prompt_type = st.selectbox(
                "Journal Prompt Type",
                ["Reflection", "Emotional Processing", "Visioning", "Gratitude", "Progress"]
            )
            
            if st.button("📝 Get Prompt", use_container_width=True):
                prompt = self.narrative_engine.get_daily_prompt()
                st.session_state.creative_data['current_prompt'] = prompt
                st.rerun()
        
        with col2:
            st.markdown("### 💭 Today's Prompt")
            
            if 'current_prompt' in st.session_state.creative_data:
                prompt = st.session_state.creative_data['current_prompt']
                
                st.markdown(f"""
                <div class="prompt-card">
                    <h4 style="color: #4ade80;">{prompt.prompt_text}</h4>
                    <div style="margin-top: 10px;">
                        <div style="color: #94a3b8; font-size: 13px;">
                            🎯 Difficulty: {"★" * int(prompt.difficulty * 5)}
                        </div>
                        <div style="color: #94a3b8; font-size: 13px;">
                            ⏱️ Estimated Time: {prompt.estimated_duration} minutes
                        </div>
                        <div style="color: #94a3b8; font-size: 13px;">
                            🌿 Theme: {prompt.sustainability_theme}
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <div style="color: #94a3b8; font-size: 12px;">Guided Questions:</div>
                        {''.join([f'<div style="color: #94a3b8; font-size: 12px; margin-left: 15px;">• {q}</div>' for q in prompt.guided_questions])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Journal entry
                journal_entry = st.text_area(
                    "Write your thoughts...",
                    height=150,
                    placeholder="Start your journal entry here..."
                )
                
                if st.button("💾 Save Entry", use_container_width=True):
                    if journal_entry:
                        emotional_state = {
                            'hope': random.uniform(0.3, 0.8),
                            'peace': random.uniform(0.2, 0.7),
                            'determination': random.uniform(0.4, 0.9)
                        }
                        
                        entry_data = self.narrative_engine.save_journal_entry(
                            self.user_id,
                            prompt.id,
                            journal_entry,
                            emotional_state
                        )
                        
                        st.session_state.creative_data['journal_entries'].append(entry_data)
                        st.success("✅ Journal entry saved!")
                        st.balloons()
            else:
                st.info("Click 'Get Prompt' to start your journaling session")
        
        # Show recent entries
        if st.session_state.creative_data['journal_entries']:
            st.markdown("### 📖 Recent Entries")
            
            recent_entries = st.session_state.creative_data['journal_entries'][-3:][::-1]
            for entry in recent_entries:
                with st.expander(f"{entry['timestamp'].strftime('%b %d, %Y')} - Entry #{entry['id'][:6]}"):
                    st.write(entry['entry'][:200] + ("..." if len(entry['entry']) > 200 else ""))
                    
                    # Emotional state
                    st.markdown("**Emotional Signature:**")
                    emotion_cols = st.columns(len(entry['emotional_state']))
                    for idx, (emotion, value) in enumerate(entry['emotional_state'].items()):
                        with emotion_cols[idx]:
                            st.metric(emotion.capitalize(), f"{value*100:.1f}%")
    
    def _render_soundscapes(self):
        """Render soundscape generation interface"""
        st.subheader("🎵 Nature Soundscapes")
        st.write("AI-generated nature sounds from environmental data")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            sound_types = [st.value.capitalize() for st in SoundscapeType]
            selected_sound = st.selectbox("Select Soundscape Type", sound_types)
            
            mood_options = ["Peaceful", "Calm", "Hopeful", "Determined", "Reflective"]
            selected_mood = st.selectbox("Select Mood", mood_options)
            
            st.markdown("### 🌿 Environmental Parameters")
            carbon_level = st.slider("Carbon Level", 0.0, 1.0, 0.4)
            biodiversity = st.slider("Biodiversity", 0.0, 1.0, 0.7)
            conservation = st.slider("Conservation", 0.0, 1.0, 0.8)
        
        with col2:
            st.markdown("### 🎵 Soundscape Player")
            
            if st.button("🎶 Generate Soundscape", use_container_width=True):
                sound_map = {
                    'Forest': SoundscapeType.FOREST,
                    'Ocean': SoundscapeType.OCEAN,
                    'Rainforest': SoundscapeType.RAINFOREST,
                    'Desert': SoundscapeType.DESERT,
                    'Mountain': SoundscapeType.MOUNTAIN,
                    'Wetland': SoundscapeType.WETLAND,
                    'Urban': SoundscapeType.URBAN
                }
                
                sound_type = sound_map.get(selected_sound, SoundscapeType.FOREST)
                
                env_data = {
                    'carbon_level': carbon_level,
                    'biodiversity': biodiversity,
                    'conservation': conservation
                }
                
                soundscape = self.soundscape_engine.generate_soundscape(sound_type, env_data)
                
                st.session_state.creative_data['soundscapes'].append({
                    'id': soundscape.id,
                    'type': sound_type.value,
                    'created_at': soundscape.created_at,
                    'duration': soundscape.duration,
                    'mood_rating': soundscape.mood_rating
                })
                
                # Display soundscape info
                st.markdown(f"""
                <div class="soundscape-player">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="color: #4ade80; margin: 0;">🎵 {selected_sound} Soundscape</h4>
                            <p style="color: #94a3b8; font-size: 13px; margin: 5px 0;">
                                Duration: {soundscape.duration}s • Mood: {selected_mood}
                            </p>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #94a3b8; font-size: 12px;">Mood Rating</div>
                            <div style="font-size: 24px; font-weight: 700; color: #4ade80;">{soundscape.mood_rating*100:.0f}%</div>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <div style="color: #94a3b8; font-size: 12px;">Audio Parameters:</div>
                        <div style="display: flex; gap: 15px; font-size: 12px;">
                            <span style="color: #94a3b8;">Frequency: {soundscape.audio_parameters['base_frequency']:.0f}Hz</span>
                            <span style="color: #94a3b8;">Tempo: {soundscape.audio_parameters['tempo']} BPM</span>
                            <span style="color: #94a3b8;">Layers: {soundscape.audio_parameters['layers_active']}</span>
                        </div>
                    </div>
                    <div style="margin-top: 15px;">
                        <button style="background: #4ade80; color: #0f172a; border: none; padding: 8px 20px; border-radius: 8px; font-weight: 600;">
                            ▶ Play Soundscape
                        </button>
                        <button style="background: transparent; color: #94a3b8; border: 1px solid #94a3b8; padding: 8px 20px; border-radius: 8px; margin-left: 10px;">
                            ⬇ Download
                        </button>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    def _render_community_canvas(self):
        """Render community canvas interface"""
        st.subheader("🤝 Community Art Canvas")
        st.write("Collaborate with others to create collective environmental art")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🎨 Create or Join Canvas")
            
            canvas_action = st.radio("Action", ["Create New Canvas", "Join Existing Canvas"])
            
            if canvas_action == "Create New Canvas":
                canvas_name = st.text_input("Canvas Name", placeholder="e.g., 'Our Green Future'")
                canvas_desc = st.text_area("Description", placeholder="Describe your collaborative art project")
                canvas_theme = st.selectbox("Theme", [t.value.capitalize() for t in ArtTheme])
                
                if st.button("🚀 Create Canvas", use_container_width=True):
                    if canvas_name:
                        canvas = self.community_engine.create_canvas(
                            canvas_name,
                            canvas_desc,
                            self.user_id,
                            canvas_theme.lower()
                        )
                        st.success(f"✅ Canvas '{canvas_name}' created!")
                        st.session_state.creative_data['canvas_participations'].append(canvas.id)
                        st.rerun()
            
            else:
                # Show available canvases
                if self.community_engine.canvases:
                    canvas_options = [(cid, c.name) for cid, c in self.community_engine.canvases.items()]
                    selected_canvas = st.selectbox("Select Canvas", canvas_options, format_func=lambda x: x[1])
                    
                    if st.button("🔗 Join Canvas", use_container_width=True):
                        canvas_id = selected_canvas[0]
                        if canvas_id not in st.session_state.creative_data['canvas_participations']:
                            st.session_state.creative_data['canvas_participations'].append(canvas_id)
                            st.success("✅ Joined canvas successfully!")
                            st.rerun()
                else:
                    st.info("No canvases available. Create one to get started!")
        
        with col2:
            st.markdown("### 📊 Your Canvases")
            
            if st.session_state.creative_data['canvas_participations']:
                for canvas_id in st.session_state.creative_data['canvas_participations']:
                    if canvas_id in self.community_engine.canvases:
                        canvas = self.community_engine.canvases[canvas_id]
                        
                        st.markdown(f"""
                        <div class="artwork-card">
                            <h4 style="color: #4ade80; margin: 0;">🎨 {canvas.name}</h4>
                            <p style="color: #94a3b8; font-size: 13px;">{canvas.description}</p>
                            <div style="display: flex; gap: 15px; font-size: 12px; color: #94a3b8;">
                                <span>👥 {len(canvas.participants)} participants</span>
                                <span>🔄 {canvas.collaborations} contributions</span>
                                <span>📊 {canvas.completion_status*100:.0f}% complete</span>
                            </div>
                            <div style="margin-top: 8px;">
                                <div class="progress-bar-custom" style="height: 4px; background: rgba(74,222,128,0.2); border-radius: 2px;">
                                    <div class="progress-fill-custom" style="width: {canvas.completion_status*100}%; height: 100%;"></div>
                                </div>
                            </div>
                            <div style="margin-top: 10px;">
                                <button style="background: #4ade80; color: #0f172a; border: none; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">
                                    Add Contribution
                                </button>
                                <button style="background: transparent; color: #60a5fa; border: 1px solid #60a5fa; padding: 4px 12px; border-radius: 6px; font-size: 12px; margin-left: 5px;">
                                    View Gallery
                                </button>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("You haven't joined any canvases yet. Create or join one to collaborate!")
    
    def _render_gallery(self):
        """Render art gallery interface"""
        st.subheader("📚 Creative Gallery")
        st.write("Explore your creative journey and community art")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            medium_filter = st.selectbox("Medium", ["All", "Visual", "Narrative", "Sound", "Collaborative"])
        with col2:
            theme_filter = st.selectbox("Theme", ["All"] + [t.value.capitalize() for t in ArtTheme])
        with col3:
            sort_by = st.selectbox("Sort By", ["Recent", "Popular", "Emotional Impact"])
        
        # Display artworks
        st.markdown("### 🎨 Artworks")
        
        artworks = st.session_state.creative_data.get('artworks', [])
        if artworks:
            # Filter and sort
            filtered_artworks = artworks
            if theme_filter != "All":
                filtered_artworks = [a for a in filtered_artworks if a['theme'].capitalize() == theme_filter]
            
            # Display in grid
            cols = st.columns(3)
            for idx, artwork in enumerate(filtered_artworks[-9:][::-1]):
                with cols[idx % 3]:
                    st.image(f"data:image/png;base64,{artwork['image_data']}", use_column_width=True)
                    st.caption(f"**{artwork['title']}**")
                    st.caption(f"🎨 {artwork['theme'].capitalize()} | 📅 {artwork['created_at'].strftime('%b %d')}")
        else:
            st.info("No artworks yet. Generate some art to start your gallery!")
        
        # Display journal entries
        st.markdown("### 📝 Journal Entries")
        
        entries = st.session_state.creative_data.get('journal_entries', [])
        if entries:
            for entry in entries[-3:][::-1]:
                with st.expander(f"{entry['timestamp'].strftime('%b %d, %Y')} - {entry['prompt_id']}"):
                    st.write(entry['entry'][:300] + ("..." if len(entry['entry']) > 300 else ""))
                    st.caption(f"📊 Emotional State: {', '.join([f'{k}: {v*100:.0f}%' for k, v in entry['emotional_state'].items()])}")
        else:
            st.info("No journal entries yet. Start journaling to build your narrative collection!")

# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_creative_hub():
    """Main entry point for eco-creative expression system"""
    user_id = st.session_state.get('user_id', 1)
    
    ui = EcoCreativeUI(user_id)
    ui.render()

# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    st.set_page_config(page_title="Eco-Creative Expression", layout="wide")
    render_creative_hub()

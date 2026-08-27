"""
AI-Powered Eco-Synesthesia & Sensory Sustainability Experience Module
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
import colorsys
import math

logger = logging.getLogger(__name__)

# ============================================================
# ENUMS AND CONSTANTS
# ============================================================

class SensoryModality(Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    OLFACTORY = "olfactory"
    TACTILE = "tactile"
    GUSTATORY = "gustatory"
    EMOTIONAL = "emotional"

class EnvironmentalData(Enum):
    CARBON = "carbon_level"
    TEMPERATURE = "temperature"
    AIR_QUALITY = "air_quality"
    BIODIVERSITY = "biodiversity"
    WATER_QUALITY = "water_quality"
    NOISE_LEVEL = "noise_level"

class SynesthesiaProfile(Enum):
    VISUAL_DOMINANT = "visual_dominant"
    AUDITORY_DOMINANT = "auditory_dominant"
    TACTILE_DOMINANT = "tactile_dominant"
    OLFACTORY_DOMINANT = "olfactory_dominant"
    BALANCED = "balanced"

class EmotionalTone(Enum):
    CALM = "calm"
    URGENT = "urgent"
    PEACEFUL = "peaceful"
    CONCERNING = "concerning"
    HOPEFUL = "hopeful"
    ALARMING = "alarming"

# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class SensoryExperience:
    experience_id: str
    user_id: int
    timestamp: datetime
    modalities: List[SensoryModality]
    environmental_data: Dict[str, float]
    visual_output: Dict[str, Any]
    auditory_output: Dict[str, Any]
    olfactory_output: Dict[str, Any]
    tactile_output: Dict[str, Any]
    gustatory_output: Dict[str, Any]
    emotional_tone: EmotionalTone
    synesthesia_profile: SynesthesiaProfile
    intensity: float

@dataclass
class ColorMapping:
    """Environmental data to color mapping"""
    data_type: EnvironmentalData
    value: float
    r: int
    g: int
    b: int
    hex_color: str
    color_name: str
    emotional_association: str

@dataclass
class AudioMapping:
    """Environmental data to audio mapping"""
    data_type: EnvironmentalData
    value: float
    frequency: float
    amplitude: float
    waveform: str
    tempo: float
    mood: str

@dataclass
class OlfactoryMapping:
    """Environmental data to scent mapping"""
    data_type: EnvironmentalData
    value: float
    scent_name: str
    intensity: float
    pleasantness: float
    description: str
    emotional_trigger: str

@dataclass
class HapticMapping:
    """Environmental data to touch mapping"""
    data_type: EnvironmentalData
    value: float
    vibration_pattern: str
    intensity: float
    duration: float
    texture: str
    temperature_feel: str

@dataclass
class GustatoryMapping:
    """Environmental data to taste mapping"""
    data_type: EnvironmentalData
    value: float
    taste_profile: str
    intensity: float
    aftertaste: str
    emotional_link: str

# ============================================================
# COLOR SYNESTHESIA ENGINE
# ============================================================

class ColorSynesthesiaEngine:
    """
    Map environmental data to color experiences
    """
    
    def __init__(self):
        self.color_palettes = self._initialize_palettes()
        
    def _initialize_palettes(self) -> Dict:
        """Initialize color palettes for different data types"""
        return {
            EnvironmentalData.CARBON: {
                'low': {'r': 144, 'g': 238, 'b': 144, 'name': 'Light Green', 'emotion': 'hopeful'},
                'medium': {'r': 255, 'g': 165, 'b': 0, 'name': 'Orange', 'emotion': 'concerned'},
                'high': {'r': 255, 'g': 69, 'b': 0, 'name': 'Red', 'emotion': 'alarmed'}
            },
            EnvironmentalData.TEMPERATURE: {
                'cold': {'r': 70, 'g': 130, 'b': 255, 'name': 'Cool Blue', 'emotion': 'calm'},
                'moderate': {'r': 135, 'g': 206, 'b': 235, 'name': 'Sky Blue', 'emotion': 'peaceful'},
                'hot': {'r': 255, 'g': 99, 'b': 71, 'name': 'Warm Orange', 'emotion': 'urgent'}
            },
            EnvironmentalData.AIR_QUALITY: {
                'clean': {'r': 34, 'g': 197, 'b': 94, 'name': 'Clean Green', 'emotion': 'refreshing'},
                'moderate': {'r': 251, 'g': 191, 'b': 36, 'name': 'Yellow', 'emotion': 'caution'},
                'polluted': {'r': 156, 'g': 39, 'b': 39, 'name': 'Dark Red', 'emotion': 'alarming'}
            },
            EnvironmentalData.BIODIVERSITY: {
                'rich': {'r': 74, 'g': 222, 'b': 128, 'name': 'Vibrant Green', 'emotion': 'hopeful'},
                'moderate': {'r': 168, 'g': 85, 'b': 247, 'name': 'Purple', 'emotion': 'thoughtful'},
                'low': {'r': 156, 'g': 163, 'b': 175, 'name': 'Gray', 'emotion': 'concerned'}
            },
            EnvironmentalData.WATER_QUALITY: {
                'pure': {'r': 0, 'g': 191, 'b': 255, 'name': 'Crystal Blue', 'emotion': 'peaceful'},
                'moderate': {'r': 72, 'g': 149, 'b': 239, 'name': 'Deep Blue', 'emotion': 'reflective'},
                'polluted': {'r': 139, 'g': 69, 'b': 19, 'name': 'Brown', 'emotion': 'concerned'}
            },
            EnvironmentalData.NOISE_LEVEL: {
                'quiet': {'r': 200, 'g': 230, 'b': 255, 'name': 'Peaceful White', 'emotion': 'calm'},
                'moderate': {'r': 255, 'g': 193, 'b': 7, 'name': 'Golden', 'emotion': 'aware'},
                'loud': {'r': 255, 'g': 0, 'b': 0, 'name': 'Warning Red', 'emotion': 'stressed'}
            }
        }
    
    def map_to_color(self, data_type: EnvironmentalData, value: float) -> ColorMapping:
        """Map environmental data value to color"""
        palette = self.color_palettes.get(data_type, self.color_palettes[EnvironmentalData.CARBON])
        
        # Determine which category the value falls into
        if value < 0.33:
            category = 'low' if 'low' in palette else list(palette.keys())[0]
        elif value < 0.66:
            category = 'medium' if 'medium' in palette else list(palette.keys())[1]
        else:
            category = 'high' if 'high' in palette else list(palette.keys())[2]
        
        color_data = palette.get(category, palette[list(palette.keys())[0]])
        
        # Interpolate color for smooth transitions
        if value > 0 and value < 1:
            # Find neighboring categories
            categories = list(palette.keys())
            if len(categories) >= 2:
                category_values = [0.16, 0.5, 0.83]  # Approximate positions
                if len(category_values) == len(categories):
                    for i in range(len(categories) - 1):
                        if category_values[i] <= value <= category_values[i + 1]:
                            # Interpolate between two colors
                            ratio = (value - category_values[i]) / (category_values[i + 1] - category_values[i])
                            color1 = palette[categories[i]]
                            color2 = palette[categories[i + 1]]
                            r = int(color1['r'] + (color2['r'] - color1['r']) * ratio)
                            g = int(color1['g'] + (color2['g'] - color1['g']) * ratio)
                            b = int(color1['b'] + (color2['b'] - color1['b']) * ratio)
                            color_data = {'r': r, 'g': g, 'b': b, 'name': 'Interpolated', 'emotion': 'mixed'}
                            break
        
        hex_color = f"#{color_data['r']:02x}{color_data['g']:02x}{color_data['b']:02x}"
        
        return ColorMapping(
            data_type=data_type,
            value=value,
            r=color_data['r'],
            g=color_data['g'],
            b=color_data['b'],
            hex_color=hex_color,
            color_name=color_data.get('name', 'Unknown'),
            emotional_association=color_data.get('emotion', 'neutral')
        )
    
    def generate_color_palette(self, data_values: Dict) -> List[ColorMapping]:
        """Generate color palette from multiple environmental data values"""
        palette = []
        
        for data_type, value in data_values.items():
            try:
                env_type = EnvironmentalData(data_type)
                color = self.map_to_color(env_type, value)
                palette.append(color)
            except ValueError:
                continue
        
        return palette
    
    def get_color_therapy_recommendation(self, dominant_color: ColorMapping) -> str:
        """Get color therapy recommendation based on color"""
        color_recommendations = {
            'green': 'Spend time in nature to balance this energy',
            'blue': 'Practice calm breathing exercises',
            'red': 'Channel this energy into action',
            'orange': 'Engage in creative environmental work',
            'purple': 'Connect with environmental spirituality',
            'yellow': 'Share environmental knowledge with others'
        }
        
        color_lower = dominant_color.color_name.lower()
        for key, recommendation in color_recommendations.items():
            if key in color_lower:
                return recommendation
        
        return 'Embrace the colors of nature for balance'

# ============================================================
# AUDIO SYNESTHESIA ENGINE
# ============================================================

class AudioSynesthesiaEngine:
    """
    Map environmental data to audio experiences
    """
    
    def __init__(self):
        self.audio_mappings = self._initialize_mappings()
        
    def _initialize_mappings(self) -> Dict:
        """Initialize audio mappings for environmental data"""
        return {
            EnvironmentalData.CARBON: {
                'base_frequency': 200,
                'frequency_range': (100, 500),
                'waveform': 'sawtooth',
                'tempo_range': (60, 120)
            },
            EnvironmentalData.TEMPERATURE: {
                'base_frequency': 440,
                'frequency_range': (200, 800),
                'waveform': 'sine',
                'tempo_range': (70, 140)
            },
            EnvironmentalData.AIR_QUALITY: {
                'base_frequency': 330,
                'frequency_range': (150, 600),
                'waveform': 'square',
                'tempo_range': (80, 160)
            },
            EnvironmentalData.BIODIVERSITY: {
                'base_frequency': 520,
                'frequency_range': (300, 900),
                'waveform': 'triangle',
                'tempo_range': (50, 100)
            },
            EnvironmentalData.WATER_QUALITY: {
                'base_frequency': 280,
                'frequency_range': (120, 500),
                'waveform': 'sine',
                'tempo_range': (60, 120)
            },
            EnvironmentalData.NOISE_LEVEL: {
                'base_frequency': 180,
                'frequency_range': (80, 400),
                'waveform': 'noise',
                'tempo_range': (40, 100)
            }
        }
    
    def map_to_audio(self, data_type: EnvironmentalData, value: float) -> AudioMapping:
        """Map environmental data to audio parameters"""
        mapping = self.audio_mappings.get(data_type, self.audio_mappings[EnvironmentalData.CARBON])
        
        # Calculate frequency based on value
        min_freq, max_freq = mapping['frequency_range']
        frequency = min_freq + (max_freq - min_freq) * (1 - value)  # Higher value = lower frequency
        
        # Calculate amplitude based on value
        amplitude = 0.3 + value * 0.6
        
        # Calculate tempo based on value (higher value = faster tempo)
        min_tempo, max_tempo = mapping['tempo_range']
        tempo = min_tempo + (max_tempo - min_tempo) * value
        
        # Determine mood
        if value < 0.3:
            mood = 'peaceful'
        elif value < 0.6:
            mood = 'concerned'
        elif value < 0.8:
            mood = 'urgent'
        else:
            mood = 'alarming'
        
        return AudioMapping(
            data_type=data_type,
            value=value,
            frequency=frequency,
            amplitude=amplitude,
            waveform=mapping['waveform'],
            tempo=tempo,
            mood=mood
        )
    
    def generate_audio_description(self, audio_mappings: List[AudioMapping]) -> str:
        """Generate human-readable audio description"""
        descriptions = []
        
        for audio in audio_mappings:
            mood_emojis = {
                'peaceful': '😌',
                'concerned': '🤔',
                'urgent': '⚠️',
                'alarming': '🚨'
            }
            
            emoji = mood_emojis.get(audio.mood, '🎵')
            
            descriptions.append(
                f"{emoji} {audio.data_type.value.replace('_', ' ').title()}: "
                f"{audio.frequency:.0f}Hz, {audio.tempo:.0f} BPM, {audio.mood}"
            )
        
        return '\n'.join(descriptions)
    
    def get_audio_therapy_recommendation(self, dominant_audio: AudioMapping) -> str:
        """Get audio therapy recommendation"""
        recommendations = {
            'peaceful': 'Listen to nature sounds for relaxation',
            'concerned': 'Practice mindful listening to understand data',
            'urgent': 'Use this energy for environmental action',
            'alarming': 'Focus on solutions while acknowledging the urgency'
        }
        
        return recommendations.get(dominant_audio.mood, 'Listen to the data symphony')

# ============================================================
# OLFACTORY SYNESTHESIA ENGINE
# ============================================================

class OlfactorySynesthesiaEngine:
    """
    Map environmental data to scent experiences
    """
    
    def __init__(self):
        self.scent_mappings = self._initialize_scents()
        
    def _initialize_scents(self) -> Dict:
        """Initialize scent mappings for environmental data"""
        return {
            EnvironmentalData.AIR_QUALITY: {
                'clean': {
                    'scent': 'Fresh Pine',
                    'intensity': 0.2,
                    'pleasantness': 0.9,
                    'description': 'Crisp, clean forest air',
                    'emotional_trigger': 'refreshing'
                },
                'moderate': {
                    'scent': 'Wildflowers',
                    'intensity': 0.4,
                    'pleasantness': 0.7,
                    'description': 'Subtle floral notes',
                    'emotional_trigger': 'hopeful'
                },
                'polluted': {
                    'scent': 'Smoke',
                    'intensity': 0.7,
                    'pleasantness': 0.2,
                    'description': 'Acrid, burning smell',
                    'emotional_trigger': 'alarming'
                }
            },
            EnvironmentalData.WATER_QUALITY: {
                'pure': {
                    'scent': 'Rain',
                    'intensity': 0.2,
                    'pleasantness': 0.9,
                    'description': 'Fresh, clean water scent',
                    'emotional_trigger': 'peaceful'
                },
                'moderate': {
                    'scent': 'Moss',
                    'intensity': 0.3,
                    'pleasantness': 0.6,
                    'description': 'Earthy, wet moss',
                    'emotional_trigger': 'thoughtful'
                },
                'polluted': {
                    'scent': 'Stagnant',
                    'intensity': 0.6,
                    'pleasantness': 0.1,
                    'description': 'Heavy, stagnant water',
                    'emotional_trigger': 'concerned'
                }
            },
            EnvironmentalData.BIODIVERSITY: {
                'rich': {
                    'scent': 'Flower Garden',
                    'intensity': 0.5,
                    'pleasantness': 0.9,
                    'description': 'Rich, diverse floral scents',
                    'emotional_trigger': 'joyful'
                },
                'moderate': {
                    'scent': 'Herbs',
                    'intensity': 0.3,
                    'pleasantness': 0.7,
                    'description': 'Aromatic herb garden',
                    'emotional_trigger': 'reflective'
                },
                'low': {
                    'scent': 'Dust',
                    'intensity': 0.2,
                    'pleasantness': 0.3,
                    'description': 'Dry, dusty air',
                    'emotional_trigger': 'concerned'
                }
            }
        }
    
    def map_to_scent(self, data_type: EnvironmentalData, value: float) -> OlfactoryMapping:
        """Map environmental data to scent experience"""
        scent_data = self.scent_mappings.get(data_type, {})
        if not scent_data:
            return OlfactoryMapping(
                data_type=data_type,
                value=value,
                scent_name='Neutral',
                intensity=0.3,
                pleasantness=0.5,
                description='No scent mapping available',
                emotional_trigger='neutral'
            )
        
        # Determine category
        if value < 0.3 and 'clean' in scent_data:
            category = 'clean'
        elif value < 0.6 and 'moderate' in scent_data:
            category = 'moderate'
        elif 'polluted' in scent_data:
            category = 'polluted'
        else:
            category = list(scent_data.keys())[0]
        
        scent_info = scent_data.get(category, scent_data[list(scent_data.keys())[0]])
        
        return OlfactoryMapping(
            data_type=data_type,
            value=value,
            scent_name=scent_info['scent'],
            intensity=scent_info['intensity'],
            pleasantness=scent_info['pleasantness'],
            description=scent_info['description'],
            emotional_trigger=scent_info['emotional_trigger']
        )
    
    def generate_scent_journey(self, scent_mappings: List[OlfactoryMapping]) -> str:
        """Generate a scent journey description"""
        journey = []
        
        for scent in scent_mappings:
            emotion_emojis = {
                'refreshing': '💚',
                'hopeful': '🌱',
                'alarming': '🚨',
                'peaceful': '😌',
                'thoughtful': '🤔',
                'concerned': '⚠️',
                'joyful': '😊',
                'reflective': '🧘',
                'neutral': '🌿'
            }
            
            emoji = emotion_emojis.get(scent.emotional_trigger, '🌬️')
            
            journey.append(
                f"{emoji} {scent.scent_name}: {scent.description} "
                f"(Intensity: {scent.intensity*100:.0f}%, Pleasantness: {scent.pleasantness*100:.0f}%)"
            )
        
        return '\n'.join(journey)

# ============================================================
# HAPTIC SYNESTHESIA ENGINE
# ============================================================

class HapticSynesthesiaEngine:
    """
    Map environmental data to tactile experiences
    """
    
    def __init__(self):
        self.haptic_patterns = self._initialize_patterns()
        
    def _initialize_patterns(self) -> Dict:
        """Initialize haptic patterns for environmental data"""
        return {
            EnvironmentalData.CARBON: {
                'low': {'pattern': 'gentle_pulse', 'intensity': 0.3, 'duration': 1.0, 'texture': 'smooth', 'temp': 'cool'},
                'medium': {'pattern': 'rhythmic_tap', 'intensity': 0.6, 'duration': 1.5, 'texture': 'rough', 'temp': 'warm'},
                'high': {'pattern': 'sharp_pulse', 'intensity': 0.9, 'duration': 0.5, 'texture': 'spiky', 'temp': 'hot'}
            },
            EnvironmentalData.AIR_QUALITY: {
                'clean': {'pattern': 'soft_breeze', 'intensity': 0.2, 'duration': 2.0, 'texture': 'silky', 'temp': 'cool'},
                'moderate': {'pattern': 'light_tap', 'intensity': 0.4, 'duration': 1.0, 'texture': 'textured', 'temp': 'warm'},
                'polluted': {'pattern': 'intense_vibration', 'intensity': 0.8, 'duration': 0.8, 'texture': 'rough', 'temp': 'hot'}
            },
            EnvironmentalData.TEMPERATURE: {
                'cold': {'pattern': 'tremor', 'intensity': 0.3, 'duration': 1.5, 'texture': 'slick', 'temp': 'freezing'},
                'moderate': {'pattern': 'steady_hum', 'intensity': 0.5, 'duration': 2.0, 'texture': 'smooth', 'temp': 'cool'},
                'hot': {'pattern': 'intense_pulse', 'intensity': 0.8, 'duration': 0.8, 'texture': 'dry', 'temp': 'scorching'}
            }
        }
    
    def map_to_haptic(self, data_type: EnvironmentalData, value: float) -> HapticMapping:
        """Map environmental data to haptic experience"""
        pattern_data = self.haptic_patterns.get(data_type, {})
        if not pattern_data:
            return HapticMapping(
                data_type=data_type,
                value=value,
                vibration_pattern='neutral',
                intensity=0.3,
                duration=1.0,
                texture='smooth',
                temperature_feel='neutral'
            )
        
        # Determine category
        if value < 0.3:
            category = 'low' if 'low' in pattern_data else list(pattern_data.keys())[0]
        elif value < 0.6:
            category = 'medium' if 'medium' in pattern_data else list(pattern_data.keys())[1]
        else:
            category = 'high' if 'high' in pattern_data else list(pattern_data.keys())[2]
        
        pattern_info = pattern_data.get(category, pattern_data[list(pattern_data.keys())[0]])
        
        return HapticMapping(
            data_type=data_type,
            value=value,
            vibration_pattern=pattern_info['pattern'],
            intensity=pattern_info['intensity'],
            duration=pattern_info['duration'],
            texture=pattern_info['texture'],
            temperature_feel=pattern_info['temp']
        )
    
    def generate_haptic_experience(self, haptic_mappings: List[HapticMapping]) -> str:
        """Generate haptic experience description"""
        experiences = []
        
        for haptic in haptic_mappings:
            texture_emojis = {
                'smooth': '🌀',
                'rough': '🌊',
                'spiky': '⚡',
                'silky': '🫧',
                'textured': '🔮',
                'slick': '💧',
                'dry': '🏜️'
            }
            
            emoji = texture_emojis.get(haptic.texture, '🤲')
            
            temp_emojis = {
                'cool': '❄️',
                'warm': '🔥',
                'hot': '☀️',
                'freezing': '🥶',
                'scorching': '🌋',
                'neutral': '🌡️'
            }
            
            temp_emoji = temp_emojis.get(haptic.temperature_feel, '🌡️')
            
            experiences.append(
                f"{emoji}{temp_emoji} {haptic.data_type.value.replace('_', ' ').title()}: "
                f"{haptic.vibration_pattern} (Intensity: {haptic.intensity*100:.0f}%, Texture: {haptic.texture}, "
                f"Feel: {haptic.temperature_feel})"
            )
        
        return '\n'.join(experiences)

# ============================================================
# GUSTATORY SYNESTHESIA ENGINE
# ============================================================

class GustatorySynesthesiaEngine:
    """
    Map environmental data to taste experiences
    """
    
    def __init__(self):
        self.taste_mappings = self._initialize_tastes()
        
    def _initialize_tastes(self) -> Dict:
        """Initialize taste mappings for environmental data"""
        return {
            EnvironmentalData.WATER_QUALITY: {
                'pure': {'taste': 'Fresh Mineral', 'intensity': 0.2, 'aftertaste': 'Clean', 'emotion': 'peaceful'},
                'moderate': {'taste': 'Earthy', 'intensity': 0.4, 'aftertaste': 'Metallic', 'emotion': 'concerned'},
                'polluted': {'taste': 'Bitter', 'intensity': 0.7, 'aftertaste': 'Toxic', 'emotion': 'alarmed'}
            },
            EnvironmentalData.AIR_QUALITY: {
                'clean': {'taste': 'Crisp Air', 'intensity': 0.1, 'aftertaste': 'Fresh', 'emotion': 'refreshing'},
                'moderate': {'taste': 'Slightly Tangy', 'intensity': 0.3, 'aftertaste': 'Smoky', 'emotion': 'cautious'},
                'polluted': {'taste': 'Acrid', 'intensity': 0.6, 'aftertaste': 'Chemical', 'emotion': 'alarming'}
            },
            EnvironmentalData.BIODIVERSITY: {
                'rich': {'taste': 'Complex Floral', 'intensity': 0.3, 'aftertaste': 'Fruity', 'emotion': 'joyful'},
                'moderate': {'taste': 'Herbal', 'intensity': 0.4, 'aftertaste': 'Earthy', 'emotion': 'reflective'},
                'low': {'taste': 'Bland', 'intensity': 0.2, 'aftertaste': 'Empty', 'emotion': 'concerned'}
            }
        }
    
    def map_to_taste(self, data_type: EnvironmentalData, value: float) -> GustatoryMapping:
        """Map environmental data to taste experience"""
        taste_data = self.taste_mappings.get(data_type, {})
        if not taste_data:
            return GustatoryMapping(
                data_type=data_type,
                value=value,
                taste_profile='Neutral',
                intensity=0.3,
                aftertaste='None',
                emotional_link='neutral'
            )
        
        # Determine category
        if value < 0.3:
            category = 'pure' if 'pure' in taste_data else list(taste_data.keys())[0]
        elif value < 0.6:
            category = 'moderate' if 'moderate' in taste_data else list(taste_data.keys())[1]
        else:
            category = 'polluted' if 'polluted' in taste_data else list(taste_data.keys())[2]
        
        taste_info = taste_data.get(category, taste_data[list(taste_data.keys())[0]])
        
        return GustatoryMapping(
            data_type=data_type,
            value=value,
            taste_profile=taste_info['taste'],
            intensity=taste_info['intensity'],
            aftertaste=taste_info['aftertaste'],
            emotional_link=taste_info['emotion']
        )
    
    def generate_taste_narrative(self, taste_mappings: List[GustatoryMapping]) -> str:
        """Generate taste experience narrative"""
        narratives = []
        
        for taste in taste_mappings:
            emotion_emojis = {
                'peaceful': '😌',
                'concerned': '🤔',
                'alarmed': '🚨',
                'refreshing': '💚',
                'cautious': '⚡',
                'alarming': '🔴',
                'joyful': '😊',
                'reflective': '🧘',
                'neutral': '🌿'
            }
            
            emoji = emotion_emojis.get(taste.emotional_link, '👅')
            
            narratives.append(
                f"{emoji} {taste.data_type.value.replace('_', ' ').title()}: "
                f"{taste.taste_profile} (Intensity: {taste.intensity*100:.0f}%, "
                f"Aftertaste: {taste.aftertaste}) → {taste.emotional_link}"
            )
        
        return '\n'.join(narratives)

# ============================================================
# EMOTIONAL SYNESTHESIA ENGINE
# ============================================================

class EmotionalSynesthesiaEngine:
    """
    Generate emotional resonance from environmental data
    """
    
    def __init__(self):
        self.emotional_mappings = self._initialize_emotions()
        
    def _initialize_emotions(self) -> Dict:
        """Initialize emotional mappings for environmental data"""
        return {
            EnvironmentalData.CARBON: {
                'low': {'emotion': EmotionalTone.HOPEFUL, 'intensity': 0.3, 'description': 'Feeling optimistic about carbon reduction'},
                'medium': {'emotion': EmotionalTone.CONCERNING, 'intensity': 0.6, 'description': 'Concerned about carbon levels'},
                'high': {'emotion': EmotionalTone.ALARMING, 'intensity': 0.9, 'description': 'Alarmed by high carbon levels'}
            },
            EnvironmentalData.TEMPERATURE: {
                'cold': {'emotion': EmotionalTone.CALM, 'intensity': 0.3, 'description': 'Cool, calm temperature awareness'},
                'moderate': {'emotion': EmotionalTone.PEACEFUL, 'intensity': 0.5, 'description': 'Balanced temperature perception'},
                'hot': {'emotion': EmotionalTone.URGENT, 'intensity': 0.8, 'description': 'Urgent climate warming awareness'}
            },
            EnvironmentalData.AIR_QUALITY: {
                'clean': {'emotion': EmotionalTone.PEACEFUL, 'intensity': 0.2, 'description': 'Breathing clean, peaceful air'},
                'moderate': {'emotion': EmotionalTone.CONCERNING, 'intensity': 0.5, 'description': 'Cautious about air quality'},
                'polluted': {'emotion': EmotionalTone.ALARMING, 'intensity': 0.9, 'description': 'Alarmed by poor air quality'}
            }
        }
    
    def map_to_emotion(self, data_type: EnvironmentalData, value: float) -> Dict:
        """Map environmental data to emotional response"""
        emotion_data = self.emotional_mappings.get(data_type, {})
        if not emotion_data:
            return {'emotion': EmotionalTone.CALM, 'intensity': 0.3, 'description': 'Emotional neutral'}
        
        # Determine category
        if value < 0.3:
            category = 'low' if 'low' in emotion_data else list(emotion_data.keys())[0]
        elif value < 0.6:
            category = 'medium' if 'medium' in emotion_data else list(emotion_data.keys())[1]
        else:
            category = 'high' if 'high' in emotion_data else list(emotion_data.keys())[2]
        
        return emotion_data.get(category, emotion_data[list(emotion_data.keys())[0]])

# ============================================================
# MAIN UI COMPONENT
# ============================================================

class EcoSynesthesiaUI:
    """
    Complete UI for eco-synesthesia module
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.color_engine = ColorSynesthesiaEngine()
        self.audio_engine = AudioSynesthesiaEngine()
        self.olfactory_engine = OlfactorySynesthesiaEngine()
        self.haptic_engine = HapticSynesthesiaEngine()
        self.gustatory_engine = GustatorySynesthesiaEngine()
        self.emotional_engine = EmotionalSynesthesiaEngine()
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        if 'synesthesia_data' not in st.session_state:
            st.session_state.synesthesia_data = {
                'experiences': [],
                'preferred_profile': SynesthesiaProfile.BALANCED.value,
                'current_experience': None
            }
    
    def render(self):
        """Render the complete UI"""
        st.markdown("""
        <style>
        .synesthesia-header {
            background: linear-gradient(135deg, #0a0a2a, #2a0a3a, #0a2a2a);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            border: 1px solid rgba(168, 85, 247, 0.3);
            text-align: center;
        }
        .synesthesia-header h2 {
            color: #a78bfa;
            margin: 0;
            font-size: 32px;
        }
        .synesthesia-header p {
            color: #94a3b8;
            margin: 5px 0 0 0;
        }
        .synesthesia-card {
            background: linear-gradient(135deg, #0a0a2a, #1a0a3a);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(168, 85, 247, 0.15);
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        .synesthesia-card:hover {
            border-color: #a78bfa;
            transform: translateY(-2px);
        }
        .sensory-tag {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            margin: 2px;
        }
        .color-display {
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            font-weight: 600;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown("""
        <div class="synesthesia-header">
            <h2>🎨 Eco-Synesthesia & Sensory Sustainability</h2>
            <p>Experience environmental data through all your senses</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Main tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "👁️ Visual Synesthesia",
            "👂 Auditory Synesthesia",
            "👃 Olfactory Synesthesia",
            "🤲 Haptic Synesthesia",
            "👅 Gustatory Synesthesia"
        ])
        
        with tab1:
            self._render_visual_synesthesia()
        
        with tab2:
            self._render_auditory_synesthesia()
        
        with tab3:
            self._render_olfactory_synesthesia()
        
        with tab4:
            self._render_haptic_synesthesia()
        
        with tab5:
            self._render_gustatory_synesthesia()
    
    def _render_visual_synesthesia(self):
        """Render visual synesthesia interface"""
        st.subheader("👁️ Visual Synesthesia - See Environmental Data")
        st.write("Experience environmental data as colors and visual patterns")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🌈 Color Mapping")
            
            # Environmental data sliders
            carbon = st.slider("Carbon Level", 0.0, 1.0, 0.5, key="vis_carbon")
            temperature = st.slider("Temperature", 0.0, 1.0, 0.4, key="vis_temp")
            air_quality = st.slider("Air Quality", 0.0, 1.0, 0.6, key="vis_air")
            biodiversity = st.slider("Biodiversity", 0.0, 1.0, 0.7, key="vis_bio")
            
            data_values = {
                'carbon_level': carbon,
                'temperature': temperature,
                'air_quality': air_quality,
                'biodiversity': biodiversity
            }
        
        with col2:
            st.markdown("### 🎨 Your Color Experience")
            
            if st.button("🌈 Generate Color Experience", use_container_width=True):
                colors = self.color_engine.generate_color_palette(data_values)
                
                # Display colors
                for color in colors:
                    st.markdown(f"""
                    <div class="color-display" style="background: {color.hex_color}; color: {'white' if (color.r + color.g + color.b) < 384 else 'black'};">
                        {color.data_type.value.replace('_', ' ').title()}: {color.color_name}
                        <br>
                        <span style="font-size: 12px; opacity: 0.8;">{color.emotional_association}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Color therapy recommendation
                if colors:
                    dominant_color = max(colors, key=lambda x: x.value)
                    recommendation = self.color_engine.get_color_therapy_recommendation(dominant_color)
                    st.info(f"💡 Color Therapy: {recommendation}")
    
    def _render_auditory_synesthesia(self):
        """Render auditory synesthesia interface"""
        st.subheader("👂 Auditory Synesthesia - Hear Environmental Data")
        st.write("Listen to environmental data through sound frequencies and rhythms")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🎵 Sound Mapping")
            
            carbon = st.slider("Carbon Level", 0.0, 1.0, 0.5, key="aud_carbon")
            temperature = st.slider("Temperature", 0.0, 1.0, 0.4, key="aud_temp")
            air_quality = st.slider("Air Quality", 0.0, 1.0, 0.6, key="aud_air")
            
            data_values = {
                'carbon_level': carbon,
                'temperature': temperature,
                'air_quality': air_quality
            }
        
        with col2:
            st.markdown("### 🎶 Your Sound Experience")
            
            if st.button("🔊 Generate Sound Experience", use_container_width=True):
                audio_mappings = []
                for data_type, value in data_values.items():
                    try:
                        env_type = EnvironmentalData(data_type)
                        audio = self.audio_engine.map_to_audio(env_type, value)
                        audio_mappings.append(audio)
                    except ValueError:
                        continue
                
                # Display audio description
                description = self.audio_engine.generate_audio_description(audio_mappings)
                st.text(description)
                
                # Audio therapy recommendation
                if audio_mappings:
                    dominant_audio = max(audio_mappings, key=lambda x: x.amplitude)
                    recommendation = self.audio_engine.get_audio_therapy_recommendation(dominant_audio)
                    st.info(f"💡 Audio Therapy: {recommendation}")
                
                # Visual frequency display
                if audio_mappings:
                    st.markdown("### 📊 Frequency Visualization")
                    freq_data = []
                    for audio in audio_mappings:
                        freq_data.append({
                            'Data': audio.data_type.value.replace('_', ' ').title(),
                            'Frequency (Hz)': audio.frequency,
                            'Tempo (BPM)': audio.tempo
                        })
                    
                    df = pd.DataFrame(freq_data)
                    fig = px.bar(df, x='Data', y='Frequency (Hz)', 
                               title='Environmental Data Sound Frequencies',
                               color='Tempo (BPM)', color_continuous_scale='Viridis')
                    fig.update_layout(
                        height=250,
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    def _render_olfactory_synesthesia(self):
        """Render olfactory synesthesia interface"""
        st.subheader("👃 Olfactory Synesthesia - Smell Environmental Data")
        st.write("Experience environmental data through scent and aroma")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🌸 Scent Mapping")
            
            air_quality = st.slider("Air Quality", 0.0, 1.0, 0.6, key="olf_air")
            water_quality = st.slider("Water Quality", 0.0, 1.0, 0.7, key="olf_water")
            biodiversity = st.slider("Biodiversity", 0.0, 1.0, 0.5, key="olf_bio")
            
            data_values = {
                'air_quality': air_quality,
                'water_quality': water_quality,
                'biodiversity': biodiversity
            }
        
        with col2:
            st.markdown("### 🌿 Your Scent Experience")
            
            if st.button("🌬️ Generate Scent Experience", use_container_width=True):
                scent_mappings = []
                for data_type, value in data_values.items():
                    try:
                        env_type = EnvironmentalData(data_type)
                        scent = self.olfactory_engine.map_to_scent(env_type, value)
                        scent_mappings.append(scent)
                    except ValueError:
                        continue
                
                # Display scent journey
                journey = self.olfactory_engine.generate_scent_journey(scent_mappings)
                st.text(journey)
                
                # Scent visualization
                if scent_mappings:
                    st.markdown("### 📊 Scent Profile")
                    scent_data = []
                    for scent in scent_mappings:
                        scent_data.append({
                            'Data': scent.data_type.value.replace('_', ' ').title(),
                            'Scent': scent.scent_name,
                            'Intensity': scent.intensity * 100,
                            'Pleasantness': scent.pleasantness * 100
                        })
                    
                    df = pd.DataFrame(scent_data)
                    fig = px.bar(df, x='Data', y=['Intensity', 'Pleasantness'],
                               title='Scent Profile',
                               barmode='group',
                               color_discrete_sequence=['#a78bfa', '#4ade80'])
                    fig.update_layout(
                        height=250,
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    def _render_haptic_synesthesia(self):
        """Render haptic synesthesia interface"""
        st.subheader("🤲 Haptic Synesthesia - Feel Environmental Data")
        st.write("Experience environmental data through touch and vibration")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🖐️ Touch Mapping")
            
            carbon = st.slider("Carbon Level", 0.0, 1.0, 0.5, key="hap_carbon")
            temperature = st.slider("Temperature", 0.0, 1.0, 0.4, key="hap_temp")
            air_quality = st.slider("Air Quality", 0.0, 1.0, 0.6, key="hap_air")
            
            data_values = {
                'carbon_level': carbon,
                'temperature': temperature,
                'air_quality': air_quality
            }
        
        with col2:
            st.markdown("### 🤲 Your Touch Experience")
            
            if st.button("🤚 Generate Haptic Experience", use_container_width=True):
                haptic_mappings = []
                for data_type, value in data_values.items():
                    try:
                        env_type = EnvironmentalData(data_type)
                        haptic = self.haptic_engine.map_to_haptic(env_type, value)
                        haptic_mappings.append(haptic)
                    except ValueError:
                        continue
                
                # Display haptic experience
                experience = self.haptic_engine.generate_haptic_experience(haptic_mappings)
                st.text(experience)
                
                # Haptic visualization
                if haptic_mappings:
                    st.markdown("### 📊 Haptic Profile")
                    haptic_data = []
                    for haptic in haptic_mappings:
                        haptic_data.append({
                            'Data': haptic.data_type.value.replace('_', ' ').title(),
                            'Intensity': haptic.intensity * 100,
                            'Duration': haptic.duration * 100
                        })
                    
                    df = pd.DataFrame(haptic_data)
                    fig = px.radar(df, r='Intensity', theta='Data',
                                  title='Haptic Intensity Profile',
                                  color_discrete_sequence=['#a78bfa'])
                    fig.update_layout(
                        height=250,
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    def _render_gustatory_synesthesia(self):
        """Render gustatory synesthesia interface"""
        st.subheader("👅 Gustatory Synesthesia - Taste Environmental Data")
        st.write("Experience environmental data through taste and flavor")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🍽️ Taste Mapping")
            
            water_quality = st.slider("Water Quality", 0.0, 1.0, 0.7, key="gus_water")
            air_quality = st.slider("Air Quality", 0.0, 1.0, 0.6, key="gus_air")
            biodiversity = st.slider("Biodiversity", 0.0, 1.0, 0.5, key="gus_bio")
            
            data_values = {
                'water_quality': water_quality,
                'air_quality': air_quality,
                'biodiversity': biodiversity
            }
        
        with col2:
            st.markdown("### 🍬 Your Taste Experience")
            
            if st.button("👅 Generate Taste Experience", use_container_width=True):
                taste_mappings = []
                for data_type, value in data_values.items():
                    try:
                        env_type = EnvironmentalData(data_type)
                        taste = self.gustatory_engine.map_to_taste(env_type, value)
                        taste_mappings.append(taste)
                    except ValueError:
                        continue
                
                # Display taste narrative
                narrative = self.gustatory_engine.generate_taste_narrative(taste_mappings)
                st.text(narrative)
                
                # Taste visualization
                if taste_mappings:
                    st.markdown("### 📊 Taste Profile")
                    taste_data = []
                    for taste in taste_mappings:
                        taste_data.append({
                            'Data': taste.data_type.value.replace('_', ' ').title(),
                            'Taste': taste.taste_profile,
                            'Intensity': taste.intensity * 100,
                            'Aftertaste': taste.aftertaste
                        })
                    
                    df = pd.DataFrame(taste_data)
                    fig = px.bar(df, x='Data', y='Intensity',
                               title='Taste Intensity Profile',
                               color='Taste',
                               color_discrete_sequence=['#4ade80', '#a78bfa', '#fbbf24'])
                    fig.update_layout(
                        height=250,
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_synesthesia_hub():
    """Main entry point for eco-synesthesia system"""
    user_id = st.session_state.get('user_id', 1)
    
    ui = EcoSynesthesiaUI(user_id)
    ui.render()

# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    st.set_page_config(page_title="Eco-Synesthesia", layout="wide")
    render_synesthesia_hub()

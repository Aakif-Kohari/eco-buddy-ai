"""
Population Demographics and Daily Routine Generator.
Generates millions of virtual citizens with socioeconomic profiles determining
their vehicle ownership, EV adoption chance, and daily commute times.
"""

from typing import List, Dict
import random
import logging

logger = logging.getLogger(__name__)

class Citizen:
    def __init__(self, citizen_id: str, home_node: str, work_node: str, income_bracket: str):
        self.id = citizen_id
        self.home_node = home_node
        self.work_node = work_node
        self.income_bracket = income_bracket # LOW, MIDDLE, HIGH
        
        # Determine transport mode based on income
        self.owns_car = False
        self.owns_ev = False
        self.takes_transit = False
        
        self._assign_transport()
        
        # Generate daily schedule (seconds since midnight)
        # Normal commute: leave 7 AM - 9 AM (25200 - 32400)
        self.commute_departure_time = random.uniform(25200, 32400)
        # Return home: leave 4 PM - 6 PM (57600 - 64800)
        self.return_departure_time = random.uniform(57600, 64800)
        
    def _assign_transport(self):
        roll = random.random()
        
        if self.income_bracket == "LOW":
            # High transit reliance, low car ownership, zero EV
            if roll < 0.70:
                self.takes_transit = True
            else:
                self.owns_car = True
                
        elif self.income_bracket == "MIDDLE":
            # Balanced
            if roll < 0.20:
                self.takes_transit = True
            elif roll < 0.35:
                self.owns_car = True
                self.owns_ev = True
            else:
                self.owns_car = True
                
        elif self.income_bracket == "HIGH":
            # High car ownership, high EV adoption
            if roll < 0.05:
                self.takes_transit = True
            elif roll < 0.55:
                self.owns_car = True
                self.owns_ev = True
            else:
                self.owns_car = True

class DemographicsEngine:
    def __init__(self):
        self.citizens: List[Citizen] = []
        
    def generate_population(self, count: int, nodes: List[str]):
        if len(nodes) < 2:
            return
            
        for i in range(count):
            home = random.choice(nodes)
            work = random.choice(nodes)
            while work == home:
                work = random.choice(nodes)
                
            # Distribution of income
            roll = random.random()
            if roll < 0.30:
                inc = "LOW"
            elif roll < 0.80:
                inc = "MIDDLE"
            else:
                inc = "HIGH"
                
            citizen = Citizen(f"Citizen_{i}", home, work, inc)
            self.citizens.append(citizen)
            
        logger.info(f"Generated {count} citizens with socioeconomic transport profiles.")
        
    def get_ev_adoption_rate(self) -> float:
        """Returns the percentage of car owners who drive an EV."""
        car_owners = sum(1 for c in self.citizens if c.owns_car)
        if car_owners == 0: return 0.0
        ev_owners = sum(1 for c in self.citizens if c.owns_ev)
        return ev_owners / car_owners
        
    def get_transit_ridership_rate(self) -> float:
        """Returns percentage of population taking transit."""
        if not self.citizens: return 0.0
        transit = sum(1 for c in self.citizens if c.takes_transit)
        return transit / len(self.citizens)

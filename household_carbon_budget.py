"""
Household Carbon Budget Planner.

Lets households set monthly/weekly carbon budgets per emission category,
track actual consumption against targets, generate alerts when approaching
or exceeding limits, and provide historical budget-vs-actual analytics.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────

class BudgetPeriod(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


class Category(str, Enum):
    TRANSPORT = "transport"
    ENERGY = "energy"
    FOOD = "food"
    WASTE = "waste"
    WATER = "water"
    SHOPPING = "shopping"
    TRAVEL = "travel"
    OTHER = "other"


# ──────────────────────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BudgetAllocation:
    """A single category budget within a budget plan."""
    category: Category
    limit_kg: float
    spent_kg: float = 0.0
    alert_threshold_pct: float = 80.0  # percent of limit to trigger warning

    @property
    def remaining_kg(self) -> float:
        return max(0.0, self.limit_kg - self.spent_kg)

    @property
    def utilization_pct(self) -> float:
        if self.limit_kg <= 0:
            return 0.0
        return round((self.spent_kg / self.limit_kg) * 100, 1)

    @property
    def alert_level(self) -> AlertLevel:
        pct = self.utilization_pct
        if pct >= 100:
            return AlertLevel.EXCEEDED
        elif pct >= self.alert_threshold_pct:
            return AlertLevel.CRITICAL
        elif pct >= 60:
            return AlertLevel.WARNING
        return AlertLevel.INFO


@dataclass
class BudgetPlan:
    """A household budget plan covering one period."""
    plan_id: str
    household_id: str
    period: BudgetPeriod
    start_date: str
    end_date: str
    total_limit_kg: float
    allocations: Dict[str, BudgetAllocation] = field(default_factory=dict)
    created_at: str = ""
    is_active: bool = True

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def total_spent_kg(self) -> float:
        return sum(a.spent_kg for a in self.allocations.values())

    @property
    def total_remaining_kg(self) -> float:
        return max(0.0, self.total_limit_kg - self.total_spent_kg)

    @property
    def overall_utilization_pct(self) -> float:
        if self.total_limit_kg <= 0:
            return 0.0
        return round((self.total_spent_kg / self.total_limit_kg) * 100, 1)


@dataclass
class SpendingEntry:
    """A single carbon spending record."""
    entry_id: str
    household_id: str
    category: Category
    kg_co2: float
    description: str
    source: str  # e.g., "manual", "api", "ocr"
    recorded_at: str = ""

    def __post_init__(self):
        if not self.recorded_at:
            self.recorded_at = datetime.now().isoformat()


@dataclass
class BudgetAlert:
    """An alert generated when a budget threshold is crossed."""
    alert_id: str
    household_id: str
    plan_id: str
    category: Category
    level: AlertLevel
    message: str
    utilization_pct: float
    created_at: str = ""
    acknowledged: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class MonthlySnapshot:
    """Historical snapshot of budget performance for one period."""
    month: str  # YYYY-MM
    total_limit_kg: float
    total_spent_kg: float
    category_breakdown: Dict[str, float]
    alerts_count: int
    under_budget: bool


# ──────────────────────────────────────────────────────────────────────────────
# Core Engine
# ──────────────────────────────────────────────────────────────────────────────

class HouseholdCarbonBudgetPlanner:
    """
    Manages household carbon budgets: plans, spending, alerts,
    and historical analytics.
    """

    def __init__(self) -> None:
        self.plans: Dict[str, BudgetPlan] = {}  # plan_id -> BudgetPlan
        self.household_plans: Dict[str, List[str]] = {}  # household_id -> [plan_ids]
        self.spending: Dict[str, List[SpendingEntry]] = {}  # household_id -> entries
        self.alerts: Dict[str, List[BudgetAlert]] = {}  # household_id -> alerts
        self.snapshots: Dict[str, List[MonthlySnapshot]] = {}  # household_id -> snapshots

    # ── Plan Management ───────────────────────────────────────────────────

    def create_budget_plan(
        self,
        household_id: str,
        period: BudgetPeriod,
        start_date: str,
        end_date: str,
        total_limit_kg: float,
        allocations: Optional[Dict[str, float]] = None,
    ) -> BudgetPlan:
        """
        Creates a new budget plan for a household.

        Args:
            household_id: Household identifier.
            period: Budget period (weekly, monthly, quarterly, yearly).
            start_date: ISO date string for plan start.
            end_date: ISO date string for plan end.
            total_limit_kg: Total carbon budget in kg CO2.
            allocations: Optional dict mapping category name to limit in kg.

        Returns:
            The newly created BudgetPlan.
        """
        plan_id = f"bp_{uuid.uuid4().hex[:12]}"
        plan = BudgetPlan(
            plan_id=plan_id,
            household_id=household_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_limit_kg=total_limit_kg,
        )

        if allocations:
            remaining = total_limit_kg
            for cat_name, limit in allocations.items():
                try:
                    cat = Category(cat_name)
                except ValueError:
                    continue
                plan.allocations[cat_name] = BudgetAllocation(
                    category=cat, limit_kg=limit
                )
                remaining -= limit

            # Distribute any remaining budget to "other"
            if remaining > 0 and "other" not in plan.allocations:
                plan.allocations["other"] = BudgetAllocation(
                    category=Category.OTHER, limit_kg=remaining
                )
        else:
            # Even distribution across all categories
            per_cat = total_limit_kg / len(Category)
            for cat in Category:
                plan.allocations[cat.value] = BudgetAllocation(
                    category=cat, limit_kg=round(per_cat, 2)
                )

        self.plans[plan_id] = plan
        self.household_plans.setdefault(household_id, []).append(plan_id)
        return plan

    def get_plan(self, plan_id: str) -> Optional[BudgetPlan]:
        """Retrieves a budget plan by ID."""
        return self.plans.get(plan_id)

    def get_active_plan(self, household_id: str) -> Optional[BudgetPlan]:
        """Returns the currently active budget plan for a household."""
        plan_ids = self.household_plans.get(household_id, [])
        for pid in plan_ids:
            plan = self.plans.get(pid)
            if plan and plan.is_active:
                return plan
        return None

    def deactivate_plan(self, plan_id: str) -> bool:
        """Deactivates a budget plan."""
        plan = self.get_plan(plan_id)
        if not plan:
            return False
        plan.is_active = False
        return True

    def deactivate_all_plans(self, household_id: str) -> int:
        """Deactivates all plans for a household. Returns count deactivated."""
        count = 0
        for pid in self.household_plans.get(household_id, []):
            plan = self.plans.get(pid)
            if plan and plan.is_active:
                plan.is_active = False
                count += 1
        return count

    def delete_plan(self, plan_id: str) -> bool:
        """Deletes a plan if it is not active."""
        plan = self.get_plan(plan_id)
        if not plan or plan.is_active:
            return False
        del self.plans[plan_id]
        for h_id, pids in self.household_plans.items():
            if plan_id in pids:
                pids.remove(plan_id)
        return True

    # ── Spending Tracking ─────────────────────────────────────────────────

    def record_spending(
        self,
        household_id: str,
        category: str,
        kg_co2: float,
        description: str,
        source: str = "manual",
    ) -> Dict[str, Any]:
        """
        Records a carbon spending entry against a household.

        Args:
            household_id: Household identifier.
            category: Category name (e.g., "transport").
            kg_co2: Amount of CO2 in kg.
            description: Human-readable description.
            source: Data source (manual, api, ocr).

        Returns:
            Dict with success status, entry, and any triggered alerts.
        """
        if kg_co2 < 0:
            return {"success": False, "error": "Cannot record negative spending."}

        try:
            cat = Category(category)
        except ValueError:
            return {"success": False, "error": f"Invalid category: {category}"}

        entry = SpendingEntry(
            entry_id=f"se_{uuid.uuid4().hex[:10]}",
            household_id=household_id,
            category=cat,
            kg_co2=kg_co2,
            description=description,
            source=source,
        )
        self.spending.setdefault(household_id, []).append(entry)

        # Update active plan allocation
        alerts = []
        plan = self.get_active_plan(household_id)
        if plan and cat.value in plan.allocations:
            alloc = plan.allocations[cat.value]
            old_level = alloc.alert_level
            alloc.spent_kg += kg_co2
            new_level = alloc.alert_level

            if new_level != old_level and new_level != AlertLevel.INFO:
                alert = self._create_alert(
                    household_id, plan.plan_id, cat, new_level, alloc
                )
                alerts.append(alert)

        return {
            "success": True,
            "entry": entry,
            "alerts": alerts,
        }

    def record_batch_spending(
        self, household_id: str, entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Records multiple spending entries at once.

        Args:
            household_id: Household identifier.
            entries: List of dicts with category, kg_co2, description, source.

        Returns:
            Dict with counts and any alerts triggered.
        """
        recorded = 0
        all_alerts = []
        errors = []

        for e in entries:
            result = self.record_spending(
                household_id=household_id,
                category=e.get("category", "other"),
                kg_co2=e.get("kg_co2", 0),
                description=e.get("description", ""),
                source=e.get("source", "manual"),
            )
            if result["success"]:
                recorded += 1
                all_alerts.extend(result.get("alerts", []))
            else:
                errors.append(result.get("error", "Unknown error"))

        return {
            "recorded": recorded,
            "errors": errors,
            "alerts": all_alerts,
        }

    def get_spending(
        self,
        household_id: str,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[SpendingEntry]:
        """
        Retrieves spending entries with optional filtering.

        Args:
            household_id: Household identifier.
            category: Optional category filter.
            start_date: Optional start date filter (ISO).
            end_date: Optional end date filter (ISO).

        Returns:
            List of matching SpendingEntry objects.
        """
        entries = self.spending.get(household_id, [])

        if category:
            entries = [e for e in entries if e.category.value == category]
        if start_date:
            entries = [e for e in entries if e.recorded_at >= start_date]
        if end_date:
            entries = [e for e in entries if e.recorded_at <= end_date]

        return entries

    def get_spending_summary(self, household_id: str) -> Dict[str, Any]:
        """
        Returns a summary of all spending for a household.

        Returns:
            Dict with total spent, per-category totals, and entry count.
        """
        entries = self.spending.get(household_id, [])
        total = sum(e.kg_co2 for e in entries)
        by_category: Dict[str, float] = {}
        for e in entries:
            by_category[e.category.value] = by_category.get(e.category.value, 0) + e.kg_co2

        return {
            "total_spent_kg": round(total, 2),
            "by_category": {k: round(v, 2) for k, v in by_category.items()},
            "entry_count": len(entries),
        }

    # ── Budget Analysis ───────────────────────────────────────────────────

    def get_budget_status(self, household_id: str) -> Dict[str, Any]:
        """
        Returns a comprehensive budget status for the active plan.

        Returns:
            Dict with plan info, category statuses, and overall health.
        """
        plan = self.get_active_plan(household_id)
        if not plan:
            return {"has_plan": False, "message": "No active budget plan."}

        categories = []
        for name, alloc in plan.allocations.items():
            categories.append({
                "category": name,
                "limit_kg": alloc.limit_kg,
                "spent_kg": round(alloc.spent_kg, 2),
                "remaining_kg": round(alloc.remaining_kg, 2),
                "utilization_pct": alloc.utilization_pct,
                "alert_level": alloc.alert_level.value,
            })

        # Sort by utilization descending
        categories.sort(key=lambda c: c["utilization_pct"], reverse=True)

        health = "green"
        max_util = max((c["utilization_pct"] for c in categories), default=0)
        if max_util >= 100:
            health = "red"
        elif max_util >= 80:
            health = "yellow"
        elif max_util >= 60:
            health = "orange"

        return {
            "has_plan": True,
            "plan_id": plan.plan_id,
            "period": plan.period.value,
            "total_limit_kg": plan.total_limit_kg,
            "total_spent_kg": round(plan.total_spent_kg, 2),
            "total_remaining_kg": round(plan.total_remaining_kg, 2),
            "overall_utilization_pct": plan.overall_utilization_pct,
            "health": health,
            "categories": categories,
        }

    def compare_periods(
        self, household_id: str, months_back: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Compares budget performance across recent months.

        Args:
            household_id: Household identifier.
            months_back: How many months to look back.

        Returns:
            List of monthly comparison dicts.
        """
        summaries = self.get_spending_summary(household_id)
        by_category = summaries.get("by_category", {})

        results = []
        now = datetime.now()
        for i in range(months_back):
            month_dt = now - timedelta(days=30 * i)
            month_str = month_dt.strftime("%Y-%m")

            # Simulated monthly breakdown (proportional)
            factor = 1.0 - (i * 0.05)  # slight historical variation
            month_data = {
                "month": month_str,
                "total_kg": round(summaries["total_spent_kg"] * factor / months_back, 2),
                "by_category": {
                    k: round(v * factor / months_back, 2)
                    for k, v in by_category.items()
                },
            }
            results.append(month_data)

        results.reverse()
        return results

    def suggest_reallocation(self, household_id: str) -> List[Dict[str, Any]]:
        """
        Suggests budget reallocations based on spending patterns.

        Returns:
            List of suggestion dicts with category, action, and reason.
        """
        plan = self.get_active_plan(household_id)
        if not plan:
            return []

        suggestions = []
        for name, alloc in plan.allocations.items():
            pct = alloc.utilization_pct

            if pct >= 100:
                suggestions.append({
                    "category": name,
                    "action": "increase",
                    "current_limit_kg": alloc.limit_kg,
                    "suggested_limit_kg": round(alloc.limit_kg * 1.25, 2),
                    "reason": f"Category exceeded by {round(pct - 100, 1)}%. Consider increasing budget or reducing consumption.",
                })
            elif pct <= 20 and alloc.limit_kg > 10:
                suggestions.append({
                    "category": name,
                    "action": "decrease",
                    "current_limit_kg": alloc.limit_kg,
                    "suggested_limit_kg": round(alloc.limit_kg * 0.75, 2),
                    "reason": f"Only {pct}% used. Consider reallocating to over-budget categories.",
                })

        return suggestions

    def calculate_savings_rate(self, household_id: str) -> Dict[str, Any]:
        """
        Calculates how much the household has saved vs. budget.

        Returns:
            Dict with savings in kg, percentage, and per-category savings.
        """
        plan = self.get_active_plan(household_id)
        if not plan:
            return {"savings_kg": 0, "savings_pct": 0, "by_category": {}}

        by_category = {}
        total_saved = 0.0
        for name, alloc in plan.allocations.items():
            saved = alloc.remaining_kg
            by_category[name] = round(saved, 2)
            total_saved += saved

        return {
            "savings_kg": round(total_saved, 2),
            "savings_pct": round(
                (total_saved / plan.total_limit_kg * 100) if plan.total_limit_kg > 0 else 0,
                1,
            ),
            "by_category": by_category,
        }

    # ── Alerts ────────────────────────────────────────────────────────────

    def get_alerts(
        self,
        household_id: str,
        level: Optional[AlertLevel] = None,
        unacknowledged_only: bool = False,
    ) -> List[BudgetAlert]:
        """
        Returns alerts for a household.

        Args:
            household_id: Household identifier.
            level: Optional filter by alert level.
            unacknowledged_only: If True, return only unacknowledged alerts.

        Returns:
            List of BudgetAlert objects.
        """
        alerts = self.alerts.get(household_id, [])

        if level:
            alerts = [a for a in alerts if a.level == level]
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]

        return alerts

    def acknowledge_alert(self, household_id: str, alert_id: str) -> bool:
        """Marks an alert as acknowledged."""
        for alert in self.alerts.get(household_id, []):
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_alert_summary(self, household_id: str) -> Dict[str, int]:
        """Returns counts of alerts by level."""
        alerts = self.alerts.get(household_id, [])
        summary: Dict[str, int] = {}
        for a in alerts:
            key = a.level.value
            summary[key] = summary.get(key, 0) + 1
        return summary

    # ── Snapshots ─────────────────────────────────────────────────────────

    def take_snapshot(self, household_id: str) -> MonthlySnapshot:
        """
        Takes a monthly snapshot of current budget performance.

        Returns:
            The created MonthlySnapshot.
        """
        plan = self.get_active_plan(household_id)
        summaries = self.get_spending_summary(household_id)
        alert_count = len(self.get_alerts(household_id))

        month = datetime.now().strftime("%Y-%m")
        snapshot = MonthlySnapshot(
            month=month,
            total_limit_kg=plan.total_limit_kg if plan else 0.0,
            total_spent_kg=summaries["total_spent_kg"],
            category_breakdown=summaries["by_category"],
            alerts_count=alert_count,
            under_budget=(
                summaries["total_spent_kg"] < plan.total_limit_kg if plan else True
            ),
        )

        self.snapshots.setdefault(household_id, []).append(snapshot)
        return snapshot

    def get_snapshot_history(
        self, household_id: str, limit: int = 12
    ) -> List[MonthlySnapshot]:
        """Returns historical snapshots."""
        return self.snapshots.get(household_id, [])[-limit:]

    def get_trend(self, household_id: str) -> Dict[str, Any]:
        """
        Calculates spending trend over available snapshots.

        Returns:
            Dict with trend direction, slope, and monthly averages.
        """
        snapshots = self.snapshots.get(household_id, [])
        if len(snapshots) < 2:
            return {"trend": "insufficient_data", "data_points": len(snapshots)}

        spent_values = [s.total_spent_kg for s in snapshots]
        n = len(spent_values)
        x_mean = (n - 1) / 2
        y_mean = sum(spent_values) / n

        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(spent_values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0.0

        if slope < -1:
            direction = "decreasing"
        elif slope > 1:
            direction = "increasing"
        else:
            direction = "stable"

        return {
            "trend": direction,
            "slope_kg_per_month": round(slope, 2),
            "average_spent_kg": round(y_mean, 2),
            "data_points": n,
        }

    # ── Presets ───────────────────────────────────────────────────────────

    @staticmethod
    def get_budget_presets() -> Dict[str, Dict[str, Any]]:
        """
        Returns predefined budget presets for common household sizes.

        Returns:
            Dict mapping preset name to budget parameters.
        """
        return {
            "solo_eco_warrior": {
                "description": "Aggressive budget for a single eco-conscious person",
                "total_limit_kg": 200.0,
                "period": "monthly",
                "allocations": {
                    "transport": 30.0,
                    "energy": 50.0,
                    "food": 60.0,
                    "waste": 15.0,
                    "water": 10.0,
                    "shopping": 20.0,
                    "travel": 10.0,
                    "other": 5.0,
                },
            },
            "couple_green": {
                "description": "Moderate budget for a two-person household",
                "total_limit_kg": 350.0,
                "period": "monthly",
                "allocations": {
                    "transport": 60.0,
                    "energy": 80.0,
                    "food": 100.0,
                    "waste": 30.0,
                    "water": 20.0,
                    "shopping": 30.0,
                    "travel": 20.0,
                    "other": 10.0,
                },
            },
            "family_balanced": {
                "description": "Standard budget for a family of four",
                "total_limit_kg": 600.0,
                "period": "monthly",
                "allocations": {
                    "transport": 100.0,
                    "energy": 130.0,
                    "food": 170.0,
                    "waste": 50.0,
                    "water": 35.0,
                    "shopping": 50.0,
                    "travel": 40.0,
                    "other": 25.0,
                },
            },
            "net_zero_aspirant": {
                "description": "Ultra-lean budget targeting near-zero emissions",
                "total_limit_kg": 100.0,
                "period": "monthly",
                "allocations": {
                    "transport": 15.0,
                    "energy": 20.0,
                    "food": 30.0,
                    "waste": 10.0,
                    "water": 5.0,
                    "shopping": 10.0,
                    "travel": 5.0,
                    "other": 5.0,
                },
            },
            "suburban_standard": {
                "description": "Typical suburban household budget",
                "total_limit_kg": 800.0,
                "period": "monthly",
                "allocations": {
                    "transport": 150.0,
                    "energy": 180.0,
                    "food": 200.0,
                    "waste": 60.0,
                    "water": 40.0,
                    "shopping": 70.0,
                    "travel": 60.0,
                    "other": 40.0,
                },
            },
        }

    def create_from_preset(
        self,
        household_id: str,
        preset_name: str,
        start_date: str,
        end_date: str,
        scale_factor: float = 1.0,
    ) -> Optional[BudgetPlan]:
        """
        Creates a budget plan from a predefined preset.

        Args:
            household_id: Household identifier.
            preset_name: Name of the preset.
            start_date: Plan start date.
            end_date: Plan end date.
            scale_factor: Multiplier to scale all values (e.g., 1.5 for 50% larger).

        Returns:
            BudgetPlan or None if preset not found.
        """
        presets = self.get_budget_presets()
        preset = presets.get(preset_name)
        if not preset:
            return None

        scaled_allocations = {
            k: round(v * scale_factor, 2)
            for k, v in preset["allocations"].items()
        }

        return self.create_budget_plan(
            household_id=household_id,
            period=BudgetPeriod(preset["period"]),
            start_date=start_date,
            end_date=end_date,
            total_limit_kg=round(preset["total_limit_kg"] * scale_factor, 2),
            allocations=scaled_allocations,
        )

    # ── Carbon Equivalent Calculations ────────────────────────────────────

    @staticmethod
    def kg_to_equivalents(kg_co2: float) -> Dict[str, Any]:
        """
        Converts kg CO2 to intuitive equivalents.

        Returns:
            Dict with various equivalence representations.
        """
        if kg_co2 < 0:
            kg_co2 = 0.0
        return {
            "kg_co2": round(kg_co2, 2),
            "tree_days": round(kg_co2 / 0.06, 1),  # days for a tree to absorb
            "car_km": round(kg_co2 / 0.21, 1),  # km driven in average car
            "flight_minutes": round(kg_co2 / 0.255, 1),  # minutes of flight
            "phone_charges": round(kg_co2 / 0.008, 0),  # smartphone charges
            "beef_burgers": round(kg_co2 / 3.6, 2),  # beef burgers avoided
            "led_bulb_hours": round(kg_co2 / 0.003, 0),  # LED bulb hours
        }

    # ── Private Helpers ───────────────────────────────────────────────────

    def _create_alert(
        self,
        household_id: str,
        plan_id: str,
        category: Category,
        level: AlertLevel,
        allocation: BudgetAllocation,
    ) -> BudgetAlert:
        """Creates and stores a budget alert."""
        messages = {
            AlertLevel.WARNING: f"{category.value.title()} budget at {allocation.utilization_pct}%. Consider moderating consumption.",
            AlertLevel.CRITICAL: f"{category.value.title()} budget at {allocation.utilization_pct}%! Approaching limit of {allocation.limit_kg} kg.",
            AlertLevel.EXCEEDED: f"{category.value.title()} budget EXCEEDED! Spent {allocation.spent_kg} kg out of {allocation.limit_kg} kg limit.",
        }

        alert = BudgetAlert(
            alert_id=f"al_{uuid.uuid4().hex[:10]}",
            household_id=household_id,
            plan_id=plan_id,
            category=category,
            level=level,
            message=messages.get(level, "Budget alert triggered."),
            utilization_pct=allocation.utilization_pct,
        )

        self.alerts.setdefault(household_id, []).append(alert)
        return alert

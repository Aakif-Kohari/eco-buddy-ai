"""
Supply Chain Transparency Scorer.
Maps and scores supply chain stages for transparency and risk.
"""

from typing import Dict, Any, List


class SupplyChainTransparency:
    """Evaluates the transparency and sustainability risk of a product's supply chain."""

    STAGES = ["raw_materials", "manufacturing", "distribution", "end_of_life"]

    def __init__(self):
        pass

    def evaluate_stage(
        self, stage: str, data_provided: bool, certification: str = "none"
    ) -> Dict[str, Any]:
        """Evaluates a single supply chain stage."""
        score = 0
        risks = []

        if data_provided:
            score += 50  # Base points for providing data

        if certification.lower() in ["fairtrade", "fsc", "iso14001", "cradle2cradle"]:
            score += 40  # Bonus for recognized certification
        elif certification.lower() != "none":
            score += 20  # Minor bonus for other certifications

        if not data_provided:
            risks.append("No data disclosed for this stage")
        if certification.lower() == "none" and data_provided:
            risks.append("Lacks third-party certification")

        # Specific stage risks
        if stage == "raw_materials" and not data_provided:
            risks.append("High risk of untraceable raw material sourcing")
        if stage == "end_of_life" and not data_provided:
            risks.append("No end-of-life recycling or disposal plan disclosed")

        return {
            "stage": stage,
            "score": min(100, score),
            "certification": certification,
            "risks": risks,
        }

    def calculate_overall_score(
        self, stage_evaluations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculates the overall supply chain transparency score."""
        total_score = sum(stage["score"] for stage in stage_evaluations)
        max_score = len(self.STAGES) * 100
        overall_percentage = round((total_score / max_score) * 100, 1)

        all_risks = []
        for stage in stage_evaluations:
            all_risks.extend(stage["risks"])

        return {
            "overall_score_pct": overall_percentage,
            "grade": "High"
            if overall_percentage >= 80
            else "Medium"
            if overall_percentage >= 50
            else "Low",
            "stage_details": stage_evaluations,
            "identified_risks": all_risks,
        }

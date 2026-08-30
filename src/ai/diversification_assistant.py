"""
src/ai/diversification_assistant.py
-----------------------------------
AI Personalized Practice Diversification Assistant for interview preparation.
"""

from __future__ import annotations

from typing import Any


class PracticeDiversificationAssistant:
    """Analyzes practice history to detect repetitive patterns and recommend balanced, diverse questions."""

    def generate_diversified_recommendations(
        self, practice_history: list[dict[str, Any]], available_question_bank: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate personalized recommendations that balance difficulty, topics, companies, and technologies."""
        if not available_question_bank:
            return {"status": "error", "message": "Question bank is empty."}

        # 1. Track previously practiced questions and detect topic bias
        practiced_topics = {q.get("topic") for q in practice_history}
        practiced_difficulties = {q.get("difficulty") for q in practice_history}
        practiced_companies = {q.get("company") for q in practice_history}

        # 2. Identify neglected topics, difficulties, companies, and technologies
        recommendations = []
        for question in available_question_bank:
            topic = question.get("topic")
            difficulty = question.get("difficulty")
            company = question.get("company")

            # Score diversity: prioritize items that fill gaps in practice history
            diversity_score = 0
            if topic not in practiced_topics:
                diversity_score += 3
            if difficulty not in practiced_difficulties:
                diversity_score += 2
            if company not in practiced_companies:
                diversity_score += 2

            if diversity_score > 0:
                recommendations.append({"question": question, "diversity_score": diversity_score})

        # Sort recommendations by diversity score descending
        recommendations.sort(key=lambda x: x["diversity_score"], reverse=True)

        return {
            "status": "success",
            "detected_biases": {
                "overpracticed_topics": list(practiced_topics),
                "overpracticed_difficulties": list(practiced_difficulties),
            },
            "recommended_questions": [r["question"] for r in recommendations[:5]],
        }

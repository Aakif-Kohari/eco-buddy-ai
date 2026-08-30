"""
src/dashboard/similarity_heatmap.py
-----------------------------------
Similarity Heatmap Dashboard and practice area analytics for interview tracking.
"""

from __future__ import annotations

from typing import Any
import numpy as np


class SimilarityHeatmapDashboard:
    """Computes similarity matrices, topic clusters, and duplicate percentages for interview practice."""

    def generate_dashboard_metrics(self, practice_history: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate comprehensive analytics for the similarity heatmap dashboard."""
        if not practice_history:
            return {
                "duplicate_percentage": 0.0,
                "most_repeated_concepts": [],
                "least_practiced_topics": [],
                "topic_clusters": {},
                "heatmap_matrix": [],
            }

        # 1. Calculate duplicate percentage
        duplicate_percentage = self._compute_duplicate_percentage(practice_history)

        # 2. Identify most repeated concepts and least practiced topics
        concept_counts = self._aggregate_concepts(practice_history)
        most_repeated = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        least_practiced = sorted(concept_counts.items(), key=lambda x: x[1])[:5]

        # 3. Compute topic clusters and similarity heatmap matrix
        heatmap_matrix, clusters = self._compute_similarity_and_clusters(practice_history)

        return {
            "duplicate_percentage": duplicate_percentage,
            "most_repeated_concepts": [c[0] for c in most_repeated],
            "least_practiced_topics": [c[0] for c in least_practiced],
            "topic_clusters": clusters,
            "heatmap_matrix": heatmap_matrix,
        }

    def _compute_duplicate_percentage(self, history: list[dict[str, Any]]) -> float:
        """Calculate the overall repetition ratio of practiced questions."""
        total = len(history)
        if total == 0:
            return 0.0
        unique_questions = len(set(q.get("question_text", "") for q in history))
        duplicates = total - unique_questions
        return round((duplicates / total) * 100.0, 2)

    def _aggregate_concepts(self, history: list[dict[str, Any]]) -> dict[str, int]:
        """Count frequency of concepts across practice sessions."""
        counts: dict[str, int] = {}
        for item in history:
            topic = item.get("topic", "General")
            counts[topic] = counts.get(topic, 0) + 1
        return counts

    def _compute_similarity_and_clusters(self, history: list[dict[str, Any]]) -> tuple[list[list[float]], dict[str, list[str]]]:
        """Compute mock similarity matrix and group questions into topic clusters."""
        n = len(history)
        # Generate a sample similarity matrix representing question-to-question cosine similarity
        matrix = np.eye(n).tolist()
        
        clusters: dict[str, list[str]] = {}
        for item in history:
            topic = item.get("topic", "General")
            clusters.setdefault(topic, []).append(item.get("question_text", ""))

        return matrix, clusters

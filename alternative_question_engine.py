from sentence_transformers import SentenceTransformer, util


class AlternativeQuestionEngine:
    """Generate semantically similar interview questions."""

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def recommend(
        self,
        question,
        question_bank,
        top_k=5,
        min_similarity=0.45,
    ):
        """Return the most semantically similar questions."""

        if not question or not question.strip():
            return []

        if not question_bank:
            return []

        query = question.strip()

        candidates = []

        for item in question_bank:
            candidate = item.get("question", "").strip()

            if not candidate:
                continue

            if candidate.lower() == query.lower():
                continue

            candidates.append(item)

        if not candidates:
            return []

        candidate_questions = [
            item["question"]
            for item in candidates
        ]

        query_embedding = self.model.encode(
            query,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )

        candidate_embeddings = self.model.encode(
            candidate_questions,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )

        similarity_scores = util.cos_sim(
            query_embedding,
            candidate_embeddings,
        )[0]

        recommendations = []

        for item, score in zip(
            candidates,
            similarity_scores,
        ):
            similarity = float(score)

            if similarity >= min_similarity:
                recommendations.append(
                    {
                        "question": item["question"],
                        "concept": item.get("concept", "General"),
                        "similarity": similarity,
                    }
                )

        recommendations.sort(
            key=lambda item: item["similarity"],
            reverse=True,
        )

        return recommendations[:top_k]
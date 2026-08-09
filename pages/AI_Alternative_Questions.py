import streamlit as st


# Lazy import - only load when user interacts
def get_engine():
    from alternative_question_engine import AlternativeQuestionEngine
    return AlternativeQuestionEngine()


st.set_page_config(
    page_title="AI Alternative Question Recommendations",
    page_icon="🤖",
    layout="wide",
)


QUESTION_BANK = [
    {
        "question": "What is Python?",
        "concept": "Python Basics",
    },
    {
        "question": "Why is Python popular?",
        "concept": "Python Basics",
    },
    {
        "question": "What are the main features of Python?",
        "concept": "Python Basics",
    },
    {
        "question": "What is a variable in Python?",
        "concept": "Python Basics",
    },
    {
        "question": "What are Python data types?",
        "concept": "Python Data Types",
    },
    {
        "question": "What is a list in Python?",
        "concept": "Python Data Structures",
    },
    {
        "question": "What is a tuple in Python?",
        "concept": "Python Data Structures",
    },
    {
        "question": "What is a dictionary in Python?",
        "concept": "Python Data Structures",
    },
    {
        "question": "What is inheritance in Python?",
        "concept": "Python OOP",
    },
    {
        "question": "Explain method overriding in Python.",
        "concept": "Python OOP",
    },
    {
        "question": "What is polymorphism in Python?",
        "concept": "Python OOP",
    },
    {
        "question": "What are Python functions?",
        "concept": "Python Functions",
    },
    {
        "question": "What is exception handling in Python?",
        "concept": "Python Exception Handling",
    },
    {
        "question": "How do you handle exceptions in Python?",
        "concept": "Python Exception Handling",
    },
]


st.title("🤖 AI Alternative Question Recommendation Engine")

st.write(
    "Enter an interview question to generate alternative "
    "questions covering the same concept."
)


question = st.text_area(
    "Enter your interview question",
    height=150,
    placeholder=(
        "Example:\n"
        "What is inheritance in Python?"
    ),
)


if st.button(
    "🔍 Generate Alternatives",
    type="primary",
):

    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()

    with st.spinner(
        "🤖 Loading AI model and generating alternatives..."
    ):

        engine = get_engine()

        recommendations = engine.recommend(
            question=question,
            question_bank=QUESTION_BANK,
            top_k=5,
            min_similarity=0.30,
        )

    st.subheader("💡 Alternative Questions")

    if not recommendations:

        st.info(
            "No sufficiently similar alternative questions "
            "were found."
        )

    else:

        for index, recommendation in enumerate(
            recommendations,
            start=1,
        ):

            similarity = recommendation["similarity"] * 100

            st.markdown(
                f"### {index}. "
                f"{recommendation['question']}"
            )

            st.write(
                f"**Concept:** "
                f"{recommendation['concept']}"
            )

            st.caption(
                f"Semantic similarity: "
                f"{similarity:.1f}%"
            )

            st.divider()

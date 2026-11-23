from src.faq_suggestion_service import FaqEntry, SuggestionRequest, suggest


def test_related_answer_wins_for_typed_api_query() -> None:
    entries = (
        FaqEntry("How do I authenticate?", "Use a bearer token.", ("api", "authenticate")),
        FaqEntry("How do I show related answers?", "Rank matching FAQ entries.", ("related", "answers", "api")),
    )

    result = suggest(SuggestionRequest("api related answers", entries, limit=1))

    assert result[0].question == "How do I show related answers?"
    assert result[0].answer == "Rank matching FAQ entries."

from apis.registry import default_registry
from retriever.retriever import APIRetriever


def test_retriever_ranks_relevant_api_first():
    registry = default_registry()
    retriever = APIRetriever(registry.all())

    top = retriever.retrieve("What is 45 divided by 9?", top_k=1)

    assert top[0].api.name == "calculator"


def test_retriever_returns_requested_number_of_results():
    registry = default_registry()
    retriever = APIRetriever(registry.all())

    results = retriever.retrieve("weather forecast", top_k=2)

    assert len(results) == 2

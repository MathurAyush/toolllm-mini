import pytest

from apis.registry import default_registry, keyless_registry
from retriever.keyword_baseline import KeywordMatchRetriever
from retriever.retriever import APIRetriever
from retriever.text import stem, tokenize


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


def test_keyword_baseline_ranks_relevant_api_first():
    registry = default_registry()
    retriever = KeywordMatchRetriever(registry.all())

    top = retriever.retrieve("What is the weather like right now?", top_k=1)

    assert top[0].api.name == "weather"


def test_keyword_baseline_scores_no_overlap_as_zero():
    registry = default_registry()
    retriever = KeywordMatchRetriever(registry.all())

    results = retriever.retrieve("zzz qqq nonsense", top_k=3)

    assert all(result.score == 0.0 for result in results)


def test_stem_matches_simple_inflections():
    assert stem("converts") == stem("convert")
    assert stem("currencies") == "currency"
    assert stem("rates") == stem("rate")
    assert stem("us") == "us"
    assert stem("status") == "status"
    assert stem("divided") == stem("divide")


def test_tokenize_drops_stop_words():
    assert tokenize("What is the weather in the US?") == ["weather", "us"]


@pytest.mark.parametrize("retriever_cls", ["tfidf", "keyword"])
@pytest.mark.parametrize(
    "instruction, expected",
    [
        ("Convert 100 US dollars to Euros.", "currency_exchange"),
        ("What is 23 times 17?", "calculator"),
        ("What is 45 divided by 9?", "calculator"),
    ],
)
def test_word_retrievers_handle_unstemmed_queries(retriever_cls, instruction, expected):
    apis = keyless_registry().all()
    retriever = APIRetriever(apis) if retriever_cls == "tfidf" else KeywordMatchRetriever(apis)

    top = retriever.retrieve(instruction, top_k=1)

    assert top[0].api.name == expected
    assert top[0].score > 0.0


def test_semantic_retriever_ranks_relevant_api_first():
    pytest.importorskip("sentence_transformers")
    from retriever.semantic_embedder import SentenceTransformerEmbedder

    registry = default_registry()
    retriever = APIRetriever(registry.all(), embedder=SentenceTransformerEmbedder())

    top = retriever.retrieve("Can you tell me today's temperature outside?", top_k=1)

    assert top[0].api.name == "weather"

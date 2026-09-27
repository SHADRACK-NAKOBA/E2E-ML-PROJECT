from rag.pipeline import ABSTENTION_MESSAGE, answer_question


class FakeSearchClient:
    def __init__(self, results):
        self.results = results
        self.last_search_kwargs = None

    def search(self, **kwargs):
        self.last_search_kwargs = kwargs
        return self.results


def fake_embed(texts):
    return [[0.1, 0.2, 0.3] for _ in texts]


def test_weak_reranker_evidence_abstains_without_generation():
    """
    Azure hybrid/RRF scores are ranking signals, not calibrated confidence.

    Even when Azure Search returns a candidate, a weak normalized reranker
    score must prevent generation.
    """
    search_client = FakeSearchClient(
        [
            {
                "id": "chunk-1",
                "text": "Weakly related repair information.",
                "source": "repair_manual",
                "source_doc_id": "DOC-001",
                "@search.score": 0.20,
            }
        ]
    )

    generation_called = False

    def fake_rerank(query, texts):
        return [0.20]

    def fake_generate(question, chunks):
        nonlocal generation_called
        generation_called = True
        return "This must never be generated."

    response = answer_question(
        question="How should this component be repaired?",
        search_client=search_client,
        embed_fn=fake_embed,
        rerank_fn=fake_rerank,
        generate_fn=fake_generate,
        allowed_sensitivity=["internal", "dealer_visible"],
    )

    assert response.abstained is True
    assert response.answer == ABSTENTION_MESSAGE
    assert response.grounding.should_abstain is True
    assert response.grounding.max_retrieval_score == 0.20
    assert generation_called is False


def test_low_rrf_but_strong_reranker_evidence_generates():
    """
    A low Azure hybrid/RRF score must not be compared directly with the
    normalized grounding threshold.

    This mirrors the live Azure Search behavior where the correct document
    can have an RRF score around 0.03.
    """
    search_client = FakeSearchClient(
        [
            {
                "id": "chunk-1",
                "text": "Touring rear axle nut torque is 95 ft-lb (129 Nm).",
                "source": "repair_manual",
                "source_doc_id": "repair_manual_touring_rear_axle",
                "@search.score": 0.033333335,
            }
        ]
    )

    def fake_rerank(query, texts):
        return [0.94]

    def fake_generate(question, chunks):
        assert len(chunks) == 1
        assert chunks[0].score == 0.94
        assert chunks[0].search_score == 0.033333335
        return "The rear axle nut torque is 95 ft-lb (129 Nm)."

    response = answer_question(
        question="What's the torque spec for the rear axle nut on a Touring model?",
        search_client=search_client,
        embed_fn=fake_embed,
        rerank_fn=fake_rerank,
        generate_fn=fake_generate,
        allowed_sensitivity=["dealer_visible"],
    )

    assert response.abstained is False
    assert response.grounding.should_abstain is False
    assert response.grounding.max_retrieval_score == 0.94
    assert response.sources == ["repair_manual_touring_rear_axle"]


def test_strong_evidence_generates_answer_and_preserves_sources():
    search_client = FakeSearchClient(
        [
            {
                "id": "chunk-1",
                "text": "Approved repair procedure.",
                "source": "service_bulletin",
                "source_doc_id": "SB-100",
                "@search.score": 0.82,
            },
            {
                "id": "chunk-2",
                "text": "Additional approved procedure.",
                "source": "repair_manual",
                "source_doc_id": "RM-200",
                "@search.score": 0.76,
            },
        ]
    )

    def fake_rerank(query, texts):
        return [0.95, 0.90]

    def fake_generate(question, chunks):
        assert len(chunks) == 2
        assert chunks[0].score == 0.95
        assert chunks[0].search_score == 0.82
        assert chunks[1].score == 0.90
        assert chunks[1].search_score == 0.76
        return "Use the approved repair procedure."

    response = answer_question(
        question="What is the approved repair procedure?",
        search_client=search_client,
        embed_fn=fake_embed,
        rerank_fn=fake_rerank,
        generate_fn=fake_generate,
        allowed_sensitivity=["internal", "dealer_visible"],
    )

    assert response.abstained is False
    assert response.answer == "Use the approved repair procedure."
    assert response.grounding.should_abstain is False
    assert response.sources == ["SB-100", "RM-200"]


def test_sensitivity_filter_is_applied_at_search_boundary():
    search_client = FakeSearchClient([])

    def fake_rerank(query, texts):
        return []

    def fake_generate(question, chunks):
        raise AssertionError("Generation must not run with no evidence")

    answer_question(
        question="Show me the repair policy.",
        search_client=search_client,
        embed_fn=fake_embed,
        rerank_fn=fake_rerank,
        generate_fn=fake_generate,
        allowed_sensitivity=["dealer_visible"],
    )

    search_filter = search_client.last_search_kwargs["filter"]

    assert search_filter == "sensitivity eq 'dealer_visible'"

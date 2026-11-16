from app.qa.llm import LLMResponse, ReplyOutcome
from tests.qa_harness import supplied_texts
from tests.test_google_maps_ingestion import request_collection
from tests.test_google_maps_ingestion import source as source
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_review_dataset_integration import ask, review_rows, summary
from tests.test_target_workflow import database as database


def test_google_maps_ratings_are_persisted_and_included_in_summary(
    client, database, source_targets, source
):
    headers, target = source_targets[0]
    source.collect.return_value = [
        {"review_text": "Helpful staff", "rating": 5},
        {"review_text": "", "rating": 4},
        {"review_text": None, "rating": 3},
        {"rating": 2},
        {"review_text": "", "rating": 9},
    ]
    result = request_collection(client, headers, target).json()
    assert (result["state"], result["persisted_count"], result["rejected_count"]) == (
        "partial",
        4,
        1,
    )
    assert sorted(
        (r["rating"], r["review_text"]) for r in review_rows(client, headers, target)
    ) == [
        (2, ""),
        (3, ""),
        (4, ""),
        (5, "Helpful staff"),
    ]
    assert summary(client, headers, target) == {
        "target_id": target,
        "review_count": 4,
        "average_rating": 3.5,
    }


def test_rating_only_dataset_supplies_ratings_without_fabricated_written_evidence(
    client, database, source_targets, source, fake_llm
):
    headers, target = source_targets[0]
    source.collect.return_value = [
        {"review_text": "", "rating": 5},
        {"review_text": None, "rating": 1},
    ]
    result = request_collection(client, headers, target).json()
    assert result["state"] == "succeeded"
    assert result["persisted_count"] == 2 and result["rejected_count"] == 0
    fake_llm.respond_with(
        LLMResponse(
            ReplyOutcome.INSUFFICIENT_EVIDENCE,
            "These ratings have no written comments.",
        )
    )
    response = ask(client, headers, target, "What do reviewers complain about?")
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    request = fake_llm.last_request
    assert sorted(r.rating for r in request.reviews) == [1, 5]
    assert supplied_texts(request) == {""}
    assert "never infer reasons or written themes" in request.system_prompt
    assert summary(client, headers, target)["average_rating"] == 3.0

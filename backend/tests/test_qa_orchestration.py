"""Q&A orchestration tests at the model boundary, using the fake LLM (S2-003)."""

from uuid import UUID, uuid4

import pytest

from app.main import create_app
from app.models.analysis_target import AnalysisTarget, ReviewPlatform
from app.qa.llm import LLMRequest, LLMUnavailableError, UnconfiguredLLMClient
from app.qa.prompt import build_system_prompt
from tests.conftest import USER_A_ID
from tests.qa_harness import (
    assert_not_in_context,
    supplied_review_ids,
    supplied_target_ids,
    supplied_texts,
)
from tests.test_review_dataset_integration import (
    BATTERY_CSV,
    SERVICE_CSV,
    ask,
    create_target,
    ingest,
    review_rows,
)
from tests.test_review_dataset_integration import as_user as as_user  # Fixture.
from tests.test_target_workflow import USER_B_ID
from tests.test_target_workflow import database as database  # Shared DB fixture.

BATTERY_TEXTS = {
    "Battery life lasts two days, amazing",
    "Battery life is solid for travel",
    "Battery life dropped after a month",
}
SERVICE_TEXTS = {
    "Customer service never called back",
    "Customer service was polite but slow",
}


@pytest.fixture
def phone_store(client, as_user):
    owner = as_user()
    target_id = create_target(client, owner, "Phone store")
    ingest(client, owner, target_id, BATTERY_CSV)
    return owner, target_id


def test_system_instructions_identify_the_active_target_and_platform(
    client, fake_llm, phone_store
):
    owner, target_id = phone_store

    assert ask(client, owner, target_id).status_code == 200

    prompt = fake_llm.last_request.system_prompt
    assert '"Phone store"' in prompt
    assert "Google Maps" in prompt
    assert prompt == build_system_prompt(
        AnalysisTarget(name="Phone store", platform=ReviewPlatform.GOOGLE_MAPS)
    )


def test_question_and_all_target_reviews_are_supplied(client, fake_llm, phone_store):
    owner, target_id = phone_store
    stored = review_rows(client, owner, target_id)

    ask(client, owner, target_id, "  Is the battery reliable?  ")

    request = fake_llm.last_request
    assert len(fake_llm.requests) == 1
    assert request.question == "Is the battery reliable?"
    assert supplied_texts(request) == BATTERY_TEXTS
    assert supplied_review_ids(request) == {UUID(row["id"]) for row in stored}
    assert supplied_target_ids(request) == {UUID(target_id)}
    assert sorted(review.rating for review in request.reviews) == [2, 4, 5]


def test_each_question_uses_only_the_selected_targets_reviews(
    client, fake_llm, as_user
):
    owner = as_user()
    battery = create_target(client, owner, "Phone store")
    service = create_target(client, owner, "Call center")
    ingest(client, owner, battery, BATTERY_CSV)
    ingest(client, owner, service, SERVICE_CSV)

    for target_id, expected in (
        (battery, BATTERY_TEXTS),
        (service, SERVICE_TEXTS),
        (battery, BATTERY_TEXTS),
    ):
        assert ask(client, owner, target_id).status_code == 200
        assert supplied_texts(fake_llm.last_request) == expected
        assert supplied_target_ids(fake_llm.last_request) == {UUID(target_id)}

    after_switch = fake_llm.requests[1]
    assert '"Call center"' in after_switch.system_prompt
    assert_not_in_context(after_switch, "Battery", "Phone store")


def test_another_users_reviews_never_reach_the_model(client, fake_llm, as_user):
    user_a, user_b = as_user(USER_A_ID), as_user(USER_B_ID)
    private = create_target(client, user_a, "Phone store")
    ingest(client, user_a, private, "rating,review_text\n5,Purple elephant charger")
    own = create_target(client, user_b, "Call center")
    ingest(client, user_b, own, SERVICE_CSV)

    probe = "What do reviews say about the purple elephant charger?"
    response = ask(client, user_b, own, probe)

    assert response.status_code == 200
    assert len(fake_llm.requests) == 1
    assert fake_llm.last_request.question == probe
    assert supplied_texts(fake_llm.last_request) == SERVICE_TEXTS
    assert_not_in_context(fake_llm.last_request, "purple elephant", "Phone store")


def test_asking_about_another_users_target_never_calls_the_model(
    client, fake_llm, phone_store, as_user
):
    _, private = phone_store

    denied = ask(client, as_user(USER_B_ID), private)
    missing = ask(client, as_user(USER_B_ID), str(uuid4()))

    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json() == {"detail": "Analysis target not found."}
    assert fake_llm.requests == []


def test_controlled_model_answer_is_returned_to_the_user(client, fake_llm, phone_store):
    owner, target_id = phone_store
    fake_llm.respond_with("Reviewers mostly praise the battery life.")

    response = ask(client, owner, target_id)

    assert response.status_code == 200
    assert response.json() == {
        "target_id": target_id,
        "status": "answered",
        "answer": "Reviewers mostly praise the battery life.",
        "review_count": 3,
    }


def test_model_failure_returns_a_safe_error(client, fake_llm, phone_store, caplog):
    owner, target_id = phone_store
    fake_llm.respond_with(LLMUnavailableError("provider timeout: secret-key-123"))

    response = ask(client, owner, target_id, "Is the battery reliable?")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "ReviewLens could not answer right now. Try again shortly."
    }
    assert "secret-key-123" not in caplog.text
    assert "Is the battery reliable?" not in caplog.text
    assert "Battery life" not in caplog.text


def test_target_without_reviews_does_not_call_the_model(client, fake_llm, as_user):
    owner = as_user()
    empty = create_target(client, owner, "Empty store")

    response = ask(client, owner, empty)

    assert response.status_code == 200
    assert response.json() == {
        "target_id": empty,
        "status": "no_reviews",
        "answer": None,
        "review_count": 0,
    }
    assert fake_llm.requests == []


@pytest.mark.parametrize(
    "body",
    [
        {"question": "   "},
        {"question": "x" * 1001},
        {},
        {"question": "Hi", "target_id": str(uuid4())},
        {"question": "Hi", "user_id": USER_B_ID},
        {"question": "Hi", "reviews": ["Injected review"]},
    ],
)
def test_invalid_question_requests_are_rejected_before_the_model(
    client, fake_llm, phone_store, body
):
    owner, target_id = phone_store

    response = client.post(
        f"/api/targets/{target_id}/questions", headers=owner, json=body
    )

    assert response.status_code == 422
    assert fake_llm.requests == []


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_questions_require_authentication(client, fake_llm, phone_store, token):
    _, target_id = phone_store
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    assert ask(client, headers, target_id).status_code == 401
    assert fake_llm.requests == []


def test_app_without_a_configured_provider_refuses_to_answer(settings, token_verifier):
    app = create_app(settings, token_verifier=token_verifier)

    assert isinstance(app.state.llm_client, UnconfiguredLLMClient)
    with pytest.raises(LLMUnavailableError):
        app.state.llm_client.complete(
            LLMRequest(system_prompt="", question="", reviews=())
        )

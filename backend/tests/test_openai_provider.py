import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from openai import APIError, OpenAI
from pydantic import SecretStr

from app.qa import openai_provider
from app.qa.llm import (
    LLMRequest,
    LLMUnavailableError,
    ReplyOutcome,
    ReviewContext,
)


class FakeResponses:
    def __init__(self, output_text: str | None = None, error: Exception | None = None):
        self.output_text = output_text
        self.error = error
        self.arguments = None

    def create(self, **kwargs):
        self.arguments = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output_text=self.output_text)


class FakeOpenAI:
    def __init__(self, responses: FakeResponses, **kwargs):
        self.responses = SimpleNamespace(create=responses.create)
        self.kwargs = kwargs


def make_request() -> LLMRequest:
    target_id = uuid4()
    return LLMRequest(
        system_prompt="Use only the supplied reviews.",
        question="What do customers like?",
        reviews=(
            ReviewContext(uuid4(), target_id, 5, "The staff were friendly."),
            ReviewContext(uuid4(), target_id, 2, "The wait was too long."),
        ),
    )


def test_openai_adapter_sends_question_and_reviews_as_json_and_parses_reply(
    monkeypatch: pytest.MonkeyPatch,
):
    responses = FakeResponses(
        '{"outcome":"answered","answer":"Reviewers praise the friendly staff."}'
    )
    client_options = {}

    def make_client(**kwargs):
        client_options.update(kwargs)
        return FakeOpenAI(responses, **kwargs)

    monkeypatch.setattr(
        openai_provider,
        "OpenAI",
        make_client,
    )

    answer = openai_provider.OpenAIReviewLLM("test-key").complete(make_request())

    assert client_options == {
        "api_key": "test-key",
        "max_retries": 0,
        "timeout": openai_provider.TIMEOUT_SECONDS,
    }
    sent = responses.arguments
    assert sent["model"] == openai_provider.MODEL
    assert sent["instructions"] == "Use only the supplied reviews."
    assert sent["max_output_tokens"] == openai_provider.MAX_OUTPUT_TOKENS
    assert sent["reasoning"] == {"effort": "low"}
    assert sent["text"] == {"format": {"type": "json_object"}}
    assert sent["store"] is False
    assert json.loads(sent["input"].split("\n", 1)[1]) == {
        "question": "What do customers like?",
        "reviews": [
            {"rating": 5, "text": "The staff were friendly."},
            {"rating": 2, "text": "The wait was too long."},
        ],
    }
    assert answer.outcome is ReplyOutcome.ANSWERED
    assert answer.text == "Reviewers praise the friendly staff."


def test_adapter_request_is_accepted_by_the_openai_sdk(
    monkeypatch: pytest.MonkeyPatch,
):
    request_body = {}
    answer_text = '{"outcome":"answered","answer":"Reviewers praise the staff."}'

    def handle(request: httpx.Request) -> httpx.Response:
        request_body.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "created_at": 1,
                "model": openai_provider.MODEL,
                "object": "response",
                "output": [
                    {
                        "id": "msg_test",
                        "content": [
                            {
                                "annotations": [],
                                "text": answer_text,
                                "type": "output_text",
                            }
                        ],
                        "role": "assistant",
                        "status": "completed",
                        "type": "message",
                    }
                ],
                "parallel_tool_calls": True,
                "tool_choice": "auto",
                "tools": [],
                "status": "completed",
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handle))
    with OpenAI(api_key="test-key", http_client=http_client) as sdk_client:
        monkeypatch.setattr(openai_provider, "OpenAI", lambda **kwargs: sdk_client)
        answer = openai_provider.OpenAIReviewLLM("test-key").complete(make_request())

    assert request_body["model"] == openai_provider.MODEL
    assert request_body["store"] is False
    assert request_body["text"] == {"format": {"type": "json_object"}}
    assert request_body["reasoning"] == {"effort": "low"}
    assert answer.text == "Reviewers praise the staff."


def test_provider_failure_becomes_safe_unavailable_error(
    monkeypatch: pytest.MonkeyPatch,
):
    error = APIError(
        "sensitive provider details",
        request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
        body=None,
    )
    responses = FakeResponses(error=error)
    monkeypatch.setattr(
        openai_provider,
        "OpenAI",
        lambda **kwargs: FakeOpenAI(responses, **kwargs),
    )

    with pytest.raises(LLMUnavailableError) as exc_info:
        openai_provider.OpenAIReviewLLM("test-key").complete(make_request())

    assert str(exc_info.value) == "OpenAI request failed."
    assert "sensitive provider details" not in str(exc_info.value)


def test_invalid_or_empty_provider_reply_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
):
    responses = FakeResponses("not a JSON answer")
    monkeypatch.setattr(
        openai_provider,
        "OpenAI",
        lambda **kwargs: FakeOpenAI(responses, **kwargs),
    )

    with pytest.raises(LLMUnavailableError):
        openai_provider.OpenAIReviewLLM("test-key").complete(make_request())


def test_missing_provider_text_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
):
    responses = FakeResponses(None)
    monkeypatch.setattr(
        openai_provider,
        "OpenAI",
        lambda **kwargs: FakeOpenAI(responses, **kwargs),
    )

    with pytest.raises(LLMUnavailableError, match="OpenAI returned no text"):
        openai_provider.OpenAIReviewLLM("test-key").complete(make_request())


def test_input_over_budget_is_rejected_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
):
    responses = FakeResponses('{"outcome":"answered","answer":"Should not run."}')
    monkeypatch.setattr(
        openai_provider,
        "OpenAI",
        lambda **kwargs: FakeOpenAI(responses, **kwargs),
    )
    request = make_request()
    request = LLMRequest(
        system_prompt="x" * openai_provider.MAX_INPUT_TOKEN_BUDGET,
        question=request.question,
        reviews=request.reviews,
    )

    with pytest.raises(LLMUnavailableError, match="exceeds the OpenAI input budget"):
        openai_provider.OpenAIReviewLLM("test-key").complete(request)

    assert responses.arguments is None


def test_manual_evaluation_factory_requires_a_configured_key(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        openai_provider, "get_settings", lambda: SimpleNamespace(openai_api_key=None)
    )

    with pytest.raises(RuntimeError, match="Set OPENAI_API_KEY"):
        openai_provider.create_client()


def test_manual_evaluation_factory_uses_the_configured_key(
    monkeypatch: pytest.MonkeyPatch,
):
    responses = FakeResponses()
    monkeypatch.setattr(
        openai_provider,
        "get_settings",
        lambda: SimpleNamespace(openai_api_key=SecretStr("test-key")),
    )
    monkeypatch.setattr(
        openai_provider,
        "OpenAI",
        lambda **kwargs: FakeOpenAI(responses, **kwargs),
    )

    assert isinstance(openai_provider.create_client(), openai_provider.OpenAIReviewLLM)

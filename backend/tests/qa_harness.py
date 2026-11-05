"""Deterministic stand-in for the LLM provider used by Q&A tests (S2-003).

Tests assert on what crossed the model boundary (system prompt, question, and
structured review context) instead of on generated wording, and script the
model's replies, including failures. No provider, API key, or network is used.
"""

from uuid import UUID

from app.qa.llm import LLMRequest, LLMResponse

DEFAULT_ANSWER = "Scripted answer from the fake model."


class FakeLLMClient:
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []
        self._scripted: list[str | Exception] = []

    def respond_with(self, *outcomes: str | Exception) -> None:
        """Queue replies in order; an exception instance is raised instead."""
        self._scripted.extend(outcomes)

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        outcome = self._scripted.pop(0) if self._scripted else DEFAULT_ANSWER
        if isinstance(outcome, Exception):
            raise outcome
        return LLMResponse(text=outcome)

    @property
    def last_request(self) -> LLMRequest:
        assert self.requests, "The model was never called."
        return self.requests[-1]


def supplied_texts(request: LLMRequest) -> set[str]:
    return {review.text for review in request.reviews}


def supplied_review_ids(request: LLMRequest) -> set[UUID]:
    return {review.review_id for review in request.reviews}


def supplied_target_ids(request: LLMRequest) -> set[UUID]:
    return {review.target_id for review in request.reviews}


def assert_not_in_context(request: LLMRequest, *fragments: str) -> None:
    """Fail if a fragment appears in the system prompt or supplied reviews.

    The user's own question is excluded because attack tests deliberately ask
    about the fragment.
    """
    sent = [request.system_prompt, *supplied_texts(request)]
    for fragment in fragments:
        leaked = [part for part in sent if fragment.lower() in part.lower()]
        assert not leaked, f"{fragment!r} crossed the model boundary: {leaked}"

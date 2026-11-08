from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ReviewContext:
    review_id: UUID
    target_id: UUID
    rating: int
    text: str


@dataclass(frozen=True)
class LLMRequest:
    """Everything sent across the model boundary for one question.

    Reviews stay structured so tests can check exactly which records were
    supplied; provider adapters decide how to render them into a prompt.
    """

    system_prompt: str
    question: str
    reviews: tuple[ReviewContext, ...]


class ReplyOutcome(str, Enum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass(frozen=True)
class LLMResponse:
    outcome: ReplyOutcome
    text: str


class LLMUnavailableError(Exception):
    """The model could not produce an answer (not configured, timeout, outage)."""


class LLMClient(Protocol):
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return the model's answer or raise LLMUnavailableError.

        Adapters must translate provider errors into LLMUnavailableError and
        must not log the question, reviews, or answer. Each call is independent:
        never reuse provider conversation/history or previous-response IDs.
        Send only this request, preserving reviews as untrusted data separate
        from system instructions. Check the actual provider token budget,
        reserving output capacity, and fail rather than silently truncating.
        """
        ...


class UnconfiguredLLMClient:
    def complete(self, request: LLMRequest) -> LLMResponse:
        raise LLMUnavailableError("No LLM provider is configured.")

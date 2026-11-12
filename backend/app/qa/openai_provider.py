"""Stateless Responses API adapter for review-grounded Q&A.

Defaults to OpenAI; ``LLM_BASE_URL`` and ``LLM_MODEL`` point it at another
Responses-compatible provider such as xAI.
"""

import json

from openai import APIError, OpenAI

from app.config import Settings, get_settings
from app.qa.llm import LLMRequest, LLMResponse, LLMUnavailableError
from app.qa.reply import parse_model_reply

MODEL = "gpt-5.6-terra"
MAX_INPUT_TOKEN_BUDGET = 800_000
INPUT_TOKEN_OVERHEAD_RESERVE = 10_000
MAX_OUTPUT_TOKENS = 2048
TIMEOUT_SECONDS = 30


class OpenAIReviewLLM:
    def __init__(
        self, api_key: str, *, base_url: str | None = None, model: str = MODEL
    ) -> None:
        self._model = model
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=0,
            timeout=TIMEOUT_SECONDS,
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        evidence = "Question and review evidence as JSON data:\n" + json.dumps(
            {
                "question": request.question,
                "reviews": [
                    {"rating": review.rating, "text": review.text}
                    for review in request.reviews
                ],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        input_bytes = len(request.system_prompt.encode("utf-8")) + len(
            evidence.encode("utf-8")
        )
        if input_bytes + INPUT_TOKEN_OVERHEAD_RESERVE > MAX_INPUT_TOKEN_BUDGET:
            raise LLMUnavailableError("Request exceeds the OpenAI input budget.")

        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=request.system_prompt,
                input=evidence,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                reasoning={"effort": "low"},
                text={"format": {"type": "json_object"}},
                store=False,
            )
        except APIError:
            raise LLMUnavailableError("OpenAI request failed.") from None

        if not isinstance(response.output_text, str):
            raise LLMUnavailableError("OpenAI returned no text.")
        return parse_model_reply(response.output_text)


def configured_client(settings: Settings) -> OpenAIReviewLLM:
    if settings.openai_api_key is None:
        raise RuntimeError("Set OPENAI_API_KEY to run the live Q&A evaluation.")
    return OpenAIReviewLLM(
        settings.openai_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        model=settings.llm_model or MODEL,
    )


def create_client() -> OpenAIReviewLLM:
    """Create the configured client for the manual model evaluation command."""
    return configured_client(get_settings())

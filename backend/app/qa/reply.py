import json

from app.qa.llm import LLMResponse, LLMUnavailableError, ReplyOutcome


def parse_model_reply(raw: str) -> LLMResponse:
    """Parse the JSON reply format defined in the system prompt.

    Provider adapters call this on the model's raw text. A reply that breaks the
    contract is treated as a failed model call rather than shown to the user.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
        outcome = ReplyOutcome(data["outcome"])
        answer = data["answer"].strip()
    except (ValueError, KeyError, TypeError, AttributeError):
        raise LLMUnavailableError("Model reply did not follow the format.") from None
    if not answer:
        raise LLMUnavailableError("Model reply had an empty answer.")
    return LLMResponse(outcome=outcome, text=answer)

import pytest

from app.qa.llm import LLMUnavailableError, ReplyOutcome
from app.qa.reply import parse_model_reply


@pytest.mark.parametrize(
    "raw",
    [
        '{"outcome": "out_of_scope", "answer": "  Only these reviews.  "}',
        '```json\n{"outcome": "out_of_scope", "answer": "Only these reviews."}\n```',
    ],
)
def test_reply_in_the_prompt_format_is_parsed(raw):
    reply = parse_model_reply(raw)

    assert reply.outcome is ReplyOutcome.OUT_OF_SCOPE
    assert reply.text == "Only these reviews."


@pytest.mark.parametrize(
    "raw",
    [
        "Customers love the pancakes.",
        '{"outcome": "maybe", "answer": "Unsure."}',
        '{"answer": "No outcome."}',
        '{"outcome": "answered"}',
        '{"outcome": "answered", "answer": "   "}',
        '{"outcome": "answered", "answer": 5}',
        '["answered", "A list, not an object."]',
    ],
)
def test_reply_that_breaks_the_format_is_a_failed_model_call(raw):
    with pytest.raises(LLMUnavailableError):
        parse_model_reply(raw)

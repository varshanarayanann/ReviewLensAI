# Deterministic Q&A test harness (S2-003)

ReviewLens Q&A is tested at the **model boundary**: tests check what the
application sends to the LLM and how it handles controlled replies, without
calling a real model. CI needs no API key and costs nothing to run.

Rules: S2-BR-009 through S2-BR-014, S2-BR-022, S2-BR-027 through S2-BR-031.

## Architecture

| Piece | Location | Role |
| --- | --- | --- |
| Model boundary | `backend/app/qa/llm.py` | `LLMClient` protocol: `complete(LLMRequest) -> LLMResponse(outcome, text)`, raising `LLMUnavailableError` on failure. |
| Reply parsing | `backend/app/qa/reply.py` | `parse_model_reply(raw)` reads the JSON reply format defined in the system prompt (S2-004). |
| Request contract | `LLMRequest` | `system_prompt`, `question`, and `reviews`: a tuple of `ReviewContext(review_id, target_id, rating, text)`. |
| System prompt | `backend/app/qa/prompt.py` | `build_system_prompt(target)`; names the target and platform and states the scope rules. |
| Orchestration | `backend/app/qa/service.py` | `answer_question(...)` loads the owner's target and its persisted reviews, then calls the client. |
| Endpoint | `POST /api/targets/{target_id}/questions` | `backend/app/api/questions.py` |
| Injection | `create_app(..., llm_client=...)` | An explicit client overrides configuration; otherwise `OPENAI_API_KEY` enables `OpenAIReviewLLM`, and no key leaves the safe unconfigured client in place. |
| Fake model | `backend/tests/qa_harness.py` | `FakeLLMClient` records every request and returns scripted replies. |

Reviews cross the boundary as structured records rather than a pre-rendered
string. Tests can therefore assert exactly which review IDs and targets were
supplied; a provider adapter decides how to render them into its prompt format.

## Writing a Q&A test

Every test app built by the `client` fixture uses the `fake_llm` fixture, so no
test can reach a real provider by accident.

```python
def test_example(client, fake_llm, phone_store):
    owner, target_id = phone_store
    fake_llm.respond_with("Reviewers praise the battery.")  # scripted reply

    response = client.post(
        f"/api/targets/{target_id}/questions",
        headers=owner,
        json={"question": "Is the battery reliable?"},
    )

    request = fake_llm.last_request              # what crossed the boundary
    assert supplied_target_ids(request) == {UUID(target_id)}
    assert_not_in_context(request, "text from another target")
    assert response.json()["answer"] == "Reviewers praise the battery."
```

| Harness feature | Use it to verify |
| --- | --- |
| `fake_llm.requests` / `last_request` | The model was (or was not) called, and with what. |
| `request.system_prompt` | Correct system instructions for the active target. |
| `supplied_texts`, `supplied_review_ids`, `supplied_target_ids` | Exactly the right review context was supplied. |
| `assert_not_in_context(request, ...)` | Wrong-target or cross-user text never reached the model. |
| `respond_with("text")` | Application behavior for a controlled `answered` reply. |
| `respond_with(LLMResponse(ReplyOutcome.OUT_OF_SCOPE, "..."))` | Behavior for a decline or an insufficient-evidence reply. |
| `respond_with(LLMUnavailableError(...))` | Behavior when the provider fails. |

Assert on these properties, not on exact generated wording (S2-BR-029, S2-BR-030).
`backend/tests/test_qa_orchestration.py` covers each required case and runs on
SQLite and PostgreSQL.

## Current behavior

For supported questions, the system prompt directs the model to synthesize
across relevant reviews, treat a theme as recurring only when multiple reviews
support it, use ratings when relevant, and reflect conflicting experiences.
It prohibits invented counts and unsupported causal claims. The request keeps
ratings and review text structured so provider adapters can supply both as
evidence.

| Situation | Response | Model called? |
| --- | --- | --- |
| Owned target with reviews | `200 {target_id, status, answer, review_count}`; `status` is the model's outcome: `answered`, `insufficient_evidence`, or `out_of_scope` | Yes |
| Owned target with no reviews | `200 {status: "no_reviews", answer: null, review_count: 0}` | No |
| Missing or another user's target | `404 {"detail": "Analysis target not found."}` | No |
| Blank, too long (over 1,000 characters), or extra fields | `422` | No |
| Missing or invalid login | `401` | No |
| Provider fails or is not configured | `503`, safe message; question and reviews are not logged | Yes |

S2-010 supplies the complete owned dataset within a 1,000-review and 64,000-byte
JSON context budget, otherwise returning safe 422 without a model call. See
[the architecture decision](qa-context-design.md). S2-012 clarifies absent
evidence; S2-016/S2-019 add cross-user and stale-context regressions in
`tests/test_qa_context.py`. S2-020 covers the empty-target experience and S2-009
the UI. Preserve the boundary contract and update orchestration tests when
changing these pieces.

## OpenAI provider

`backend/app/qa/openai_provider.py` implements the provider-neutral `LLMClient`
boundary with OpenAI's Responses API and `gpt-5.6-terra`. The backend activates
it only when the server-side `OPENAI_API_KEY` is configured; otherwise the
existing safe 503 behavior remains. Calls are stateless, disable response
storage, use a 30-second timeout with SDK retries disabled, preserve the
system prompt separately from JSON-serialized question/review evidence, and
require JSON output parsed by `parse_model_reply`. The adapter checks the
serialized prompt and input against a conservative 800,000-token input budget
before calling the API. Its UTF-8 byte count upper-bounds text token count, with
10,000 tokens reserved for API framing.

Set `OPENAI_API_KEY` in `backend/.env` to enable it locally. Do not send real
review data to a provider unless the deployment's data-handling requirements
permit it. Provider failures and malformed replies become
`LLMUnavailableError`; the API logs only the target ID and error class, never
the question, reviews, or answer. The model's reported behavior still requires
live evaluation: mocked provider tests establish request shape and failure
handling, not factual accuracy or prompt-injection immunity.

Live-model checks (for example the S2-004 evaluation set against a real model)
may supplement these tests, but they must run manually outside CI and do not
replace the deterministic tests (S2-BR-031).

# Deterministic Q&A test harness (S2-003)

ReviewLens Q&A is tested at the **model boundary**: tests check what the
application sends to the LLM and how it handles controlled replies, without
calling a real model. CI needs no API key and costs nothing to run.

Rules: S2-BR-009 through S2-BR-014, S2-BR-022, S2-BR-027 through S2-BR-031.

## Architecture

| Piece | Location | Role |
| --- | --- | --- |
| Model boundary | `backend/app/qa/llm.py` | `LLMClient` protocol: `complete(LLMRequest) -> LLMResponse`, raising `LLMUnavailableError` on failure. |
| Request contract | `LLMRequest` | `system_prompt`, `question`, and `reviews`: a tuple of `ReviewContext(review_id, target_id, rating, text)`. |
| System prompt | `backend/app/qa/prompt.py` | `build_system_prompt(target)`; names the target and platform and states the scope rules. |
| Orchestration | `backend/app/qa/service.py` | `answer_question(...)` loads the owner's target and its persisted reviews, then calls the client. |
| Endpoint | `POST /api/targets/{target_id}/questions` | `backend/app/api/questions.py` |
| Injection | `create_app(..., llm_client=...)` | Production defaults to `UnconfiguredLLMClient` until a provider adapter is added. |
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
| `respond_with("text")` | Application behavior for a controlled model answer. |
| `respond_with(LLMUnavailableError(...))` | Behavior when the provider fails. |

Assert on these properties, not on exact generated wording (S2-BR-029, S2-BR-030).
`backend/tests/test_qa_orchestration.py` covers each required case and runs on
SQLite and PostgreSQL.

## Current behavior

| Situation | Response | Model called? |
| --- | --- | --- |
| Owned target with reviews | `200 {target_id, status: "answered", answer, review_count}` | Yes |
| Owned target with no reviews | `200 {status: "no_reviews", answer: null, review_count: 0}` | No |
| Missing or another user's target | `404 {"detail": "Analysis target not found."}` | No |
| Blank, too long (over 1,000 characters), or extra fields | `422` | No |
| Missing or invalid login | `401` | No |
| Provider fails or is not configured | `503`, safe message; question and reviews are not logged | Yes |

The prompt wording and the "send every review of the target" context strategy
are deliberately simple starting points. S2-013 owns the final system prompt,
S2-010 the context strategy and size limits, S2-020 the empty-target experience,
and S2-009 the UI. When changing them, keep the boundary contract and update the
orchestration tests.

## Adding a real provider

A provider adapter is a class with a `complete(request)` method, passed to
`create_app` as `llm_client` in production. It must:

- Keep its API key in `backend/.env` only (add the name to `.env.example`).
- Convert every provider error and timeout into `LLMUnavailableError`.
- Never log the question, review text, or answer.
- Be unit tested with a mocked HTTP transport or SDK, never a live call in CI.

Live-model checks (for example the S2-004 evaluation set against a real model)
may supplement these tests, but they must run manually outside CI and do not
replace the deterministic tests (S2-BR-031).

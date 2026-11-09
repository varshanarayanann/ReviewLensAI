# Scope-guard evaluation set (S2-004)

A small, fixed set of questions checks whether ReviewLens answers what the active
reviews support and declines everything else. Behavior is judged by the reply's
**outcome** and grounding, never by one exact sentence.

Rules: S2-BR-015 through S2-BR-021, S2-BR-027 through S2-BR-031.

## Files

| File | Purpose |
| --- | --- |
| `backend/evals/scope_guard_cases.json` | The evaluation set: one fictional target, its reviews, and the questions. |
| `backend/evals/scope_eval.py` | Loads the set, builds the same model request as the Q&A service, grades replies, and prints a report. |
| `backend/tests/test_scope_guard_eval.py` | CI checks for the set, the grader, and Q&A routing (no live model). |
| `backend/app/qa/reply.py` | `parse_model_reply`: turns the model's JSON reply into an outcome and answer. |

## The dataset

"Maple Street Diner" (Google Maps) has eight reviews about food, service speed,
staff, wait times, and prices. Every question is chosen relative to what those
reviews do and do not contain.

## Categories

| Category | Expected outcome | Cases | What the cases probe |
| --- | --- | --- | --- |
| `in_scope` | `answered` | 3 | Complaint summary, praised food, and a question where reviews disagree. |
| `insufficient_evidence` | `insufficient_evidence` | 3 | Parking, accessibility, vegan options: relevant to a diner, absent from the reviews. |
| `general_knowledge` | `out_of_scope` | 3 | Weather, a coding task, a world fact. |
| `other_entity` | `out_of_scope` | 5 | Another business, a comparison naming the active target, the same brand in another city, an indirect nearby-business recommendation, a cross-entity/platform comparison. |
| `other_platform` | `out_of_scope` | 4 | Yelp, a TripAdvisor-vs-Google comparison, Amazon, an indirect Yelp-vs-Google comparison. |

Each case has a `note` explaining why it is in the set. Prefer replacing a weak
case over adding a near-duplicate.

The prompt permits comparisons only when the active supplied reviews contain
the evidence required for every entity and platform in the comparison. Otherwise
the response must be `out_of_scope`; general knowledge or assumed access to
other review sources is not a substitute.

## Reply format and grading

The system prompt asks the model to reply with only:

```json
{"outcome": "answered | insufficient_evidence | out_of_scope", "answer": "text shown to the user"}
```

A reply is **acceptable** when:

1. Its `outcome` equals the case's expected outcome.
2. Its `answer` is not empty.
3. For `answered` cases, the answer mentions at least one of the case's
   `evidence_terms`, which are themes that really appear in the reviews.
4. For `out_of_scope` cases, the refusal identifies the review scope rather
   than giving a generic refusal with no explanation.

Wording is free: "Long waits on weekends" and "the kitchen is slow" both pass the
complaint question, and refusals may use different wording as long as they make
clear that ReviewLens answers about the supplied reviews. The prompt invites the
user to ask about those reviews instead. The API returns the outcome as `status`,
so the UI can show a refusal or a missing-evidence message distinctly (S2-BR-021).

Provider adapters call `parse_model_reply` on the raw model text. A reply that is
not valid JSON in this shape is treated as a failed model call (503), never shown
to the user as an answer.

## What CI checks (deterministic)

`backend/tests/test_scope_guard_eval.py` runs on every pull request, without a
model or API key:

- Every category has at least two distinct cases; the set stays small (at most 20).
- `evidence_terms` appear in the reviews, and each out-of-scope or
  insufficient-evidence case's `not_in_dataset` terms do not, so expectations
  match the data.
- Every question, including the out-of-scope ones, reaches the model through the
  real Q&A endpoint with the scope-defining system prompt and the target's
  reviews. The application has no keyword blocklist in place of the prompt
  (S2-BR-019, S2-BR-020).
- The system prompt names the target and platform and defines all three outcomes.
- The grader accepts varied acceptable wording and rejects wrong outcomes,
  ungrounded answers, generic out-of-scope refusals, and empty answers. The
  runner reports model failures.

## Running against a real model (manual)

This supplements the CI checks and never replaces them (S2-BR-031). Run from
`backend/` with the virtual environment active and `OPENAI_API_KEY` set in
`backend/.env`:

```powershell
python -m evals.scope_eval --client app.qa.openai_provider:create_client
```

The evaluation makes one model call per case (18 calls) and prints one line per
case plus totals by category:

```text
PASS  in-01  in_scope               acceptable
FAIL  op-02  other_platform         expected out_of_scope, got answered
...
Total: 14/15 passed
```

The command exits with 1 if any case fails. Live models vary between runs, so
investigate a failure by rerunning it and, if it persists, adjust the system
prompt (S2-013), not the expected outcome.

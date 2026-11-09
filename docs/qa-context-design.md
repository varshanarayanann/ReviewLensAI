# Review context implementation plan and decision

Research date: 2026-11-07. Baseline: `df5ffc3` on `main`. GitHub assignment
search found four open issues for nidhisakpal: #55, #57, #61, #64. Assigned
Sprint 1 issues #10, #16, #23 are closed, with implementation and regression
coverage already on main. No open PRs were returned during this inspection.

## Execution order

1. **#55 / S2-010:** extract a bounded complete-dataset context builder; preserve
   persisted IDs, ratings and text; test exact byte and row boundaries.
2. **#57 / S2-012:** clarify absent evidence versus negative evidence, preserve
   the structured insufficient-evidence response, test a controlled parking
   question against food/service reviews.
3. **#61 / S2-016:** verify two-user isolation at the model boundary, including
   forged identity inputs and repeated calls through the same client.
4. **#64 / S2-019:** verify A → B → A, populated → empty, updated/deleted rows,
   and failure recovery; prohibit conversational state reuse in provider adapters.
5. Run backend checks and changed-code coverage; update AGENTS.md and the ticket
   status record; deliver through a PR for human and security review.

## Alternatives and selected approach

| Approach | Assessment for this sprint |
| --- | --- |
| Unbounded full dataset | Simple, but repeated imports grow without bound and can exceed provider limits. |
| First N reviews or text truncation | Cheap, but silently biases frequency questions and can conceal available evidence. |
| Lexical selection | Useful for larger datasets, but misses synonyms and needs explicit partial-context semantics. |
| Embeddings/vector retrieval | Requires provider selection, indexing, deletion/invalidation, ownership filtering and retrieval evaluation; unnecessary for the present small-dataset workflow. |
| Bounded complete dataset | Selected: preserve every persisted review or reject before the model call. No sampling, indexing or cache. |

The initial application budget is **1,000 reviews and 64,000 UTF-8 bytes** of
compact JSON review records, including review ID, target ID, rating, text,
escaping, commas and array brackets. Both limits apply across all imports of a
target. A budget overflow returns safe HTTP 422 and makes no model call. Existing
reviews remain available; nothing is deleted to fit the budget. This is a
conservative application payload limit, not a measured model token limit.

Question length remains limited to 1,000 characters. System instructions,
question, provider message framing and output tokens are additional overhead.
A future provider adapter must count its actual serialized input using its
model's tokenizer and reserve output capacity; it must fail safely when its
window is too small. Do not silently truncate or equate characters/bytes with
tokens. There is no configured production model or paid API call in this work.

## Retrieval and trust boundary

Authorize the parent by verified subject plus target UUID, then load review
columns through a target join with both owner and target predicates. UUID order
makes the context deterministic. Column projection obtains database values rather
than potentially stale ORM entity attributes. Stream rows in small batches and
stop on overflow; limit the SQL query to one more than the row budget. Each
request constructs a fresh immutable tuple. No browser-supplied reviews, session
history, previous answer, shared index, or review-context cache enters it.

[SQLAlchemy's query guide](https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html)
explains identity-map refresh and incremental result fetching. This informed the
column projection and batched iteration; calling `.all()` would defeat streaming.
The API uses request-scoped sessions. Fresh reads reflect committed data visible
under the database transaction's isolation; this is not a guarantee that an
in-flight answer changes when a later import commits.

For S2-018, the workspace URL identifies the active target for both summary
and Q&A. Changing the target remounts the workspace, so the next question uses
the new URL and the previous question and answer are cleared. The workspace
test verifies that routing behavior, and the backend integration test checks
the exact persisted review records supplied to the model across an A → B → A
sequence.

[OWASP's prompt-injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
recommends separating instructions from untrusted content. Review text and target
names are data, never permission to change scope. Adapters must preserve this
separation and use independent, stateless calls (no shared provider conversation
or previous-response ID). Prompt wording cannot replace SQL ownership checks or
prove a model immune to injection.

## Insufficient evidence and validation limits

The model must distinguish unsupported information from a negative observation.
No mention of parking does not establish that parking is safe or unsafe. The
existing `insufficient_evidence` outcome is returned as a normal 200 response with
a useful limitation, while missing reviews bypass the model entirely. Do not
hard-code a parking keyword detector or fabricate evidence verification.

Deterministic tests capture actual requests and script outcomes; they prove
context isolation and response handling, not live-model factual reliability.
The existing scope evaluation includes absent-evidence cases and can be run
manually with a future configured provider. No provider adapter or Q&A UI is
introduced by these four backend tickets; those remain separate team work.

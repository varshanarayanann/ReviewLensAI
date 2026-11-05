"""Deterministic checks for the scope-guard evaluation set (S2-004).

These run in CI without a model. The live run is `python -m evals.scope_eval`.
"""

import csv
import io
from collections import Counter

import pytest

from app.models.analysis_target import AnalysisTarget
from app.qa.llm import LLMRequest, LLMResponse, LLMUnavailableError, ReplyOutcome
from app.qa.prompt import build_system_prompt
from evals.scope_eval import (
    CATEGORY_OUTCOMES,
    EvalCase,
    grade,
    load_evaluation_set,
    main,
    report,
    run,
)
from tests.qa_harness import FakeLLMClient, supplied_texts
from tests.test_review_dataset_integration import as_user as as_user  # Fixture.
from tests.test_review_dataset_integration import ask, create_target, ingest
from tests.test_target_workflow import database as database  # Shared DB fixture.

EVAL = load_evaluation_set()
CASES_BY_QUESTION = {case.question: case for case in EVAL.cases}


def acceptable_reply(case: EvalCase) -> LLMResponse:
    if case.evidence_terms:
        return LLMResponse(
            case.expected_outcome, f"Reviewers mention {case.evidence_terms[0]}."
        )
    return LLMResponse(case.expected_outcome, "ReviewLens can only use these reviews.")


class AcceptableModel:
    def complete(self, request: LLMRequest) -> LLMResponse:
        return acceptable_reply(CASES_BY_QUESTION[request.question])


class AlwaysDecliningModel:
    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(ReplyOutcome.OUT_OF_SCOPE, "I can't help with that.")


def acceptable_model() -> AcceptableModel:
    return AcceptableModel()


def always_declining_model() -> AlwaysDecliningModel:
    return AlwaysDecliningModel()


def dataset_text() -> str:
    return " ".join([EVAL.target_name, *(r.text for r in EVAL.reviews)]).lower()


def test_every_required_category_has_multiple_distinct_cases():
    counts = Counter(case.category for case in EVAL.cases)

    assert set(counts) == set(CATEGORY_OUTCOMES)
    assert all(count >= 2 for count in counts.values())
    assert len({case.id for case in EVAL.cases}) == len(EVAL.cases)
    assert len({case.question.lower() for case in EVAL.cases}) == len(EVAL.cases)
    assert len(EVAL.cases) <= 20
    for case in EVAL.cases:
        assert case.expected_outcome == CATEGORY_OUTCOMES[case.category], case.id
        assert case.note.strip(), case.id


@pytest.mark.parametrize("case", EVAL.cases, ids=lambda case: case.id)
def test_expected_outcome_matches_what_the_dataset_contains(case):
    text = dataset_text()
    if case.expected_outcome is ReplyOutcome.ANSWERED:
        assert case.evidence_terms and not case.not_in_dataset
        missing = [term for term in case.evidence_terms if term not in text]
        assert not missing, f"evidence terms not in the reviews: {missing}"
    else:
        assert case.not_in_dataset and not case.evidence_terms
        present = [term for term in case.not_in_dataset if term in text]
        assert not present, f"supposedly absent terms found in the reviews: {present}"


def test_every_question_reaches_the_model_with_the_scope_prompt(
    client, fake_llm, as_user
):
    owner = as_user()
    target_id = create_target(client, owner, EVAL.target_name)
    source = io.StringIO()
    writer = csv.writer(source, lineterminator="\n")
    writer.writerow(["rating", "review_text"])
    writer.writerows((review.rating, review.text) for review in EVAL.reviews)
    ingest(client, owner, target_id, source.getvalue())

    for case in EVAL.cases:
        fake_llm.respond_with(acceptable_reply(case))
        response = ask(client, owner, target_id, case.question)
        assert response.status_code == 200
        assert response.json()["status"] == case.expected_outcome.value

    expected_prompt = build_system_prompt(
        AnalysisTarget(name=EVAL.target_name, platform=EVAL.platform)
    )
    assert [r.question for r in fake_llm.requests] == [c.question for c in EVAL.cases]
    for request in fake_llm.requests:
        assert request.system_prompt == expected_prompt
        assert supplied_texts(request) == {review.text for review in EVAL.reviews}


def test_system_prompt_defines_the_reply_format_the_grader_relies_on():
    prompt = build_system_prompt(
        AnalysisTarget(name=EVAL.target_name, platform=EVAL.platform)
    )

    assert EVAL.target_name in prompt and "Google Maps" in prompt
    assert '"outcome"' in prompt and '"answer"' in prompt
    for outcome in ReplyOutcome:
        assert f'"{outcome.value}"' in prompt


def test_runner_sends_the_same_prompt_as_the_application():
    request = EVAL.request_for(EVAL.cases[0])

    assert request.system_prompt == build_system_prompt(
        AnalysisTarget(name=EVAL.target_name, platform=EVAL.platform)
    )
    assert [review.text for review in request.reviews] == [
        review.text for review in EVAL.reviews
    ]


@pytest.mark.parametrize("case", EVAL.cases, ids=lambda case: case.id)
def test_grader_requires_the_expected_outcome(case):
    assert grade(case, acceptable_reply(case)).passed
    text = acceptable_reply(case).text
    for outcome in ReplyOutcome:
        if outcome != case.expected_outcome:
            assert not grade(case, LLMResponse(outcome, text)).passed


def test_grader_accepts_different_wordings_of_acceptable_behavior():
    complaints = CASES_BY_QUESTION["What do customers complain about most?"]
    weather = CASES_BY_QUESTION["What is the weather in Newark today?"]

    for text in (
        "Long waits on weekends come up most often.",
        "Several reviewers say the kitchen is slow and prices are high.",
    ):
        assert grade(complaints, LLMResponse(ReplyOutcome.ANSWERED, text)).passed
    for text in (
        "Sorry, I can only discuss the reviews of Maple Street Diner.",
        "That is outside what these Google Maps reviews cover.",
    ):
        assert grade(weather, LLMResponse(ReplyOutcome.OUT_OF_SCOPE, text)).passed


def test_grader_rejects_ungrounded_or_empty_answers():
    complaints = CASES_BY_QUESTION["What do customers complain about most?"]

    vague = grade(
        complaints, LLMResponse(ReplyOutcome.ANSWERED, "Customers have mixed feelings.")
    )
    empty = grade(complaints, LLMResponse(ReplyOutcome.ANSWERED, "   "))

    assert not vague.passed and "theme" in vague.reason
    assert not empty.passed


def test_runner_reports_each_case_including_model_failures():
    fake = FakeLLMClient()
    *answered, last = EVAL.cases
    fake.respond_with(
        *(acceptable_reply(case) for case in answered), LLMUnavailableError("timeout")
    )

    results = run(fake, EVAL)

    assert [r.grade.passed for r in results] == [True] * len(answered) + [False]
    text = report(results)
    assert f"FAIL  {last.id}" in text
    assert f"Total: {len(answered)}/{len(EVAL.cases)} passed" in text
    assert len(fake.requests) == len(EVAL.cases)


def test_command_exit_code_reflects_the_evaluation(capsys):
    module = "tests.test_scope_guard_eval"

    assert main(["--client", f"{module}:acceptable_model"]) == 0
    assert "Total: 15/15 passed" in capsys.readouterr().out
    assert main(["--client", f"{module}:always_declining_model"]) == 1
    assert "in_scope               0/3" in capsys.readouterr().out

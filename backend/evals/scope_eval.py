"""Scope-guard evaluation set and grader (S2-004).

Run against a real model (manual only, never in CI), from backend/:

    python -m evals.scope_eval --client <module>:<factory>

The factory must return an LLMClient. The command exits with 1 if any case fails.
"""

import argparse
import importlib
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid5

from app.models.analysis_target import AnalysisTarget, ReviewPlatform
from app.qa.llm import (
    LLMClient,
    LLMRequest,
    LLMResponse,
    LLMUnavailableError,
    ReplyOutcome,
    ReviewContext,
)
from app.qa.prompt import build_system_prompt

CASES_PATH = Path(__file__).with_name("scope_guard_cases.json")
EVAL_TARGET_ID = UUID("00000000-0000-4000-8000-000000000004")
CATEGORY_OUTCOMES = {
    "in_scope": ReplyOutcome.ANSWERED,
    "insufficient_evidence": ReplyOutcome.INSUFFICIENT_EVIDENCE,
    "general_knowledge": ReplyOutcome.OUT_OF_SCOPE,
    "other_entity": ReplyOutcome.OUT_OF_SCOPE,
    "other_platform": ReplyOutcome.OUT_OF_SCOPE,
}


@dataclass(frozen=True)
class EvalReview:
    rating: int
    text: str


@dataclass(frozen=True)
class EvalCase:
    id: str
    category: str
    question: str
    expected_outcome: ReplyOutcome
    evidence_terms: tuple[str, ...]
    not_in_dataset: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class EvaluationSet:
    target_name: str
    platform: ReviewPlatform
    reviews: tuple[EvalReview, ...]
    cases: tuple[EvalCase, ...]

    def request_for(self, case: EvalCase) -> LLMRequest:
        """Build the same request the Q&A service sends for this target."""
        target = AnalysisTarget(
            id=EVAL_TARGET_ID, name=self.target_name, platform=self.platform
        )
        return LLMRequest(
            system_prompt=build_system_prompt(target),
            question=case.question,
            reviews=tuple(
                ReviewContext(
                    review_id=uuid5(EVAL_TARGET_ID, str(index)),
                    target_id=EVAL_TARGET_ID,
                    rating=review.rating,
                    text=review.text,
                )
                for index, review in enumerate(self.reviews)
            ),
        )


@dataclass(frozen=True)
class Grade:
    passed: bool
    reason: str


@dataclass(frozen=True)
class CaseResult:
    case: EvalCase
    grade: Grade


def load_evaluation_set(path: Path = CASES_PATH) -> EvaluationSet:
    data = json.loads(path.read_text(encoding="utf-8"))
    return EvaluationSet(
        target_name=data["target"]["name"],
        platform=ReviewPlatform(data["target"]["platform"]),
        reviews=tuple(EvalReview(**review) for review in data["reviews"]),
        cases=tuple(
            EvalCase(
                id=case["id"],
                category=case["category"],
                question=case["question"],
                expected_outcome=ReplyOutcome(case["expected_outcome"]),
                evidence_terms=tuple(case.get("evidence_terms", ())),
                not_in_dataset=tuple(case.get("not_in_dataset", ())),
                note=case["note"],
            )
            for case in data["cases"]
        ),
    )


def grade(case: EvalCase, response: LLMResponse) -> Grade:
    """Judge behavior, not wording: right outcome, and grounded when answering."""
    if response.outcome != case.expected_outcome:
        return Grade(
            False,
            f"expected {case.expected_outcome.value}, got {response.outcome.value}",
        )
    answer = response.text.lower()
    if not answer.strip():
        return Grade(False, "empty answer")
    if case.evidence_terms and not any(term in answer for term in case.evidence_terms):
        return Grade(False, "answer mentions no theme that appears in the reviews")
    if response.outcome is ReplyOutcome.OUT_OF_SCOPE and not (
        "review" in answer
        and any(
            phrase in answer
            for phrase in ("these", "supplied", "google maps", "reviewlens", "only")
        )
    ):
        return Grade(False, "refusal does not clarify ReviewLens review scope")
    return Grade(True, "acceptable")


def run(client: LLMClient, evaluation_set: EvaluationSet) -> list[CaseResult]:
    results = []
    for case in evaluation_set.cases:
        try:
            response = client.complete(evaluation_set.request_for(case))
        except LLMUnavailableError as exc:
            result = Grade(False, f"model call failed ({type(exc).__name__})")
        else:
            result = grade(case, response)
        results.append(CaseResult(case, result))
    return results


def report(results: Sequence[CaseResult]) -> str:
    lines = [
        f"{'PASS' if r.grade.passed else 'FAIL'}  {r.case.id:<6} "
        f"{r.case.category:<22} {r.grade.reason}"
        for r in results
    ]
    totals = Counter(r.case.category for r in results)
    passed = Counter(r.case.category for r in results if r.grade.passed)
    lines.append("")
    lines.extend(
        f"{category:<22} {passed[category]}/{total}"
        for category, total in totals.items()
    )
    lines.append(f"Total: {sum(passed.values())}/{len(results)} passed")
    return "\n".join(lines)


def load_client(spec: str) -> LLMClient:
    module_name, _, factory_name = spec.partition(":")
    return getattr(importlib.import_module(module_name), factory_name)()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the scope-guard evaluation.")
    parser.add_argument(
        "--client", required=True, help="module:factory returning an LLMClient"
    )
    args = parser.parse_args(argv)
    results = run(load_client(args.client), load_evaluation_set())
    print(report(results))
    return 0 if all(result.grade.passed for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())

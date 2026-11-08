from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.ingestion_result import IngestionResult


def result(**kwargs):
    return IngestionResult(run_id=uuid4(), target_id=uuid4(), **kwargs)


def test_success_reports_persisted_and_rejected_counts():
    run = result(state="succeeded", persisted_count=3, rejected_count=0)
    assert run.message == "Imported 3 reviews; rejected 0 records."


def test_partial_reports_persisted_and_rejected_counts():
    run = result(state="partial", persisted_count=2, rejected_count=1)
    assert run.message == "Imported 2 reviews; rejected 1 record."


def test_fully_rejected_batch_has_safe_message():
    run = result(state="failed", rejected_count=2)
    assert run.persisted_count == 0
    assert run.message == (
        "Imported 0 reviews; rejected 2 records. Check the review text and ratings."
    )


def test_failure_has_safe_message_without_diagnostics():
    run = result(state="failed")
    assert run.persisted_count == 0
    assert run.rejected_count == 0
    assert "Try again" in run.message
    with pytest.raises(ValidationError):
        result(state="failed", error="password=secret")


@pytest.mark.parametrize(
    "state,count,rejected_count",
    [
        ("succeeded", 0, 0),
        ("failed", 2, 0),
        ("processing", 1, 0),
        ("succeeded", -1, 0),
        ("succeeded", 1, 1),
        ("partial", 1, 0),
        ("partial", 0, 1),
        ("failed", 1, 1),
        ("processing", 0, 1),
    ],
)
def test_inconsistent_results_are_rejected(state, count, rejected_count):
    with pytest.raises(ValidationError):
        result(state=state, persisted_count=count, rejected_count=rejected_count)


def test_negative_rejected_count_is_rejected():
    with pytest.raises(ValidationError):
        result(state="failed", rejected_count=-1)


def test_processing_is_distinct_from_success():
    run = result(state="processing")
    assert run.message == "Collecting reviews. Please wait."
    assert run.persisted_count == 0

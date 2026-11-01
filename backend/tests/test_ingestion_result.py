from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.ingestion_result import IngestionResult


def result(**kwargs):
    return IngestionResult(run_id=uuid4(), target_id=uuid4(), **kwargs)


def test_success_reports_persisted_count():
    run = result(state="succeeded", persisted_count=3)
    assert run.message == "Ingested 3 reviews."


def test_failure_has_safe_message_without_diagnostics():
    run = result(state="failed")
    assert run.persisted_count == 0
    assert "Try again" in run.message
    with pytest.raises(ValidationError):
        result(state="failed", error="password=secret")


@pytest.mark.parametrize(
    "state,count",
    [("succeeded", 0), ("failed", 2), ("processing", 1), ("succeeded", -1)],
)
def test_inconsistent_results_are_rejected(state, count):
    with pytest.raises(ValidationError):
        result(state=state, persisted_count=count)


def test_processing_is_distinct_from_success():
    run = result(state="processing")
    assert run.message == "Collecting reviews. Please wait."
    assert run.persisted_count == 0

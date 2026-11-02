from pathlib import Path

import pytest

from app.reviews.csv_source import ReviewSourceError, parse_csv_reviews

FIXTURE = Path(__file__).parent / "fixtures" / "google_maps_export.csv"


def test_saved_export_identifies_records_and_preserves_raw_fields():
    records = parse_csv_reviews(FIXTURE.read_text(encoding="utf-8"))
    assert len(records) == 3
    assert [record["rating"] for record in records] == ["5", "2", "4"]
    assert records[0]["review_text"] == "Fixture café review, with a comma."
    assert records[1]["review_text"] == "Fixture first line.\nFixture second line."
    assert records[2]["review_text"] == 'Fixture says "thank you" — ありがとう.'
    assert [record["source_review_id"] for record in records] == [
        "fixture-review-001",
        "fixture-review-002",
        "fixture-review-003",
    ]
    assert records[0]["reviewer_name"] == "Fixture reviewer A"
    assert records[0]["review_date"] == "2026-10-01"
    assert records[2]["reviewer_name"] == ""


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_bom_header_order_and_line_endings(ending):
    records = parse_csv_reviews(
        "\ufeffreview_text,rating" + ending + '"  Exact input  ",5' + ending
    )
    assert records == [{"review_text": "  Exact input  ", "rating": "5"}]


def test_record_values_are_left_for_normalization():
    assert parse_csv_reviews("rating,review_text\nnot-a-rating,\n4\n") == [
        {"rating": "not-a-rating", "review_text": ""},
        {"rating": "4", "review_text": None},
    ]


@pytest.mark.parametrize(
    "source",
    [
        "",
        "  \n",
        "\ufeff",
        "rating,review_text\n",
        "rating,text\n5,Text",
        "rating,rating,review_text\n5,1,Text",
        "rating,review_text,\n5,Text,X",
        "rating,review_text\n5,Text,extra",
        'rating,review_text\n5,"unclosed',
        None,
    ],
    ids=[
        "empty",
        "whitespace",
        "bom",
        "no-records",
        "missing-header",
        "duplicate-header",
        "blank-header",
        "extra-values",
        "bad-quote",
        "not-text",
    ],
)
def test_unusable_source_has_a_safe_error(source):
    with pytest.raises(ReviewSourceError) as exc:
        parse_csv_reviews(source)
    assert str(exc.value) == "Invalid CSV source"


def test_limits_reject_instead_of_silently_truncating():
    source = "rating,review_text\n5,One\n4,Two\n"
    assert len(parse_csv_reviews(source, max_records=2)) == 2
    with pytest.raises(ReviewSourceError):
        parse_csv_reviews(source, max_records=1)
    source = "rating,review_text\n5,café"
    size = len(source.encode("utf-8"))
    assert parse_csv_reviews(source, max_bytes=size)[0]["review_text"] == "café"
    with pytest.raises(ReviewSourceError):
        parse_csv_reviews(source, max_bytes=size - 1)


@pytest.mark.parametrize(
    "limits",
    [
        {"max_records": 0},
        {"max_records": 1001},
        {"max_bytes": 0},
        {"max_bytes": 1_000_001},
    ],
)
def test_invalid_adapter_limits_are_programming_errors(limits):
    with pytest.raises(ValueError):
        parse_csv_reviews("rating,review_text\n5,Text", **limits)


def test_export_does_not_fabricate_missing_values_or_reuse_previous_data():
    first = parse_csv_reviews("rating,review_text\n5,Submitted content")
    first[0]["review_text"] = "Mutated by caller"
    assert parse_csv_reviews("rating,review_text\n2,Different source") == [
        {"rating": "2", "review_text": "Different source"}
    ]
    with pytest.raises(ReviewSourceError):
        parse_csv_reviews("unusable")


def test_default_record_boundary():
    source = "rating,review_text\n" + "5,Submitted text\n" * 1000
    assert len(parse_csv_reviews(source)) == 1000
    with pytest.raises(ReviewSourceError):
        parse_csv_reviews(source + "5,One too many\n")

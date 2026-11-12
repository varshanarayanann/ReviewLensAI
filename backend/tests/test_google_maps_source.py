import io
import json
from types import SimpleNamespace
from urllib.error import URLError

import pytest
from pydantic import SecretStr

from app.reviews import google_maps
from app.reviews.google_maps import (
    ApifyReviewSource,
    NoRedirects,
    ReviewCollectionError,
    parse_google_maps_reviews,
)
from app.reviews.normalization import normalize_reviews

SOURCE = "https://www.google.com/maps/place/Example"
ITEM = {
    "text": "  Helpful staff  ",
    "stars": 5,
    "reviewId": "review-1",
    "publishedAtDate": "2026-11-01",
    "reviewOrigin": "Google",
}


def test_collect_uses_saved_url_and_fixed_authenticated_endpoint(monkeypatch):
    sent = []

    def open_request(request, timeout):
        sent.append((request, timeout))
        return io.BytesIO(json.dumps([ITEM]).encode())

    monkeypatch.setattr(
        google_maps, "build_opener", lambda *args: SimpleNamespace(open=open_request)
    )
    result = ApifyReviewSource(SecretStr("test-token")).collect(SOURCE)
    request, timeout = sent[0]
    assert request.full_url.startswith(google_maps.ACTOR_URL + "?")
    assert "maxTotalChargeUsd=0.1" in request.full_url
    assert request.get_header("Authorization") == "Bearer test-token"
    assert "test-token" not in request.full_url
    assert timeout == 135
    assert json.loads(request.data) == {
        "startUrls": [{"url": SOURCE}],
        "maxReviews": 20,
        "reviewsSort": "newest",
        "reviewsOrigin": "google",
        "personalData": False,
        "language": "en",
    }
    normalized = normalize_reviews(result)
    assert normalized.reviews[0].review_text == "Helpful staff"
    assert normalized.reviews[0].rating == 5
    assert normalized.reviews[0].source_metadata["source_review_id"] == "review-1"


@pytest.mark.parametrize(
    "raw",
    [b"not JSON", b"{}", b'[{"error":"remote detail"}]', b"[" * 4_000_001],
    ids=["malformed", "wrong-shape", "provider-error", "too-large"],
)
def test_invalid_response_is_safely_rejected(monkeypatch, raw):
    monkeypatch.setattr(
        google_maps,
        "build_opener",
        lambda *args: SimpleNamespace(open=lambda *args, **kwargs: io.BytesIO(raw)),
    )
    with pytest.raises(ReviewCollectionError):
        ApifyReviewSource(SecretStr("test-token")).collect(SOURCE)


def test_network_errors_do_not_expose_credentials_or_provider_details(monkeypatch):
    def fail(*args, **kwargs):
        raise URLError("private test-token and review contents")

    monkeypatch.setattr(
        google_maps, "build_opener", lambda *args: SimpleNamespace(open=fail)
    )
    with pytest.raises(ReviewCollectionError) as error:
        ApifyReviewSource(SecretStr("test-token")).collect(SOURCE)
    assert str(error.value) == "Review source is unavailable."


def test_no_token_or_invalid_saved_url_never_starts_network(monkeypatch):
    def forbidden(*args):
        pytest.fail("Must not contact provider")

    monkeypatch.setattr(google_maps, "build_opener", forbidden)
    source = ApifyReviewSource(None)
    assert not source.configured
    with pytest.raises(ReviewCollectionError):
        source.collect(SOURCE)
    with pytest.raises(ReviewCollectionError):
        ApifyReviewSource(SecretStr("test-token")).collect("http://localhost/private")


def test_parser_preserves_invalid_records_for_counting_and_never_truncates():
    records = parse_google_maps_reviews(
        [
            ITEM,
            {"stars": 4},
            {"text": "Bad rating", "stars": 4.5},
            None,
            {**ITEM, "reviewOrigin": "Tripadvisor"},
        ],
        20,
    )
    normalized = normalize_reviews(records)
    assert len(normalized.reviews) == 1
    assert len(normalized.rejected) == 4
    assert parse_google_maps_reviews([], 20) == []
    with pytest.raises(ReviewCollectionError):
        parse_google_maps_reviews([ITEM, ITEM], 1)


def test_redirects_are_not_followed():
    assert (
        NoRedirects().redirect_request(None, None, 302, "", {}, "https://other") is None
    )

"""Google Maps reviews from the fixed Compass actor on Apify."""

import json
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import SecretStr

from app.schemas.analysis_target import AnalysisTargetCreate

MAX_RESPONSE_BYTES = 4_000_000
ACTOR_URL = (
    "https://api.apify.com/v2/acts/"
    "compass~google-maps-reviews-scraper/run-sync-get-dataset-items"
)


class ReviewCollectionError(Exception):
    """Collection failed; never expose remote diagnostics to clients."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the API token to a redirect destination.
        return None


class ApifyReviewSource:
    def __init__(
        self, token: SecretStr | None, max_reviews: int = 20, max_charge: float = 0.10
    ):
        self.token = token
        self.max_reviews = max_reviews
        self.max_charge = max_charge

    @property
    def configured(self) -> bool:
        return self.token is not None

    def collect(self, source_url: str) -> list[object]:
        if self.token is None:
            raise ReviewCollectionError("Review collection is not configured.")
        # Revalidate stored targets too. The server contacts only Apify's fixed
        # HTTPS endpoint, never a browser-supplied network destination.
        try:
            source_url = AnalysisTargetCreate.validate_source(source_url)
        except ValueError:
            raise ReviewCollectionError("Invalid saved Google Maps URL.") from None
        payload = {
            "startUrls": [{"url": source_url}],
            "maxReviews": self.max_reviews,
            "reviewsSort": "newest",
            "reviewsOrigin": "google",
            "personalData": False,
            "language": "en",
        }
        request = Request(
            f"{ACTOR_URL}?timeout=120&maxTotalChargeUsd={self.max_charge}",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.token.get_secret_value()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with build_opener(NoRedirects()).open(request, timeout=135) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ReviewCollectionError("Review response exceeded the limit.")
            return parse_google_maps_reviews(json.loads(raw), self.max_reviews)
        except (URLError, OSError, ValueError):
            # Remote errors can contain credentials, URLs, and review contents.
            raise ReviewCollectionError("Review source is unavailable.") from None


def parse_google_maps_reviews(payload: object, limit: int) -> list[object]:
    if not isinstance(payload, list) or len(payload) > limit:
        raise ReviewCollectionError("Invalid review response.")
    records: list[object] = []
    for item in payload:
        if not isinstance(item, dict):
            records.append({})
            continue
        if item.get("error"):
            raise ReviewCollectionError("Review source could not process the place.")
        if item.get("reviewOrigin", "Google") != "Google":
            records.append({})
            continue
        records.append(
            {
                "review_text": item.get("text"),
                "rating": item.get("stars"),
                "source_review_id": item.get("reviewId"),
                "review_date": item.get("publishedAtDate"),
            }
        )
    return records

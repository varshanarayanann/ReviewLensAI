from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalysisTargetCreate(BaseModel):
    """Creation contract; ownership is supplied by verified auth, never the body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    source_url: str
    platform: Literal["google_maps"] = "google_maps"

    @field_validator("source_url")
    @classmethod
    def validate_source(cls, value: str) -> str:
        try:
            url = urlsplit(value)
            port = url.port
        except ValueError:
            raise ValueError("Enter a valid Google Maps HTTPS URL.") from None
        if (
            url.scheme != "https"
            or url.username is not None
            or url.password is not None
            or port not in (None, 443)
            or any(char.isspace() or ord(char) < 32 for char in value)
            or "\\" in value
        ):
            raise ValueError("Enter a valid Google Maps HTTPS URL.")
        host = url.hostname
        path = url.path
        allowed = (
            host in {"google.com", "www.google.com", "goo.gl"}
            and path.startswith("/maps/")
            and bool(path[len("/maps/") :])
        ) or (
            host in {"maps.google.com", "maps.app.goo.gl"}
            and bool(path.strip("/") or url.query)
        )
        if not allowed:
            raise ValueError("Enter a Google Maps link to the business.")
        return value

import pytest
from pydantic import ValidationError

from app.schemas.analysis_target import AnalysisTargetCreate

URL = "https://www.google.com/maps/place/Example"


@pytest.mark.parametrize("name", [None, "", "   ", "x" * 121])
def test_invalid_name(name):
    with pytest.raises(ValidationError):
        AnalysisTargetCreate(name=name, source_url=URL)


@pytest.mark.parametrize("missing", ["name", "source_url"])
def test_missing_required_field(missing):
    data = {"name": "Example", "source_url": URL}
    del data[missing]
    with pytest.raises(ValidationError):
        AnalysisTargetCreate(**data)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "http://google.com/maps/place/X",
        "https://google.com.evil.test/maps/place/X",
        "https://evil.test/?url=https://google.com/maps/place/X",
        "https://evil@google.com/maps/place/X",
        "https://google.com/search?q=X",
        "https://google.com/maps/",
        "https://maps.app.goo.gl/",
        "https://google.com:444/maps/place/X",
        "https://[broken",
        "https://google.com/maps/place/a b",
    ],
)
def test_invalid_source(url):
    with pytest.raises(ValidationError):
        AnalysisTargetCreate(name="Example", source_url=url)


@pytest.mark.parametrize(
    "url",
    [
        URL,
        "https://google.com/maps/place/X",
        "https://maps.google.com/?q=X",
        "https://maps.app.goo.gl/abc",
        "https://goo.gl/maps/abc",
    ],
)
def test_valid_source_and_trimmed_name(url):
    target = AnalysisTargetCreate(name=" Example ", source_url=url)
    assert target.name == "Example"
    assert target.source_url == url
    assert target.platform == "google_maps"


def test_owner_cannot_be_supplied():
    with pytest.raises(ValidationError):
        AnalysisTargetCreate(name="Example", source_url=URL, owner_id="other-user")

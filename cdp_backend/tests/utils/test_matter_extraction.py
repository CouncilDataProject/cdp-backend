import sys
from pathlib import Path

import pytest
from textract.exceptions import ExtensionNotSupported, MissingFileError

from cdp_backend.utils import matter_extraction


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="File removal for test cleanup sometimes fails on Windows",
)
@pytest.mark.parametrize(
    "file_uri, expected_size",
    [
        ("fake_creds.json", 382),
        ("code_of_conduct.docx", 3169),
        ("code_of_conduct.pdf", 4105),
        ("code_of_conduct.txt", 3119),
        pytest.param(
            "fake_fake_creds.json",
            100,
            marks=pytest.mark.raises(exception=MissingFileError),
        ),
        pytest.param(
            "example_video.mp4",
            100,
            marks=pytest.mark.raises(exception=ExtensionNotSupported),
        ),
    ],
)
def test_get_matter_text(
    resources_dir: Path,
    file_uri: Path,
    expected_size: int,
) -> None:
    file_uri = resources_dir / file_uri
    text = matter_extraction.get_matter_text(str(file_uri))
    assert len(text) == expected_size

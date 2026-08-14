import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.audit_repository_product_metadata import badge_state

def test_badge_state_empty():
    readme = ""
    result = badge_state(readme)
    assert result["count"] == 0
    assert result["ci"] is False
    assert result["coverage"] is False
    assert result["license"] is False
    assert result["citation"] is False
    assert result["version"] is False

def test_badge_state_count():
    readme = """
    ![CI](https://github.com/user/repo/actions/workflows/main.yml/badge.svg)
    ![Coverage](https://coveralls.io/repos/github/user/repo/badge.svg)
    [![Shield](https://img.shields.io/badge/version-1.0-blue)](https://github.com/user/repo)
    ![Not a badge](https://example.com/image.png)
    """
    result = badge_state(readme)
    assert result["count"] == 3

def test_badge_state_ci():
    readme = "Here is a CI status: github/workflow/status/something"
    result = badge_state(readme)
    assert result["ci"] is True

    readme2 = "Using actions/workflows in my text"
    result2 = badge_state(readme2)
    assert result2["ci"] is True

def test_badge_state_coverage():
    readme = "Testing with codecov for coverage"
    result = badge_state(readme)
    assert result["coverage"] is True

    readme2 = "Testing with coveralls instead"
    result2 = badge_state(readme2)
    assert result2["coverage"] is True

def test_badge_state_license():
    readme = "Here is our license-mit"
    result = badge_state(readme)
    assert result["license"] is True

    readme2 = "Find our terms at /license"
    result2 = badge_state(readme2)
    assert result2["license"] is True

def test_badge_state_citation():
    readme = "See our citation.cff file"
    result = badge_state(readme)
    assert result["citation"] is True

    readme2 = "Available at doi.org/10.1234/something"
    result2 = badge_state(readme2)
    assert result2["citation"] is True

    readme3 = "Archived on zenodo"
    result3 = badge_state(readme3)
    assert result3["citation"] is True

def test_badge_state_version():
    readme = "Current version-2.0"
    result = badge_state(readme)
    assert result["version"] is True

    readme2 = "Find releases at /v/release"
    result2 = badge_state(readme2)
    assert result2["version"] is True

    readme3 = "Tags are at /v/tag"
    result3 = badge_state(readme3)
    assert result3["version"] is True

def test_badge_state_case_insensitivity():
    readme = """
    ![CI](HTTPS://GITHUB.COM/ACTIONS/WORKFLOWS/MAIN.YML/BADGE.SVG)
    Testing with CODECOV.
    See our CITATION.CFF.
    Current VERSION-3.0.
    """
    result = badge_state(readme)
    # The count regex flag re.I makes the badge checking case insensitive too
    assert result["count"] == 1
    assert result["ci"] is True
    assert result["coverage"] is True
    assert result["citation"] is True
    assert result["version"] is True

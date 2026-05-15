import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.scraper import scrape_asin


def test_scraper_smoke():
    result = scrape_asin("B0CWRXMRTG")
    if result is None:
        pytest.skip("amazon.de blocked the smoke request")
    assert result["title"]

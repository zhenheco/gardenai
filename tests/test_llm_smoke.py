import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm import GeminiClient
from core.memory import get_db


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_llm_smoke():
    client = GeminiClient(engine=get_db("demo"))
    try:
        text = client.generate_text("Hallo, antworte auf Deutsch.")
    except Exception as exc:
        if "API key not valid" in str(exc):
            pytest.skip("GEMINI_API_KEY is present but invalid in this shell")
        raise
    assert text.strip()

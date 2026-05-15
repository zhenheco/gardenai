import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import verify_password
from core.llm import GeminiClient
from core.memory import ASIN, ChangeRequest, LLMCall, ListingVersion, Partner
from core.scraper import scrape_asin


def make_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


def test_llm_call_row_created_on_every_gemini_call(monkeypatch):
    class FakeModels:
        def generate_content(self, model: str, contents: str, config=None):
            return SimpleNamespace(text="Guten Tag", usage_metadata=SimpleNamespace(total_token_count=7))

    class FakeGenAI:
        class Client:
            def __init__(self, api_key: str):
                self.models = FakeModels()

    monkeypatch.setitem(sys.modules, "google.genai", FakeGenAI)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL_PRIMARY", "gemini-test")
    engine = make_engine()

    client = GeminiClient(engine=engine)
    assert client.generate_text("Hallo") == "Guten Tag"

    with Session(engine) as session:
        calls = session.exec(select(LLMCall)).all()
        assert len(calls) == 1
        assert calls[0].model == "gemini-test"
        assert calls[0].cache_hit is False


def test_change_request_approve_updates_listing_version_and_audit_log():
    engine = make_engine()
    with Session(engine) as session:
        partner = Partner(slug="demo", name="Demo Garden GmbH")
        session.add(partner)
        session.commit()
        asin = ASIN(partner_id=partner.id, asin="B0TEST1234", title="Old title")
        session.add(asin)
        session.commit()
        current = ListingVersion(
            asin_id=asin.id,
            title="Old title",
            bullets_json=json.dumps(["old"]),
            description="Old description",
            is_current=True,
        )
        session.add(current)
        session.commit()
        request = ChangeRequest(
            asin_id=asin.id,
            change_type="listing_rewrite",
            status="pending",
            summary="Rewrite",
            proposed_json=json.dumps(
                {
                    "title": "New title",
                    "bullets": ["new"],
                    "description": "New description",
                }
            ),
        )
        session.add(request)
        session.commit()

        request.approve(session, actor="tester")
        session.refresh(request)

        versions = session.exec(select(ListingVersion).where(ListingVersion.asin_id == asin.id)).all()
        assert request.status == "approved"
        assert sum(1 for version in versions if version.is_current) == 1
        assert any(version.title == "New title" and version.is_current for version in versions)
        assert "tester approved" in request.audit_log


def test_auth_wrong_password_blocks_access(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "correct-horse")
    assert verify_password("wrong") is False
    assert verify_password("correct-horse") is True


def test_scraper_returns_none_on_403(monkeypatch):
    class FakeResponse:
        status_code = 403
        text = "Forbidden"

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("core.scraper.httpx.get", fake_get)
    assert scrape_asin("B0BLOCKED") is None

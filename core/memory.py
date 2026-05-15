from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy.engine import Engine


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "partners"
_ENGINES: dict[str, Engine] = {}


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Partner(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str
    marketplace: str = "DE"
    created_at: datetime = Field(default_factory=now_utc)


class ASIN(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    partner_id: int = Field(foreign_key="partner.id", index=True)
    asin: str = Field(index=True)
    title: str
    image_url: str | None = None
    category: str | None = None
    bsr: str | None = None
    rating: str | None = None
    health_score: int = 70
    compliance_score: int = 80
    listing_score: int = 70
    rufus_score: int = 65
    last_checked_at: datetime = Field(default_factory=now_utc)
    raw_json: str = "{}"


class ListingVersion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    asin_id: int = Field(foreign_key="asin.id", index=True)
    title: str
    bullets_json: str = "[]"
    description: str = ""
    images_json: str = "[]"
    is_current: bool = True
    source: str = "seed"
    created_at: datetime = Field(default_factory=now_utc)

    @property
    def bullets(self) -> list[str]:
        return json.loads(self.bullets_json or "[]")

    @property
    def images(self) -> list[str]:
        return json.loads(self.images_json or "[]")


class ChangeRequest(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    asin_id: int = Field(foreign_key="asin.id", index=True)
    change_type: str = Field(index=True)
    status: str = Field(default="pending", index=True)
    summary: str
    rationale: str = ""
    proposed_json: str = "{}"
    impact_estimate: str = ""
    audit_log: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    decided_at: datetime | None = None

    def approve(self, session: Session, actor: str = "admin") -> ListingVersion | None:
        payload = json.loads(self.proposed_json or "{}")
        self.status = "approved"
        self.decided_at = now_utc()
        self.audit_log = _append_audit(self.audit_log, f"{actor} approved change request {self.id}")

        if self.change_type == "listing_rewrite":
            current_versions = session.exec(
                select(ListingVersion).where(
                    ListingVersion.asin_id == self.asin_id,
                    ListingVersion.is_current == True,  # noqa: E712
                )
            ).all()
            for version in current_versions:
                version.is_current = False
                session.add(version)
            new_version = ListingVersion(
                asin_id=self.asin_id,
                title=payload.get("title") or payload.get("new_title") or "",
                bullets_json=json.dumps(payload.get("bullets") or payload.get("new_bullets") or []),
                description=payload.get("description") or payload.get("new_description") or "",
                images_json=json.dumps(payload.get("images") or []),
                source=f"change_request:{self.id}",
                is_current=True,
            )
            session.add(new_version)
            session.add(self)
            session.commit()
            return new_version

        session.add(self)
        session.commit()
        return None

    def reject(self, session: Session, actor: str = "admin") -> None:
        self.status = "rejected"
        self.decided_at = now_utc()
        self.audit_log = _append_audit(self.audit_log, f"{actor} rejected change request {self.id}")
        session.add(self)
        session.commit()


class LLMCall(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cache_key: str = Field(index=True)
    model: str
    prompt_hash: str
    prompt_preview: str
    response_text: str
    tokens: int = 0
    cost_estimate_eur: float = 0.0
    cache_hit: bool = False
    created_at: datetime = Field(default_factory=now_utc, index=True)


class WeeklyReport(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    partner_id: int = Field(foreign_key="partner.id", index=True)
    period_start: datetime
    period_end: datetime
    markdown: str
    created_at: datetime = Field(default_factory=now_utc)


def get_db(partner_slug: str) -> Engine:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if partner_slug not in _ENGINES:
        db_path = DATA_DIR / f"{partner_slug}.db"
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(engine)
        _ENGINES[partner_slug] = engine
    return _ENGINES[partner_slug]


def list_partner_slugs() -> list[str]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(path.stem for path in DATA_DIR.glob("*.db")) or ["demo"]


def get_partner(session: Session, slug: str) -> Partner:
    partner = session.exec(select(Partner).where(Partner.slug == slug)).first()
    if partner:
        return partner
    partner = Partner(slug=slug, name=slug.replace("-", " ").title())
    session.add(partner)
    session.commit()
    session.refresh(partner)
    return partner


def current_versions(session: Session) -> dict[int, ListingVersion]:
    versions = session.exec(select(ListingVersion).where(ListingVersion.is_current == True)).all()  # noqa: E712
    return {version.asin_id: version for version in versions}


def seed_demo() -> None:
    engine = get_db("demo")
    with Session(engine) as session:
        if session.exec(select(Partner).where(Partner.slug == "demo")).first():
            return
        partner = Partner(slug="demo", name="Demo Garden GmbH")
        session.add(partner)
        session.commit()
        session.refresh(partner)

        samples = [
            {
                "asin": "B0GARDN001",
                "title": "Flexibler Gartenschlauch 30 m mit Messingkupplung",
                "category": "irrigation",
                "bsr": "#1.248 in Garten",
                "rating": "4,4",
                "image": "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=300",
                "scores": (84, 78, 72, 66),
                "bullets": ["30 m Schlauch", "Messingkupplungen", "Knickarm und leicht"],
                "description": "Flexibler Gartenschlauch fuer Balkon, Terrasse und Garten.",
            },
            {
                "asin": "B0GARDN002",
                "title": "Bypass Gartenschere fuer Rosen und Obstbaeume",
                "category": "hand_tools",
                "bsr": "#842 in Gartenscheren",
                "rating": "4,6",
                "image": "https://images.unsplash.com/photo-1466692476868-aef1dfb1e735?w=300",
                "scores": (81, 86, 77, 69),
                "bullets": ["Scharfe SK5-Klinge", "Ergonomischer Griff", "Sicherheitsverschluss"],
                "description": "Praezise Bypass-Schere fuer frische Triebe und Rosen.",
            },
            {
                "asin": "B0GARDN003",
                "title": "Mähroboter fuer kleine Gaerten bis 500 m2",
                "category": "electric_tools",
                "bsr": "#391 in Rasenmaeher",
                "rating": "4,1",
                "image": "https://images.unsplash.com/photo-1558904541-efa843a96f01?w=300",
                "scores": (62, 70, 68, 58),
                "bullets": ["Leiser Motor", "Regensensor", "App-Steuerung"],
                "description": "Automatischer Maehroboter mit Begrenzungskabel und Ladestation.",
            },
            {
                "asin": "B0GARDN004",
                "title": "Hochbeet Metall 120 x 80 cm witterungsbestaendig",
                "category": "outdoor_furniture",
                "bsr": "#2.016 in Hochbeete",
                "rating": "4,3",
                "image": "https://images.unsplash.com/photo-1591857177580-dc82b9ac4e1e?w=300",
                "scores": (88, 74, 75, 71),
                "bullets": ["Verzinkter Stahl", "Offener Boden", "Schneller Aufbau"],
                "description": "Robustes Metall-Hochbeet fuer Gemuese und Kraeuter.",
            },
            {
                "asin": "B0GARDN005",
                "title": "Smart Bewaesserungscomputer WLAN fuer kalkhaltiges Wasser",
                "category": "irrigation",
                "bsr": "#614 in Bewaesserungscomputer",
                "rating": "4,2",
                "image": "https://images.unsplash.com/photo-1599685315640-4a0ab5cfc822?w=300",
                "scores": (69, 82, 79, 73),
                "bullets": ["WLAN-Steuerung", "Zeitplaene per App", "Fuer 1/2 Zoll und 3/4 Zoll"],
                "description": "Smarte Bewaesserung fuer Rasen, Beete und Balkonpflanzen.",
            },
        ]

        for item in samples:
            compliance_score, listing_score, rufus_score, health_score = item["scores"]
            asin = ASIN(
                partner_id=partner.id,
                asin=item["asin"],
                title=item["title"],
                image_url=item["image"],
                category=item["category"],
                bsr=item["bsr"],
                rating=item["rating"],
                compliance_score=compliance_score,
                listing_score=listing_score,
                rufus_score=rufus_score,
                health_score=health_score,
                raw_json=json.dumps(item),
            )
            session.add(asin)
            session.commit()
            session.refresh(asin)
            session.add(
                ListingVersion(
                    asin_id=asin.id,
                    title=item["title"],
                    bullets_json=json.dumps(item["bullets"]),
                    description=item["description"],
                    images_json=json.dumps([item["image"]]),
                )
            )

        session.commit()
        asins = session.exec(select(ASIN)).all()
        requests = [
            ChangeRequest(
                asin_id=asins[2].id,
                change_type="compliance_fix",
                summary="缺少 EU Responsible Person 聲明",
                rationale="電動園藝工具需要更清楚呈現 CE / RP / 電池安全資訊。",
                proposed_json=json.dumps({"fix_text_de": "EU-Verantwortliche Person: Demo Garden GmbH, Musterstrasse 1, 10115 Berlin, Deutschland."}),
                impact_estimate="合規風險下降",
            ),
            ChangeRequest(
                asin_id=asins[0].id,
                change_type="listing_rewrite",
                summary="DE 標題改寫建議",
                rationale="加入 witterungsbestaendig、knickarm 等德國買家常用詞。",
                proposed_json=json.dumps(
                    {
                        "title": "Gartenschlauch 30 m, knickarm und witterungsbestaendig, mit Messingkupplungen",
                        "bullets": ["30 m Reichweite fuer Garten und Terrasse", "Messingkupplungen fuer sicheren Anschluss", "Knickarme Struktur fuer einfaches Aufrollen"],
                        "description": "Robuster Gartenschlauch fuer taegliche Bewaesserung von Rasen, Beeten und Balkonpflanzen.",
                    }
                ),
                impact_estimate="+8-12% CTR",
            ),
            ChangeRequest(
                asin_id=asins[4].id,
                change_type="rufus_answerability",
                summary="Rufus 缺少水壓相容性資訊",
                rationale="德國買家常問是否支援 Regenfass、kalkhaltiges Wasser、3/4 Zoll Anschluss。",
                proposed_json=json.dumps({"suggestion": "Ergaenze Angaben zu Wasserdruck, Kalkschutz und Anschlussgroessen."}),
                impact_estimate="Rufus score +10",
            ),
        ]
        session.add_all(requests)
        session.commit()


def _append_audit(existing: str, line: str) -> str:
    stamp = now_utc().isoformat(timespec="seconds")
    return f"{existing}\n{stamp} {line}".strip()

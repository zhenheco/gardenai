from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from core.llm import GeminiClient
from core.prompts import GPSR_PROMPT_V1


class Finding(BaseModel):
    type: str
    severity: str
    description: str
    suggested_fix: str
    fix_text_de: str = ""


CATEGORY_RULES: dict[str, list[dict[str, str]]] = {
    "electric_tools": [
        {"needle": "ce", "type": "missing_ce_mark", "severity": "high", "label": "CE 標示"},
        {"needle": "verantwortliche person", "type": "missing_eu_rp", "severity": "high", "label": "EU Responsible Person"},
        {"needle": "batterie", "type": "missing_battery_warning", "severity": "medium", "label": "電池安全資訊"},
    ],
    "chemicals": [
        {"needle": "sicherheit", "type": "missing_chemical_warning", "severity": "high", "label": "化學品安全警語"},
        {"needle": "lagerung", "type": "missing_chemical_storage", "severity": "medium", "label": "儲存方式"},
    ],
    "hand_tools": [
        {"needle": "sicherheits", "type": "missing_sharp_tool_warning", "severity": "medium", "label": "刀刃/受傷警語"},
    ],
    "irrigation": [
        {"needle": "wasserdruck", "type": "missing_pressure_info", "severity": "medium", "label": "水壓相容性"},
        {"needle": "anschluss", "type": "missing_connector_info", "severity": "low", "label": "接頭尺寸"},
    ],
    "outdoor_furniture": [
        {"needle": "traglast", "type": "missing_load_warning", "severity": "medium", "label": "承重資訊"},
        {"needle": "montage", "type": "missing_installation_warning", "severity": "low", "label": "安裝安全資訊"},
    ],
}


def check(listing: dict[str, Any]) -> list[Finding]:
    text = _listing_text(listing).lower()
    category = _category_key(listing)
    findings: list[Finding] = []
    for rule in CATEGORY_RULES.get(category, []):
        if rule["needle"] not in text:
            findings.append(
                Finding(
                    type=rule["type"],
                    severity=rule["severity"],
                    description=f"可能缺少 {rule['label']}，Amazon.de 園藝類賣家應在 listing 或合規文件中明確提供。",
                    suggested_fix=f"補上 {rule['label']} 的德文說明，並確認與實際文件一致。",
                    fix_text_de=_fix_text(rule["type"]),
                )
            )
    return findings


def check_with_llm(listing: dict[str, Any], client: GeminiClient | None = None) -> list[Finding]:
    findings = check(listing)
    prompt = GPSR_PROMPT_V1.format(
        title=listing.get("title", ""),
        bullets=json.dumps(listing.get("bullets", []), ensure_ascii=False),
        description=listing.get("description", ""),
        category=listing.get("category", ""),
        image_urls=json.dumps(listing.get("images", []), ensure_ascii=False),
    )
    data = (client or GeminiClient()).generate_json(prompt)
    for item in data.get("findings", [])[:5]:
        try:
            findings.append(
                Finding(
                    type=item.get("type", "other"),
                    severity=item.get("severity", "medium"),
                    description=item.get("description", ""),
                    suggested_fix=item.get("suggested_fix", ""),
                    fix_text_de=item.get("fix_text_de", ""),
                )
            )
        except Exception:
            continue
    return findings


def generate_rp_statement(listing: dict[str, Any], partner_name: str = "Demo Garden GmbH") -> str:
    prompt = (
        "Schreibe eine kurze, neutrale EU Responsible Person Angabe fuer Amazon.de. "
        "Nutze keine erfundenen Zertifikate. Produkt: "
        f"{listing.get('title', '')}. Marke/Haendler: {partner_name}. "
        "Gib nur den deutschen Text aus, maximal 80 Woerter."
    )
    try:
        return GeminiClient().generate_text(prompt)
    except Exception:
        return (
            f"EU-Verantwortliche Person: {partner_name}, Musterstrasse 1, "
            "10115 Berlin, Deutschland. Bitte pruefen und durch die tatsaechlichen Kontaktdaten ersetzen."
        )


def risk_badge(findings: list[Finding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "🔴"
    if findings:
        return "🟡"
    return "🟢"


def _listing_text(listing: dict[str, Any]) -> str:
    bullets = " ".join(listing.get("bullets") or [])
    return f"{listing.get('title', '')} {bullets} {listing.get('description', '')} {listing.get('category', '')}"


def _category_key(listing: dict[str, Any]) -> str:
    raw = str(listing.get("category", "")).lower()
    title = str(listing.get("title", "")).lower()
    combined = f"{raw} {title}"
    if any(term in combined for term in ["mähroboter", "maehroboter", "wlan", "akku", "electric", "elektro"]):
        return "electric_tools"
    if any(term in combined for term in ["duenger", "dünger", "chem", "reiniger"]):
        return "chemicals"
    if any(term in combined for term in ["schere", "säge", "saege", "messer"]):
        return "hand_tools"
    if any(term in combined for term in ["schlauch", "bewaesser", "bewässer", "irrigation"]):
        return "irrigation"
    if any(term in combined for term in ["hochbeet", "moebel", "möbel", "furniture"]):
        return "outdoor_furniture"
    return raw or "other"


def _fix_text(rule_type: str) -> str:
    texts = {
        "missing_ce_mark": "Dieses Produkt entspricht den geltenden EU-Anforderungen. Bitte CE-Konformitaet und Dokumentation vor Veroeffentlichung pruefen.",
        "missing_eu_rp": "EU-Verantwortliche Person: [Name], [Strasse], [PLZ Ort], [Land], [E-Mail].",
        "missing_battery_warning": "Hinweis: Akkus und Ladegeraete nur gemaess Bedienungsanleitung verwenden. Vor Feuchtigkeit schuetzen und sachgerecht entsorgen.",
        "missing_sharp_tool_warning": "Sicherheitshinweis: Scharfe Klinge. Ausser Reichweite von Kindern aufbewahren und bei Nichtgebrauch verriegeln.",
        "missing_pressure_info": "Geeignet fuer haushaltsuebliche Wasseranschluesse. Bitte Wasserdruck und Anschlussgroesse vor dem Kauf pruefen.",
        "missing_connector_info": "Kompatibel mit gaengigen 1/2-Zoll- und 3/4-Zoll-Anschluessen, sofern in der Anleitung bestaetigt.",
        "missing_load_warning": "Bitte maximale Traglast beachten und das Produkt auf ebenem, stabilem Untergrund montieren.",
    }
    return texts.get(rule_type, "Bitte ergaenzen Sie klare Sicherheits- und Herstellerangaben fuer Amazon.de.")

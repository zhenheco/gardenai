from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from selectolax.parser import HTMLParser


LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.6",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
}


def scrape_asin(asin: str, marketplace: str = "DE") -> dict[str, Any] | None:
    domain = "amazon.de" if marketplace.upper() == "DE" else "amazon.com"
    url = f"https://www.{domain}/dp/{asin}"
    try:
        response = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
    except httpx.HTTPError as exc:
        LOGGER.warning("Amazon scrape failed for %s: %s", asin, exc)
        return None

    if response.status_code in {403, 429, 503} or _looks_blocked(response.text):
        LOGGER.warning("Amazon blocked scrape for %s with status %s", asin, response.status_code)
        return None
    if response.status_code >= 400:
        LOGGER.warning("Amazon scrape returned status %s for %s", response.status_code, asin)
        return None

    tree = HTMLParser(response.text)
    title = _text(tree, "#productTitle")
    if not title:
        return None

    bullets = [
        node.text(separator=" ", strip=True)
        for node in tree.css("#feature-bullets li span.a-list-item")
        if node.text(strip=True)
    ]
    description = _text(tree, "#productDescription") or _text(tree, "#aplus")
    images = _images(tree)
    category = _category(tree)
    bsr = _best_seller_rank(tree.text(separator=" ", strip=True))
    rating = _text(tree, "#acrPopover .a-icon-alt") or _text(tree, "span[data-hook='rating-out-of-text']")

    return {
        "asin": asin,
        "marketplace": marketplace.upper(),
        "title": title,
        "bullets": bullets[:8],
        "description": description,
        "images": images,
        "category": category,
        "bsr": bsr,
        "rating": rating,
        "url": url,
    }


def _text(tree: HTMLParser, selector: str) -> str:
    node = tree.css_first(selector)
    return node.text(separator=" ", strip=True) if node else ""


def _images(tree: HTMLParser) -> list[str]:
    images: list[str] = []
    for selector in ["#landingImage", "#imgTagWrapperId img", "img[data-old-hires]"]:
        node = tree.css_first(selector)
        if not node:
            continue
        src = node.attributes.get("data-old-hires") or node.attributes.get("src")
        if src and src.startswith("http") and src not in images:
            images.append(src)
    for node in tree.css("img"):
        src = node.attributes.get("src", "")
        if "images/I/" in src and src.startswith("http") and src not in images:
            images.append(src)
        if len(images) >= 6:
            break
    return images


def _category(tree: HTMLParser) -> str:
    crumbs = [
        node.text(separator=" ", strip=True)
        for node in tree.css("#wayfinding-breadcrumbs_feature_div li a")
        if node.text(strip=True)
    ]
    return " > ".join(crumbs)


def _best_seller_rank(page_text: str) -> str:
    patterns = [
        r"Nr\.\s*[\d\.,]+\s+in\s+[^#]+",
        r"#\s*[\d\.,]+\s+in\s+[^#]+",
        r"Amazon Bestseller-Rang\s*[:\-]?\s*([^|]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, page_text)
        if match:
            return match.group(0 if pattern.startswith(("Nr", "#")) else 1).strip()[:120]
    return ""


def _looks_blocked(html: str) -> bool:
    lowered = html.lower()
    return "captcha" in lowered or "robot check" in lowered or "automated access" in lowered

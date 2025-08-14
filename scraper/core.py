# scraper-webUI
# By G0246

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.parse import urlparse, urljoin

import bs4
import requests
from bs4 import BeautifulSoup
from requests import Response
from urllib import robotparser

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


@dataclass
class ScrapedItem:
    index: int
    tag: str
    text: str
    href: Optional[str]
    attribute_value: Optional[str]
    html: str


@dataclass
class ScrapeResult:
    url: str
    selector: str
    selector_type: str
    items: List[dict]
    elapsed_ms: int


def is_allowed_by_robots(url: str, user_agent: str = "scraper-webUI") -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True


def _build_headers(user_agent: Optional[str]) -> dict:
    return {
        "User-Agent": user_agent or DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }


def _http_get(url: str, headers: dict) -> Response:
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return response


def _resolve_link(base_url: str, element: bs4.Tag) -> Optional[str]:
    href = element.get("href")
    if href:
        return urljoin(base_url, href)
    return None


def _to_absolute_url(base_url: str, maybe_url: Optional[str]) -> Optional[str]:
    if not maybe_url:
        return None
    return urljoin(base_url, maybe_url)


def _parse_srcset_take_first(srcset_value: str) -> Optional[str]:
    if not srcset_value:
        return None
    # srcset can be like: "image1.jpg 1x, image2.jpg 2x"
    first_part = srcset_value.split(',')[0].strip()
    return first_part.split(' ')[0]


def _extract_attribute(element: bs4.Tag, attribute_name: Optional[str], base_url: Optional[str] = None) -> Optional[str]:
    if not attribute_name:
        return None
    value = element.get(attribute_name)
    if isinstance(value, list):
        value = " ".join(value)

    # Resolve common URL-like attributes to absolute
    if base_url and attribute_name.lower() in {"src", "data-src", "href"}:
        return _to_absolute_url(base_url, value)

    if base_url and attribute_name.lower() == "srcset" and isinstance(value, str):
        first_src = _parse_srcset_take_first(value)
        return _to_absolute_url(base_url, first_src)

    return value


def _is_image_url(url: Optional[str]) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return any(
        lowered.endswith(ext)
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".avif")
    )


def _image_url_from_element(base_url: str, element: bs4.Tag, attribute_name: Optional[str]) -> Optional[str]:
    # Prefer <img src> or data-src/srcset
    if element.name == "img":
        src = element.get("src") or element.get("data-src")
        if not src and element.get("srcset"):
            src = _parse_srcset_take_first(element.get("srcset"))
        return _to_absolute_url(base_url, src)

    # If a specific attribute is requested and looks like an image URL
    if attribute_name:
        candidate = _extract_attribute(element, attribute_name, base_url)
        if _is_image_url(candidate):
            return candidate

    # As a fallback, if href points to an image
    href = element.get("href")
    href_abs = _to_absolute_url(base_url, href)
    if _is_image_url(href_abs):
        return href_abs

    return None


def _elements_to_items(base_url: str, elements: Iterable[bs4.Tag], attribute_name: Optional[str]) -> List[dict]:
    items: List[dict] = []
    for index, element in enumerate(elements):
        text = element.get_text(strip=True)
        href = _resolve_link(base_url, element)
        attribute_value = _extract_attribute(element, attribute_name, base_url)
        image_url = _image_url_from_element(base_url, element, attribute_name)
        items.append(
            {
                "index": index,
                "tag": element.name or "",
                "text": text,
                "href": href,
                "attribute_value": attribute_value,
                "image_url": image_url,
                "html": str(element),
            }
        )
    return items


def scrape_with_selector(
    url: str,
    selector_type: str,
    selector: str,
    attribute_name: Optional[str] = None,
    user_agent: Optional[str] = None,
    max_items: Optional[int] = None,
) -> ScrapeResult:
    start_time = time.perf_counter()
    headers = _build_headers(user_agent)
    response = _http_get(url, headers=headers)
    html = response.text

    soup = BeautifulSoup(html, "lxml")

    if selector_type.lower() in {"css", "selector", "query"}:
        elements = soup.select(selector)
    elif selector_type.lower() in {"xpath"}:
        # Minimal xpath support using select from SoupSieve does not support XPATH; require parsel/lxml if needed later
        raise ValueError("XPATH is not supported in this minimal build. Use CSS selectors.")
    else:
        raise ValueError("Unknown selector_type. Use 'css'.")

    if max_items is not None and max_items >= 0:
        elements = elements[: max(0, max_items)]

    items = _elements_to_items(url, elements, attribute_name)

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    return ScrapeResult(
        url=url,
        selector=selector,
        selector_type=selector_type,
        items=items,
        elapsed_ms=elapsed_ms,
    )


def _find_next_url(base_url: str, soup: BeautifulSoup, next_selector: Optional[str]) -> Optional[str]:
    if not next_selector:
        return None
    try:
        el = soup.select_one(next_selector)
        if not el:
            return None
        href = el.get("href")
        return urljoin(base_url, href) if href else None
    except Exception:
        return None


def scrape_paginated(
    url: str,
    selector_type: str,
    selector: str,
    next_selector: Optional[str] = None,
    attribute_name: Optional[str] = None,
    user_agent: Optional[str] = None,
    max_items: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> ScrapeResult:
    start_time = time.perf_counter()
    headers = _build_headers(user_agent)

    collected: List[dict] = []
    pages_visited = 0
    current_url = url

    while current_url:
        response = _http_get(current_url, headers=headers)
        html = response.text
        soup = BeautifulSoup(html, "lxml")

        if selector_type.lower() in {"css", "selector", "query"}:
            elements = soup.select(selector)
        else:
            raise ValueError("Unknown selector_type. Use 'css'.")

        page_items = _elements_to_items(current_url, elements, attribute_name)
        collected.extend(page_items)

        pages_visited += 1
        if max_pages is not None and pages_visited >= max_pages:
            break

        if max_items is not None and len(collected) >= max_items:
            collected = collected[:max(0, max_items)]
            break

        next_url = _find_next_url(current_url, soup, next_selector)
        if not next_url or next_url == current_url:
            break
        current_url = next_url

    # Reindex items after aggregation
    for idx, item in enumerate(collected):
        item["index"] = idx

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    return ScrapeResult(
        url=url,
        selector=selector,
        selector_type=selector_type,
        items=collected,
        elapsed_ms=elapsed_ms,
    )



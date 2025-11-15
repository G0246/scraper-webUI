# scraper-webUI
# A not very efficient web scraper.
# core.py
# By G0246

from __future__ import annotations

import time
import concurrent.futures
from dataclasses import dataclass
from typing import Iterable, List, Optional, Callable, Dict, Any
from urllib.parse import urlparse, urljoin

import bs4
import requests
from bs4 import BeautifulSoup
from requests import Response
from urllib import robotparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import the dynamic user agent generator
from scraper.gen_UA import get_random_user_agent, UserAgentGenerator

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)

# Cache for robots.txt parsers to avoid repeated fetches
_robots_cache: Dict[str, robotparser.RobotFileParser] = {}

# Not used
DESKTOP_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
]

MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

def get_user_agent_stats() -> Dict[str, Any]:
    return {
        "mode": "dynamic",
        "description": "User agents are generated fresh on every request using common patterns",
        "desktop_browsers": ["Chrome", "Firefox", "Safari", "Edge"],
        "mobile_browsers": ["Chrome (Android)", "Safari (iOS)", "Safari (iPad)", "Firefox (Android)"],
        "os_platforms": ["Windows", "macOS", "Linux", "Android", "iOS"],
        "note": "Each request generates a unique user agent with random versions",
        "fallback_desktop": len(DESKTOP_USER_AGENTS),
        "fallback_mobile": len(MOBILE_USER_AGENTS),
    }

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
    
    # Check cache first to avoid repeated fetches
    if robots_url in _robots_cache:
        robot_bouncer = _robots_cache[robots_url]
        try:
            return robot_bouncer.can_fetch(user_agent, url)
        except Exception:
            return True
    
    # Fetch and cache if not found
    robot_bouncer = robotparser.RobotFileParser()
    try:
        robot_bouncer.set_url(robots_url)
        robot_bouncer.read()
        _robots_cache[robots_url] = robot_bouncer
        return robot_bouncer.can_fetch(user_agent, url)
    except Exception:
        return True

def _pick_user_agent(explicit_user_agent: Optional[str], prefer_mobile: bool = False) -> str:
    if explicit_user_agent:
        return explicit_user_agent

    try:
        # Use the dynamic generator instead of hardcoded lists
        return get_random_user_agent(prefer_mobile=prefer_mobile)
    except Exception:
        # Fallback to default if something goes wrong
        return DEFAULT_USER_AGENT

def _build_headers(user_agent: Optional[str], prefer_mobile: bool = False) -> dict:
    picked_ua = _pick_user_agent(user_agent, prefer_mobile)

    # Adjust Accept headers based on whether it's mobile
    is_mobile = "Mobile" in picked_ua or "Android" in picked_ua

    headers = {
        "User-Agent": picked_ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        # Don't set Accept-Encoding manually - let requests handle it automatically
        # This ensures automatic decompression of gzip/deflate/br responses
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # Add mobile-specific headers
    if is_mobile:
        headers["Viewport-Width"] = "360"

    return headers

def create_session(user_agent: Optional[str], fast_mode: bool = False, retries: int = 2, prefer_mobile: bool = False) -> requests.Session:
    session = requests.Session()
    session.headers.update(_build_headers(user_agent, prefer_mobile))
    total_retries = 0 if fast_mode else max(0, retries)
    retry_strategy = Retry(
        total=total_retries, 
        backoff_factor=(0.15 if fast_mode else 0.3), 
        status_forcelist=[429, 500, 502, 503, 504],
        # Optimize retries by avoiding retries on POST/PUT/PATCH
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    # Increase pool sizes for better concurrent performance
    adapter = HTTPAdapter(
        pool_connections=50,  # Increased from 20
        pool_maxsize=100,     # Increased from 50
        max_retries=retry_strategy,
        pool_block=False      # Don't block when pool is full
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def _http_get(url: str, session: requests.Session, timeout_seconds: Optional[int] = None) -> Response:
    response = session.get(url, timeout=(timeout_seconds if timeout_seconds is not None else 15))
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
    first_course = srcset_value.split(',')[0].strip()
    return first_course.split(' ')[0]

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

    # If a specific attribute is requested and looks like an image URL?
    if attribute_name:
        maybe_an_image = _extract_attribute(element, attribute_name, base_url)
        if _is_image_url(maybe_an_image):
            return maybe_an_image

    # Fallback: if href points to an image
    href = element.get("href")
    href_abs = _to_absolute_url(base_url, href)
    if _is_image_url(href_abs):
        return href_abs

    return None

def _find_detail_url(base_url: str, element: bs4.Tag, detail_url_selector: Optional[str], detail_url_attribute: str) -> Optional[str]:
    # Prefer an explicit detail selector inside the element
    if detail_url_selector:
        try:
            sub = element.select_one(detail_url_selector)
            if sub:
                href = sub.get(detail_url_attribute or "href")
                if href:
                    return _to_absolute_url(base_url, href)
        except Exception:
            pass

    # Fallback: self href, then nearest parent link
    href = element.get("href")
    if href:
        return _to_absolute_url(base_url, href)
    parent_link = element.find_parent("a")
    if parent_link and parent_link.get("href"):
        return _to_absolute_url(base_url, parent_link.get("href"))
    return None


def _elements_to_items(
    base_url: str,
    elements: Iterable[bs4.Tag],
    attribute_name: Optional[str],
    detail_url_selector: Optional[str] = None,
    detail_url_attribute: str = "href",
    detail_image_selector: Optional[str] = None,
    detail_image_attribute: str = "src",
) -> List[dict]:
    items: List[dict] = []
    for index, element in enumerate(elements):
        # Use get_text with separator to be more efficient than strip=True
        text = element.get_text(separator=" ", strip=True)
        href = _resolve_link(base_url, element)
        attribute_value = _extract_attribute(element, attribute_name, base_url)
        image_url = _image_url_from_element(base_url, element, attribute_name)
        detail_url = _find_detail_url(base_url, element, detail_url_selector, detail_url_attribute)
        
        # Lazily convert to string only when needed - use encode for faster serialization
        # Limit HTML field length to prevent memory issues with large elements
        html_str = str(element)
        if len(html_str) > 5000:  # Truncate very large HTML
            html_str = html_str[:5000] + "..."
        
        items.append(
            {
                "index": index,
                "tag": element.name or "",
                "text": text,
                "href": href,
                "attribute_value": attribute_value,
                "image_url": image_url,
                "detail_url": detail_url,
                "html": html_str,
            }
        )
    return items

def _extract_full_image_from_detail(session: requests.Session, detail_url: str, detail_image_selector: str, detail_image_attribute: str) -> Optional[str]:
    try:
        resp = session.get(detail_url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        el = soup.select_one(detail_image_selector)
        if not el:
            return None
        value = el.get(detail_image_attribute or "src")
        return _to_absolute_url(detail_url, value)
    except Exception:
        return None

def _enrich_items_with_detail_images(
    session: requests.Session,
    items: List[dict],
    detail_image_selector: str,
    detail_image_attribute: str,
    is_canceled: Optional[Callable[[], bool]] = None,
    max_workers: int = 8
) -> None:
    """Fetch detail page images in parallel to enrich items.
    
    Modifies items in-place by updating their image_url field.
    Uses URL deduplication to avoid fetching the same detail page multiple times.
    """
    # Build a map of detail URLs to item indices for deduplication
    url_to_indices: Dict[str, List[int]] = {}
    for i, item in enumerate(items):
        detail_url = item.get("detail_url")
        if detail_url:
            if detail_url not in url_to_indices:
                url_to_indices[detail_url] = []
            url_to_indices[detail_url].append(i)
    
    if not url_to_indices:
        return
    
    # Create unique fetch tasks (one per unique URL)
    unique_urls = list(url_to_indices.keys())
    
    def fetch_detail_image(detail_url):
        if is_canceled and is_canceled():
            return detail_url, None
        full_img = _extract_full_image_from_detail(
            session=session,
            detail_url=detail_url,
            detail_image_selector=detail_image_selector,
            detail_image_attribute=detail_image_attribute,
        )
        return detail_url, full_img
    
    # Fetch unique images in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for detail_url, full_img in executor.map(fetch_detail_image, unique_urls):
            if is_canceled and is_canceled():
                raise RuntimeError("Cancelled")
            if full_img:
                # Update all items that share this detail URL
                for idx in url_to_indices[detail_url]:
                    items[idx]["image_url"] = full_img

def scrape_with_selector(
    url: str,
    selector_type: str,
    selector: str,
    attribute_name: Optional[str] = None,
    user_agent: Optional[str] = None,
    max_items: Optional[int] = None,
    detail_url_selector: Optional[str] = None,
    detail_url_attribute: str = "href",
    detail_image_selector: Optional[str] = None,
    detail_image_attribute: str = "src",
    fast_mode: bool = False,
    progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    is_canceled: Optional[Callable[[], bool]] = None
) -> ScrapeResult:
    start_time = time.perf_counter()
    session = create_session(user_agent, fast_mode=fast_mode)
    response = _http_get(url, session=session)
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
        # Slice early to avoid converting unnecessary elements
        elements = elements[: max(0, max_items)]

    items = _elements_to_items(url, elements, attribute_name, detail_url_selector, detail_url_attribute, detail_image_selector, detail_image_attribute)

    # Optionally enrich/override image_url by visiting detail pages (in parallel)
    if detail_image_selector:
        _enrich_items_with_detail_images(
            session=session,
            items=items,
            detail_image_selector=detail_image_selector,
            detail_image_attribute=detail_image_attribute,
            is_canceled=is_canceled,
            max_workers=8
        )

    if progress_cb:
        progress_cb({"stage": "done", "items": len(items), "url": url})

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
    detail_url_selector: Optional[str] = None,
    detail_url_attribute: str = "href",
    detail_image_selector: Optional[str] = None,
    detail_image_attribute: str = "src",
    fast_mode: bool = False,
    progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    is_canceled: Optional[Callable[[], bool]] = None
) -> ScrapeResult:
    start_time = time.perf_counter()
    session = create_session(user_agent, fast_mode=fast_mode)

    collected: List[dict] = []
    pages_visited = 0
    current_url = url
    url_graveyard: set = set()  # Track visited URLs to avoid infinite loops

    while current_url:
        if is_canceled and is_canceled():
            raise RuntimeError("Cancelled")

        # Check if we've been here before (avoid infinite loops)
        if current_url in url_graveyard:
            break
        url_graveyard.add(current_url)

        response = _http_get(current_url, session=session)
        html = response.text
        soup = BeautifulSoup(html, "lxml")

        if selector_type.lower() in {"css", "selector", "query"}:
            elements = soup.select(selector)
        else:
            raise ValueError("Unknown selector_type. Use 'css'.")

        page_items = _elements_to_items(
            current_url,
            elements,
            attribute_name,
            detail_url_selector,
            detail_url_attribute,
            detail_image_selector,
            detail_image_attribute,
        )
        for it in page_items:
            if is_canceled and is_canceled():
                raise RuntimeError("Cancelled")
            collected.append(it)

        if progress_cb:
            progress_cb({
                "stage": "page",
                "pages_visited": pages_visited,
                "items": len(collected),
                "url": current_url,
            })

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

    # Enrich/override items with full images if requested (in parallel)
    if detail_image_selector:
        _enrich_items_with_detail_images(
            session=session,
            items=collected,
            detail_image_selector=detail_image_selector,
            detail_image_attribute=detail_image_attribute,
            is_canceled=is_canceled,
            max_workers=8
        )

    # Reindex items
    for idx, item in enumerate(collected):
        item["index"] = idx

    if progress_cb:
        progress_cb({"stage": "done", "items": len(collected), "url": url})

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    return ScrapeResult(
        url=url,
        selector=selector,
        selector_type=selector_type,
        items=collected,
        elapsed_ms=elapsed_ms,
    )

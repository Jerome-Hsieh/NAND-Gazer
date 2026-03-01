import time
import random
import logging

import httpx

logger = logging.getLogger(__name__)

SEARCH_URL = "https://ecshweb.pchome.com.tw/search/v4.3/all/results"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://24h.pchome.com.tw/",
}

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class PChomeClient:
    def __init__(self) -> None:
        self._client = httpx.Client(headers=DEFAULT_HEADERS, timeout=15.0)

    def search(self, keyword: str, page: int = 1, sort: str = "sale/dc") -> dict:
        """Search PChome for products. Returns the raw JSON response as a dict."""
        params = {"q": keyword, "page": page, "sort": sort}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info("Searching '%s' page %d (attempt %d)", keyword, page, attempt)
                resp = self._client.get(SEARCH_URL, params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.warning("Request failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    raise

    def search_pages(self, keyword: str, pages: int = 3) -> list[dict]:
        """Search multiple pages and return a list of raw JSON responses."""
        results: list[dict] = []
        for page in range(1, pages + 1):
            data = self.search(keyword, page=page)
            results.append(data)

            total_pages = data.get("TotalPage") or data.get("totalPage") or 0
            if page >= total_pages:
                logger.info("Reached last page (%d/%d) for '%s'", page, total_pages, keyword)
                break

            delay = random.uniform(1.0, 3.0)
            logger.debug("Sleeping %.1fs before next page", delay)
            time.sleep(delay)

        return results

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

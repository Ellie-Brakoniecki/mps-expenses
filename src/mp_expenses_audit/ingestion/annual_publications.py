"""Ingestion module for IPSA annual publications total spend data."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from mp_expenses_audit import config


LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.theipsa.org.uk"
ANNUAL_PAGE = f"{BASE_URL}/mp-staffing-business-costs/annual-publications"
DEFAULT_RAW_DIR = config.DATA_DIR / "raw" / "annual_publications"
REQUEST_TIMEOUT_SECONDS = 60
REQUEST_HEADERS = {
    "User-Agent": "mp-expenses-audit/1.0 (+https://www.theipsa.org.uk)",
}


def fetch_annual_page(
    url: str = ANNUAL_PAGE,
    *,
    session: requests.Session | None = None,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> BeautifulSoup:
    """Fetch the IPSA annual publications page and return parsed HTML."""
    client = session or requests.Session()
    LOGGER.info("Fetching IPSA annual publications page from %s", url)
    response = client.get(url, timeout=timeout, headers=REQUEST_HEADERS)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_total_spend_links(soup: BeautifulSoup, base_url: str = BASE_URL) -> list[str]:
    """Extract, deduplicate, and sort total spend CSV download links."""
    links = {
        urljoin(base_url, href)
        for anchor in soup.find_all("a", href=True)
        for href in [anchor["href"]]
        if "type=totalSpend" in href
    }
    ordered_links = sorted(links, reverse=True)
    LOGGER.info("Extracted %s total spend links from annual publications page", len(ordered_links))
    return ordered_links


def download_all_total_spend(
    links: Iterable[str],
    *,
    output_dir: Path | None = None,
    session: requests.Session | None = None,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> pd.DataFrame:
    """Download all total spend CSVs, save raw files, and return a combined DataFrame."""
    client = session or requests.Session()
    raw_dir = output_dir or DEFAULT_RAW_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)

    ordered_links = sorted(set(links), reverse=True)
    LOGGER.info("Preparing to download %s total spend files into %s", len(ordered_links), raw_dir)

    frames: list[pd.DataFrame] = []

    for index, link in enumerate(ordered_links, start=1):
        try:
            raw_file_path = _download_raw_csv(
                link,
                raw_dir=raw_dir,
                session=client,
                timeout=timeout,
                index=index,
            )
            frame = pd.read_csv(raw_file_path)
            frame["source_url"] = link
            frame["source_file"] = str(raw_file_path)
            frames.append(frame)
            LOGGER.info("Downloaded and loaded %s", raw_file_path.name)
        except Exception:
            LOGGER.exception("Failed to download or load total spend file from %s", link)

    if not frames:
        LOGGER.warning("No total spend files were downloaded successfully")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    LOGGER.info("Combined %s files into a DataFrame with %s rows", len(frames), len(combined))
    return combined


def run_ingestion_pipeline(
    *,
    annual_page_url: str = ANNUAL_PAGE,
    output_dir: Path | None = None,
    session: requests.Session | None = None,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> pd.DataFrame:
    """Run the annual publications ingestion flow for total spend data."""
    LOGGER.info("Starting IPSA annual publications ingestion pipeline")
    soup = fetch_annual_page(url=annual_page_url, session=session, timeout=timeout)
    links = extract_total_spend_links(soup)
    return download_all_total_spend(links, output_dir=output_dir, session=session, timeout=timeout)


def _download_raw_csv(
    link: str,
    *,
    raw_dir: Path,
    session: requests.Session,
    timeout: int,
    index: int,
) -> Path:
    """Download a CSV from IPSA and persist the raw response body to disk."""
    response = session.get(link, timeout=timeout, headers=REQUEST_HEADERS)
    response.raise_for_status()

    raw_file_path = raw_dir / _build_raw_file_name(link, index=index)
    raw_file_path.write_bytes(response.content)
    return raw_file_path


def _build_raw_file_name(link: str, *, index: int) -> str:
    """Create a deterministic file name from the source URL."""
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    year = query.get("year", [f"file_{index:02d}"])[0]
    report_type = query.get("type", ["totalSpend"])[0]
    safe_year = _slugify(year)
    safe_type = _slugify(report_type)
    return f"ipsa_{safe_type}_{safe_year}.csv"


def _slugify(value: str) -> str:
    """Create a filesystem-safe slug from a source string."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()
    return slug or "unknown"
"""Cached live metadata fetcher for IGR portal cascading dropdowns (SRO, Tahsil, Village)."""

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright

from app.automation.parser import match_dropdown_option
from app.automation.selectors import COMMON_SELECTORS, MODE_SELECTORS
from app.config import settings

_sro_cache: dict[str, list[str]] = {}
_tahsil_cache: dict[str, list[str]] = {}
_village_cache: dict[tuple[str, str], list[str]] = {}
_meta_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="igr-meta")


async def _open_portal_page(playwright):
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    )
    page = await browser.new_page()
    page.set_default_timeout(35000)
    await page.goto(settings.igr_portal_url, wait_until="commit", timeout=60000)
    await page.wait_for_load_state("domcontentloaded", timeout=45000)
    await page.wait_for_selector("#mnuSearchType", timeout=35000)
    await page.evaluate("() => { const p = document.querySelector('#popup'); if (p) p.remove(); }")
    return browser, page


async def _wait_for_options(page, selector: str, prev_snapshot: list[str] | None = None, timeout: float = 25.0) -> list[dict[str, str]]:
    elapsed = 0.0
    while elapsed < timeout:
        opts = await page.eval_on_selector_all(
            f"{selector} option",
            "els => els.map(o => ({ value: o.value ?? '', text: (o.text || '').trim() }))",
        )
        valid = [
            o for o in (opts or [])
            if (o.get("value") or "").strip() not in {"", "0", "-1"}
            and not o.get("text", "").startswith("---")
        ]
        texts = [o["text"] for o in valid]
        if valid and (prev_snapshot is None or texts != prev_snapshot):
            return valid
        await asyncio.sleep(0.4)
        elapsed += 0.4
    return []


async def _fetch_sros_async(district: str) -> list[str]:
    async with async_playwright() as p:
        browser, page = await _open_portal_page(p)
        try:
            await page.locator(COMMON_SELECTORS["tab_document"]).first.click()
            doc_cfg = MODE_SELECTORS["DOCUMENT"]
            await page.wait_for_selector(doc_cfg["district_select"], timeout=30000)
            dist_opts = await _wait_for_options(page, doc_cfg["district_select"])
            matched = match_dropdown_option(dist_opts, district)
            if not matched:
                return []
            await page.select_option(doc_cfg["district_select"], value=matched["value"])
            sro_opts = await _wait_for_options(page, doc_cfg["sro_select"])
            return [o["text"] for o in sro_opts]
        finally:
            await browser.close()


async def _fetch_tahsils_async(district: str) -> list[str]:
    async with async_playwright() as p:
        browser, page = await _open_portal_page(p)
        try:
            await page.locator(COMMON_SELECTORS["region_rest_of_mh"]).first.click()
            cfg = MODE_SELECTORS["PROPERTY_REST_OF_MH"]
            await page.wait_for_selector(cfg["district_select"], timeout=30000)
            dist_opts = await _wait_for_options(page, cfg["district_select"])
            matched = match_dropdown_option(dist_opts, district)
            if not matched:
                return []
            await page.select_option(cfg["district_select"], value=matched["value"])
            tahsil_opts = await _wait_for_options(page, cfg["tahsil_select"])
            return [o["text"] for o in tahsil_opts]
        finally:
            await browser.close()


async def _fetch_villages_async(district: str, tahsil: str) -> list[str]:
    async with async_playwright() as p:
        browser, page = await _open_portal_page(p)
        try:
            await page.locator(COMMON_SELECTORS["region_rest_of_mh"]).first.click()
            cfg = MODE_SELECTORS["PROPERTY_REST_OF_MH"]
            await page.wait_for_selector(cfg["district_select"], timeout=30000)
            dist_opts = await _wait_for_options(page, cfg["district_select"])
            matched_dist = match_dropdown_option(dist_opts, district)
            if not matched_dist:
                return []
            await page.select_option(cfg["district_select"], value=matched_dist["value"])
            tahsil_opts = await _wait_for_options(page, cfg["tahsil_select"])
            matched_tahsil = match_dropdown_option(tahsil_opts, tahsil)
            if not matched_tahsil:
                return []
            await page.select_option(cfg["tahsil_select"], value=matched_tahsil["value"])
            village_opts = await _wait_for_options(page, cfg["village_select"])
            return [o["text"] for o in village_opts]
        finally:
            await browser.close()


def _run_coro(coro_fn, *args):
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    return asyncio.run(coro_fn(*args))


def get_sros_for_district(district: str) -> tuple[list[str], str]:
    key = district.strip().lower()
    if key in _sro_cache:
        return _sro_cache[key], "cache"
    try:
        items = _meta_executor.submit(_run_coro, _fetch_sros_async, district).result(timeout=45)
        if items:
            _sro_cache[key] = items
        return items, "live"
    except Exception:
        return [], "unavailable"


def get_tahsils_for_district(district: str) -> tuple[list[str], str]:
    key = district.strip().lower()
    if key in _tahsil_cache:
        return _tahsil_cache[key], "cache"
    try:
        items = _meta_executor.submit(_run_coro, _fetch_tahsils_async, district).result(timeout=45)
        if items:
            _tahsil_cache[key] = items
        return items, "live"
    except Exception:
        return [], "unavailable"


def get_villages_for_tahsil(district: str, tahsil: str) -> tuple[list[str], str]:
    key = (district.strip().lower(), tahsil.strip().lower())
    if key in _village_cache:
        return _village_cache[key], "cache"
    try:
        items = _meta_executor.submit(_run_coro, _fetch_villages_async, district, tahsil).result(timeout=55)
        if items:
            _village_cache[key] = items
        return items, "live"
    except Exception:
        return [], "unavailable"

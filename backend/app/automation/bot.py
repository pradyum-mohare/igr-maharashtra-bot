import asyncio
import base64
import re
from datetime import datetime
from pathlib import Path
from uuid import UUID
from playwright.async_api import async_playwright, Page, BrowserContext
from app.config import settings
from app.database import SessionLocal
from app.models import SearchJob, PropertyRecord, DocumentFile, AutomationLog
from app.automation.selectors import SELECTORS


DISTRICT_ALIASES = {
    "pune": "पुणे",
    "satara": "सातारा",
    "sangli": "सांगली",
    "kolhapur": "कोल्हापूर",
    "solapur": "सोलापूर",
    "thane": "ठाणे",
    "raigad": "रायगड",
    "sindhudurg": "सिंधुदुर्ग",
    "palghar": "पालघर",
    "nashik": "नाशिक",
    "jalgaon": "जळगाव",
    "dhule": "धुळे",
    "ahilyanagar": "अहिल्यानगर",
    "ahmednagar": "अहिल्यानगर",
    "nandurbar": "नंदुरबार",
    "chhatrapati sambhajinagar": "छत्रपती संभाजीनगर",
    "aurangabad": "छत्रपती संभाजीनगर",
    "jalna": "जालना",
    "beed": "बीड",
    "latur": "लातूर",
    "dharashiv": "धाराशिव",
    "osmanabad": "धाराशिव",
    "nanded": "नांदेड",
    "parbhani": "परभणी",
    "hingoli": "हिंगोली",
    "amravati": "अमरावती",
    "akola": "अकोला",
    "washim": "वाशिम",
    "buldhana": "बुलढाणा",
    "yavatmal": "यवतमाळ",
    "nagpur": "नागपूर",
    "wardha": "वर्धा",
    "bhandara": "भंडारा",
    "gondia": "गोंदिया",
    "chandrapur": "चंद्रपूर",
    "gadchiroli": "गडचिरोली",
}


class IGRPortalBot:
    def __init__(self, job_id: UUID):
        self.job_id = job_id
        self.storage_dir = settings.resolved_storage_path()

    def _log(self, message: str, level: str = "INFO", step: str | None = None):
        db = SessionLocal()
        try:
            db.add(AutomationLog(job_id=self.job_id, level=level, step=step, message=message))
            db.commit()
        finally:
            db.close()

    def _set_status(self, status: str, captcha_b64: str | None = None, error: str | None = None):
        db = SessionLocal()
        try:
            job = db.query(SearchJob).filter(SearchJob.id == self.job_id).first()
            if not job:
                return
            job.status = status
            if captcha_b64 is not None or status != "AWAITING_CAPTCHA":
                job.captcha_image_base64 = captcha_b64
            if status == "PROCESSING":
                job.captcha_solution = None
            if error is not None:
                job.error_message = error
            db.commit()
        finally:
            db.close()

    def _get_job_snapshot(self) -> tuple[str, dict, str | None]:
        db = SessionLocal()
        try:
            job = db.query(SearchJob).filter(SearchJob.id == self.job_id).first()
            return job.search_type, dict(job.criteria or {}), job.captcha_solution
        finally:
            db.close()

    async def _goto_with_retry(self, page: Page, url: str, attempts: int = 3):
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                self._log(
                    f"Navigating to {url} (attempt {attempt}/{attempts})...",
                    step="NAVIGATE",
                )
                await page.goto(url, wait_until="commit", timeout=90000)
                return
            except Exception as exc:
                last_exc = exc
                self._log(
                    f"Navigation attempt {attempt}/{attempts} failed: {type(exc).__name__}: {exc}",
                    level="WARNING",
                    step="NAVIGATE",
                )
                if attempt < attempts:
                    await asyncio.sleep(3.0)
        raise last_exc

    async def _wait_for_loading_to_finish(self, page: Page, max_wait: float = 15.0):
        elapsed = 0.0
        step = 0.4
        while elapsed < max_wait:
            still_loading = False
            try:
                still_loading = await page.evaluate(
                    """() => {
                        const loaders = document.querySelectorAll('[id*="UpdateProgress"], [id*="Progress"], .loading, .loader');
                        for (const el of loaders) {
                            const style = window.getComputedStyle(el);
                            const rect = el.getBoundingClientRect();
                            if (style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0) {
                                return true;
                            }
                        }
                        return false;
                    }"""
                )
            except Exception:
                still_loading = False
            if not still_loading:
                break
            await asyncio.sleep(step)
            elapsed += step

    async def _wait_for_postback(self, page: Page, delay: float = 1.0):
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        await self._wait_for_loading_to_finish(page, max_wait=15.0)
        await asyncio.sleep(delay)

    async def _dismiss_popup_if_present(self, page: Page):
        popup = page.locator("#popup").first
        if await popup.count() == 0:
            return
        try:
            if not await popup.is_visible():
                return
        except Exception:
            return

        close_candidates = popup.locator(
            "button, a, input[type='button'], input[type='submit'], [class*='close'], [id*='close']"
        )
        for i in range(await close_candidates.count()):
            btn = close_candidates.nth(i)
            try:
                if await btn.is_visible():
                    await btn.click(timeout=2000)
                    self._log("Dismissed initial portal popup.", step="NAVIGATE")
                    await self._wait_for_postback(page, delay=0.5)
                    return
            except Exception:
                continue

        try:
            await page.evaluate(
                "() => { const p = document.querySelector('#popup'); if (p) { p.style.display = 'none'; p.remove(); } }"
            )
            self._log("Hid blocking #popup overlay.", step="NAVIGATE")
        except Exception:
            pass

    async def _resolve_active_page(self, context: BrowserContext, current_page: Page) -> Page:
        pages = [p for p in context.pages if not p.is_closed()]
        if not pages:
            return current_page
        newest = pages[-1]
        if newest != current_page:
            newest.set_default_timeout(30000)
            await self._wait_for_postback(newest, delay=0.8)
            self._log(f"Switched to active page: {newest.url}", step="NAVIGATE")
            return newest
        return current_page

    async def _click_if_present(self, context: BrowserContext, page: Page, selector: str, label: str) -> Page:
        await self._wait_for_loading_to_finish(page)
        await self._dismiss_popup_if_present(page)
        loc = page.locator(selector).first
        if await loc.count() > 0 and await loc.is_visible():
            try:
                async with context.expect_page(timeout=4000) as popup_info:
                    await loc.click()
                new_page = await popup_info.value
                new_page.set_default_timeout(30000)
                self._log(f"Clicked {label} (opened new tab)", step="NAVIGATE")
                await self._wait_for_postback(new_page)
                return new_page
            except Exception:
                self._log(f"Clicked {label}", step="NAVIGATE")
                await self._wait_for_postback(page)
                return await self._resolve_active_page(context, page)
        return page

    async def _get_district_locator(self, page: Page):
        loc = page.locator(SELECTORS["district_select"]).first
        if await loc.count() == 0:
            loc = page.locator("select[id*='District' i], select[name*='District' i]").first
        return loc

    async def _list_all_district_options(self, page: Page) -> list[dict[str, str]]:
        loc = await self._get_district_locator(page)
        if await loc.count() == 0:
            return []
        options = await loc.evaluate(
            """(selectEl) => {
                const items = [];
                for (const opt of selectEl.options) {
                    const text = (opt.text || '').trim();
                    const value = (opt.value || '').trim();
                    if (!value || value === '0' || value === '-1' || text.startsWith('---') || text.toLowerCase().includes('select district')) {
                        continue;
                    }
                    items.append({ value, text });
                }
                return items;
            }"""
        )
        return options or []

    async def _select_option_if_present(
        self,
        page: Page,
        primary_selector: str,
        value: str | None,
        label: str,
        fallback_selector: str | None = None,
    ):
        if not value:
            return
        await self._wait_for_loading_to_finish(page)
        loc = page.locator(primary_selector).first
        if await loc.count() == 0 and fallback_selector:
            loc = page.locator(fallback_selector).first
        if await loc.count() == 0:
            self._log(f"Dropdown '{label}' ({primary_selector}) not found; skipping.", level="WARNING", step="FORM")
            return

        target_str = str(value).strip()
        alias_target = DISTRICT_ALIASES.get(target_str.lower())

        try:
            await loc.select_option(label=target_str)
        except Exception:
            try:
                await loc.select_option(value=target_str)
            except Exception:
                matched_value = await loc.evaluate(
                    """(selectEl, args) => {
                        const [raw, alias] = args;
                        const normRaw = raw.toLowerCase();
                        const normAlias = (alias || '').toLowerCase();
                        for (const opt of selectEl.options) {
                            const txt = (opt.text || '').trim();
                            const val = (opt.value || '').trim();
                            if (!val || val === '0' || txt.startsWith('---')) continue;
                            if (
                                txt.toLowerCase() === normRaw ||
                                val.toLowerCase() === normRaw ||
                                (normAlias && (txt.toLowerCase().includes(normAlias) || txt.includes(alias))) ||
                                txt.toLowerCase().includes(normRaw)
                            ) {
                                return opt.value;
                            }
                        }
                        return null;
                    }""",
                    [target_str, alias_target],
                )
                if matched_value:
                    await loc.select_option(value=matched_value)
                else:
                    self._log(
                        f"Could not match option '{target_str}' in '{label}' dropdown; skipping.",
                        level="WARNING",
                        step="FORM",
                    )
                    return

        self._log(f"Selected {label}: {target_str}", step="FORM")
        await self._wait_for_postback(page)

    async def _fill_if_present(
        self,
        page: Page,
        primary_selector: str,
        value: str | None,
        label: str,
        fallback_selector: str | None = None,
    ):
        if not value:
            return
        await self._wait_for_loading_to_finish(page)
        loc = page.locator(primary_selector).first
        if await loc.count() == 0 and fallback_selector:
            loc = page.locator(fallback_selector).first
        if await loc.count() == 0:
            self._log(f"Input '{label}' ({primary_selector}) not found; skipping.", level="WARNING", step="FORM")
            return
        await loc.fill(str(value))
        self._log(f"Entered {label}: {value}", step="FORM")

    async def _is_blank_png(self, png_bytes: bytes) -> bool:
        return len(png_bytes) < 500

    async def _capture_captcha_bytes(self, page: Page, img_loc) -> bytes:
        await self._wait_for_loading_to_finish(page, max_wait=15.0)

        for _ in range(12):
            try:
                ready = await img_loc.evaluate(
                    """(el) => {
                        if (el.tagName && el.tagName.toLowerCase() === 'img') {
                            return Boolean(el.complete && el.naturalWidth > 0);
                        }
                        return true;
                    }"""
                )
                if ready:
                    break
            except Exception:
                break
            await asyncio.sleep(0.5)

        try:
            await img_loc.scroll_into_view_if_needed(timeout=4000)
        except Exception:
            pass
        await asyncio.sleep(1.0)

        try:
            debug_path = self.storage_dir / f"captcha_debug_{self.job_id.hex[:8]}.png"
            await page.screenshot(path=str(debug_path), full_page=False)
        except Exception:
            pass

        try:
            shot = await img_loc.screenshot(timeout=5000)
            if shot and not await self._is_blank_png(shot):
                return shot
        except Exception:
            pass

        try:
            box = await img_loc.bounding_box(timeout=3000)
            if box and box["width"] > 0 and box["height"] > 0:
                pad = 8
                clip = {
                    "x": max(0.0, box["x"] - pad),
                    "y": max(0.0, box["y"] - pad),
                    "width": box["width"] + pad * 2,
                    "height": box["height"] + pad * 2,
                }
                return await page.screenshot(clip=clip, timeout=5000)
        except Exception:
            pass

        return await page.screenshot(full_page=False, timeout=5000)

    async def _solve_captcha(self, page: Page):
        img_loc = page.locator(SELECTORS["captcha_img"]).first
        if await img_loc.count() == 0:
            img_loc = page.locator("img[id*='Captcha' i], img[src*='Captcha' i]").first

        input_loc = page.locator(SELECTORS["captcha_input"]).first
        if await input_loc.count() == 0:
            input_loc = page.locator("input[id*='Captcha' i][type='text'], input[placeholder*='captcha' i]").first

        if await img_loc.count() == 0 or await input_loc.count() == 0:
            self._log("No CAPTCHA element detected; proceeding to submit.", step="CAPTCHA")
            return

        is_vis = False
        try:
            is_vis = await img_loc.is_visible(timeout=4000)
        except Exception:
            is_vis = False

        if not is_vis:
            self._log("CAPTCHA image is not visible on this form state; proceeding to submit.", level="WARNING", step="CAPTCHA")
            return

        self._log("CAPTCHA detected. Capturing image for dashboard verification.", step="CAPTCHA")
        img_bytes = await self._capture_captcha_bytes(page, img_loc)
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        self._set_status("AWAITING_CAPTCHA", captcha_b64=b64_img)

        solution = None
        for _ in range(120):
            await asyncio.sleep(1.5)
            db = SessionLocal()
            try:
                job = db.query(SearchJob).filter(SearchJob.id == self.job_id).first()
                if job and job.captcha_solution:
                    solution = job.captcha_solution.strip()
                    break
            finally:
                db.close()

        if not solution:
            raise TimeoutError("Timed out waiting for CAPTCHA solution from dashboard.")

        await input_loc.fill(solution)
        self._set_status("PROCESSING", captcha_b64=None)
        self._log("CAPTCHA entered; submitting search.", step="CAPTCHA")

    async def _save_record_and_pdf(self, context: BrowserContext, index_page: Page, fallback_sro: str, fallback_year: int):
        html_content = await index_page.content()
        text_content = await index_page.inner_text("body")

        doc_match = re.search(r"(?:Document\s*(?:No\.?|Number)|दस्त\s*क्रमांक)\s*[:\-]?\s*([A-Za-z0-9/\-]+)", text_content, re.I)
        sro_match = re.search(r"(?:SRO|Sub-?Registrar(?:\s*Office)?|दुय्यम\s*निबंधक)\s*[:\-]?\s*([^\n\r]+)", text_content, re.I)

        doc_number = doc_match.group(1).strip() if doc_match else f"DOC-{datetime.utcnow().strftime('%H%M%S%f')}"
        sro_name = (sro_match.group(1).strip() if sro_match else fallback_sro)[:250]

        safe_doc = re.sub(r"[^A-Za-z0-9_\-]", "_", doc_number)
        pdf_name = f"IndexII_{safe_doc}_{fallback_year}_{self.job_id.hex[:8]}.pdf"
        pdf_path = self.storage_dir / pdf_name

        try:
            await index_page.pdf(path=str(pdf_path), format="A4", print_background=True)
        except Exception:
            pdf_path = pdf_path.with_suffix(".html")
            pdf_path.write_text(html_content, encoding="utf-8")

        db = SessionLocal()
        try:
            record = (
                db.query(PropertyRecord)
                .filter(
                    PropertyRecord.sro_name == sro_name,
                    PropertyRecord.document_number == doc_number,
                    PropertyRecord.registration_year == fallback_year,
                )
                .first()
            )
            if not record:
                record = PropertyRecord(
                    sro_name=sro_name,
                    document_number=doc_number,
                    registration_year=fallback_year,
                    property_details=text_content[:4000],
                    raw_html_snapshot=html_content[:50000],
                )
                db.add(record)
                db.flush()

            job = db.query(SearchJob).filter(SearchJob.id == self.job_id).first()
            if job and record not in job.records:
                job.records.append(record)

            file_size = pdf_path.stat().st_size if pdf_path.exists() else None
            mime = "application/pdf" if pdf_path.suffix == ".pdf" else "text/html"
            doc_file = DocumentFile(
                record_id=record.id,
                file_name=pdf_path.name,
                file_path=str(pdf_path),
                mime_type=mime,
                file_size_bytes=file_size,
            )
            db.add(doc_file)
            db.commit()
            self._log(f"Saved record {doc_number} ({sro_name}) and document {pdf_path.name}.", step="EXTRACT")
        finally:
            db.close()

    async def _extract_results(self, context: BrowserContext, page: Page, criteria: dict, district_label: str | None = None) -> int:
        fallback_sro = district_label or criteria.get("sro") or criteria.get("district") or "IGR Maharashtra"
        try:
            fallback_year = int(criteria.get("year") or datetime.utcnow().year)
        except ValueError:
            fallback_year = datetime.utcnow().year

        page_num = 1
        total_processed = 0

        while True:
            self._log(f"Scanning search results page {page_num} ({fallback_sro}).", step="RESULTS")
            rows = page.locator(SELECTORS["results_rows"])
            row_count = await rows.count()

            for i in range(row_count):
                row = rows.nth(i)
                link = row.locator(SELECTORS["index_ii_link"]).first
                if await link.count() == 0:
                    continue

                async with context.expect_page(timeout=8000) as popup_info:
                    await link.click()
                    try:
                        popup = await popup_info.value
                    except Exception:
                        popup = None

                target_page = popup if popup else page
                await self._wait_for_postback(target_page, delay=0.6)
                await self._save_record_and_pdf(context, target_page, fallback_sro, fallback_year)
                total_processed += 1

                if popup and not popup.is_closed():
                    await popup.close()

            next_pager = page.locator(f"a[href*='Page${page_num + 1}']").first
            if await next_pager.count() == 0:
                break
            page_num += 1
            await next_pager.click()
            await self._wait_for_postback(page)

        self._log(f"Saved {total_processed} Index-II record(s) for {fallback_sro}.", step="EXTRACT")
        return total_processed

    async def _submit_and_extract_for_district(self, context: BrowserContext, page: Page, criteria: dict, district_label: str | None = None) -> int:
        await self._select_option_if_present(
            page,
            SELECTORS["area_select"],
            criteria.get("area"),
            "Area / Village",
            fallback_selector="select[id*='Village' i], select[id*='Area' i]",
        )
        await self._fill_if_present(
            page,
            SELECTORS["area_name_input"],
            criteria.get("area_name"),
            "Area Name",
            fallback_selector="input[id*='Village' i], input[id*='Area' i]",
        )
        await self._fill_if_present(
            page,
            SELECTORS["attribute_value_input"],
            criteria.get("attribute_value") or criteria.get("property_number") or criteria.get("document_number"),
            "Search Value",
            fallback_selector="input[id*='Property' i], input[id*='Attribute' i], input[id*='Doc' i]",
        )

        await self._solve_captcha(page)

        await self._wait_for_loading_to_finish(page)
        submit_btn = page.locator(SELECTORS["search_btn"]).first
        if await submit_btn.count() == 0:
            submit_btn = page.locator("input[type='submit'][value*='Search' i], input[type='submit'][value*='शोध' i], input[id*='Search' i]").first
        await submit_btn.click(timeout=15000)
        self._log(f"Submitted search form ({district_label or 'default'}). Waiting for results.", step="SEARCH")
        await self._wait_for_postback(page, delay=1.5)

        return await self._extract_results(context, page, criteria, district_label=district_label)

    async def run(self):
        self._set_status("PROCESSING", error=None)
        self._log("Launching Playwright Chromium browser.", step="INIT")
        search_type, criteria, _ = self._get_job_snapshot()

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=settings.headless)
                context = await browser.new_context()
                page = await context.new_page()
                page.set_default_timeout(30000)

                await self._goto_with_retry(page, settings.igr_portal_url, attempts=3)
                await self._wait_for_postback(page)
                await self._dismiss_popup_if_present(page)

                region = criteria.get("region")
                if region == "MUMBAI":
                    page = await self._click_if_present(context, page, SELECTORS["region_mumbai"], "Mumbai Search")
                elif region == "URBAN":
                    page = await self._click_if_present(context, page, SELECTORS["region_urban"], "Urban Areas Search")
                elif region == "REST":
                    page = await self._click_if_present(context, page, SELECTORS["region_rest_of_mh"], "Rest of Maharashtra Search")

                page = await self._resolve_active_page(context, page)

                await self._select_option_if_present(
                    page,
                    SELECTORS["year_select"],
                    criteria.get("year"),
                    "Year",
                    fallback_selector="select[id*='Year' i], select[name*='Year' i]",
                )

                raw_district = criteria.get("district")
                scan_all_districts = bool(criteria.get("all_districts")) or (
                    isinstance(raw_district, str) and raw_district.strip().lower() in {"all", "*", "all districts"}
                )

                total_records = 0
                if scan_all_districts:
                    district_options = await self._list_all_district_options(page)
                    self._log(f"Scanning across all {len(district_options)} districts.", step="FORM")
                    for idx, opt in enumerate(district_options, start=1):
                        d_text = opt["text"]
                        d_val = opt["value"]
                        self._log(f"[{idx}/{len(district_options)}] Selecting District: {d_text}", step="FORM")
                        await self._select_option_if_present(
                            page,
                            SELECTORS["district_select"],
                            d_val,
                            f"District ({d_text})",
                            fallback_selector="select[id*='District' i], select[name*='District' i]",
                        )
                        total_records += await self._submit_and_extract_for_district(context, page, criteria, district_label=d_text)
                else:
                    await self._select_option_if_present(
                        page,
                        SELECTORS["district_select"],
                        raw_district,
                        "District",
                        fallback_selector="select[id*='District' i], select[name*='District' i]",
                    )
                    total_records += await self._submit_and_extract_for_district(context, page, criteria, district_label=raw_district)

                self._log(f"Finished extraction. Total Index-II records saved: {total_records}.", step="COMPLETE")
                await browser.close()

            self._set_status("COMPLETED")
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            self._log(err_msg, level="ERROR", step="FAILED")
            self._set_status("FAILED", error=err_msg)


async def execute_igr_job(job_id: UUID):
    bot = IGRPortalBot(job_id)
    await bot.run()
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

    async def _wait_for_postback(self, page: Page, delay: float = 0.8):
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await asyncio.sleep(delay)

    async def _select_option_if_present(self, page: Page, selector: str, value: str | None, label: str):
        if not value:
            return
        loc = page.locator(selector).first
        if await loc.count() == 0:
            self._log(f"Field '{label}' ({selector}) not visible on current form; skipping.", level="WARNING", step="FORM")
            return
        try:
            await loc.select_option(label=value)
        except Exception:
            await loc.select_option(value=value)
        self._log(f"Selected {label}: {value}", step="FORM")
        await self._wait_for_postback(page)

    async def _fill_if_present(self, page: Page, selector: str, value: str | None, label: str):
        if not value:
            return
        loc = page.locator(selector).first
        if await loc.count() == 0:
            self._log(f"Input '{label}' ({selector}) not visible on current form; skipping.", level="WARNING", step="FORM")
            return
        await loc.fill(str(value))
        self._log(f"Entered {label}: {value}", step="FORM")

    async def _solve_captcha(self, page: Page):
        img_loc = page.locator(SELECTORS["captcha_img"]).first
        input_loc = page.locator(SELECTORS["captcha_input"]).first

        if await img_loc.count() == 0 or await input_loc.count() == 0:
            self._log("No CAPTCHA element detected; proceeding to submit.", step="CAPTCHA")
            return

        self._log("CAPTCHA detected. Capturing image for manual verification.", step="CAPTCHA")
        img_bytes = await img_loc.screenshot()
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        self._set_status("AWAITING_CAPTCHA", captcha_b64=b64_img)

        # Poll for up to 3 minutes while keeping the browser session alive
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
            # Fallback if popup does not support page.pdf() directly
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

    async def _extract_results(self, context: BrowserContext, page: Page, criteria: dict):
        fallback_sro = criteria.get("sro") or criteria.get("district") or "IGR Maharashtra"
        try:
            fallback_year = int(criteria.get("year") or datetime.utcnow().year)
        except ValueError:
            fallback_year = datetime.utcnow().year

        page_num = 1
        total_processed = 0

        while True:
            self._log(f"Scanning search results page {page_num}.", step="RESULTS")
            rows = page.locator(SELECTORS["results_rows"])
            row_count = await rows.count()

            for i in range(row_count):
                row = rows.nth(i)
                link = row.locator(SELECTORS["index_ii_link"]).first
                if await link.count() == 0:
                    continue

                async with context.expect_page(timeout=8000) as popup_info:
                    await link.click()
                    popup = None
                    try:
                        popup = await popup_info.value
                    except Exception:
                        popup = None

                target_page = popup if popup else page
                await self._wait_for_postback(target_page, delay=0.5)
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

        self._log(f"Finished extraction. Total Index-II records saved: {total_processed}.", step="COMPLETE")

    async def run(self):
        self._set_status("PROCESSING", error=None)
        self._log("Launching Playwright Chromium browser.", step="INIT")
        search_type, criteria, _ = self._get_job_snapshot()

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=settings.headless)
                context = await browser.new_context()
                page = await context.new_page()
                page.set_default_timeout(25000)

                self._log(f"Navigating to {settings.igr_portal_url}", step="NAVIGATE")
                await page.goto(settings.igr_portal_url, wait_until="domcontentloaded")
                await self._wait_for_postback(page)

                region = criteria.get("region")
                if region == "MUMBAI":
                    await self._select_option_if_present(page, SELECTORS["region_mumbai"], "MUMBAI", "Region")
                elif region == "URBAN":
                    await self._select_option_if_present(page, SELECTORS["region_urban"], "URBAN", "Region")
                else:
                    await self._select_option_if_present(page, SELECTORS["region_rest_of_mh"], "REST", "Region")

                if search_type == "DOCUMENT":
                    mode_loc = page.locator(SELECTORS["mode_document"]).first
                    if await mode_loc.count() > 0:
                        await mode_loc.click()
                        await self._wait_for_postback(page)
                    await self._select_option_if_present(page, SELECTORS["year_select"], criteria.get("year"), "Year")
                    await self._select_option_if_present(page, SELECTORS["district_select"], criteria.get("district"), "District")
                    await self._select_option_if_present(page, SELECTORS["sro_select"], criteria.get("sro"), "SRO")
                    await self._fill_if_present(page, SELECTORS["doc_no_input"], criteria.get("document_number"), "Document Number")
                else:
                    mode_loc = page.locator(SELECTORS["mode_property"]).first
                    if await mode_loc.count() > 0:
                        await mode_loc.click()
                        await self._wait_for_postback(page)
                    await self._select_option_if_present(page, SELECTORS["year_select"], criteria.get("year"), "Year")
                    await self._select_option_if_present(page, SELECTORS["district_select"], criteria.get("district"), "District")
                    await self._fill_if_present(page, SELECTORS["village_input"], criteria.get("village"), "Village")
                    await self._select_option_if_present(page, SELECTORS["village_select"], criteria.get("village"), "Village")
                    await self._fill_if_present(page, SELECTORS["property_no_input"], criteria.get("property_number"), "Property / Survey / CTS No.")

                await self._solve_captcha(page)

                submit_btn = page.locator(SELECTORS["search_btn"]).first
                await submit_btn.click()
                self._log("Submitted search form. Waiting for results.", step="SEARCH")
                await self._wait_for_postback(page, delay=1.2)

                await self._extract_results(context, page, criteria)
                await browser.close()

            self._set_status("COMPLETED")
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            self._log(err_msg, level="ERROR", step="FAILED")
            self._set_status("FAILED", error=err_msg)


async def execute_igr_job(job_id: UUID):
    bot = IGRPortalBot(job_id)
    await bot.run()
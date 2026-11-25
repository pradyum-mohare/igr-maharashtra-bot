"""Playwright automation agent for the Maharashtra IGR Free Search portal."""

import asyncio
import base64
import re
from datetime import datetime
from pathlib import Path
from uuid import UUID
from playwright.async_api import async_playwright, BrowserContext, Dialog, Page

from app.automation.parser import DISTRICT_ALIASES, parse_index_ii_text
from app.automation.selectors import COMMON_SELECTORS, MODE_SELECTORS
from app.config import settings
from app.database import SessionLocal
from app.models import AutomationLog, DocumentFile, PropertyRecord, SearchJob
from app.services.storage import storage_service


class JobCancelledError(Exception):
    """Raised when the user cancels a running automation job."""


class IGRPortalBot:
    def __init__(self, job_id: UUID):
        self.job_id = job_id
        self.last_dialog_message: str | None = None

    def _log(self, message: str, level: str = "INFO", step: str | None = None):
        db = SessionLocal()
        try:
            db.add(AutomationLog(job_id=self.job_id, level=level, step=step, message=message))
            db.commit()
        finally:
            db.close()

    def _set_status(
        self,
        status: str,
        captcha_b64: str | None = None,
        error: str | None = None,
        portal_notice: str | None = None,
    ):
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
                job.captcha_refresh_requested = False
            if error is not None:
                job.error_message = error
            if portal_notice is not None:
                job.portal_notice = portal_notice
            db.commit()
        finally:
            db.close()

    def _get_job_snapshot(self) -> tuple[str, dict, bool]:
        db = SessionLocal()
        try:
            job = db.query(SearchJob).filter(SearchJob.id == self.job_id).first()
            if not job:
                raise ValueError(f"SearchJob {self.job_id} not found")
            return job.search_type, dict(job.criteria or {}), bool(job.cancel_requested)
        finally:
            db.close()

    def _check_cancelled(self):
        db = SessionLocal()
        try:
            job = db.query(SearchJob).filter(SearchJob.id == self.job_id).first()
            if job and job.cancel_requested:
                raise JobCancelledError("Job cancelled by user.")
        finally:
            db.close()

    def _attach_dialog_handler(self, page: Page):
        async def on_dialog(dialog: Dialog):
            self.last_dialog_message = dialog.message
            self._log(f"Portal dialog: {dialog.message}", level="WARNING", step="PORTAL")
            try:
                await dialog.accept()
            except Exception:
                pass

        page.on("dialog", on_dialog)

    async def _goto_with_retry(self, page: Page, url: str, attempts: int = 3):
        last_exc = None
        for attempt in range(1, attempts + 1):
            self._check_cancelled()
            try:
                self._log(f"Navigating to {url} (attempt {attempt}/{attempts})...", step="NAVIGATE")
                await page.goto(url, wait_until="commit", timeout=90000)
                await page.wait_for_load_state("domcontentloaded", timeout=60000)
                await page.wait_for_selector("#mnuSearchType, #btnMumbaisearch, #ddlDistrict", timeout=45000)
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

    async def _wait_for_loading_to_finish(self, page: Page, max_wait: float = 20.0):
        elapsed = 0.0
        step = 0.35
        while elapsed < max_wait:
            self._check_cancelled()
            still_loading = False
            try:
                still_loading = await page.evaluate(
                    """(selector) => {
                        const loaders = document.querySelectorAll(selector);
                        for (const el of loaders) {
                            const style = window.getComputedStyle(el);
                            const rect = el.getBoundingClientRect();
                            if (style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0) {
                                return true;
                            }
                        }
                        return false;
                    }""",
                    COMMON_SELECTORS["update_progress"],
                )
            except Exception:
                still_loading = False
            if not still_loading:
                break
            await asyncio.sleep(step)
            elapsed += step

    async def _wait_for_postback(
        self,
        page: Page,
        wait_selector: str | None = None,
        min_options: int | None = None,
        delay: float = 0.6,
        timeout: float = 20.0,
    ):
        await asyncio.sleep(0.35)
        await self._wait_for_loading_to_finish(page, max_wait=timeout)
        if wait_selector:
            elapsed = 0.0
            while elapsed < timeout:
                try:
                    loc = page.locator(wait_selector).first
                    if await loc.count() > 0 and await loc.is_visible():
                        if min_options is None:
                            break
                        opt_count = await loc.evaluate("el => el.options ? el.options.length : 0")
                        if opt_count >= min_options:
                            break
                except Exception:
                    pass
                await asyncio.sleep(0.35)
                elapsed += 0.35
        await asyncio.sleep(delay)

    async def _dismiss_popup_if_present(self, page: Page):
        popup = page.locator(COMMON_SELECTORS["popup"]).first
        if await popup.count() == 0:
            return
        try:
            if not await popup.is_visible():
                return
        except Exception:
            return

        close_candidates = popup.locator(COMMON_SELECTORS["popup_close"])
        for i in range(await close_candidates.count()):
            btn = close_candidates.nth(i)
            try:
                if await btn.is_visible():
                    await btn.click(timeout=2000)
                    self._log("Dismissed initial portal popup.", step="NAVIGATE")
                    await self._wait_for_postback(page, delay=0.4)
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

    async def _click_and_wait(self, page: Page, selector: str, label: str, wait_selector: str | None = None):
        await self._wait_for_loading_to_finish(page)
        await self._dismiss_popup_if_present(page)
        loc = page.locator(selector).first
        if await loc.count() == 0:
            self._log(f"Control '{label}' ({selector}) not found.", level="WARNING", step="NAVIGATE")
            return False
        await loc.click(timeout=15000)
        self._log(f"Clicked {label}.", step="NAVIGATE")
        await self._wait_for_postback(page, wait_selector=wait_selector, delay=0.6)
        return True

    async def _select_option(
        self,
        page: Page,
        selector: str,
        value: str | int | None,
        label: str,
        dependent_selector: str | None = None,
    ) -> str | None:
        if value is None or str(value).strip() == "":
            return None
        await self._wait_for_loading_to_finish(page)
        loc = page.locator(selector).first
        if await loc.count() == 0 or not await loc.is_visible():
            self._log(f"Dropdown '{label}' ({selector}) not visible; skipping.", level="WARNING", step="FORM")
            return None

        target_str = str(value).strip()
        alias_target = DISTRICT_ALIASES.get(target_str.lower())

        selected_text = None
        try:
            await loc.select_option(label=target_str)
            selected_text = target_str
        except Exception:
            try:
                await loc.select_option(value=target_str)
                selected_text = target_str
            except Exception:
                matched = await loc.evaluate(
                    """(selectEl, args) => {
                        const [raw, alias] = args;
                        const normRaw = raw.toLowerCase().trim();
                        const normAlias = (alias || '').toLowerCase().trim();
                        const stripped = normRaw.replace(/\\([^)]*\\)/g, ' ').replace(/\\s+/g, ' ').trim();
                        const tokens = stripped.split(/[^a-z0-9\\u0900-\\u097f]+/).filter(Boolean);
                        const validOpts = Array.from(selectEl.options).filter(opt => {
                            const txt = (opt.text || '').trim();
                            const val = (opt.value || '').trim();
                            return val && val !== '0' && val !== '-1' && !txt.startsWith('---');
                        });

                        for (const opt of validOpts) {
                            const txt = opt.text.trim();
                            const low = txt.toLowerCase();
                            const val = opt.value.trim().toLowerCase();
                            if (low === normRaw || val === normRaw || (normAlias && low === normAlias)) {
                                return { value: opt.value, text: txt };
                            }
                        }
                        for (const opt of validOpts) {
                            const txt = opt.text.trim();
                            const low = txt.toLowerCase();
                            if (
                                (normAlias && (low.includes(normAlias) || txt.includes(alias))) ||
                                low.includes(normRaw) ||
                                (stripped && low.includes(stripped))
                            ) {
                                return { value: opt.value, text: txt };
                            }
                        }
                        if (tokens.length > 0) {
                            for (const opt of validOpts) {
                                const txt = opt.text.trim();
                                const optTokens = txt.toLowerCase().split(/[^a-z0-9\\u0900-\\u097f]+/).filter(Boolean);
                                if (tokens.every(t => optTokens.includes(t))) {
                                    return { value: opt.value, text: txt };
                                }
                            }
                        }
                        return null;
                    }""",
                    [target_str, alias_target],
                )
                if matched:
                    await loc.select_option(value=matched["value"])
                    selected_text = matched["text"]
                else:
                    self._log(
                        f"Could not match '{target_str}' in '{label}'; skipping.",
                        level="WARNING",
                        step="FORM",
                    )
                    return None

        self._log(f"Selected {label}: {selected_text}", step="FORM")
        await self._wait_for_postback(
            page,
            wait_selector=dependent_selector,
            min_options=2 if dependent_selector else None,
            delay=0.5,
        )
        return selected_text

    async def _fill_input(self, page: Page, selector: str, value: str | None, label: str, trigger_postback: bool = False):
        if value is None or str(value).strip() == "":
            return
        await self._wait_for_loading_to_finish(page)
        loc = page.locator(selector).first
        if await loc.count() == 0 or not await loc.is_visible():
            self._log(f"Input '{label}' ({selector}) not visible; skipping.", level="WARNING", step="FORM")
            return
        text_val = str(value).strip()
        await loc.fill(text_val)
        self._log(f"Entered {label}: {text_val}", step="FORM")
        if trigger_postback:
            await loc.press("Tab")

    async def _capture_captcha_bytes(self, page: Page, img_loc) -> bytes:
        await self._wait_for_loading_to_finish(page, max_wait=15.0)
        for _ in range(12):
            try:
                ready = await img_loc.evaluate(
                    "(el) => el.tagName.toLowerCase() === 'img' ? Boolean(el.complete && el.naturalWidth > 0) : true"
                )
                if ready:
                    break
            except Exception:
                break
            await asyncio.sleep(0.4)

        try:
            await img_loc.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        await asyncio.sleep(0.5)

        try:
            shot = await img_loc.screenshot(timeout=5000)
            if shot and len(shot) >= 400:
                return shot
        except Exception:
            pass

        return await page.screenshot(full_page=False, timeout=5000)

    async def _request_manual_captcha(self, page: Page, mode_cfg: dict) -> bool:
        """Pause session and wait for manual CAPTCHA entry in dashboard (or visible browser)."""
        img_loc = page.locator(mode_cfg["captcha_img"]).first
        input_loc = page.locator(mode_cfg["captcha_input"]).first

        if await img_loc.count() == 0 or await input_loc.count() == 0 or not await img_loc.is_visible():
            self._log("No visible CAPTCHA detected on active form; proceeding.", step="CAPTCHA")
            return False

        self._log("CAPTCHA detected. Waiting for manual verification from dashboard.", step="CAPTCHA")
        img_bytes = await self._capture_captcha_bytes(page, img_loc)
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        self._set_status("AWAITING_CAPTCHA", captcha_b64=b64_img)

        solution = None
        for _ in range(200):  # up to 5 minutes
            await asyncio.sleep(1.5)
            db = SessionLocal()
            try:
                job = db.query(SearchJob).filter(SearchJob.id == self.job_id).first()
                if not job:
                    raise ValueError("SearchJob deleted while waiting for CAPTCHA.")
                if job.cancel_requested:
                    raise JobCancelledError("Job cancelled while awaiting CAPTCHA.")
                if job.captcha_refresh_requested:
                    job.captcha_refresh_requested = False
                    db.commit()
                    self._log("Refreshing CAPTCHA image on user request.", step="CAPTCHA")
                    try:
                        await img_loc.evaluate(
                            """(el) => {
                                const base = el.src.split('&r=')[0];
                                el.src = base + (base.includes('?') ? '&' : '?') + 'r=' + Date.now();
                            }"""
                        )
                    except Exception:
                        pass
                    await asyncio.sleep(0.8)
                    refreshed = await self._capture_captcha_bytes(page, img_loc)
                    job.captcha_image_base64 = base64.b64encode(refreshed).decode("utf-8")
                    db.commit()
                    continue
                if job.captcha_solution:
                    solution = job.captcha_solution.strip()
                    break
            finally:
                db.close()

            # Also check if user typed CAPTCHA directly in the visible Playwright browser
            if not settings.headless:
                try:
                    typed = (await input_loc.input_value()).strip()
                    if len(typed) >= 4:
                        self._log("Detected manual CAPTCHA entry in visible browser.", step="CAPTCHA")
                        solution = typed
                        break
                except Exception:
                    pass

        if not solution:
            raise TimeoutError("Timed out waiting for manual CAPTCHA verification.")

        await input_loc.fill(solution)
        self._set_status("PROCESSING", captcha_b64=None)
        self._log("CAPTCHA entered; submitting search.", step="CAPTCHA")
        return True

    async def _check_portal_error(self, page: Page) -> tuple[bool, str | None]:
        """Inspect dialog or error labels after search submit. Returns (is_captcha_error, msg)."""
        if self.last_dialog_message:
            msg = self.last_dialog_message
            self.last_dialog_message = None
            is_captcha = "captcha" in msg.lower() or "code" in msg.lower() or "invalid" in msg.lower()
            return is_captcha, msg

        err_loc = page.locator(COMMON_SELECTORS["error_labels"])
        for i in range(await err_loc.count()):
            el = err_loc.nth(i)
            try:
                if await el.is_visible():
                    txt = (await el.inner_text()).strip()
                    if txt:
                        is_captcha = "captcha" in txt.lower() or "verification" in txt.lower()
                        return is_captcha, txt
            except Exception:
                continue

        try:
            inline_err = await page.evaluate(
                """() => {
                    const els = document.querySelectorAll('span, div, td, p');
                    for (const el of els) {
                        const txt = (el.innerText || '').trim();
                        if (!txt || txt.length > 140) continue;
                        const low = txt.toLowerCase();
                        if (low.includes('entered captcha is incorrect') || low.includes('invalid captcha') || low.includes('no record found')) {
                            const st = window.getComputedStyle(el);
                            if (st.display !== 'none' && st.visibility !== 'hidden') return txt;
                        }
                    }
                    return null;
                }"""
            )
            if inline_err:
                return ("captcha" in inline_err.lower()), inline_err
        except Exception:
            pass

        return False, None

    def _resolve_mode_key(self, search_type: str, criteria: dict) -> str:
        if search_type == "DOCUMENT":
            return "DOCUMENT"
        region = str(criteria.get("region") or "MUMBAI").upper()
        if region == "REST":
            return "PROPERTY_REST_OF_MH"
        if region == "URBAN":
            return "PROPERTY_URBAN"
        return "PROPERTY_MUMBAI"

    async def _prepare_mode_and_fill(self, page: Page, search_type: str, criteria: dict) -> tuple[str, dict, str]:
        mode_key = self._resolve_mode_key(search_type, criteria)
        mode_cfg = MODE_SELECTORS[mode_key]

        if search_type == "DOCUMENT":
            await self._click_and_wait(
                page,
                COMMON_SELECTORS["tab_document"],
                "Document Number Tab",
                wait_selector=mode_cfg["district_select"],
            )
            doc_type = str(criteria.get("doc_type") or "Regular").strip().lower()
            radio_sel = mode_cfg["doc_type_radios"].get(doc_type)
            if radio_sel:
                radio_loc = page.locator(radio_sel).first
                if await radio_loc.count() > 0 and not await radio_loc.is_checked():
                    await self._click_and_wait(page, radio_sel, f"Document Type ({criteria.get('doc_type')})")

            selected_dist = await self._select_option(
                page,
                mode_cfg["district_select"],
                criteria.get("district"),
                "District",
                dependent_selector=mode_cfg["sro_select"],
            )
            selected_sro = await self._select_option(
                page,
                mode_cfg["sro_select"],
                criteria.get("sro"),
                "Sub-Registrar Office (SRO)",
            )
            await self._select_option(page, mode_cfg["year_select"], criteria.get("year"), "Year")
            await self._fill_input(
                page,
                mode_cfg["document_input"],
                criteria.get("document_number"),
                "Document Number",
            )
            return mode_key, mode_cfg, (selected_sro or selected_dist or criteria.get("district") or "IGR Maharashtra")

        # PROPERTY search mode
        await self._click_and_wait(page, COMMON_SELECTORS["tab_property"], "Property Details Tab")
        if mode_key == "PROPERTY_REST_OF_MH":
            await self._click_and_wait(
                page,
                COMMON_SELECTORS["region_rest_of_mh"],
                "Rest of Maharashtra",
                wait_selector=mode_cfg["district_select"],
            )
        elif mode_key == "PROPERTY_URBAN":
            await self._click_and_wait(
                page,
                COMMON_SELECTORS["region_urban"],
                "Urban Areas in Rest of Maharashtra",
                wait_selector=mode_cfg["district_select"],
            )
        else:
            await self._click_and_wait(
                page,
                COMMON_SELECTORS["region_mumbai"],
                "Mumbai",
                wait_selector=mode_cfg["district_select"],
            )

        await self._select_option(page, mode_cfg["year_select"], criteria.get("year"), "Year")

        if mode_key == "PROPERTY_MUMBAI":
            selected_dist = await self._select_option(
                page,
                mode_cfg["district_select"],
                criteria.get("district") or "Mumbai",
                "District",
            )
            area_query = criteria.get("area_name") or criteria.get("village") or criteria.get("area")
            if area_query:
                await self._fill_input(page, mode_cfg["area_name_input"], str(area_query)[:20], "Village Search Text", trigger_postback=True)
                await self._wait_for_postback(page, wait_selector=mode_cfg["village_select"], min_options=2, delay=0.5)
            selected_village = await self._select_option(
                page,
                mode_cfg["village_select"],
                criteria.get("village") or criteria.get("area") or criteria.get("area_name"),
                "Area / Village",
            )
            prop_val = criteria.get("property_number") or criteria.get("attribute_value")
            await self._fill_input(page, mode_cfg["property_input"], prop_val, "Property / Survey / CTS No.")
            return mode_key, mode_cfg, (selected_village or selected_dist or "Mumbai")

        # Rest of Maharashtra / Urban
        selected_dist = await self._select_option(
            page,
            mode_cfg["district_select"],
            criteria.get("district"),
            "District",
            dependent_selector=mode_cfg["tahsil_select"],
        )
        selected_tahsil = await self._select_option(
            page,
            mode_cfg["tahsil_select"],
            criteria.get("tahsil"),
            "Tahsil",
            dependent_selector=mode_cfg["village_select"],
        )
        selected_village = await self._select_option(
            page,
            mode_cfg["village_select"],
            criteria.get("village") or criteria.get("area"),
            "Village",
        )
        prop_val = criteria.get("property_number") or criteria.get("attribute_value")
        await self._fill_input(page, mode_cfg["property_input"], prop_val, "Property / Survey / CTS No.")
        label = selected_village or selected_tahsil or selected_dist or criteria.get("district") or "IGR Maharashtra"
        return mode_key, mode_cfg, label

    async def _save_record(
        self,
        index_page: Page | None,
        row_cells: list[str],
        criteria: dict,
        fallback_sro: str,
        fallback_year: int,
        downloaded_file: tuple[Path, str] | None = None,
    ) -> bool:
        html_content = ""
        text_content = " | ".join(row_cells)
        if index_page is not None:
            try:
                html_content = await index_page.content()
                text_content = await index_page.inner_text("body")
            except Exception:
                pass

        parsed = parse_index_ii_text(
            text=text_content,
            row_cells=row_cells,
            fallback_sro=criteria.get("sro") or fallback_sro,
            fallback_year=fallback_year,
        )

        # Optional client-side party name filter if user provided party_name
        party_filter = (criteria.get("party_name") or "").strip().lower()
        if party_filter:
            searchable = f"{text_content} {' '.join(row_cells)}".lower()
            if party_filter not in searchable:
                self._log(
                    f"Skipping document {parsed['document_number']} (does not match party filter '{criteria.get('party_name')}').",
                    step="EXTRACT",
                )
                return False

        safe_doc = re.sub(r"[^A-Za-z0-9_\-]", "_", parsed["document_number"])
        saved_path: Path | None = None
        mime_type = "application/pdf"

        if downloaded_file is not None:
            saved_path, mime_type = downloaded_file
        elif index_page is not None:
            pdf_name = f"IndexII_{safe_doc}_{parsed['registration_year']}_{self.job_id.hex[:8]}.pdf"
            pdf_path = storage_service.build_path(pdf_name)
            try:
                await index_page.pdf(path=str(pdf_path), format="A4", print_background=True)
                saved_path = pdf_path
                mime_type = "application/pdf"
            except Exception:
                html_name = f"IndexII_{safe_doc}_{parsed['registration_year']}_{self.job_id.hex[:8]}.html"
                saved_path = storage_service.save_text(html_name, html_content)
                mime_type = "text/html"

        db = SessionLocal()
        try:
            record = (
                db.query(PropertyRecord)
                .filter(
                    PropertyRecord.sro_name == parsed["sro_name"],
                    PropertyRecord.document_number == parsed["document_number"],
                    PropertyRecord.registration_year == parsed["registration_year"],
                )
                .first()
            )
            district_val = criteria.get("district")
            tahsil_or_village = criteria.get("village") or criteria.get("area") or criteria.get("tahsil")
            if not record:
                record = PropertyRecord(
                    district=str(district_val)[:150] if district_val else None,
                    tahsil_or_village=str(tahsil_or_village)[:255] if tahsil_or_village else None,
                    sro_name=parsed["sro_name"],
                    document_number=parsed["document_number"],
                    registration_year=parsed["registration_year"],
                    registration_date=parsed["registration_date"],
                    article_type=parsed["article_type"],
                    consideration_amount=parsed["consideration_amount"],
                    market_value=parsed["market_value"],
                    party_details=parsed["party_details"],
                    property_details=parsed["property_details"],
                    survey_cts_number=parsed["survey_cts_number"],
                    raw_html_snapshot=html_content[:50000] if html_content else None,
                )
                db.add(record)
                db.flush()
            else:
                # Enrich existing record if fields were previously missing
                for attr in (
                    "registration_date",
                    "article_type",
                    "consideration_amount",
                    "market_value",
                    "party_details",
                    "survey_cts_number",
                ):
                    if getattr(record, attr) is None and parsed[attr] is not None:
                        setattr(record, attr, parsed[attr])

            job = db.query(SearchJob).filter(SearchJob.id == self.job_id).first()
            if job and record not in job.records:
                job.records.append(record)

            if saved_path and saved_path.exists():
                doc_file = DocumentFile(
                    record_id=record.id,
                    file_name=saved_path.name,
                    file_path=str(saved_path),
                    mime_type=mime_type,
                    file_size_bytes=saved_path.stat().st_size,
                )
                db.add(doc_file)

            db.commit()
            self._log(
                f"Saved record {parsed['document_number']} ({parsed['sro_name']})"
                + (f" with document {saved_path.name}" if saved_path else "."),
                step="EXTRACT",
            )
            return True
        finally:
            db.close()

    async def _open_and_extract_row(
        self,
        context: BrowserContext,
        page: Page,
        row_index: int,
        row_cells: list[str],
        criteria: dict,
        fallback_sro: str,
        fallback_year: int,
    ) -> bool:
        rows = page.locator(COMMON_SELECTORS["results_rows"])
        row = rows.nth(row_index)
        link = row.locator(COMMON_SELECTORS["index_ii_link"]).first
        if await link.count() == 0:
            return False

        existing_pages = set(context.pages)
        downloaded_file: tuple[Path, str] | None = None
        popup_page: Page | None = None

        # Listen safely for download OR new tab OR same-page navigation
        download_task = asyncio.create_task(page.wait_for_event("download", timeout=6000))
        page_task = asyncio.create_task(context.wait_for_event("page", timeout=6000))
        try:
            await link.click(timeout=10000)
            done, pending = await asyncio.wait(
                {download_task, page_task},
                timeout=6.0,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
            if download_task in done and not download_task.exception():
                dl = download_task.result()
                fname = dl.suggested_filename or f"IndexII_{self.job_id.hex[:8]}.pdf"
                dest = storage_service.build_path(fname)
                await dl.save_as(str(dest))
                mime = "application/pdf" if dest.suffix.lower() == ".pdf" else "application/octet-stream"
                downloaded_file = (dest, mime)
            elif page_task in done and not page_task.exception():
                popup_page = page_task.result()
        finally:
            for t in (download_task, page_task):
                if not t.done():
                    t.cancel()

        if popup_page is None:
            new_pages = [p for p in context.pages if p not in existing_pages and not p.is_closed()]
            if new_pages:
                popup_page = new_pages[-1]

        if downloaded_file is not None:
            return await self._save_record(None, row_cells, criteria, fallback_sro, fallback_year, downloaded_file=downloaded_file)

        if popup_page is not None:
            popup_page.set_default_timeout(30000)
            await self._wait_for_postback(popup_page, delay=0.5)
            try:
                return await self._save_record(popup_page, row_cells, criteria, fallback_sro, fallback_year)
            finally:
                if not popup_page.is_closed():
                    await popup_page.close()

        # Fallback: check if same-page navigation or inline detail modal opened
        await self._wait_for_postback(page, delay=0.5)
        return await self._save_record(page, row_cells, criteria, fallback_sro, fallback_year)

    async def _extract_results(self, context: BrowserContext, page: Page, criteria: dict, fallback_sro: str) -> int:
        try:
            fallback_year = int(criteria.get("year") or datetime.utcnow().year)
        except ValueError:
            fallback_year = datetime.utcnow().year

        table = page.locator(COMMON_SELECTORS["results_table"]).first
        if await table.count() == 0 or not await table.is_visible():
            self._log("No results table rendered for search criteria.", level="WARNING", step="RESULTS")
            return 0

        page_num = 1
        total_saved = 0

        while True:
            self._check_cancelled()
            self._log(f"Scanning search results page {page_num} ({fallback_sro}).", step="RESULTS")
            rows = page.locator(COMMON_SELECTORS["results_rows"])
            row_count = await rows.count()

            for i in range(row_count):
                self._check_cancelled()
                row = rows.nth(i)
                if await row.locator(COMMON_SELECTORS["index_ii_link"]).count() == 0:
                    continue
                row_cells = await row.locator("td").all_inner_texts()
                if await self._open_and_extract_row(context, page, i, row_cells, criteria, fallback_sro, fallback_year):
                    total_saved += 1

            next_pager = page.locator(f"a[href*='Page${page_num + 1}']").first
            if await next_pager.count() == 0:
                break
            page_num += 1
            await next_pager.click()
            await self._wait_for_postback(page, delay=0.8)

        self._log(f"Saved {total_saved} Index-II record(s) for {fallback_sro}.", step="EXTRACT")
        return total_saved

    async def run(self):
        self._set_status("PROCESSING", error=None, portal_notice=None)
        self._log("Launching Playwright Chromium browser.", step="INIT")
        search_type, criteria, cancelled = self._get_job_snapshot()
        if cancelled:
            self._set_status("CANCELLED")
            return

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=settings.headless)
                context = await browser.new_context(accept_downloads=True)
                page = await context.new_page()
                page.set_default_timeout(30000)
                self._attach_dialog_handler(page)

                await self._goto_with_retry(page, settings.igr_portal_url, attempts=3)
                await self._wait_for_postback(page, delay=0.8)
                await self._dismiss_popup_if_present(page)

                _, mode_cfg, label = await self._prepare_mode_and_fill(page, search_type, criteria)

                # Up to 3 CAPTCHA verification attempts in the same live session
                submitted_ok = False
                for attempt in range(1, 4):
                    self._check_cancelled()
                    await self._request_manual_captcha(page, mode_cfg)
                    await self._wait_for_loading_to_finish(page)
                    self.last_dialog_message = None

                    submit_btn = page.locator(mode_cfg["search_btn"]).first
                    await submit_btn.click(timeout=15000)
                    self._log(f"Submitted search (attempt {attempt}/3). Waiting for results.", step="SEARCH")
                    await self._wait_for_postback(page, delay=1.2)

                    is_captcha_err, portal_msg = await self._check_portal_error(page)
                    if is_captcha_err:
                        self._log(
                            f"Portal rejected CAPTCHA ({portal_msg}). Prompting user to retry.",
                            level="WARNING",
                            step="CAPTCHA",
                        )
                        continue
                    if portal_msg:
                        self._set_status("PROCESSING", portal_notice=portal_msg)
                        self._log(f"Portal message: {portal_msg}", level="INFO", step="RESULTS")
                    submitted_ok = True
                    break

                if not submitted_ok:
                    raise ValueError("CAPTCHA verification failed after 3 attempts.")

                total_records = await self._extract_results(context, page, criteria, fallback_sro=label)
                if total_records == 0:
                    self._set_status(
                        "COMPLETED",
                        portal_notice="Search completed cleanly, but no matching records were returned by the portal.",
                    )
                else:
                    self._set_status("COMPLETED")
                self._log(f"Finished job. Total records saved: {total_records}.", step="COMPLETE")
                await browser.close()
        except JobCancelledError as exc:
            self._log(str(exc), level="WARNING", step="CANCELLED")
            self._set_status("CANCELLED", error=str(exc))
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            self._log(err_msg, level="ERROR", step="FAILED")
            self._set_status("FAILED", error=err_msg)


async def execute_igr_job(job_id: UUID):
    bot = IGRPortalBot(job_id)
    await bot.run()

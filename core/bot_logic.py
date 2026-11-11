from __future__ import annotations

import random
from typing import Any

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from config import (
    CAPTCHA_WAIT_SECONDS,
    DEFAULT_BOT_CONFIG,
    DRIVER_RETRY_COUNT,
    PROGRESS_FILE,
    WORD_LIST,
)
from core.browser import setup_edge_driver
from core.models import JobResult, JobStatus, RuntimeConfig
from core.progress_store import WebProgressStore
from core.runtime import CancelledError, RuntimeControl
from core.waydroid_logic import WaydroidBot


class BotLogic(RuntimeControl):
    """Core web flow.

    The selectors, search counts, timing values and workflow order are kept from the
    tested v5.2 project. Reliability concerns (checkpointing, cancellation, result
    states and driver lifecycle) are handled around that flow.
    """

    def __init__(self, logger_callback, stop_event):
        super().__init__(stop_event, logger_callback)
        self.cfg = dict(DEFAULT_BOT_CONFIG)
        self.progress = WebProgressStore(PROGRESS_FILE)

    def update_config(self, new_config: dict[str, Any]) -> None:
        merged = dict(self.cfg)
        merged.update(new_config)
        validated = RuntimeConfig.from_mapping(merged)
        self.cfg = validated.as_dict()

    def check_stop(self) -> None:
        try:
            super().check_stop()
        except CancelledError:
            self.log("🛑 Đã nhận lệnh DỪNG.")
            raise

    # ------------------------------------------------------------------
    # Progress compatibility facade
    # ------------------------------------------------------------------
    def save_progress(self, acc: str, mode: str, index: int, points: Any) -> None:
        self.progress.save_stage(acc, mode, index, points, status="RUNNING")

    def load_progress(self) -> dict[str, Any]:
        return self.progress.load()

    def clear_progress(self) -> None:
        self.progress.clear()

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def get_random_query(self) -> str:
        return f"{random.choice(WORD_LIST)} {random.choice(WORD_LIST)} {random.choice(WORD_LIST)}"

    def human_typing(self, element, text: str) -> None:
        try:
            ActionChains(driver).move_to_element(element).pause(0.2).click().perform()
            self.sleep_random(0.5, 1.0)
        except CancelledError:
            raise
        except Exception:
            pass

        for char in text:
            self.check_stop()
            element.send_keys(char)
            self.sleep_random(float(self.cfg["type_min"]), float(self.cfg["type_max"]))

        self.sleep_random(1.0, float(self.cfg["think_time"]))
        element.send_keys(Keys.RETURN)

    def dismiss_popups(self, driver) -> None:
        """Legacy popup cleanup kept to avoid changing the tested browsing flow."""
        try:
            driver.execute_script(
                """
                let msBtns = document.querySelectorAll('#bnp_btn_accept, #acceptButton, .c-dialog-button');
                msBtns.forEach(btn => btn.click());

                let allBtns = document.querySelectorAll('button, a[role="button"]');
                let keywords = ['xác nhận', 'chấp nhận', 'đồng ý', 'bỏ qua', 'accept', 'agree', 'got it', 'close', 'tiếp tục', 'continue'];
                for (let btn of allBtns) {
                    let txt = (btn.innerText || '').toLowerCase().trim();
                    if (keywords.some(kw => txt.includes(kw)) && btn.offsetParent !== null) {
                        btn.click();
                    }
                }

                let overlays = document.querySelectorAll('[role="dialog"], .modal, .overlay, div[style*="z-index"]');
                for (let obj of overlays) {
                    let zIndex = window.getComputedStyle(obj).zIndex;
                    if (zIndex !== 'auto' && parseInt(zIndex) > 100) {
                        obj.style.display = 'none';
                        obj.style.visibility = 'hidden';
                    }
                }
                """
            )
            self.sleep(1.5)
        except CancelledError:
            raise
        except Exception:
            pass

    def get_current_points_pc(self, driver):
        self.dismiss_popups(driver)
        wait = WebDriverWait(driver, 5)
        selectors = [
            '[data-tag="RewardsHeader.Counter"]',
            '#id_rc',
            '.rw-qs-cnt',
            '.points-container',
        ]
        for selector in selectors:
            try:
                elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                raw_txt = elem.text.strip()
                if not raw_txt:
                    continue
                if '/' in raw_txt:
                    current_val = raw_txt.split('/')[0].strip()
                    if current_val.replace(',', '').isdigit():
                        return current_val
                elif raw_txt.replace(',', '').isdigit():
                    return raw_txt
            except Exception:
                continue
        return "N/A"

    def get_points_from_dashboard(self, driver) -> int:
        self.dismiss_popups(driver)
        scan_js = """
            let selectors = ['p.text-pageHeader', '[id*="rewards-dashboard-count"]', '.pointsDetail'];
            for (let sel of selectors) {
                let el = document.querySelector(sel);
                if (el && el.innerText) {
                    let cleanNum = el.innerText.replace(/,/g, '').trim();
                    if (/^\\d+$/.test(cleanNum)) return parseInt(cleanNum);
                }
            }

            let elements = document.querySelectorAll('p, span, h1, h2, h3, div');
            let maxFontSize = 0;
            let probablePoints = -1;
            for (let el of elements) {
                if (el.children.length === 0) {
                    let text = el.innerText || el.textContent;
                    if (text) {
                        let cleanText = text.replace(/,/g, '').trim();
                        if (/^\\d+$/.test(cleanText) && cleanText.length >= 2) {
                            let style = window.getComputedStyle(el);
                            let fontSize = parseFloat(style.fontSize);
                            if (fontSize > maxFontSize && fontSize > 16) {
                                maxFontSize = fontSize;
                                probablePoints = parseInt(cleanText);
                            }
                        }
                    }
                }
            }
            return probablePoints;
        """

        for attempt in range(15):
            self.check_stop()
            try:
                points = driver.execute_script(scan_js)
                if points and points > 0:
                    self.log(f"✅ Quét đc: {points} sau {attempt}s")
                    return int(points)
            except Exception:
                pass
            self.sleep(1)

        self.log("🔄 Web bị văng đăng nhập. Đang tìm và click nút 'Sign in'...")
        try:
            clicked = driver.execute_script(
                """
                let elements = document.querySelectorAll('a, button, span, div');
                for (let el of elements) {
                    let txt = (el.innerText || '').toLowerCase().trim();
                    if (txt === 'sign in' || txt === 'đăng nhập') {
                        el.click();
                        return true;
                    }
                }
                return false;
                """
            )
            if clicked:
                self.log("👉 Đã click Sign in, chờ 8s để tải lại điểm...")
                self.sleep(8)
                for _ in range(5):
                    self.check_stop()
                    points = driver.execute_script(scan_js)
                    if points and points > 0:
                        self.log(f"✅ Quét đc: {points} sau khi phục hồi đăng nhập")
                        return int(points)
                    self.sleep(1)
        except CancelledError:
            raise
        except Exception:
            pass

        self.log("⚠️ Không lấy được điểm dù đã thử Sign in.")
        return -1

    def handle_captcha(self, driver) -> bool:
        """Pause for manual CAPTCHA handling; no automated challenge solving."""
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            markers = ("verify you are human", "giải quyết thử thách", "bước cuối cùng")
            if any(marker in page_text for marker in markers):
                self.log("⚠️ PHÁT HIỆN CAPTCHA!")
                self.log("👉 Đang tạm dừng. Hãy xử lý CAPTCHA thủ công hoặc Refresh (F5)...")
                for _ in range(CAPTCHA_WAIT_SECONDS):
                    self.check_stop()
                    self.sleep(1)
                    current_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                    if "verify you are human" not in current_text and "giải quyết thử thách" not in current_text:
                        self.log("✅ CAPTCHA không còn hiển thị, tiếp tục.")
                        self.sleep(3)
                        return True
                self.log("❌ Quá thời gian chờ CAPTCHA. Bỏ qua lượt này.")
                return False
        except CancelledError:
            raise
        except Exception:
            pass
        return True

    # ------------------------------------------------------------------
    # PC flow
    # ------------------------------------------------------------------
    def perform_pc_loop(self, driver, acc_name: str, count: int, start_from: int = 0, saved_last_points="N/A") -> tuple[bool, Any]:
        mode_name = "PC"
        self.log(f"► {mode_name}: Bắt đầu từ {start_from}/{count}")
        driver.get("https://www.bing.com")
        self.sleep(5)
        wait = WebDriverWait(driver, 15)

        last_verified_points = self.get_current_points_pc(driver)
        if last_verified_points == "N/A":
            self.log("⚠️ Cảnh báo: Không đọc được điểm PC (Mạng chậm hoặc chưa đăng nhập).")
            last_verified_points = saved_last_points if saved_last_points != "N/A" else "Unknown"

        self.log(f"💰 Điểm khởi đầu: {last_verified_points}")

        for i in range(start_from, count):
            self.check_stop()
            if not self.handle_captcha(driver):
                driver.get("https://www.bing.com")
                self.sleep(5)
                continue

            try:
                if i > 0 and i % int(self.cfg["check_interval"]) == 0:
                    current_points = self.get_current_points_pc(driver)
                    if current_points != "N/A" and last_verified_points != "N/A":
                        if current_points == last_verified_points:
                            self.log(f"🛑 ĐÃ ĐẠT GIỚI HẠN PC: {current_points}. Dừng!")
                            break
                        self.log(f"📈 PC Tăng: {last_verified_points} -> {current_points}")
                        last_verified_points = current_points

                query = self.get_random_query()
                try:
                    search_box = wait.until(EC.element_to_be_clickable((By.NAME, "q")))
                    search_box.clear()
                    self.human_typing(search_box, query)
                except TimeoutException:
                    driver.get("https://www.bing.com")
                    continue

                self.log(f"[{mode_name} {i + 1}/{count}] 🔍 '{query}' | 💰 {last_verified_points}")
                self.save_progress(acc_name, mode_name, i + 1, last_verified_points)
                self.sleep_random(float(self.cfg["read_min"]), float(self.cfg["read_max"]))
                if random.random() > 0.5:
                    driver.execute_script(f"window.scrollTo(0, {random.randint(100, 500)});")
            except CancelledError:
                raise
            except Exception as exc:
                self.log(f"⚠️ PC lượt {i + 1} gặp lỗi: {exc}")
                driver.get("https://www.bing.com")
                self.sleep(5)

        return True, last_verified_points

    # ------------------------------------------------------------------
    # Mobile flow
    # ------------------------------------------------------------------
    def perform_mobile_loop_2tab(self, driver, acc_name: str, count: int, start_from: int = 0, saved_last_points="N/A") -> tuple[bool, Any]:
        mode_name = "MOBILE"
        self.log(f"► {mode_name} (2-TAB): Bắt đầu từ {start_from}/{count}")

        driver.get("https://www.bing.com")
        self.sleep(3)
        tab_search = driver.current_window_handle
        driver.switch_to.new_window("tab")
        tab_dashboard = driver.current_window_handle
        driver.get("https://rewards.bing.com/")
        self.sleep(7)

        driver.switch_to.window(tab_dashboard)
        last_dashboard_points = self.get_points_from_dashboard(driver)
        if last_dashboard_points == -1 and str(saved_last_points).lstrip('-').isdigit():
            last_dashboard_points = int(saved_last_points)
        self.log(f"💰 Tổng điểm (Dashboard): {last_dashboard_points}")

        driver.switch_to.window(tab_search)
        wait = WebDriverWait(driver, 15)

        for i in range(start_from, count):
            self.check_stop()
            if not self.handle_captcha(driver):
                driver.get("https://www.bing.com")
                self.sleep(5)
                continue

            try:
                if i > 0 and i % int(self.cfg["check_interval"]) == 0:
                    driver.switch_to.window(tab_dashboard)
                    driver.refresh()
                    self.sleep(4)
                    current_total = self.get_points_from_dashboard(driver)

                    if current_total != -1:
                        self.log(f"📊 Điểm Dashboard hiện tại: {current_total}")
                        if last_dashboard_points == -1:
                            self.log("✅ Đã khôi phục nhận diện điểm thành công.")
                            last_dashboard_points = current_total
                        elif current_total == last_dashboard_points:
                            self.log("🛑 GIỚI HẠN: Tổng điểm không tăng. Mobile xong!")
                            break
                        else:
                            self.log(f"📈 Tăng: +{current_total - last_dashboard_points} điểm.")
                            last_dashboard_points = current_total
                    else:
                        self.log("⚠️ Không quét được điểm đợt này, bỏ qua check...")

                    driver.switch_to.window(tab_search)

                query = self.get_random_query()
                try:
                    search_box = wait.until(EC.element_to_be_clickable((By.NAME, "q")))
                    search_box.clear()
                    self.human_typing(search_box, query)
                except TimeoutException:
                    driver.get("https://www.bing.com")
                    continue

                self.log(f"[{mode_name} {i + 1}/{count}] 🔍 '{query}'")
                self.save_progress(acc_name, mode_name, i + 1, str(last_dashboard_points))
                self.sleep_random(float(self.cfg["read_min"]), float(self.cfg["read_max"]))
                if random.random() > 0.5:
                    driver.execute_script(f"window.scrollTo(0, {random.randint(100, 500)});")
            except CancelledError:
                raise
            except Exception as exc:
                self.log(f"⚠️ Mobile lượt {i + 1} gặp lỗi: {exc}")
                try:
                    driver.switch_to.window(tab_search)
                except Exception:
                    pass
                driver.get("https://www.bing.com")
                self.sleep(5)

        return True, last_dashboard_points

    # ------------------------------------------------------------------
    # Orchestration / result state
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_quit(driver) -> None:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

    def _run_web_stage(self, acc_name: str, mode: str, total: int) -> JobResult:
        checkpoint = self.progress.get_stage(acc_name, mode)
        if checkpoint.get("status") == "SUCCESS":
            self.log(f"⏩ {mode} đã xong. Bỏ qua.")
            return JobResult(JobStatus.SKIPPED, account=acc_name, stage=mode, message="Checkpoint đã hoàn thành")

        start_idx = int(checkpoint.get("index", 0) or 0)
        last_pts = checkpoint.get("last_points", "N/A")
        retry_count = 0

        while retry_count < DRIVER_RETRY_COUNT:
            self.check_stop()
            driver = None
            try:
                is_mobile = mode == "MOBILE"
                driver = setup_edge_driver(is_mobile=is_mobile, profile_name=acc_name, logger=self.log)
                self.sleep(3)

                if mode == "PC":
                    success, final_points = self.perform_pc_loop(driver, acc_name, total, start_idx, last_pts)
                else:
                    success, final_points = self.perform_mobile_loop_2tab(driver, acc_name, total, start_idx, last_pts)

                if not success:
                    return JobResult.failed(acc_name, mode, f"{mode} trả về trạng thái thất bại")

                self.progress.mark_stage_completed(acc_name, mode, total, final_points)
                return JobResult.success(acc_name, mode, f"{mode} hoàn thành")

            except CancelledError:
                return JobResult.cancelled(acc_name, mode)
            except WebDriverException as exc:
                retry_count += 1
                self.log(f"🔄 Restart Driver ({retry_count}/{DRIVER_RETRY_COUNT}): {exc}")
                if retry_count >= DRIVER_RETRY_COUNT:
                    return JobResult.failed(acc_name, mode, f"Driver lỗi sau {DRIVER_RETRY_COUNT} lần thử")
                checkpoint = self.progress.get_stage(acc_name, mode)
                start_idx = int(checkpoint.get("index", 0) or 0)
                last_pts = checkpoint.get("last_points", "N/A")
                self.sleep(10)
            except Exception as exc:
                self.log(f"❌ Lỗi Fatal [{mode}]: {exc}")
                return JobResult.failed(acc_name, mode, str(exc))
            finally:
                self._safe_quit(driver)

        return JobResult.failed(acc_name, mode, "Không thể hoàn thành stage")

    def run_bot_safe(
        self,
        acc_name: str,
        run_pc: bool = True,
        run_mobile: bool = True,
        run_waydroid: bool = False,
        waydroid_only: bool = False,
    ) -> JobResult:
        try:
            self.check_stop()

            if waydroid_only:
                self.log(f"🤖 CHẾ ĐỘ: CHỈ CHẠY WAYDROID CHO {acc_name}")
                result = WaydroidBot(self.log, self.stop_event).run_waydroid_flow(acc_name)
                if result.ok:
                    self.progress.mark_profile_completed(acc_name)
                return result

            if run_pc:
                result = self._run_web_stage(acc_name, "PC", int(self.cfg["pc_count"]))
                if not result.ok:
                    return result

            if run_mobile:
                result = self._run_web_stage(acc_name, "MOBILE", int(self.cfg["mobile_count"]))
                if not result.ok:
                    return result

            if run_waydroid:
                way_result = WaydroidBot(self.log, self.stop_event).run_waydroid_flow(acc_name)
                if not way_result.ok:
                    return way_result

            self.progress.mark_profile_completed(acc_name)
            self.log(f"✅ HOÀN THÀNH TOÀN BỘ: {acc_name}")
            return JobResult.success(acc_name, "ALL", "Hoàn thành toàn bộ profile")

        except CancelledError:
            return JobResult.cancelled(acc_name, "ALL")
        except Exception as exc:
            self.log(f"❌ Lỗi không dự kiến [{acc_name}]: {exc}")
            return JobResult.failed(acc_name, "ALL", str(exc))

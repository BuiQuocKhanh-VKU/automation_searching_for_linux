from __future__ import annotations

import random
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from config import (
    ADB_COMMAND_TIMEOUT,
    BING_APP_PACKAGE,
    PROFILES_LIST,
    WAYDROID_CHECKIN_X,
    WAYDROID_CHECKIN_Y,
    WAYDROID_EMAILS,
    WAYDROID_IP,
    WAYDROID_NEWS_COUNT,
    WAYDROID_PROGRESS_FILE,
)
from core.models import JobResult, JobStatus
from core.progress_store import WaydroidProgressStore
from core.runtime import CancelledError, RuntimeControl


class ADBError(RuntimeError):
    pass


class WaydroidFlowError(RuntimeError):
    pass


class WaydroidBot(RuntimeControl):
    def __init__(self, logger_callback, stop_event):
        super().__init__(stop_event, logger_callback)
        self.progress = WaydroidProgressStore(WAYDROID_PROGRESS_FILE)

    def check_stop(self) -> None:
        try:
            super().check_stop()
        except CancelledError:
            self.log("🛑 DỪNG WAYDROID.")
            raise

    def adb_command(self, cmd: str, *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
        self.check_stop()
        if not shutil.which("adb"):
            raise ADBError("Không tìm thấy lệnh adb trong PATH")

        full_cmd = ["adb", "-s", WAYDROID_IP, *cmd.split()]
        try:
            result = subprocess.run(
                full_cmd,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=ADB_COMMAND_TIMEOUT,
            )
        except subprocess.TimeoutExpired as exc:
            raise ADBError(f"ADB timeout: {cmd}") from exc

        if check and result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise ADBError(f"ADB lỗi ({result.returncode}) [{cmd}]: {stderr or 'không có stderr'}")
        return result

    def tap(self, cord: tuple[int, int]) -> None:
        x, y = cord
        self.adb_command(f"shell input tap {x} {y}")
        self.sleep_random(1.0, 1.5)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 500) -> None:
        self.adb_command(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
        self.sleep_random(1.0, 2.0)

    def back(self) -> None:
        self.adb_command("shell input keyevent 4")
        self.sleep(1.5)

    def dump_ui_xml(self) -> str:
        try:
            self.adb_command("shell uiautomator dump /sdcard/window_dump.xml")
            result = self.adb_command("shell cat /sdcard/window_dump.xml", capture=True)
            return result.stdout or ""
        except CancelledError:
            raise
        except Exception as exc:
            self.log(f"⚠️ Lỗi lấy UI dump: {exc}")
            return ""

    @staticmethod
    def find_element_center(xml_data: str, text: str = "", resource_id: str = "") -> tuple[int, int] | None:
        if not xml_data:
            return None
        try:
            root = ET.fromstring(xml_data)
            for node in root.iter("node"):
                node_text = node.attrib.get("text", "")
                node_desc = node.attrib.get("content-desc", "")
                node_id = node.attrib.get("resource-id", "")

                match = False
                if resource_id and resource_id in node_id:
                    match = True
                elif text and (text.lower() in node_text.lower() or text.lower() in node_desc.lower()):
                    match = True

                if match:
                    bounds_str = node.attrib.get("bounds")
                    if bounds_str:
                        coords = re.findall(r"\d+", bounds_str)
                        if len(coords) == 4:
                            x1, y1, x2, y2 = map(int, coords)
                            return (x1 + x2) // 2, (y1 + y2) // 2
        except ET.ParseError:
            return None
        return None

    def tap_element(self, text: str = "", resource_id: str = "", wait_time: float = 2) -> bool:
        self.log(f"🔍 Đang tìm element: {text or resource_id}...")
        xml_data = self.dump_ui_xml()
        center_coords = self.find_element_center(xml_data, text, resource_id)
        if center_coords:
            self.tap(center_coords)
            self.sleep(wait_time)
            return True
        self.log(f"❌ Không tìm thấy '{text or resource_id}' trên màn hình.")
        return False

    def tap_webview_relative(self, percent_x: float, percent_y: float) -> bool:
        xml_data = self.dump_ui_xml()
        if not xml_data:
            return False
        try:
            root = ET.fromstring(xml_data)
            for node in root.iter("node"):
                if node.attrib.get("resource-id") == "com.microsoft.bing:id/edge_web_view":
                    bounds_str = node.attrib.get("bounds")
                    if bounds_str:
                        coords = re.findall(r"\d+", bounds_str)
                        if len(coords) == 4:
                            x1, y1, x2, y2 = map(int, coords)
                            width = x2 - x1
                            height = y2 - y1
                            target_x = x1 + int(width * percent_x)
                            target_y = y1 + int(height * percent_y)
                            self.tap((target_x, target_y))
                            return True
        except ET.ParseError as exc:
            self.log(f"⚠️ Lỗi tính tọa độ tương đối: {exc}")
        return False

    def start_waydroid_and_connect(self) -> None:
        self.check_stop()
        if not shutil.which("waydroid"):
            raise WaydroidFlowError("Không tìm thấy lệnh waydroid trong PATH")
        if not shutil.which("adb"):
            raise WaydroidFlowError("Không tìm thấy lệnh adb trong PATH")

        self.log("🚀 Khởi động Bing trực tiếp qua Waydroid...")
        subprocess.Popen(
            ["waydroid", "app", "launch", BING_APP_PACKAGE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.sleep(15)

        self.log(f"🔌 Kết nối ADB: {WAYDROID_IP}")
        try:
            connect = subprocess.run(
                ["adb", "connect", WAYDROID_IP],
                capture_output=True,
                text=True,
                timeout=ADB_COMMAND_TIMEOUT,
            )
        except subprocess.TimeoutExpired as exc:
            raise ADBError("adb connect timeout") from exc
        if connect.returncode != 0:
            raise ADBError((connect.stderr or connect.stdout or "adb connect failed").strip())
        self.sleep(2)

        state = self.adb_command("get-state", capture=True)
        if "device" not in (state.stdout or "").lower():
            raise ADBError(f"ADB device chưa online: {(state.stdout or '').strip()}")

    # Compatibility names retained for external callers.
    def load_progress(self) -> dict:
        return self.progress.load().get("profiles", {})

    def save_progress(self, acc_name: str, status: str) -> None:
        self.progress.set_status(acc_name, status)

    def read_news_articles(self, target_count: int = 10) -> int:
        self.log(f"📰 Bắt đầu đọc {target_count} bài báo ngẫu nhiên...")
        read_articles: set[str] = set()
        read_count = 0
        scroll_attempts = 0

        while read_count < target_count and scroll_attempts < 15:
            self.check_stop()
            xml_data = self.dump_ui_xml()
            if not xml_data:
                # v5.2 không tăng biến này nên có thể lặp vô hạn nếu UI dump lỗi liên tục.
                scroll_attempts += 1
                self.sleep(1)
                continue

            available_articles: list[tuple[str, tuple[int, int]]] = []
            try:
                root = ET.fromstring(xml_data)
                for node in root.iter("node"):
                    node_id = node.attrib.get("resource-id", "")
                    if node_id == "com.microsoft.bing:id/sa_hp_native_list_item_container":
                        desc = node.attrib.get("content-desc", "").strip()
                        bounds = node.attrib.get("bounds", "")
                        if desc and desc not in read_articles and bounds:
                            coords = re.findall(r"\d+", bounds)
                            if len(coords) == 4:
                                x1, y1, x2, y2 = map(int, coords)
                                if y1 > 100 and y2 < 950:
                                    available_articles.append(
                                        (desc, ((x1 + x2) // 2, (y1 + y2) // 2))
                                    )
            except ET.ParseError:
                available_articles = []

            if available_articles:
                article_desc, coords = random.choice(available_articles)
                self.log(f"   [{read_count + 1}/{target_count}] Đọc: {article_desc[:30]}...")
                self.tap(coords)
                read_articles.add(article_desc)
                read_count += 1
                scroll_attempts = 0
                self.sleep_random(3.0, 4.5)
                self.back()
                self.sleep(2.5)
            else:
                self.swipe(960, 800, 960, 300, duration=600)
                self.sleep(2.5)
                scroll_attempts += 1

        if read_count >= target_count:
            self.log(f"✅ Đã hoàn thành đọc đủ {target_count} bài báo.")
        else:
            self.log(f"⚠️ Dừng đọc báo ở {read_count}/{target_count} do không tìm thấy bài mới.")
        return read_count

    def _tap_target_email(self, target_email: str) -> bool:
        xml_data = self.dump_ui_xml()
        if not xml_data or not target_email:
            return False
        try:
            root = ET.fromstring(xml_data)
            for node in root.iter("node"):
                if node.attrib.get("resource-id") == "com.microsoft.bing:id/profile_display_email":
                    node_email = node.attrib.get("text", "").lower()
                    if target_email.lower() in node_email:
                        bounds_str = node.attrib.get("bounds")
                        if not bounds_str:
                            continue
                        coords = re.findall(r"\d+", bounds_str)
                        if len(coords) == 4:
                            x1, y1, x2, y2 = map(int, coords)
                            self.tap(((x1 + x2) // 2, (y1 + y2) // 2))
                            return True
        except ET.ParseError:
            return False
        return False

    @staticmethod
    def _require(ok: bool, message: str) -> None:
        if not ok:
            raise WaydroidFlowError(message)

    def run_waydroid_flow(self, acc_name: str) -> JobResult:
        if self.progress.status(acc_name) == "DONE":
            self.log(f"⏩ Waydroid: {acc_name} đã hoàn thành hôm nay, bỏ qua.")
            return JobResult(JobStatus.SKIPPED, account=acc_name, stage="WAYDROID", message="Đã hoàn thành hôm nay")

        try:
            self.start_waydroid_and_connect()
            self.check_stop()

            self.log("🎁 Đang mở tab Rewards...")
            self._require(self.tap_element(text="Rewards"), "Không mở được tab Rewards")
            self.sleep(3)

            self.log("✔️ Đang click Check-in (Sử dụng Tọa độ Tương đối)...")
            checkin_hits = 0
            for pct_x in WAYDROID_CHECKIN_X:
                self.check_stop()
                if self.tap_webview_relative(pct_x, WAYDROID_CHECKIN_Y):
                    checkin_hits += 1
                self.sleep(0.4)
            if checkin_hits == 0:
                raise WaydroidFlowError("Không tìm thấy WebView để thực hiện Check-in")

            self.log("🏠 Quay lại màn hình chính để đọc báo...")
            self._require(self.tap_element(text="Home"), "Không quay về được Home")
            self.sleep(1)

            self.read_news_articles(target_count=WAYDROID_NEWS_COUNT)

            self.log("🔄 Chuẩn bị đổi tài khoản...")
            self.log("🏠 Nhấn Home lần nữa để cuộn lên đầu...")
            self._require(self.tap_element(text="Home"), "Không tìm thấy Home trước khi đổi tài khoản")
            self.sleep(1)

            self.log("👤 Mở menu Profile...")
            self._require(
                self.tap_element(resource_id="com.microsoft.bing:id/sa_profile_button"),
                "Không mở được menu Profile",
            )
            self.sleep(1)

            self.log("⚙️ Mở danh sách tài khoản...")
            self._require(
                self.tap_element(resource_id="com.microsoft.bing:id/sapphire_profile_account_hint"),
                "Không mở được danh sách tài khoản",
            )
            self.sleep(1)

            try:
                curr_idx = PROFILES_LIST.index(acc_name)
                next_idx = (curr_idx + 1) % len(PROFILES_LIST)
                next_acc = PROFILES_LIST[next_idx]
                target_email = WAYDROID_EMAILS.get(next_acc, "")
            except (ValueError, ZeroDivisionError):
                target_email = ""

            if not target_email:
                raise WaydroidFlowError(f"Không có WAYDROID_EMAILS cho profile sau {acc_name}")

            self.log(f"👉 Chọn tài khoản tiếp theo: {target_email}")
            self._require(self._tap_target_email(target_email), f"Không tìm thấy email {target_email}")

            self.log(f"✅ Xác nhận Switch now sang {target_email}...")
            self._require(self.tap_element(text="Switch now", wait_time=0), "Không tìm thấy nút Switch now")

            # Chỉ ghi DONE sau khi toàn bộ các bước quan trọng đã xác nhận thành công.
            self.save_progress(acc_name, "DONE")
            self.log(f"✅ Hoàn thành Waydroid cho {acc_name}")

            try:
                self.adb_command(f"shell am force-stop {BING_APP_PACKAGE}")
            finally:
                self.sleep(1)

            return JobResult.success(acc_name, "WAYDROID", "Waydroid hoàn thành")

        except CancelledError:
            self.log("🛑 Đã dừng luồng Waydroid.")
            return JobResult.cancelled(acc_name, "WAYDROID")
        except Exception as exc:
            self.log(f"❌ Lỗi Waydroid: {exc}")
            return JobResult.failed(acc_name, "WAYDROID", str(exc))

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable

from selenium import webdriver
from selenium.webdriver.edge.service import Service

from config import (
    DRIVER_FILENAME,
    EDGE_USER_DATA_DIR,
    EDGE_SOURCE_USER_DATA_DIR,
    MS_EDGE_BINARY,
    PAGE_LOAD_TIMEOUT,
    MOBILE_WINDOW_SIZE,
    MOBILE_USER_AGENT,
    MOBILE_PLATFORM,
    MOBILE_ACCEPT_LANGUAGE,
    MOBILE_PLATFORM_VERSION,
)

from core.edge_profiles import prepare_profile

Logger = Callable[[str], None]


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_driver() -> str | None:
    local_driver = _project_root() / DRIVER_FILENAME
    if local_driver.exists():
        return str(local_driver)
    return shutil.which(DRIVER_FILENAME)


def _build_options(is_mobile: bool, profile_name: str) -> webdriver.EdgeOptions:
    options = webdriver.EdgeOptions()
    options.binary_location = MS_EDGE_BINARY

    # Dữ liệu profile riêng cho bot để Edge cho phép kết nối DevTools.
    options.add_argument(f"--user-data-dir={EDGE_USER_DATA_DIR}")
    options.add_argument(f"--profile-directory={profile_name}")

    # Các cờ ổn định trên Ubuntu/Linux.
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # Để Edge chọn cổng trống, tránh xung đột với phiên đang chạy.
    options.add_argument("--remote-debugging-port=0")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    if is_mobile:
        options.add_argument(f"--window-size={MOBILE_WINDOW_SIZE}")
    else:
        options.add_argument("--start-maximized")

    return options


def _apply_mobile_emulation(driver: webdriver.Edge) -> None:
    """Keep the legacy mobile rendering parameters used by the tested project."""
    driver.execute_cdp_cmd(
        "Network.setUserAgentOverride",
        {
            "userAgent": MOBILE_USER_AGENT,
            "platform": MOBILE_PLATFORM,
            "acceptLanguage": MOBILE_ACCEPT_LANGUAGE,
            "userAgentMetadata": {
                "brands": [{"brand": "Safari", "version": "16"}],
                "fullVersionList": [{"brand": "Safari", "version": "16.6"}],
                "fullVersion": "16.6",
                "platform": "iOS",
                "platformVersion": MOBILE_PLATFORM_VERSION,
                "architecture": "",
                "model": MOBILE_PLATFORM,
                "mobile": True,
                "bitness": "",
            },
        },
    )


def setup_edge_driver(is_mobile: bool, profile_name: str, logger: Logger | None = None):
    if not os.path.exists(MS_EDGE_BINARY):
        message = f"Không thấy Microsoft Edge tại: {MS_EDGE_BINARY}"
        if logger:
            logger(f"❌ {message}")
        raise FileNotFoundError(message)

    if prepare_profile(profile_name, EDGE_SOURCE_USER_DATA_DIR, EDGE_USER_DATA_DIR) and logger:
        logger(f"📂 Đã nhập profile {profile_name}; nếu cần, đăng nhập lại bằng chế độ Thủ công.")
    options = _build_options(is_mobile, profile_name)
    driver_path = _resolve_driver()

    try:
        if driver_path:
            if logger:
                logger(f"🧩 EdgeDriver: {driver_path}")
            driver = webdriver.Edge(service=Service(executable_path=driver_path), options=options)
        else:
            # Selenium Manager tự tìm/tải driver phù hợp nếu msedgedriver không có sẵn.
            if logger:
                logger("🧩 Không thấy msedgedriver cục bộ; dùng Selenium Manager.")
            driver = webdriver.Edge(options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        if is_mobile:
            _apply_mobile_emulation(driver)
        return driver
    except Exception as exc:
        if logger:
            logger(f"❌ Lỗi khởi động Edge: {exc}")
        raise

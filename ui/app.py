from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import flet as ft

from config import (
    DEFAULT_BOT_CONFIG,
    PROFILE_SWITCH_DELAY,
    PROFILES_LIST,
    PROFILE_LABELS,
    SHUTDOWN_COUNTDOWN_SECONDS,
)
from core.bot_logic import BotLogic
from core.browser import setup_edge_driver
from core.models import JobResult, JobStatus, RuntimeConfig
from core.runtime import CancelledError
from core.progress_store import DashboardProgressStore


APP_VERSION = "v6.0 Clean"


def _build_file_logger() -> logging.Logger:
    logger = logging.getLogger("msbot")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "run.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger


def build_ui(page: ft.Page):
    page.title = f"Auto claim 🍗🍟 {APP_VERSION}"
    # Neutral surfaces and a single accent keep the desktop UI quiet and readable.
    background = "#F5F5F7"
    surface = "#FFFFFF"
    sidebar_surface = "#ECEEF1"
    field_surface = "#F8F9FB"
    border = "#DDE1E6"
    text_primary = "#20242B"
    text_secondary = "#626B78"
    accent = "#2563A6"
    success = "#28734C"
    danger = "#B43B3B"

    # SF Pro is installed on this desktop; Text is designed for small UI labels.
    ui_font = "SF Pro Text"
    body_style = ft.TextStyle(
        font_family=ui_font,
        font_family_fallback=["Noto Sans", "sans-serif"],
        size=14,
        weight=ft.FontWeight.W_500,
        letter_spacing=0,
        color=text_primary,
    )
    caption_style = body_style.copy(size=13, color=text_secondary)
    label_style = ft.TextStyle(
        font_family=ui_font,
        size=14,
        weight=ft.FontWeight.W_600,
        letter_spacing=0,
    )

    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=accent,
        font_family=ui_font,
        text_theme=ft.TextTheme(
            body_large=body_style,
            body_medium=body_style,
            body_small=caption_style,
            title_large=label_style.copy(size=20),
            title_medium=label_style.copy(size=16),
            title_small=label_style,
            label_large=label_style,
            label_medium=caption_style,
            label_small=caption_style,
        ),
        scaffold_bgcolor=background,
    )
    page.padding = 0
    page.spacing = 0
    page.bgcolor = background

    # Ubuntu desktop: giữ kích thước tối thiểu để layout không vỡ/pixel hóa.
    page.window.width = 1180
    page.window.height = 820
    page.window.min_width = 900
    page.window.min_height = 620

    stop_event = threading.Event()
    cancel_shutdown_event = threading.Event()
    ui_lock = threading.RLock()
    run_lock = threading.Lock()
    run_generation = 0
    file_logger = _build_file_logger()

    # ------------------------------------------------------------
    # Header state
    # ------------------------------------------------------------
    status_text = ft.Text("SẴN SÀNG", size=13, weight=ft.FontWeight.W_600, color=text_secondary)
    active_profile_text = ft.Text("Chưa chạy", size=14, color=text_primary)

    log_list = ft.ListView(expand=True, spacing=6, auto_scroll=True)

    def schedule_update() -> None:
        try:
            page.schedule_update()
        except Exception:
            try:
                page.update()
            except Exception:
                pass

    def log_message(msg: str, level: int = logging.INFO) -> None:
        file_logger.log(level, msg)
        with ui_lock:
            t = datetime.now().strftime("%H:%M:%S")
            log_list.controls.append(
                ft.Text(
                    f"[{t}] {msg}",
                    font_family=ui_font,
                    weight=ft.FontWeight.W_500,
                    size=13,
                    color=text_primary,
                    selectable=True,
                )
            )
            if len(log_list.controls) > 500:
                del log_list.controls[:50]
        refresh_profile_status()

    bot_logic = BotLogic(log_message, stop_event)

    # ------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------
    mode_radio = ft.RadioGroup(
        content=ft.Column(
            controls=[
                ft.Radio(value="Auto All", label="Tất cả tài khoản", label_style=body_style),
                ft.Radio(value="Single", label="Một tài khoản", label_style=body_style),
                ft.Radio(value="Manual", label="Thủ công", label_style=body_style),
            ],
            spacing=4,
        ),
        value="Auto All",
    )

    acc_dropdown = ft.Dropdown(
        label="Tài khoản",
        options=[ft.DropdownOption(key=x, text=PROFILE_LABELS.get(x, x)) for x in PROFILES_LIST],
        value=PROFILES_LIST[0] if PROFILES_LIST else None,
        text_size=14,
        text_style=body_style,
        label_style=caption_style,
        filled=True,
        fill_color=surface,
        border_color=border,
        focused_border_color=accent,
        border_radius=10,
        content_padding=12,
    )

    def set_active_profile(profile: str) -> None:
        active_profile_text.value = PROFILE_LABELS.get(profile, profile)
        acc_dropdown.value = profile

    def on_account_change(_):
        set_active_profile(str(acc_dropdown.value))
        schedule_update()

    acc_dropdown.on_change = on_account_change

    def option_switch(label: str, value: bool) -> ft.Switch:
        return ft.Switch(
            label=label,
            value=value,
            active_color=accent,
            label_text_style=body_style,
        )

    mobile_switch = option_switch("Chỉ chạy Mobile", False)
    shutdown_switch = option_switch("Tắt máy khi hoàn thành", False)

    btn_start = ft.FilledButton(
        content="Bắt đầu",
        icon=ft.Icons.PLAY_ARROW_ROUNDED,
        width=240,
        height=44,
        style=ft.ButtonStyle(
            bgcolor={ft.ControlState.DISABLED: "#E1E5EB", ft.ControlState.DEFAULT: accent},
            color={ft.ControlState.DISABLED: text_secondary, ft.ControlState.DEFAULT: surface},
            shape=ft.RoundedRectangleBorder(radius=10),
            text_style=label_style,
        ),
    )
    btn_stop = ft.OutlinedButton(
        content="Dừng lại",
        icon=ft.Icons.STOP_ROUNDED,
        width=240,
        height=44,
        disabled=True,
        style=ft.ButtonStyle(
            color={ft.ControlState.DISABLED: text_secondary, ft.ControlState.DEFAULT: danger},
            side=ft.BorderSide(1, border),
            shape=ft.RoundedRectangleBorder(radius=10),
            text_style=label_style,
        ),
    )

    input_refs: dict[str, ft.TextField] = {}

    def create_field(label: str, key: str, default) -> ft.TextField:
        field = ft.TextField(
            label=label,
            value=str(default),
            height=52,
            text_size=14,
            text_style=body_style,
            color=text_primary,
            label_style=caption_style,
            border_color=border,
            focused_border_color=accent,
            border_radius=8,
            filled=True,
            fill_color=field_surface,
            content_padding=12,
        )
        input_refs[key] = field
        return field

    # Runtime defaults intentionally match the tested v5.2 UI values.
    config_grid = ft.ResponsiveRow(
        controls=[
            ft.Container(
                col={"xs": 12, "sm": 4},
                content=ft.Column(
                    controls=[
                        ft.Text("Số lượng", size=13, color=text_secondary, weight=ft.FontWeight.W_600),
                        create_field("Lượt PC", "pc_count", DEFAULT_BOT_CONFIG["pc_count"]),
                        create_field("Lượt Mobile", "mobile_count", DEFAULT_BOT_CONFIG["mobile_count"]),
                        create_field("Chu kỳ kiểm tra", "check_interval", DEFAULT_BOT_CONFIG["check_interval"]),
                    ],
                    spacing=8,
                ),
            ),
            ft.Container(
                col={"xs": 12, "sm": 4},
                content=ft.Column(
                    controls=[
                        ft.Text("Gõ & suy nghĩ (giây)", size=13, color=text_secondary, weight=ft.FontWeight.W_600),
                        create_field("Gõ tối thiểu", "type_min", DEFAULT_BOT_CONFIG["type_min"]),
                        create_field("Gõ tối đa", "type_max", DEFAULT_BOT_CONFIG["type_max"]),
                        create_field("Thời gian suy nghĩ", "think_time", DEFAULT_BOT_CONFIG["think_time"]),
                    ],
                    spacing=8,
                ),
            ),
            ft.Container(
                col={"xs": 12, "sm": 4},
                content=ft.Column(
                    controls=[
                        ft.Text("Đọc (giây)", size=13, color=text_secondary, weight=ft.FontWeight.W_600),
                        create_field("Đọc tối thiểu", "read_min", DEFAULT_BOT_CONFIG["read_min"]),
                        create_field("Đọc tối đa", "read_max", DEFAULT_BOT_CONFIG["read_max"]),
                    ],
                    spacing=8,
                ),
            ),
        ],
        spacing=12,
        run_spacing=12,
    )

    def get_ui_config() -> RuntimeConfig:
        values: dict[str, object] = {}
        for key, field in input_refs.items():
            raw = (field.value or "").strip()
            values[key] = DEFAULT_BOT_CONFIG[key] if not raw else raw
        return RuntimeConfig.from_mapping(values)

    # ------------------------------------------------------------
    # Status dashboard
    # ------------------------------------------------------------
    profile_status_controls: dict[str, dict[str, ft.Text]] = {}
    dashboard_progress = DashboardProgressStore(
        str(Path(__file__).resolve().parent.parent / "dashboard_progress.json")
    )
    rows: list[ft.DataRow] = []
    for profile in PROFILES_LIST:
        web_status = ft.Text("—", size=13)
        mobile_status = ft.Text("—", size=13)
        profile_status_controls[profile] = {"web": web_status, "mobile": mobile_status}
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(PROFILE_LABELS.get(profile, profile), size=13, weight=ft.FontWeight.W_600, color=text_primary)),
                    ft.DataCell(web_status),
                    ft.DataCell(mobile_status),
                ]
            )
        )

    status_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Tài khoản", size=13, color=text_secondary)),
            ft.DataColumn(ft.Text("Web", size=13, color=text_secondary)),
            ft.DataColumn(ft.Text("Mobile", size=13, color=text_secondary)),
        ],
        rows=rows,
        column_spacing=20,
        horizontal_margin=12,
        heading_row_color=field_surface,
        horizontal_lines=ft.BorderSide(1, border),
        heading_row_height=40,
        data_row_min_height=42,
        data_row_max_height=48,
    )

    def refresh_profile_status() -> None:
        web_doc = bot_logic.progress.load()
        web_profiles = dashboard_progress.merge_profiles(web_doc.get("profiles", {})).get("profiles", {})
        for profile in PROFILES_LIST:
            pdata = web_profiles.get(profile, {})
            stages = pdata.get("stages", {})
            if stages.get("PC", {}).get("status") == "SUCCESS":
                web_label = "Hoàn tất"
            elif stages:
                parts = []
                for stage in ("PC",):
                    if stage in stages:
                        s = stages[stage]
                        state = s.get("status")
                        if state == "SUCCESS":
                            parts.append(f"{stage}✓")
                        elif state == "FAILED":
                            parts.append(f"{stage}⚠")
                        else:
                            parts.append(f"{stage}:{s.get('index', 0)}")
                web_label = "  ".join(parts) or "—"
            else:
                web_label = "—"

            profile_status_controls[profile]["web"].value = web_label
            mobile = stages.get("MOBILE", {})
            mobile_state = mobile.get("status")
            if mobile_state == "SUCCESS":
                mobile_label = "Hoàn tất"
            elif mobile_state == "FAILED":
                mobile_label = "Lỗi ⚠"
            elif mobile_state == "CANCELLED":
                mobile_label = "Đã dừng"
            elif mobile:
                mobile_label = f"Lượt {mobile.get('index', 0)}"
            else:
                mobile_label = "—"
            profile_status_controls[profile]["mobile"].value = mobile_label
        schedule_update()

    # ------------------------------------------------------------
    # Shutdown dialog
    # ------------------------------------------------------------
    countdown_text = ft.Text(str(SHUTDOWN_COUNTDOWN_SECONDS), size=42, weight=ft.FontWeight.BOLD, color=danger)

    def on_cancel_shutdown(_):
        cancel_shutdown_event.set()
        try:
            page.pop_dialog()
        except Exception:
            pass
        log_message("🛑 Đã hủy lệnh tự động tắt máy.")

    shutdown_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Tự động tắt máy", weight=ft.FontWeight.BOLD),
        content=ft.Column(
            controls=[
                ft.Text("Hệ thống sẽ tắt nguồn sau:"),
                countdown_text,
                ft.Text("giây nữa..."),
            ],
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        actions=[ft.FilledButton(content="Hủy tắt máy", on_click=on_cancel_shutdown)],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )

    def maybe_shutdown(auto_shutdown: bool, result: JobResult) -> None:
        # Chỉ poweroff khi toàn bộ run SUCCESS thực sự.
        if not auto_shutdown or result.status != JobStatus.SUCCESS or stop_event.is_set():
            return

        cancel_shutdown_event.clear()
        log_message("⚠️ Hoàn thành thành công. Bắt đầu đếm ngược tắt máy...")
        try:
            page.show_dialog(shutdown_dialog)
        except Exception:
            pass
        schedule_update()

        for i in range(SHUTDOWN_COUNTDOWN_SECONDS, 0, -1):
            if cancel_shutdown_event.wait(1):
                return
            countdown_text.value = str(i - 1)
            schedule_update()

        try:
            page.pop_dialog()
        except Exception:
            pass
        log_message("🔌 Đang ngắt điện...")
        try:
            subprocess.run(["systemctl", "poweroff"], check=False)
        except Exception as exc:
            log_message(f"❌ Không thể gọi systemctl poweroff: {exc}", logging.ERROR)

    # ------------------------------------------------------------
    # Run orchestration
    # ------------------------------------------------------------
    def set_running(running: bool) -> None:
        btn_start.disabled = running
        btn_stop.disabled = not running
        acc_dropdown.disabled = running
        status_text.value = "ĐANG CHẠY" if running else "SẴN SÀNG"
        status_text.color = success if running else text_secondary
        schedule_update()

    def run_manual(acc: str) -> JobResult:
        driver = None
        try:
            log_message(f"🔧 Manual: {acc}")
            driver = setup_edge_driver(False, acc, logger=log_message)
            driver.get("https://rewards.bing.com")
            while not stop_event.wait(0.5):
                pass
            return JobResult.cancelled(acc, "MANUAL", "Manual mode đã đóng theo nút DỪNG")
        except Exception as exc:
            return JobResult.failed(acc, "MANUAL", str(exc))
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

    def run_wrapper(mode: str, acc: str, mobile_only: bool, auto_shutdown: bool, generation: int):
        overall = JobResult.success(stage="SESSION", message="Hoàn thành")
        try:
            if mode == "Auto All":
                log_message("🚀 AUTO ALL STARTING...")
                start_idx = bot_logic.progress.first_incomplete_index(PROFILES_LIST)
                if start_idx >= len(PROFILES_LIST):
                    # Trường hợp app crash ngay sau profile cuối nhưng trước khi clear session.
                    log_message("✅ Checkpoint cho thấy tất cả profile đã hoàn thành.")
                else:
                    for i in range(start_idx, len(PROFILES_LIST)):
                        if stop_event.is_set():
                            overall = JobResult.cancelled(stage="SESSION")
                            break

                        curr = PROFILES_LIST[i]
                        set_active_profile(curr)
                        refresh_profile_status()
                        log_message(f"👤 PROFILE: {curr}")

                        result = bot_logic.run_bot_safe(
                            curr,
                            run_pc=not mobile_only,
                            run_mobile=True,
                        )
                        refresh_profile_status()
                        if not result.ok:
                            overall = result
                            break

                        if i < len(PROFILES_LIST) - 1:
                            log_message(f"💤 Sleep {PROFILE_SWITCH_DELAY}s...")
                            try:
                                bot_logic.sleep(PROFILE_SWITCH_DELAY)
                            except CancelledError:
                                overall = JobResult.cancelled(curr, "WAIT")
                                break

                if overall.ok and not stop_event.is_set():
                    # Giữ hành vi v5.2: khi Auto All hoàn tất tự nhiên, lần chạy sau bắt đầu mới.
                    bot_logic.clear_progress()
                    overall = JobResult.success(stage="SESSION", message="Auto All hoàn thành")

            elif mode == "Single":
                set_active_profile(acc)
                # Nếu profile đã hoàn thành và app trước đó đóng trước bước cleanup,
                # Single run mới được xem là một run mới giống hành vi v5.2.
                if bot_logic.progress.is_profile_completed(acc):
                    bot_logic.progress.clear_profile(acc)
                overall = bot_logic.run_bot_safe(
                    acc,
                    run_pc=not mobile_only,
                    run_mobile=True,
                )
                if overall.ok:
                    bot_logic.progress.clear_profile(acc)

            elif mode == "Manual":
                set_active_profile(acc)
                overall = run_manual(acc)
            else:
                overall = JobResult.failed(stage="SESSION", message=f"Mode không hợp lệ: {mode}")

            refresh_profile_status()
            if overall.status == JobStatus.SUCCESS:
                log_message("🏁 DONE - SUCCESS.")
            elif overall.status == JobStatus.CANCELLED:
                log_message("🛑 RUN ĐÃ DỪNG - checkpoint được giữ lại.")
            elif overall.status == JobStatus.SKIPPED:
                log_message("⏩ RUN SKIPPED.")
            else:
                log_message(f"❌ RUN FAILED: {overall.message}", logging.ERROR)

        except Exception as exc:
            overall = JobResult.failed(stage="SESSION", message=str(exc))
            log_message(f"❌ ERR: {exc}", logging.ERROR)
        finally:
            with ui_lock:
                if generation == run_generation:
                    set_running(False)
            maybe_shutdown(auto_shutdown, overall)

    def start_when_ready(cfg: RuntimeConfig, mode: str, acc: str, mobile_only: bool, auto_shutdown: bool, generation: int):
        # Serialize browser sessions. A restart waits for the previous driver to
        # close without clearing its cancellation signal prematurely.
        with run_lock:
            with ui_lock:
                if generation != run_generation:
                    return
                bot_logic.update_config(cfg.as_dict())
                stop_event.clear()
                cancel_shutdown_event.clear()
                log_list.controls.clear()
                set_running(True)
            log_message("⚙️ Bot Starting...")
            run_wrapper(mode, acc, mobile_only, auto_shutdown, generation)

    def on_start(_):
        nonlocal run_generation
        try:
            cfg = get_ui_config()
        except ValueError as exc:
            page.show_dialog(ft.SnackBar(content=ft.Text(f"Cấu hình không hợp lệ: {exc}")))
            return

        if not PROFILES_LIST or not acc_dropdown.value:
            page.show_dialog(ft.SnackBar(content=ft.Text("Chưa có Profile hợp lệ trong config.py")))
            return

        with ui_lock:
            if btn_start.disabled:
                return
            run_generation += 1
            generation = run_generation
            set_running(True)
            if stop_event.is_set():
                status_text.value = "CHỜ LƯỢT TRƯỚC DỪNG"
                schedule_update()

        page.run_thread(
            start_when_ready,
            cfg,
            str(mode_radio.value),
            str(acc_dropdown.value),
            bool(mobile_switch.value),
            bool(shutdown_switch.value),
            generation,
        )

    def on_stop(_):
        nonlocal run_generation
        with ui_lock:
            run_generation += 1
            stop_event.set()
            cancel_shutdown_event.set()
            set_running(False)
            status_text.value = "ĐÃ YÊU CẦU DỪNG"
            schedule_update()
        log_message("🛑 Đã yêu cầu dừng. Có thể bấm Bắt đầu; lượt mới sẽ chờ Edge cũ đóng xong.")

    btn_start.on_click = on_start
    btn_stop.on_click = on_stop

    # ------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------
    def section_title(title: str, subtitle: str | None = None) -> ft.Column:
        controls = [ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=text_primary)]
        if subtitle:
            controls.append(ft.Text(subtitle, size=13, color=text_secondary))
        return ft.Column(controls=controls, spacing=4)

    def card(content, **kwargs) -> ft.Container:
        return ft.Container(
            content=content,
            bgcolor=surface,
            border=ft.Border.all(1, border),
            border_radius=14,
            padding=18,
            **kwargs,
        )

    sidebar = ft.Container(
        width=280,
        bgcolor=sidebar_surface,
        padding=20,
        border=ft.Border(right=ft.BorderSide(1, border)),
        content=ft.Column(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Auto claim", font_family="SF Pro Display", size=24, weight=ft.FontWeight.W_600, color=text_primary),
                        ft.Text(APP_VERSION, size=13, color=text_secondary),
                    ],
                    spacing=4,
                ),
                ft.Divider(height=16, color=border),
                ft.Column(
                    controls=[
                        section_title("Chế độ chạy"),
                        mode_radio,
                        acc_dropdown,
                        ft.Divider(height=16, color=border),
                        section_title("Tùy chọn"),
                        mobile_switch,
                        ft.Divider(height=16, color=border),
                        shutdown_switch,
                    ],
                    spacing=10,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                ft.Divider(height=1, color=border),
                btn_start,
                btn_stop,
            ],
            spacing=12,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )

    status_card = card(
        ft.Row(
            controls=[
                ft.Column(
                    controls=[ft.Text("Trạng thái", size=13, color=text_secondary), status_text],
                    spacing=6,
                    expand=True,
                ),
                ft.Container(width=1, height=32, bgcolor=border),
                ft.Column(
                    controls=[ft.Text("Tài khoản hiện tại", size=13, color=text_secondary), active_profile_text],
                    spacing=6,
                    expand=True,
                ),
            ],
            spacing=20,
        )
    )

    # Bound each scrolling area so long progress/log content cannot push out controls.
    progress_card = card(
        ft.Column(
            controls=[
                section_title("Tiến độ tài khoản", "Kết quả Web và Mobile"),
                ft.Column(
                    controls=[ft.Row(controls=[status_table], scroll=ft.ScrollMode.AUTO)],
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ],
            spacing=14,
            expand=True,
        ),
        height=280,
        col={"xs": 12, "md": 5},
    )

    log_card = card(
        ft.Column(
            controls=[
                section_title("Nhật ký hoạt động", "Cập nhật trong quá trình chạy"),
                ft.Container(
                    content=log_list,
                    expand=True,
                    bgcolor=field_surface,
                    border_radius=8,
                    padding=12,
                ),
            ],
            spacing=14,
            expand=True,
        ),
        height=280,
        col={"xs": 12, "md": 7},
    )

    config_card = card(
        ft.Column(
            controls=[
                section_title("Thông số chạy", "Số lượt và thời gian chờ giữa các thao tác."),
                config_grid,
            ],
            spacing=18,
        )
    )

    main_panel = ft.Container(
        expand=True,
        padding=24,
        content=ft.Column(
            controls=[
                section_title("Tổng quan", "Thiết lập phiên chạy và theo dõi hoạt động."),
                status_card,
                ft.ResponsiveRow(controls=[progress_card, log_card], spacing=16, run_spacing=16),
                config_card,
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )

    page.add(
        ft.Row(
            controls=[sidebar, main_panel],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )
    refresh_profile_status()

# Baseline compatibility (v5.2 -> v6.0 Clean)

Mục tiêu của bản này là thay kiến trúc/lifecycle mà không tự ý "tuning" lại các thông số đã chạy thực tế.

## Giữ nguyên baseline

- Profile list, Edge user-data path, Bing package, Waydroid IP, email mapping và toàn bộ `WORD_LIST` từ `config.py` gốc.
- PC 35; Mobile 25; check interval 3.
- Typing 0.3-0.6s; thinking 3s; read 8-12s.
- Nghỉ giữa profile 60s; manual CAPTCHA wait 90s; shutdown countdown 60s.
- Browser desktop maximized; mobile viewport 390x844; iPhone 16.6 UA/client hints; remote debugging port 9222.
- Driver retry 2 lần.
- Daily Set tối đa 3 thẻ và các khoảng chờ/các selector chính của flow cũ.
- Waydroid check-in X `[0.125, 0.243, 0.375, 0.500, 0.628, 0.754, 0.885]`, Y `0.539`; đọc 15 bài; swipe 960,800 -> 960,300 duration 600.
- Thứ tự tác vụ: PC -> Daily Set -> Mobile -> Waydroid.

## Thay đổi có chủ đích để tăng reliability

- Sleep dài trở thành interruptible wait để STOP phản hồi nhanh.
- Progress chuyển sang atomic, theo profile/stage và tự migrate schema cũ.
- Daily Set là checkpoint riêng để resume đúng vị trí; vẫn best-effort như bản cũ.
- ADB có timeout/return-code/error rõ ràng và không ghi DONE khi flow quan trọng thất bại.
- Browser có page-load timeout và Selenium Manager fallback khi không có driver local.
- Auto shutdown chỉ chạy khi kết quả toàn phiên là SUCCESS.
- Flet dùng API desktop hiện hành (`ft.run`, `Page.run_thread`, `Page.schedule_update`).

## Khác biệt không được mang sang

Các hook chỉ nhằm che trạng thái WebDriver/detection trong browser cũ không nằm trong bản clean. Việc này không thay đổi các selector, account profile, mobile rendering, timings hay thứ tự flow ở trên.

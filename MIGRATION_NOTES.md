# Migration notes: v5.2 -> v6.0 Clean

## Được giữ nguyên

- `PROFILES_LIST`, `WAYDROID_EMAILS`, `WAYDROID_IP`, `BING_APP_PACKAGE`.
- Toàn bộ `WORD_LIST`.
- PC 35, Mobile 25, check interval 3.
- UI runtime typing 0.3-0.6s, thinking 3s, read 8-12s.
- Nghỉ profile 60s.
- CAPTCHA chờ người dùng xử lý 90s.
- Mobile viewport 390x844 và iPhone 16.6 UA/client hints.
- Daily Set tối đa 3 card.
- Waydroid: check-in X `[0.125, 0.243, 0.375, 0.500, 0.628, 0.754, 0.885]`, Y `0.539`.
- Waydroid đọc 15 bài, swipe 960/800 -> 960/300 duration 600.
- Thứ tự flow PC -> Daily -> Mobile -> Waydroid.

## Sửa lỗi

1. Waydroid progress v5.2 ghi ngày trong từng profile nhưng loader tìm ngày ở root. v6 tự migrate schema cũ.
2. ADB lỗi không còn bị `pass` âm thầm.
3. UI dump rỗng liên tục không còn gây loop vô hạn.
4. STOP ngắt được sleep 60s/read delay/CAPTCHA wait.
5. STOP không còn bị báo `DONE`.
6. Fatal error không còn kích hoạt auto shutdown.
7. Daily Set vẫn được thử sau khi PC kết thúc sớm vì checkpoint điểm không tăng.
8. Progress write atomic, giảm nguy cơ JSON hỏng khi process chết giữa lúc ghi.
9. Retry driver hết số lần sẽ trả FAILED thay vì rơi qua và báo thành công.
10. Waydroid chỉ ghi DONE sau khi các bước điều hướng quan trọng thành công.

## Browser compatibility

Các tham số profile, Linux stability và mobile rendering được giữ. Bản clean không bổ sung cơ chế né/phá hệ thống phát hiện tự động; các hook chỉ nhằm che WebDriver trong v5.2 không được mở rộng trong bản này.

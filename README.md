# MS Automation v6.0 Clean

Bản refactor từ project v5.2, ưu tiên **Flet trên Ubuntu**, giữ nguyên các thông số runtime và trình tự tác vụ đã được sử dụng trong project gốc, đồng thời thay phần kiến trúc/lifecycle để dễ chạy, dừng, resume và chẩn đoán lỗi hơn. Phiên bản này đã được thêm antiban so với mã nguồn gốc, nếu cần hãy liên hệ.

## Chạy nhanh trên Ubuntu

```bash
chmod +x run.sh
./run.sh
```

`run.sh` sẽ tạo `.venv` và cài dependencies nếu máy chưa có. Nếu muốn cài riêng trước:

```bash
./setup.sh
./run.sh
```

Kiểm tra môi trường:

```bash
python3 diagnose.py
```

## Dependencies được khóa phiên bản

- Python >= 3.10
- Flet Desktop 0.86.5
- Selenium 4.49.0
- Microsoft Edge tại `/usr/bin/microsoft-edge`
- `msedgedriver` là tùy chọn: nếu file nằm ở thư mục project thì dùng file đó; nếu thiếu, Selenium Manager được dùng.
- Waydroid + ADB cần có nếu bật phần Waydroid.

## Các thông số runtime mặc định

| Thông số | Giá trị |
|---|---:|
| PC Count | 35 |
| Mobile Count | 25 |
| Check interval | 3 |
| Min Type | 0.3 s |
| Max Type | 0.3 s |
| Thinking | 3 s |
| Min Read | 3 s |
| Max Read | 4 s |
| Nghỉ giữa profile | 10 s |
| CAPTCHA manual wait | 90 s |
| Waydroid news | 15 bài |
| Shutdown countdown | 60 s |

Các tỷ lệ check-in Waydroid, IP ADB, package Bing, profile list, email mapping và `WORD_LIST` được giữ trong `config.py`.

## Cấu trúc

```text
.
├── main.py
├── config.py
├── diagnose.py
├── requirements.txt
├── run.sh
├── setup.sh
├── core/
│   ├── browser.py
│   ├── bot_logic.py
│   ├── models.py
│   ├── progress_store.py
│   ├── runtime.py
│   └── waydroid_logic.py
├── ui/
│   └── app.py
├── tests/
│   ├── test_models.py
│   ├── test_progress_store.py
│   └── test_runtime.py
└── logs/
```

## Thay đổi kỹ thuật chính

- `ft.run()` thay cho API Flet cũ.
- Worker chạy bằng `page.run_thread()` thay vì thread rời không gắn lifecycle UI.
- STOP dùng `threading.Event.wait()` nên có thể ngắt các khoảng chờ dài ngay.
- Job trả trạng thái rõ ràng: `SUCCESS / FAILED / CANCELLED / SKIPPED`.
- Tự tắt máy chỉ chạy sau `SUCCESS`, không chạy sau lỗi hoặc người dùng bấm STOP.
- Progress ghi atomic bằng temp-file + `os.replace()`.
- Tự migrate progress v5.2 sang schema v2.
- Web checkpoint theo profile + stage PC/MOBILE; tác vụ Daily Set đã bỏ.
- Waydroid progress đã sửa lỗi schema ngày ở v5.2.
- ADB có timeout, return-code và error message; không còn nuốt lỗi rồi báo DONE.
- Vòng đọc tin Waydroid không còn khả năng lặp vô hạn khi UI dump liên tục lỗi.
- `DONE` Waydroid chỉ được ghi sau khi các bước điều hướng quan trọng được xác nhận.
- Input UI được validate trước khi chạy.
- Có dashboard trạng thái profile và log file `logs/run.log`.
- Log tự xoay vòng khi đạt 2 MB; giữ tối đa 3 bản cũ (`run.log.1`–`run.log.3`)
  và tự xóa bản lâu nhất khi cần. Tổng dung lượng khoảng 8 MB.
- Có `diagnose.py` và unit tests cho config/progress/cancellation.

## Resume / progress

Kết quả hiển thị trong bảng tiến độ được lưu riêng tại `dashboard_progress.json`
theo ngày. Kết quả vẫn còn sau khi checkpoint chạy được xóa và khi mở lại app;
chạy riêng Mobile không làm mất kết quả PC đã ghi nhận trong ngày.
Giao diện dùng cùng tên tài khoản Personal1 trong danh sách chọn và mục tài khoản
hiện tại. Khi chạy tất cả, danh sách tự chuyển theo tài khoản đang thực hiện.

Nếu app bị dừng/crash giữa Auto All, `bot_progress.json` giữ stage và index. Lần chạy Auto All tiếp theo sẽ bỏ qua profile/stage đã hoàn thành và tiếp tục checkpoint. Khi Auto All hoàn tất tự nhiên, web progress được xóa để lần chạy sau bắt đầu mới như hành vi v5.2.

`waydroid_progress.json` vẫn là progress theo ngày: profile đã `DONE` trong ngày sẽ được bỏ qua cho tới ngày mới.

## Test

Các test lõi không cần mở Edge/Waydroid:

```bash
python3 -m unittest discover -s tests -v
```

Để test đầy đủ UI/browser, cài dependencies trước bằng `./setup.sh`.

## Lưu ý Edge Profile

Bot tự dò profile từ `~/.config/microsoft-edge` và `~/.config/ms-bot-edge`;
không cần khai báo tên tài khoản hoặc email. Khởi động lại bot sau khi thêm
profile mới trong Edge. Tên hiển thị đi kèm mã thư mục profile.

Bot dùng dữ liệu riêng tại `~/.config/ms-bot-edge` để Selenium kết nối DevTools.
Profile còn thiếu được nhập khi chạy lần đầu, không ghi đè profile bot đã có.
Đóng Edge trước khi nhập profile mới. Nếu phiên đăng nhập không được giữ sau
khi sao chép, chọn **Thủ công** và đăng nhập lại đúng tài khoản trong profile đó.
Hai tùy chọn **Tích hợp Waydroid** và **Chỉ chạy Waydroid** đã bỏ khỏi giao diện;
các phiên chạy từ giao diện không gọi Waydroid.

Không nên mở cùng một Edge Profile bằng Edge thủ công và Selenium cùng lúc vì Chromium có thể khóa profile. Nếu `SessionNotCreated` xuất hiện, đóng Edge đang sử dụng profile đó rồi chạy lại.

## Flet trên Ubuntu

UI đặt window tối thiểu 900x620 và dùng layout co giãn cho nhóm cấu hình, tránh phụ thuộc pixel tuyệt đối ở phần nội dung chính. Nếu desktop scaling của Ubuntu khác 100%, Flet/Flutter sẽ tự scale theo hệ thống thay vì render giao diện HTML/CSS riêng.

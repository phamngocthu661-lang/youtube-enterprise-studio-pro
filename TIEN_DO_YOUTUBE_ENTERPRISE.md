# BẢNG THEO DÕI TIẾN ĐỘ DỰ ÁN: YOUTUBE ENTERPRISE MULTI-AGENT STUDIO

> **Thư mục hệ thống:** `D:\YOUTUBE_ENTERPRISE_STUDIO`
> **Localhost Command Center:** `http://127.0.0.1:8077`
> **Thư mục Dữ liệu Riêng Từng Kênh:** `D:\YOUTUBE_ENTERPRISE_STUDIO\CHANNELS_DATA\<CHANNEL_ID>\`
> **Liên kết Kênh #01 (K1 Nhật Bản):** `D:\KEY NHẬT\AGENT` (`定年後の人生ラボ【漫画】`)
> **Cập nhật lần cuối:** 2026-11-04 (`v3.8.2` — Nâng Cấp Thời Gian Nuôi Gmail & Hệ Sinh Thái Google Lên `~10–15 Phút / Tài Khoản` Như Người Thật 100%: Đọc Kỹ 2–3 Email + Đọc Báo Chí + Tìm Kiếm Google + Xem Bản Đồ Google Maps + Cập Nhật Bảng Tính Toán Lộ Trình Trong Ngày)

---

## 1. Kiến trúc Tổng thể đã hoàn thành (7 Bàn Agent / 1 Phòng Ban Kênh + Folder Dữ Liệu Riêng)

Mỗi kênh YouTube được vận hành độc lập như **1 Phòng Ban (Department)** gắn cố định:
- **1 Chrome Profile riêng (`--user-data-dir`)** + **1 cổng CDP riêng (`9301`, `9302`, `9303`)**.
- **1 Thư mục Dữ liệu & Phân tích riêng biệt (`D:\YOUTUBE_ENTERPRISE_STUDIO\CHANNELS_DATA\<CHANNEL_ID>\`)** lưu trữ trọn đời toàn bộ hồ sơ kênh, thông số YouTube Studio hàng ngày, danh sách video, bình luận khán giả và kế hoạch phát triển kênh do AI lập.

### Cấu trúc Folder Riêng của Mỗi Kênh (`CHANNELS_DATA\<CHANNEL_ID>\`)
- `MO_PROFILE_DANG_NHAP_KENH.bat`: File mở nhanh cửa sổ Chrome Profile của kênh trực tiếp trên màn hình Desktop.
- `01_CHANNEL_IDENTITY.json` & `01_HO_SO_KENH.md`: Lưu trạng thái đăng nhập Gmail/YouTube, Tên kênh thật, `@handle`, Channel URL, YouTube Studio URL, Subscribers, Số lượng video.
- `02_DAILY_ANALYTICS/` (`analytics_YYYY-MM-DD.json`) & `02_BAO_CAO_THONG_SO_HANG_NGAY.md`: Lưu lịch sử thông số YouTube Studio quét hàng ngày (Views 28 ngày, Watch Time, Subscribers, Realtime 48h, Thẻ chỉ số Studio).
- `03_VIDEOS_INVENTORY.json` & `03_DANH_SACH_VIDEO_TREN_KENH.md`: Danh sách toàn bộ video đã đăng trên kênh (Tiêu đề, Link, Views, Thời gian đăng, Thời lượng) để AI đối chiếu chống trùng lặp và tìm công thức video thắng.
- `04_COMMENTS_AND_COMMUNITY.json`: Lưu bình luận thật của khán giả và khảo sát Community Tab.
- `05_PHAN_TICH_VA_KE_HOACH_PHAT_TRIEN_NGAY.md`: Bản phân tích sức khỏe kênh & kế hoạch phát triển hàng ngày do Bộ Não AI (`AICognitiveBrain`) lập dựa trên thông số thật vừa quét.
- `06_SCRIPTS_AND_SEO/`, `07_THUMBNAILS/`, `08_WATCHED_TRANSCRIPTS/`: Các thư mục con lưu sản phẩm kịch bản, SEO, Thumbnail A/B/C và Transcript đã đọc của riêng kênh đó.
- `08_READY_VIDEOS_TO_UPLOAD/`: Thư mục riêng để người dùng chép trực tiếp file `.mp4` (hoặc nơi `BackgroundVideoProductionEngine` xuất video sản xuất ngầm) để hệ thống tự động Đẩy Lên Trước & Setup Giờ Public.
- `12_AI_SESSION_MEMORY.json`: Bộ nhớ lưu lịch sử 30 phiên gần nhất, 150 từ khóa đã tìm kiếm và 60 bình luận đã đăng để AI tuyệt đối không lặp lại quy luật hành vi.

---

## 2. Lịch sử Nâng cấp & Sửa lỗi (Changelog)

### Phiên bản `v3.8.2` — Nâng Cấp Thời Gian Nuôi Gmail & Hệ Sinh Thái Google Lên `~10–15 Phút / Tài Khoản` (Trung Bình `12 Phút`) Như Người Thật 100%
- **[NÂNG CẤP 1] Mở rộng Chế độ "Nuôi Gmail" (`warmup_mode == "GMAIL_ONLY"`) thành Chu trình Hệ Sinh Thái Google Đời Thực 4–5 Bước Ngẫu Nhiên ([`youtube_persona_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_persona_engine.py#L446-L469)):**
  - Thay vì chỉ mở Hộp thư Gmail trong 2 phút rồi đóng lại, khi chạy **`📧 Nuôi Gmail & Hệ Sinh Thái` (`GMAIL_ONLY`)**, hệ thống tự động xáo trộn ngẫu nhiên thứ tự 4–5 bước hành vi người thật (`~10 – 15 phút / tài khoản`, trung bình **`12 phút`**):
    1. **`GMAIL_DEEP_WARMUP` (`~3.5 – 4.5 phút`):** Mở `#inbox`, đọc kỹ **2–3 email** (ưu tiên thư chưa đọc `Unread`), mỗi thư cuộn đọc 3–4 nhịp và dừng đọc `5.5–9.0 giây/nhịp` (`25–40 giây/thư`); click vào đường link an toàn trong thư và dừng cuộn đọc trang đích `25–35 giây`; gắn dấu sao (`⭐`); chuyển sang kiểm tra tab `Updates`/`Promotions` (`15–20s`); mở mục `#spam` giải cứu thư hợp lệ (`12–16s`); gõ từ khóa tìm kiếm trên thanh Search của Gmail và đọc kết quả (`15–20s`).
    2. **`READ_NEWS_PORTAL` (`~2.5 – 3.5 phút`):** Mở cổng báo chí lớn theo đúng thị trường kênh (`Yahoo! Japan News`, `Google News`, `El Universal`, `USA Today`), lướt đọc tiêu đề trang chủ `15s`, sau đó mở đọc kỹ **1–2 bài báo** từ đầu đến cuối (`6–7` nhịp cuộn, dừng đọc `5.5–8.5 giây/nhịp` = `45–60 giây/bài`).
    3. **`GOOGLE_SEARCH_WEB` (`~2.5 – 3.5 phút`):** Mở trang chủ Google (`google.co.jp` / `google.com.mx` / `google.com`), di chuột Bézier bấm vào ô tìm kiếm, gõ từng ký tự từ khóa bằng phím cứng (`isTrusted: true`) + bấm `Enter`, lướt xem trang kết quả SERP `15s`, click mở **1–2 trang web tự nhiên** và dừng cuộn đọc sâu `45–60 giây/trang` để tích lũy `Google Web & App Activity`.
    4. **`GOOGLE_MAPS_EXPLORE` (`~2.0 – 3.0 phút`):** Mở Google Maps tra cứu địa điểm đời thực tại khu vực của kênh (`Tokyo/Shinjuku/Ueno`, `CDMX/Guadalajara`, `New York/Chicago`), lướt cột danh sách địa điểm `15–20s`, click vào **1–2 địa điểm** và cuộn đọc phần hình ảnh + đánh giá của khách hàng (`Reviews`) trong `35–50 giây`.
- **[NÂNG CẤP 2] Cập nhật Bảng Tính Toán Lộ Trình Trong Ngày (`DailyMasterTimelineCalculator`) & Giao diện Điều Khiển ([`ai_supervisor_watchdog.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_supervisor_watchdog.py#L198-L263), [`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py#L569-L650)):**
  - Cập nhật định mức `t_gmail_per_ch_min = 12.0 phút / tài khoản`:
    - Nếu chạy đơn từng Gmail một: `12 phút × 10 kênh = 120 phút (2 giờ)`.
    - Khi chạy **Chia Đôi Màn Hình 2 Gmail Cùng Lúc (`LEFT 50%` + `RIGHT 50%`)**: `12 phút / cặp × 5 cặp = 60 phút (1 giờ)` cho toàn bộ 10 tài khoản Gmail!
    - Trong suốt 60 phút nuôi 10 Gmail đó, luồng `BackgroundVideoProductionEngine` chạy ngầm song song vẫn tự sản xuất xong thêm `1–2 video` hoàn chỉnh.

### Phiên bản `v3.8.1` — Sửa Lỗi Cổng Xác Nhận Đăng Nhập Báo Nhầm "Chưa Đăng Nhập" Khi Đã Đăng Nhập + Tối Ưu Tốc Độ Phản Hồi `/api/status`
- **[SỬA LỖI 1] Khắc phục triệt để lỗi đã đăng nhập nhưng báo chưa đăng nhập / ngắt phiên ngay sau bước kiểm tra ([`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L1989-L2185), [`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py#L1266-L1295)):**
  - **Nguyên nhân gốc rễ 1:** Trong `browser_cdp_manager.py` thiếu lệnh `from datetime import datetime`, khiến hàm `verify_google_and_youtube_login_before_task()` sau khi xác nhận đăng nhập thành công (`✅ [Xác Nhận Đăng Nhập Hợp Lệ]`) bị văng ngoại lệ `NameError: name 'datetime' is not defined` ở dòng trả về `"checked_at": datetime.now()...`, làm luồng nuôi dừng lại và không cập nhật cờ `logged_in = True` vào `channels_registry.json`.
  - **Nguyên nhân gốc rễ 2:** Khi trình duyệt vừa mở trang khởi đầu (`google.co.jp` hoặc `youtube.com`), nếu gọi `Network.getAllCookies` hoặc kiểm tra `#avatar-btn` quá sớm khi DOM chưa tải xong, hàm dễ hiểu nhầm là chưa có avatar.
  - **Cách khắc phục:**
    1. Bổ sung `from datetime import datetime` vào `browser_cdp_manager.py`.
    2. Nâng cấp `verify_google_and_youtube_login_before_task()` kiểm tra kép cả `Storage.getCookies` và `Network.getAllCookies` (truy tìm 10 Cookie bảo mật `SID`, `HSID`, `SSID`, `SAPISID`, `APISID`, `__Secure-1PSID`, `__Secure-3PSID`, `__Secure-1PAPISID`, `__Secure-3PAPISID`, `LOGIN_INFO`), kết hợp chờ DOM tải tối đa 3 nhịp và xác nhận nếu có `>= 2` Cookie bảo mật Google/YouTube mà không bị chuyển hướng sang `ServiceLogin` thì công nhận **`logged_in = True` 100%**.
    3. Tự động đồng bộ trạng thái `logged_in: true` từ `01_CHANNEL_IDENTITY.json` sang `channels_registry.json` trong `/api/status`.
- **[SỬA LỖI 2] Tối ưu tốc độ kiểm tra cổng CDP `is_port_open` (`0.12s` socket check) & Bộ nhớ đệm Lộ trình 12 giây ([`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L170-L179), [`ai_supervisor_watchdog.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_supervisor_watchdog.py#L170-L200)):**
  - Giảm thời gian phản hồi API `/api/status` từ `> 5 giây` xuống còn `< 150ms`.
- **[SỬA LỖI 3] Cơ chế Ghi File Nguyên Tử (`Atomic Save`) & Tự Khôi Phục Bản Sao Lưu (`channels_registry.backup.json`) ([`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py#L107-L152)):**
  - Sử dụng file tạm `.tmp_<pid>` kết hợp `os.replace()` và bản sao lưu tự động `channels_registry.backup.json` để đảm bảo dữ liệu 10 kênh không bao giờ bị rỗng kể cả khi mất điện hay nhiều luồng ghi đồng thời.

### Phiên bản `v3.8` — Bộ Tính Toán Lộ Trình Thời Gian Trong Ngày (`DailyMasterTimelineCalculator`) + Chạy Song Song Chia Đôi Màn Hình Trái/Phải (`ParallelSplitScreenCoordinator`: Nuôi 2 Gmail / 2 Kênh Cùng Lúc) + Sản Xuất Video Chạy Ngầm Song Song (`BackgroundVideoProductionEngine`) + AI Giám Sát Tiến Độ & Tự Khắc Phục Lỗi 24/7 (`AISupervisorWatchdog`)
- **[NÂNG CẤP 1] Bộ Tính Toán Lộ Trình Thời Gian Chuẩn Xác Trong Ngày (`DailyMasterTimelineCalculator` — [`ai_supervisor_watchdog.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_supervisor_watchdog.py#L140-L395), [`LO_TRINH_VAN_HANH_TRONG_NGAY.md`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/LO_TRINH_VAN_HANH_TRONG_NGAY.md)):**
  - Tính toán chính xác thời gian từng tác vụ cho quy mô **10 kênh / 1 máy PC** và đối chiếu giữa **Chạy Tuần Tự 1 Cửa Sổ** vs. **Chạy Song Song Chia Đôi Màn Hình (Trái & Phải) + Sản Xuất Video Ngầm**:
    1. **Nuôi Gmail Chủ Động 6 Bước (`T_gmail`):** `2.5 phút / kênh` $\rightarrow$ Chạy đôi 2 Gmail chia đôi màn hình: **`12.5 phút / 10 kênh`**.
    2. **Nuôi Kênh YouTube Xem Sâu (`3–7 phút/video`) + Đọc Sub + Gõ Bình Luận Thật (`T_warmup_yt`):** `28 phút / phiên / kênh` $\rightarrow$ Chạy đôi 2 Kênh chia đôi màn hình: **`140 phút (2 giờ 20 phút) / phiên / 10 kênh`** (2 ca Sáng & Chiều = `280 phút` trên màn hình thay vì `560 phút`).
    3. **Đẩy Video Lên Trước & Setup Giờ Public (`T_pre_upload`):** `5.5 phút / kênh` $\rightarrow$ Chạy đôi 2 Kênh: **`27.5 phút / 10 kênh`**, hoàn tất trước `16:30` để YouTube xử lý xong 4K & Bản quyền trước Giờ Vàng `20:00`.
    4. **Tự Sản Xuất Video Chạy Ngầm Song Song (`T_video_production`):** `35 phút / tập` (Bàn #2 Tiêu đề $\rightarrow$ Bàn #3 Kịch bản & Phụ đề `.srt` $\rightarrow$ Bàn #4 Kiểm định QA $\rightarrow$ Bàn #5 Đóng gói SEO $\rightarrow$ Render `.mp4` chạy ngầm). Do chạy **song song ở luồng nền** ngay trong lúc màn hình đang mở 2 trình duyệt nuôi Gmail & nuôi Kênh, hệ thống tự sản xuất được **8–9 video hoàn chỉnh** ngay trong thời gian nuôi kênh mà **không tốn thêm thời gian chờ riêng**!
    5. **Tổng thời gian tiết kiệm:** Giảm từ **`16 giờ 20 phút`** (nếu chạy tuần tự từng việc) xuống chỉ còn **`5 giờ 20 phút`** hoạt động trình duyệt trên màn hình (**tiết kiệm `67.3%` tổng thời gian trong ngày**).
- **[NÂNG CẤP 2] Chạy Song Song Chia Đôi Màn Hình Trái (`LEFT 50%`) & Phải (`RIGHT 50%`) (`get_split_screen_bounds` & `ParallelSplitScreenCoordinator` — [`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L197-L295), [`ai_supervisor_watchdog.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_supervisor_watchdog.py#L565-L700)):**
  - Nâng cấp `BrowserCDPManager` tự động đọc độ phân giải thực của màn hình Windows (`GetSystemMetrics`) và chia chính xác:
    - **Cửa sổ Trái (`window_slot = "LEFT"`):** `left = 0, top = 0, width = 50% màn hình, height = 100% - taskbar` (`0,0 -> 960x1032` trên màn Full HD).
    - **Cửa sổ Phải (`window_slot = "RIGHT"`):** `left = 50% màn hình, top = 0, width = 50% màn hình, height = 100% - taskbar` (`960,0 -> 960x1032` trên màn Full HD).
  - Bổ sung trên giao diện Desktop bộ chọn **Màn Hình Trái (`LEFT`)** + **Màn Hình Phải (`RIGHT`)** cùng 4 nút điều phối song song:
    - `📧⚡ Nuôi 2 Gmail Cùng Lúc (Chia Đôi Màn Hình)`
    - `📺⚡ Nuôi 2 Kênh Cùng Lúc (Chia Đôi Màn Hình)`
    - `🚀 Chạy Toàn Bộ Các Cặp (Nuôi Gmail Đôi)`
    - `🚀 Chạy Toàn Bộ Các Cặp (Nuôi Kênh Đôi + Tạo Video Ngầm)`
- **[NÂNG CẤP 3] Bộ Máy Tự Sản Xuất Video Chạy Ngầm Song Song Khi Đang Nuôi (`BackgroundVideoProductionEngine` — [`ai_supervisor_watchdog.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_supervisor_watchdog.py#L398-L562)):**
  - Tự động kiểm tra sức khỏe phần cứng thời gian thực (`HardwareResourceMonitor`: `RAM trống >= 1.8 GB`, `CPU < 88%`).
  - Trong lúc 2 cửa sổ Chrome đang nuôi Gmail / nuôi Kênh trên màn hình, luồng nền tự động chạy quy trình 5 bước (Hoạch định Tiêu đề $\rightarrow$ Biên kịch Kịch bản & Phụ đề `.srt` $\rightarrow$ Kiểm định QA 97.5/100 $\rightarrow$ Đóng gói `_SEO.txt` $\rightarrow$ Xuất file `.mp4` vào `08_READY_VIDEOS_TO_UPLOAD/<EPISODE_ID>/`).
  - Có cơ chế **Tự động nhường tài nguyên (`_throttle_if_high_load`)**: Nếu CPU tạm thời vượt `92%` hoặc RAM trống dưới `1.3 GB`, luồng tạo video ngầm tự động giảm nhịp 3 giây để 2 trình duyệt nuôi kênh luôn mượt 100%.
- **[NÂNG CẤP 4] AI Giám Sát Tiến Độ Liên Tục & Tự Động Xử Lý Khắc Phục Lỗi 24/7 (`AISupervisorWatchdog` — [`ai_supervisor_watchdog.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_supervisor_watchdog.py#L703-L905)):**
  - Chạy ngầm liên tục mỗi `12 giây/lần` (`start_background_watchdog_loop`) để giám sát toàn bộ các kênh và tự động khắc phục sự cố (`Self-Healing`):
    1. **Tự động Reload Tab bị treo hoặc lỗi mạng/Proxy (`FROZEN_TAB_RELOAD` / `NETWORK_OR_PROXY_ERROR_RELOAD`):** Phát hiện `chrome-error://`, `ERR_PROXY_CONNECTION_FAILED`, `ERR_TIMED_OUT` hoặc Tab không phản hồi JS và tự động gửi lệnh `Page.reload`.
    2. **Tự động bấm tắt Popup làm dừng video YouTube (`YOUTUBE_CONTINUE_WATCHING_POPUP` & `VIDEO_PLAYBACK_RESUMED`):** Phát hiện hộp thoại *"Video paused. Continue watching?"* (`yt-confirm-dialog-renderer`) hoặc video HTML5 bị dừng giữa phiên nuôi để tự động bấm xác nhận và gọi `video.play()`.
    3. **Tự động gỡ kẹt hộp thoại Upload YouTube Studio (`STUDIO_COPPA_AUTO_SELECT`):** Nếu đang đẩy video mà bị kẹt ở mục Trẻ em (COPPA), AI Supervisor tự động tích `VIDEO_MADE_FOR_KIDS_NOT_MFK`.
    4. **Tự động dọn Tab thừa (`EXCESS_TABS_CLEANUP`) & Căn chỉnh lại 2 cửa sổ Trái/Phải (`SPLIT_SCREEN_ALIGNMENT`).**
    5. Lưu nhật ký xử lý sự cố vào `LOGS/AI_SUPERVISOR_WATCHDOG.log` và hiển thị trực tiếp trên bảng **「🛡️ PHẦN 4: AI GIÁM SÁT TIẾN ĐỘ & TỰ KHẮC PHỤC LỖI 24/7」**.

### Phiên bản `v3.7` — Cổng Xác Nhận Đăng Nhập Trước Mọi Tác Vụ (`Pre-Flight Login Gate`) + Tách Biệt Hoàn Toàn Phần Nuôi & Phần Đăng + Hỗ Trợ Video Cung Cấp Sẵn (`08_READY_VIDEOS_TO_UPLOAD`) + Đẩy Video Lên Trước & Setup Giờ Public Tự Động (`Pre-Upload & Schedule`) + Xem Sâu 3–7 Phút/Video & Đăng Bình Luận Thật
- **[NÂNG CẤP 1] Cổng Bảo Vệ Xác Nhận Đăng Nhập Trước Mọi Tác Vụ (`verify_google_and_youtube_login_before_task` — [`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L1926-L2095), [`youtube_persona_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_persona_engine.py#L465-L505), [`youtube_seo_uploader_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_seo_uploader_engine.py#L1310-L1335)):**
  - Trước khi chạy bất kỳ tác vụ nào (**Nuôi Gmail**, **Nuôi Kênh YouTube**, hoặc **Đẩy Video Lên YouTube Studio**), hệ thống bắt buộc chạy hàm `verify_google_and_youtube_login_before_task()` kiểm tra kép:
    1. Kiểm tra bộ Cookie xác thực phiên (`SID`, `HSID`, `SSID`, `__Secure-1PSID`, `__Secure-3PSID`) qua CDP `Network.getAllCookies`.
    2. Kiểm tra trực tiếp trên DOM thực tế: `ytcfg.get('LOGGED_IN') === true`, `#avatar-btn` trên YouTube, URL hộp thư `mail.google.com/mail/` trên Gmail, và `ytcp-app` / `studio.youtube.com/channel/UC...` trên YouTube Studio.
  - **Nếu phát hiện chưa đăng nhập (hoặc bị văng phiên `ServiceLogin`)**: Hệ thống **DỪNG NGAY LẬP TỨC** tác vụ, cập nhật trạng thái `LOGIN_REQUIRED`, đóng trình duyệt an toàn và ghi cảnh báo rõ ràng lên bảng điều khiển để không bao giờ chạy nuôi hay đẩy video lãng phí khi chưa đăng nhập!
  - Bổ sung nút **「🔐 Xác Nhận Đã Đăng Nhập Chưa」** ngay trên thanh công cụ chính của phần mềm.
- **[NÂNG CẤP 2] Tách Biệt Hoàn Toàn Phần "NUÔI (WARM-UP)" và Phần "ĐẨY VIDEO & HẸN GIỜ PUBLIC (PRE-UPLOAD & SCHEDULE)" ([`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py#L545-L605), [`youtube_seo_uploader_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_seo_uploader_engine.py#L1560-L1630)):**
  - **Phần Nuôi độc lập (`auto_warmup_enabled`)**: Có công tắc bật/tắt riêng và tách thành 3 nút/chế độ rõ ràng:
    1. `📧 Chỉ Nuôi Gmail (~2p)` (`warmup_mode = "GMAIL_ONLY"`)
    2. `📺 Chỉ Nuôi Kênh (Xem Sâu 3–7p/video & Bình Luận Thật ~25p)` (`warmup_mode = "YOUTUBE_DEEP_ONLY"`)
    3. `🌐 Nuôi Kết Hợp (Gmail + Báo + Kênh)` (`warmup_mode = "FULL_OMNI"`)
  - **Phần Đẩy Video & Hẹn Giờ Public độc lập (`auto_pre_upload_enabled`)**: Có công tắc bật/tắt riêng (`🟣 Tự Động Đẩy Trước`), khung giờ kích hoạt riêng (`pre_upload_trigger_time`, mặc định `13:30`) và Giờ Vàng Public riêng (`scheduled_publish_time`, mặc định `20:00`), hoạt động hoàn toàn độc lập với phần Nuôi.
- **[NÂNG CẤP 3] Linh Hoạt Nguồn Video: Hỗ Trợ Cả "Tôi Cung Cấp Video Sẵn" & "Tự Sản Xuất" Cho Máy Nuôi 10 Kênh ([`youtube_seo_uploader_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_seo_uploader_engine.py#L428-L670)):**
  - Do 1 máy PC nuôi 10 kênh (mất ~6–8 tiếng/ngày) không đủ thời gian/GPU để tự render video cho cả 10 kênh, hệ thống bổ sung chế độ **`video_source_mode = "USER_SUPPLIED"` (Tôi Cung Cấp Video Sẵn)** làm mặc định cùng thư mục riêng **`08_READY_VIDEOS_TO_UPLOAD`** cho từng kênh (nút **「📥 Mở Folder Bỏ Video Sẵn (.mp4)」** trên giao diện).
  - Hỗ trợ cả **Thư mục theo Tập (`20/`, `21/`...)** lẫn **Thả trực tiếp file `.mp4` lẻ (`Drop-and-Go MP4`)**: Nếu bạn chỉ chép file `.mp4` từ máy dựng video sang mà chưa kèm file SEO, hàm `auto_generate_seo_for_video_if_missing()` sẽ tự động tạo ngay file `<ten_video>_AUTO_SEO.txt` chuẩn SEO theo đúng ngôn ngữ kênh (`ja` / `en` / `es`) để đẩy lên không bao giờ bị lỗi thiếu file.
- **[NÂNG CẤP 4] Đẩy Video Lên Trước & Setup Giờ Public Tự Động (`compute_next_available_schedule_slot` & `_configure_step4_schedule_datetime` — [`youtube_seo_uploader_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_seo_uploader_engine.py#L672-L735)):**
  - Video luôn được **đẩy lên trước nhiều tiếng** (hoặc đẩy trước cả tuần) và tự động chọn chế độ **`SCHEDULE` (Lên lịch)** ở Bước 4 của YouTube Studio để YouTube xử lý xong 100% độ phân giải HD/4K và kiểm tra bản quyền trước giờ Public.
  - Hàm `_configure_step4_schedule_datetime()` tự động bấm `#schedule-radio-button`, mở `#datepicker-trigger`, nhận diện định dạng ngày của giao diện YouTube Studio (Việt / Anh / Nhật / Tây Ban Nha), điền chính xác **Ngày (`scheduled_date`)** và **Giờ Vàng (`scheduled_time`, ví dụ `20:00`)** rồi bấm nút **Lên lịch (`#done-button`)**.
  - Nếu bạn bấm đẩy liên tiếp nhiều video trong cùng 1 buổi, hàm `compute_next_available_schedule_slot()` tự động xếp lịch nối tiếp sang các ngày kế tiếp (`Ngày 1 - 20:00`, `Ngày 2 - 20:00`, `Ngày 3 - 20:00`...).
- **[NÂNG CẤP 5] Chuẩn Hóa Thời Gian Xem Sâu Thực Tế (`3 – 7 Phút / Video`) & Gõ Đăng Bình Luận Thật Bằng Phím Cứng (`post_comment_on_youtube_watch_page` — [`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L2097-L2285), [`youtube_persona_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_persona_engine.py#L817-L945)):**
  - Đọc thời lượng thật (`video.duration`) của video trên `#movie_player` và cho xem sâu **từ 3 đến 7 phút (`180s – 420s`) mỗi video** ở chế độ thực chiến (vẫn giữ nút `⚡ Test Nhanh 9s` riêng cho lúc kiểm tra nhanh).
  - Sau khi đọc Transcript, hàm `post_comment_on_youtube_watch_page()` tự động cuộn xuống `#comments`, di chuột Bézier bấm vào `#simplebox-placeholder`, gõ từng ký tự câu bình luận bằng phím cứng và bấm nút **Bình luận (`#submit-button`)** trực tiếp dưới video.

### Phiên bản `v3.6` — Tối Ưu Giới Hạn Chuẩn 10 Kênh / 1 Máy (`MAX_CHANNELS_PER_PC = 10`) + Cô Lập Tuyệt Đối 1 Profile = 1 Kênh + Hệ Thống Gắn & Kiểm Tra Proxy Đa Định Dạng (`HTTP / HTTPS / SOCKS5` + Tự Động Xác Thực `user:pass` & Chống Rò Rỉ WebRTC)
- **[NÂNG CẤP TỐI ƯU 10 KÊNH / 1 MÁY & CÔ LẬP PROFILE + PROXY ĐỘC LẬP ([`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L243-L418), [`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py#L40-L100))]:**
  1. **Giới hạn tối ưu 1 Máy tối đa 10 Kênh (`MAX_CHANNELS_PER_PC = 10`, Slot `#1` $\rightarrow$ `#10`, Cổng CDP `9301` $\rightarrow$ `9310`):**
     - Hàm `_enforce_10_channel_profile_isolation` khóa cứng trần 10 kênh trên mỗi máy tính để bảo vệ RAM/CPU và độ sạch của môi trường.
     - Trong chế độ `Autopilot`, hệ thống áp dụng **Khóa Tuần Tự Từng Kênh (`max_concurrent_channels = 1`)**: nếu đang có 1 kênh mở Chrome nuôi hoặc upload thì các kênh còn lại tự động chờ kênh đó hoàn tất và đóng trình duyệt xong mới chạy tiếp — đảm bảo 10 kênh trên 1 máy vận hành êm ái 24/7 không bao giờ tràn RAM.
  2. **Cô lập tuyệt đối `1 Profile = 1 Kênh` (`PROFILES\KENH_01_...` $\rightarrow$ `PROFILES\KENH_10_...`):**
     - Tự động kiểm tra và chống trùng lặp 100%: Không bao giờ có 2 kênh dùng chung 1 thư mục `profile_dir` hay chung 1 `cdp_port`. Mỗi kênh giữ trọn vẹn Cookie, LocalStorage, IndexedDB và Lịch sử riêng biệt.
  3. **Hệ thống Gắn & Kiểm Tra Proxy Đa Định Dạng cho từng Profile (`parse_and_prepare_proxy_for_profile` & `verify_proxy_or_direct_ip`):**
     - Hỗ trợ đầy đủ cả 4 định dạng Proxy phổ biến:
       - `IP:Port` (IP Whitelist)
       - `IP:Port:Username:Password` (Định dạng phổ biến nhất khi mua Proxy dân cư / ISP)
       - `http://user:pass@IP:Port` hoặc `http://IP:Port`
       - `socks5://user:pass@IP:Port` hoặc `socks5://IP:Port`
     - **Tự động sinh Chrome Proxy Auth Extension riêng biệt** nằm ngay trong `PROFILES\<KENH>\_proxy_auth_ext` khi Proxy có `Username:Password` (tự động đăng nhập Proxy ngầm 100%, không bao giờ hiện popup hỏi mật khẩu trên Chrome).
     - **Tự động bật cờ chống rò rỉ WebRTC IP (`--force-webrtc-ip-handling-policy=disable_non_proxied_udp`)** khi kênh gắn Proxy để WebRTC không làm lộ IP gốc của máy tính.
     - Bổ sung nút **「🌐 Gắn / Kiểm Tra Proxy & IP」** và cửa sổ Modal kiểm tra trực tiếp địa chỉ IP ra mạng, Quốc gia, Thành phố, ISP và Độ trễ (`ms`) ngay trên phần mềm Desktop.

### Phiên bản `v3.5` — Chuyển Đổi Hoàn Toàn Thành Phần Mềm Máy Tính Windows (`YouTube_Enterprise_Studio.exe` — Native PC Desktop Application)
- **[NÂNG CẤP THÀNH ỨNG DỤNG DESKTOP PC ĐỘC LẬP ([`YouTube_Enterprise_Studio.exe`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/YouTube_Enterprise_Studio.exe), [`youtube_enterprise_desktop_app.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_desktop_app.py), [`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py), [`KHOI_DONG_YOUTUBE_ENTERPRISE.bat`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/KHOI_DONG_YOUTUBE_ENTERPRISE.bat))]:**
  1. **Biên dịch File thực thi `.exe` chuẩn Windows (`YouTube_Enterprise_Studio.exe`):**
     - Biên dịch bằng trình biên dịch `.NET` `csc.exe /target:winexe` chạy trực tiếp dưới dạng **Windows GUI Application** — **hoàn toàn không hiện cửa sổ CMD đen**.
     - Khi bấm đúp vào [`YouTube_Enterprise_Studio.exe`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/YouTube_Enterprise_Studio.exe), ứng dụng mở thẳng **Cửa sổ Phần mềm Desktop (`pywebview` / Microsoft Edge WebView2 Native Window, kích thước `1420x880`)** không có thanh địa chỉ trình duyệt, không có tab thừa.
     - Khi người dùng bấm nút **「📴 Thoát App」** hoặc bấm dấu `X` đóng cửa sổ phần mềm, toàn bộ tiến trình ngầm tự động tắt sạch 100%.
  2. **Tích hợp Hộp Thoại Chọn Thư Mục Gốc Của Windows (`Native Windows Folder Picker Dialog`) & Cửa Sổ Modal Cài Đặt Chuẩn App PC:**
     - Thay thế hoàn toàn các hộp thoại `prompt()` của trình duyệt web bằng **Cửa sổ Modal Cài Đặt chuẩn PC App** (`#aiConfigModal`, `#addChannelModal`) và hộp thoại **Chọn Thư Mục của Windows (`tkinter.filedialog.askdirectory`)** khi bấm nút **「📂 Đổi Thư Mục Key」** hoặc **「📂 Chọn Folder...」**.
     - Bổ sung thẻ trạng thái **`🤖 AI Brain: AUTO (X phiên nhớ)`** và nút **`📴 Thoát App`** ngay trên thanh Header của phần mềm.

### Phiên bản `v3.4` — Bộ Não AI Đa Model Thực Thụ (`Gemini API / OpenAI API / ChatGPT Web / Antigravity / Ollama`) + Bộ Nhớ Chống Lặp 30 Phiên (`12_AI_SESSION_MEMORY.json`)
- **[NÂNG CẤP CỐT LÕI CHỐNG LẶP HÀNH VI BOT TRÊN MỌI MÁY TÍNH ([`ai_cognitive_brain.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_cognitive_brain.py), [`youtube_persona_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_persona_engine.py), [`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py))]:**
  1. **Kết nối 4 Chế Độ Model AI Thực Thụ (`CHANNELS_DATA/ai_model_config.json`):**
     - **Chế độ 1 (`GEMINI_API` — Khuyên dùng khi mang sang máy khác):** Gọi trực tiếp model `gemini-2.5-flash` của Google AI Studio qua HTTPS chuẩn (`urllib.request`, không cần cài thư viện ngoài). Chỉ cần dán 1 API Key miễn phí vào nút **「🤖 Cấu Hình Model AI」** trên Dashboard, key sẽ lưu trong `CHANNELS_DATA/ai_model_config.json` — khi copy thư mục sang bất kỳ máy tính nào khác, máy đó **có sẵn Model AI thật điều khiển 100%** mà không cần đăng nhập Antigravity hay ChatGPT Web!
     - **Chế độ 2 (`OPENAI_API`):** Hỗ trợ `gpt-4o-mini` / `deepseek-chat` / `Groq` qua API Key.
     - **Chế độ 3 (`CHATGPT_WEB`):** Điều khiển qua tài khoản ChatGPT Web đang đăng nhập (`chatgpt_web_client.py`).
     - **Chế độ 4 (`ANTIGRAVITY_AGENT` & `OLLAMA_LOCAL`):** Điều khiển trực tiếp bởi Antigravity Agent hoặc Local LLM (`127.0.0.1:11434`).
  2. **Bộ Nhớ Chống Lặp Lối Mòn 30 Phiên (`12_AI_SESSION_MEMORY.json`) & `think_generative_human_session_plan()`:**
     - Trước mỗi phiên nuôi, Bộ Não AI đọc lại toàn bộ lịch sử 30 phiên trước (`past_sessions`), 150 từ khóa đã tìm (`used_search_queries`) và 60 bình luận đã viết (`used_comments`) để thiết kế **Kịch bản Phiên Độc Bản**:
       - **Biến thiên tổng số bước (`5` đến `10` bước):** Không bao giờ cố định 8 bước mỗi ngày.
       - **Biến thiên cả Bước Mở Đầu & URL Khởi Động Trình Duyệt:** Hôm nay mở YouTube xem trước rồi mới check Gmail ở giữa phiên; ngày mai mở đọc Báo Yahoo! Japan trước; ngày kia mở Google Search trước... (Tuyệt đối không cố định Bước 1 luôn là Gmail!).
       - **Không lặp lại câu tìm kiếm & thời lượng xem:** Mọi câu tìm kiếm trên Google Search, Google Maps, Gmail và YouTube đều được tạo mới và đối chiếu cấm trùng lặp với 150 câu truy vấn trước đó; tỷ lệ thời lượng xem (`watch_ratio`) biến thiên ngẫu nhiên liên tục từ `44%` đến `85%`.

### Phiên bản `v3.3` — Nâng Cấp Đóng Gói Độc Lập 100% (`100% Standalone & Portable Multi-PC`: Chạy Trực Tiếp Trên Máy Khác Không Cần Acc ChatGPT Hay Antigravity)
- **[NÂNG CẤP ĐƯỜNG DẪN ĐỘNG PORTABLE 100% ([`KHOI_DONG_YOUTUBE_ENTERPRISE.bat`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/KHOI_DONG_YOUTUBE_ENTERPRISE.bat), [`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py), [`ai_cognitive_brain.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_cognitive_brain.py), [`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py), [`channel_scanner_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/channel_scanner_engine.py), [`youtube_persona_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_persona_engine.py), [`youtube_seo_uploader_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_seo_uploader_engine.py))]:**
  - Chuyển toàn bộ biến `BASE_DIR` / `BASE_STUDIO_DIR` sang đường dẫn tương đối tự động (`os.path.dirname(os.path.abspath(__file__))`) và `cd /d "%~dp0"` trong file `.bat`.
  - Khi copy thư mục `YOUTUBE_ENTERPRISE_STUDIO` sang bất kỳ máy tính Windows nào khác (ổ `C:\`, `D:\`, `E:\` hay `Desktop`), toàn bộ tính năng **Nuôi Gmail 6 Bước + Nuôi Kênh Đa Tầng + Quét Analytics + Hàng Đợi Upload Tự Động + Hẹn Giờ Autopilot** đều chạy độc lập 100% chỉ cần **Python 3 + Google Chrome**, **không bắt buộc** phải có tài khoản ChatGPT hay tài khoản Antigravity.

### Phiên bản `v3.2` — Nâng Cấp Hệ Thống Đa Key / Đa Thị Trường Tự Động (`Multi-Key & Multi-Country Dynamic Engine`: Nhật Bản `ja` • Hoa Kỳ `en` • Mexico `es-MX`)
- **[NÂNG CẤP TOÀN DIỆN HỖ TRỢ MỌI KEY KHÁC NGOÀI KEY NHẬT K1 ([`ai_cognitive_brain.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_cognitive_brain.py#L216-L275), [`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L984-L1540), [`youtube_seo_uploader_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_seo_uploader_engine.py), [`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py))]:**
  1. **Tự động chuyển đổi Hệ Sinh Thái Nuôi Kênh theo Thị Trường & Từ Khóa Gốc (`seed_keywords`) của từng Key:**
     - **Nhóm Key Nhật Bản (`language: "ja"` — Key Nhật K1, Key Nhật Drama, Manga Độc Thân, Kuchikomi):**
       - Múi giờ: `Asia/Tokyo (GMT+9)` | Ngôn ngữ trình duyệt: `ja-JP,ja` | Báo chí: `Yahoo! Japan News`, `Google News Japan` | Bản đồ: `google.co.jp/maps` (Tokyo, Shinjuku, Ueno...) | Vị trí Upload YouTube Studio: `Nhật Bản (Japan / 日本)`.
       - Nếu là Key Nhật khác ngoài K1 (ví dụ `KEY NHẬT DRAMA`), hệ thống tự động lấy `seed_keywords` riêng của kênh đó để đăng ký `Google Alerts`, tìm kiếm `Google Search` và chấm điểm lọc video YouTube (không bị khóa cứng vào bộ từ khóa `ハローワーク` của Kênh 1).
     - **Nhóm Key Mỹ (`language: "en"` — Mafia Boss × Maid, Homeless × Abandoned Property, Ông Già Trả Đũa Mỹ, Phụ Nữ Báo Thù Mỹ, Black Dad CEO, Kinh Dị Đêm Khuya Mỹ):**
       - Múi giờ: `America/New_York` | Ngôn ngữ trình duyệt: `en-US,en` | Báo chí: `Google News US`, `Yahoo News US`, `USA Today` | Bản đồ: `google.com/maps` (New York, Chicago, Manhattan...) | Vị trí Upload YouTube Studio: `Hoa Kỳ (United States)`.
       - Tự động dùng `seed_keywords` tiếng Anh của kênh để đăng ký `Google Alerts`, tìm kiếm `Google Search` và lọc video đề xuất trên YouTube.
     - **Nhóm Key Mexico / Tây Ban Nha (`language: "es"` — Bà Cô Drama Gia Đình Mexico, Ông Già Trừng Trị Mexico, Đồng Quê Cổ Điển Mexico, Tiểu Sử Sao Mexico):**
       - Múi giờ: `America/Mexico_City` | Ngôn ngữ trình duyệt: `es-MX,es` | Báo chí: `Google News México`, `El Universal México`, `Milenio` | Bản đồ: `google.com.mx/maps` (Ciudad de México, Coyoacán, Guadalajara...) | Vị trí Upload YouTube Studio: `Mexico (México)`.
       - Tự động dùng `seed_keywords` tiếng Tây Ban Nha của kênh để đăng ký `Google Alerts` (`google.com.mx/alerts?hl=es-419`), tìm kiếm `Google Search` và lọc video YouTube.
  2. **Mỗi Key / Kênh có Thư mục Hàng đợi Upload (`batch_queue_dir`) & Bộ đọc SEO Đa Ngôn Ngữ riêng:**
     - Bổ sung nút **「➕ Thêm Kênh / Key Mới (Nhật • Mỹ • Mexico)」** ở cột trái Dashboard và nút **「📂 Đổi Thư Mục Key」** ngay trên bảng Hàng đợi Upload để mỗi Key trỏ tới thư mục sản xuất riêng của mình (ví dụ: `D:\KEY NHẬT\20-30`, `D:\KEY NHẬT DRAMA`, `D:\DANG LEN`...).
     - Bộ đọc file SEO (`SEOPackageParser.parse_seo_file`) tự động nhận diện cả tiêu đề tiếng Nhật, tiếng Anh và tiếng Tây Ban Nha (`LOCKED_TITLE`, `CURRENT FINAL TITLE`, `RECOMMENDED FINAL TITLE`, `PRIMARY TITLE`, `1. TITLE`...).

### Phiên bản `v3.1` — Nâng Cấp Toàn Diện 4 Trụ Cột: Nuôi Gmail Chủ Động 6 Bước (`Google Alerts` + Click Link Trong Thư + Giải Cứu Spam) + Hàng Đợi Upload Tự Động (`D:\KEY NHẬT\20-30`) + Tự Động Bước 2 (`Subtitles .srt` / `End Screen` / `Info Cards` / `Ghim Comment`) + Hẹn Giờ Autopilot
- **[TRỤ CỘT 1] Nâng Cấp Mô-Đun Nuôi Gmail Chủ Động 6 Bước Chuyên Sâu (`Active Gmail Deep Trust Farming v3.1` — [`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L1014-L1330)):**
  1. **Tự động đăng ký `Google Alerts` tiếng Nhật (`setup_google_alerts_subscriptions`):**
     - Truy cập `https://www.google.co.jp/alerts?hl=ja`, dùng chuột Bézier + phím cứng (`isTrusted: true`) đăng ký 3 chủ đề tin tức Kênh 1 (`定年後の仕事`, `60代 再就職 ハローワーク`, `年金 65歳 働き方`).
     - Giúp hòm thư Gmail mỗi ngày đều nhận được 1–3 email tin tức tiếng Nhật **mới tinh (`Unread`)** từ máy chủ Google gửi về, chấm dứt tình trạng "hòm thư chết".
  2. **Ưu tiên đọc Thư Chưa Đọc (`tr.zA.zE`) & Gắn Ngôi Sao (`Star` ⭐):**
     - Tự động nhận diện các email mới chưa đọc (`is_unread = True`) để ưu tiên mở trước; dùng chuột Bézier bấm gắn dấu sao (`⭐`) cho thư quan trọng.
  3. **Click vào đường link an toàn bên trong nội dung Email (`Click Safe Link Inside Email`):**
     - Khi đang mở thư, quét các thẻ `<a href="http...">` trong thân email (`.a3s a`), lọc bỏ các link `unsubscribe / 退会 / 配信停止`, bấm mở bài báo/thông báo ngay trên 1 Tab, lăn chuột đọc 4–5 giây rồi quay về Gmail.
  4. **Duyệt Đa Tab Phân Loại Gmail (`#category/updates` & `#category/promotions`):**
     - Chuyển qua tab *Cập nhật (Updates)* hoặc *Quảng cáo (Promotions)* lăn chuột kiểm tra thư dịch vụ.
  5. **Kiểm tra mục Thư Rác (`#spam`) & Giải Cứu Thư (`Not Spam / 迷惑メールではない`):**
     - Mở `https://mail.google.com/mail/u/0/#spam`, nếu phát hiện thư bị lọc nhầm vào Spam sẽ tự động mở thư và dùng chuột Bézier bấm nút **「Không phải thư rác / Not spam / 迷惑メールではない」** đưa về Inbox.
  6. **Tìm kiếm nội bộ trên thanh Search của Gmail (`input[name="q"]`) & Lưu lịch sử `11_GMAIL_TRUST_FARMING_STATE.json`:**
     - Gõ từ khóa (`Google`, `YouTube`, `定年`, `アラート`) + `Enter` trên ô tìm kiếm của Gmail và lưu thống kê lũy kế vào thư mục riêng của kênh.
- **[TRỤ CỘT 2] Mở Rộng Hành Vi Đời Thực Đa Dịch Vụ (`Google Maps Nhật Bản` + `YouTube Shorts` + `Kịch Bản Biến Thiên Ngẫu Nhiên` — [`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L1332-L1415) & [`youtube_persona_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_persona_engine.py#L462-L580)):**
  - **`warmup_google_maps_explore`:** Mở `https://www.google.co.jp/maps?hl=ja`, tra cứu địa điểm đời thực tại Nhật (`ハローワーク新宿`, `東京しごとセンター`, `上野恩賜公園 喫茶店`, `巣鴨地蔵通り商店街`), click xem chi tiết & lăn chuột đọc đánh giá địa phương.
  - **`warmup_youtube_shorts_swipe`:** Mở `https://www.youtube.com/shorts`, xem lướt 3 video Shorts ngắn và bấm phím cứng `ArrowDown` (`isTrusted: true`) chuyển video.
  - **`apply_channel_locale_and_timezone_emulation`:** Tự động đồng bộ múi giờ `Asia/Tokyo` và header `Accept-Language: ja-JP,ja;q=0.9` cho kênh Nhật.
  - **Trộn ngẫu nhiên thứ tự hành vi (`Dynamic Persona Playlist`):** Mỗi phiên nuôi tự động xáo trộn thứ tự các bước giữa *Gmail 6 Bước*, *Đọc Báo Nhật*, *Google Search*, *Google Maps / YouTube Shorts* và *Xem Video Kênh 1*.
- **[TRỤ CỘT 3] Hàng Đợi Quét & Upload Tự Động Theo Thư Mục Mẹ (`D:\KEY NHẬT\20-30`) + Hoàn Thiện Bước 2 (`Subtitles .srt`, `End Screen`, `Info Cards`) & `Ghim Comment` ([`youtube_seo_uploader_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_seo_uploader_engine.py)):**
  - **Bộ quét Hàng Đợi Tập Video (`scan_batch_folder_queue`):**
     - Tự động quét toàn bộ 10 tập `20` $\rightarrow$ `29` trong [`D:\KEY NHẬT\20-30`](file:///D:/KEY%20NH%E1%BA%ACT/20-30), tự động ghép nối cả file SEO nằm trong thư mục tập (`SEO.txt`, `K1_04_SEO_AND_THUMBNAIL_PROMPTS.md`) lẫn file SEO nằm ở thư mục cha (`KB_21_SEO.txt` .. `KB_24_SEO.txt`), cộng với `TIMESTAMPS.txt` và `subtitles.srt`.
     - Đối chiếu với `09_UPLOAD_HISTORY.json` và `03_VIDEOS_INVENTORY.json`: Ghi nhận chính xác **Tập 20 (`UPLOADED` — `9w98MWbBh-c`)** và **9 Tập `21` $\rightarrow$ `29` (`READY_PENDING` — đủ 20–26 thẻ Tags và phụ đề `.srt`)**.
  - **Tự động hóa Bước 2 (`_configure_step2_video_elements`) & Ghim Bình Luận (`post_and_pin_first_comment`):**
     - Đính kèm file `subtitles.srt`, mở trình chỉnh sửa `End Screen` gắn mẫu *1 Video + 1 Đăng ký*, mở `Info Cards`, và tự động đăng + bấm **Ghim (`Pin` / `固定`)** bình luận đầu tiên của chủ kênh khi video xuất bản Công khai.
- **[TRỤ CỘT 4] Bộ Hẹn Giờ Tự Động Chạy Ngầm Hàng Ngày (`Daily Autopilot Scheduler` — [`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py)):**
  - Bổ sung `DailyAutopilotScheduler` (`10_AUTOPILOT_SCHEDULE.json`) và luồng nền `autopilot_daemon_loop()` tự động kích hoạt phiên nuôi kênh vào giờ ngẫu nhiên trong khung sáng (`09:15–11:00`) và khung chiều (`15:00–16:45`), nuôi xong tự đóng trình duyệt.

### Phiên bản `v3.0` — Nâng Cấp Tàng Hình Phần Cứng Chống BotGuard Của YouTube (`100% Hardware Input / event.isTrusted = true`)
- **[NÂNG CẤP BẢO MẬT CHỐNG PHÁT HIỆN BOT — `Anti-BotGuard Hardware Stealth` ([`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L470-L867))]:**
  - Triệt tiêu hoàn toàn 4 dấu vết vi mô mà hệ thống **Google BotGuard** dùng để phân biệt kịch bản JS thông thường với người thật:
    1. **Chuyển 100% thao tác Click sang Tín hiệu Phần cứng (`event.isTrusted === true`):** Thay thế lệnh `el.click()` trong JavaScript bằng hàm [`hardware_bezier_move_and_click`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L470-L535). Chuột di chuyển theo **đường cong bậc 3 Cubic Bézier** (9–15 điểm trung gian với nhịp nhanh ở giữa, chậm dần khi chạm mục tiêu + độ lệch ngẫu nhiên $\pm 30\%$ diện tích nút) rồi mới phát xung phần cứng `Input.dispatchMouseEvent` (`mousePressed` $\rightarrow$ trễ 45–115ms $\rightarrow$ `mouseReleased`).
    2. **Chuyển 100% thao tác Cuộn trang sang Con lăn Chuột Phần cứng (`mouseWheel`):** Thay thế `window.scrollBy()` thuần JS bằng [`human_scroll`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L549-L579) phát xung con lăn vật lý `Input.dispatchMouseEvent(type="mouseWheel")` chia thành 3–6 nấc lăn tự nhiên kèm độ rung ngang siêu nhỏ (`deltaX: -1..1`).
    3. **Chuyển Tương tác Video Player sang Phím Bấm Vật Lý (`hardware_press_key`):** Thay vì gán trực tiếp `video.currentTime += 5` hay gọi `video.pause()` trong JS, hàm [`perform_human_player_micro_interaction`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L814-L867) sử dụng phím cứng vật lý `ArrowRight` (tua tới), `ArrowLeft` (tua lùi), `KeyK` (tạm dừng/phát tiếp) qua `Input.dispatchKeyEvent`.
    4. **Zero DOM Mutation (Không chạm vào CSS/DOM của trang):** Loại bỏ hoàn toàn việc chèn viền xanh `el.style.outline` lên thẻ video YouTube và hàng thư Gmail, đảm bảo `MutationObserver` của YouTube thấy DOM sạch 100% nguyên bản.

### Phiên bản `v2.9` — Kiểm Chứng Tải Video Thật Lên YouTube Studio & Điền Đủ 100% Trường SEO Chế Độ Riêng Tư (`Private`)
- **[HOÀN THÀNH TEST UPLOAD THỰC TẾ — TẬP 20 (`Video ID: 9w98MWbBh-c`)]:**
  - **File Video đã tải lên:** [`【漫画】63歳、3社不採用で気づいた。「前職の月給」より大切な仕事選び_5p.mp4`](file:///D:/KEY%20NH%E1%BA%ACT/20-30/20/%E3%80%90%E6%BC%AB%E7%94%BB%E3%80%9163%E6%AD%B3%E3%80%813%E7%A4%BE%E4%B8%8D%E6%8E%A1%E7%94%A8%E3%81%A7%E6%B0%97%E3%81%A5%E3%81%84%E3%81%9F%E3%80%82%E3%80%8C%E5%89%8D%E8%81%B7%E3%81%AE%E6%9C%88%E7%B5%A6%E3%80%8D%E3%82%88%E3%82%8A%E5%A4%A7%E5%88%87%E3%81%AA%E4%BB%95%E4%BA%8B%E9%81%B8%E3%81%B3_5p.mp4) (`114 MB`).
  - **Link Video trên YouTube:** `https://youtu.be/9w98MWbBh-c` (Trang quản trị: `https://studio.youtube.com/video/9w98MWbBh-c/edit`).
  - **Toàn bộ thông tin SEO từ [`SEO.txt`](file:///D:/KEY%20NH%E1%BA%ACT/20-30/20/SEO.txt) & [`TIMESTAMPS.txt`](file:///D:/KEY%20NH%E1%BA%ACT/20-30/20/TIMESTAMPS.txt) đã tự động điền và lưu thành công:**
    1. **Tiêu đề (`Title`):** `【漫画】63歳の再就職で3社不採用。「前職と同じ月給32万円」にこだわり見落としたこと`
    2. **Mô tả (`Description` — 953 ký tự):** Toàn bộ nội dung chuẩn SEO tiếng Nhật + Mục lục Chapters (`00:00`, `00:52`, `02:56`) + Disclaimer + Hashtags (`#定年後 #60代 #再就職 #定年後の仕事`).
    3. **Thẻ từ khóa (`Tags` — đủ 25 thẻ chip):** `60代 再就職 給料`, `60代 再就職`, `63歳 再就職`, `定年後の仕事`, `ハローワーク`, `求人票`, `月給32万円`...
    4. **Đối tượng người xem (COPPA):** `Không, nội dung này không dành cho trẻ em` (`checked = true`).
    5. **Quảng cáo trả tiền:** `Không` (`checked = true`).
    6. **Nội dung tạo/chỉnh sửa bằng AI (`Altered content`):** `Có` (`checked = true`).
    7. **Ngôn ngữ video:** `Tiếng Nhật` (`Japanese`).
    8. **Vị trí video:** `Nhật Bản` (`Japan`).
    9. **Danh mục:** `Mọi người và Blog` (`People & Blogs`).
    10. **Chế độ hiển thị (`Visibility`):** **`Riêng tư` (`Private`)** — Đã lưu hoàn tất trên YouTube Studio.
    11. **Xử lý Thumbnail:** Tự động nén 3 ảnh Thumbnail A/B/C xuống `< 500 KB` (`THUMBNAIL_A.jpg`, `THUMBNAIL_B.jpg`, `THUMBNAIL_C.jpg` tại [`07_THUMBNAILS`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/CHANNELS_DATA/DEPT_01_JAPAN_K1/07_THUMBNAILS)) và tự động bỏ qua bước gắn Thumbnail tùy chỉnh nếu tài khoản chưa xác minh SĐT mà không làm gián đoạn luồng tải video.

### Phiên bản `v2.8` — Khóa Quy Chuẩn SEO & Upload Tự Động Toàn Diện Theo Lựa Chọn Của Người Dùng (12 Hạng Mục YouTube Studio)
- **[NÂNG CẤP] Hoàn thiện Bộ Đọc File SEO Tự Động & Cấu Hình Upload YouTube Studio ([`youtube_seo_uploader_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_seo_uploader_engine.py), [`09_UPLOAD_SEO_CONFIG.json`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/CHANNELS_DATA/DEPT_01_JAPAN_K1/09_UPLOAD_SEO_CONFIG.json), [`09_CAU_HINH_SEO_VA_UPLOAD_KENH.md`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/CHANNELS_DATA/DEPT_01_JAPAN_K1/09_CAU_HINH_SEO_VA_UPLOAD_KENH.md)):**
  - **Nhóm 1 — Tự động đọc từ File SEO (`K1_SEO_MASTER.docx` / `_seo.md`) không cần hỏi lại:**
    1. `Title` (Tiêu đề chính $\le$ 100 ký tự).
    2. `Description` (Mô tả chuẩn SEO tiếng Nhật + Timestamps + Hashtags + Disclaimer).
    3. `Tags` (Bộ thẻ từ khóa $\le$ 500 ký tự).
    4. `Hashtags` (3 hashtag chính + hashtag phụ).
    5. `Thumbnail A/B/C` (Tự động giải nén cả 3 ảnh Thumbnail nhúng trong `K1_SEO_MASTER.docx` ra thư mục `07_THUMBNAILS/`).
    6. `Playlist` (Danh sách phát đề xuất).
    7. `Pinned Comment` (Bình luận ghim đầu tiên dưới video).
    8. `File Phụ đề (.srt)` (Tự động đính kèm nếu có trong thư mục video).
  - **Nhóm 2 — 12 Thiết lập cố định chung trong YouTube Studio đã khóa theo yêu cầu người dùng:**
    - **Thumbnail thích ứng theo tình trạng kênh (`ADAPTIVE_BY_CHANNEL_STATUS`):** Nếu kênh mới (chưa mở tính năng *Test & Compare*) thì tự động tải **1 ảnh tốt nhất (`THUMBNAIL_A`)**; sau này khi kênh mở tính năng nâng cao thì tự động đẩy cả **3 ảnh (`THUMBNAIL_A`, `THUMBNAIL_B`, `THUMBNAIL_C`)** lên.
    - **Giờ tải lên & Lên lịch xuất bản:** Bắt đầu tải video lên vào **giờ ngẫu nhiên (Random)** trong ngày như người thật, sau đó đặt **Lên lịch (`Schedule`) cố định lúc `20:00` hằng ngày** (đã thiết kế sẵn mảng khung giờ để nâng cấp lên **2 video/ngày** sau này).
    - **Danh mục (`Category`):** **Mọi người và Blog (`People & Blogs` / `ブログ`)**.
    - **4 Thành phần tối ưu chuyển đổi bật 100%:** Tự động tải phụ đề `.srt` tiếng Nhật + Tự động thêm **Màn hình kết thúc (`End Screen`: 1 Video + 1 Subscribe ở 20s cuối)** + Tự động thêm **Thẻ đề xuất (`Info Card`)** giữa video & chọn **Playlist** + Tự động đăng và **Ghim bình luận đầu tiên (`Pinned Comment`)**.
    - **Các trường cố định khác:** Không dành cho trẻ em (`COPPA = No`), Không có quảng cáo trả tiền (`False`), **Nội dung tạo bằng AI (`Altered/Synthetic Content = CÓ / Yes`)**, Ngôn ngữ Video & Tiêu đề/Mô tả (`Tiếng Nhật / 日本語`), Địa điểm quay (`Nhật Bản / Japan`).

### Phiên bản `v2.6` — Nuôi Xong Hoặc Bấm Dừng Tự Động Đóng Luôn Cửa Sổ Chrome Profile (Lưu Sạch Cookie & Giải Phóng RAM)
- **[SỬA LỖI] Tự động đóng hẳn cửa sổ Chrome Profile sau khi kết thúc phiên nuôi hoặc khi bấm Dừng ([`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L1049-L1088) & [`youtube_persona_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_persona_engine.py#L794-L802)):**
  - Nguyên nhân: Sau khi nuôi xong, việc để cửa sổ Chrome Profile mở không cần thiết vừa tốn RAM vừa dễ khiến YouTube tự động chạy tiếp.
  - Khắc phục: Bổ sung hàm `BrowserCDPManager.close_channel_browser(cdp_port)` tự động kích hoạt ngay khi hoàn tất phiên nuôi hoặc khi bấm nút **⏹️ Dừng**:
    1. Gửi lệnh CDP `Browser.close` để Chrome ghi toàn bộ Cookie / LocalStorage xuống thư mục Profile (`PROFILES\KENH_01_NHAT_K1`) một cách an toàn.
    2. Đóng hoàn toàn tiến trình `chrome.exe` của cổng `--remote-debugging-port=<cdp_port>`, tắt hẳn cửa sổ trình duyệt trên màn hình để người dùng làm việc khác.

### Phiên bản `v2.5` — Chu Trình Nuôi Tài Khoản Đa Tầng (Omni-Persona Warm-up: Nuôi Gmail + Đọc Báo Nhật + Tìm Kiếm Google Search + YouTube Ngắn Gọn)
- **[NÂNG CẤP] Bổ sung 3 Mô-đun Nuôi Hệ Sinh Thái Google & Cookie Đa Tầng ([`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L818-L1052)):**
  1. **`warmup_gmail_inbox(cdp_port, target_id)` (Nuôi Hòm Thư Gmail):**
     - Truy cập `https://mail.google.com/mail/u/0/#inbox` trên đúng 1 Tab duy nhất.
     - Vuốt rà soát danh sách thư đến (`tr.zA`), quét tiêu đề và người gửi thực tế trong Inbox.
     - Click mở đọc 1–2 email trong hòm thư, cuộn đọc nội dung thư từ trên xuống dưới như người thật rồi quay lại Inbox.
  2. **`warmup_read_news_portal(cdp_port, target_id, language)` (Đọc Báo & Tin Tức Tích Lũy Cookie Báo Chí):**
     - Luân phiên mở các trang báo lớn của Nhật Bản (**Yahoo! Japan News** `https://news.yahoo.co.jp/`, chuyên mục Kinh tế `categories/business`, Đời sống `categories/life`, hoặc **Google News Japan**).
     - Vuốt đọc trang chủ báo, ưu tiên chọn bài báo có chủ đề Kinh tế / Đời sống / Lương hưu / Việc làm (`経済`, `年金`, `仕事`, `定年`, `シニア`, `生活`), click mở bài báo và cuộn đọc 4 nhịp từ đầu đến cuối.
  3. **`warmup_google_search_and_explore(cdp_port, target_id, query, language)` (Nuôi Google Search & Web Activity):**
     - Truy cập `https://www.google.co.jp/`, tìm kiếm các truy vấn đời sống tuổi 60+ (`65歳 年金 働き方 手取り 計算`, `ハローワーク 60代 求人 現実`, `シルバー人材センター 仕事内容 体験談`).
     - Vuốt xem trang kết quả Google SERP, chọn click vào 1 trang web tự nhiên (`#search a h3`) và cuộn đọc nội dung trang web ngoài để tích lũy **Third-Party Cookies & Google Web Activity**.
- **[NÂNG CẤP] Rút gọn thời gian YouTube & Chuyển sang Lịch Trình Xen Kẽ 8 Bước ([`youtube_persona_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_persona_engine.py#L426-L520) & [`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py#L331-L340)):**
  - Thay vì chỉ ngồi trên YouTube 30–35 phút xem 20 video liên tục, chu trình mặc định nay gồm **8 bước ngắn gọn (~5–6 phút/phiên)** xen kẽ tự nhiên:
    - **Bước 1:** Mở Hòm thư Gmail kiểm tra & đọc thư đến (`GMAIL_INBOX`).
    - **Bước 2:** Đọc báo Yahoo! Japan News / Google News (`READ_NEWS_PORTAL`).
    - **Bước 3:** Tìm kiếm Google Search & click đọc trang web ngoài (`GOOGLE_SEARCH_WEB`).
    - **Bước 4 & 5:** Xem 2 video YouTube chuẩn Kênh 1 (ngắn gọn ~25–35s/video, tự tắt quảng cáo + tương tác màn hình + quét nhanh comment 1s).
    - **Bước 6:** Đọc báo đời sống/kinh tế lần 2 (`READ_NEWS_PORTAL`).
    - **Bước 7:** Tìm kiếm Google Search & lướt web ngoài lần 2 (`GOOGLE_SEARCH_WEB`).
    - **Bước 8:** Xem 1 video YouTube chuẩn Kênh 1 và kết thúc phiên.
  - Bổ sung 3 nút bấm tức thì trên Dashboard (`http://127.0.0.1:8077`): **「📧 Đọc Hòm Thư Gmail」**, **「📰 Đọc Báo & Tin Tức Nhật」**, **「🔍 Tìm Kiếm Google & Đọc Web」**.

### Phiên bản `v2.4` — Tự Động Tắt Quảng Cáo Sau Đếm Ngược + Tương Tác Màn Hình Video Như Người Thật (Tua Tới/Lùi, Âm Lượng, Độ Phân Giải) + Quét Nhanh Comment `< 1.8s`
- **[NÂNG CẤP] Tự động phát hiện & tắt quảng cáo sau khi hết thời gian đếm ngược ([`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L626-L685) & [`youtube_persona_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_persona_engine.py#L642-L689)):**
  - Bổ sung hàm `BrowserCDPManager.check_and_skip_youtube_ads(cdp_port, target_id)` kiểm tra trạng thái `#movie_player.ad-showing`, banner overlay `.ytp-ad-overlay-close-button` và các nút `button.ytp-skip-ad-button`, `button.ytp-ad-skip-button`, `button.ytp-ad-skip-button-modern`.
  - Khi gặp quảng cáo có đếm ngược, hệ thống tự động chờ hết giây đếm ngược và bấm **Skip Ad / Bỏ qua quảng cáo** ngay lập tức (kiểm tra ở cả đầu video và giữa video).
- **[NÂNG CẤP] Tương tác vi mô trực tiếp với màn hình Video Player như người thật ([`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py#L687-L813)):**
  - Bổ sung hàm `BrowserCDPManager.perform_human_player_micro_interaction(cdp_port, target_id)` thực hiện ngẫu nhiên các thao tác tự nhiên trong lúc đang xem video:
    1. **Rê chuột đánh thức thanh điều khiển** trên khung hình `#movie_player`.
    2. **Tua nhanh nhẹ (`+5s` / `+10s`)** hoặc **tua lùi xem lại (`-5s` / `-10s`)** đoạn quan trọng.
    3. **Tăng / giảm âm lượng ngẫu nhiên (`38%–82%`)** trên thanh âm thanh player.
    4. **Thay đổi độ phân giải / chất lượng video (`1080p` / `720p`)** qua nút bánh răng cài đặt `button.ytp-settings-button`.
    5. **Tạm dừng ngắn (`2–3 giây`) rồi bấm phát tiếp** để đọc chữ manga trên màn hình.
- **[NÂNG CẤP] Tối ưu tốc độ Quét Bình Luận & Transcript (`< 1.8 giây`) ([`youtube_persona_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/youtube_persona_engine.py#L661-L678) & [`ai_cognitive_brain.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_cognitive_brain.py#L280-L395)):**
  - Khi đang xem video, trình duyệt chỉ cuộn nhanh xuống khu vực `#comments` trong ~0.9 giây để thu thập nhanh bình luận & phụ đề (`TranscriptExtractor.extract_from_active_video_tab`), sau đó lập tức cuộn ngược lên màn hình video chính để xem tiếp.
  - Tối ưu `think_and_write_transcript_comment` và `analyze_community_and_comments_for_k1_upgrade` phản hồi tức thì `< 0.2 giây` (không treo chờ 90 giây).
- **[HOÀN THÀNH PHIÊN NUÔI KÊNH 15/15 VIDEO CHUẨN K1 TRÊN 1 TAB DUY NHẤT]:**
  - Phòng Ban #01 (`DEPT_01_JAPAN_K1` - Port `9301`) đã hoàn thành trọn vẹn phiên xem 15/15 video tiếng Nhật đúng chủ đề Kênh 1 (`ハローワーク`, `シルバー人材センター`, `60歳 再雇用`, `年金`, `定年後の仕事`), trích xuất 140 đoạn phụ đề kèm mốc `mm:ss` và giữ nghiêm ngặt `TabGuard: 1/1 Tab`.

### Phiên bản `v2.2` — Sửa lỗi Mở Profile Đăng Nhập Gmail Trên Desktop Thật & Tích Hợp Bộ Quét Thông Số Kênh Lưu Theo Folder Riêng
- **[SỬA LỖI] Khắc phục triệt để lỗi không hiện cửa sổ Chrome khi bấm mở Profile đăng nhập Gmail/Kênh ([`browser_cdp_manager.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/browser_cdp_manager.py)):**
  - Nguyên nhân: Khi chạy từ tiến trình nền, `subprocess.Popen(..., DETACHED_PROCESS)` mở Chrome trong Desktop ẩn khiến người dùng không nhìn thấy cửa sổ, đồng thời cờ `--disable-blink-features=AutomationControlled` dễ bị trang `accounts.google.com` cảnh báo khi đăng nhập lần đầu.
  - Khắc phục: Chuyển sang cơ chế `_spawn_on_interactive_desktop` qua `schtasks /Create /IT` + `schtasks /Run` kết hợp lệnh CDP `Browser.setWindowBounds` + `Page.bringToFront` và loại bỏ cờ nhạy cảm khi login. Cửa sổ Chrome hiện nổi trực tiếp trên màn hình người dùng với **Tab #1 mở sẵn trang Đăng nhập Google/YouTube** và **Tab #2 mở sẵn YouTube Studio** (giữ khóa cứng $\le$ 2 tab).
- **[NÂNG CẤP] Xây dựng Bộ Máy Quét Thông Tin Kênh & Phân Tích Thông Số Hàng Ngày ([`channel_scanner_engine.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/channel_scanner_engine.py)):**
  - Tự động khởi tạo Folder riêng cho từng kênh tại `D:\YOUTUBE_ENTERPRISE_STUDIO\CHANNELS_DATA\<CHANNEL_ID>\`.
  - Quét trạng thái đăng nhập Gmail/YouTube, Tên kênh, `@handle`, Subscribers, Tổng số video, các thẻ số liệu trong YouTube Studio Dashboard và danh sách video công khai trên kênh.
  - Gọi Bộ Não AI (`SHARED_AI_BRAIN`) đọc thông số thật vừa quét để tự động lập **Báo cáo Phân tích & Kế hoạch Phát triển Kênh Hàng ngày** (`05_PHAN_TICH_VA_KE_HOACH_PHAT_TRIEN_NGAY.md`).
- **[KẾT NỐI KÊNH THẬT & KHỞI CHẠY NUÔI TƯƠNG TÁC — PHÒNG BAN #01 (`Port 9301`)]:**
  - Đã kết nối tài khoản kênh thật trên Chrome Profile #01 (`Nguyen Sơn`, Handle `@NguyenSơn-m9m4k`, Channel ID `UCvYcAYX8D6aaxmW-MWZzJqw`, `Subscribers: 0`, `Số lượt xem 28 ngày: 0`, `Thời gian xem: 0,0 giờ`).
  - Đã lưu toàn bộ thông tin định danh và thông số Studio vào folder riêng `D:\YOUTUBE_ENTERPRISE_STUDIO\CHANNELS_DATA\DEPT_01_JAPAN_K1\` và kích hoạt phiên AI tự suy nghĩ tương tác nuôi kênh (`start_warmup`).
- **[NÂNG CẤP `v2.3`] Khóa Cứng 1 Tab Duy Nhất + Cử Chỉ Vuốt Tìm Kiếm Như Người Thật + Cổng Kiểm Định Tiêu Đề 3 Lớp (`verify_video_matches_channel_dna`):**
  - **Khóa 1 Tab Duy Nhất (`TabGuard.MAX_TABS = 1`):** Tắt ngay lập tức mọi tab thừa không dùng thông qua cả lệnh CDP `Target.closeTarget` và `/json/close/`.
  - **Cử chỉ vuốt dò tìm như người thật (`human_browse_scroll_pattern` & `human_scroll_to_and_click_video`):** Khi tìm kiếm hoặc duyệt danh sách, trình duyệt tự động vuốt xuống từng nhịp, dừng 1.5–2.4s đọc tiêu đề, vuốt nhẹ ngược lên so sánh, sau đó cuộn đưa đúng thẻ video được chọn ra chính giữa màn hình (`scrollIntoView`), viền xanh nhận diện 1.5s và click trực tiếp vào tiêu đề trên DOM.
  - **Cổng Kiểm Định Tiêu Đề 3 Lớp (`verify_video_matches_channel_dna`):**
    1. Lọc bỏ hoàn toàn Home Feed ẩn của SPA YouTube và chỉ lấy video tiếng Nhật khi `language == "ja"`.
    2. Trước khi click: Kiểm tra tiêu đề bắt buộc chứa từ khóa trụ Kênh 1 (`ハローワーク`, `シルバー人材`, `再雇用`, `再就職`, `定年`, `65歳`, `年金`, `求人票`...) và không chứa từ khóa cấm Kênh 2 (`熟年離婚`, `復讐`, `スカッと`, `孤独`).
    3. Sau khi mở `/watch`: Kiểm tra lại thẻ `h1` của video đang phát, nếu không khớp chuẩn K1 lập tức chặn lại và tìm kiếm từ khóa chuẩn.
- **[NÂNG CẤP] Cập nhật Giao diện Localhost Command Center (`http://127.0.0.1:8077` — [`youtube_enterprise_server.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/youtube_enterprise_server.py)):**
  - Bổ sung nút **「🔑 1. Mở Cửa Sổ Chrome Để Đăng Nhập Gmail & Kênh」**, **「📊 2. Đăng Nhập Xong -> Quét Thông Tin Kênh & Lấy Thông Số Studio Lưu Vào Folder Riêng」**, và **「📂 Mở Folder Dữ Liệu Riêng Của Kênh」**.
  - Hiển thị trực tiếp bảng **📁 HỒ SƠ KÊNH THẬT & FOLDER DỮ LIỆU RIÊNG CỦA KÊNH** và **📈 BÁO CÁO PHÂN TÍCH THÔNG SỐ & KẾ HOẠCH PHÁT TRIỂN HÀNG NGÀY** ngay trên Dashboard.

### Phiên bản `v2.1` — Tích hợp 100% AI Cognitive Brain & 20 Điểm Master DNA Kênh 1 (`定年後の人生ラボ【漫画】`)
- Tích hợp 20 điểm Master DNA Kênh 1 ([`K1_MASTER_DNA_20_POINTS.md`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/knowledge/K1_MASTER_DNA_20_POINTS.md)) và bộ não nhận thức [`ai_cognitive_brain.py`](file:///D:/YOUTUBE_ENTERPRISE_STUDIO/engine/ai_cognitive_brain.py).

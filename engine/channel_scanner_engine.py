# -*- coding: utf-8 -*-
"""
Bộ Máy Quét Thông Tin Kênh Thật, Thu Thập Thông Số YouTube Studio Hàng Ngày & Quản Lý Folder Riêng Từng Kênh
(`D:\\YOUTUBE_ENTERPRISE_STUDIO\\CHANNELS_DATA\\<CHANNEL_ID>\\`)
- Tự động kiểm tra trạng thái đăng nhập Gmail + Kênh YouTube trên Chrome Profile của Phòng Ban
- Quét thông tin định danh kênh (Tên kênh, @handle, URL, Subscribers, Tổng số video, Danh sách video đã đăng)
- Quét thông số YouTube Studio Dashboard & Analytics (Views 28 ngày, Watch Time, Subscribers, Realtime 48h, Video hiệu quả nhất)
- Lưu toàn bộ vào Folder riêng của từng kênh và gọi Bộ Não AI (`SHARED_AI_BRAIN`) phân tích kế hoạch phát triển kênh hàng ngày.
"""

import datetime
import json
import os
import time
from typing import Any, Dict, List, Optional

from .browser_cdp_manager import BrowserCDPManager, TabGuard
from .ai_cognitive_brain import SHARED_AI_BRAIN

BASE_STUDIO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS_DATA_ROOT = os.path.join(BASE_STUDIO_DIR, "CHANNELS_DATA")


class ChannelScannerAndAnalyticsEngine:
    """
    Quản lý Folder dữ liệu độc lập cho từng kênh và quét toàn bộ thông số kênh thật sau khi đăng nhập.
    """

    @staticmethod
    def ensure_channel_folder_structure(channel: Dict[str, Any]) -> Dict[str, str]:
        """
        Khởi tạo cấu trúc thư mục riêng biệt cho 1 kênh tại:
        D:\\YOUTUBE_ENTERPRISE_STUDIO\\CHANNELS_DATA\\<CHANNEL_ID>\\
        """
        cid = channel.get("channel_id", "DEPT_01_JAPAN_K1")
        channel_folder = channel.get("channel_data_dir") or os.path.join(CHANNELS_DATA_ROOT, cid)
        analytics_dir = os.path.join(channel_folder, "02_DAILY_ANALYTICS")
        scripts_dir = os.path.join(channel_folder, "06_SCRIPTS_AND_SEO")
        thumbnails_dir = os.path.join(channel_folder, "07_THUMBNAILS")
        transcripts_dir = os.path.join(channel_folder, "08_WATCHED_TRANSCRIPTS")
        ready_videos_dir = os.path.join(channel_folder, "08_READY_VIDEOS_TO_UPLOAD")

        for d in (channel_folder, analytics_dir, scripts_dir, thumbnails_dir, transcripts_dir, ready_videos_dir):
            os.makedirs(d, exist_ok=True)

        paths = {
            "channel_folder": channel_folder,
            "ready_videos_dir": ready_videos_dir,
            "identity_json": os.path.join(channel_folder, "01_CHANNEL_IDENTITY.json"),
            "identity_md": os.path.join(channel_folder, "01_HO_SO_KENH.md"),
            "analytics_dir": analytics_dir,
            "daily_report_md": os.path.join(channel_folder, "02_BAO_CAO_THONG_SO_HANG_NGAY.md"),
            "videos_json": os.path.join(channel_folder, "03_VIDEOS_INVENTORY.json"),
            "videos_md": os.path.join(channel_folder, "03_DANH_SACH_VIDEO_TREN_KENH.md"),
            "comments_json": os.path.join(channel_folder, "04_COMMENTS_AND_COMMUNITY.json"),
            "growth_plan_md": os.path.join(channel_folder, "05_PHAN_TICH_VA_KE_HOACH_PHAT_TRIEN_NGAY.md"),
            "launcher_bat": os.path.join(channel_folder, "MO_PROFILE_DANG_NHAP_KENH.bat"),
        }

        # Nếu chưa có file 01_CHANNEL_IDENTITY.json thì khởi tạo khung mặc định
        if not os.path.isfile(paths["identity_json"]):
            default_identity = {
                "channel_id": cid,
                "department_name": channel.get("department_name", cid),
                "logged_in": False,
                "gmail_account": "",
                "account_display_name": "",
                "detected_channel_title": channel.get("channel_title", ""),
                "detected_handle": "",
                "channel_url": "",
                "studio_url": "https://studio.youtube.com",
                "subscribers_text": "Chưa quét",
                "videos_count_text": "Chưa quét",
                "total_views_text": "Chưa quét",
                "channel_description": "",
                "avatar_url": "",
                "profile_dir": channel.get("profile_dir", ""),
                "cdp_port": channel.get("cdp_port", 9301),
                "last_scanned_at": "Chưa quét (Vui lòng đăng nhập Gmail/Kênh và bấm Quét Thông Tin Kênh)",
            }
            with open(paths["identity_json"], "w", encoding="utf-8") as f:
                json.dump(default_identity, f, ensure_ascii=False, indent=2)

        return paths

    @classmethod
    def load_channel_summary(cls, channel: Dict[str, Any]) -> Dict[str, Any]:
        paths = cls.ensure_channel_folder_structure(channel)
        identity = {}
        videos = []
        latest_analytics = {}
        growth_plan_preview = ""

        if os.path.isfile(paths["identity_json"]):
            try:
                with open(paths["identity_json"], "r", encoding="utf-8") as f:
                    identity = json.load(f)
            except Exception:
                pass

        if os.path.isfile(paths["videos_json"]):
            try:
                with open(paths["videos_json"], "r", encoding="utf-8") as f:
                    vdata = json.load(f)
                    videos = vdata.get("videos", []) if isinstance(vdata, dict) else []
            except Exception:
                pass

        today_str = datetime.date.today().isoformat()
        today_analytics_path = os.path.join(paths["analytics_dir"], f"analytics_{today_str}.json")
        if os.path.isfile(today_analytics_path):
            try:
                with open(today_analytics_path, "r", encoding="utf-8") as f:
                    latest_analytics = json.load(f)
            except Exception:
                pass
        else:
            # Tìm file analytics gần nhất nếu có
            try:
                files = sorted(
                    [fn for fn in os.listdir(paths["analytics_dir"]) if fn.startswith("analytics_") and fn.endswith(".json")]
                )
                if files:
                    with open(os.path.join(paths["analytics_dir"], files[-1]), "r", encoding="utf-8") as f:
                        latest_analytics = json.load(f)
            except Exception:
                pass

        if os.path.isfile(paths["growth_plan_md"]):
            try:
                with open(paths["growth_plan_md"], "r", encoding="utf-8") as f:
                    growth_plan_preview = f.read()[:2500]
            except Exception:
                pass

        return {
            "channel_folder": paths["channel_folder"],
            "identity": identity,
            "videos_count": len(videos),
            "videos_sample": videos[:10],
            "latest_analytics": latest_analytics,
            "growth_plan_preview": growth_plan_preview,
        }

    @classmethod
    def scan_channel_and_analytics(
        cls,
        channel: Dict[str, Any],
        emit_log_fn=None,
    ) -> Dict[str, Any]:
        """
        Quét trực tiếp từ trình duyệt Chrome của Kênh (Port CDP):
        1. Kiểm tra đăng nhập trên YouTube (Tab #1) & lấy thông tin tài khoản / @handle / Avatar.
        2. Mở hoặc kiểm tra YouTube Studio (`https://studio.youtube.com`) trên Tab #2 (giữ khóa cứng <= 2 tab)
           để lấy Subscribers, Views 28 ngày, Watch Time, Realtime 48h, và danh sách video mới nhất.
        3. Nếu kênh có `@handle`, quét thêm trang `https://www.youtube.com/@handle/videos` để lấy danh sách video công khai.
        4. Lưu toàn bộ vào Folder riêng của kênh (`D:\\YOUTUBE_ENTERPRISE_STUDIO\\CHANNELS_DATA\\<CHANNEL_ID>\\`).
        5. Gọi Bộ Não AI (`SHARED_AI_BRAIN`) phân tích các thông số vừa quét để lập kế hoạch phát triển kênh hàng ngày.
        """
        cid = channel["channel_id"]
        port = int(channel["cdp_port"])
        paths = cls.ensure_channel_folder_structure(channel)

        def _log(msg: str, extra: Optional[Dict[str, Any]] = None):
            if emit_log_fn:
                emit_log_fn(cid, 6, msg, extra)

        # Đảm bảo trình duyệt đang mở
        BrowserCDPManager.launch_channel_browser(
            profile_dir=channel["profile_dir"],
            cdp_port=port,
            proxy=channel.get("proxy", ""),
            initial_url="https://www.youtube.com",
            side_by_side_right=True,
        )
        # Quét YouTube Studio trước nếu có tab đang ở Studio, hoặc mở Tab #2 vào Studio
        pages = TabGuard.enforce_max_two_tabs(port)
        studio_tab = next((p for p in pages if "studio.youtube.com" in p.get("url", "")), None)
        yt_tab = next((p for p in pages if "youtube.com" in p.get("url", "") and "studio.youtube.com" not in p.get("url", "")), None)

        if not studio_tab:
            studio_tab = TabGuard.get_or_allocate_tab(port, slot=2, target_url="https://studio.youtube.com")
            time.sleep(4.2)
        if not yt_tab:
            yt_tab = TabGuard.get_or_allocate_tab(
                port,
                slot=1 if (not studio_tab or pages[0].get("id") != studio_tab.get("id")) else 2,
                target_url="https://www.youtube.com",
            )
            time.sleep(3.2)

        TabGuard.enforce_max_two_tabs(port)
        tab1 = yt_tab or TabGuard.get_or_allocate_tab(port, slot=1)
        tab2 = studio_tab or TabGuard.get_or_allocate_tab(port, slot=2)

        _log("🔍 [Quét Kênh - Bước 1/4] Đang kiểm tra trạng thái đăng nhập Gmail & tài khoản YouTube...")

        login_check = {}
        acc_info = {}
        if tab1 and "studio.youtube.com" not in tab1.get("url", ""):
            js_open_account_menu = r"""
            (() => {
                const avatarBtn = document.querySelector('button#avatar-btn, ytd-topbar-menu-button-renderer button#avatar-btn');
                const signInBtn = document.querySelector('a[href*="accounts.google.com/ServiceLogin"], ytd-button-renderer a[aria-label*="Sign in"], ytd-button-renderer a[aria-label*="Đăng nhập"], ytd-button-renderer a[aria-label*="ログイン"]');
                if (avatarBtn) {
                    avatarBtn.click();
                    return { logged_in: true };
                }
                return { logged_in: false, has_signin_btn: !!signInBtn };
            })()
            """
            login_check = BrowserCDPManager.eval_js(port, tab1["id"], js_open_account_menu) or {}
            time.sleep(1.5)

            js_extract_account_popup = r"""
            (() => {
                const avatarImg = document.querySelector('button#avatar-btn img, ytd-active-account-header-renderer img#img');
                const nameEl = document.querySelector('ytd-active-account-header-renderer #account-name, #account-name');
                const handleEl = document.querySelector('ytd-active-account-header-renderer #channel-handle, #channel-handle');
                const emailEl = document.querySelector('ytd-active-account-header-renderer #email, #email');
                const viewChannelLink = Array.from(document.querySelectorAll('ytd-compact-link-renderer a, a#channel-link')).find(a => a.href && (a.href.includes('/@') || a.href.includes('/channel/')));
                document.body.click();
                return {
                    account_name: nameEl ? nameEl.innerText.trim() : '',
                    handle: handleEl ? handleEl.innerText.trim() : '',
                    email: emailEl ? emailEl.innerText.trim() : '',
                    channel_link: viewChannelLink ? viewChannelLink.href : '',
                    avatar_url: avatarImg ? (avatarImg.src || '') : ''
                };
            })()
            """
            acc_info = BrowserCDPManager.eval_js(port, tab1["id"], js_extract_account_popup) or {}

        # Bước 2: Quét YouTube Studio Dashboard
        _log("📊 [Quét Kênh - Bước 2/4] Đang quét thông số trực tiếp từ YouTube Studio Dashboard (Subscribers, Views 28 ngày, Watch Time)...")
        studio_info = {}
        if tab2:
            js_extract_studio = r"""
            (() => {
                const url = window.location.href;
                const title = document.title;
                const isLoginRedirect = url.includes('accounts.google.com');
                if (isLoginRedirect) {
                    return { studio_logged_in: false, current_url: url };
                }

                const bodyLines = (document.body.innerText || '')
                    .split('\n')
                    .map(s => s.trim())
                    .filter(s => s.length > 0 && s.length < 180);

                // Tìm tên kênh ngay sau dòng "Kênh của bạn" / "Your channel" / "あなたのチャンネル"
                let parsedName = '';
                let parsedSubs = '';
                let views28d = '';
                let watchTime28d = '';
                for (let i = 0; i < bodyLines.length; i++) {
                    const line = bodyLines[i];
                    if (['Kênh của bạn', 'Your channel', 'あなたのチャンネル'].includes(line) && i + 1 < bodyLines.length) {
                        parsedName = bodyLines[i + 1];
                    }
                    if (['Số người đăng ký hiện tại', 'Current subscribers', '現在のチャンネル登録者数'].includes(line) && i + 1 < bodyLines.length) {
                        parsedSubs = bodyLines[i + 1];
                    }
                    if (line.startsWith('Số lượt xem') || line.startsWith('Views') || line.startsWith('視聴回数')) {
                        views28d = line.replace(/\t+/g, ': ');
                    }
                    if (line.startsWith('Thời gian xem') || line.startsWith('Watch time') || line.startsWith('総再生時間')) {
                        watchTime28d = line.replace(/\t+/g, ': ');
                    }
                }

                const chNameEl = document.querySelector('#channel-title, ytcp-channel-Crumb #channel-title, .channel-name, #entity-name');
                const subsEl = document.querySelector('#subscriber-count, .metric-value-big, ytcp-Subscribers-metric .metric-value');
                
                // Tìm link @handle trong Studio
                let studioHandle = '';
                let handleHref = '';
                document.querySelectorAll('a[href]').forEach(a => {
                    const h = a.href || '';
                    if (h.includes('/@')) {
                        handleHref = h;
                        const mH = decodeURIComponent(h).match(/\/(@[^/?#]+)/);
                        if (mH) studioHandle = mH[1];
                    }
                });

                const metricCards = [];
                if (parsedSubs !== '') metricCards.push('Số người đăng ký hiện tại: ' + parsedSubs);
                if (views28d) metricCards.push('28 ngày qua - ' + views28d);
                if (watchTime28d) metricCards.push('28 ngày qua - ' + watchTime28d);

                document.querySelectorAll('ytcp-metric-card, .metric-row, ytcp-analytics-summary-item, .summary-item, ytcp-feature-card').forEach(el => {
                    const txt = (el.innerText || '').trim().replace(/\s+/g, ' ');
                    if (txt && txt.length > 2 && txt.length < 300 && !metricCards.includes(txt)) {
                        metricCards.push(txt);
                    }
                });

                const m = url.match(/channel\/(UC[a-zA-Z0-9_-]+)/);
                const ucId = m ? m[1] : '';

                return {
                    studio_logged_in: true,
                    current_url: url,
                    page_title: title,
                    channel_uc_id: ucId,
                    studio_channel_name: (chNameEl ? chNameEl.innerText.trim() : '') || parsedName,
                    studio_handle: studioHandle,
                    studio_handle_href: handleHref,
                    studio_subs_raw: (subsEl ? subsEl.innerText.trim() : '') || parsedSubs || '0',
                    views_28d: views28d || 'Số lượt xem: 0',
                    watch_time_28d: watchTime28d || 'Thời gian xem (giờ): 0,0',
                    metric_cards: metricCards.slice(0, 20),
                    studio_text_lines: bodyLines.slice(0, 120)
                };
            })()
            """
            studio_info = BrowserCDPManager.eval_js(port, tab2["id"], js_extract_studio) or {}

        is_logged_in = bool(login_check.get("logged_in")) or bool(studio_info.get("studio_logged_in"))

        # Bước 3: Quét trang kênh công khai (`/@handle/videos` hoặc `/channel/UC.../videos`) trên Tab #1 để lấy danh sách video, views, mô tả
        channel_handle = acc_info.get("handle") or studio_info.get("studio_handle") or ""
        channel_uc_id = studio_info.get("channel_uc_id", "")
        channel_link = acc_info.get("channel_link") or studio_info.get("studio_handle_href") or ""
        if not channel_link:
            if channel_handle and channel_handle.startswith("@"):
                channel_link = f"https://www.youtube.com/{channel_handle}"
            elif channel_uc_id:
                channel_link = f"https://www.youtube.com/channel/{channel_uc_id}"

        public_channel_data = {}
        if channel_link:
            videos_url = channel_link.rstrip("/") + "/videos"
            _log(f"📹 [Quét Kênh - Bước 3/4] Đang quét danh sách video & chỉ số công khai tại {videos_url} (Tab #1)...")
            TabGuard.navigate_tab(port, tab1["id"], videos_url)
            time.sleep(3.8)
            BrowserCDPManager.human_scroll(port, tab1["id"], distance=650)
            time.sleep(1.2)

            js_extract_public_channel = r"""
            (() => {
                const headerTitle = document.querySelector('yt-dynamic-sizing-formatted-string#channel-name, #channel-header #channel-name, h1.dynamic-text-view-model-wiz__h1');
                const metaSpans = Array.from(document.querySelectorAll('yt-content-metadata-view-model span, #channel-header-container span, #subscriber-count, #videos-count'))
                    .map(s => (s.innerText || '').trim())
                    .filter(Boolean);

                const videos = [];
                const items = document.querySelectorAll('ytd-rich-item-renderer, ytd-grid-video-renderer');
                items.forEach((item, idx) => {
                    if (videos.length >= 30) return;
                    const a = item.querySelector('a#video-title-link, a#video-title');
                    if (!a || !a.href) return;
                    const title = (a.innerText || a.getAttribute('title') || '').trim();
                    const metaEls = Array.from(item.querySelectorAll('#metadata-line span, .inline-metadata-item')).map(x => (x.innerText || '').trim()).filter(Boolean);
                    const durEl = item.querySelector('ytd-thumbnail-overlay-time-status-renderer span, badge-shape .yt-badge-shape__text');
                    videos.push({
                        index: videos.length + 1,
                        title: title,
                        url: a.href,
                        views_text: metaEls[0] || '',
                        published_text: metaEls[1] || '',
                        duration: durEl ? durEl.innerText.trim() : ''
                    });
                });

                return {
                    header_title: headerTitle ? headerTitle.innerText.trim() : '',
                    meta_items: Array.from(new Set(metaSpans)).slice(0, 15),
                    videos: videos
                };
            })()
            """
            public_channel_data = BrowserCDPManager.eval_js(port, tab1["id"], js_extract_public_channel) or {}

        # Tổng hợp thông tin định danh kênh (`01_CHANNEL_IDENTITY.json`)
        detected_title = (
            studio_info.get("studio_channel_name")
            or public_channel_data.get("header_title")
            or acc_info.get("account_name")
            or channel.get("channel_title", "")
        )
        meta_items = public_channel_data.get("meta_items", [])
        subs_text = studio_info.get("studio_subs_raw") or next(
            (m for m in meta_items if any(k in m.lower() for k in ("sub", "đăng ký", "登録者"))), "0"
        )
        vids_count_text = next(
            (m for m in meta_items if any(k in m.lower() for k in ("video", "本", "動画"))),
            f"{len(public_channel_data.get('videos', []))} video",
        )

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        identity_payload = {
            "channel_id": cid,
            "department_name": channel.get("department_name", cid),
            "logged_in": is_logged_in,
            "gmail_account": acc_info.get("email", ""),
            "account_display_name": acc_info.get("account_name", ""),
            "detected_channel_title": detected_title,
            "detected_handle": channel_handle or next((m for m in meta_items if m.startswith("@")), ""),
            "channel_uc_id": channel_uc_id,
            "channel_url": channel_link or "https://www.youtube.com",
            "studio_url": studio_info.get("current_url", "https://studio.youtube.com"),
            "subscribers_text": subs_text,
            "videos_count_text": vids_count_text,
            "header_metadata": meta_items,
            "avatar_url": acc_info.get("avatar_url", ""),
            "profile_dir": channel.get("profile_dir", ""),
            "cdp_port": port,
            "last_scanned_at": now_str,
        }

        with open(paths["identity_json"], "w", encoding="utf-8") as f:
            json.dump(identity_payload, f, ensure_ascii=False, indent=2)

        # Lưu danh sách video (`03_VIDEOS_INVENTORY.json` & `03_DANH_SACH_VIDEO_TREN_KENH.md`)
        videos_list = public_channel_data.get("videos", [])
        videos_payload = {
            "channel_id": cid,
            "channel_title": detected_title,
            "scanned_at": now_str,
            "total_videos_scanned": len(videos_list),
            "videos": videos_list,
        }
        with open(paths["videos_json"], "w", encoding="utf-8") as f:
            json.dump(videos_payload, f, ensure_ascii=False, indent=2)

        videos_md_lines = [
            f"# DANH SÁCH VIDEO ĐÃ ĐĂNG TRÊN KÊNH: {detected_title} ({cid})",
            f"- **Thời điểm quét:** {now_str}",
            f"- **Tổng số video quét được:** {len(videos_list)}",
            "",
            "| # | Tiêu đề Video | Lượt xem | Thời gian đăng | Thời lượng | Link |",
            "|---|---|---|---|---|---|",
        ]
        for v in videos_list:
            videos_md_lines.append(
                f"| {v.get('index')} | {v.get('title')} | {v.get('views_text')} | {v.get('published_text')} | {v.get('duration')} | {v.get('url')} |"
            )
        with open(paths["videos_md"], "w", encoding="utf-8") as f:
            f.write("\n".join(videos_md_lines) + "\n")

        # Lưu thông số YouTube Studio Hàng Ngày (`02_DAILY_ANALYTICS/analytics_YYYY-MM-DD.json`)
        today_str = datetime.date.today().isoformat()
        daily_analytics_file = os.path.join(paths["analytics_dir"], f"analytics_{today_str}.json")
        analytics_payload = {
            "date": today_str,
            "scanned_at": now_str,
            "channel_id": cid,
            "channel_title": detected_title,
            "logged_in": is_logged_in,
            "subscribers_text": subs_text,
            "videos_count_text": vids_count_text,
            "studio_metric_cards": studio_info.get("metric_cards", []),
            "studio_snapshot_lines": studio_info.get("studio_text_lines", []),
            "top_videos_on_channel": videos_list[:10],
        }
        with open(daily_analytics_file, "w", encoding="utf-8") as f:
            json.dump(analytics_payload, f, ensure_ascii=False, indent=2)

        # Bước 4: Gọi Bộ Não AI (`SHARED_AI_BRAIN`) phân tích thông số kênh vừa quét để lập kế hoạch phát triển hàng ngày
        _log("🧠 [Quét Kênh - Bước 4/4] Bộ Não AI đang phân tích thông số kênh & danh sách video để lập Kế hoạch Phát triển Kênh hàng ngày...")
        ai_growth_analysis = cls._generate_ai_daily_channel_audit(
            channel=channel,
            identity=identity_payload,
            analytics=analytics_payload,
            videos=videos_list,
        )

        # Ghi file Hồ Sơ Kênh (`01_HO_SO_KENH.md`)
        identity_md = f"""# HỒ SƠ ĐỊNH DANH KÊNH YOUTUBE: {detected_title}
> **Phòng Ban:** `{cid}` — {channel.get('department_name', '')}
> **Thư mục dữ liệu riêng của kênh:** `{paths['channel_folder']}`
> **Cập nhật lần cuối:** `{now_str}`

## 1. Trạng thái Tài khoản & Định danh
- **Trạng thái đăng nhập Gmail/YouTube:** `{"ĐÃ ĐĂNG NHẬP ✅" if is_logged_in else "CHƯA ĐĂNG NHẬP ⚠️ (Hãy đăng nhập trên cửa sổ Chrome của kênh)"}`
- **Tên kênh phát hiện:** `{detected_title}`
- **Handle (`@`):** `{identity_payload.get('detected_handle') or 'Chưa có'}`
- **Email / Tài khoản:** `{identity_payload.get('gmail_account') or identity_payload.get('account_display_name') or 'Đã ẩn / Chưa hiển thị'}`
- **Channel URL:** {identity_payload.get('channel_url')}
- **YouTube Studio URL:** {identity_payload.get('studio_url')}
- **Số người đăng ký (Subscribers):** `{subs_text}`
- **Số lượng video:** `{vids_count_text}`
- **Chrome Profile cố định:** `{channel.get('profile_dir')}` (Cổng CDP: `{port}`)

## 2. Tóm tắt Thông số YouTube Studio Hôm nay ({today_str})
- **Các thẻ chỉ số Studio quét được:**
{chr(10).join(['  - ' + c for c in studio_info.get('metric_cards', [])[:10]]) or '  - (Chưa có dữ liệu thẻ Studio hoặc kênh mới tạo)'}
"""
        with open(paths["identity_md"], "w", encoding="utf-8") as f:
            f.write(identity_md)

        # Ghi file Báo cáo & Kế hoạch Phát triển Hàng ngày (`05_PHAN_TICH_VA_KE_HOACH_PHAT_TRIEN_NGAY.md` & `02_BAO_CAO_THONG_SO_HANG_NGAY.md`)
        growth_md = f"""# BÁO CÁO PHÂN TÍCH THÔNG SỐ & KẾ HOẠCH PHÁT TRIỂN KÊNH HÀNG NGÀY (DO AI LẬP)
> **Kênh:** `{detected_title}` (`{cid}`)
> **Ngày phân tích:** `{now_str}`
> **Trạng thái đăng nhập:** `{"ĐÃ ĐĂNG NHẬP ✅" if is_logged_in else "CHƯA ĐĂNG NHẬP ⚠️"}`
> **Subscribers:** `{subs_text}` | **Tổng số video:** `{len(videos_list)}`

---

## 🧠 NHẬN ĐỊNH & KẾ HOẠCH PHÁT TRIỂN TỪ BỘ NÃO AI (`AICognitiveBrain`)

{ai_growth_analysis}
"""
        with open(paths["growth_plan_md"], "w", encoding="utf-8") as f:
            f.write(growth_md)
        with open(paths["daily_report_md"], "w", encoding="utf-8") as f:
            f.write(growth_md)

        status_msg = (
            f"✅ Đã quét xong kênh 「{detected_title}」 ({subs_text}, {len(videos_list)} video) và lưu vào folder riêng: {paths['channel_folder']}"
            if is_logged_in
            else f"⚠️ Trình duyệt ở Port {port} hiện CHƯA đăng nhập Gmail/Kênh. Đã tạo sẵn cấu trúc folder riêng tại {paths['channel_folder']} — Bạn hãy đăng nhập trên cửa sổ Chrome vừa bật lên rồi bấm Quét lại!"
        )
        _log(
            status_msg,
            {
                "last_ai_thought": ai_growth_analysis[:380].replace("\n", " "),
                "detected_channel_title": detected_title,
                "detected_handle": identity_payload.get("detected_handle", ""),
                "subscribers_text": subs_text,
                "logged_in": is_logged_in,
                "channel_folder": paths["channel_folder"],
            },
        )

        return {
            "ok": True,
            "logged_in": is_logged_in,
            "channel_folder": paths["channel_folder"],
            "identity": identity_payload,
            "videos_count": len(videos_list),
            "videos": videos_list[:15],
            "analytics": analytics_payload,
            "ai_growth_analysis": ai_growth_analysis,
        }

    @classmethod
    def _generate_ai_daily_channel_audit(
        cls,
        channel: Dict[str, Any],
        identity: Dict[str, Any],
        analytics: Dict[str, Any],
        videos: List[Dict[str, Any]],
    ) -> str:
        """
        Gọi Bộ Não AI (`SHARED_AI_BRAIN`) đọc thông số thật của kênh vừa quét về
        để phân tích hiệu suất và đề xuất chiến lược phát triển kênh trong ngày.
        """
        logged_in = identity.get("logged_in", False)
        title = identity.get("detected_channel_title") or channel.get("channel_title", "")
        subs = identity.get("subscribers_text", "0")
        vcount = len(videos)

        if logged_in:
            prompt = f"""Bạn là Giám Đốc Chiến Lược Phát Triển Kênh YouTube AI của Phòng Ban {channel.get('department_name')}.
Hãy phân tích dữ liệu thực tế vừa quét từ kênh YouTube và lập kế hoạch hành động hôm nay bằng tiếng Việt rõ ràng, thực chiến:

1. THÔNG TIN ĐỊNH DANH KÊNH VỪA QUÉT:
- Trạng thái đăng nhập: {identity.get('logged_in')}
- Tên kênh: {identity.get('detected_channel_title')} ({identity.get('detected_handle')})
- Subscribers: {identity.get('subscribers_text')}
- Số lượng video: {identity.get('videos_count_text')}

2. SỐ LIỆU YOUTUBE STUDIO QUÉT ĐƯỢC:
- Thẻ chỉ số Studio: {json.dumps(analytics.get('studio_metric_cards', [])[:8], ensure_ascii=False)}
- Dòng dữ liệu Studio: {json.dumps(analytics.get('studio_snapshot_lines', [])[:25], ensure_ascii=False)}

3. DANH SÁCH 10 VIDEO MỚI NHẤT / TRÊN KÊNH:
{json.dumps(videos[:10], ensure_ascii=False, indent=2)}

4. ĐỊNH VỊ CHỦ ĐỀ KÊNH (MASTER DNA):
- Niche: {channel.get('niche')}
- Từ khóa trụ cột: {json.dumps(channel.get('seed_keywords', []), ensure_ascii=False)}

Trả về JSON duy nhất:
{{"report_markdown": "Nội dung báo cáo Markdown gồm 3 mục: 1. Chẩn đoán sức khỏe kênh hiện tại; 2. Chiến lược Nuôi tương tác hôm nay (Bàn #1); 3. Đề xuất 3 Tiêu đề Video Tiếp Theo (Bàn #2 & Bàn #3)"}}
"""
            res_json = SHARED_AI_BRAIN.ask_ai_json(
                channel.get("channel_id", "DEPT_01_JAPAN_K1"),
                "DAILY_CHANNEL_AUDIT",
                prompt,
                timeout_sec=40,
            )
            if isinstance(res_json, dict) and res_json.get("report_markdown"):
                return str(res_json["report_markdown"]).strip()

        if not logged_in:
            return (
                f"### 1. Chẩn đoán Trạng thái Kênh (`{title}`)\n"
                f"- **Hiện trạng:** Profile Chrome tại cổng `{identity.get('cdp_port')}` hiện **chưa đăng nhập tài khoản Gmail / YouTube Studio**.\n"
                f"- **Hành động cần làm ngay:** Cửa sổ Chrome thật của kênh đã được bật nổi lên trên màn hình chính. Bạn hãy đăng nhập Gmail & chọn đúng kênh YouTube của mình trên cửa sổ đó, sau đó bấm nút **「📊 Quét Thông Tin Kênh & Lấy Thông Số Studio」**.\n\n"
                f"### 2. Kế hoạch Nuôi Tương Tác Chuẩn Bị Luồng Đề Xuất (Bàn #1)\n"
                f"- Ngay sau khi đăng nhập, AI sẽ thực hiện phiên nuôi 12–16 video/ngày tập trung vào **Trụ A (55–60%): ハローワーク, シルバー人材センター, 60歳 再雇用** để huấn luyện thuật toán YouTube nhận diện đúng tệp khán giả Nhật 60–70+ tuổi.\n\n"
                f"### 3. Đề xuất 3 Tiêu đề Chuẩn DNA Kênh 1 Sẵn Sàng Sản Xuất (Bàn #2 & Bàn #3)\n"
                f"1. `【漫画】65歳でハローワークへ。「まだ働ける」と週5日パートを選んだ元会社員が、半年後に直面した現実`\n"
                f"2. `【漫画】67歳、シルバー人材センターに登録。「軽い仕事」のはずが違った…月5万円でも長く続けるための選択`\n"
                f"3. `【漫画】65歳、月18万円の再雇用と月10万円の週3パート。手取りと体力を比べてわかった定年後の正解`"
            )

        top_vid_info = (
            f"Video gần nhất: 「{videos[0].get('title')}」 ({videos[0].get('views_text')}, đăng {videos[0].get('published_text')})"
            if videos
            else "Hiện chưa phát hiện video công khai trên tab Videos."
        )
        return (
            f"### 1. Chẩn đoán Sức khỏe Kênh Thực tế (`{title}`)\n"
            f"- **Trạng thái:** Đã kết nối tài khoản kênh thành công (`Subscribers: {subs}`, `Số video quét được: {vcount}`).\n"
            f"- **Dữ liệu Video trên kênh:** {top_vid_info}.\n\n"
            f"### 2. Chiến lược Nuôi Tương tác & Kéo Đề Xuất Hôm Nay (Bàn #1)\n"
            f"- Chạy 14–18 lượt xem đa nguồn (40% Search từ khóa `ハローワーク 65歳`, `シルバー人材センター シニア`, `60歳 再雇用 週3`, 40% Home Feed & Cột đề xuất bên phải).\n"
            f"- Để lại 2–3 bình luận có trích dẫn mốc thời gian `mm:ss` dưới các video cùng ngách đang có lượng view cao để thu hút khán giả 60–70+ bấm vào xem hồ sơ kênh `{title}`.\n\n"
            f"### 3. Đề xuất 3 Tiêu đề Tiếp Theo Để Phát Triển Kênh (Bàn #2 & Bàn #3)\n"
            f"1. `【漫画】65歳、ハローワークの「シニア歓迎」に応募した結果…求人票では見えない現場のリアルと続け方`\n"
            f"2. `【漫画】66歳、再雇用で週5日働き続けた末路。半年後に週3日へ変えて気づいた「老後資金と体力」の境界線`\n"
            f"3. `【漫画】67歳、シルバー人材センターで働く現実。予想外だった人間関係と、無理せず月6万円を得る選択`"
        )

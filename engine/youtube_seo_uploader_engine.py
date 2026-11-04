import json
import os
import random
import re
import shutil
import subprocess
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .browser_cdp_manager import BASE_STUDIO_DIR, BrowserCDPManager, TabGuard


DEFAULT_JAPAN_K1_UPLOAD_CONFIG: Dict[str, Any] = {
    "channel_id": "DEPT_01_JAPAN_K1",
    "profile_preset_name": "Chuẩn Kênh Nhật Bản K1 (定年後の人生ラボ【漫画】)",
    "default_batch_queue_dir": r"D:\KEY NHẬT\20-30",
    "auto_from_seo_file": {
        "fields_read_automatically_without_asking": [
            "1. File Video chính (.mp4)",
            "2. Tiêu đề chính (RECOMMENDED FINAL TITLE <= 100 ký tự)",
            "3. Mô tả chuẩn SEO tiếng Nhật (Description + Timestamps + Hashtags + Disclaimer)",
            "4. Bộ Thẻ từ khóa (Tags <= 500 ký tự)",
            "5. Hashtags (#定年後 #60代仕事 #年金 ...)",
            "6. Bộ 3 ảnh Thumbnail A/B/C nhúng trong K1_SEO_MASTER.docx (hoặc ảnh .png trong thư mục tập)",
            "7. Danh sách phát đề xuất (RECOMMENDED_PLAYLIST)",
            "8. Bình luận ghim đầu tiên (PINNED_COMMENT)",
            "9. File phụ đề tiếng Nhật (.srt / subtitles.srt trong cùng thư mục video)",
        ]
    },
    "locked_common_studio_settings": {
        "1_audience_coppa": {
            "made_for_kids": False,
            "age_restriction_18_plus": False,
            "label": "Không, đây không phải là nội dung dành cho trẻ em (No, it's not made for kids)",
        },
        "2_paid_promotion": {
            "has_paid_promotion": False,
            "label": "KHÔNG — Video không có quảng cáo trả tiền / tài trợ (Unchecked)",
        },
        "3_altered_ai_content": {
            "has_altered_or_synthetic_content": True,
            "label": "CÓ (Yes) — Có sử dụng nội dung tạo hoặc chỉnh sửa bằng AI (Altered/Synthetic Content = Yes)",
        },
        "4_automatic_chapters_and_places": {
            "allow_auto_chapters": True,
            "allow_auto_places": True,
            "allow_auto_concepts": True,
            "label": "BẬT — Cho phép phân đoạn tự động, địa điểm và khái niệm",
        },
        "5_language_and_captions": {
            "video_language": "ja",
            "video_language_label": "Tiếng Nhật (Japanese / 日本語)",
            "title_description_language": "ja",
            "title_description_language_label": "Tiếng Nhật (Japanese / 日本語)",
            "caption_certification": "NONE (Chưa từng phát sóng trên truyền hình Hoa Kỳ)",
            "auto_upload_srt_if_found": True,
        },
        "6_recording_date_and_location": {
            "video_location": "Japan",
            "video_location_ja": "日本",
            "use_upload_date_as_recording_date": True,
            "label": "Địa điểm: Nhật Bản (Japan / 日本)",
        },
        "7_license_and_distribution": {
            "license": "Standard YouTube License",
            "allow_embedding": True,
            "publish_to_subscriptions_feed_and_notify": True,
            "shorts_remixing": "allow_video_and_audio",
            "label": "Giấy phép chuẩn YouTube + Cho phép nhúng + Thông báo người đăng ký + Cho phép phối lại Shorts",
        },
        "8_category": {
            "category_name_vi": "Mọi người và Blog (People & Blogs)",
            "category_name_en": "People & Blogs",
            "category_name_ja": "ブログ",
        },
        "9_comments_and_ratings": {
            "comments_mode": "ON",
            "moderation_level": "BASIC",
            "sort_by": "TOP",
            "show_like_count": True,
            "label": "Bật bình luận (Kiểm duyệt Cơ bản) + Xếp theo Hàng đầu (Top) + Hiện số lượt Thích",
        },
        "10_thumbnail_adaptive_policy": {
            "mode": "ADAPTIVE_BY_CHANNEL_STATUS",
            "new_channel_rule": "Tự động tải lên 1 ảnh tốt nhất (THUMBNAIL_A) khi kênh mới chưa mở tính năng Test & Compare (tự động bỏ qua nếu kênh chưa xác minh SĐT)",
            "eligible_channel_rule": "Tự động tải cả 3 ảnh (THUMBNAIL_A, THUMBNAIL_B, THUMBNAIL_C) vào tính năng Thử nghiệm & So sánh (Test & Compare) khi kênh đã mở tính năng nâng cao",
        },
        "11_video_elements_and_conversion": {
            "auto_upload_japanese_srt_subtitles": True,
            "auto_add_end_screen": True,
            "end_screen_layout": "1 Video phù hợp nhất với người xem + 1 Nút Đăng ký (Subscribe) ở 20 giây cuối",
            "auto_add_mid_video_info_card": True,
            "info_card_default_timestamp": "06:30",
            "auto_select_playlist_from_seo": True,
            "auto_post_and_pin_first_comment": True,
        },
        "12_upload_timing_and_schedule": {
            "upload_trigger_time_policy": "RANDOM_HUMAN_WINDOW (Tải video lên vào giờ ngẫu nhiên trong ngày như người thật)",
            "random_upload_window_hours": ["09:15-11:45", "14:10-17:30"],
            "publish_mode": "SCHEDULE",
            "daily_schedule_slots": ["20:00"],
            "future_2_videos_per_day_ready": True,
            "future_2_videos_slots_placeholder": ["12:00", "20:00"],
            "label": "Tải lên vào giờ ngẫu nhiên trong ngày -> Lên lịch xuất bản cố định lúc 20:00 hằng ngày (Sẵn sàng nâng lên 2 video/ngày sau này)",
        },
    },
}


class SEOPackageParser:
    """
    [v3.1] Tự động đọc và bóc tách 100% thông tin từ mọi định dạng File SEO của Kênh 1:
    - Hỗ trợ `K1_SEO_MASTER.docx`, `SEO.txt`, `KB_<ep>_SEO.txt`, `K1_04_SEO_AND_THUMBNAIL_PROMPTS.md`, `K1_05_SEO_THUMBNAIL_PROMPTS.md`.
    - Tự động ghép `TIMESTAMPS.txt` (Chapters `00:00 ...`) và `Hashtags` vào `Description` nếu chưa có.
    - Tự động trích xuất hoặc tạo `PINNED_COMMENT` tiếng Nhật chuẩn tương tác khán giả 60+.
    """

    @staticmethod
    def extract_text_and_images_from_docx(docx_path: str, output_thumb_dir: str) -> Dict[str, Any]:
        text_lines: List[str] = []
        extracted_images: List[str] = []
        os.makedirs(output_thumb_dir, exist_ok=True)

        with zipfile.ZipFile(docx_path, "r") as zf:
            if "word/document.xml" in zf.namelist():
                xml_bytes = zf.read("word/document.xml")
                root = ET.fromstring(xml_bytes)
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                for p in root.findall(".//w:p", ns):
                    texts = [t.text for t in p.findall(".//w:t", ns) if t.text]
                    line = "".join(texts).strip()
                    if line:
                        text_lines.append(line)

            media_files = sorted(
                [name for name in zf.namelist() if name.startswith("word/media/") and not name.endswith("/")]
            )
            labels = ["THUMBNAIL_A", "THUMBNAIL_B", "THUMBNAIL_C"]
            for idx, m_name in enumerate(media_files):
                ext = os.path.splitext(m_name)[1].lower() or ".png"
                tag = labels[idx] if idx < len(labels) else f"THUMBNAIL_{idx + 1}"
                out_file = os.path.join(output_thumb_dir, f"{tag}{ext}")
                with open(out_file, "wb") as f:
                    f.write(zf.read(m_name))
                extracted_images.append(out_file)

        return {
            "raw_text": "\n".join(text_lines),
            "extracted_thumbnails": extracted_images,
        }

    @classmethod
    def parse_seo_file(
        cls,
        seo_file_path: str,
        output_thumb_dir: str,
        timestamps_file_path: str = "",
        episode_dir: str = "",
    ) -> Dict[str, Any]:
        if not seo_file_path or not os.path.exists(seo_file_path):
            return {"ok": False, "error": f"Không tìm thấy file SEO: {seo_file_path}"}

        ext = os.path.splitext(seo_file_path)[1].lower()
        extracted_thumbs: List[str] = []
        if ext == ".docx":
            docx_data = cls.extract_text_and_images_from_docx(seo_file_path, output_thumb_dir)
            raw_text = docx_data["raw_text"]
            extracted_thumbs = docx_data["extracted_thumbnails"]
        else:
            with open(seo_file_path, "r", encoding="utf-8", errors="replace") as f:
                raw_text = f.read()

        # Nếu thư mục tập video có sẵn các file ảnh .png/.jpg thì lấy làm Thumbnail A/B/C
        if not extracted_thumbs and episode_dir and os.path.isdir(episode_dir):
            pngs = sorted(
                [
                    os.path.join(episode_dir, fn)
                    for fn in os.listdir(episode_dir)
                    if fn.lower().endswith((".png", ".jpg", ".jpeg"))
                ]
            )
            extracted_thumbs = pngs[:3]

        # 1. Tiêu đề chính (Title)
        title = ""
        # Ưu tiên RECOMMENDED TITLE có chứa 【漫画】 ở dòng ngay dưới hoặc cùng dòng
        rec_block = re.search(
            r"(?:RECOMMENDED[_\s]*FINAL[_\s]*TITLE|RECOMMENDED[_\s]*TITLE)[:\s\*]*\n+\s*\*?\*?(【漫画】[^\n\*]+)",
            raw_text,
            flags=re.IGNORECASE,
        )
        if rec_block:
            title = rec_block.group(1).strip().strip("* ")

        if not title:
            orig_lock = re.search(
                r"(?:ORIGINAL_TITLE\s*/\s*FINAL TITLE|FINAL[_\s]*TITLE|PRIMARY[_\s]*TITLE)[^\n]*\n+\s*\*?\*?(【漫画】[^\n\*]+)",
                raw_text,
                flags=re.IGNORECASE,
            )
            if orig_lock:
                title = orig_lock.group(1).strip().strip("* ")

        if not title:
            # Tìm dòng có 【漫画】 dài >= 18 ký tự và không phải tiêu đề tài liệu "定年後の人生ラボ【漫画】 — SEO"
            for m in re.finditer(r"【漫画】[^\n\*]{14,96}", raw_text):
                cand = m.group(0).strip().strip("* ")
                if "SEO" in cand or "THUMBNAIL" in cand:
                    continue
                title = cand
                break

        if not title:
            # Hỗ trợ các Key khác (Key Mỹ tiếng Anh, Key Mexico tiếng Tây Ban Nha, Key Nhật không dùng nhãn 【漫画】)
            generic_title_patterns = [
                r"(?:LOCKED[_\s]*TITLE|CURRENT[_\s]*FINAL[_\s]*TITLE|RECOMMENDED[_\s]*FINAL[_\s]*TITLE|PRIMARY[_\s]*TITLE|FINAL[_\s]*TITLE|TIÊU ĐỀ CHÍNH)[:\s\*]*\n*\s*([^\n#\*]{15,105})",
                r"^\s*1\.\s+([^\n#\*]{18,105})",
            ]
            for gpat in generic_title_patterns:
                gm = re.search(gpat, raw_text, flags=re.IGNORECASE | re.MULTILINE)
                if gm:
                    cand = gm.group(1).strip().strip("*\"' ")
                    if "retain ORIGINAL_TITLE" not in cand and "TITLE OPTIONS" not in cand.upper():
                        title = cand
                        break

        # 2. Mô tả video (Description)
        description = ""
        desc_patterns = [
            r"2\.\s*MÔ TẢ[^\n]*\n+=+\n+(.*?)(?=\n+=+\n+3\.\s*TAG|\Z)",
            r"##\s*(?:3\.\s*)?SEO DESCRIPTION[^\n]*\n+(.*?)(?=\n+##\s*(?:4\.|TAGS|SEO TAGS|HASHTAGS|CONVERSION|THUMBNAIL)|\Z)",
            r"(?:JAPANESE SEO DESCRIPTION|VIDEO DESCRIPTION|2\.\s*DESCRIPTION|MÔ TẢ VIDEO)[:\s]*\n(.*?)(?=\n(?:3\.|4\.|##|TAGS|HASHTAGS|SEARCH KEYWORDS|CONVERSION|GLOBAL_STYLE_MASTER|$))",
        ]
        for dpat in desc_patterns:
            dm = re.search(dpat, raw_text, flags=re.IGNORECASE | re.DOTALL)
            if dm and len(dm.group(1).strip()) >= 40:
                description = dm.group(1).strip()
                break

        # 3. Thẻ từ khóa (Tags)
        tags_list: List[str] = []
        tags_section = re.search(
            r"(?:3\.\s*TAG[^\n]*\n+=+|##\s*(?:4\.\s*)?(?:SEO\s+)?TAGS[^\n]*|TAGS\s*\(\d+\)|(?:TAGS|SEARCH KEYWORDS|TỪ KHÓA)[:\s]*)\n+([^\n#=]+(?:\n[^\n#A-Z=]{2,90})?)",
            raw_text,
            flags=re.IGNORECASE,
        )
        if tags_section:
            raw_tags = tags_section.group(1)
            for t in re.split(r"[,、\n]", raw_tags):
                clean_t = t.strip().lstrip("-•* ")
                if 1 < len(clean_t) <= 45 and clean_t not in tags_list:
                    tags_list.append(clean_t)

        # 4. Hashtags
        hashtags = re.findall(r"#[^\s#、,]+", raw_text)
        unique_hashtags: List[str] = []
        for h in hashtags:
            if h not in unique_hashtags:
                unique_hashtags.append(h)
        if not unique_hashtags:
            unique_hashtags = ["#定年後", "#60代", "#再就職", "#定年後の仕事", "#漫画"]

        # Ghép thêm TIMESTAMPS.txt và Hashtags vào Description nếu có
        if not timestamps_file_path and episode_dir:
            cand_ts = os.path.join(episode_dir, "TIMESTAMPS.txt")
            if os.path.exists(cand_ts):
                timestamps_file_path = cand_ts

        timestamps_text = ""
        if timestamps_file_path and os.path.exists(timestamps_file_path):
            try:
                with open(timestamps_file_path, "r", encoding="utf-8", errors="replace") as tf:
                    ts_lines = [
                        ln.strip()
                        for ln in tf.read().splitlines()
                        if re.match(r"^\d{1,2}:\d{2}\s+", ln.strip())
                    ]
                    if ts_lines:
                        timestamps_text = "【目次】\n" + "\n".join(ts_lines)
            except Exception:
                pass

        full_description = description
        if timestamps_text and "00:00" not in full_description:
            full_description = full_description.rstrip() + "\n\n" + timestamps_text
        if unique_hashtags and not any(h in full_description for h in unique_hashtags[:2]):
            full_description = full_description.rstrip() + "\n\n" + " ".join(unique_hashtags[:6])

        # 5. Bình luận ghim (Pinned Comment)
        pinned_comment = ""
        pin_match = re.search(
            r"(?:PINNED_COMMENT|PINNED COMMENT|BÌNH LUẬN GHIM)[:\s]*\n?([^\n]+(?:\n[^\n#]+){0,4})",
            raw_text,
            flags=re.IGNORECASE,
        )
        if pin_match:
            pinned_comment = pin_match.group(1).strip().replace("\\n", "\n")

        if not pinned_comment:
            # Tự động trích đoạn câu hỏi tương tác khán giả trong Description làm Bình luận ghim chuẩn Nhật
            q_para = ""
            for para in description.split("\n"):
                p_clean = para.strip()
                if "皆さんは" in p_clean or "コメントで教えて" in p_clean:
                    q_para = p_clean
                    break
            if q_para:
                pinned_comment = (
                    f"{q_para}\n"
                    "定年後の仕事・お金・暮らしについて、これからも具体的な物語を漫画でお届けします。よろしければチャンネル登録をお願いします。"
                )
            else:
                pinned_comment = (
                    "皆さんは、定年後の仕事や働き方を選ぶとき、どんな条件を一番大切にしていますか？ぜひコメントで体験やご意見を教えてください。\n"
                    "「定年後の人生ラボ【漫画】」では、これからも定年後の仕事・お金・暮らしの物語をお届けします。"
                )

        # 6. Danh sách phát đề xuất (Playlist)
        playlist_name = "60代の仕事・再就職"
        pl_match = re.search(
            r"(?:RECOMMENDED_PLAYLIST|PLAYLIST|DANH SÁCH PHÁT)[:\s]*([^\n]+)",
            raw_text,
            flags=re.IGNORECASE,
        )
        if pl_match:
            playlist_name = pl_match.group(1).strip()

        # 7. Mốc gắn thẻ giữa video (Mid-video CTA timestamp)
        mid_cta_time = "03:30"
        cta_match = re.search(r"(\d{1,2}:\d{2})", raw_text)
        if cta_match:
            mid_cta_time = cta_match.group(1)

        return {
            "ok": True,
            "seo_file_path": seo_file_path,
            "title": title[:100],
            "description": full_description[:4950],
            "tags": tags_list[:28],
            "tags_csv": ", ".join(tags_list)[:495],
            "hashtags": unique_hashtags[:15],
            "pinned_comment": pinned_comment,
            "recommended_playlist": playlist_name,
            "mid_video_card_timestamp": mid_cta_time,
            "extracted_thumbnails": extracted_thumbs,
        }


class YouTubeStudioAutoUploader:
    """
    [v3.1] Bàn #6: Bộ máy Tự động Quét Hàng Đợi Tập Video (`Batch Folder Queue`), Tải Video lên YouTube Studio,
    Điền 100% trường SEO (Bước 1: Chi tiết + Bước 2: Phụ đề .srt, Màn hình kết thúc End Screen, Thẻ Info Card + Bước 4: Lên lịch / Riêng tư)
    và Tự động Đăng + Ghim Bình Luận Đầu Tiên (`Pinned Comment`).
    """

    @staticmethod
    def ensure_channel_upload_config(channel_folder: str, channel_id: str) -> Dict[str, Any]:
        cfg_path = os.path.join(channel_folder, "09_UPLOAD_SEO_CONFIG.json")
        md_path = os.path.join(channel_folder, "09_CAU_HINH_SEO_VA_UPLOAD_KENH.md")
        cfg = dict(DEFAULT_JAPAN_K1_UPLOAD_CONFIG)
        cfg["channel_id"] = channel_id
        cfg["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs(channel_folder, exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

        # Khởi tạo lịch sử tải lên 09_UPLOAD_HISTORY.json (ghi nhận sẵn Tập 20 đã upload thành công)
        hist_path = os.path.join(channel_folder, "09_UPLOAD_HISTORY.json")
        if not os.path.exists(hist_path):
            initial_history = {
                "channel_id": channel_id,
                "uploaded_episodes": {
                    "20": {
                        "episode_id": "20",
                        "video_id": "9w98MWbBh-c",
                        "youtube_url": "https://youtu.be/9w98MWbBh-c",
                        "studio_edit_url": "https://studio.youtube.com/video/9w98MWbBh-c/edit",
                        "title": "【漫画】63歳の再就職で3社不採用。「前職と同じ月給32万円」にこだわり見落としたこと",
                        "visibility": "PRIVATE",
                        "uploaded_at": "2026-10-29 19:15:00",
                    }
                },
            }
            with open(hist_path, "w", encoding="utf-8") as hf:
                json.dump(initial_history, hf, ensure_ascii=False, indent=2)

        md_content = f"""# BỘ QUY CHUẨN SEO & UPLOAD TỰ ĐỘNG — KÊNH `{channel_id}` (`v3.1`)

> **Cập nhật lần cuối:** `{cfg['updated_at']}`
> **File cấu hình JSON:** `09_UPLOAD_SEO_CONFIG.json`
> **File lịch sử Hàng đợi Upload:** `09_UPLOAD_HISTORY.json`

---

## PHẦN 1: HÀNG ĐỢI QUÉT TỰ ĐỘNG THEO THƯ MỤC MẸ (`D:\\KEY NHẬT\\20-30`)
- Hệ thống tự động quét các thư mục tập (`20`, `21`, `22`... `29`), tự tìm:
  1. File Video `.mp4`.
  2. File SEO (`SEO.txt`, `K1_04_SEO_AND_THUMBNAIL_PROMPTS.md`, `K1_SEO_MASTER.docx` hoặc `KB_<Tập>_SEO.txt` ở thư mục cha).
  3. File Mục lục `TIMESTAMPS.txt` & File Phụ đề `subtitles.srt`.
  4. Bộ ảnh Thumbnail `.png` / `.jpg` trong thư mục tập.
- Đối chiếu với `09_UPLOAD_HISTORY.json` và `03_VIDEOS_INVENTORY.json` để đánh dấu tập nào **ĐÃ ĐĂNG (`UPLOADED`)**, tập nào **CHỜ ĐĂNG (`PENDING`)**.

---

## PHẦN 2: 12 THIẾT LẬP CỐ ĐỊNH CHUNG TRONG YOUTUBE STUDIO (ĐÃ KHÓA CHO KÊNH NHẬT K1)
| STT | Hạng mục trong YouTube Studio | Giá trị mặc định đã khóa |
| :--- | :--- | :--- |
| **1** | **Đối tượng người xem (COPPA)** | **Không**, đây không phải là nội dung dành cho trẻ em (*No, not made for kids*) |
| **2** | **Quảng cáo trả tiền / Tài trợ** | **KHÔNG** tích chọn (*Unchecked*) |
| **3** | **Nội dung tạo / chỉnh sửa bằng AI** | **CÓ (Yes)** — Có sử dụng âm thanh hoặc hình ảnh tạo bằng AI |
| **4** | **Phân đoạn / Địa điểm / Khái niệm tự động** | **BẬT** toàn bộ 3 mục tự động |
| **5** | **Ngôn ngữ Video & Tiêu đề/Mô tả** | **Tiếng Nhật (`Japanese / 日本語`)** |
| **6** | **Vị trí quay (Video Location)** | **Nhật Bản (`Japan / 日本`)** |
| **7** | **Giấy phép & Phối lại Shorts** | **Giấy phép chuẩn YouTube** + Cho phép nhúng + Cho phép phối lại video & âm thanh |
| **8** | **Danh mục (Category)** | **Mọi người và Blog (`People & Blogs` / `ブログ`)** |
| **9** | **Bình luận & Lượt thích** | **Bật bình luận** (Kiểm duyệt Cơ bản) + Xếp theo **Hàng đầu (Top)** + **Hiện số lượt thích** |
| **10** | **Bước 2 — Phụ đề, Màn hình kết thúc & Thẻ** | Tải file `subtitles.srt` + Gắn **End Screen** (1 Video + 1 Nút Subscribe ở 20s cuối) + Gắn **Thẻ (Card)** giữa video |
| **11** | **Giờ tải video lên (Upload Trigger)** | **Ngẫu nhiên (Random)** trong khung giờ sinh hoạt người thật (`09:15–11:45` hoặc `14:10–17:30`) |
| **12** | **Chế độ xuất bản (Visibility / Schedule)** | **Lên lịch (`Schedule`) cố định lúc `20:00` hằng ngày** (hoặc `Private` khi test) + **Tự động Đăng & Ghim Bình Luận Đầu Tiên** |
"""
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        return cfg

    @staticmethod
    def auto_generate_seo_for_video_if_missing(video_file_path: str, language: str = "ja") -> str:
        """
        [v3.7] Khi người dùng tự cung cấp file `.mp4` (chép từ máy dựng video sang mà chưa kèm file SEO),
        tự động tạo ngay `<ten_video>_AUTO_SEO.txt` chuẩn SEO theo ngôn ngữ kênh (`ja` / `en` / `es`)
        để hệ thống sẵn sàng Đẩy Lên Trước & Hẹn Giờ Public mà không bị kẹt.
        """
        if not video_file_path or not os.path.exists(video_file_path):
            return ""
        ep_dir = os.path.dirname(os.path.abspath(video_file_path))
        stem = os.path.splitext(os.path.basename(video_file_path))[0]
        clean_stem = re.sub(r"[_\-]+", " ", stem).strip()
        auto_seo_path = os.path.join(ep_dir, f"{stem}_AUTO_SEO.txt")
        if os.path.exists(auto_seo_path):
            return auto_seo_path

        lang = (language or "ja").lower()
        if lang == "es":
            title = clean_stem if len(clean_stem) >= 18 else f"Historia Familiar Conmovedora — {clean_stem}"
            desc = (
                f"{title}\n\n"
                "Una historia profunda sobre la familia, la dignidad y las decisiones que cambian el destino.\n"
                "Déjanos tu opinión en los comentarios y suscríbete para más relatos.\n\n"
                "00:00 Inicio de la historia\n05:00 Desarrollo del conflicto\n12:00 El momento de la verdad\n\n"
                "#DramaFamiliar #HistoriasDeVida #Mexico #Reflexion #Familia"
            )
            tags = "drama familiar mexico, historias de vida, relatos conmovedores, adultos mayores, justicia familiar"
            pin = "¿Qué habrías hecho tú en esta situación? Cuéntanos tu opinión en los comentarios."
        elif lang == "en":
            title = clean_stem if len(clean_stem) >= 18 else f"Emotional Family Story — {clean_stem}"
            desc = (
                f"{title}\n\n"
                "An inspiring life story about family, resilience, and unexpected turning points.\n"
                "Share your thoughts in the comments below and subscribe for new episodes.\n\n"
                "00:00 Introduction\n05:00 Turning Point\n12:00 Final Resolution\n\n"
                "#LifeStories #FamilyDrama #EmotionalStory #Storytime"
            )
            tags = "emotional family story, life lessons, family drama story, inspiring stories, storytime"
            pin = "What are your thoughts on this story? Let us know in the comments below!"
        else:
            title = clean_stem if "【漫画】" in clean_stem else f"【漫画】{clean_stem}"
            if len(title) < 18:
                title = f"【漫画】定年後の人生と仕事・暮らしの物語 — {clean_stem}"
            desc = (
                f"{title}\n\n"
                "定年後の仕事・お金・人間関係について考えるオリジナル漫画ストーリーです。\n"
                "皆さんのご意見やご経験をぜひコメント欄で教えてください。\n\n"
                "【目次】\n00:00 オープニング\n04:30 転機と葛藤\n12:00 新たな気づきと決断\n\n"
                "#定年後 #60代 #シニア #再就職 #漫画"
            )
            tags = "定年後, 60代 仕事, シニア 再就職, 年金 暮らし, 漫画, 人生劇場, 定年後の人生ラボ"
            pin = "皆さんはこの物語についてどう思われましたか？ぜひコメント欄でご意見や体験談を教えてください。"

        content = (
            f"RECOMMENDED FINAL TITLE:\n{title[:100]}\n\n"
            f"2. DESCRIPTION:\n{desc}\n\n"
            f"3. TAGS:\n{tags}\n\n"
            f"PINNED_COMMENT:\n{pin}\n"
        )
        try:
            with open(auto_seo_path, "w", encoding="utf-8") as f:
                f.write(content)
            return auto_seo_path
        except Exception:
            return ""

    @staticmethod
    def load_upload_history(channel_folder: str) -> Dict[str, Any]:
        hist_path = os.path.join(channel_folder, "09_UPLOAD_HISTORY.json")
        if os.path.exists(hist_path):
            try:
                with open(hist_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"uploaded_episodes": {}}

    @staticmethod
    def record_uploaded_episode(
        channel_folder: str,
        episode_id: str,
        video_id: str,
        title: str,
        visibility: str,
        video_file_path: str = "",
        scheduled_publish_date: str = "",
        scheduled_publish_time: str = "",
    ) -> None:
        hist_path = os.path.join(channel_folder, "09_UPLOAD_HISTORY.json")
        data = YouTubeStudioAutoUploader.load_upload_history(channel_folder)
        if "uploaded_episodes" not in data:
            data["uploaded_episodes"] = {}
        data["uploaded_episodes"][str(episode_id)] = {
            "episode_id": str(episode_id),
            "video_id": video_id,
            "youtube_url": f"https://youtu.be/{video_id}" if video_id else "",
            "studio_edit_url": f"https://studio.youtube.com/video/{video_id}/edit" if video_id else "",
            "title": title,
            "visibility": visibility,
            "scheduled_publish_date": scheduled_publish_date,
            "scheduled_publish_time": scheduled_publish_time,
            "scheduled_display": f"{scheduled_publish_date} {scheduled_publish_time}".strip(),
            "video_file_path": video_file_path,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        os.makedirs(channel_folder, exist_ok=True)
        with open(hist_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def scan_batch_folder_queue(
        cls,
        channel_folder: str,
        parent_batch_dir: str = r"D:\KEY NHẬT\20-30",
        language: str = "ja",
    ) -> Dict[str, Any]:
        """
        [v3.7] Quét Hàng Đợi Video Đa Nguồn (Hỗ trợ cả Video Người Dùng Tự Cung Cấp & Thư Mục Tập Sản Xuất):
        1. Quét thư mục riêng của kênh `CHANNELS_DATA/<CHANNEL_ID>/08_READY_VIDEOS_TO_UPLOAD` (nơi người dùng chép nhanh file `.mp4` vào).
        2. Quét thư mục mẹ `parent_batch_dir` (ví dụ: `D:\\KEY NHẬT\\20-30` hoặc thư mục bất kỳ do người dùng chọn).
        3. Hỗ trợ cả 2 cấu trúc:
           - Cấu trúc Thư mục con theo Tập (`20/`, `21/`, `Tap_01/`...).
           - Cấu trúc File `.mp4` thả trực tiếp (`Drop-and-Go MP4`) — nếu chưa có file SEO kèm theo thì tự động tạo `<ten_file>_AUTO_SEO.txt`!
        """
        cls.ensure_channel_upload_config(channel_folder, os.path.basename(channel_folder))
        ready_drop_dir = os.path.join(channel_folder, "08_READY_VIDEOS_TO_UPLOAD")
        os.makedirs(ready_drop_dir, exist_ok=True)

        history = cls.load_upload_history(channel_folder).get("uploaded_episodes", {})

        inv_titles: List[str] = []
        inv_path = os.path.join(channel_folder, "03_VIDEOS_INVENTORY.json")
        if os.path.exists(inv_path):
            try:
                with open(inv_path, "r", encoding="utf-8") as f:
                    inv_data = json.load(f)
                    for v in inv_data.get("videos", []):
                        if v.get("title"):
                            inv_titles.append(v["title"].strip())
            except Exception:
                pass

        scan_roots: List[str] = []
        if os.path.isdir(ready_drop_dir):
            scan_roots.append(ready_drop_dir)
        if parent_batch_dir and os.path.isdir(parent_batch_dir) and os.path.abspath(parent_batch_dir) != os.path.abspath(ready_drop_dir):
            scan_roots.append(parent_batch_dir)

        if not scan_roots:
            return {
                "ok": False,
                "parent_batch_dir": parent_batch_dir,
                "ready_drop_dir": ready_drop_dir,
                "error": f"Không tìm thấy thư mục chứa video: {parent_batch_dir}",
                "episodes": [],
            }

        episodes_list: List[Dict[str, Any]] = []
        seen_video_paths = set()
        thumb_cache_dir = os.path.join(channel_folder, "07_THUMBNAILS")

        for root_dir in scan_roots:
            source_tag = "USER_DROP_FOLDER" if os.path.abspath(root_dir) == os.path.abspath(ready_drop_dir) else "BATCH_QUEUE_DIR"

            # A. Quét các file .mp4 lẻ được người dùng thả trực tiếp vào thư mục gốc
            direct_mp4s = sorted(
                [
                    f
                    for f in os.listdir(root_dir)
                    if os.path.isfile(os.path.join(root_dir, f)) and f.lower().endswith(".mp4")
                ]
            )
            for mp4_fn in direct_mp4s:
                video_path = os.path.join(root_dir, mp4_fn)
                if os.path.abspath(video_path).lower() in seen_video_paths:
                    continue
                seen_video_paths.add(os.path.abspath(video_path).lower())
                stem = os.path.splitext(mp4_fn)[0]
                ep_name = stem

                # Tìm file SEO cùng tên hoặc tự sinh nếu chỉ có file .mp4
                seo_cand = ""
                for ext in (".txt", ".md", ".docx"):
                    for pattern_fn in (f"{stem}_SEO{ext}", f"{stem}_AUTO_SEO{ext}", f"{stem}{ext}", f"KB_{stem}_SEO{ext}"):
                        p_cand = os.path.join(root_dir, pattern_fn)
                        if os.path.exists(p_cand):
                            seo_cand = p_cand
                            break
                    if seo_cand:
                        break
                if not seo_cand:
                    seo_cand = cls.auto_generate_seo_for_video_if_missing(video_path, language=language)

                srt_cand = os.path.join(root_dir, f"{stem}.srt")
                srt_path = srt_cand if os.path.exists(srt_cand) else ""
                parsed_preview = (
                    SEOPackageParser.parse_seo_file(seo_cand, thumb_cache_dir, episode_dir=root_dir)
                    if seo_cand
                    else {}
                )
                seo_title = parsed_preview.get("title") or stem
                hist_rec = history.get(str(ep_name))
                already_on_channel = any(seo_title[:22] in t for t in inv_titles if len(seo_title) >= 22)
                is_uploaded = bool(hist_rec or already_on_channel)

                episodes_list.append({
                    "episode_id": ep_name,
                    "source_type": source_tag,
                    "episode_dir": root_dir,
                    "video_file_path": video_path,
                    "video_file_name": mp4_fn,
                    "video_size_mb": round(os.path.getsize(video_path) / (1024 * 1024), 1) if os.path.exists(video_path) else 0,
                    "seo_file_path": seo_cand,
                    "seo_file_name": os.path.basename(seo_cand) if seo_cand else "",
                    "srt_file_path": srt_path,
                    "timestamps_file_path": "",
                    "parsed_title": seo_title,
                    "tags_count": len(parsed_preview.get("tags") or []),
                    "has_srt": bool(srt_path),
                    "status": "UPLOADED" if is_uploaded else ("READY_PENDING" if video_path else "MISSING_FILES"),
                    "uploaded_info": hist_rec or {},
                })

            # B. Quét các thư mục con theo từng Tập (`20`, `21`, `Tap_01`...)
            subdirs = sorted(
                [
                    d
                    for d in os.listdir(root_dir)
                    if os.path.isdir(os.path.join(root_dir, d)) and d.lower() not in ("agent", "_proxy_auth_ext")
                ],
                key=lambda x: (0, int(x)) if x.isdigit() else (1, x),
            )

            for ep_name in subdirs:
                ep_dir = os.path.join(root_dir, ep_name)
                files_in_ep = os.listdir(ep_dir)

                mp4_files = sorted(
                    [os.path.join(ep_dir, f) for f in files_in_ep if f.lower().endswith(".mp4")]
                )
                video_path = mp4_files[0] if mp4_files else ""
                if video_path:
                    if os.path.abspath(video_path).lower() in seen_video_paths:
                        continue
                    seen_video_paths.add(os.path.abspath(video_path).lower())

                seo_candidates = [
                    os.path.join(ep_dir, f)
                    for f in files_in_ep
                    if ("seo" in f.lower() and f.lower().endswith((".txt", ".md", ".docx")))
                ]
                parent_seo_cand = os.path.join(root_dir, f"KB_{ep_name}_SEO.txt")
                if not seo_candidates and os.path.exists(parent_seo_cand):
                    seo_candidates.append(parent_seo_cand)
                seo_path = seo_candidates[0] if seo_candidates else ""

                # Nếu thư mục tập đã có file .mp4 do người dùng cung cấp nhưng chưa có file SEO -> Tự sinh SEO ngay!
                if video_path and not seo_path:
                    seo_path = cls.auto_generate_seo_for_video_if_missing(video_path, language=language)

                srt_candidates = [os.path.join(ep_dir, f) for f in files_in_ep if f.lower().endswith(".srt")]
                srt_path = srt_candidates[0] if srt_candidates else ""
                ts_path = os.path.join(ep_dir, "TIMESTAMPS.txt") if "TIMESTAMPS.txt" in files_in_ep else ""

                parsed_preview = (
                    SEOPackageParser.parse_seo_file(seo_path, thumb_cache_dir, timestamps_file_path=ts_path, episode_dir=ep_dir)
                    if seo_path
                    else {}
                )
                seo_title = parsed_preview.get("title") or (os.path.splitext(os.path.basename(video_path))[0] if video_path else f"Tập {ep_name}")

                hist_rec = history.get(str(ep_name))
                already_on_channel = any(seo_title[:22] in t for t in inv_titles if len(seo_title) >= 22)
                is_uploaded = bool(hist_rec or already_on_channel)

                episodes_list.append({
                    "episode_id": ep_name,
                    "source_type": source_tag,
                    "episode_dir": ep_dir,
                    "video_file_path": video_path,
                    "video_file_name": os.path.basename(video_path) if video_path else "",
                    "video_size_mb": round(os.path.getsize(video_path) / (1024 * 1024), 1) if video_path and os.path.exists(video_path) else 0,
                    "seo_file_path": seo_path,
                    "seo_file_name": os.path.basename(seo_path) if seo_path else "",
                    "srt_file_path": srt_path,
                    "timestamps_file_path": ts_path,
                    "parsed_title": seo_title,
                    "tags_count": len(parsed_preview.get("tags") or []),
                    "has_srt": bool(srt_path),
                    "status": "UPLOADED" if is_uploaded else ("READY_PENDING" if (video_path and seo_path) else "MISSING_FILES"),
                    "uploaded_info": hist_rec or {},
                })

        pending_eps = [e for e in episodes_list if e["status"] == "READY_PENDING"]
        uploaded_eps = [e for e in episodes_list if e["status"] == "UPLOADED"]

        return {
            "ok": True,
            "parent_batch_dir": parent_batch_dir,
            "ready_drop_dir": ready_drop_dir,
            "total_episodes": len(episodes_list),
            "uploaded_count": len(uploaded_eps),
            "pending_count": len(pending_eps),
            "next_pending_episode": pending_eps[0] if pending_eps else None,
            "episodes": episodes_list,
        }

    @classmethod
    def compute_next_available_schedule_slot(
        cls,
        channel_folder: str,
        publish_hour_str: str = "20:00",
        min_lead_hours: float = 1.5,
        custom_schedule_date: str = "",
        custom_schedule_time: str = "",
    ) -> Dict[str, Any]:
        """
        [v3.7] TÍNH TOÁN KHUNG GIỜ HẸN LỊCH PUBLIC TỰ ĐỘNG KHI ĐẨY VIDEO LÊN TRƯỚC (PRE-UPLOAD & SCHEDULE):
        - Đảm bảo đẩy video lên trước giờ Public ít nhất `min_lead_hours` (mặc định 1.5 – 3 tiếng) để YouTube kịp xử lý HD/4K và kiểm tra bản quyền.
        - Tự động đọc `09_UPLOAD_HISTORY.json` để kiểm tra những ngày nào đã có video hẹn giờ rồi -> Nếu bạn đẩy trước 3–5 video liên tiếp trong 1 buổi,
          hệ thống tự động rải lịch nối tiếp nhau sang các ngày tiếp theo (`Ngày 1 - 20:00`, `Ngày 2 - 20:00`, `Ngày 3 - 20:00`...).
        """
        now = datetime.now()
        clean_time = (custom_schedule_time or publish_hour_str or "20:00").strip()
        if not re.match(r"^\d{1,2}:\d{2}$", clean_time):
            clean_time = "20:00"
        hh, mm = [int(x) for x in clean_time.split(":")]
        clean_time = f"{hh:02d}:{mm:02d}"

        if custom_schedule_date and re.match(r"^\d{4}-\d{2}-\d{2}$", custom_schedule_date.strip()):
            c_date = custom_schedule_date.strip()
            return {
                "scheduled_publish_date": c_date,
                "scheduled_publish_time": clean_time,
                "scheduled_display": f"{c_date} {clean_time}",
                "mode": "CUSTOM_USER_SLOT",
            }

        history = cls.load_upload_history(channel_folder).get("uploaded_episodes", {})
        booked_dates = {
            str(info.get("scheduled_publish_date") or "").strip()
            for info in history.values()
            if str(info.get("visibility") or "").upper() == "SCHEDULE" and info.get("scheduled_publish_date")
        }

        for day_offset in range(0, 30):
            cand_dt = (now + timedelta(days=day_offset)).replace(hour=hh, minute=mm, second=0, microsecond=0)
            cand_date_str = cand_dt.strftime("%Y-%m-%d")
            # Nếu là hôm nay nhưng thời gian còn lại tới giờ Public ít hơn min_lead_hours -> Đẩy sang ngày mai
            if (cand_dt - now).total_seconds() < (min_lead_hours * 3600.0):
                continue
            if cand_date_str in booked_dates:
                continue
            lead_hrs = round((cand_dt - now).total_seconds() / 3600.0, 1)
            return {
                "scheduled_publish_date": cand_date_str,
                "scheduled_publish_time": clean_time,
                "scheduled_display": f"{cand_date_str} {clean_time} (Đẩy trước {lead_hrs}h)",
                "lead_hours": lead_hrs,
                "mode": "AUTO_NEXT_AVAILABLE_SLOT",
            }

        fallback_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        return {
            "scheduled_publish_date": fallback_date,
            "scheduled_publish_time": clean_time,
            "scheduled_display": f"{fallback_date} {clean_time}",
            "mode": "FALLBACK_TOMORROW",
        }

    @staticmethod
    def compute_random_upload_and_schedule_plan(config: Dict[str, Any]) -> Dict[str, str]:
        sched_cfg = config.get("locked_common_studio_settings", {}).get("12_upload_timing_and_schedule", {})
        slots = sched_cfg.get("daily_schedule_slots", ["20:00"])
        rand_hour = random.randint(9, 16)
        rand_min = random.randint(5, 55)
        now = datetime.now()
        target_date = now.strftime("%Y-%m-%d")
        if now.hour >= 19:
            target_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        return {
            "random_upload_trigger": f"{rand_hour:02d}:{rand_min:02d}",
            "scheduled_publish_date": target_date,
            "scheduled_publish_time": slots[0] if slots else "20:00",
            "all_configured_slots": slots,
        }

    @classmethod
    def _configure_step2_video_elements(
        cls,
        port: int,
        tid: str,
        srt_file_path: str = "",
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        [v3.1] Tự động hóa Bước 2 (Các thành phần của video / Video elements):
        1. Thêm Phụ đề (`.srt` — `#subtitles-button`) nếu có file `subtitles.srt`.
        2. Thêm Màn hình kết thúc (`End Screen` — `#endscreens-button`): chọn mẫu 1 Video + 1 Subscribe và bấm Lưu (`#save-button`).
        3. Thêm Thẻ đề xuất (`Info Cards` — `#cards-button`): chọn gắn thẻ Video và bấm Lưu (`#save-button`).
        """
        results = {"subtitles_added": False, "endscreen_added": False, "cards_added": False}

        # 1. Tải file phụ đề .srt nếu có
        if srt_file_path and os.path.exists(srt_file_path):
            if log_fn:
                log_fn(f"📝 [Bước 2 - Phụ đề .srt]: Đang đính kèm file phụ đề tiếng Nhật `{os.path.basename(srt_file_path)}`...")
            sub_clicked = BrowserCDPManager.eval_js(
                port,
                tid,
                r"""
                (() => {
                    const btn = document.querySelector('#subtitles-button button, ytcp-button#subtitles-button');
                    if (btn && !btn.hasAttribute('disabled')) { btn.click(); return true; }
                    return false;
                })()
                """,
            )
            if sub_clicked:
                time.sleep(2.2)
                # Bấm nút "Tải tệp lên / Upload file / ファイルをアップロード"
                BrowserCDPManager.eval_js(
                    port,
                    tid,
                    r"""
                    (() => {
                        const items = Array.from(document.querySelectorAll(' button, ytcp-button, tp-yt-paper-item, div[role="button"]'));
                        const upBtn = items.find(el => {
                            const t = (el.innerText || '').toLowerCase();
                            return t.includes('tải tệp lên') || t.includes('upload file') || t.includes('ファイルをアップロード');
                        });
                        if (upBtn) { upBtn.click(); return true; }
                        return false;
                    })()
                    """,
                )
                time.sleep(1.2)
                # Bấm "Tiếp tục / Continue / 続行" (Có định thời gian)
                BrowserCDPManager.eval_js(
                    port,
                    tid,
                    r"""
                    (() => {
                        const btns = Array.from(document.querySelectorAll('ytcp-button, button'));
                        const cont = btns.find(el => {
                            const t = (el.innerText || '').toLowerCase();
                            return t.includes('tiếp tục') || t.includes('continue') || t.includes('続行');
                        });
                        if (cont) { cont.click(); return true; }
                        return false;
                    })()
                    """,
                )
                time.sleep(1.0)
                # Đóng hộp thoại phụ đề nếu đã xong hoặc bấm Xong/Hủy an toàn
                BrowserCDPManager.eval_js(
                    port,
                    tid,
                    r"""
                    (() => {
                        const doneBtn = document.querySelector('ytve-captions-editor-modal #save-button, ytcp-button#done-button, ytcp-button#close-button, button[aria-label*="Đóng"], button[aria-label*="Close"]');
                        if (doneBtn) doneBtn.click();
                        return true;
                    })()
                    """,
                )
                results["subtitles_added"] = True
                time.sleep(1.2)

        # 2. Thêm Màn hình kết thúc (End Screen: 1 Video + 1 Subscribe ở 20s cuối)
        if log_fn:
            log_fn("🎬 [Bước 2 - Màn Hình Kết Thúc (End Screen)]: Đang mở trình chỉnh sửa End Screen và gắn mẫu 『1 Video + 1 Nút Đăng Ký』 ở 20 giây cuối...")
        end_clicked = BrowserCDPManager.eval_js(
            port,
            tid,
            r"""
            (() => {
                const btn = document.querySelector('#endscreens-button button, ytcp-button#endscreens-button');
                if (btn && !btn.hasAttribute('disabled')) { btn.click(); return true; }
                return false;
            })()
            """,
        )
        if end_clicked:
            time.sleep(2.8)
            end_saved = BrowserCDPManager.eval_js(
                port,
                tid,
                r"""
                (() => {
                    const tpl = document.querySelector('.ytve-endscreen-template-picker-item, ytve-endscreen-template-picker .template-preview');
                    if (tpl) tpl.click();
                    return Boolean(tpl);
                })()
                """,
            )
            time.sleep(1.6)
            BrowserCDPManager.eval_js(
                port,
                tid,
                r"""
                (() => {
                    const saveBtn = document.querySelector('ytve-endscreen-modal #save-button button, ytve-endscreen-modal ytcp-button#save-button');
                    if (saveBtn && !saveBtn.hasAttribute('disabled')) {
                        saveBtn.click();
                        return 'SAVED';
                    }
                    const discardBtn = document.querySelector('ytve-endscreen-modal #discard-button button, ytve-endscreen-modal ytcp-button#discard-button, button[aria-label*="Đóng"], button[aria-label*="Close"]');
                    if (discardBtn) discardBtn.click();
                    return 'CLOSED';
                })()
                """,
            )
            results["endscreen_added"] = bool(end_saved)
            time.sleep(1.5)

        # 3. Thêm Thẻ đề xuất (Info Cards)
        if log_fn:
            log_fn("🏷️ [Bước 2 - Thẻ Đề Xuất (Info Cards)]: Đang kiểm tra và gắn Thẻ đề xuất giữa video...")
        card_clicked = BrowserCDPManager.eval_js(
            port,
            tid,
            r"""
            (() => {
                const btn = document.querySelector('#cards-button button, ytcp-button#cards-button');
                if (btn && !btn.hasAttribute('disabled')) { btn.click(); return true; }
                return false;
            })()
            """,
        )
        if card_clicked:
            time.sleep(2.4)
            BrowserCDPManager.eval_js(
                port,
                tid,
                r"""
                (() => {
                    const saveBtn = document.querySelector('ytve-info-cards-editor-modal #save-button button, ytcp-button#save-button');
                    if (saveBtn && !saveBtn.hasAttribute('disabled')) {
                        saveBtn.click();
                        return 'SAVED';
                    }
                    const closeBtn = document.querySelector('ytve-info-cards-editor-modal #discard-button button, ytcp-button#discard-button, ytcp-icon-button#close-button, button[aria-label*="Đóng"], button[aria-label*="Close"]');
                    if (closeBtn) closeBtn.click();
                    return 'CLOSED';
                })()
                """,
            )
            results["cards_added"] = True
            time.sleep(1.2)

        return results

    @classmethod
    def post_and_pin_first_comment(
        cls,
        port: int,
        tid: str,
        video_id: str,
        pinned_comment_text: str,
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        [v3.1] Mở trang xem video vừa tải lên (`https://www.youtube.com/watch?v=<video_id>`),
        viết Bình luận đầu tiên của chủ kênh (`PINNED_COMMENT`) và bấm nút Ghim (`Pin` / `固定`).
        """
        if not video_id or not pinned_comment_text:
            return {"ok": False, "reason": "Missing video_id or pinned_comment_text"}

        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        if log_fn:
            log_fn(f"📌 [Ghim Bình Luận Đầu Tiên]: Mở {watch_url} để đăng và ghim bình luận tương tác của chủ kênh...")
        TabGuard.navigate_tab(port, tid, watch_url)
        time.sleep(4.2)
        BrowserCDPManager.human_scroll(port, tid, min_px=420, max_px=580, direction=1)
        time.sleep(2.2)

        comment_posted = BrowserCDPManager.eval_js(
            port,
            tid,
            f"""
            (() => {{
                const placeholder = document.querySelector('#simplebox-placeholder, ytd-comment-simplebox-renderer #placeholder-area');
                if (placeholder) placeholder.click();
                const box = document.querySelector('#contenteditable-root[contenteditable="true"]');
                if (!box) return false;
                box.focus();
                box.innerText = {json.dumps(pinned_comment_text)};
                box.dispatchEvent(new Event('input', {{ bubbles: true }}));
                setTimeout(() => {{
                    const sub = document.querySelector('#submit-button button, ytd-button-renderer#submit-button button');
                    if (sub) sub.click();
                }}, 450);
                return true;
            }})()
            """,
        )
        time.sleep(3.0)

        # Bấm menu 3 chấm của bình luận đầu tiên -> Chọn Ghim (Pin / 固定)
        pinned_ok = False
        if comment_posted:
            pinned_ok = bool(
                BrowserCDPManager.eval_js(
                    port,
                    tid,
                    r"""
                    (() => {
                        const menuBtn = document.querySelector('ytd-comment-thread-renderer #action-menu button, ytd-comment-view-model #action-menu button');
                        if (!menuBtn) return false;
                        menuBtn.click();
                        setTimeout(() => {
                            const items = Array.from(document.querySelectorAll('ytd-menu-navigation-item-renderer, tp-yt-paper-item'));
                            const pinItem = items.find(el => {
                                const t = (el.innerText || '').toLowerCase();
                                return t.includes('ghim') || t.includes('pin') || t.includes('固定');
                            });
                            if (pinItem) {
                                pinItem.click();
                                setTimeout(() => {
                                    const confirmBtn = document.querySelector('yt-confirm-dialog-renderer #confirm-button button');
                                    if (confirmBtn) confirmBtn.click();
                                }, 500);
                            }
                        }, 500);
                        return true;
                    })()
                    """,
                )
            )
            time.sleep(1.8)

        return {"ok": True, "comment_posted": bool(comment_posted), "pinned": pinned_ok}

    @classmethod
    def _configure_step4_schedule_datetime(
        cls,
        port: int,
        tid: str,
        scheduled_date: str,
        scheduled_time: str,
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        [v3.7] Tự động thiết lập Ngày (`scheduled_date`: YYYY-MM-DD) và Giờ (`scheduled_time`: HH:MM)
        trong hộp thoại Lên lịch (`ytcp-datetime-picker`) ở Bước 4 của YouTube Studio:
        - Hỗ trợ đa ngôn ngữ giao diện YouTube Studio (Tiếng Việt, Tiếng Anh, Tiếng Nhật, Tiếng Tây Ban Nha).
        - Đảm bảo video được Đẩy Lên Trước (Pre-Upload) và tự động Public đúng Giờ Vàng đã định.
        """
        if log_fn:
            log_fn(
                f"📅 [Bước 4 - Đẩy Lên Trước & Hẹn Giờ Public]: Đang mở bộ hẹn giờ YouTube Studio -> Cài đặt xuất bản ngày `{scheduled_date}` lúc `{scheduled_time}`..."
            )

        # 1. Bấm mở phần Lên lịch (Schedule radio button / second-container-expand-button)
        BrowserCDPManager.eval_js(
            port,
            tid,
            r"""
            (() => {
                const schedBtn = document.querySelector('#schedule-radio-button, tp-yt-paper-radio-button[name="SCHEDULE"], #second-container-expand-button');
                if (schedBtn) schedBtn.click();
                return Boolean(schedBtn);
            })()
            """,
        )
        time.sleep(1.5)

        # Phân tích năm, tháng, ngày từ scheduled_date (YYYY-MM-DD)
        try:
            dt_obj = datetime.strptime(scheduled_date, "%Y-%m-%d")
        except Exception:
            dt_obj = datetime.now() + timedelta(days=1)

        # 2. Mở ô nhập Ngày (#datepicker-trigger) và tự động nhận diện định dạng ngày của giao diện Studio
        date_set_res = BrowserCDPManager.eval_js(
            port,
            tid,
            r"""
            (() => {
                const trigger = document.querySelector('ytcp-datetime-picker #datepicker-trigger, #datepicker-trigger');
                if (trigger) trigger.click();
                return Boolean(trigger);
            })()
            """,
        )
        time.sleep(1.0)

        cur_date_sample = str(
            BrowserCDPManager.eval_js(
                port,
                tid,
                r"""
                (() => {
                    const inp = document.querySelector('ytcp-date-picker tp-yt-paper-input input, ytcp-datetime-picker input');
                    return inp ? (inp.value || '') : '';
                })()
                """,
            )
            or ""
        ).strip()

        # Tự động định dạng chuỗi ngày khớp với ngôn ngữ hiển thị hiện tại của YouTube Studio
        y, m, d = dt_obj.year, dt_obj.month, dt_obj.day
        en_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        es_months = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        if "thg" in cur_date_sample.lower():
            formatted_date = f"{d} thg {m}, {y}"
        elif any(em.lower() in cur_date_sample.lower() for em in en_months):
            formatted_date = f"{en_months[m - 1]} {d}, {y}"
        elif any(sm in cur_date_sample.lower() for sm in es_months):
            formatted_date = f"{d} {es_months[m - 1]} {y}"
        elif "/" in cur_date_sample and cur_date_sample.startswith("20"):
            formatted_date = f"{y}/{m:02d}/{d:02d}"
        else:
            formatted_date = f"{d:02d}/{m:02d}/{y}"

        # Điền ngày vào input của ytcp-date-picker và nhấn Enter
        BrowserCDPManager.eval_js(
            port,
            tid,
            f"""
            (() => {{
                const inp = document.querySelector('ytcp-date-picker tp-yt-paper-input input, tp-yt-paper-dialog ytcp-date-picker input');
                if (!inp) return false;
                inp.focus();
                inp.select();
                inp.value = {json.dumps(formatted_date)};
                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                inp.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }}));
                return true;
            }})()
            """,
        )
        BrowserCDPManager.hardware_press_key(port, tid, "Enter", "Enter", 13)
        time.sleep(1.2)

        # 3. Điền Giờ xuất bản (`scheduled_time`, ví dụ "20:00") vào ô Time of Day
        BrowserCDPManager.eval_js(
            port,
            tid,
            f"""
            (() => {{
                const timeInputs = Array.from(document.querySelectorAll('ytcp-datetime-picker tp-yt-paper-input input, #time-of-day-trigger input'));
                const tInp = timeInputs[timeInputs.length - 1];
                if (tInp) {{
                    tInp.focus();
                    tInp.select();
                    tInp.value = {json.dumps(scheduled_time)};
                    tInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    tInp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    tInp.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }}));
                }}
                const items = Array.from(document.querySelectorAll('tp-yt-paper-item'));
                const matched = items.find(el => (el.innerText || '').trim() === {json.dumps(scheduled_time)});
                if (matched) matched.click();
                return true;
            }})()
            """,
        )
        BrowserCDPManager.hardware_press_key(port, tid, "Enter", "Enter", 13)
        time.sleep(1.2)

        return {
            "ok": True,
            "date_trigger_clicked": bool(date_set_res),
            "formatted_date_used": formatted_date,
            "scheduled_date": scheduled_date,
            "scheduled_time": scheduled_time,
        }

    @classmethod
    def execute_studio_upload_workflow(
        cls,
        channel: Dict[str, Any],
        video_file_path: str,
        seo_file_path: str,
        srt_file_path: str = "",
        timestamps_file_path: str = "",
        episode_id: str = "",
        visibility_mode: str = "SCHEDULE",
        scheduled_publish_date: str = "",
        scheduled_publish_time: str = "",
        emit_log_fn: Optional[Callable] = None,
        auto_close_browser_when_done: bool = True,
        window_slot: str = "RIGHT",
    ) -> Dict[str, Any]:
        """
        [v3.7] Quy trình Đẩy Video Lên Trước & Hẹn Giờ Public (Pre-Upload & Schedule) Có Cổng Xác Nhận Đăng Nhập:
        1. Kiểm tra file Video & File SEO (nếu người dùng chỉ cấp file `.mp4` chưa có SEO -> Tự sinh `_AUTO_SEO.txt`).
        2. Mở YouTube Studio trên 1 Tab duy nhất -> BẮT BUỘC CHẠY CỔNG XÁC NHẬN ĐĂNG NHẬP (`verify_google_and_youtube_login_before_task`).
           Nếu chưa đăng nhập -> Dừng ngay lập tức để bảo vệ hiệu quả!
        3. Đẩy file `.mp4` lên trước và điền đầy đủ Bước 1 (Chi tiết) + Bước 2 (Phụ đề, End Screen, Info Cards).
        4. Bước 4 (Chế độ hiển thị): Mặc định ưu tiên `SCHEDULE` (Đẩy lên trước & Cài đặt Ngày + Giờ Vàng Public tự động trên YouTube Studio).
        5. Lưu lịch sử kèm khung giờ đã hẹn vào `09_UPLOAD_HISTORY.json` và tự động đóng trình duyệt.
        """
        cid = channel["channel_id"]
        port = int(channel["cdp_port"])
        ch_lang = channel.get("language", "ja")
        channel_folder = os.path.join(BASE_STUDIO_DIR, "CHANNELS_DATA", cid)
        thumb_dir = os.path.join(channel_folder, "07_THUMBNAILS")
        cfg = cls.ensure_channel_upload_config(channel_folder, cid)
        sched_cfg = DailyAutopilotScheduler.load_or_init_schedule(channel_folder, cid)

        def _log(msg: str, extra: Optional[Dict[str, Any]] = None):
            if emit_log_fn:
                payload = {"active_desk": 6}
                if extra:
                    payload.update(extra)
                emit_log_fn(cid, 6, msg, payload)

        ep_dir = os.path.dirname(os.path.abspath(video_file_path)) if video_file_path else ""
        if not episode_id and video_file_path:
            episode_id = os.path.splitext(os.path.basename(video_file_path))[0]

        # Nếu người dùng tự cung cấp file .mp4 mà chưa có file SEO -> Tự động tạo ngay file SEO
        if video_file_path and os.path.exists(video_file_path) and (not seo_file_path or not os.path.exists(seo_file_path)):
            seo_file_path = cls.auto_generate_seo_for_video_if_missing(video_file_path, language=ch_lang)

        parsed_seo = SEOPackageParser.parse_seo_file(
            seo_file_path, thumb_dir, timestamps_file_path=timestamps_file_path, episode_dir=ep_dir
        )
        if not parsed_seo.get("ok"):
            _log(f"⚠️ [Bàn #6 - Upload & SEO]: {parsed_seo.get('error')}")
            return parsed_seo

        if not srt_file_path and ep_dir:
            cand_srt = os.path.join(ep_dir, "subtitles.srt")
            if os.path.exists(cand_srt):
                srt_file_path = cand_srt

        # Tính toán khung giờ Hẹn Lịch Public tự động (Đẩy lên trước & Setup giờ Public)
        vis_upper = (visibility_mode or "SCHEDULE").upper()
        default_pub_hour = str(sched_cfg.get("scheduled_publish_time") or "20:00")
        slot_plan = cls.compute_next_available_schedule_slot(
            channel_folder=channel_folder,
            publish_hour_str=default_pub_hour,
            min_lead_hours=float(sched_cfg.get("pre_upload_lead_hours") or 1.5),
            custom_schedule_date=scheduled_publish_date,
            custom_schedule_time=scheduled_publish_time,
        )
        final_sched_date = slot_plan["scheduled_publish_date"]
        final_sched_time = slot_plan["scheduled_publish_time"]

        _log(
            f"📦 [Bàn #6 - Chuẩn Bị Đẩy Video (Tập {episode_id or '?'})]: Tiêu đề: 「{parsed_seo.get('title', '')[:60]}」 | "
            f"Chế độ: {vis_upper}" + (f" (Hẹn giờ Public: {final_sched_date} {final_sched_time})" if vis_upper == "SCHEDULE" else "")
        )

        if not os.path.exists(video_file_path):
            return {
                "ok": True,
                "mode": "DRY_RUN_SEO_PARSED_READY_FOR_VIDEO",
                "parsed_seo": parsed_seo,
                "schedule_plan": slot_plan,
                "config": cfg,
            }

        # Chuẩn bị hardlink ASCII an toàn cho file video
        ascii_link_path = os.path.join(BASE_STUDIO_DIR, f"upload_staging_ep_{re.sub(r'[^A-Za-z0-9_-]', '_', str(episode_id or 'video'))}.mp4")
        try:
            if os.path.exists(ascii_link_path):
                os.remove(ascii_link_path)
            os.link(os.path.abspath(video_file_path), ascii_link_path)
        except Exception:
            ascii_link_path = os.path.abspath(video_file_path)

        # Mở Chrome Profile vào thẳng YouTube Studio (hỗ trợ chia đôi màn hình LEFT / RIGHT)
        slot_clean = (window_slot or "RIGHT").upper()
        BrowserCDPManager.launch_channel_browser(
            profile_dir=channel["profile_dir"],
            cdp_port=port,
            proxy=channel.get("proxy", ""),
            initial_url="https://studio.youtube.com",
            side_by_side_right=(slot_clean != "FULL"),
            channel_folder=channel_folder,
            window_slot=slot_clean,
        )
        time.sleep(4.5)
        pages = TabGuard.enforce_max_two_tabs(port, max_tabs=1)
        tid = pages[0]["id"] if pages else ""
        if not tid:
            return {"ok": False, "error": "Không mở được Tab YouTube Studio"}

        # [v3.7] BƯỚC BẮT BUỘC: CỔNG XÁC NHẬN ĐĂNG NHẬP STUDIO TRƯỚC KHI ĐẨY VIDEO
        login_chk = BrowserCDPManager.verify_google_and_youtube_login_before_task(
            cdp_port=port,
            target_id=tid,
            check_mode="STUDIO",
            emit_cb=lambda msg: _log(msg),
        )
        if not login_chk.get("logged_in"):
            if ascii_link_path != os.path.abspath(video_file_path) and os.path.exists(ascii_link_path):
                try:
                    os.remove(ascii_link_path)
                except Exception:
                    pass
            BrowserCDPManager.close_channel_browser(port)
            _log(
                f"⛔ [ĐÃ DỪNG NGAY ĐỂ BẢO VỆ HIỆU QUẢ]: Profile `{channel['profile_dir']}` CHƯA ĐĂNG NHẬP YouTube Studio ({login_chk.get('reason')})! "
                f"Vui lòng đăng nhập trước khi đẩy video.",
                {"status": "LOGIN_REQUIRED", "logged_in": False, "open_tabs_count": 0},
            )
            return {"ok": False, "login_required": True, "error": login_chk.get("reason")}

        _log(f"🔐 [Đã Xác Nhận Đăng Nhập Studio]: Kênh `{login_chk.get('detected_account')}` sẵn sàng -> Bắt đầu đẩy video lên trước!", {"logged_in": True})

        # Mở hộp thoại Tải video lên (Upload videos)
        _log("📤 [Bàn #6]: Đang mở hộp thoại Tải video lên trong YouTube Studio...")
        BrowserCDPManager.eval_js(
            port,
            tid,
            r"""
            (() => {
                const createBtn = document.querySelector('#create-icon, ytcp-button#create-icon, button[aria-label*="Create"], button[aria-label*="Tạo"], button[aria-label*="作成"]');
                if (createBtn) createBtn.click();
                setTimeout(() => {
                    const upItem = document.querySelector('tp-yt-paper-item#text-item-0, ytcp-ve#text-item-0');
                    if (upItem) upItem.click();
                }, 650);
                return true;
            })()
            """,
        )
        time.sleep(3.0)

        # Đẩy file .mp4 vào ytcp-uploads-file-picker qua Temp Input + DataTransfer trên cùng kết nối CDP
        BrowserCDPManager.eval_js(
            port,
            tid,
            r"""
            (() => {
                let temp = document.getElementById('agy-temp-video-upload');
                if (temp) temp.remove();
                temp = document.createElement('input');
                temp.type = 'file';
                temp.id = 'agy-temp-video-upload';
                temp.style.position = 'fixed';
                temp.style.top = '0';
                temp.style.left = '0';
                temp.style.opacity = '0.01';
                document.body.appendChild(temp);
                return true;
            })()
            """,
        )
        BrowserCDPManager.send_cdp_command(port, tid, "DOM.enable", {})
        doc_root = BrowserCDPManager.send_cdp_command(port, tid, "DOM.getDocument", {"depth": -1})
        root_node_id = (doc_root.get("root") or {}).get("nodeId", 1)
        q_sel = BrowserCDPManager.send_cdp_command(
            port, tid, "DOM.querySelector", {"nodeId": root_node_id, "selector": "#agy-temp-video-upload"}
        )
        file_node_id = (q_sel or {}).get("nodeId", 0)
        if file_node_id:
            BrowserCDPManager.send_cdp_command(
                port,
                tid,
                "DOM.setFileInputFiles",
                {"nodeId": file_node_id, "files": [ascii_link_path]},
            )
            time.sleep(0.5)
            BrowserCDPManager.eval_js(
                port,
                tid,
                r"""
                (() => {
                    const temp = document.getElementById('agy-temp-video-upload');
                    const realInput = document.querySelector('ytcp-uploads-file-picker input[type="file"], input[name="Filedata"]');
                    if (!temp || !temp.files.length || !realInput) return false;
                    const dt = new DataTransfer();
                    dt.items.add(temp.files[0]);
                    realInput.files = dt.files;
                    realInput.dispatchEvent(new Event('change', { bubbles: true }));
                    temp.remove();
                    return true;
                })()
                """,
            )
            _log(f"🎬 [Bàn #6]: Đã nạp file video `{os.path.basename(video_file_path)}` vào trình tải lên YouTube Studio!")

        # Chờ form Chi tiết (#title-textarea) xuất hiện
        for _ in range(30):
            has_title_box = BrowserCDPManager.eval_js(
                port, tid, "Boolean(document.querySelector('#title-textarea #textbox'))"
            )
            if has_title_box:
                break
            time.sleep(1.0)

        time.sleep(2.5)
        video_link_info = BrowserCDPManager.eval_js(
            port,
            tid,
            r"""
            (() => {
                const a = document.querySelector('a.video-url-fadeable, ytcp-video-info a[href*="youtu.be"], ytcp-video-info a[href*="youtube.com"]');
                const href = a ? a.href : '';
                const m = href.match(/(?:youtu\.be\/|v=|\/video\/)([A-Za-z0-9_-]{11})/);
                return { href: href, video_id: m ? m[1] : '' };
            })()
            """,
        ) or {}
        video_id = video_link_info.get("video_id", "")

        # BƯỚC 1: Điền Tiêu đề, Mô tả, COPPA = No
        _log("✍️ [Bước 1 - Chi tiết]: Đang điền Tiêu đề, Mô tả chuẩn SEO, Chapters, Hashtags & COPPA...")
        BrowserCDPManager.eval_js(
            port,
            tid,
            f"""
            (() => {{
                const setTextbox = (sel, text) => {{
                    const el = document.querySelector(sel);
                    if (!el) return false;
                    el.focus();
                    el.innerText = text;
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    el.blur();
                    return true;
                }};
                setTextbox('#title-textarea #textbox', {json.dumps(parsed_seo["title"])});
                setTextbox('#description-textarea #textbox', {json.dumps(parsed_seo["description"])});
                const notKids = document.querySelector('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]');
                if (notKids) notKids.click();
                return true;
            }})()
            """,
        )
        time.sleep(1.5)

        if ch_lang == "ja":
            loc_query = "Nhật Bản"
            loc_matches = ["Nhật Bản", "Japan", "日本"]
        elif ch_lang == "es":
            loc_query = "Mexico"
            loc_matches = ["Mexico", "México"]
        else:
            loc_query = "Hoa Kỳ"
            loc_matches = ["Hoa Kỳ", "United States", "Mỹ"]

        # Mở mục "Hiện thêm (Show more)" -> Điền Quảng cáo = Không, Nội dung AI = Có, 25+ thẻ Tags, Ngôn ngữ & Vị trí
        _log(f"🏷️ [Bước 1 - Hiện thêm]: Đang cấu hình Nội dung AI = Có, {len(parsed_seo['tags'])} thẻ Tags, Vị trí = {loc_query}...")
        BrowserCDPManager.eval_js(
            port,
            tid,
            r"""
            (() => {
                const toggleBtn = document.querySelector('#toggle-button, ytcp-video-metadata-editor-advanced #toggle-button');
                if (toggleBtn) toggleBtn.click();
                return true;
            })()
            """,
        )
        time.sleep(1.8)

        BrowserCDPManager.eval_js(
            port,
            tid,
            f"""
            (() => {{
                const aiYes = document.querySelector('tp-yt-paper-radio-button[name="VIDEO_HAS_ALTERED_CONTENT_YES"]');
                if (aiYes) aiYes.click();

                const tagInput = document.querySelector('#tags-container input#text-input, ytcp-form-input-container#tags-container input');
                if (tagInput) {{
                    const tags = {json.dumps(parsed_seo["tags"])};
                    for (const t of tags) {{
                        tagInput.focus();
                        tagInput.value = t;
                        tagInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        tagInput.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }}));
                    }}
                }}

                const locInput = document.querySelector('#location input, ytcp-form-location input');
                if (locInput) {{
                    locInput.focus();
                    locInput.value = {json.dumps(loc_query)};
                    locInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                return true;
            }})()
            """,
        )
        time.sleep(1.5)
        BrowserCDPManager.eval_js(
            port,
            tid,
            f"""
            (() => {{
                const allowed = {json.dumps(loc_matches)};
                const items = Array.from(document.querySelectorAll('tp-yt-paper-item'));
                const matchedLoc = items.find(el => {{
                    const t = (el.innerText || '').trim();
                    return allowed.includes(t);
                }});
                if (matchedLoc) matchedLoc.click();
                return true;
            }})()
            """,
        )
        time.sleep(1.0)

        # BƯỚC 2: Bấm Next sang "Các thành phần của video (Video elements)"
        BrowserCDPManager.eval_js(port, tid, "(() => { const n = document.querySelector('#next-button'); if (n) n.click(); return true; })()")
        time.sleep(2.2)
        step2_res = cls._configure_step2_video_elements(port, tid, srt_file_path=srt_file_path, log_fn=_log)

        # BƯỚC 3 & BƯỚC 4: Bấm Next qua "Kiểm tra (Checks)" -> Sang "Chế độ hiển thị (Visibility)"
        for _ in range(2):
            BrowserCDPManager.eval_js(port, tid, "(() => { const n = document.querySelector('#next-button'); if (n) n.click(); return true; })()")
            time.sleep(1.8)

        # Chọn chế độ hiển thị: SCHEDULE (Đẩy lên trước & Hẹn giờ Public) / PUBLIC / PRIVATE
        schedule_setup_res = {}
        if vis_upper == "PUBLIC":
            BrowserCDPManager.eval_js(
                port,
                tid,
                "(() => { const r = document.querySelector('tp-yt-paper-radio-button[name=\"PUBLIC\"]'); if (r) r.click(); return true; })()",
            )
        elif vis_upper == "SCHEDULE":
            schedule_setup_res = cls._configure_step4_schedule_datetime(
                port=port,
                tid=tid,
                scheduled_date=final_sched_date,
                scheduled_time=final_sched_time,
                log_fn=_log,
            )
        else:
            BrowserCDPManager.eval_js(
                port,
                tid,
                "(() => { const r = document.querySelector('tp-yt-paper-radio-button[name=\"PRIVATE\"]'); if (r) r.click(); return true; })()",
            )
        time.sleep(1.5)

        # Chờ nếu video vẫn đang tải lên (0% -> 100%) trước khi bấm nút Lên lịch / Lưu (#done-button)
        for _ in range(180):
            can_save = BrowserCDPManager.eval_js(
                port,
                tid,
                r"""
                (() => {
                    const doneBtn = document.querySelector('#done-button');
                    if (!doneBtn) return false;
                    return !doneBtn.hasAttribute('disabled');
                })()
                """,
            )
            if can_save:
                break
            time.sleep(2.0)

        BrowserCDPManager.eval_js(
            port,
            tid,
            "(() => { const doneBtn = document.querySelector('#done-button'); if (doneBtn) doneBtn.click(); return true; })()",
        )
        time.sleep(4.5)

        # Lưu vào lịch sử 09_UPLOAD_HISTORY.json kèm ngày giờ đã lên lịch Public
        cls.record_uploaded_episode(
            channel_folder=channel_folder,
            episode_id=episode_id or "custom",
            video_id=video_id,
            title=parsed_seo["title"],
            visibility=vis_upper,
            video_file_path=video_file_path,
            scheduled_publish_date=final_sched_date if vis_upper == "SCHEDULE" else "",
            scheduled_publish_time=final_sched_time if vis_upper == "SCHEDULE" else "",
        )
        sched_note = f" -> Đã hẹn giờ tự động Public lúc `{final_sched_date} {final_sched_time}`" if vis_upper == "SCHEDULE" else ""
        _log(
            f"✅ [Bàn #6 - HOÀN TẤT ĐẨY VIDEO TẬP {episode_id}]: Video ID `{video_id}` (https://youtu.be/{video_id}) chế độ `{vis_upper}`{sched_note}!"
        )

        # Nếu xuất bản Công khai (PUBLIC) hoặc Không công khai (UNLISTED), tự động mở trang video để Đăng & Ghim bình luận đầu tiên
        pin_res = {"ok": False, "skipped": True}
        if vis_upper in ("PUBLIC", "UNLISTED") and video_id and parsed_seo.get("pinned_comment"):
            pin_res = cls.post_and_pin_first_comment(
                port, tid, video_id=video_id, pinned_comment_text=parsed_seo["pinned_comment"], log_fn=_log
            )

        # Dọn file hardlink tạm
        if ascii_link_path != os.path.abspath(video_file_path) and os.path.exists(ascii_link_path):
            try:
                os.remove(ascii_link_path)
            except Exception:
                pass

        if auto_close_browser_when_done:
            BrowserCDPManager.close_channel_browser(port)
            _log("🛑 [Bàn #6]: Đã lưu Cookie và tự động đóng cửa sổ Chrome Profile sau khi hoàn tất Đẩy Video & Hẹn Giờ.")

        return {
            "ok": True,
            "episode_id": episode_id,
            "video_id": video_id,
            "youtube_url": f"https://youtu.be/{video_id}" if video_id else "",
            "studio_edit_url": f"https://studio.youtube.com/video/{video_id}/edit" if video_id else "",
            "visibility": vis_upper,
            "scheduled_publish_date": final_sched_date if vis_upper == "SCHEDULE" else "",
            "scheduled_publish_time": final_sched_time if vis_upper == "SCHEDULE" else "",
            "schedule_setup": schedule_setup_res,
            "parsed_seo": parsed_seo,
            "step2_elements": step2_res,
            "pinned_comment_result": pin_res,
        }

    @classmethod
    def upload_next_pending_episode_from_queue(
        cls,
        channel: Dict[str, Any],
        parent_batch_dir: str = r"D:\KEY NHẬT\20-30",
        visibility_mode: str = "SCHEDULE",
        scheduled_publish_date: str = "",
        scheduled_publish_time: str = "",
        emit_log_fn: Optional[Callable] = None,
        window_slot: str = "RIGHT",
    ) -> Dict[str, Any]:
        """
        [v3.7 / v3.8] Tự động quét cả Thư mục Video Người Dùng Cung Cấp (`08_READY_VIDEOS_TO_UPLOAD`) và Thư mục Hàng đợi (`parent_batch_dir`),
        tìm tập đầu tiên CHƯA ĐĂNG (`READY_PENDING`) và Đẩy Lên Trước + Setup Giờ Public (`SCHEDULE`).
        """
        cid = channel["channel_id"]
        ch_lang = channel.get("language", "ja")
        channel_folder = os.path.join(BASE_STUDIO_DIR, "CHANNELS_DATA", cid)
        queue_info = cls.scan_batch_folder_queue(
            channel_folder, parent_batch_dir=parent_batch_dir, language=ch_lang
        )
        next_ep = queue_info.get("next_pending_episode")
        if not next_ep:
            return {
                "ok": False,
                "error": "Không còn tập nào ở trạng thái CHỜ ĐĂNG (READY_PENDING) trong thư mục hàng đợi.",
                "queue_info": queue_info,
            }

        return cls.execute_studio_upload_workflow(
            channel=channel,
            video_file_path=next_ep["video_file_path"],
            seo_file_path=next_ep["seo_file_path"],
            srt_file_path=next_ep.get("srt_file_path", ""),
            timestamps_file_path=next_ep.get("timestamps_file_path", ""),
            episode_id=next_ep["episode_id"],
            visibility_mode=visibility_mode,
            scheduled_publish_date=scheduled_publish_date,
            scheduled_publish_time=scheduled_publish_time,
            emit_log_fn=emit_log_fn,
            auto_close_browser_when_done=True,
            window_slot=window_slot,
        )


class DailyAutopilotScheduler:
    """
    [v3.7] Bộ Hẹn Giờ Tự Động Chạy Hàng Ngày — TÁCH BIỆT HOÀN TOÀN PHẦN NUÔI VÀ PHẦN ĐẨY VIDEO HẸN GIỜ:
    1. Nhánh 1 — Tự động NUÔI (`auto_warmup_enabled`):
       - Có thể bật/tắt độc lập.
       - Hỗ trợ chọn `warmup_mode`: `"FULL_OMNI"` (Nuôi đa tầng), `"YOUTUBE_DEEP_ONLY"` (Chỉ nuôi kênh xem sâu & bình luận), `"GMAIL_ONLY"` (Chỉ nuôi Gmail).
    2. Nhánh 2 — Tự động ĐẨY VIDEO LÊN TRƯỚC & HẸN GIỜ PUBLIC (`auto_pre_upload_enabled`):
       - Có thể bật/tắt độc lập hoàn toàn với phần Nuôi.
       - Hỗ trợ chọn `video_source_mode`:
         + `"USER_SUPPLIED"`: Tôi tự cung cấp video sẵn (Khuyên dùng cho máy nuôi 10 kênh).
         + `"HYBRID_AUTO"`: Ưu tiên video tôi cung cấp sẵn -> nếu hết mới tự sản xuất.
         + `"SELF_PRODUCED"`: Tự sản xuất video trên máy.
       - Tự động đẩy video lên trước vào `pre_upload_trigger_time` (ví dụ `13:30`) và cài đặt giờ Public trên YouTube Studio vào đúng Giờ Vàng `scheduled_publish_time` (ví dụ `20:00`)!
    """

    @staticmethod
    def get_schedule_path(channel_folder: str) -> str:
        return os.path.join(channel_folder, "10_AUTOPILOT_SCHEDULE.json")

    @classmethod
    def load_or_init_schedule(cls, channel_folder: str, channel_id: str) -> Dict[str, Any]:
        path = cls.get_schedule_path(channel_folder)
        today_str = datetime.now().strftime("%Y-%m-%d")
        default_sched = {
            "channel_id": channel_id,
            "autopilot_enabled": False,
            "auto_warmup_enabled": False,
            "warmup_mode": "FULL_OMNI",
            "auto_warmup_morning_window": "09:15-11:00",
            "auto_warmup_afternoon_window": "15:00-16:45",
            "today_date": today_str,
            "today_morning_trigger_time": f"{random.randint(9, 10):02d}:{random.randint(15, 55):02d}",
            "today_afternoon_trigger_time": f"{random.randint(15, 16):02d}:{random.randint(10, 45):02d}",
            "morning_done_today": False,
            "afternoon_done_today": False,
            "auto_pre_upload_enabled": False,
            "auto_daily_upload_from_queue_enabled": False,
            "video_source_mode": "USER_SUPPLIED",
            "auto_upload_visibility_mode": "SCHEDULE",
            "pre_upload_trigger_time": "13:30",
            "scheduled_publish_time": "20:00",
            "pre_upload_lead_hours": 3.0,
            "pre_upload_done_today": False,
            "batch_queue_dir": r"D:\KEY NHẬT\20-30",
            "last_triggered_at": "Chưa kích hoạt",
            "last_pre_upload_at": "Chưa đẩy video",
        }
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                for k, v in default_sched.items():
                    loaded.setdefault(k, v)
                # Đồng bộ cờ tương thích ngược
                if "auto_warmup_enabled" not in loaded and loaded.get("autopilot_enabled"):
                    loaded["auto_warmup_enabled"] = bool(loaded["autopilot_enabled"])
                return loaded
            except Exception:
                pass

        os.makedirs(channel_folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_sched, f, ensure_ascii=False, indent=2)
        return default_sched

    @classmethod
    def update_schedule_config(cls, channel_folder: str, channel_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        sched = cls.load_or_init_schedule(channel_folder, channel_id)
        sched.update(updates)
        # Đồng bộ cờ tổng quát
        if "auto_warmup_enabled" in updates:
            sched["autopilot_enabled"] = bool(updates["auto_warmup_enabled"])
        if "auto_pre_upload_enabled" in updates:
            sched["auto_daily_upload_from_queue_enabled"] = bool(updates["auto_pre_upload_enabled"])
        sched["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        path = cls.get_schedule_path(channel_folder)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sched, f, ensure_ascii=False, indent=2)
        return sched

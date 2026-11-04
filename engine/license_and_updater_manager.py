# -*- coding: utf-8 -*-
"""
HỆ THỐNG QUẢN LÝ BẢN QUYỀN MÃ KEY KÍCH HOẠT (LICENSE KEY SYSTEM),
KHO CÔNG THỨC ĐA NGÁCH "MỖI KEY 1 CÁCH VIẾT KỊCH BẢN & EDIT VIDEO RIÊNG" (PLUGGABLE NICHE RECIPES)
VÀ CẬP NHẬT TỪ XA QUA GITHUB KHÔNG CẦN TẢI LẠI ỨNG DỤNG (OTA HOT-UPDATER v3.9)
"""

import datetime
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import time
import urllib.request
import uuid
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
os.makedirs(CONFIG_DIR, exist_ok=True)

LICENSE_STATE_PATH = os.path.join(CONFIG_DIR, "license_state.json")
ADMIN_KEYS_VAULT_PATH = os.path.join(CONFIG_DIR, "admin_generated_keys_vault.json")
NICHE_RECIPES_PATH = os.path.join(CONFIG_DIR, "niche_recipes_registry.json")
VERSION_MANIFEST_PATH = os.path.join(BASE_DIR, "version_manifest.json")

# Cấu hình Kho GitHub OTA chính thức để máy khách tự động cập nhật từ xa
GITHUB_OWNER = "phamngocthu661-lang"
GITHUB_REPO = "youtube-enterprise-studio-pro"
GITHUB_BRANCH = "main"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"

CURRENT_APP_VERSION = "3.9.0"
CURRENT_BUILD_DATE = "2026-11-04"

# Khóa bí mật ký số HMAC-SHA256 để sinh & xác thực Mã Key Kích Hoạt cho khách
_MASTER_HMAC_SECRET = b"YT_ENTERPRISE_STUDIO_MASTER_SECRET_KEY_2026_V39_HMAC"


# ==============================================================================
# 1. KHO CÔNG THỨC ĐA NGÁCH: "MỖI KEY 1 CÁCH VIẾT KỊCH BẢN & EDIT VIDEO RIÊNG"
# ==============================================================================
DEFAULT_NICHE_RECIPES: List[Dict[str, Any]] = [
    {
        "niche_key": "KEY_JP_K1_MANGA",
        "niche_code": "JP-K1",
        "niche_name": "🇯🇵 Key Nhật K1: Hưu Trí & Drama Gia Đình Seinen Manga (定年後の人生ラボ)",
        "language": "ja",
        "market": "Nhật Bản (JP)",
        "unlock_addon_code": "ADDON-KEY-JP-K1-MANGA",
        "script_formula": {
            "style_name": "K1 Seinen Manga Narrated Story (20–25 Phút)",
            "target_length": "7.500 – 8.500 ký tự tiếng Nhật (Chuẩn 20–25 phút đọc)",
            "title_dna": "【漫画】AGE + ACTION + CONSEQUENCE + LESSON (Ưu tiên: ハローワーク / シルバー人材センター / 60歳 再雇用 / 年金)",
            "narrative_arc": "5 Nhịp: OLD BELIEF (Niềm tin cũ) ➔ COLLISION (Va chạm thực tế) ➔ EXPERIMENT (Thử nghiệm) ➔ NEW BELIEF (Nhận thức mới) ➔ WARM RESOLUTION (Kết ấm áp)",
            "qa_gate": "Kiểm định độc lập >= 96/100 điểm, cấm trùng lặp mô-típ Kênh 2",
            "linked_skills": ["k1-title-planner", "k1-script-writer", "k1-script-auditor", "k1-seo-packaging"],
        },
        "video_edit_formula": {
            "edit_style_name": "Chuẩn Điện Ảnh Manga Nhật Bản (Veo3 Hook + Seinen Manga 4s–10s)",
            "opening_hook_rule": "10 CẢNH ĐẦU TIÊN 100% LÀ VIDEO AI (VEO 3) chuyển động điện ảnh giữ chân khán giả 60s đầu",
            "body_visual_rule": "Từ Cảnh 11 trở đi: 10% Video AI + 90% Ảnh tĩnh Seinen Manga (nhịp đổi ảnh 4s–10s, 50–60% góc B-roll giấu mặt giảm mỏi mắt)",
            "camera_and_effects": "Kỹ thuật Shot-Reverse-Shot điện ảnh + Pan/Zoom nhẹ 1.08x + Phụ đề lớn rõ ràng cho khán giả Nhật 60–70+",
            "audio_and_tts": "Giọng đọc Nhật trầm ấm tốc độ 1.0x + Nhạc nền Piano/Acoustic nhẹ -24dB + Render FFmpeg GPU NVENC chống tràn RAM",
            "linked_skills": ["San_Xuat_Video_Nhat_Ban", "K1_Studio_Company"],
        },
    },
    {
        "niche_key": "KEY_JP_KUCHIKOMI_60",
        "niche_code": "JP-KCK",
        "niche_name": "🇯🇵 Key Nhật Kuchikomi: 30 Bình Luận Việc Làm & Tiền Tuổi Già (60代・定年口コミ)",
        "language": "ja",
        "market": "Nhật Bản (JP)",
        "unlock_addon_code": "ADDON-KEY-JP-KUCHIKOMI",
        "script_formula": {
            "style_name": "30 Độc Giả Chia Sẻ Thực Tế (7 Phần / 30 口コミ Độc Lập)",
            "target_length": "18.000 – 24.000 ký tự tiếng Nhật (30 câu chuyện thực tế về việc làm & lương hưu tuổi 60+)",
            "title_dna": "Con số cụ thể (Lương hưu / Thu nhập làm thêm) + 30인의 口コミ + Cảnh báo tuổi già",
            "narrative_arc": "Mở đầu tổng quan ➔ 7 Phần chia theo nhóm ngành nghề (30 口コミ có tuổi, nghề cũ, thu nhập thật) ➔ Tổng kết lời khuyên",
            "qa_gate": "Kiểm toán số học tiền tệ/lương hưu Nhật Bản chính xác 100%, 1 lần vá lỗi cố định",
            "linked_skills": ["viet-lai-tieu-de-japan-kuchikomi", "viet-gian-y-japan-kuchikomi", "viet-kich-ban-japan-kuchikomi", "kiem-tra-kich-ban-japan-kuchikomi", "viet-seo-japan-kuchikomi"],
        },
        "video_edit_formula": {
            "edit_style_name": "Bảng Tin 2ch/Kuchikomi Nhật Bản + Thẻ Nhân Vật Biểu Cảm",
            "opening_hook_rule": "Hiệu ứng lật thẻ bình luận nhanh 3 câu chuyện sốc nhất trong 15 giây đầu",
            "body_visual_rule": "Khung nền giấy Nhật truyền thống + Avatar nhân vật 60+ đổi biểu cảm theo từng 口コミ + Highlight con số tiền lương màu vàng/đỏ",
            "camera_and_effects": "Chuyển cảnh trượt thẻ (Card Slide) kèm âm thanh 'Pon!' đặc trưng kênh Kuchikomi Nhật",
            "audio_and_tts": "Phân tách giọng dẫn chuyện và giọng đọc từng bình luận 口コミ (1.05x)",
            "linked_skills": ["viet-kich-ban-japan-kuchikomi"],
        },
    },
    {
        "niche_key": "KEY_US_MAFIA_MAID",
        "niche_code": "US-MAFIA",
        "niche_name": "🇺🇸 Key Mỹ (US): Mafia Boss × Người Hầu / Cô Gái Bị Coi Thường (Emotional Romance)",
        "language": "en",
        "market": "Hoa Kỳ (US)",
        "unlock_addon_code": "ADDON-KEY-US-MAFIA",
        "script_formula": {
            "style_name": "First-Person American Emotional Mafia Storytelling",
            "target_length": "44.000 – 48.000 ký tự (7.400 – 7.650 từ tiếng Anh Mỹ chuẩn, Strict < 8.000 từ)",
            "title_dna": "Bảo toàn 60% DNA từ khóa triệu view + Đột biến 40% biến số câu chuyện (Maid/Waitress/Nurse × Ruthless Don)",
            "narrative_arc": "7 Parts: Bị sỉ nhục/bỏ rơi ➔ Cuộc gặp gỡ định mệnh với Ông Trùm ➔ Che giấu thân phận ➔ Cao trào vạch mặt kẻ phản bội ➔ Cái kết viên mãn",
            "qa_gate": "Forensic Score nghiêm ngặt, 0 ký tự ngoặc vuông TTS, kiểm tra chính tả en-US",
            "linked_skills": ["viet-lai-tieu-de-mafia-nguoi-hau", "viet-gian-y-nguoi-hau", "viet-kich-ban-nguoi-hau-tu-gian-y", "kiem-tra-kich-ban-nguoi-hau", "viet-seo-nguoi-hau"],
        },
        "video_edit_formula": {
            "edit_style_name": "Cinematic Dark Luxury Mansion (Ken Burns Pan/Zoom + Golden Dust)",
            "opening_hook_rule": "8-Second Visual Power Hook mở màn bằng cảnh đối đầu cảm xúc tại biệt thự/nhà hàng sang trọng",
            "body_visual_rule": "Bộ ảnh Photorealistic 16:9 đồng nhất Visual DNA nhân vật, nhịp đổi cảnh 7s–11s",
            "camera_and_effects": "Hiệu ứng Ken Burns Zoom-In chậm vào ánh mắt + Lớp phủ bụi vàng (Golden Bokeh Overlay) + Vignette tối góc",
            "audio_and_tts": "Giọng đọc nữ/nam trầm truyền cảm American English + Nhạc nền Cello/Piano trầm lắng",
            "linked_skills": ["Tao_Prompt_Anh", "viet-seo-nguoi-hau"],
        },
    },
    {
        "niche_key": "KEY_US_HOMELESS_LEGACY",
        "niche_code": "US-HOME",
        "niche_name": "🇺🇸 Key Mỹ (US): Homeless × Bất Động Sản Bỏ Hoang × Di Sản Ẩn Giấu",
        "language": "en",
        "market": "Hoa Kỳ (US)",
        "unlock_addon_code": "ADDON-KEY-US-HOMELESS",
        "script_formula": {
            "style_name": "7-Part Survival & Abandoned Property Restoration Saga",
            "target_length": "70.000 – 80.000 ký tự tiếng Anh Mỹ (Long-form 80–95 phút)",
            "title_dna": "Bị đuổi khỏi nhà tay trắng ➔ Mua/Thừa kế mảnh đất/căn nhà đổ nát ➔ Phát hiện giá trị triệu đô dưới lớp bụi",
            "narrative_arc": "7 Phần: Early Retention Survival (90s đầu sinh tồn khắc nghiệt) ➔ Khôi phục từng bước bằng tay nghề ➔ Phát hiện bí mật lịch sử/pháp lý ➔ Đảo ngược vị thế",
            "qa_gate": "Forensic Gate >= 98/100, sổ cái tài chính & quyền sở hữu đất đai khớp 100%",
            "linked_skills": ["viral-title-rewriter", "viet-gian-y-homeless", "viet-kich-ban-homeless", "kiem-tra-kich-ban-homeless", "seo-homeless-story"],
        },
        "video_edit_formula": {
            "edit_style_name": "Documentary Realism (Contrast Cold Survival ➔ Warm Restoration)",
            "opening_hook_rule": "Trailer 10–30 giây không lời thoại (Omni Multi-Shot) đối lập cảnh mưa lạnh ngoài đường và ánh đèn ấm trong ngôi nhà được phục dựng",
            "body_visual_rule": "Nửa đầu dùng bảng màu lạnh xám (Desaturated Blue), nửa sau chuyển dần sang màu nắng vàng ấm (Warm Amber) khi căn nhà hoàn thiện",
            "camera_and_effects": "Hiệu ứng mưa rơi/tuyết rơi nhẹ ở Part 1–2 + Chuyển cảnh Crossfade mượt 1.2s",
            "audio_and_tts": "Giọng kể chuyện mộc mạc, chân thực + Tiếng mưa/tiếng búa gỗ nhẹ làm nền",
            "linked_skills": ["seo-homeless-story"],
        },
    },
    {
        "niche_key": "KEY_US_DAD_REVENGE",
        "niche_code": "US-DAD",
        "niche_name": "🇺🇸 Key Mỹ (US): Ông Già Trả Đũa & Công Lý Tài Chính Gia Đình (DADUS)",
        "language": "en",
        "market": "Hoa Kỳ (US)",
        "unlock_addon_code": "ADDON-KEY-US-DAD",
        "script_formula": {
            "style_name": "7-Part American Father Quiet Legal & Financial Justice",
            "target_length": "70.000 – 80.000 ký tự tiếng Anh Mỹ",
            "title_dna": "Người cha già bị con cái coi thường/chiếm đoạt tại bữa tiệc gia đình ➔ Âm thầm rút quỹ tín thác/bất động sản",
            "narrative_arc": "7 Phần: Sự phản bội công khai ➔ Thu thập chứng cứ pháp lý/ngân hàng Mỹ ➔ Khóa tài khoản/thu hồi ủy quyền ➔ Cao trào đối chất ➔ Bình yên tuổi già",
            "qa_gate": "Kiểm định logic pháp luật/tài chính Mỹ (Trust Fund, Deed, POA) và chính tả en-US",
            "linked_skills": ["viet-tieu-de-ong-gia-us", "viet-gian-y-ong-gia-us", "viet-kich-ban-ong-gia-us", "kiem-tra-kich-ban-ong-gia-us", "seo-ong-gia-us"],
        },
        "video_edit_formula": {
            "edit_style_name": "Photorealistic American Family Drama & Courtroom Tension",
            "opening_hook_rule": "Cận cảnh biểu cảm điềm tĩnh của người cha già trước sự ngạo mạn của con cái + Zoom vào văn bản pháp lý",
            "body_visual_rule": "Ảnh chụp chân thực chuẩn điện ảnh Mỹ (Photoreal 8K), nhịp cắt 6s–10s",
            "camera_and_effects": "Slow Push-In vào khuôn mặt nhân vật chính + Phụ đề vàng viền đen rõ nét",
            "audio_and_tts": "Giọng nam trầm lớn tuổi (Deep Senior American Male Voice) đĩnh đạc, uy quyền",
            "linked_skills": ["seo-ong-gia-us"],
        },
    },
    {
        "niche_key": "KEY_MX_DONA_FAMILIA",
        "niche_code": "MX-DONA",
        "niche_name": "🇲🇽 Key Mexico: Bà Cô (Doña) Drama Gia Đình & Phản Bội (es-MX Chuẩn)",
        "language": "es",
        "market": "Mexico (MX)",
        "unlock_addon_code": "ADDON-KEY-MX-DONA",
        "script_formula": {
            "style_name": "7-Part Mexican Spanish Family Drama (Doña / Nuera / Consuegra)",
            "target_length": "70.000 – 80.000 ký tự tiếng Tây Ban Nha Mexico (es-MX)",
            "title_dna": "Mi nuera / Mis hijos me humillaron ➔ Không ngờ Bà Cô nắm giữ Escritura / Công ty gia đình tại Mexico",
            "narrative_arc": "Tích hợp Canon Guard (chống trùng tên Doña, địa danh Colonia/CDMX, vật chứng trong 100 kịch bản) + 7 Phần cảm xúc gia đình Mexico",
            "qa_gate": "Kiểm định 24 chiều (>=98 điểm) + Bàn #7 Verificador TTS bung 100% từ viết tắt (Sra., Lic., CDMX, IMSS, CFE, MXN) & lọc từ Tây Ban Nha châu Âu",
            "linked_skills": ["titulos-drama-familiar-mexico", "canon-guard-drama-familiar-mexico", "arquitectura-drama-familiar-mexico", "escritor-y-reparacion-drama-familiar-mexico", "auditor-forense-guion-familiar-mexico", "seo-thumbnail-trailer-drama-familiar-mexico", "verificador-tts-drama-familiar-mexico"],
        },
        "video_edit_formula": {
            "edit_style_name": "Warm Latin Cinema (Telenovela Realism 16:9)",
            "opening_hook_rule": "Teaser 10–30 giây cảm xúc mạnh tại bàn ăn gia đình Mexico hoặc văn phòng công chứng (Notaría Pública)",
            "body_visual_rule": "Tông màu ấm đặc trưng Mexico, trang phục truyền thống/hiện đại lịch sự của Doña, nhịp đổi cảnh 6s–9s",
            "camera_and_effects": "Ken Burns chuyển động mượt + Hiệu ứng ánh sáng ấm + Phụ đề tiếng Tây Ban Nha chuẩn dấu câu `¿...?` `¡...!`",
            "audio_and_tts": "Giọng đọc tiếng Tây Ban Nha Mexico (es-MX) truyền cảm + Nhạc nền Guitar Acoustic Mexico nhẹ nhàng",
            "linked_skills": ["seo-thumbnail-trailer-drama-familiar-mexico"],
        },
    },
    {
        "niche_key": "KEY_MX_HACIENDA_RURAL",
        "niche_code": "MX-RURAL",
        "niche_name": "🇲🇽 Key Mexico: Đồng Quê Cổ Điển & Điền Trang Hacienda (85–100 Phút)",
        "language": "es",
        "market": "Mexico (MX)",
        "unlock_addon_code": "ADDON-KEY-MX-RURAL",
        "script_formula": {
            "style_name": "7-Part Mexican Rural Hacienda & Inheritance Audio Drama",
            "target_length": "70.000 – 82.000 ký tự (85 – 100 phút nghe)",
            "title_dna": "Bí mật điền trang Hacienda cổ / Người làm vườn già thực chất là chủ nhân vùng đất Jalisco/Michoacán",
            "narrative_arc": "7 Phần: Bối cảnh đồng quê Mexico giàu hình ảnh ➔ Xung đột đất đai/gia tộc ➔ Di chúc cổ & công lý",
            "qa_gate": "Kiểm định từ vựng nông thôn Mexico chuẩn xác, 1 lần sửa lỗi duy nhất",
            "linked_skills": ["viet-lai-tieu-de-mexico", "viet-gian-y-mexico", "viet-kich-ban-mexico", "kiem-tra-kich-ban-mexico", "seo-mexico"],
        },
        "video_edit_formula": {
            "edit_style_name": "Golden Hour Hacienda Panorama (Sepia & Warm Sunset)",
            "opening_hook_rule": "Cảnh toàn điền trang Hacienda dưới ánh hoàng hôn Mexico kèm câu dẫn mở màn đầy bí ẩn",
            "body_visual_rule": "Khung hình phong cảnh đồng quê rộng lớn xen kẽ cận cảnh nhân vật, nhịp đổi cảnh chậm 8s–12s phù hợp người nghe thư giãn",
            "camera_and_effects": "Pan ngang chậm (Horizontal Panorama) + Bộ lọc màu nắng chiều ấm áp",
            "audio_and_tts": "Giọng kể chuyện trầm ấm es-MX + Âm thanh gió đồng quê và guitar cổ điển",
            "linked_skills": ["seo-mexico"],
        },
    },
    {
        "niche_key": "KEY_US_MIDNIGHT_HORROR",
        "niche_code": "US-HORROR",
        "niche_name": "🇺🇸 Key Mỹ (US): Truyện Kinh Dị Ca Đêm & Đường Trường (Midnight Horror Anthology)",
        "language": "en",
        "market": "Hoa Kỳ (US)",
        "unlock_addon_code": "ADDON-KEY-US-HORROR",
        "script_formula": {
            "style_name": "US Night Shift & Highway Horror Anthology (3–8 Stories)",
            "target_length": "65.000 – 78.000 ký tự tiếng Anh Mỹ",
            "title_dna": "I Worked the Graveyard Shift / 3 True Night Shift Stories That Made Me Quit Immediately",
            "narrative_arc": "Đa dạng hóa 8 bối cảnh ca đêm Mỹ (Trạm xăng, Kiểm lâm, Bảo vệ bệnh viện, Tài xế xe tải đường dài) với luật nhân quả & bằng chứng thực tế",
            "qa_gate": "Kiểm định chống trùng bối cảnh giữa các truyện trong cùng tuyển tập + chính tả en-US",
            "linked_skills": ["us-midnight-title-rewriter", "us-midnight-outline-engine", "us-midnight-script-writer", "us-midnight-script-auditor", "us-midnight-seo-publish"],
        },
        "video_edit_formula": {
            "edit_style_name": "Atmospheric Night Rain & Low-Key VHS Thriller",
            "opening_hook_rule": "Cảnh ánh đèn pha ô tô xuyên qua màn sương đêm hoặc hành lang trực đêm nhấp nháy đèn huỳnh quang",
            "body_visual_rule": "Tông màu tối lạnh (Dark Teal & Shadow), nhịp đổi ảnh chậm 10s–15s tối ưu cho khán giả bật nghe ban đêm",
            "camera_and_effects": "Hiệu ứng mưa rơi lên kính + hạt nhiễu phim nhẹ (Subtle Film Grain) + Zoom cực chậm",
            "audio_and_tts": "Giọng đọc nam trầm khàn kể chuyện đêm khuya + Tiếng mưa đêm rả rích -22dB",
            "linked_skills": ["us-midnight-seo-publish"],
        },
    },
]


class NicheRecipeRegistry:
    """
    Quản lý Kho Công Thức Đa Ngách ('Mỗi Key 1 Cách Viết Kịch Bản & Edit Video Riêng').
    Cho phép thêm mới hoặc cập nhật từ xa qua GitHub OTA mà không cần cài lại ứng dụng.
    """

    @classmethod
    def load_all_recipes(cls) -> List[Dict[str, Any]]:
        if not os.path.exists(NICHE_RECIPES_PATH):
            cls.save_all_recipes(DEFAULT_NICHE_RECIPES)
            return list(DEFAULT_NICHE_RECIPES)
        try:
            with open(NICHE_RECIPES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                recipes = data.get("recipes", []) if isinstance(data, dict) else data
                if isinstance(recipes, list) and len(recipes) > 0:
                    # Đảm bảo mọi recipe mặc định đều có mặt
                    existing_keys = {r.get("niche_key") for r in recipes if isinstance(r, dict)}
                    merged = list(recipes)
                    for d_rec in DEFAULT_NICHE_RECIPES:
                        if d_rec["niche_key"] not in existing_keys:
                            merged.append(d_rec)
                    return merged
        except Exception:
            pass
        cls.save_all_recipes(DEFAULT_NICHE_RECIPES)
        return list(DEFAULT_NICHE_RECIPES)

    @classmethod
    def save_all_recipes(cls, recipes: List[Dict[str, Any]]) -> None:
        payload = {
            "schema_version": CURRENT_APP_VERSION,
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_niche_keys": len(recipes),
            "recipes": recipes,
        }
        tmp_path = f"{NICHE_RECIPES_PATH}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, NICHE_RECIPES_PATH)

    @classmethod
    def get_recipe_by_key(cls, niche_key: str) -> Dict[str, Any]:
        recipes = cls.load_all_recipes()
        for r in recipes:
            if r.get("niche_key") == niche_key or r.get("niche_code") == niche_key:
                return r
        return recipes[0]

    @classmethod
    def add_or_update_custom_niche_recipe(
        cls,
        niche_key: str,
        niche_name: str,
        language: str,
        market: str,
        script_style_name: str,
        target_length: str,
        title_dna: str,
        narrative_arc: str,
        edit_style_name: str,
        opening_hook_rule: str,
        body_visual_rule: str,
        camera_and_effects: str,
        audio_and_tts: str,
    ) -> Dict[str, Any]:
        recipes = cls.load_all_recipes()
        clean_key = niche_key.strip().upper().replace(" ", "_")
        if not clean_key.startswith("KEY_"):
            clean_key = f"KEY_{clean_key}"
        short_code = clean_key.replace("KEY_", "")[:10]
        addon_code = f"ADDON-{clean_key.replace('_', '-')}"

        new_entry = {
            "niche_key": clean_key,
            "niche_code": short_code,
            "niche_name": niche_name.strip() or clean_key,
            "language": language.strip() or "ja",
            "market": market.strip() or "Quốc tế",
            "unlock_addon_code": addon_code,
            "script_formula": {
                "style_name": script_style_name.strip() or "Custom AI Script Formula",
                "target_length": target_length.strip() or "45.000 – 75.000 ký tự",
                "title_dna": title_dna.strip() or "Chuẩn CTR cao theo ngách",
                "narrative_arc": narrative_arc.strip() or "Mở đầu Hook ➔ Xung đột ➔ Cao trào ➔ Giải quyết",
                "qa_gate": "Kiểm định logic & chính tả tự động >= 96/100",
                "linked_skills": ["custom-niche-workflow"],
            },
            "video_edit_formula": {
                "edit_style_name": edit_style_name.strip() or "Custom FFmpeg Cinematic Edit",
                "opening_hook_rule": opening_hook_rule.strip() or "Video/Animation Hook 30s đầu giữ chân người xem",
                "body_visual_rule": body_visual_rule.strip() or "Ảnh tĩnh 16:9 nhịp 6s–10s kết hợp B-roll",
                "camera_and_effects": camera_and_effects.strip() or "Ken Burns Pan/Zoom + Phụ đề nổi bật",
                "audio_and_tts": audio_and_tts.strip() or "Giọng đọc AI tự nhiên + Nhạc nền -24dB + Render GPU NVENC",
                "linked_skills": ["custom-video-editor"],
            },
        }
        updated = False
        for idx, r in enumerate(recipes):
            if r.get("niche_key") == clean_key:
                recipes[idx] = new_entry
                updated = True
                break
        if not updated:
            recipes.append(new_entry)
        cls.save_all_recipes(recipes)
        return {"ok": True, "recipe": new_entry, "total_recipes": len(recipes)}


# ==============================================================================
# 2. HỆ THỐNG MÃ KEY KÍCH HOẠT BẢN QUYỀN CHO KHÁCH (LICENSE KEY SYSTEM)
# ==============================================================================
class LicenseKeyManager:
    """
    Hệ thống tạo & xác thực Mã Key Kích Hoạt Bản Quyền Phần Mềm (HMAC-SHA256 Signed Keys):
    - Cho phép Chủ phần mềm tạo mã Key cho từng khách hàng (Gói 3 Kênh / 5 Kênh / 10 Kênh / Trọn Đời).
    - Cho phép mở khóa thêm từng Gói Key Ngách Kịch Bản & Edit Video (`ADDON-KEY-...`).
    - Tự động xuất bảng tổng hợp Mã Key vào `DANH_SACH_MA_KEY_KICH_HOAT_CHO_KHACH.md`.
    """

    @staticmethod
    def get_hardware_id() -> str:
        """Lấy mã định danh phần cứng máy tính (HWID) để quản lý thiết bị kích hoạt."""
        try:
            node = str(uuid.getnode())
            comp = os.environ.get("COMPUTERNAME", "WINPC")
            raw = f"{comp}-{node}"
            h = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()[:12]
            return f"PC-{h[:4]}-{h[4:8]}-{h[8:12]}"
        except Exception:
            return "PC-STD-0001-9999"

    @classmethod
    def generate_signed_license_key(
        cls,
        tier_code: str = "VIP10",
        max_channels: int = 10,
        valid_days: int = 365,
        niche_scope: str = "ALL",
        customer_tag: str = "CLIENT01",
    ) -> Dict[str, Any]:
        """
        Tạo mã Key kích hoạt có chữ ký số HMAC-SHA256 chống làm giả:
        Định dạng: `YTES-<TIER>-<MAX_CH>C-<EXP_YYYYMMDD>-<SCOPE>-<TAG>-<SIG8>`
        """
        tier_clean = tier_code.upper().replace("-", "")[:6]
        max_ch = max(1, min(10, int(max_channels)))
        if valid_days >= 3650:
            exp_str = "20991231"
            exp_human = "TRỌN ĐỜI (LIFETIME)"
        else:
            exp_dt = datetime.date.today() + datetime.timedelta(days=max(1, int(valid_days)))
            exp_str = exp_dt.strftime("%Y%m%d")
            exp_human = exp_dt.strftime("%Y-%m-%d")

        scope_clean = niche_scope.upper().replace("-", "")[:6]
        tag_clean = "".join(c for c in customer_tag.upper() if c.isalnum())[:6] or "CUST01"

        payload_core = f"YTES-{tier_clean}-{max_ch}C-{exp_str}-{scope_clean}-{tag_clean}"
        sig = hmac.new(_MASTER_HMAC_SECRET, payload_core.encode("utf-8"), hashlib.sha256).hexdigest().upper()[:8]
        full_key = f"{payload_core}-{sig}"

        return {
            "license_key": full_key,
            "tier_code": tier_clean,
            "max_channels": max_ch,
            "expires_yyyymmdd": exp_str,
            "expires_display": exp_human,
            "niche_scope": scope_clean,
            "customer_tag": tag_clean,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @classmethod
    def verify_and_decode_license_key(cls, raw_key: str) -> Dict[str, Any]:
        """Kiểm tra chữ ký số HMAC-SHA256 và thời hạn của Mã Key Kích Hoạt."""
        k = (raw_key or "").strip().upper()
        if not k:
            return {"valid": False, "reason": "Vui lòng nhập Mã Key Kích Hoạt!"}

        # Hỗ trợ Master Key cố định siêu nhanh dành cho Chủ Phần Mềm
        if k in ("YTES-ADMIN-MASTER-2026-FULL-8888", "YTES-OWNER-ULTIMATE-10CH-LIFETIME"):
            return {
                "valid": True,
                "license_key": k,
                "tier_code": "MASTER_OWNER",
                "tier_label": "👑 GÓI CHỦ PHẦN MỀM (ADMIN MASTER TRỌN ĐỜI)",
                "max_channels": 10,
                "expires_display": "TRỌN ĐỜI (LIFETIME)",
                "niche_scope": "ALL",
                "customer_tag": "OWNER_ADMIN",
                "is_admin_master": True,
            }

        parts = k.split("-")
        # Định dạng chuẩn: YTES - TIER - {N}C - YYYYMMDD - SCOPE - TAG - SIG8 (7 phần)
        if len(parts) != 7 or parts[0] != "YTES":
            return {"valid": False, "reason": "Định dạng Mã Key không hợp lệ (Chuẩn: YTES-TIER-10C-YYYYMMDD-SCOPE-TAG-SIG)."}

        _, tier_clean, ch_part, exp_str, scope_clean, tag_clean, sig_given = parts
        payload_core = f"YTES-{tier_clean}-{ch_part}-{exp_str}-{scope_clean}-{tag_clean}"
        expected_sig = hmac.new(_MASTER_HMAC_SECRET, payload_core.encode("utf-8"), hashlib.sha256).hexdigest().upper()[:8]

        if not hmac.compare_digest(sig_given, expected_sig):
            return {"valid": False, "reason": "Chữ ký bảo mật của Mã Key không hợp lệ (Key bị sai ký tự)!"}

        try:
            max_ch = int(ch_part.replace("C", ""))
        except Exception:
            max_ch = 3

        today_str = datetime.date.today().strftime("%Y%m%d")
        if exp_str < today_str:
            return {
                "valid": False,
                "reason": f"Mã Key đã hết hạn vào ngày {exp_str[:4]}-{exp_str[4:6]}-{exp_str[6:8]}. Vui lòng liên hệ gia hạn!",
            }

        exp_human = "TRỌN ĐỜI (LIFETIME)" if exp_str >= "20900101" else f"{exp_str[:4]}-{exp_str[4:6]}-{exp_str[6:8]}"
        tier_label_map = {
            "MASTER": "👑 GÓI CHỦ PHẦN MỀM (ADMIN MASTER TRỌN ĐỜI)",
            "VIP10": "💎 GÓI DOANH NGHIỆP VIP (10 KÊNH / 1 MÁY)",
            "PRO5": "🚀 GÓI CHUYÊN NGHIỆP PRO (5 KÊNH / 1 MÁY)",
            "TRIAL3": "🌱 GÓI DÙNG THỬ TRIAL (3 KÊNH / 1 MÁY)",
        }
        return {
            "valid": True,
            "license_key": k,
            "tier_code": tier_clean,
            "tier_label": tier_label_map.get(tier_clean, f"GÓI BẢN QUYỀN ({tier_clean})"),
            "max_channels": max_ch,
            "expires_display": exp_human,
            "niche_scope": scope_clean,
            "customer_tag": tag_clean,
            "is_admin_master": (tier_clean == "MASTER"),
        }

    @classmethod
    def ensure_initial_admin_key_vault(cls) -> Dict[str, Any]:
        """
        Khởi tạo sẵn Bộ Mã Key Kích Hoạt mẫu cho Chủ phần mềm (Lưu vào `config/admin_generated_keys_vault.json`
        và xuất ra file Markdown `DANH_SACH_MA_KEY_KICH_HOAT_CHO_KHACH.md`).
        """
        if os.path.exists(ADMIN_KEYS_VAULT_PATH):
            try:
                with open(ADMIN_KEYS_VAULT_PATH, "r", encoding="utf-8") as f:
                    vault = json.load(f)
                    if vault.get("keys"):
                        return vault
            except Exception:
                pass

        generated_keys = [
            # 1. Key Chủ Phần Mềm (Master Trọn Đời)
            cls.generate_signed_license_key("MASTER", max_channels=10, valid_days=36500, niche_scope="ALL", customer_tag="OWNER"),
            # 2. 5 Key Khách VIP (10 Kênh / 1 Năm / Tất cả các ngách)
            cls.generate_signed_license_key("VIP10", max_channels=10, valid_days=365, niche_scope="ALL", customer_tag="VIP001"),
            cls.generate_signed_license_key("VIP10", max_channels=10, valid_days=365, niche_scope="ALL", customer_tag="VIP002"),
            cls.generate_signed_license_key("VIP10", max_channels=10, valid_days=365, niche_scope="ALL", customer_tag="VIP003"),
            cls.generate_signed_license_key("VIP10", max_channels=10, valid_days=365, niche_scope="JPK1", customer_tag="VIPJP1"),
            cls.generate_signed_license_key("VIP10", max_channels=10, valid_days=365, niche_scope="USMX", customer_tag="VIPUS1"),
            # 3. 3 Key Khách PRO (5 Kênh / 180 Ngày)
            cls.generate_signed_license_key("PRO5", max_channels=5, valid_days=180, niche_scope="ALL", customer_tag="PRO001"),
            cls.generate_signed_license_key("PRO5", max_channels=5, valid_days=180, niche_scope="JPK1", customer_tag="PRO002"),
            cls.generate_signed_license_key("PRO5", max_channels=5, valid_days=180, niche_scope="USMX", customer_tag="PRO003"),
            # 4. 3 Key Khách Dùng Thử (3 Kênh / 7 Ngày)
            cls.generate_signed_license_key("TRIAL3", max_channels=3, valid_days=7, niche_scope="JPK1", customer_tag="TEST01"),
            cls.generate_signed_license_key("TRIAL3", max_channels=3, valid_days=7, niche_scope="ALL", customer_tag="TEST02"),
            cls.generate_signed_license_key("TRIAL3", max_channels=3, valid_days=14, niche_scope="ALL", customer_tag="TEST03"),
        ]

        vault = {
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "master_quick_key": "YTES-ADMIN-MASTER-2026-FULL-8888",
            "keys": generated_keys,
        }
        with open(ADMIN_KEYS_VAULT_PATH, "w", encoding="utf-8") as f:
            json.dump(vault, f, ensure_ascii=False, indent=2)

        cls.export_keys_markdown_guide(vault)
        return vault

    @classmethod
    def export_keys_markdown_guide(cls, vault: Optional[Dict[str, Any]] = None) -> str:
        if not vault:
            vault = cls.ensure_initial_admin_key_vault()
        recipes = NicheRecipeRegistry.load_all_recipes()
        md_path = os.path.join(BASE_DIR, "DANH_SACH_MA_KEY_KICH_HOAT_CHO_KHACH.md")
        lines = [
            "# 🔑 BẢNG MÃ KEY KÍCH HOẠT BẢN QUYỀN & TÀI KHOẢN CẦN THIẾT KHI BÀN GIAO CHO KHÁCH",
            f"> **Cập nhật lần cuối**: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}` | **Phiên bản App**: `v{CURRENT_APP_VERSION}`",
            f"> **Kho Cập Nhật Từ Xa (GitHub OTA)**: `{GITHUB_REPO_URL}`",
            "",
            "---",
            "",
            "## 1. Khi Chuyển Ứng Dụng Cho Khách Thì Khách Cần Những Tài Khoản Gì?",
            "",
            "### A. 2 Thứ Bắt Buộc Để Chạy Ngay:",
            "1. **Mã Key Kích Hoạt Bản Quyền (`License Key` do bạn cấp bên dưới):**",
            "   - Khách mở phần mềm `YouTube_Enterprise_Studio.exe` ➔ Bấm nút **「🔑 Kích Hoạt Key Bản Quyền」** ➔ Dán Mã Key bạn cấp để mở khóa số lượng kênh (3 / 5 / 10 kênh) và các Gói Công Thức Viết Kịch Bản & Edit Video theo ngách.",
            "2. **Tài khoản Gmail & Kênh YouTube (`1 đến 10 tài khoản`):**",
            "   - Khách tự đăng nhập tài khoản Gmail/YouTube của khách vào từng Chrome Profile cô lập của phần mềm bằng nút **「🔑 1. Mở Chrome Đăng Nhập Gmail & Kênh」**.",
            "   - Phần mềm lưu Cookie đăng nhập cục bộ ngay trên máy khách (`PROFILES/KENH_01...`), hoàn toàn riêng tư và cô lập.",
            "",
            "### B. Các Tài Khoản Bổ Trợ (Tùy Chọn Theo Nhu Cầu Của Khách):",
            "3. **API Key Trí Tuệ Nhân Tạo (`Google Gemini API Key` — Có gói Miễn Phí tại `https://aistudio.google.com/app/apikey` hoặc `OpenAI API Key`):**",
            "   - Khách dán vào mục **「🤖 Cấu Hình Model AI」** trên phần mềm để Bộ Não AI tự suy nghĩ lộ trình nuôi độc bản, đọc phụ đề video viết bình luận có mốc `MM:SS`, và tự viết kịch bản + SEO.",
            "   - *(Lưu ý: Kể cả khi khách chưa nhập API Key, phần mềm vẫn chạy mượt nhờ bộ não `Heuristic Cognitive Engine` tích hợp sẵn).* ",
            "4. **Proxy Tĩnh Riêng (`HTTP / HTTPS / SOCKS5` — Tùy chọn khi nuôi nhiều kênh):**",
            "   - Nếu khách chỉ nuôi `1–3 kênh`: Dùng trực tiếp mạng Wi-Fi/LAN gốc của gia đình không cần mua Proxy.",
            "   - Nếu khách nuôi `5–10 kênh` cùng lúc: Khuyên khách gắn mỗi Profile 1 Proxy tĩnh riêng qua nút **「🌐 Gắn / Kiểm Tra Proxy & IP」**.",
            "",
            "---",
            "",
            "## 2. Danh Sách Mã Key Kích Hoạt Đã Tạo Sẵn Cho Bạn (Dùng Ngay)",
            "",
            "### 👑 A. Mã Key Master Dành Riêng Cho Bạn (Chủ Phần Mềm — Mở Khóa Full 10 Kênh + Quyền Tạo Key Mới)",
            "- **Mã Key Master Nhanh**: `YTES-ADMIN-MASTER-2026-FULL-8888`",
        ]
        for k_info in vault.get("keys", []):
            if k_info.get("tier_code") == "MASTER":
                lines.append(f"- **Mã Key Master Ký Số HMAC**: `{k_info['license_key']}` (Hạn: `{k_info['expires_display']}`)")

        lines.extend([
            "",
            "### 💎 B. Danh Sách Mã Key Cấp Cho Khách Hàng (Ký Số Bảo Mật HMAC-SHA256)",
            "| Mã Khách | Gói Bản Quyền | Số Kênh Tối Đa | Thời Hạn | Phạm Vi Ngách | Mã Key Kích Hoạt (Copy gửi khách) |",
            "|---|---|---:|---|---|---|",
        ])
        for k_info in vault.get("keys", []):
            if k_info.get("tier_code") == "MASTER":
                continue
            lines.append(
                f"| `{k_info['customer_tag']}` | **{k_info['tier_code']}** | `{k_info['max_channels']} Kênh` | `{k_info['expires_display']}` | `{k_info['niche_scope']}` | `{k_info['license_key']}` |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 3. Danh Sách Các Mã Mở Khóa Từng Key Ngách Riêng (`Mỗi Key 1 Cách Viết Kịch Bản & Edit Video Riêng`)",
            "| Mã Key Ngách | Tên Ngách & Thị Trường | Mã Mở Khóa Ngách (`Add-on Code`) | Công Thức Kịch Bản Riêng | Công Thức Edit Video Riêng |",
            "|---|---|---|---|---|",
        ])
        for r in recipes:
            sf = r.get("script_formula", {})
            ef = r.get("video_edit_formula", {})
            lines.append(
                f"| `{r['niche_key']}` | **{r['niche_name']}** | `{r['unlock_addon_code']}` | {sf.get('style_name')} ({sf.get('target_length')}) | {ef.get('edit_style_name')} |"
            )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return md_path

    @classmethod
    def get_current_license_state(cls) -> Dict[str, Any]:
        """Đọc trạng thái kích hoạt bản quyền hiện tại của máy."""
        vault = cls.ensure_initial_admin_key_vault()
        hwid = cls.get_hardware_id()
        recipes = NicheRecipeRegistry.load_all_recipes()
        all_niche_keys = [r["niche_key"] for r in recipes]

        if os.path.exists(LICENSE_STATE_PATH):
            try:
                with open(LICENSE_STATE_PATH, "r", encoding="utf-8") as f:
                    st = json.load(f)
                chk = cls.verify_and_decode_license_key(st.get("license_key", ""))
                if chk.get("valid"):
                    st["valid"] = True
                    st["hardware_id"] = hwid
                    st["total_available_niche_recipes"] = len(recipes)
                    if st.get("niche_scope") == "ALL" or chk.get("is_admin_master"):
                        st["unlocked_niche_keys"] = all_niche_keys
                    return st
            except Exception:
                pass

        # Mặc định trên máy của bạn: Tự động kích hoạt sẵn Key Master Chủ Phần Mềm
        master_key_obj = vault["keys"][0]
        default_state = {
            "valid": True,
            "license_key": master_key_obj["license_key"],
            "tier_code": "MASTER",
            "tier_label": "👑 GÓI CHỦ PHẦN MỀM (ADMIN MASTER TRỌN ĐỜI)",
            "customer_tag": "OWNER",
            "max_channels": 10,
            "expires_display": "TRỌN ĐỜI (LIFETIME)",
            "niche_scope": "ALL",
            "unlocked_niche_keys": all_niche_keys,
            "is_admin_master": True,
            "hardware_id": hwid,
            "activated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_available_niche_recipes": len(recipes),
        }
        cls.save_license_state(default_state)
        return default_state

    @classmethod
    def save_license_state(cls, state: Dict[str, Any]) -> None:
        tmp = f"{LICENSE_STATE_PATH}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, LICENSE_STATE_PATH)

    @classmethod
    def activate_license_key(cls, raw_key: str) -> Dict[str, Any]:
        """Kích hoạt Mã Key Bản Quyền Chính hoặc Mã Mở Khóa Thêm Ngách (`ADDON-KEY-...`)."""
        clean_input = (raw_key or "").strip().upper()
        recipes = NicheRecipeRegistry.load_all_recipes()
        all_niche_keys = [r["niche_key"] for r in recipes]

        # Trường hợp 1: Khách nhập Mã Mở Khóa Thêm Ngách (ADDON-KEY-...)
        for r in recipes:
            if clean_input == r.get("unlock_addon_code", "").upper() or clean_input == r.get("niche_key", "").upper():
                cur = cls.get_current_license_state()
                unlocked = list(cur.get("unlocked_niche_keys") or [])
                if r["niche_key"] not in unlocked:
                    unlocked.append(r["niche_key"])
                cur["unlocked_niche_keys"] = unlocked
                cls.save_license_state(cur)
                return {
                    "ok": True,
                    "addon_unlocked": True,
                    "message": f"✅ Đã mở khóa thành công Gói Ngách 「{r['niche_name']}」!",
                    "license_state": cur,
                }

        # Trường hợp 2: Khách nhập Mã Key Kích Hoạt Bản Quyền Phần Mềm (YTES-...)
        chk = cls.verify_and_decode_license_key(clean_input)
        if not chk.get("valid"):
            return {"ok": False, "error": chk.get("reason", "Mã Key không hợp lệ")}

        scope = chk.get("niche_scope", "ALL")
        if scope == "ALL" or chk.get("is_admin_master"):
            unlocked_niches = all_niche_keys
        elif scope == "JPK1":
            unlocked_niches = ["KEY_JP_K1_MANGA", "KEY_JP_KUCHIKOMI_60"]
        elif scope == "USMX":
            unlocked_niches = [k for k in all_niche_keys if "_US_" in k or "_MX_" in k]
        else:
            unlocked_niches = all_niche_keys[:3]

        new_state = {
            "valid": True,
            "license_key": chk["license_key"],
            "tier_code": chk["tier_code"],
            "tier_label": chk["tier_label"],
            "customer_tag": chk["customer_tag"],
            "max_channels": chk["max_channels"],
            "expires_display": chk["expires_display"],
            "niche_scope": scope,
            "unlocked_niche_keys": unlocked_niches,
            "is_admin_master": chk.get("is_admin_master", False),
            "hardware_id": cls.get_hardware_id(),
            "activated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_available_niche_recipes": len(recipes),
        }
        cls.save_license_state(new_state)
        return {
            "ok": True,
            "message": f"🎉 Kích hoạt bản quyền thành công: {chk['tier_label']} (Tối đa {chk['max_channels']} kênh | Hạn: {chk['expires_display']})!",
            "license_state": new_state,
        }

    @classmethod
    def admin_create_new_customer_key(
        cls,
        tier_code: str,
        max_channels: int,
        valid_days: int,
        niche_scope: str,
        customer_tag: str,
    ) -> Dict[str, Any]:
        """Dành cho Chủ Phần Mềm: Tạo mã Key mới cho khách ngay trên giao diện và lưu vào kho."""
        vault = cls.ensure_initial_admin_key_vault()
        new_key_obj = cls.generate_signed_license_key(
            tier_code=tier_code,
            max_channels=max_channels,
            valid_days=valid_days,
            niche_scope=niche_scope,
            customer_tag=customer_tag,
        )
        vault.setdefault("keys", []).insert(1, new_key_obj)
        vault["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(ADMIN_KEYS_VAULT_PATH, "w", encoding="utf-8") as f:
            json.dump(vault, f, ensure_ascii=False, indent=2)
        cls.export_keys_markdown_guide(vault)
        return {"ok": True, "new_key": new_key_obj, "total_keys": len(vault["keys"])}


# ==============================================================================
# 3. HỆ THỐNG CẬP NHẬT TỪ XA QUA GITHUB KHÔNG CẦN TẢI LẠI ỨNG DỤNG (OTA UPDATER)
# ==============================================================================
OTA_HOT_UPDATE_FILES = [
    "version_manifest.json",
    "youtube_enterprise_server.py",
    "youtube_enterprise_desktop_app.py",
    "engine/browser_cdp_manager.py",
    "engine/youtube_persona_engine.py",
    "engine/youtube_seo_uploader_engine.py",
    "engine/ai_cognitive_brain.py",
    "engine/ai_supervisor_watchdog.py",
    "engine/channel_scanner_and_analytics.py",
    "engine/k1_department_orchestrator.py",
    "engine/license_and_updater_manager.py",
    "config/niche_recipes_registry.json",
]


class OTAUpdaterManager:
    """
    Hệ Thống Cập Nhật Từ Xa Qua GitHub (Over-The-Air Hot Updater):
    - Kiểm tra phiên bản mới và các Gói Key Ngách mới từ kho GitHub `phamngocthu661-lang/youtube-enterprise-studio`.
    - Tải trực tiếp các file code `.py` và `config/niche_recipes_registry.json` mới nhất về máy khách qua HTTPS
      (hoặc `git pull`) mà KHÔNG chạm vào dữ liệu kênh/Profile riêng của khách (`PROFILES/`, `CHANNELS_DATA/`).
    - Tự động nạp nóng (Hot-Reload) công thức kịch bản/edit mới mà khách KHÔNG cần tải lại file `.exe`!
    """

    @classmethod
    def build_local_version_manifest(cls, release_notes: str = "") -> Dict[str, Any]:
        recipes = NicheRecipeRegistry.load_all_recipes()
        file_hashes: Dict[str, str] = {}
        for rel_path in OTA_HOT_UPDATE_FILES:
            if rel_path == "version_manifest.json":
                continue
            abs_p = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
            if os.path.exists(abs_p):
                try:
                    with open(abs_p, "rb") as f:
                        file_hashes[rel_path] = hashlib.sha256(f.read()).hexdigest()[:16]
                except Exception:
                    pass

        manifest = {
            "app_name": "YouTube Enterprise Multi-Agent Studio",
            "version": CURRENT_APP_VERSION,
            "build_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "github_repo": f"{GITHUB_OWNER}/{GITHUB_REPO}",
            "github_branch": GITHUB_BRANCH,
            "github_url": GITHUB_REPO_URL,
            "total_niche_recipes": len(recipes),
            "niche_keys_available": [r["niche_key"] for r in recipes],
            "release_notes": release_notes
            or (
                "v3.9.0: Tích hợp Hệ thống Mã Key Kích Hoạt Bản Quyền (HMAC-SHA256), "
                "Kho 8+ Gói Key Công Thức Viết Kịch Bản & Edit Video Riêng Theo Ngách, "
                "Chu trình Nuôi Gmail & Hệ Sinh Thái Google 12 phút như người thật, "
                "và Cập Nhật Tự Động Từ Xa Qua GitHub (OTA Hot-Update)."
            ),
            "hot_update_files": [p for p in OTA_HOT_UPDATE_FILES if p != "version_manifest.json"],
            "file_hashes": file_hashes,
        }
        with open(VERSION_MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        return manifest

    @classmethod
    def get_local_manifest(cls) -> Dict[str, Any]:
        if not os.path.exists(VERSION_MANIFEST_PATH):
            return cls.build_local_version_manifest()
        try:
            with open(VERSION_MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return cls.build_local_version_manifest()

    @classmethod
    def check_for_remote_updates(cls) -> Dict[str, Any]:
        """Kiểm tra bản cập nhật mới từ kho GitHub OTA."""
        local_m = cls.get_local_manifest()
        manifest_url = f"{GITHUB_RAW_BASE}/version_manifest.json?t={int(time.time())}"
        try:
            req = urllib.request.Request(
                manifest_url,
                headers={"User-Agent": "YouTubeEnterpriseStudio-OTA/3.9", "Cache-Control": "no-cache"},
            )
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                remote_m = json.loads(resp.read().decode("utf-8"))

            local_hashes = local_m.get("file_hashes", {})
            remote_hashes = remote_m.get("file_hashes", {})
            changed_files = [
                f_path
                for f_path, r_hash in remote_hashes.items()
                if local_hashes.get(f_path) != r_hash
            ]
            has_update = (
                remote_m.get("version") != local_m.get("version")
                or len(changed_files) > 0
                or int(remote_m.get("total_niche_recipes", 0)) > int(local_m.get("total_niche_recipes", 0))
            )
            return {
                "ok": True,
                "has_update": has_update,
                "local_version": local_m.get("version", CURRENT_APP_VERSION),
                "remote_version": remote_m.get("version", CURRENT_APP_VERSION),
                "remote_build_date": remote_m.get("build_date", ""),
                "remote_release_notes": remote_m.get("release_notes", ""),
                "remote_total_niche_recipes": remote_m.get("total_niche_recipes", 0),
                "changed_files": changed_files,
                "github_url": GITHUB_REPO_URL,
                "checked_at": datetime.datetime.now().strftime("%H:%M:%S"),
            }
        except Exception as e:
            return {
                "ok": False,
                "has_update": False,
                "local_version": local_m.get("version", CURRENT_APP_VERSION),
                "remote_version": local_m.get("version", CURRENT_APP_VERSION),
                "github_url": GITHUB_REPO_URL,
                "error": f"Không thể kết nối GitHub OTA ({e})",
                "checked_at": datetime.datetime.now().strftime("%H:%M:%S"),
            }

    @classmethod
    def apply_remote_ota_update(cls) -> Dict[str, Any]:
        """
        Tải và áp dụng bản cập nhật mới nhất từ GitHub OTA ngay lập tức (Không cần tải lại App `.exe`):
        1. Sao lưu các file hiện tại vào `BACKUPS/ota_backup_<timestamp>/`.
        2. Tải trực tiếp các file có thay đổi từ `raw.githubusercontent.com/phamngocthu661-lang/youtube-enterprise-studio/main/...`
           (Hoặc đồng bộ `git pull` nếu máy có Git).
        3. Bảo toàn 100% dữ liệu riêng của khách (`channels_registry.json`, `license_state.json`, `PROFILES/`, `CHANNELS_DATA/`).
        """
        check_res = cls.check_for_remote_updates()
        backup_dir = os.path.join(BASE_DIR, "BACKUPS", f"ota_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(backup_dir, exist_ok=True)

        files_to_fetch = check_res.get("changed_files") or OTA_HOT_UPDATE_FILES
        if "config/niche_recipes_registry.json" not in files_to_fetch:
            files_to_fetch.append("config/niche_recipes_registry.json")
        if "version_manifest.json" not in files_to_fetch:
            files_to_fetch.append("version_manifest.json")

        updated_files: List[str] = []
        errors: List[str] = []

        for rel_path in files_to_fetch:
            abs_target = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
            # Sao lưu bản cũ trước khi ghi đè
            if os.path.exists(abs_target):
                bak_target = os.path.join(backup_dir, rel_path.replace("/", os.sep))
                os.makedirs(os.path.dirname(bak_target), exist_ok=True)
                try:
                    shutil.copy2(abs_target, bak_target)
                except Exception:
                    pass

            raw_url = f"{GITHUB_RAW_BASE}/{rel_path}?t={int(time.time())}"
            try:
                req = urllib.request.Request(
                    raw_url,
                    headers={"User-Agent": "YouTubeEnterpriseStudio-OTA/3.9", "Cache-Control": "no-cache"},
                )
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    content_bytes = resp.read()
                if content_bytes and len(content_bytes) > 10:
                    os.makedirs(os.path.dirname(abs_target), exist_ok=True)
                    tmp_file = f"{abs_target}.ota_tmp"
                    with open(tmp_file, "wb") as f_out:
                        f_out.write(content_bytes)
                    os.replace(tmp_file, abs_target)
                    updated_files.append(rel_path)
            except Exception as ex:
                errors.append(f"{rel_path}: {ex}")

        # Đồng bộ thêm git fetch/reset cho các file code nếu máy có .git
        if os.path.isdir(os.path.join(BASE_DIR, ".git")):
            try:
                subprocess.run(
                    ["git", "fetch", "origin", GITHUB_BRANCH],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    timeout=12,
                )
            except Exception:
                pass

        recipes_now = NicheRecipeRegistry.load_all_recipes()
        return {
            "ok": len(updated_files) > 0,
            "updated_files_count": len(updated_files),
            "updated_files": updated_files,
            "backup_dir": backup_dir,
            "total_niche_recipes_now": len(recipes_now),
            "new_version": check_res.get("remote_version", CURRENT_APP_VERSION),
            "errors": errors,
            "message": (
                f"✅ Đã cập nhật từ xa thành công {len(updated_files)} mô-đun từ GitHub OTA "
                f"(Phiên bản v{check_res.get('remote_version', CURRENT_APP_VERSION)} • {len(recipes_now)} Gói Key Ngách)! "
                f"Toàn bộ Profile Chrome & Dữ liệu kênh của bạn được giữ nguyên 100%."
            ),
        }

    @classmethod
    def admin_publish_update_to_github(cls, commit_message: str = "") -> Dict[str, Any]:
        """
        [Dành cho Chủ Phần Mềm]: Đóng gói `version_manifest.json` mới nhất và đẩy (`git push`)
        lên kho GitHub OTA để toàn bộ máy khách nhận được bản cập nhật & Gói Key Ngách mới ngay lập tức!
        """
        msg = (commit_message or "").strip() or f"OTA Hot-Update v{CURRENT_APP_VERSION} ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})"
        manifest = cls.build_local_version_manifest(release_notes=msg)
        try:
            subprocess.run(["git", "add", "-A"], cwd=BASE_DIR, capture_output=True, text=True, timeout=15)
            commit_res = subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=15,
            )
            push_res = subprocess.run(
                ["git", "push", "-u", "origin", GITHUB_BRANCH],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=30,
            )
            ok = push_res.returncode == 0
            return {
                "ok": ok,
                "manifest": manifest,
                "commit_output": (commit_res.stdout or commit_res.stderr or "").strip(),
                "push_output": (push_res.stdout or push_res.stderr or "").strip(),
                "github_url": GITHUB_REPO_URL,
                "message": (
                    f"🚀 Đã đẩy bản cập nhật OTA lên GitHub ({GITHUB_REPO_URL}) thành công! "
                    f"Tất cả máy khách bấm 『Cập Nhật Từ Xa』 sẽ nhận được ngay."
                    if ok
                    else f"⚠️ Lỗi khi đẩy lên GitHub: {push_res.stderr}"
                ),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

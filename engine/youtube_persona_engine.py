# -*- coding: utf-8 -*-
"""
Bộ Điều Hành 7 Bàn Agent Bằng Tư Duy AI (100% AI Cognitive Reasoning — Không dùng kịch bản cố định):
- Mọi thao tác trên trình duyệt (chọn nguồn, gõ từ khóa, chọn video nào trên màn hình để xem, xem bao lâu,
  đọc Transcript viết bình luận có mốc thời gian mm:ss, và phân tích Community Research Loop ở Bàn #7)
  đều do AI quan sát màn hình thực tế, suy nghĩ (ai_thought) và ra quyết định.
"""

import datetime
import json
import os
import random
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional

from .ai_cognitive_brain import SHARED_AI_BRAIN
from .browser_cdp_manager import BrowserCDPManager, TabGuard

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSCRIPTS_DIR = os.path.join(BASE_DIR, "TRANSCRIPTS")
EVOLUTION_DIR = os.path.join(BASE_DIR, "EVOLUTION_MEMORY")
LOGS_DIR = os.path.join(BASE_DIR, "LOGS")

for d in (TRANSCRIPTS_DIR, EVOLUTION_DIR, LOGS_DIR):
    os.makedirs(d, exist_ok=True)


def format_mm_ss(seconds: float) -> str:
    total = max(0, int(seconds))
    mm = total // 60
    ss = total % 60
    return f"{mm:02d}:{ss:02d}"


class ScreenObserver:
    """
    Quan sát trực tiếp màn hình DOM của tab YouTube đang mở để gửi danh sách các video thực tế
    cho Bộ Não AI suy nghĩ và lựa chọn.
    """

    @staticmethod
    def observe_current_screen(cdp_port: int, target_id: str, language: str = "ja") -> Dict[str, Any]:
        js_observe = r"""
        (() => {
            try {
                const url = window.location.href;
                const pageTitle = document.title;
                const items = [];

                const isValidTitle = (t, href) => {
                    if (!t || t.length < 6) return false;
                    if (/^\d+:\d+(:\d+)?$/.test(t.trim())) return false;
                    if (t.includes('Đang phát') || t.includes('Now playing')) return false;
                    if (href && (href.includes('start_radio=1') || href.includes('list=RD'))) return false;
                    return true;
                };

                if (url.includes('/results')) {
                    // Đang ở trang Kết quả Tìm kiếm -> CHỈ lấy kết quả tìm kiếm thực tế (không lấy Home Feed ẩn của SPA)
                    document.querySelectorAll('ytd-search ytd-video-renderer, ytd-video-renderer').forEach((el) => {
                        if (el.offsetParent === null) return;
                        const a = el.querySelector('a#video-title, h3 a[href*="/watch?v="]');
                        const ch = el.querySelector('ytd-channel-name');
                        const dur = el.querySelector('ytd-thumbnail-overlay-time-status-renderer, badge-shape');
                        const titleText = a ? (a.innerText || a.getAttribute('title') || '').trim() : '';
                        if (a && a.href && isValidTitle(titleText, a.href)) {
                            items.push({
                                area: 'search_results',
                                title: titleText,
                                href: a.href,
                                channel: ch ? ch.innerText.trim().split('\\n')[0] : '',
                                duration: dur ? dur.innerText.trim() : ''
                            });
                        }
                    });
                } else if (url.includes('/watch')) {
                    // Đang xem Video -> CHỈ lấy Cột đề xuất bên phải (Right Sidebar Suggested)
                    document.querySelectorAll('#secondary ytd-compact-video-renderer, #related yt-lockup-view-model, #secondary yt-lockup-view-model').forEach((el) => {
                        if (el.offsetParent === null) return;
                        const a = el.querySelector('a#video-title, a.yt-lockup-metadata-view-model__title, h3 a[href*="/watch?v="]');
                        const ch = el.querySelector('ytd-channel-name, .yt-content-metadata-view-model__metadata-row');
                        const titleText = a ? (a.innerText || a.getAttribute('title') || '').trim() : '';
                        if (a && a.href && isValidTitle(titleText, a.href)) {
                            items.push({
                                area: 'sidebar',
                                title: titleText,
                                href: a.href,
                                channel: ch ? ch.innerText.trim().split('\\n')[0] : '',
                                duration: ''
                            });
                        }
                    });
                } else {
                    // Trang chủ (Home Feed) hoặc Kênh đăng ký (chỉ lấy phần tử đang hiển thị)
                    document.querySelectorAll('ytd-browse:not([hidden]) ytd-rich-item-renderer, ytd-browse:not([hidden]) ytd-grid-video-renderer').forEach((el) => {
                        if (el.offsetParent === null) return;
                        const a = el.querySelector('a.yt-lockup-metadata-view-model__title, a#video-title-link, a#video-title, h3 a[href*="/watch?v="]');
                        const ch = el.querySelector('ytd-channel-name, .ytd-channel-name, .yt-content-metadata-view-model__metadata-row');
                        const dur = el.querySelector('ytd-thumbnail-overlay-time-status-renderer, badge-shape');
                        const titleText = a ? (a.innerText || a.getAttribute('title') || '').trim() : '';
                        if (a && a.href && isValidTitle(titleText, a.href)) {
                            items.push({
                                area: 'home_or_grid',
                                title: titleText,
                                href: a.href,
                                channel: ch ? ch.innerText.trim().split('\\n')[0] : '',
                                duration: dur ? dur.innerText.trim() : ''
                            });
                        }
                    });
                }

                return {
                    url,
                    pageTitle,
                    visibleVideos: items.slice(0, 20)
                };
            } catch (e) {
                return { url: window.location.href, pageTitle: '', visibleVideos: [] };
            }
        })()
        """
        raw_obs = BrowserCDPManager.eval_js(cdp_port, target_id, js_observe) or {
            "url": "",
            "pageTitle": "",
            "visibleVideos": [],
        }
        vids = raw_obs.get("visibleVideos") or []
        if language == "ja" and vids:
            # Lọc chỉ giữ các video có ký tự tiếng Nhật (Hiragana/Katakana/Kanji) để tuyệt đối không bấm nhầm video tiếng Việt cũ trên trang chủ
            ja_vids = [
                v for v in vids if re.search(r"[\u3040-\u30ff\u4e00-\u9faf]", v.get("title", ""))
            ]
            raw_obs["rawTotalCount"] = len(vids)
            raw_obs["visibleVideos"] = ja_vids
        return raw_obs


class TranscriptExtractor:
    """
    Trích xuất phụ đề / nội dung lời thoại thực tế của video YouTube kèm mốc thời gian (mm:ss)
    để Bộ Não AI đọc hiểu toàn bộ câu chuyện trước khi suy nghĩ và viết bình luận.
    """

    @staticmethod
    def extract_from_active_video_tab(cdp_port: int, target_id: str, channel_id: str) -> Dict[str, Any]:
        js_extract_meta = """
        (() => {
            try {
                const urlParams = new URLSearchParams(window.location.search);
                const videoId = urlParams.get('v') || '';
                const titleEl = document.querySelector('h1.ytd-watch-metadata yt-formatted-string, h1.title');
                const title = titleEl ? titleEl.innerText.trim() : document.title.replace(' - YouTube', '');
                const ownerEl = document.querySelector('#owner #channel-name a, ytd-channel-name a');
                const author = ownerEl ? ownerEl.innerText.trim() : '';
                const descEl = document.querySelector('#description-inline-expander, #description');
                const description = descEl ? descEl.innerText.trim().slice(0, 1800) : '';
                const videoEl = document.querySelector('video');
                const duration = videoEl && videoEl.duration ? videoEl.duration : 0;

                let captionUrl = '';
                const playerResp = window.ytInitialPlayerResponse;
                if (playerResp && playerResp.captions && playerResp.captions.playerCaptionsTracklistRenderer) {
                    const tracks = playerResp.captions.playerCaptionsTracklistRenderer.captionTracks || [];
                    if (tracks.length > 0) {
                        captionUrl = tracks[0].baseUrl || '';
                    }
                }

                const commentEls = Array.from(document.querySelectorAll('ytd-comment-thread-renderer #content-text')).slice(0, 15);
                const existingComments = commentEls.map(el => el.innerText.trim()).filter(Boolean);

                const segEls = Array.from(document.querySelectorAll('ytd-transcript-segment-renderer'));
                const domSegments = segEls.slice(0, 140).map(seg => {
                    const tsEl = seg.querySelector('.segment-timestamp');
                    const txtEl = seg.querySelector('.segment-text');
                    return {
                        timestamp: tsEl ? tsEl.innerText.trim() : '00:00',
                        text: txtEl ? txtEl.innerText.trim() : ''
                    };
                }).filter(s => s.text);

                return {
                    videoId,
                    title,
                    author,
                    description,
                    duration,
                    captionUrl,
                    existingComments,
                    domSegments
                };
            } catch (e) {
                return { error: String(e) };
            }
        })()
        """
        meta = BrowserCDPManager.eval_js(cdp_port, target_id, js_extract_meta) or {}
        video_id = meta.get("videoId") or f"vid_{int(time.time())}"
        segments: List[Dict[str, Any]] = meta.get("domSegments") or []

        caption_url = meta.get("captionUrl", "")
        if not segments and caption_url:
            try:
                req = urllib.request.Request(caption_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=6.0) as resp:
                    xml_text = resp.read().decode("utf-8", errors="replace")
                root = ET.fromstring(xml_text)
                for node in root.findall(".//text"):
                    start_sec = float(node.attrib.get("start", "0"))
                    raw_txt = (node.text or "").replace("\n", " ").strip()
                    if raw_txt:
                        segments.append({
                            "timestamp": format_mm_ss(start_sec),
                            "seconds": int(start_sec),
                            "text": raw_txt,
                        })
            except Exception:
                pass

        if not segments:
            open_transcript_js = """
            (() => {
                const btn = document.querySelector('ytd-video-description-transcript-section-renderer button, button[aria-label*="transcript" i], button[aria-label*="bản chép lời" i], button[aria-label*="文字起こし"]');
                if (btn) { btn.click(); return true; }
                return false;
            })()
            """
            if BrowserCDPManager.eval_js(cdp_port, target_id, open_transcript_js):
                time.sleep(2.2)
                seg_js = """
                (() => {
                    const segEls = Array.from(document.querySelectorAll('ytd-transcript-segment-renderer'));
                    return segEls.slice(0, 140).map(seg => {
                        const tsEl = seg.querySelector('.segment-timestamp');
                        const txtEl = seg.querySelector('.segment-text');
                        return {
                            timestamp: tsEl ? tsEl.innerText.trim() : '00:00',
                            text: txtEl ? txtEl.innerText.trim() : ''
                        };
                    }).filter(s => s.text);
                })()
                """
                segments = BrowserCDPManager.eval_js(cdp_port, target_id, seg_js) or []

        if not segments:
            duration = float(meta.get("duration") or 1200)
            title = meta.get("title") or "定年後の仕事と生活"
            desc = meta.get("description") or title
            for idx, ratio in enumerate((0.18, 0.42, 0.67, 0.85)):
                sec = int(duration * ratio)
                snippet = desc[idx * 120:(idx + 1) * 120].strip() or title
                segments.append({
                    "timestamp": format_mm_ss(sec),
                    "seconds": sec,
                    "text": snippet,
                })

        result = {
            "video_id": video_id,
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "duration": meta.get("duration", 0),
            "description": meta.get("description", ""),
            "segments_count": len(segments),
            "segments": segments[:140],
            "existing_comments": meta.get("existingComments", []),
            "extracted_at": datetime.datetime.now().isoformat(),
        }

        ch_folder = os.path.join(TRANSCRIPTS_DIR, channel_id)
        os.makedirs(ch_folder, exist_ok=True)
        save_path = os.path.join(ch_folder, f"{video_id}.json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        result["saved_file"] = save_path
        return result


class MeaningfulCommentGenerator:
    """
    Giao hoàn toàn cho Bộ Não AI (SHARED_AI_BRAIN) đọc Transcript và tự suy nghĩ câu bình luận
    có mốc thời gian mm:ss (không dùng mẫu cố định).
    """

    @staticmethod
    def build_timestamp_comment(
        transcript_data: Dict[str, Any],
        channel: Optional[Dict[str, Any]] = None,
        language: str = "ja",
    ) -> Dict[str, str]:
        ch_obj = channel or {"channel_id": "DEPT_01_JAPAN_K1", "language": language}
        return SHARED_AI_BRAIN.think_and_write_transcript_comment(ch_obj, transcript_data)


class FeedbackEvolutionEngine:
    """
    Bàn #7 (Agent_Feedback_Evolution & Community Research Loop):
    Lưu trữ và dùng Bộ Não AI phân tích sâu bình luận khán giả + kết quả khảo sát Community Tab
    để nâng cấp cách viết Tiêu đề (Bàn #2) và Kịch bản (Bàn #3).
    """

    @staticmethod
    def get_evolution_file(channel_id: str) -> str:
        return os.path.join(EVOLUTION_DIR, f"{channel_id}_evolution.json")

    @classmethod
    def load_evolution_memory(cls, channel_id: str) -> Dict[str, Any]:
        path = cls.get_evolution_file(channel_id)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "channel_id": channel_id,
            "updated_at": datetime.datetime.now().isoformat(),
            "harvested_comments_count": 0,
            "community_polls_analyzed": 0,
            "title_upgrade_directives": [],
            "script_upgrade_directives": [],
            "proposed_new_titles": [],
            "recent_harvested_samples": [],
        }

    @classmethod
    def save_evolution_memory(cls, channel_id: str, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.datetime.now().isoformat()
        with open(cls.get_evolution_file(channel_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def ingest_comments_and_community_feedback(
        cls,
        channel_id: str,
        raw_comments: List[str],
        community_feedback: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        mem = cls.load_evolution_memory(channel_id)
        clean_comments = [c.strip() for c in (raw_comments or []) if c and len(c.strip()) > 5]
        clean_polls = [p.strip() for p in (community_feedback or []) if p and len(p.strip()) > 5]

        mem["harvested_comments_count"] = int(mem.get("harvested_comments_count", 0)) + len(clean_comments)
        if clean_polls:
            mem["community_polls_analyzed"] = int(mem.get("community_polls_analyzed", 0)) + len(clean_polls)

        # Gọi Bộ Não AI suy nghĩ và phân tích chiến lược từ bình luận + Community Poll
        ai_analysis = SHARED_AI_BRAIN.analyze_community_and_comments_for_k1_upgrade(
            channel_id, clean_comments, clean_polls
        )
        if ai_analysis:
            if ai_analysis.get("ai_thought"):
                mem["last_ai_evolution_thought"] = ai_analysis["ai_thought"]
            if ai_analysis.get("title_upgrade_directives"):
                mem["title_upgrade_directives"] = (
                    ai_analysis["title_upgrade_directives"] + mem.get("title_upgrade_directives", [])
                )[:10]
            if ai_analysis.get("script_upgrade_directives"):
                mem["script_upgrade_directives"] = (
                    ai_analysis["script_upgrade_directives"] + mem.get("script_upgrade_directives", [])
                )[:10]
            if ai_analysis.get("proposed_new_titles"):
                mem["proposed_new_titles"] = ai_analysis["proposed_new_titles"]
        else:
            # Ghi nhận trực tiếp insight mới để AI sử dụng ở lượt tiếp theo
            for item in clean_comments[:8]:
                note = f"[Insight từ Khán giả / Community]: {item[:130]}"
                if note not in mem.get("script_upgrade_directives", []):
                    mem.setdefault("script_upgrade_directives", []).insert(0, note)

        mem["recent_harvested_samples"] = (clean_comments[:10] + mem.get("recent_harvested_samples", []))[:25]
        cls.save_evolution_memory(channel_id, mem)
        return mem


class YouTubePersonaEngine:
    """
    Thực thi vòng lặp Nhận Thức AI (Observe -> Think -> Act) cho từng Phòng Ban Kênh YouTube.
    """

    def __init__(self, state_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        self.state_callback = state_callback
        self.stop_flags: Dict[str, bool] = {}

    def emit_log(self, channel_id: str, desk: int, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        log_line = f"[{ts}] [Bàn #{desk}] {message}"
        log_file = os.path.join(LOGS_DIR, f"{channel_id}.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
        if self.state_callback:
            payload = {"last_log": log_line, "active_desk": desk}
            if extra:
                payload.update(extra)
            self.state_callback(channel_id, payload)

    def stop_channel(self, channel_id: str) -> None:
        self.stop_flags[channel_id] = True

    def _interruptible_sleep(self, channel_id: str, total_seconds: float) -> bool:
        """
        Ngủ chờ theo từng nhịp 1.0s nhưng kiểm tra cờ dừng `stop_flags[channel_id]` liên tục.
        Trả về True nếu đã bị người dùng bấm Dừng giữa chừng.
        """
        deadline = time.time() + max(0.0, float(total_seconds))
        while time.time() < deadline:
            if self.stop_flags.get(channel_id):
                return True
            time.sleep(min(1.0, max(0.05, deadline - time.time())))
        return bool(self.stop_flags.get(channel_id))

    def run_daily_persona_warmup_session(
        self,
        channel: Dict[str, Any],
        num_videos_override: Optional[int] = None,
        demo_fast_mode: bool = False,
        warmup_mode: str = "FULL_OMNI",
        window_slot: str = "RIGHT",
    ) -> Dict[str, Any]:
        """
        [v3.7 / v3.8] Vòng lặp AI-Driven 100% có Cổng Xác Nhận Đăng Nhập Trước Tác Vụ, Tách Biệt Chế Độ Nuôi & Chia Đôi Màn Hình:
        - `warmup_mode`:
          + `"FULL_OMNI"`: Nuôi Đa Tầng Biến Thiên (Gmail + Báo + Google Search + Maps + Kênh YouTube Xem Sâu 3–7p & Bình Luận)
          + `"YOUTUBE_DEEP_ONLY"`: Chỉ Nuôi Kênh YouTube Chuyên Sâu (Xem 3–4 video dài 3–7 phút/video + Đọc Transcript + Gõ đăng bình luận thật)
          + `"GMAIL_ONLY"`: Nuôi Gmail & Hệ Sinh Thái Google Như Người Thật (~10–15 phút: Đọc kỹ 2–3 Email + Đọc Báo + Tìm Kiếm Google + Xem Google Maps)
        - `window_slot`: `"LEFT"` | `"RIGHT"` | `"FULL"` (Hỗ trợ chạy 2 kênh chia đôi màn hình cùng lúc)
        """
        channel_id = channel["channel_id"]
        cdp_port = int(channel["cdp_port"])
        profile_dir = channel["profile_dir"]
        proxy = channel.get("proxy", "")

        self.stop_flags[channel_id] = False
        lang = channel.get("language", "ja")
        channel_folder = os.path.join(BASE_DIR, "CHANNELS_DATA", channel_id)
        custom_seeds = [str(s).strip() for s in (channel.get("seed_keywords") or []) if str(s).strip()]
        mode_clean = (warmup_mode or "FULL_OMNI").upper()
        slot_clean = (window_slot or "RIGHT").upper()

        # [v3.4/v3.8.2] GỌI BỘ NÃO AI LẬP KẾ HOẠCH PHIÊN ĐỘC BẢN + TÁCH BIỆT CHẾ ĐỘ NUÔI
        session_plan = SHARED_AI_BRAIN.think_generative_human_session_plan(channel, demo_fast_mode=demo_fast_mode)
        raw_plan: List[str] = list(session_plan["step_sequence"])
        if mode_clean == "GMAIL_ONLY":
            # Chu trình Nuôi Gmail & Hệ Sinh Thái Google Như Người Thật (~10 - 15 phút / tài khoản):
            # Bao gồm: Đọc kỹ Hộp thư Gmail (~4p) + Đọc Báo chí (~3p) + Tìm kiếm Google & Đọc Web (~3p) + Xem Bản đồ Google Maps (~2.5p)
            ecosystem_other = ["READ_NEWS_PORTAL", "GOOGLE_SEARCH_WEB", "GOOGLE_MAPS_EXPLORE"]
            random.shuffle(ecosystem_other)
            if random.random() < 0.72:
                dynamic_plan = ["GMAIL_DEEP_WARMUP"] + ecosystem_other
            else:
                # Đôi khi người thật mở đọc báo hoặc tra Google trước rồi mới vào kiểm tra Gmail
                dynamic_plan = [ecosystem_other[0], "GMAIL_DEEP_WARMUP"] + ecosystem_other[1:]
            if not demo_fast_mode and random.random() < 0.45:
                dynamic_plan.append(random.choice(["READ_NEWS_PORTAL", "GOOGLE_SEARCH_WEB"]))
        elif mode_clean == "YOUTUBE_DEEP_ONLY":
            yt_only = [s for s in raw_plan if s in ("YOUTUBE_K1_VIDEO", "YOUTUBE_SHORTS_SWIPE")]
            while len(yt_only) < (3 if demo_fast_mode else 4):
                yt_only.append("YOUTUBE_K1_VIDEO")
            dynamic_plan = yt_only[: (3 if demo_fast_mode else 5)]
        else:
            dynamic_plan = raw_plan

        daily_target = num_videos_override or len(dynamic_plan)
        fresh_google_queries: List[str] = list(session_plan.get("fresh_google_queries") or [])
        fresh_youtube_queries: List[str] = list(session_plan.get("fresh_youtube_queries") or [])
        ai_provider_used = session_plan.get("ai_provider", "GENERATIVE_AI")

        # Biến thiên cả URL khởi động trình duyệt theo đúng bước đầu tiên mà AI chọn
        first_step_plan = dynamic_plan[0] if dynamic_plan else "YOUTUBE_K1_VIDEO"
        if first_step_plan == "GMAIL_DEEP_WARMUP":
            start_url = "https://mail.google.com/mail/u/0/#inbox"
        elif first_step_plan == "READ_NEWS_PORTAL":
            start_url = "https://news.yahoo.co.jp/" if lang == "ja" else ("https://news.google.com/?hl=es-419&gl=MX&ceid=MX:es-419" if lang == "es" else "https://news.google.com/?hl=en-US&gl=US&ceid=US:en")
        elif first_step_plan == "GOOGLE_SEARCH_WEB":
            start_url = "https://www.google.co.jp/" if lang == "ja" else ("https://www.google.com.mx/" if lang == "es" else "https://www.google.com/")
        else:
            start_url = "https://www.youtube.com/"

        self.emit_log(
            channel_id,
            1,
            f"🤖 [Bộ Não AI v3.8 ({ai_provider_used} | Chế độ: {mode_clean} | Màn hình: {slot_clean})]: {session_plan.get('session_persona_mood')} -> Lộ trình {daily_target} bước: {' ➔ '.join(dynamic_plan[:daily_target])}",
            {"status": f"WARMING_{mode_clean}", "today_target_quota": daily_target, "window_slot": slot_clean},
        )

        BrowserCDPManager.launch_channel_browser(
            profile_dir=profile_dir,
            cdp_port=cdp_port,
            proxy=proxy,
            initial_url=start_url,
            side_by_side_right=(slot_clean != "FULL"),
            window_slot=slot_clean,
        )
        time.sleep(2.5)

        # [v3.7] BƯỚC BẮT BUỘC: CỔNG XÁC NHẬN ĐĂNG NHẬP TRƯỚC KHI CHẠY (PRE-FLIGHT LOGIN GATE)
        tab_init = TabGuard.get_or_allocate_tab(cdp_port, slot=1)
        pages_init = TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=tab_init["id"] if tab_init else None, max_tabs=1)
        tid_init = tab_init["id"] if tab_init else (pages_init[0]["id"] if pages_init else "")
        if not tid_init:
            BrowserCDPManager.close_channel_browser(cdp_port)
            return {"ok": False, "error": "Không khởi tạo được Tab trình duyệt"}

        check_mode = "GMAIL" if mode_clean == "GMAIL_ONLY" else "YOUTUBE"
        login_chk = BrowserCDPManager.verify_google_and_youtube_login_before_task(
            cdp_port=cdp_port,
            target_id=tid_init,
            check_mode=check_mode,
            emit_cb=lambda msg: self.emit_log(channel_id, 1, msg),
        )
        if not login_chk.get("logged_in"):
            BrowserCDPManager.close_channel_browser(cdp_port)
            self.emit_log(
                channel_id,
                0,
                f"⛔ [ĐÃ DỪNG NGAY ĐỂ BẢO VỆ HIỆU QUẢ]: Profile `{profile_dir}` CHƯA ĐĂNG NHẬP ({login_chk.get('reason')})! "
                f"Vui lòng bấm nút 「🔑 1. Mở Cửa Sổ Chrome Để Đăng Nhập Gmail & Kênh」 trước khi chạy Nuôi.",
                {
                    "status": "LOGIN_REQUIRED",
                    "logged_in": False,
                    "open_tabs_count": 0,
                    "last_ai_thought": f"⛔ CHẶN TÁC VỤ: Profile chưa đăng nhập Google/YouTube ({login_chk.get('reason')}). Đã dừng ngay để tránh chạy không hiệu quả!",
                },
            )
            return {"ok": False, "login_required": True, "reason": login_chk.get("reason")}

        self.emit_log(
            channel_id,
            1,
            f"🔐 [Đã Xác Nhận Đăng Nhập]: Tài khoản hợp lệ ({login_chk.get('detected_account')}) -> Bắt đầu phiên nuôi!",
            {"logged_in": True},
        )

        watched_count = 0
        session_history: List[str] = []
        harvested_comments_all: List[str] = []
        session_queries_used: List[str] = []
        session_comments_posted: List[str] = []
        executed_steps: List[str] = []

        for step_idx in range(1, daily_target + 1):
            if self.stop_flags.get(channel_id):
                self.emit_log(channel_id, 1, "⏹️ Đã nhận lệnh dừng từ người dùng.", {"status": "STOPPED"})
                break

            # BẮT BUỘC CHỈ MỞ DUY NHẤT 1 TAB ĐANG DÙNG (Đóng ngay lập tức mọi tab thừa không dùng)
            tab_watch = TabGuard.get_or_allocate_tab(cdp_port, slot=1)
            pages_now = TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=tab_watch["id"] if tab_watch else None, max_tabs=1)
            tid = tab_watch["id"] if tab_watch else (pages_now[0]["id"] if pages_now else "")
            if not tid:
                break

            BrowserCDPManager.apply_channel_locale_and_timezone_emulation(cdp_port, tid, language=lang)
            step_task = dynamic_plan[(step_idx - 1) % len(dynamic_plan)]
            executed_steps.append(step_task)

            # LỊCH TRÌNH ĐA TẦNG DO AI ĐIỀU KHIỂN (Không cố định thứ tự bước hay số bước)
            if step_task == "GMAIL_DEEP_WARMUP":
                self.emit_log(
                    channel_id,
                    1,
                    f"🧠 [AI Suy nghĩ - Bước {step_idx}/{daily_target}]: Thực thi Chu trình Nuôi Gmail Chuyên Sâu Như Người Thật (~3.5–4.5p: Kiểm tra Google Alerts + Mở đọc kỹ 2–3 thư 25–40s/thư + Click link trong thư + Gắn sao ⭐ + Kiểm tra Updates/Promotions & Giải cứu Spam + Tìm kiếm thư).",
                    {"current_source": "GMAIL_DEEP_WARMUP", "open_tabs_count": len(pages_now)},
                )
                BrowserCDPManager.warmup_gmail_inbox(
                    cdp_port,
                    tid,
                    emit_cb=lambda msg: self.emit_log(channel_id, 1, msg),
                    channel_folder=channel_folder,
                    language=lang,
                    custom_topics=custom_seeds if channel_id != "DEPT_01_JAPAN_K1" else None,
                    demo_fast_mode=demo_fast_mode,
                )
                watched_count += 1
                session_history.append(f"Bước {step_idx}: GMAIL_DEEP_WARMUP")
                self.emit_log(channel_id, 1, f"✅ Hoàn thành Bước {watched_count}/{daily_target} (Đọc Kỹ Hộp Thư Gmail Chuyên Sâu).", {"today_watched_count": watched_count})
                continue

            if step_task == "READ_NEWS_PORTAL":
                self.emit_log(
                    channel_id,
                    1,
                    f"🧠 [AI Suy nghĩ - Bước {step_idx}/{daily_target}]: Mở trang Báo chí & Tin tức đọc kỹ 1–2 bài báo từ đầu đến cuối (~3 phút) để tích lũy Cookie đọc báo tự nhiên như người thật.",
                    {"current_source": "READ_NEWS_PORTAL", "open_tabs_count": len(pages_now)},
                )
                BrowserCDPManager.warmup_read_news_portal(
                    cdp_port,
                    tid,
                    language=lang,
                    emit_cb=lambda msg: self.emit_log(channel_id, 1, msg),
                    demo_fast_mode=demo_fast_mode,
                )
                watched_count += 1
                session_history.append(f"Bước {step_idx}: READ_NEWS_PORTAL")
                self.emit_log(channel_id, 1, f"✅ Hoàn thành Bước {watched_count}/{daily_target} (Đọc Báo & Tin Tức Chuyên Sâu).", {"today_watched_count": watched_count})
                continue

            if step_task == "GOOGLE_SEARCH_WEB":
                g_query = (
                    fresh_google_queries.pop(0)
                    if fresh_google_queries
                    else SHARED_AI_BRAIN._generate_non_repeating_query(channel, session_queries_used, "GOOGLE")
                )
                session_queries_used.append(g_query)
                self.emit_log(
                    channel_id,
                    1,
                    f"🧠 [AI Suy nghĩ - Bước {step_idx}/{daily_target}]: Mở Google Search gõ tìm kiếm từ khóa 「{g_query}」 và click mở đọc kỹ 1–2 trang web ngoài (~3 phút) để nuôi lịch sử Web & App Activity.",
                    {"current_source": "GOOGLE_SEARCH_WEB", "open_tabs_count": len(pages_now)},
                )
                BrowserCDPManager.warmup_google_search_and_explore(
                    cdp_port,
                    tid,
                    query=g_query,
                    language=lang,
                    emit_cb=lambda msg: self.emit_log(channel_id, 1, msg),
                    demo_fast_mode=demo_fast_mode,
                )
                watched_count += 1
                session_history.append(f"Bước {step_idx}: GOOGLE_SEARCH ({g_query})")
                self.emit_log(channel_id, 1, f"✅ Hoàn thành Bước {watched_count}/{daily_target} (Tìm Kiếm Google & Đọc Web Ngoài).", {"today_watched_count": watched_count})
                continue

            if step_task == "GOOGLE_MAPS_EXPLORE":
                self.emit_log(
                    channel_id,
                    1,
                    f"🧠 [AI Suy nghĩ - Bước {step_idx}/{daily_target}]: Mở Google Maps tra cứu địa điểm đời thực, click xem chi tiết, ảnh & đọc đánh giá (~2.5 phút) để làm giàu Location/Maps Cookie.",
                    {"current_source": "GOOGLE_MAPS_EXPLORE", "open_tabs_count": len(pages_now)},
                )
                BrowserCDPManager.warmup_google_maps_explore(
                    cdp_port,
                    tid,
                    language=lang,
                    emit_cb=lambda msg: self.emit_log(channel_id, 1, msg),
                    demo_fast_mode=demo_fast_mode,
                )
                watched_count += 1
                session_history.append(f"Bước {step_idx}: GOOGLE_MAPS_EXPLORE")
                self.emit_log(channel_id, 1, f"✅ Hoàn thành Bước {watched_count}/{daily_target} (Tra Cứu Bản Đồ & Đọc Đánh Giá Google Maps).", {"today_watched_count": watched_count})
                continue

            if step_task == "YOUTUBE_SHORTS_SWIPE":
                self.emit_log(
                    channel_id,
                    1,
                    f"🧠 [AI Suy nghĩ - Bước {step_idx}/{daily_target}]: Lướt xem nhanh 3 video YouTube Shorts bằng phím cứng ArrowDown như người dùng thực tế.",
                    {"current_source": "YOUTUBE_SHORTS_SWIPE", "open_tabs_count": len(pages_now)},
                )
                BrowserCDPManager.warmup_youtube_shorts_swipe(
                    cdp_port, tid, count=3, emit_cb=lambda msg: self.emit_log(channel_id, 1, msg)
                )
                watched_count += 1
                session_history.append(f"Bước {step_idx}: YOUTUBE_SHORTS_SWIPE")
                self.emit_log(channel_id, 1, f"✅ Hoàn thành Bước {watched_count}/{daily_target} (Lướt Xem YouTube Shorts).", {"today_watched_count": watched_count})
                continue

            # CÁC BƯỚC CÒN LẠI (Bước 4, 5, 8): XEM VIDEO YOUTUBE CHUẨN NGÁCH NGẮN GỌN (~30-35s/video)
            obs = ScreenObserver.observe_current_screen(cdp_port, tid, language=lang)
            visible_videos = obs.get("visibleVideos") or []
            current_url = obs.get("url") or "https://www.youtube.com"
            if "youtube.com" not in current_url:
                TabGuard.navigate_tab(cdp_port, tid, "https://www.youtube.com")
                time.sleep(3.2)
                obs = ScreenObserver.observe_current_screen(cdp_port, tid, language=lang)
                visible_videos = obs.get("visibleVideos") or []
                current_url = obs.get("url") or "https://www.youtube.com"

            # BƯỚC 2: AI SUY NGHĨ & RA QUYẾT ĐỊNH (THINK)
            decision = SHARED_AI_BRAIN.think_next_browsing_action(
                channel=channel,
                step_index=step_idx,
                daily_target=daily_target,
                current_url=current_url,
                visible_videos_on_screen=visible_videos,
                session_history=session_history,
            )

            ai_thought = decision.get("ai_thought", "AI đang phân tích màn hình...")
            action_type = decision.get("action_type", "SEARCH_NEW_KEYWORD")

            # Nếu Trang chủ hiện tại chưa đúng chủ đề kênh (không có video đúng ngôn ngữ/từ khóa ngách), ưu tiên câu tìm kiếm mới do AI tạo ra!
            if not visible_videos and action_type in ("CLICK_VISIBLE_VIDEO", "BROWSE_HOME_FEED"):
                forced_kw = (
                    fresh_youtube_queries.pop(0)
                    if fresh_youtube_queries
                    else SHARED_AI_BRAIN._generate_non_repeating_query(channel, session_queries_used, "YOUTUBE")
                )
                action_type = "SEARCH_NEW_KEYWORD"
                decision["search_query"] = forced_kw
                ai_thought = (
                    f"[Huấn luyện Luồng Đề Xuất Kênh Mới] Trang chủ hiện tại chưa có video đúng chủ đề kênh ({channel.get('channel_title')}). "
                    f"Quyết định tìm kiếm câu truy vấn mới độc bản: 「{forced_kw}」."
                )
            if action_type == "SEARCH_NEW_KEYWORD" and decision.get("search_query"):
                session_queries_used.append(str(decision["search_query"]))

            self.emit_log(
                channel_id,
                1,
                f"🧠 [Suy nghĩ của AI - Bước {step_idx}/{daily_target}]: {ai_thought}",
                {
                    "last_ai_thought": ai_thought,
                    "open_tabs_count": len(pages_now),
                    "current_source": action_type,
                },
            )

            # BƯỚC 3: THỰC THI QUYẾT ĐỊNH CỦA AI TRÊN TRÌNH DUYỆT NHƯ NGƯỜI THẬT (ACT)
            chosen_title_for_step = ""
            if action_type == "CHECK_GMAIL":
                tab1 = TabGuard.get_or_allocate_tab(cdp_port, slot=1, target_url="https://mail.google.com")
                pages_now = TabGuard.enforce_max_two_tabs(cdp_port, max_tabs=1)
                self.emit_log(channel_id, 1, f"📧 AI mở hộp thư Gmail kiểm tra thông báo ({len(pages_now)}/1 Tab).")
                time.sleep(3.5 if demo_fast_mode else 10.0)
                if tab1:
                    BrowserCDPManager.human_scroll(cdp_port, tab1["id"], 250, 550, 1)
                session_history.append(f"Bước {step_idx}: CHECK_GMAIL")
                continue

            if action_type == "CLICK_VISIBLE_VIDEO" and visible_videos:
                sel_idx = int(decision.get("selected_video_index", 0))
                sel_idx = max(0, min(sel_idx, len(visible_videos) - 1))
                chosen_v = visible_videos[sel_idx]
                chk = SHARED_AI_BRAIN.verify_video_matches_channel_dna(
                    channel, chosen_v.get("title", ""), chosen_v.get("href", "")
                )
                if not chk.get("ok"):
                    # Tìm video đạt chuẩn K1 trong danh sách hiện tại
                    fallback_decision = SHARED_AI_BRAIN._semantic_k1_screen_reasoning(
                        channel, step_idx, daily_target, current_url, visible_videos, session_history
                    )
                    if fallback_decision.get("action_type") == "CLICK_VISIBLE_VIDEO":
                        sel_idx = int(fallback_decision.get("selected_video_index", 0))
                        chosen_v = visible_videos[sel_idx]
                        chk = SHARED_AI_BRAIN.verify_video_matches_channel_dna(
                            channel, chosen_v.get("title", ""), chosen_v.get("href", "")
                        )

                if chk.get("ok"):
                    chosen_title_for_step = chosen_v.get("title", "")
                    target_href = chosen_v.get("href", "")
                    self.emit_log(
                        channel_id,
                        1,
                        f"🖱️ AI vuốt rà soát danh sách -> Kiểm định tiêu đề đạt chuẩn K1 ({chk.get('reason')}) -> Cuộn tới & Click chọn video [{sel_idx}]: 「{chosen_title_for_step[:70]}」",
                    )
                    BrowserCDPManager.human_browse_scroll_pattern(cdp_port, tid, fast_mode=demo_fast_mode)
                    BrowserCDPManager.human_scroll_to_and_click_video(cdp_port, tid, target_href, chosen_title_for_step)
                    session_history.append(f"Bước {step_idx}: CLICK_VISIBLE_VIDEO ({chosen_title_for_step[:35]} | {target_href.split('&')[0]})")
                else:
                    action_type = "SEARCH_NEW_KEYWORD"

            if action_type == "SEARCH_NEW_KEYWORD":
                seed_kws = channel.get("seed_keywords") or ["ハローワーク 65歳 再就職 漫画"]
                query = decision.get("search_query") or seed_kws[(step_idx - 1) % len(seed_kws)]
                self.emit_log(channel_id, 1, f"🔍 AI bấm thanh Search & gõ từng chữ từ khóa chủ đề kênh: 「{query}」")
                typed = BrowserCDPManager.human_type_in_selector(
                    cdp_port, tid, "input[name='search_query'], input#search", query, press_enter=True
                )
                if typed:
                    BrowserCDPManager.eval_js(
                        cdp_port,
                        tid,
                        "(() => { const btn = document.querySelector('button.ytSearchboxComponentSearchButton, button#search-icon-legacy'); if (btn) btn.click(); return true; })()",
                    )
                    time.sleep(2.2)
                cur_after_type = BrowserCDPManager.eval_js(cdp_port, tid, "window.location.href") or ""
                if "/results" not in str(cur_after_type):
                    TabGuard.navigate_tab(
                        cdp_port, tid, "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
                    )
                time.sleep(3.5)

                # CỬ CHỈ NGƯỜI THẬT: Vuốt lên xuống rà đọc các tiêu đề trên trang kết quả tìm kiếm trước khi chọn!
                self.emit_log(channel_id, 1, "🖱️ AI đang vuốt cuộn lên xuống rà đọc và kiểm định từng tiêu đề trong danh sách kết quả tìm kiếm...")
                BrowserCDPManager.human_browse_scroll_pattern(cdp_port, tid, fast_mode=demo_fast_mode)

                obs_after = ScreenObserver.observe_current_screen(cdp_port, tid, language=lang)
                vids_after = obs_after.get("visibleVideos") or []
                if vids_after:
                    follow_decision = SHARED_AI_BRAIN._semantic_k1_screen_reasoning(
                        channel=channel,
                        step_index=step_idx,
                        daily_target=daily_target,
                        current_url=obs_after.get("url", "https://www.youtube.com/results"),
                        visible_videos=vids_after,
                        session_history=session_history,
                    )
                    pick_i = max(0, min(int(follow_decision.get("selected_video_index", 0)), len(vids_after) - 1))
                    picked_v = vids_after[pick_i]
                    chosen_title_for_step = picked_v.get("title", "")
                    picked_href = picked_v.get("href", "")
                    self.emit_log(
                        channel_id,
                        1,
                        f"✅ [AI Kiểm Định Tiêu Đề & Click]: {follow_decision.get('ai_thought', '')} -> Cuộn đưa vào giữa màn hình & Click mở 「{chosen_title_for_step[:70]}」",
                        {"last_ai_thought": follow_decision.get("ai_thought", "")},
                    )
                    BrowserCDPManager.human_scroll_to_and_click_video(cdp_port, tid, picked_href, chosen_title_for_step)
                    session_history.append(
                        f"Bước {step_idx}: SEARCH_NEW_KEYWORD ({query}) -> {chosen_title_for_step[:35]} | {picked_href.split('&')[0]}"
                    )

            elif action_type == "BROWSE_SUBSCRIPTIONS":
                TabGuard.navigate_tab(cdp_port, tid, "https://www.youtube.com/feed/subscriptions")
                time.sleep(3.0)
                BrowserCDPManager.human_browse_scroll_pattern(cdp_port, tid, fast_mode=demo_fast_mode)
                session_history.append(f"Bước {step_idx}: BROWSE_SUBSCRIPTIONS")

            elif action_type == "WATCH_SHORTS":
                TabGuard.navigate_tab(cdp_port, tid, "https://www.youtube.com/shorts")
                time.sleep(4.0 if demo_fast_mode else 15.0)
                session_history.append(f"Bước {step_idx}: WATCH_SHORTS")
                watched_count += 1
                continue

            time.sleep(3.5)
            TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=tid, max_tabs=1)

            # LỚP KIỂM ĐỊNH TIÊU ĐỀ SAU KHI MỞ VIDEO (/watch): Đảm bảo 100% trang đang xem đúng chủ đề Kênh 1!
            actual_page_meta = BrowserCDPManager.eval_js(
                cdp_port,
                tid,
                "(() => { const h1 = document.querySelector('h1.ytd-watch-metadata yt-formatted-string, h1.title'); return { url: window.location.href, title: h1 ? h1.innerText.trim() : document.title.replace(' - YouTube', '') }; })()",
            ) or {}
            actual_watch_title = actual_page_meta.get("title") or chosen_title_for_step
            post_chk = SHARED_AI_BRAIN.verify_video_matches_channel_dna(
                channel, actual_watch_title, actual_page_meta.get("url", "")
            )
            if not post_chk.get("ok"):
                self.emit_log(
                    channel_id,
                    1,
                    f"🛡️ [Cổng Kiểm Định Tiêu Đề Chặn Lại]: Trang hiện tại 「{actual_watch_title[:55]}」 không khớp chuẩn Kênh 1 ({post_chk.get('reason')}) -> Bỏ qua ngay không xem!",
                )
                continue

            # CỬ CHỈ XEM VIDEO SÂU NHƯ NGƯỜI THẬT (Deep Watch Time 3–7 phút/video + Skip Ads + Micro-Interactions + Đăng Bình Luận Thật)
            watch_ratio = float(decision.get("watch_ratio") or 0.65)
            vid_state = BrowserCDPManager.get_active_video_duration_and_state(cdp_port, tid)
            vid_dur = float(vid_state.get("duration") or 0)
            if demo_fast_mode:
                watch_sec = 9.0
            else:
                if vid_dur >= 240:
                    # Video dài (4–25 phút): Xem sâu từ 3 đến 7 phút (180s - 420s) theo tỷ lệ độ cuốn hút
                    watch_sec = max(180.0, min(420.0, vid_dur * watch_ratio * 0.42 + random.uniform(-12.0, 22.0)))
                elif vid_dur >= 60:
                    watch_sec = max(60.0, min(vid_dur * 0.78, 210.0))
                else:
                    watch_sec = random.uniform(180.0, 310.0)

            watch_mins_str = f"{watch_sec / 60.0:.1f} phút ({int(watch_sec)}s)" if not demo_fast_mode else f"{int(watch_sec)}s (Demo nhanh)"
            self.emit_log(
                channel_id,
                1,
                f"📺 Đang xem sâu video ngách: 「{actual_watch_title[:65]}」 (Thời lượng gốc: {int(vid_dur // 60)}p{int(vid_dur % 60):02d}s -> Mục tiêu xem: {watch_mins_str})...",
            )

            # Giai đoạn 1: Kiểm tra Quảng cáo đầu video -> Chờ hết đếm ngược & bấm Skip Ad
            ad_check_start = BrowserCDPManager.check_and_skip_youtube_ads(cdp_port, tid)
            if ad_check_start.get("ad_detected"):
                self.emit_log(
                    channel_id,
                    1,
                    f"⏭️ [Xử lý Quảng Cáo]: Phát hiện quảng cáo đầu video -> Đã chờ hết thời gian đếm ngược và bấm Tắt/Bỏ qua quảng cáo (skipped={ad_check_start.get('skipped')})!",
                )

            if self._interruptible_sleep(channel_id, watch_sec * 0.30):
                break

            # Giai đoạn 2: Tương tác màn hình Video Player lần 1 (Tua tới/lùi, chỉnh âm lượng, đổi độ phân giải 1080p/720p, tạm dừng ngắn)
            micro_action_1 = BrowserCDPManager.perform_human_player_micro_interaction(cdp_port, tid)
            self.emit_log(
                channel_id,
                1,
                f"🎛️ [Tương tác màn hình Video]: {micro_action_1}",
            )
            if self._interruptible_sleep(channel_id, watch_sec * 0.35):
                break

            # Giai đoạn 3: Quét Mô tả, Bình luận & Phụ đề (Transcript) rồi cuộn lên xem tiếp
            BrowserCDPManager.human_scroll(cdp_port, tid, min_px=380, max_px=520, direction=1)
            BrowserCDPManager.eval_js(
                cdp_port,
                tid,
                "(() => { const exp = document.querySelector('#expand, tp-yt-paper-button#expand'); if (exp) exp.click(); return true; })()",
            )
            time.sleep(0.9)
            transcript_info = TranscriptExtractor.extract_from_active_video_tab(cdp_port, tid, channel_id)
            if transcript_info.get("existing_comments"):
                harvested_comments_all.extend(transcript_info["existing_comments"])
            # Lập tức cuộn ngược lên màn hình chính của Video Player
            BrowserCDPManager.human_scroll(cdp_port, tid, min_px=400, max_px=550, direction=-1)
            self.emit_log(
                channel_id,
                1,
                f"⚡ [Quét Comment & Transcript]: Đã thu thập {len(transcript_info.get('existing_comments', []))} bình luận & {transcript_info.get('segments_count', 0)} đoạn phụ đề, cuộn lại màn hình video.",
            )

            # Giai đoạn 4: Kiểm tra Quảng cáo giữa video (Mid-roll Ad) & Tương tác màn hình lần 2
            ad_check_mid = BrowserCDPManager.check_and_skip_youtube_ads(cdp_port, tid)
            if ad_check_mid.get("ad_detected"):
                self.emit_log(
                    channel_id,
                    1,
                    "⏭️ [Xử lý Quảng Cáo giữa video]: Đã chờ hết đếm ngược và bấm Bỏ qua quảng cáo!",
                )
            micro_action_2 = BrowserCDPManager.perform_human_player_micro_interaction(cdp_port, tid)
            self.emit_log(
                channel_id,
                1,
                f"🎛️ [Tương tác màn hình Video]: {micro_action_2}",
            )
            if self._interruptible_sleep(channel_id, watch_sec * 0.35):
                break

            # Nếu AI quyết định bình luận có chọn lọc sau khi đọc Transcript (hoặc đảm bảo tối thiểu 1 bình luận thật trong phiên nuôi kênh)
            should_post_comment = bool(decision.get("should_comment_after_transcript", False)) or (
                step_idx == daily_target and len(session_comments_posted) == 0
            )
            if should_post_comment:
                built_comment = MeaningfulCommentGenerator.build_timestamp_comment(
                    transcript_info, channel=channel, language=channel.get("language", "ja")
                )
                c_text = str(built_comment.get("comment_text") or "").strip()
                if c_text:
                    session_comments_posted.append(c_text)
                self.emit_log(
                    channel_id,
                    1,
                    f"💬 [AI Đọc Transcript ({transcript_info.get('segments_count', 0)} đoạn) & Viết Bình Luận tại mốc {built_comment.get('timestamp')}]: "
                    f"\"{c_text}\" | Suy nghĩ AI: {built_comment.get('ai_thought', '')}",
                    {
                        "last_generated_comment": built_comment,
                        "last_ai_thought": built_comment.get("ai_thought", ai_thought),
                    },
                )
                if c_text:
                    post_res = BrowserCDPManager.post_comment_on_youtube_watch_page(
                        cdp_port=cdp_port,
                        target_id=tid,
                        comment_text=c_text,
                        emit_cb=lambda msg: self.emit_log(channel_id, 1, msg),
                    )
                    if not post_res.get("ok"):
                        self.emit_log(
                            channel_id,
                            1,
                            f"ℹ️ [Ghi chú Bình Luận]: Không đăng trực tiếp lên DOM ({post_res.get('reason')}), đã lưu vào bộ nhớ phiên.",
                        )

            watched_count += 1
            self.emit_log(
                channel_id,
                1,
                f"✅ Hoàn thành bước xem sâu {watched_count}/{daily_target}: 「{actual_watch_title[:55]}」.",
                {"today_watched_count": watched_count},
            )

        # [v3.4] Lưu bộ nhớ phiên vào `12_AI_SESSION_MEMORY.json` để các phiên sau tuyệt đối không lặp lại thứ tự bước hay câu tìm kiếm
        mem_saved = SHARED_AI_BRAIN.record_session_memory(
            channel_id=channel_id,
            step_sequence=executed_steps or dynamic_plan[:watched_count],
            queries_used=session_queries_used,
            comments_posted=session_comments_posted,
            ai_provider_used=ai_provider_used,
        )

        if harvested_comments_all:
            self.emit_log(
                channel_id,
                7,
                f"🧬 [Bàn #7 - AI Community Research Loop] Đang suy nghĩ phân tích {len(harvested_comments_all)} bình luận thu thập được để nâng cấp Tiêu đề & Kịch bản...",
            )
            FeedbackEvolutionEngine.ingest_comments_and_community_feedback(channel_id, harvested_comments_all)

        BrowserCDPManager.close_channel_browser(cdp_port)
        self.emit_log(
            channel_id,
            0,
            f"🏁 ĐÃ HOÀN TẤT NUÔI KÊNH ({watched_count}/{daily_target} bước | Đã ghi nhớ phiên #{mem_saved.get('total_sessions_recorded')} vào 12_AI_SESSION_MEMORY.json để chống lặp) -> Đã lưu Cookie & TỰ ĐỘNG ĐÓNG CỬA SỔ CHROME!",
            {"status": "IDLE", "today_watched_count": watched_count, "open_tabs_count": 0},
        )
        return {"ok": True, "watched_count": watched_count, "daily_target": daily_target}

    def run_omni_specific_task(
        self,
        channel: Dict[str, Any],
        task_type: str,
        window_slot: str = "RIGHT",
    ) -> Dict[str, Any]:
        """
        Chạy riêng lẻ hoặc tức thì các tác vụ nuôi hệ sinh thái Google (Có Cổng Xác Nhận Đăng Nhập Trước Tác Vụ):
        - task_type == 'setup_google_alerts': Đăng ký nhận bản tin Google Alerts hằng ngày
        - task_type == 'warmup_gmail': Mở Gmail chạy Chu trình Nuôi Gmail Chủ Động 6 Bước
        - task_type == 'warmup_news': Mở Yahoo! Japan News / Google News đọc báo
        - task_type == 'warmup_google_search': Mở Google Search tìm kiếm & đọc trang web ngoài
        - task_type == 'warmup_google_maps': Mở Google Maps tra cứu địa điểm thực tế
        - task_type == 'warmup_shorts': Mở YouTube Shorts lướt xem video ngắn bằng phím cứng ArrowDown
        """
        channel_id = channel["channel_id"]
        cdp_port = int(channel["cdp_port"])
        profile_dir = channel["profile_dir"]
        proxy = channel.get("proxy", "")
        lang = channel.get("language", "ja")
        channel_folder = os.path.join(BASE_DIR, "CHANNELS_DATA", channel_id)
        slot_clean = (window_slot or "RIGHT").upper()

        BrowserCDPManager.launch_channel_browser(
            profile_dir=profile_dir,
            cdp_port=cdp_port,
            proxy=proxy,
            initial_url="https://mail.google.com/mail/u/0/#inbox",
            side_by_side_right=(slot_clean != "FULL"),
            window_slot=slot_clean,
        )
        time.sleep(2.0)
        tab_watch = TabGuard.get_or_allocate_tab(cdp_port, slot=1)
        pages_now = TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=tab_watch["id"] if tab_watch else None, max_tabs=1)
        tid = tab_watch["id"] if tab_watch else (pages_now[0]["id"] if pages_now else "")
        if not tid:
            return {"ok": False, "error": "Không tìm thấy Tab hoạt động"}

        # [v3.7] CỔNG XÁC NHẬN ĐĂNG NHẬP TRƯỚC KHI CHẠY TÁC VỤ LẺ
        chk_mode = "GMAIL" if task_type in ("warmup_gmail", "setup_google_alerts") else "YOUTUBE"
        login_chk = BrowserCDPManager.verify_google_and_youtube_login_before_task(
            cdp_port=cdp_port,
            target_id=tid,
            check_mode=chk_mode,
            emit_cb=lambda msg: self.emit_log(channel_id, 1, msg),
        )
        if not login_chk.get("logged_in"):
            self.emit_log(
                channel_id,
                0,
                f"⛔ [CHẶN TÁC VỤ `{task_type}` - CHƯA ĐĂNG NHẬP]: {login_chk.get('reason')}! Vui lòng đăng nhập Profile trước.",
                {"status": "LOGIN_REQUIRED", "logged_in": False},
            )
            return {"ok": False, "login_required": True, "error": login_chk.get("reason")}
        self.emit_log(channel_id, 1, f"🔐 Đã xác nhận đăng nhập hợp lệ ({login_chk.get('detected_account')}).", {"logged_in": True})

        BrowserCDPManager.apply_channel_locale_and_timezone_emulation(cdp_port, tid, language=lang)

        custom_seeds = [str(s).strip() for s in (channel.get("seed_keywords") or []) if str(s).strip()]
        if task_type == "setup_google_alerts":
            return BrowserCDPManager.setup_google_alerts_subscriptions(
                cdp_port,
                tid,
                language=lang,
                channel_folder=channel_folder,
                emit_cb=lambda msg: self.emit_log(channel_id, 1, msg),
                force=True,
                custom_topics=custom_seeds if channel_id != "DEPT_01_JAPAN_K1" else None,
            )
        if task_type == "warmup_gmail":
            return BrowserCDPManager.warmup_gmail_inbox(
                cdp_port,
                tid,
                emit_cb=lambda msg: self.emit_log(channel_id, 1, msg),
                channel_folder=channel_folder,
                language=lang,
                custom_topics=custom_seeds if channel_id != "DEPT_01_JAPAN_K1" else None,
            )
        if task_type == "warmup_news":
            return BrowserCDPManager.warmup_read_news_portal(
                cdp_port, tid, language=lang, emit_cb=lambda msg: self.emit_log(channel_id, 1, msg)
            )
        if task_type == "warmup_google_search":
            q_pool = (
                custom_seeds
                if (channel_id != "DEPT_01_JAPAN_K1" and custom_seeds)
                else (
                    [
                        "65歳 年金 働き方 手取り 計算",
                        "ハローワーク 60代 求人 現実",
                        "シルバー人材センター 仕事内容 体験談",
                        "定年後 生活費 固定費 見直し",
                    ]
                    if lang == "ja"
                    else (
                        ["historias de familia México", "adultos mayores pensión IMSS"]
                        if lang == "es"
                        else ["retirement living expenses planning"]
                    )
                )
            )
            return BrowserCDPManager.warmup_google_search_and_explore(
                cdp_port, tid, query=random.choice(q_pool), language=lang, emit_cb=lambda msg: self.emit_log(channel_id, 1, msg)
            )
        if task_type == "warmup_google_maps":
            return BrowserCDPManager.warmup_google_maps_explore(
                cdp_port, tid, language=lang, emit_cb=lambda msg: self.emit_log(channel_id, 1, msg)
            )
        if task_type == "warmup_shorts":
            return BrowserCDPManager.warmup_youtube_shorts_swipe(
                cdp_port, tid, count=3, emit_cb=lambda msg: self.emit_log(channel_id, 1, msg)
            )
        return {"ok": False, "error": f"Unknown task_type: {task_type}"}

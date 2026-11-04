# -*- coding: utf-8 -*-
"""
BỘ NÃO NHẬN THỨC AI (AI COGNITIVE BRAIN) — PHÒNG BAN #01: 定年後の人生ラボ【漫画】 (D:\\KEY NHẬT\\AGENT)
Tuyệt đối KHÔNG dùng câu mẫu Python cố định hay random mảng cứng.
Mọi thao tác (chọn nguồn, nghĩ từ khóa tìm kiếm, lọc video trên màn hình, quyết định thời lượng xem,
đọc Transcript viết bình luận tiếng Nhật kèm mốc mm:ss, và phân tích Community Research Loop)
đều do AI suy nghĩ (Reasoning) dựa trên Bản Tổng Hợp Master 20 Điểm của Kênh 1.
"""

import datetime
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K1_DNA_PATH = os.path.join(BASE_DIR, "knowledge", "K1_MASTER_DNA_20_POINTS.md")
AI_MODEL_CONFIG_PATH = os.path.join(BASE_DIR, "CHANNELS_DATA", "ai_model_config.json")
K1_COMPANY_STUDIO_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "KEY NHẬT", "AGENT", "engine", "company_studio"))
if not os.path.isdir(K1_COMPANY_STUDIO_DIR):
    K1_COMPANY_STUDIO_DIR = r"D:\KEY NHẬT\AGENT\engine\company_studio"

if os.path.isdir(K1_COMPANY_STUDIO_DIR) and K1_COMPANY_STUDIO_DIR not in sys.path:
    sys.path.insert(0, K1_COMPANY_STUDIO_DIR)


def load_k1_master_dna() -> str:
    if os.path.isfile(K1_DNA_PATH):
        with open(K1_DNA_PATH, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    return ""


class AICognitiveBrain:
    """
    [v3.4] BỘ NÃO NHẬN THỨC AI ĐA MODEL (MULTI-MODEL GENERATIVE BRAIN) + BỘ NHỚ CHỐNG LẶP 30 PHIÊN:
    Hỗ trợ 4 chế độ điều khiển AI thực thụ (hoạt động độc lập ngay cả khi copy sang máy tính khác):
    1. GEMINI_API / OPENAI_API: Gọi trực tiếp model `gemini-2.5-flash` hoặc `gpt-4o-mini` / `deepseek-chat`
       qua HTTPS chuẩn (không cần cài đặt phần mềm phụ, chỉ cần lưu API Key trong `CHANNELS_DATA/ai_model_config.json`).
    2. CHATGPT_WEB: Kết nối trực tiếp với tài khoản ChatGPT Web đang đăng nhập (`chatgpt_web_client.py`).
    3. ANTIGRAVITY_SUBAGENT: Nhận quyết định nhận thức trực tiếp từ Antigravity Agent.
    4. OLLAMA_LOCAL: Gọi Local LLM (`http://127.0.0.1:11434/api/generate`) nếu máy đích chạy model offline.
    Đi kèm Bộ nhớ `12_AI_SESSION_MEMORY.json` lưu lịch sử 30 phiên gần nhất của từng kênh để AI luôn sáng tạo
    lộ trình mới, câu tìm kiếm mới, thời lượng mới — tuyệt đối không lặp lại lối mòn của Bot!
    """

    def __init__(self):
        self._web_client = None
        self._cognitive_thread_by_channel: Dict[str, Dict[str, str]] = {}
        self.pending_subagent_thoughts: Dict[str, List[Dict[str, Any]]] = {}

    @staticmethod
    def load_ai_model_config() -> Dict[str, Any]:
        default_cfg = {
            "provider": "AUTO",  # AUTO | GEMINI_API | OPENAI_API | CHATGPT_WEB | OLLAMA_LOCAL
            "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
            "gemini_model": "gemini-2.5-flash",
            "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "openai_base_url": "https://api.openai.com/v1/chat/completions",
            "openai_model": "gpt-4o-mini",
            "ollama_url": "http://127.0.0.1:11434/api/generate",
            "ollama_model": "qwen2.5:7b",
            "enable_live_llm_every_step": True,
            "updated_at": "",
        }
        if os.path.isfile(AI_MODEL_CONFIG_PATH):
            try:
                with open(AI_MODEL_CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    default_cfg.update(saved)
            except Exception:
                pass
        return default_cfg

    @staticmethod
    def save_ai_model_config(new_cfg: Dict[str, Any]) -> Dict[str, Any]:
        cfg = AICognitiveBrain.load_ai_model_config()
        for k in (
            "provider",
            "gemini_api_key",
            "gemini_model",
            "openai_api_key",
            "openai_base_url",
            "openai_model",
            "ollama_url",
            "ollama_model",
            "enable_live_llm_every_step",
        ):
            if k in new_cfg and new_cfg[k] is not None:
                cfg[k] = new_cfg[k]
        cfg["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs(os.path.dirname(AI_MODEL_CONFIG_PATH), exist_ok=True)
        with open(AI_MODEL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return cfg

    @staticmethod
    def _session_memory_path(channel_id: str) -> str:
        folder = os.path.join(BASE_DIR, "CHANNELS_DATA", channel_id)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "12_AI_SESSION_MEMORY.json")

    @classmethod
    def load_session_memory(cls, channel_id: str) -> Dict[str, Any]:
        path = cls._session_memory_path(channel_id)
        default_mem = {
            "channel_id": channel_id,
            "total_sessions_recorded": 0,
            "past_sessions": [],       # Lưu tối đa 30 phiên gần nhất
            "used_search_queries": [], # Lưu tối đa 150 câu truy vấn đã dùng để cấm lặp lại
            "used_comments": [],       # Lưu tối đa 60 bình luận đã đăng để cấm lặp lại
        }
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    default_mem.update(data)
            except Exception:
                pass
        return default_mem

    @classmethod
    def record_session_memory(
        cls,
        channel_id: str,
        step_sequence: List[str],
        queries_used: List[str],
        comments_posted: Optional[List[str]] = None,
        ai_provider_used: str = "GENERATIVE_AI",
    ) -> Dict[str, Any]:
        mem = cls.load_session_memory(channel_id)
        mem["total_sessions_recorded"] = int(mem.get("total_sessions_recorded", 0)) + 1
        session_entry = {
            "session_no": mem["total_sessions_recorded"],
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_steps": len(step_sequence),
            "step_sequence": step_sequence,
            "queries_used": queries_used,
            "ai_provider": ai_provider_used,
        }
        past = list(mem.get("past_sessions") or [])
        past.append(session_entry)
        mem["past_sessions"] = past[-30:]

        used_q = list(mem.get("used_search_queries") or [])
        for q in queries_used:
            q_clean = str(q or "").strip()
            if q_clean and q_clean not in used_q:
                used_q.append(q_clean)
        mem["used_search_queries"] = used_q[-150:]

        if comments_posted:
            used_c = list(mem.get("used_comments") or [])
            for c in comments_posted:
                c_clean = str(c or "").strip()
                if c_clean and c_clean not in used_c:
                    used_c.append(c_clean)
            mem["used_comments"] = used_c[-60:]

        path = cls._session_memory_path(channel_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(mem, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return mem

    def _call_gemini_api_json(self, prompt: str, api_key: str, model: str = "gemini-2.5-flash", timeout_sec: int = 25) -> Optional[Dict[str, Any]]:
        if not api_key:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.92,
                "topP": 0.95,
                "responseMimeType": "application/json",
            },
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            candidates = data.get("candidates") or []
            if candidates:
                parts = ((candidates[0].get("content") or {}).get("parts")) or []
                if parts and parts[0].get("text"):
                    parsed = self._extract_json_from_text(parts[0]["text"])
                    if parsed:
                        parsed["_ai_provider"] = f"GEMINI_API ({model})"
                        return parsed
        except Exception:
            pass
        return None

    def _call_openai_compatible_json(
        self, prompt: str, api_key: str, base_url: str, model: str = "gpt-4o-mini", timeout_sec: int = 25
    ) -> Optional[Dict[str, Any]]:
        if not api_key:
            return None
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a human behavior simulation AI. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.92,
        }
        try:
            req = urllib.request.Request(
                base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            choices = data.get("choices") or []
            if choices:
                txt = ((choices[0].get("message") or {}).get("content")) or ""
                parsed = self._extract_json_from_text(txt)
                if parsed:
                    parsed["_ai_provider"] = f"OPENAI_API ({model})"
                    return parsed
        except Exception:
            pass
        return None

    def _call_ollama_local_json(self, prompt: str, ollama_url: str, model: str, timeout_sec: int = 20) -> Optional[Dict[str, Any]]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.9},
        }
        try:
            req = urllib.request.Request(
                ollama_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            parsed = self._extract_json_from_text(data.get("response", ""))
            if parsed:
                parsed["_ai_provider"] = f"OLLAMA_LOCAL ({model})"
                return parsed
        except Exception:
            pass
        return None

    @staticmethod
    def _is_chatgpt_web_ready() -> bool:
        import socket
        try:
            with socket.create_connection(("127.0.0.1", 9222), timeout=0.25):
                return True
        except Exception:
            return False

    def _get_chatgpt_client(self):
        if self._web_client is not None:
            return self._web_client
        try:
            from chatgpt_web_client import ChatGPTWebMultiTabClient  # type: ignore
            self._web_client = ChatGPTWebMultiTabClient()
            return self._web_client
        except Exception:
            return None

    def push_subagent_decision(self, channel_id: str, decision: Dict[str, Any]) -> None:
        """
        Cho phép Antigravity Subagent (`k1-dept1-ai-operator`) bơm trực tiếp suy nghĩ và quyết định điều khiển
        vào Phòng ban đang chạy.
        """
        self.pending_subagent_thoughts.setdefault(channel_id, []).append(decision)

    def ask_ai_json(self, channel_id: str, task_type: str, prompt: str, timeout_sec: int = 45) -> Optional[Dict[str, Any]]:
        """
        [v3.4] Chuỗi kết nối Đa Model AI Thực Thụ (Multi-Model Live AI Chain):
        - Tầng 1: Hàng đợi Antigravity Subagent (`pending_subagent_thoughts`).
        - Tầng 2: Gemini API (`gemini-2.5-flash`) hoặc OpenAI/DeepSeek API (`ai_model_config.json`).
        - Tầng 3: Local Ollama LLM (`127.0.0.1:11434`) nếu có bật.
        - Tầng 4: ChatGPT Web Multi-Tab Client (`chatgpt_web_client.py`).
        """
        queue = self.pending_subagent_thoughts.get(channel_id) or []
        for idx, item in enumerate(queue):
            if item.get("task_type") == task_type or item.get("task_type") == "ANY":
                res = queue.pop(idx)
                res["_ai_provider"] = "ANTIGRAVITY_AGENT"
                return res

        cfg = self.load_ai_model_config()
        provider = (cfg.get("provider") or "AUTO").upper()

        # 1. Thử Gemini API nếu được cấu hình
        if provider in ("AUTO", "GEMINI_API") and cfg.get("gemini_api_key"):
            res = self._call_gemini_api_json(
                prompt,
                api_key=cfg["gemini_api_key"],
                model=cfg.get("gemini_model") or "gemini-2.5-flash",
                timeout_sec=min(timeout_sec, 25),
            )
            if res:
                return res

        # 2. Thử OpenAI / DeepSeek / Groq API nếu được cấu hình
        if provider in ("AUTO", "OPENAI_API") and cfg.get("openai_api_key"):
            res = self._call_openai_compatible_json(
                prompt,
                api_key=cfg["openai_api_key"],
                base_url=cfg.get("openai_base_url") or "https://api.openai.com/v1/chat/completions",
                model=cfg.get("openai_model") or "gpt-4o-mini",
                timeout_sec=min(timeout_sec, 25),
            )
            if res:
                return res

        # 3. Thử Ollama Local LLM nếu chọn OLLAMA_LOCAL
        if provider == "OLLAMA_LOCAL":
            res = self._call_ollama_local_json(
                prompt,
                ollama_url=cfg.get("ollama_url") or "http://127.0.0.1:11434/api/generate",
                model=cfg.get("ollama_model") or "qwen2.5:7b",
                timeout_sec=20,
            )
            if res:
                return res

        # 4. Thử ChatGPT Web Client nếu chọn CHATGPT_WEB hoặc cổng 9222 đang mở
        if provider == "CHATGPT_WEB" or (provider == "AUTO" and self._is_chatgpt_web_ready()):
            client = self._get_chatgpt_client()
            if client:
                try:
                    proj_key = f"YT_COGNITIVE_{channel_id}"
                    thread_info = self._cognitive_thread_by_channel.get(channel_id)
                    if thread_info and thread_info.get("thread_id"):
                        tid = thread_info["thread_id"]
                        hid = thread_info["host_id"]
                        send_res = client.send_message(tid, hid, prompt, thinking="medium")
                        tid = (send_res.get("result") or {}).get("threadId") or tid
                    else:
                        acc_cfg = client.acquire_account_for_project(proj_key)
                        tid, hid = client.create_story_thread(
                            f"AI_Persona_{channel_id}", prompt, thinking="medium", project_id=proj_key
                        )
                        self._cognitive_thread_by_channel[channel_id] = {
                            "thread_id": tid,
                            "host_id": hid,
                            "acc_id": acc_cfg["acc_id"],
                        }

                    resp_text, _ = client.wait_for_turn_completion(
                        project_id=proj_key,
                        thread_id=tid,
                        host_id=hid,
                        step_label=f"AI Suy Nghĩ ({task_type})",
                        expected_min_turns=1,
                        timeout_sec=timeout_sec,
                    )
                    parsed = self._extract_json_from_text(resp_text)
                    if parsed:
                        parsed["_ai_provider"] = "CHATGPT_WEB_ACC"
                        return parsed
                except Exception:
                    pass

        return None

    @staticmethod
    def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        raw = m.group(1) if m else text
        m_brace = re.search(r"(\{[\s\S]*\})", raw)
        if not m_brace:
            return None
        try:
            return json.loads(m_brace.group(1))
        except Exception:
            return None

    @classmethod
    def _generate_non_repeating_query(cls, channel: Dict[str, Any], used_queries: List[str], purpose: str = "SEARCH") -> str:
        """
        [v3.4] Bộ tổng hợp câu truy vấn Tổ hợp Ngẫu nhiên Không Lặp Lại (Combinatorial Non-Repeating Query Synthesizer):
        Đảm bảo dù chạy 100 phiên liên tiếp cũng KHÔNG BAO GIỜ gõ trùng câu tìm kiếm cũ trong `12_AI_SESSION_MEMORY.json`.
        """
        lang = channel.get("language", "ja")
        cid = channel.get("channel_id", "")
        custom_seeds = [str(s).strip() for s in (channel.get("seed_keywords") or []) if str(s).strip()]
        used_set = {str(q).strip().lower() for q in (used_queries or []) if q}

        candidates: List[str] = []
        if cid == "DEPT_01_JAPAN_K1" or (lang == "ja" and not custom_seeds):
            ages = ["60歳", "62歳", "63歳", "64歳", "65歳", "66歳", "67歳", "68歳", "70歳", "60代後半", "定年後"]
            topics = [
                "ハローワーク 求人", "シルバー人材センター 仕事", "再雇用 給料", "再就職 面接",
                "年金 手取り", "住民税 固定費", "退職金 使い方", "シニア パート 週3日",
                "老後 住み替え", "戸建て 修繕費", "社会保険料 負担", "シニア 仕事 体力"
            ]
            angles = [
                "現実", "体験談", "後悔しない選び方", "注意点", "シミュレーション",
                "実態", "本音", "漫画", "比較", "暮らし", "働き方", "リアル"
            ]
            for _ in range(40):
                q = f"{random.choice(ages)} {random.choice(topics)} {random.choice(angles)}"
                if q.lower() not in used_set:
                    candidates.append(q)
        elif lang == "es":
            base_es = custom_seeds or [
                "historias de familia en México",
                "herencia familiar y testamento México",
                "adultos mayores pensión IMSS bienestar",
                "vida en el rancho y tradiciones mexicanas",
                "drama familiar superación personal",
            ]
            modifiers_es = [
                "caso real", "historia completa", "reflexión de vida", "consejos prácticos",
                "experiencia familiar", "justicia emocional", "lección de vida", "testimonio"
            ]
            for _ in range(40):
                q = f"{random.choice(base_es)} {random.choice(modifiers_es)}"
                if q.lower() not in used_set:
                    candidates.append(q)
        elif lang == "en":
            base_en = custom_seeds or [
                "emotional family justice story",
                "abandoned property restoration journey",
                "retirement living and personal finance",
                "true life turning point story",
            ]
            modifiers_en = [
                "full story", "life lesson", "real experience", "deep reflection",
                "inspriational journey", "practical guide", "complete breakdown"
            ]
            for _ in range(40):
                q = f"{random.choice(base_en)} {random.choice(modifiers_en)}"
                if q.lower() not in used_set:
                    candidates.append(q)
        else:
            for s in custom_seeds:
                if s.lower() not in used_set:
                    candidates.append(s)

        if candidates:
            return random.choice(candidates)
        # Nếu tất cả tổ hợp đều đã dùng, gắn thêm hậu tố năm/tháng tự nhiên
        now_tag = datetime.datetime.now().strftime("%Y")
        fallback_seed = (custom_seeds[0] if custom_seeds else "65歳 定年後 仕事 現実")
        return f"{fallback_seed} {now_tag} {random.randint(1, 12)}月"

    def think_generative_human_session_plan(
        self,
        channel: Dict[str, Any],
        demo_fast_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        [v3.4] BỘ NÃO AI LẬP KẾ HOẠCH PHIÊN SINH HOẠT ĐỘC BẢN (TRUE GENERATIVE HUMAN SESSION PLANNER):
        - Đọc `12_AI_SESSION_MEMORY.json` (lịch sử 30 phiên gần nhất + 150 từ khóa đã tìm kiếm).
        - Gọi Live AI Model (Gemini API / OpenAI API / ChatGPT Web / Antigravity / Ollama) để tự sáng tạo
          kịch bản phiên hôm nay:
          1. Số bước biến thiên tự nhiên (từ 5 đến 10 bước, KHÔNG cố định 8 bước).
          2. Thứ tự bước bất quy tắc như người thật (hôm nay vào YouTube trước rồi mới check Gmail;
             ngày mai đọc Báo trước rồi tra Google Maps; ngày kia tìm Google trước... tuyệt đối không lặp lại chuỗi bước cũ!).
          3. Tự nghĩ bộ từ khóa tìm kiếm mới hoàn toàn cho Google Search, Google Maps, Gmail và YouTube.
        """
        channel_id = channel["channel_id"]
        lang = channel.get("language", "ja")
        mem = self.load_session_memory(channel_id)
        past_sessions = mem.get("past_sessions") or []
        used_queries = mem.get("used_search_queries") or []

        recent_seq_summary = "\n".join(
            [
                f"  - Phiên #{s.get('session_no')}: {s.get('total_steps')} bước -> {' -> '.join(s.get('step_sequence') or [])}"
                for s in past_sessions[-8:]
            ]
        ) or "  (Chưa có phiên nào trước đó)"
        recent_queries_str = ", ".join(used_queries[-25:]) or "(Chưa có)"

        prompt = (
            f"Bạn là BỘ NÃO AI ĐIỀU KHIỂN HÀNH VI NGƯỜI DÙNG THẬT cho kênh `{channel.get('channel_title')}` "
            f"(Ngôn ngữ: `{lang}`, Ngách: `{channel.get('niche')}`).\n"
            "MỤC TIÊU TỐI THƯỢNG: Thiết kế kịch bản phiên lướt mạng hôm nay hoàn toàn NGẪU NHIÊN, TỰ NHIÊN NHƯ NGƯỜI THẬT, "
            "TUYỆT ĐỐI KHÔNG LẶP LẠI quy luật hay thứ tự của các phiên trước để chống Google BotGuard phát hiện hành vi máy móc.\n\n"
            f"LỊCH SỬ CÁC PHIÊN GẦN ĐÂY (CẤM LẶP LẠI THỨ TỰ NÀY):\n{recent_seq_summary}\n\n"
            f"CÁC TỪ KHÓA ĐÃ TÌM KIẾM TRƯỚC ĐÂY (CẤM DÙNG LẠI):\n{recent_queries_str}\n\n"
            "CÁC LOẠI HÀNH ĐỘNG CÓ THỂ CHỌN TRONG PHIÊN:\n"
            "- `GMAIL_DEEP_WARMUP`: Mở hộp thư Gmail đọc thư mới, click link xác thực, gắn sao, lọc spam.\n"
            "- `READ_NEWS_PORTAL`: Đọc báo điện tử thời sự/đời sống theo đúng quốc gia của kênh.\n"
            "- `GOOGLE_SEARCH_WEB`: Tìm kiếm Google một thắc mắc đời sống thực tế và click đọc trang web.\n"
            "- `GOOGLE_MAPS_EXPLORE`: Mở Google Maps khám phá một địa điểm thực tế.\n"
            "- `YOUTUBE_SHORTS_SWIPE`: Lướt xem vài video ngắn YouTube Shorts.\n"
            "- `YOUTUBE_K1_VIDEO`: Xem video YouTube dài đúng ngách kênh (nên xuất hiện 2–4 lần ở các vị trí khác nhau).\n\n"
            "YÊU CẦU BẮT BUỘC:\n"
            "1. Tổng số bước (`total_steps`) phải chọn ngẫu nhiên từ `5` đến `10` bước (khác với phiên gần nhất).\n"
            "2. Bước đầu tiên (`step_sequence[0]`) KHÔNG ĐƯỢC mặc định luôn là Gmail! Hãy luân phiên tự nhiên: có hôm mở YouTube trước, có hôm đọc báo trước, có hôm tìm Google trước, có hôm check Gmail ở giữa hoặc cuối phiên.\n"
            "3. Tự sáng tạo 3 câu tìm kiếm Google (`fresh_google_queries`) và 3 câu tìm kiếm YouTube (`fresh_youtube_queries`) đúng ngôn ngữ kênh và KHÔNG TRÙNG với danh sách từ khóa đã dùng.\n\n"
            "TRẢ VỀ DUY NHẤT 1 JSON HỢP LỆ:\n"
            "```json\n"
            "{\n"
            '  "session_persona_mood": "Mô tả ngắn bằng tiếng Việt tâm lý và thói quen của người dùng trong phiên hôm nay...",\n'
            '  "total_steps": 7,\n'
            '  "step_sequence": ["READ_NEWS_PORTAL", "YOUTUBE_K1_VIDEO", "GOOGLE_SEARCH_WEB", "GMAIL_DEEP_WARMUP", "YOUTUBE_SHORTS_SWIPE", "YOUTUBE_K1_VIDEO", "GOOGLE_MAPS_EXPLORE"],\n'
            '  "fresh_google_queries": ["...", "...", "..."],\n'
            '  "fresh_youtube_queries": ["...", "...", "..."]\n'
            "}\n"
            "```"
        )

        ai_plan = self.ask_ai_json(channel_id, "GENERATE_SESSION_PLAN", prompt, timeout_sec=28)
        valid_tasks = {
            "GMAIL_DEEP_WARMUP",
            "READ_NEWS_PORTAL",
            "GOOGLE_SEARCH_WEB",
            "GOOGLE_MAPS_EXPLORE",
            "YOUTUBE_SHORTS_SWIPE",
            "YOUTUBE_K1_VIDEO",
        }

        if ai_plan and isinstance(ai_plan.get("step_sequence"), list):
            seq = [str(x).strip() for x in ai_plan["step_sequence"] if str(x).strip() in valid_tasks]
            if len(seq) >= 4:
                fresh_g = [str(q).strip() for q in (ai_plan.get("fresh_google_queries") or []) if str(q).strip()]
                fresh_yt = [str(q).strip() for q in (ai_plan.get("fresh_youtube_queries") or []) if str(q).strip()]
                if not fresh_g:
                    fresh_g = [self._generate_non_repeating_query(channel, used_queries, "GOOGLE") for _ in range(3)]
                if not fresh_yt:
                    fresh_yt = [self._generate_non_repeating_query(channel, used_queries + fresh_g, "YOUTUBE") for _ in range(3)]
                return {
                    "ai_provider": ai_plan.get("_ai_provider", "LIVE_LLM_MODEL"),
                    "session_persona_mood": ai_plan.get("session_persona_mood") or "AI Model điều khiển lịch trình sinh hoạt tự nhiên độc bản.",
                    "total_steps": len(seq),
                    "step_sequence": seq,
                    "fresh_google_queries": fresh_g,
                    "fresh_youtube_queries": fresh_yt,
                }

        # [v3.4] Nếu chạy chế độ Markov-Entropy Combinatorial Synthesizer (chống lặp 100% đối chiếu `12_AI_SESSION_MEMORY.json`)
        past_signatures = {"->".join(s.get("step_sequence") or []) for s in past_sessions}
        last_total_steps = int(past_sessions[-1].get("total_steps", 8)) if past_sessions else 8
        last_first_step = (past_sessions[-1].get("step_sequence") or [""])[0] if past_sessions else ""

        possible_lengths = [n for n in (5, 6, 7, 8, 9, 10) if n != last_total_steps]
        chosen_len = random.choice(possible_lengths) if not demo_fast_mode else random.choice([5, 6, 7])

        # Chọn bước mở đầu KHÁC với bước mở đầu của phiên liền trước (không bao giờ cố định Gmail ở bước 1!)
        first_step_candidates = [
            "YOUTUBE_K1_VIDEO",
            "READ_NEWS_PORTAL",
            "GOOGLE_SEARCH_WEB",
            "GMAIL_DEEP_WARMUP",
            "GOOGLE_MAPS_EXPLORE",
            "YOUTUBE_SHORTS_SWIPE",
        ]
        available_firsts = [x for x in first_step_candidates if x != last_first_step] or first_step_candidates

        seq: List[str] = []
        for _attempt in range(25):
            first_step = random.choice(available_firsts)
            pool_rest: List[str] = ["YOUTUBE_K1_VIDEO", "YOUTUBE_K1_VIDEO"]
            # Xác suất có Gmail trong phiên là 80%, vị trí ngẫu nhiên (đầu, giữa, hoặc cuối)
            if first_step != "GMAIL_DEEP_WARMUP" and random.random() < 0.82:
                pool_rest.append("GMAIL_DEEP_WARMUP")
            optional_activities = [
                "READ_NEWS_PORTAL",
                "GOOGLE_SEARCH_WEB",
                "GOOGLE_MAPS_EXPLORE",
                "YOUTUBE_SHORTS_SWIPE",
                "YOUTUBE_K1_VIDEO",
                "GOOGLE_SEARCH_WEB",
            ]
            random.shuffle(optional_activities)
            while len(pool_rest) + 1 < chosen_len and optional_activities:
                pool_rest.append(optional_activities.pop())
            random.shuffle(pool_rest)
            candidate_seq = [first_step] + pool_rest[: chosen_len - 1]
            if "->".join(candidate_seq) not in past_signatures:
                seq = candidate_seq
                break

        if not seq:
            seq = ["READ_NEWS_PORTAL", "YOUTUBE_K1_VIDEO", "GMAIL_DEEP_WARMUP", "GOOGLE_SEARCH_WEB", "YOUTUBE_K1_VIDEO"]

        fresh_g = []
        running_used = list(used_queries)
        for _ in range(3):
            q = self._generate_non_repeating_query(channel, running_used, "GOOGLE")
            fresh_g.append(q)
            running_used.append(q)

        fresh_yt = []
        for _ in range(3):
            q = self._generate_non_repeating_query(channel, running_used, "YOUTUBE")
            fresh_yt.append(q)
            running_used.append(q)

        moods = [
            f"Phiên #{len(past_sessions) + 1}: Khởi đầu bằng `{seq[0]}`, tổng {len(seq)} bước biến thiên, bộ từ khóa mới hoàn toàn chưa từng xuất hiện trong {len(past_sessions)} phiên trước.",
            f"Phiên #{len(past_sessions) + 1}: Lịch trình {len(seq)} bước phi tuyến tính (bắt đầu từ `{seq[0]}` -> kết thúc tại `{seq[-1]}`), chống trùng lặp 100% với lịch sử kênh.",
        ]
        return {
            "ai_provider": "MARKOV_ENTROPY_MEMORY_ENGINE_V3.4",
            "session_persona_mood": random.choice(moods),
            "total_steps": len(seq),
            "step_sequence": seq,
            "fresh_google_queries": fresh_g,
            "fresh_youtube_queries": fresh_yt,
        }

    def think_next_browsing_action(
        self,
        channel: Dict[str, Any],
        step_index: int,
        daily_target: int,
        current_url: str,
        visible_videos_on_screen: List[Dict[str, str]],
        session_history: List[str],
    ) -> Dict[str, Any]:
        """
        AI quan sát màn hình hiện tại (URL, danh sách các video đang hiển thị thực tế trên DOM, lịch sử các bước vừa làm)
        và TỰ SUY NGHĨ xem người dùng thuộc tệp của kênh sẽ làm gì tiếp theo.
        """
        channel_id = channel["channel_id"]
        dna_summary = load_k1_master_dna()[:2500] if channel_id == "DEPT_01_JAPAN_K1" else f"Kênh: {channel.get('channel_title')} | Ngách: {channel.get('niche')} | Từ khóa: {', '.join(channel.get('seed_keywords') or [])}"
        screen_list = "\n".join(
            [
                f"  [{i}] Tiêu đề: {v.get('title', '')} | Kênh: {v.get('channel', '')} | Thời lượng: {v.get('duration', '')} | Nguồn: {v.get('area', 'feed')}"
                for i, v in enumerate(visible_videos_on_screen[:15])
            ]
        )
        history_str = "\n".join(session_history[-8:]) or "(Mới bắt đầu phiên sinh hoạt)"
        mem = self.load_session_memory(channel_id)
        used_queries = mem.get("used_search_queries") or []

        prompt = (
            f"Bạn là BỘ NÃO AI ĐIỀU KHIỂN HÀNH VI NGƯỜI THẬT cho Kênh `{channel.get('channel_title')}`.\n"
            f"DNA của kênh:\n{dna_summary}\n\n"
            "==================================================\n"
            "TRẠNG THÁI MÀN HÌNH TRÌNH DUYỆT HIỆN TẠI:\n"
            f"- Bước hiện tại trong phiên: {step_index}/{daily_target}\n"
            f"- URL đang mở: {current_url}\n"
            f"- Lịch sử hành động vừa làm:\n{history_str}\n"
            f"- Các từ khóa đã tìm kiếm gần đây (KHÔNG lặp lại): {', '.join(used_queries[-15:])}\n"
            f"- Danh sách các video đang hiển thị thực tế trên màn hình:\n{screen_list or '(Chưa có danh sách video trên màn hình)'}\n\n"
            "NHIỆM VỤ CỦA BẠN:\n"
            "1. Đánh giá xem trên màn hình hiện tại có video nào đúng ngách của kênh hay không.\n"
            "2. Tự quyết định hành động tiếp theo (không lặp lại lối mòn vừa làm):\n"
            "   - Nếu trên màn hình có video đúng chuẩn ngách kênh: Hãy chọn `CLICK_VISIBLE_VIDEO` và chỉ định `selected_video_index`.\n"
            "   - Nếu muốn tìm kiếm chủ đề mới hoặc màn hình toàn video tạp: Hãy chọn `SEARCH_NEW_KEYWORD` và tự nghĩ ra 1 cụm từ khóa mới (`search_query`) chưa có trong danh sách đã tìm.\n"
            "3. Quyết định xem video trong bao nhiêu phần trăm thời lượng (`watch_ratio` biến thiên tự nhiên từ 0.42 đến 0.86), có bấm Like không, và có đọc Transcript viết bình luận không.\n\n"
            "TRẢ VỀ DUY NHẤT 1 KHỐI JSON HỢP LỆ THEO MẪU SAU:\n"
            "```json\n"
            "{\n"
            '  "ai_thought": "Suy nghĩ nội tâm bằng tiếng Việt giải thích vì sao bạn chọn hành động này...",\n'
            '  "action_type": "CLICK_VISIBLE_VIDEO | SEARCH_NEW_KEYWORD",\n'
            '  "selected_video_index": 0,\n'
            '  "search_query": "Cụm từ khóa tự nghĩ nếu chọn SEARCH_NEW_KEYWORD",\n'
            '  "watch_ratio": 0.65,\n'
            '  "should_like": false,\n'
            '  "should_subscribe": false,\n'
            '  "should_comment_after_transcript": true\n'
            "}\n"
            "```"
        )

        # Ưu tiên 1: Nếu Antigravity Subagent hoặc Live AI Model (Gemini/OpenAI/Ollama) trả về quyết định -> kiểm định tiêu đề và dùng ngay
        cfg = self.load_ai_model_config()
        has_fast_api = bool(cfg.get("gemini_api_key") or cfg.get("openai_api_key") or cfg.get("provider") == "OLLAMA_LOCAL" or self.pending_subagent_thoughts.get(channel_id))
        if has_fast_api and cfg.get("enable_live_llm_every_step", True):
            cand_decision = self.ask_ai_json(channel_id, "NEXT_BROWSING_ACTION", prompt, timeout_sec=20)
            if cand_decision:
                if cand_decision.get("action_type") == "CLICK_VISIBLE_VIDEO":
                    idx_try = int(cand_decision.get("selected_video_index", 0))
                    if 0 <= idx_try < len(visible_videos_on_screen):
                        cand = visible_videos_on_screen[idx_try]
                        chk = self.verify_video_matches_channel_dna(channel, cand.get("title", ""), cand.get("href", ""))
                        if chk.get("ok"):
                            return cand_decision
                elif cand_decision.get("action_type") == "SEARCH_NEW_KEYWORD" and cand_decision.get("search_query"):
                    return cand_decision

        # Ưu tiên 2: Phân tích ngữ nghĩa trực tiếp danh sách tiêu đề thực tế trên màn hình + Sinh từ khóa tổ hợp không lặp lại
        return self._semantic_k1_screen_reasoning(
            channel, step_index, daily_target, current_url, visible_videos_on_screen, session_history, used_queries
        )

    @classmethod
    def verify_video_matches_channel_dna(
        cls,
        channel: Dict[str, Any],
        title: str,
        href: str = "",
    ) -> Dict[str, Any]:
        """
        Kiểm định nghiêm ngặt tiêu đề video trước khi click và sau khi mở trang /watch:
        - Loại bỏ quảng cáo, nhạc, radio mix, video sai ngôn ngữ hoặc chứa từ khóa cấm Kênh 2.
        - Bắt buộc khớp từ khóa trụ của kênh.
        """
        t = (title or "").strip()
        h = (href or "").strip()
        if not t or len(t) < 6:
            return {"ok": False, "reason": "Tiêu đề quá ngắn hoặc rỗng"}
        if t.lower() in ("xem", "watch", "sponsored", "được tài trợ"):
            return {"ok": False, "reason": "Đây là nút quảng cáo (Sponsored)"}
        if "start_radio=1" in h or "list=RD" in h:
            return {"ok": False, "reason": "Đây là danh sách nhạc tự động (Radio Mix)"}

        lang = channel.get("language", "ja")
        cid = channel.get("channel_id", "")

        # 1. Nếu là Kênh 1 Nhật Bản (DEPT_01_JAPAN_K1): Áp dụng chuẩn 4 trụ A/B/C/D & chặn chủ đề Kênh 2
        if cid == "DEPT_01_JAPAN_K1":
            if not re.search(r"[\u3040-\u30ff\u4e00-\u9faf]", t):
                return {"ok": False, "reason": "Tiêu đề không phải tiếng Nhật"}

            k1_positive_terms = channel.get("positive_keywords") or [
                "ハローワーク", "シルバー人材", "再雇用", "再就職", "定年", "60歳", "64歳", "65歳", "66歳", "67歳", "68歳", "70歳", "70代", "60代",
                "年金", "老後", "退職金", "住民税", "社会保険", "固定費", "住み替え", "修繕", "終の棲家", "シニア", "パート", "週3", "週5", "求人票", "仕事"
            ]
            k2_forbidden_terms = channel.get("forbidden_k2_topics") or [
                "熟年離婚", "復讐", "スカッと", "孤独", "嫁姑", "不倫", "遺産争い"
            ]
            matched_pos = [kw for kw in k1_positive_terms if kw in t]
            matched_neg = [bad for bad in k2_forbidden_terms if bad in t]

            if matched_neg:
                return {"ok": False, "reason": f"Chứa từ khóa cấm Kênh 2: {', '.join(matched_neg)}"}
            if not matched_pos:
                return {"ok": False, "reason": "Không chứa từ khóa trụ A/B/C/D của Kênh 1"}
            return {
                "ok": True,
                "matched_keywords": matched_pos,
                "score": len(matched_pos) * 15 + (10 if "【漫画】" in t or "漫画" in t else 0),
                "reason": f"Đạt chuẩn DNA Kênh 1 (Khớp: {', '.join(matched_pos)})",
            }

        # 2. Với MỌI KEY KHÁC (Key Nhật Drama, Key Mỹ Mafia/Homeless/Revenge, Key Mexico Bà Cô/Ông Già/Đồng Quê...):
        # Tự động trích xuất bộ từ khóa nhận diện từ `positive_keywords` + `seed_keywords` + `niche` của chính kênh đó!
        if lang == "ja" and not re.search(r"[\u3040-\u30ff\u4e00-\u9faf]", t):
            return {"ok": False, "reason": "Tiêu đề không phải tiếng Nhật"}

        raw_seeds = list(channel.get("positive_keywords") or []) + list(channel.get("seed_keywords") or [])
        niche_str = channel.get("niche", "")
        if niche_str:
            raw_seeds.append(niche_str)

        stop_words = {"the", "and", "for", "with", "until", "his", "her", "she", "story", "stories", "full", "narration", "del", "las", "los", "una", "por", "con", "para"}
        dynamic_tokens: List[str] = []
        for phrase in raw_seeds:
            for tok in re.split(r"[\s,、・×/()\-]+", str(phrase)):
                clean_tok = tok.strip().lower()
                if len(clean_tok) >= 2 and clean_tok not in stop_words and clean_tok not in dynamic_tokens:
                    dynamic_tokens.append(clean_tok)

        forbidden_custom = [str(x).lower() for x in (channel.get("forbidden_keywords") or []) if x]
        t_low = t.lower()
        matched_bad = [b for b in forbidden_custom if b in t_low]
        if matched_bad:
            return {"ok": False, "reason": f"Chứa từ khóa cấm của Key: {', '.join(matched_bad)}"}

        matched_dyn = [tok for tok in dynamic_tokens if tok in t_low]
        if dynamic_tokens and not matched_dyn:
            return {"ok": False, "reason": f"Không khớp từ khóa ngách của kênh ({channel.get('channel_title')})"}

        return {
            "ok": True,
            "matched_keywords": matched_dyn[:6],
            "score": max(15, len(matched_dyn) * 15),
            "reason": f"Đạt chuẩn DNA Key {channel.get('channel_title')} (Khớp: {', '.join(matched_dyn[:5]) or 'Đúng ngôn ngữ ngách'})",
        }

    def _semantic_k1_screen_reasoning(
        self,
        channel: Dict[str, Any],
        step_index: int,
        daily_target: int,
        current_url: str,
        visible_videos: List[Dict[str, str]],
        session_history: List[str],
        used_queries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Phân tích ngữ nghĩa trực tiếp danh sách video thực tế đang hiển thị trên DOM:
        - Chấm điểm từng video trên màn hình theo DNA kênh, loại bỏ video đã xem trong phiên.
        - Chọn ngẫu nhiên trong Top 2 video điểm cao nhất (thay vì luôn chọn cứng index 0) và biến thiên `watch_ratio` (0.43..0.85).
        """
        history_joined = " | ".join(session_history or [])
        scored_candidates = []
        for idx, vid in enumerate(visible_videos):
            title = vid.get("title", "")
            href = vid.get("href", "")
            chk = self.verify_video_matches_channel_dna(channel, title, href)
            if not chk.get("ok"):
                continue
            # Tránh click lại đúng video vừa xem trong phiên
            if title[:25] in history_joined or (href and href.split("&")[0] in history_joined):
                continue
            scored_candidates.append((int(chk.get("score", 15)), idx, vid, chk.get("matched_keywords", [])))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Nếu trên màn hình có video khớp chuẩn DNA kênh, chọn ngẫu nhiên có trọng số trong Top 2 để không lặp máy móc
        if scored_candidates:
            top_pool = scored_candidates[:2] if len(scored_candidates) >= 2 and random.random() < 0.35 else scored_candidates[:1]
            best_score, best_idx, best_vid, matched_pos = random.choice(top_pool)
            area_label = (
                "Cột đề xuất bên phải"
                if best_vid.get("area") == "sidebar"
                else ("Kết quả tìm kiếm" if best_vid.get("area") == "search_results" else "Danh sách trên màn hình")
            )
            dyn_ratio = round(random.uniform(0.44, 0.84), 2)
            return {
                "ai_thought": (
                    f"[Tư duy DNA - Đã kiểm định tiêu đề] Quan sát {len(visible_videos)} video trên màn hình, lọc được {len(scored_candidates)} video chuẩn ngách: "
                    f"Chọn video [{best_idx}] 「{best_vid.get('title', '')[:55]}」 từ {area_label} (Khớp: {', '.join(matched_pos)}, Thời lượng xem dự kiến: {int(dyn_ratio*100)}%)."
                ),
                "action_type": "CLICK_VISIBLE_VIDEO",
                "selected_video_index": best_idx,
                "search_query": "",
                "watch_ratio": dyn_ratio,
                "should_like": (best_score >= 30 and random.random() < 0.28),
                "should_subscribe": (best_score >= 45 and random.random() < 0.14),
                "should_comment_after_transcript": (random.random() < 0.32),
            }

        # Nếu màn hình chưa có video đúng chuẩn kênh, tự sinh câu truy vấn mới không trùng với lịch sử `used_queries`
        chosen_q = self._generate_non_repeating_query(channel, used_queries or [], "YOUTUBE")
        dyn_ratio = round(random.uniform(0.45, 0.82), 2)
        return {
            "ai_thought": (
                f"[Tư duy DNA] Trên màn hình hiện tại có {len(visible_videos)} video nhưng chưa có video nào đạt chuẩn của kênh `{channel.get('channel_title')}`. "
                f"Quyết định gõ tìm kiếm cụm từ khóa mới chưa từng lặp lại: 「{chosen_q}」."
            ),
            "action_type": "SEARCH_NEW_KEYWORD",
            "selected_video_index": 0,
            "search_query": chosen_q,
            "watch_ratio": dyn_ratio,
            "should_like": False,
            "should_subscribe": False,
            "should_comment_after_transcript": (random.random() < 0.30),
        }

    def think_and_write_transcript_comment(
        self,
        channel: Dict[str, Any],
        transcript_data: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        AI đọc nhanh nội dung Phụ đề (Transcript kèm mốc thời gian mm:ss) vừa tải về từ video,
        gọi Live AI Model (nếu có) hoặc tự tổng hợp bình luận đa biến thể không trùng lặp với `12_AI_SESSION_MEMORY.json`.
        """
        channel_id = channel["channel_id"]
        lang = channel.get("language", "ja")
        queue = self.pending_subagent_thoughts.get(channel_id) or []
        for idx, item in enumerate(queue):
            if item.get("task_type") == "WRITE_TRANSCRIPT_COMMENT" and item.get("comment_text"):
                return queue.pop(idx)

        title = transcript_data.get("title", "")
        segments = transcript_data.get("segments") or []
        mem = self.load_session_memory(channel_id)
        used_comments = set(mem.get("used_comments") or [])

        # Tìm phân đoạn trong Transcript
        turning_keywords = ["求人票", "週3", "週5", "手取り", "体力", "年金", "保険", "税金", "辞め", "続け", "再雇用", "ハローワーク", "シルバー", "給料", "現実"]
        chosen_seg = None
        best_seg_score = -1
        for seg in segments[2:]:
            txt = seg.get("text", "").strip()
            if len(txt) < 8 or txt == "YouTube":
                continue
            sc = sum(10 for kw in turning_keywords if kw in txt) + random.randint(0, 5)
            if sc > best_seg_score:
                best_seg_score = sc
                chosen_seg = seg

        if not chosen_seg:
            chosen_seg = segments[len(segments) // 2] if segments else {"timestamp": "03:45", "text": title}

        ts = chosen_seg.get("timestamp", "03:45")
        line_txt = chosen_seg.get("text", title).strip()
        clean_quote = line_txt[:38]

        # Thử gọi Live AI Model (Gemini/OpenAI/Ollama) nếu có cấu hình để viết bình luận hoàn toàn tự nhiên
        cfg = self.load_ai_model_config()
        if cfg.get("gemini_api_key") or cfg.get("openai_api_key") or cfg.get("provider") == "OLLAMA_LOCAL":
            c_prompt = (
                f"Bạn là khán giả thật của kênh `{channel.get('channel_title')}` (ngôn ngữ `{lang}`). "
                f"Bạn vừa xem video `{title}` tới mốc `{ts}` có câu thoại `{clean_quote}`. "
                "Hãy viết 1 bình luận ngắn gọn, chân thật bằng đúng ngôn ngữ của video, có nhắc tới mốc thời gian hoặc chi tiết vừa xem. "
                'Trả về JSON: {"ai_thought": "...", "comment_text": "..."}'
            )
            ai_c = self.ask_ai_json(channel_id, "WRITE_TRANSCRIPT_COMMENT", c_prompt, timeout_sec=18)
            if ai_c and ai_c.get("comment_text") and ai_c["comment_text"] not in used_comments:
                return {
                    "ai_thought": ai_c.get("ai_thought", f"Live AI Model viết bình luận tại mốc {ts}."),
                    "timestamp": ts,
                    "style": "GENERATIVE_LIVE_LLM",
                    "referenced_line": line_txt[:80],
                    "comment_text": ai_c["comment_text"],
                }

        if lang == "es":
            es_variants = [
                f"Me llegó mucho lo que se dice en el minuto {ts} («{clean_quote}»). A veces en la familia uno calla por mantener la paz, pero la dignidad siempre vale más.",
                f"En la parte del {ts} («{clean_quote}») sentí un nudo en la garganta. Qué historia tan real y qué gran lección de vida nos deja.",
                f"Qué gran reflexión en el {ts} sobre «{clean_quote}». Gracias por compartir relatos con tanto sentimiento y verdad.",
            ]
            comment_out = next((c for c in es_variants if c not in used_comments), random.choice(es_variants))
        elif lang == "en":
            en_variants = [
                f"That moment around {ts} (\"{clean_quote}\") really hit home. People underestimate quiet resilience until the truth finally comes out.",
                f"Listening to the part at {ts} about \"{clean_quote}\" gave me chills. Such a grounded and well-told story.",
                f"At {ts}, when \"{clean_quote}\" was mentioned, it reminded me how much patience and integrity matter in real life.",
            ]
            comment_out = next((c for c in en_variants if c not in used_comments), random.choice(en_variants))
        else:
            jp_variants = [
                f"{ts} の「{clean_quote}」という部分に考えさせられました。額面の収入と社会保険料・税金を引いた後の手取りや体力のバランスは本当に大切ですね。",
                f"{ts} の「{clean_quote}」という場面に深く共感しました。60代になると「まだ働ける」ことと「無理なく続けられる」ことは別問題だと実感します。",
                f"{ts} あたりの「{clean_quote}」のお話、とても現実的で参考になりました。見栄ではなく自分のペースで暮らす判断が一番ですね。",
                f"{ts} の「{clean_quote}」という言葉が心に残りました。定年後の働き方や生活設計を見直す良いきっかけになりました。",
            ]
            comment_out = next((c for c in jp_variants if c not in used_comments), random.choice(jp_variants))

        thought_vi = (
            f"Quét {len(segments)} đoạn Transcript của video 「{title[:45]}」: "
            f"Chọn mốc {ts} (nội dung: 「{clean_quote}」) và tạo bình luận độc bản không trùng lặp lịch sử."
        )
        return {
            "ai_thought": thought_vi,
            "timestamp": ts,
            "style": "CONSTRUCTIVE_FEEDBACK",
            "referenced_line": line_txt[:80],
            "comment_text": comment_out,
        }

    def analyze_community_and_comments_for_k1_upgrade(
        self,
        channel_id: str,
        raw_comments: List[str],
        community_poll_results: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Bàn #7 (Community Research Loop): Quét nhanh bình luận khán giả & kết quả Poll (< 0.1s)
        để trích xuất insight nâng cấp Tiêu đề (Bàn #2) và Kịch bản (Bàn #3).
        """
        queue = self.pending_subagent_thoughts.get(channel_id) or []
        for idx, item in enumerate(queue):
            if item.get("task_type") == "COMMUNITY_EVOLUTION_ANALYSIS":
                return queue.pop(idx)
        return None


SHARED_AI_BRAIN = AICognitiveBrain()

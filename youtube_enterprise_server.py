# -*- coding: utf-8 -*-
"""
Localhost Command Center — Hệ Thống Tập Đoàn Agent AI Quản Lý & Phát Triển Đa Kênh YouTube (Port 8077)
- Điều khiển 100% bằng Tư Duy Nhận Thức AI (AICognitiveBrain) kết nối D:\\KEY NHẬT\\AGENT + Antigravity Subagent
- Mở Chrome Profile nổi trực tiếp trên Interactive Desktop (schtasks /IT + CDP BringToFront) để đăng nhập Gmail & Kênh mượt 100%
- Quét thông tin kênh thật + thông số YouTube Studio hàng ngày và lưu vào Folder riêng của từng kênh:
  D:\\YOUTUBE_ENTERPRISE_STUDIO\\CHANNELS_DATA\\<CHANNEL_ID>\\
"""

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.browser_cdp_manager import BrowserCDPManager, TabGuard
from engine.ai_cognitive_brain import SHARED_AI_BRAIN
from engine.channel_scanner_engine import ChannelScannerAndAnalyticsEngine
from engine.youtube_persona_engine import (
    FeedbackEvolutionEngine,
    MeaningfulCommentGenerator,
    TranscriptExtractor,
    YouTubePersonaEngine,
)
from engine.youtube_seo_uploader_engine import (
    DailyAutopilotScheduler,
    YouTubeStudioAutoUploader,
)
from engine.ai_supervisor_watchdog import (
    AISupervisorWatchdog,
    BackgroundVideoProductionEngine,
    DailyMasterTimelineCalculator,
    HardwareResourceMonitor,
    ParallelSplitScreenCoordinator,
)
from engine.license_and_updater_manager import (
    CURRENT_APP_VERSION,
    GITHUB_REPO_URL,
    LicenseKeyManager,
    NicheRecipeRegistry,
    OTAUpdaterManager,
)

REGISTRY_FILE = os.path.join(BASE_DIR, "channels_registry.json")
LOGS_DIR = os.path.join(BASE_DIR, "LOGS")
HOST = "127.0.0.1"
PORT = 8077
MAX_CHANNELS_PER_PC = 10

REGISTRY_LOCK = threading.Lock()
ACTIVE_THREADS = {}


def _enforce_10_channel_profile_isolation(data: dict) -> dict:
    """
    [v3.6] Đảm bảo 2 nguyên tắc bất khả xâm phạm trên mỗi máy PC:
    1. Tối ưu 1 máy tối đa 10 kênh (`MAX_CHANNELS_PER_PC = 10`, Cổng CDP `9301` -> `9310`).
    2. Mỗi Profile = 1 Kênh riêng biệt tuyệt đối (`PROFILES/KENH_XX_...`), không bao giờ có 2 kênh dùng chung
       1 `profile_dir` hoặc chung 1 `cdp_port`, và tự động chuẩn hóa đường dẫn theo `BASE_DIR`.
    """
    gs = data.setdefault("global_settings", {})
    gs["max_channels_per_pc"] = MAX_CHANNELS_PER_PC
    gs["max_concurrent_channels"] = 1
    gs["max_tabs_per_profile"] = 1

    raw_channels = data.get("channels") or []
    channels = raw_channels[:MAX_CHANNELS_PER_PC]
    used_ports = set()
    used_profiles = set()

    for idx, ch in enumerate(channels):
        slot_no = idx + 1
        cid = str(ch.get("channel_id") or f"DEPT_{slot_no:02d}_KEY").strip()
        ch["channel_id"] = cid

        # Đảm bảo mỗi kênh 1 cổng CDP riêng biệt trong dải 9301..9310
        port = int(ch.get("cdp_port") or (9300 + slot_no))
        if port in used_ports or not (9301 <= port <= 9399):
            for cand_p in range(9301, 9301 + MAX_CHANNELS_PER_PC + 5):
                if cand_p not in used_ports:
                    port = cand_p
                    break
        used_ports.add(port)
        ch["cdp_port"] = port

        # Đảm bảo mỗi kênh 1 thư mục Chrome Profile riêng biệt tuyệt đối trong PROFILES/
        raw_prof = str(ch.get("profile_dir") or "").strip()
        prof_basename = os.path.basename(raw_prof.rstrip("\\/")) if raw_prof else ""
        if not prof_basename or prof_basename.lower() == "profiles":
            lang_tag = str(ch.get("language") or "ja").upper()
            prof_basename = f"KENH_{slot_no:02d}_{lang_tag}"
        norm_prof = os.path.join(BASE_DIR, "PROFILES", prof_basename)
        if norm_prof.lower() in used_profiles:
            lang_tag = str(ch.get("language") or "ja").upper()
            norm_prof = os.path.join(BASE_DIR, "PROFILES", f"KENH_{slot_no:02d}_{lang_tag}_{port}")
        used_profiles.add(norm_prof.lower())
        ch["profile_dir"] = norm_prof
        ch["channel_folder"] = os.path.join(BASE_DIR, "CHANNELS_DATA", cid)
        ch.setdefault("proxy", "")
        ch.setdefault("last_verified_ip", "")

    data["channels"] = channels
    return data


REGISTRY_BACKUP_FILE = os.path.join(BASE_DIR, "channels_registry.backup.json")


def load_registry() -> dict:
    with REGISTRY_LOCK:
        for candidate in (REGISTRY_FILE, REGISTRY_BACKUP_FILE):
            if not os.path.isfile(candidate):
                continue
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    raw = f.read().strip()
                if not raw:
                    continue
                data = json.loads(raw)
                if candidate == REGISTRY_BACKUP_FILE:
                    with open(REGISTRY_FILE, "w", encoding="utf-8") as wf:
                        json.dump(data, wf, ensure_ascii=False, indent=2)
                return _enforce_10_channel_profile_isolation(data)
            except Exception:
                continue
        return {"global_settings": {"max_channels_per_pc": MAX_CHANNELS_PER_PC}, "channels": []}


def save_registry(data: dict) -> None:
    with REGISTRY_LOCK:
        tmp_path = f"{REGISTRY_FILE}.tmp_{os.getpid()}"
        serialized = json.dumps(data, ensure_ascii=False, indent=2)
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(serialized)
            os.replace(tmp_path, REGISTRY_FILE)
            if data.get("channels"):
                with open(REGISTRY_BACKUP_FILE, "w", encoding="utf-8") as bf:
                    bf.write(serialized)
        except Exception:
            try:
                with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                    f.write(serialized)
            except Exception:
                pass
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


def get_channel_by_id(channel_id: str) -> dict:
    reg = load_registry()
    for ch in reg.get("channels", []):
        if ch.get("channel_id") == channel_id:
            return ch
    return {}


def update_channel_state(channel_id: str, updates: dict) -> None:
    reg = load_registry()
    for ch in reg.get("channels", []):
        if ch.get("channel_id") == channel_id:
            ch.update(updates)
            break
    save_registry(reg)


PERSONA_ENGINE = YouTubePersonaEngine(state_callback=update_channel_state)
BG_VIDEO_ENGINE = BackgroundVideoProductionEngine(emit_log_fn=PERSONA_ENGINE.emit_log)
PARALLEL_COORDINATOR = ParallelSplitScreenCoordinator(
    persona_engine=PERSONA_ENGINE,
    bg_video_engine=BG_VIDEO_ENGINE,
    emit_log_fn=PERSONA_ENGINE.emit_log,
)
AI_SUPERVISOR = AISupervisorWatchdog(
    get_channels_fn=lambda: load_registry().get("channels", []),
    emit_log_fn=PERSONA_ENGINE.emit_log,
    persona_engine=PERSONA_ENGINE,
)


def read_channel_logs(channel_id: str, max_lines: int = 60) -> list:
    log_file = os.path.join(LOGS_DIR, f"{channel_id}.log")
    if not os.path.isfile(log_file):
        return ["[Hệ thống AI] Phòng ban đã nạp Master DNA 20 Điểm và sẵn sàng suy nghĩ điều hành."]
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]
    return lines[-max_lines:]


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tập Đoàn Agent AI Đa Kênh YouTube — Command Center (Port 8077)</title>
<style>
  :root {
    --bg: #0b0f19;
    --panel: #131a2a;
    --panel-2: #1a2438;
    --border: #283552;
    --accent: #3b82f6;
    --accent-2: #10b981;
    --warn: #f59e0b;
    --danger: #ef4444;
    --purple: #8b5cf6;
    --text: #f1f5f9;
    --muted: #94a3b8;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    display: flex;
    height: 100vh;
    overflow: hidden;
  }
  .sidebar {
    width: 330px;
    background: var(--panel);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }
  .brand {
    padding: 16px 18px;
    border-bottom: 1px solid var(--border);
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  }
  .brand h1 { font-size: 15px; font-weight: 700; color: #60a5fa; letter-spacing: 0.3px; }
  .brand p { font-size: 11.5px; color: var(--muted); margin-top: 4px; }
  .dept-list { padding: 12px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 10px; }
  .dept-card {
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .dept-card:hover { border-color: var(--accent); }
  .dept-card.active {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent), 0 6px 20px rgba(59,130,246,0.18);
  }
  .dept-title { font-size: 13.5px; font-weight: 700; color: #fff; margin-bottom: 4px; }
  .dept-meta { font-size: 11.5px; color: var(--muted); display: flex; justify-content: space-between; margin-top: 6px; flex-wrap: wrap; gap: 4px; }
  .badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10.5px;
    font-weight: 600;
  }
  .badge-idle { background: rgba(148,163,184,0.15); color: #cbd5e1; }
  .badge-run { background: rgba(16,185,129,0.2); color: #34d399; }
  .badge-tab { background: rgba(59,130,246,0.2); color: #93c5fd; }

  .main { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 16px 20px; gap: 14px; }
  .top-header {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }
  .top-info h2 { font-size: 17px; color: #fff; }
  .top-info p { font-size: 12px; color: var(--muted); margin-top: 3px; }
  .top-stats { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .stat-pill {
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 7px 11px;
    font-size: 12px;
  }
  .stat-pill strong { color: #38bdf8; }

  .thought-banner {
    background: linear-gradient(90deg, rgba(139,92,246,0.16) 0%, rgba(59,130,246,0.12) 100%);
    border: 1px solid #7c3aed;
    border-radius: 10px;
    padding: 11px 15px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .thought-title { font-size: 11px; font-weight: 700; color: #c4b5fd; text-transform: uppercase; letter-spacing: 0.5px; }
  .thought-body { font-size: 13px; color: #f8fafc; line-height: 1.45; font-weight: 500; }

  .action-bar { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn {
    border: none;
    border-radius: 8px;
    padding: 9px 13px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    color: #fff;
    background: var(--accent);
    transition: opacity 0.15s;
  }
  .btn:hover { opacity: 0.9; }
  .btn-green { background: var(--accent-2); }
  .btn-warn { background: var(--warn); color: #111827; }
  .btn-danger { background: var(--danger); }
  .btn-purple { background: var(--purple); }
  .btn-outline { background: var(--panel-2); border: 1px solid var(--border); color: var(--text); }

  .section-title { font-size: 12.5px; font-weight: 700; color: #93c5fd; text-transform: uppercase; letter-spacing: 0.5px; }

  .channel-vault-card {
    background: var(--panel);
    border: 1px solid #3b82f6;
    border-radius: 12px;
    padding: 14px 16px;
    display: grid;
    grid-template-columns: 1fr 1.1fr;
    gap: 14px;
  }
  .vault-kv { font-size: 12px; line-height: 1.65; color: #e2e8f0; }
  .vault-kv span.lbl { color: var(--muted); }
  .vault-box {
    background: #080c14;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 11.8px;
    max-height: 185px;
    overflow-y: auto;
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .desks-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 9px;
  }
  .desk-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px;
    position: relative;
  }
  .desk-card.active-desk {
    border-color: var(--accent-2);
    background: rgba(16,185,129,0.08);
    box-shadow: 0 0 15px rgba(16,185,129,0.18);
  }
  .desk-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
  .desk-num { font-size: 11.5px; font-weight: 700; color: #60a5fa; }
  .desk-desc { font-size: 11px; color: var(--muted); line-height: 1.38; }

  .bottom-grid {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 14px;
  }
  .card-box {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 9px;
  }
  .log-box {
    background: #070a12;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    font-family: Consolas, monospace;
    font-size: 11.8px;
    color: #a7f3d0;
    height: 190px;
    overflow-y: auto;
    line-height: 1.5;
  }
  .evo-list { list-style: none; display: flex; flex-direction: column; gap: 5px; }
  .evo-list li {
    background: var(--panel-2);
    border-left: 3px solid var(--purple);
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 11.5px;
    line-height: 1.4;
  }
  textarea, input[type="text"], input[type="password"], select.form-select {
    width: 100%;
    background: #090d16;
    border: 1px solid var(--border);
    color: var(--text);
    padding: 8px 10px;
    border-radius: 7px;
    font-size: 12px;
  }
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(5, 8, 16, 0.78);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    backdrop-filter: blur(4px);
  }
  .modal-card {
    background: var(--panel);
    border: 1px solid #3b82f6;
    border-radius: 14px;
    width: 560px;
    max-width: 94vw;
    padding: 18px 20px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.65);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .modal-card h3 { font-size: 15px; color: #fff; }
  .form-group { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: #cbd5e1; }
</style>
</head>
<body>

  <!-- MODAL 1: CẤU HÌNH MODEL AI ĐIỀU KHIỂN (PC APP MODAL) -->
  <div class="modal-overlay" id="aiConfigModal">
    <div class="modal-card">
      <h3>🤖 Cấu Hình Bộ Não Model AI Điều Khiển (Chống Lặp 30 Phiên)</h3>
      <div class="form-group">
        <label>1. Chế độ Model AI điều khiển:</label>
        <select id="modalAiProvider" class="form-select">
          <option value="AUTO">AUTO — Tự động (Antigravity ➔ Gemini/OpenAI API ➔ ChatGPT Web ➔ Markov 30 Phiên)</option>
          <option value="GEMINI_API">GEMINI_API — Google Gemini 2.5 Flash (Khuyên dùng khi mang sang PC khác)</option>
          <option value="OPENAI_API">OPENAI_API — OpenAI GPT-4o-mini / DeepSeek API</option>
          <option value="CHATGPT_WEB">CHATGPT_WEB — Tài khoản ChatGPT Web đang đăng nhập</option>
          <option value="OLLAMA_LOCAL">OLLAMA_LOCAL — Model AI Offline trên máy (127.0.0.1:11434)</option>
        </select>
      </div>
      <div class="form-group">
        <label>2. Gemini API Key (Lưu trực tiếp vào CHANNELS_DATA/ai_model_config.json):</label>
        <input type="password" id="modalGeminiKey" placeholder="Dán Gemini API Key (AIzaSy...) — Để trống nếu giữ nguyên" />
      </div>
      <div class="form-group">
        <label>3. OpenAI / DeepSeek API Key (Tùy chọn):</label>
        <input type="password" id="modalOpenaiKey" placeholder="Dán sk-... — Để trống nếu giữ nguyên" />
      </div>
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:4px;">
        <button class="btn btn-outline" onclick="closeModals()">Hủy</button>
        <button class="btn btn-green" onclick="saveAiConfigFromModal()">💾 Lưu Cấu Hình Model AI</button>
      </div>
    </div>
  </div>

  <!-- MODAL 2: THÊM PHÒNG BAN / KEY KÊNH MỚI (TỐI ĐA 10 KÊNH / 1 MÁY) -->
  <div class="modal-overlay" id="addChannelModal">
    <div class="modal-card">
      <h3>➕ Thêm Phòng Ban / Kênh Mới (Giới Hạn Tối Ưu: Tối Đa 10 Kênh / 1 Máy)</h3>
      <div class="form-group">
        <label>1. Tên Phòng Ban / Kênh Mới:</label>
        <input type="text" id="modalNewDeptName" placeholder="Ví dụ: Phòng Ban #04 — Kênh Bà Cô Mexico (Doña Drama)" />
      </div>
      <div class="form-group">
        <label>2. Thị trường & Ngôn ngữ của Key (Tự động đổi Múi giờ, Báo chí, Google Maps & Studio):</label>
        <select id="modalNewLang" class="form-select" onchange="onNewLangChange()">
          <option value="ja">🇯🇵 Nhật Bản (ja — Tokyo GMT+9, Yahoo! Japan News, Google Maps Nhật)</option>
          <option value="en">🇺🇸 Hoa Kỳ (en — New York EST, USA News, Google Maps US)</option>
          <option value="es">🇲🇽 Mexico (es-MX — Ciudad de México, El Universal, Google Maps México)</option>
        </select>
      </div>
      <div class="form-group">
        <label>3. Bộ Từ Khóa Gốc Của Key (Cách nhau bằng dấu phẩy — Dùng cho Google Alerts, Search & Lọc Video):</label>
        <input type="text" id="modalNewSeeds" value="熟年離婚 漫画, シニア 人生劇場, 定年後 ドラマ" />
      </div>
      <div class="form-group">
        <label>4. Thư Mục Chứa Các Tập Video Để Hàng Đợi Tự Động Upload:</label>
        <div style="display:flex;gap:6px;">
          <input type="text" id="modalNewQueueDir" value="D:\KEY NHẬT\20-30" />
          <button class="btn btn-outline" style="white-space:nowrap;" onclick="browseFolderForInput('modalNewQueueDir')">📂 Chọn Folder...</button>
        </div>
      </div>
      <div class="form-group">
        <label>5. Proxy Riêng Cho Profile Kênh Này (Tùy chọn — Để trống nếu dùng Mạng Gốc; hỗ trợ IP:Port hoặc IP:Port:User:Pass):</label>
        <input type="text" id="modalNewProxy" placeholder="Ví dụ: 103.22.33.44:8080:myuser:mypass hoặc http://user:pass@ip:port (Để trống nếu không dùng)" />
      </div>
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:4px;">
        <button class="btn btn-outline" onclick="closeModals()">Hủy</button>
        <button class="btn btn-green" onclick="submitNewChannelFromModal()">🚀 Tạo Phòng Ban & Profile Riêng</button>
      </div>
    </div>
  </div>

  <!-- MODAL 3: GẮN / SỬA PROXY & KIỂM TRA ĐỊA CHỈ IP RIÊNG CỦA PROFILE KÊNH -->
  <div class="modal-overlay" id="proxyConfigModal">
    <div class="modal-card">
      <h3>🌐 Cấu Hình Proxy & Kiểm Tra IP Riêng Cho Profile Kênh</h3>
      <div style="font-size:11.5px;color:#93c5fd;line-height:1.45;">
        🛡️ <strong>Cô lập tuyệt đối 1 Profile = 1 Kênh:</strong> Mỗi kênh có thư mục Chrome Profile riêng và gắn Proxy độc lập (tự động tạo Extension xác thực <code>user:pass</code> và khóa chống rò rỉ WebRTC IP).
      </div>
      <div class="form-group">
        <label>Nhập Proxy cho kênh hiện tại (Để trống để dùng Mạng Gốc Direct IP):</label>
        <input type="text" id="modalChannelProxyInput" placeholder="Hỗ trợ: IP:Port | IP:Port:User:Pass | http://user:pass@IP:Port | socks5://IP:Port" />
      </div>
      <div class="vault-box" id="proxyTestResultBox" style="max-height:95px;font-size:11.5px;color:#34d399;">
        Bấm 「🔍 Kiểm Tra Kết Nối Proxy / IP」 để xem địa chỉ IP thực tế, Quốc gia, Thành phố và Độ trễ (ms).
      </div>
      <div style="display:flex;justify-content:space-between;gap:8px;margin-top:4px;flex-wrap:wrap;">
        <button class="btn btn-outline" onclick="testProxyInModal()">🔍 Kiểm Tra Kết Nối Proxy / IP</button>
        <div style="display:flex;gap:8px;">
          <button class="btn btn-outline" onclick="closeModals()">Đóng</button>
          <button class="btn btn-green" onclick="saveProxyFromModal()">💾 Lưu Proxy Cho Kênh Này</button>
        </div>
      </div>
    </div>
  </div>

  <!-- MODAL 4: QUẢN LÝ BẢN QUYỀN MÃ KEY KÍCH HOẠT & TRÌNH TẠO MÃ KEY CHO KHÁCH (ADMIN KEYGEN) -->
  <div class="modal-overlay" id="licenseManagerModal">
    <div class="modal-card" style="width:680px;max-height:90vh;overflow-y:auto;">
      <h3>🔑 Kích Hoạt Bản Quyền Phần Mềm & Trình Tạo Mã Key Cho Khách (HMAC-SHA256)</h3>
      <div class="vault-box" id="licenseCurrentStatusBox" style="max-height:110px;font-size:11.5px;color:#34d399;">
        Đang tải thông tin bản quyền máy hiện tại...
      </div>
      <div class="form-group">
        <label>Nhập Mã Key Kích Hoạt Bản Quyền (`YTES-...`) hoặc Mã Mở Khóa Gói Ngách (`ADDON-KEY-...`):</label>
        <div style="display:flex;gap:8px;">
          <input type="text" id="inputActivateLicenseKey" placeholder="Ví dụ: YTES-VIP10-10C-20271104-ALL-VIP001-XXXX hoặc ADDON-KEY-JP-K1-MANGA" />
          <button class="btn btn-green" style="flex-shrink:0;" onclick="activateLicenseKeyNow()">✅ Kích Hoạt Ngay</button>
        </div>
      </div>
      <div id="licenseActivateMsg" style="font-size:11.5px;color:#fbbf24;"></div>

      <div style="margin-top:8px;padding-top:10px;border-top:1px solid var(--border);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <strong style="font-size:12.5px;color:#c084fc;">👑 DÀNH CHO CHỦ PHẦN MỀM: TẠO MÃ KEY KÍCH HOẠT MỚI CHO KHÁCH</strong>
          <button class="btn btn-outline" style="padding:3px 8px;font-size:11px;" onclick="openKeysMarkdownFile()">📄 Mở Bảng Tổng Hợp Key (.md)</button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;">
          <div class="form-group">
            <label>Gói Bản Quyền:</label>
            <select id="keygenTierSelect">
              <option value="VIP10">💎 VIP10 (10 Kênh)</option>
              <option value="PRO5">🚀 PRO5 (5 Kênh)</option>
              <option value="TRIAL3">🌱 TRIAL3 (3 Kênh)</option>
              <option value="MASTER">👑 MASTER (Admin)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Số Kênh Tối Đa:</label>
            <select id="keygenMaxChannels">
              <option value="10" selected>10 Kênh / 1 Máy</option>
              <option value="5">5 Kênh / 1 Máy</option>
              <option value="3">3 Kênh / 1 Máy</option>
              <option value="1">1 Kênh / 1 Máy</option>
            </select>
          </div>
          <div class="form-group">
            <label>Thời Hạn (Ngày):</label>
            <select id="keygenValidDays">
              <option value="365" selected>365 Ngày (1 Năm)</option>
              <option value="180">180 Ngày (6 Tháng)</option>
              <option value="30">30 Ngày (1 Tháng)</option>
              <option value="7">7 Ngày (Dùng thử)</option>
              <option value="36500">Trọn Đời (Lifetime)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Phạm Vi Ngách & Mã Khách:</label>
            <input type="text" id="keygenCustomerTag" value="KHACH01" placeholder="Mã khách (VD: KHACH01)" />
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">
          <select id="keygenNicheScope" style="width:62%;">
            <option value="ALL" selected>🌐 Mở Khóa Tất Cả Các Gói Key Ngách (ALL)</option>
            <option value="JPK1">🇯🇵 Chỉ Mở Khóa Nhóm Key Nhật Bản (JPK1)</option>
            <option value="USMX">🇺🇸🇲🇽 Chỉ Mở Khóa Nhóm Key Mỹ & Mexico (USMX)</option>
          </select>
          <button class="btn btn-purple" onclick="adminGenerateNewCustomerKey()">⚡ Tạo Mã Key Mới Cho Khách</button>
        </div>
        <div class="vault-box" id="adminGeneratedKeysListBox" style="max-height:145px;font-size:11px;margin-top:8px;">
          Đang tải danh sách Mã Key Kích Hoạt đã tạo...
        </div>
      </div>
      <div style="display:flex;justify-content:flex-end;margin-top:6px;">
        <button class="btn btn-outline" onclick="closeModals()">Đóng</button>
      </div>
    </div>
  </div>

  <!-- MODAL 5: KHO ĐA KEY NGÁCH ("MỖI KEY 1 CÁCH VIẾT KỊCH BẢN & EDIT VIDEO RIÊNG") -->
  <div class="modal-overlay" id="nicheRecipeModal">
    <div class="modal-card" style="width:720px;max-height:90vh;overflow-y:auto;">
      <h3>🎬 Kho Đa Key Ngách: Mỗi Key 1 Cách Viết Kịch Bản & Edit Video Riêng</h3>
      <div style="font-size:11.5px;color:#93c5fd;line-height:1.45;">
        Mỗi Kênh được gắn 1 <strong>Gói Key Ngách (`niche_recipe_key`)</strong> độc lập quy định rõ: <strong>Công thức viết Tiêu đề & Kịch bản riêng</strong> + <strong>Công thức dựng & Edit Video FFmpeg riêng</strong>. Khi bạn thêm Key mới và đẩy lên GitHub OTA, toàn bộ máy khách sẽ nhận được ngay!
      </div>
      <div class="form-group" style="margin-top:4px;">
        <label>Chọn Gói Key Kịch Bản & Cách Edit Video áp dụng cho Kênh đang chọn:</label>
        <div style="display:flex;gap:8px;">
          <select id="modalChannelNicheRecipeSelect" onchange="previewSelectedNicheRecipeInModal()"></select>
          <button class="btn btn-green" style="flex-shrink:0;" onclick="saveChannelNicheRecipeFromModal()">💾 Áp Dụng Key Ngách Này Cho Kênh</button>
        </div>
      </div>
      <div class="vault-box" id="nicheRecipeDetailPreviewBox" style="max-height:155px;font-size:11.5px;color:#e2e8f0;">
        Đang tải chi tiết công thức Kịch bản & Edit Video của Key ngách...
      </div>

      <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);">
        <strong style="font-size:12px;color:#34d399;">➕ THÊM / CẬP NHẬT GÓI KEY NGÁCH MỚI (TÍCH HỢP CÔNG THỨC KỊCH BẢN & EDIT RIÊNG):</strong>
        <div style="display:grid;grid-template-columns:1fr 1.4fr 0.6fr;gap:8px;margin-top:6px;">
          <input type="text" id="newNicheKeyId" placeholder="Mã Key (VD: KEY_JP_CEO_DRAMA)" />
          <input type="text" id="newNicheName" placeholder="Tên Ngách (VD: 🇯🇵 Key Nhật: Chủ Tịch Giả Nghèo)" />
          <select id="newNicheLang">
            <option value="ja">🇯🇵 Tiếng Nhật (ja)</option>
            <option value="en">🇺🇸 Tiếng Anh (en)</option>
            <option value="es">🇲🇽 Tây Ban Nha (es)</option>
          </select>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px;">
          <input type="text" id="newNicheScriptStyle" placeholder="Phong cách Kịch bản & Độ dài (VD: 7 Phần • 50.000 ký tự)" />
          <input type="text" id="newNicheTitleDna" placeholder="Công thức Tiêu đề & Cấu trúc (DNA)" />
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px;">
          <input type="text" id="newNicheEditStyle" placeholder="Cách Edit Video (VD: 10 cảnh đầu Veo3 + Ảnh Manga 5s)" />
          <input type="text" id="newNicheEffectsRule" placeholder="Hiệu ứng Camera/Âm thanh (VD: Ken Burns + Nhạc Piano -24dB)" />
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
          <span id="newNicheSaveStatus" style="font-size:11.5px;color:#34d399;"></span>
          <div style="display:flex;gap:8px;">
            <button class="btn btn-purple" onclick="addCustomNicheRecipeFromModal()">➕ Lưu Gói Key Ngách Mới Vào Kho</button>
            <button class="btn btn-outline" onclick="closeModals()">Đóng</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- MODAL 6: CẬP NHẬT TỪ XA QUA GITHUB OTA (KHÔNG CẦN TẢI LẠI ỨNG DỤNG) -->
  <div class="modal-overlay" id="otaUpdaterModal">
    <div class="modal-card" style="width:650px;">
      <h3>☁️ Cập Nhật Tính Năng & Gói Key Mới Từ Xa Qua GitHub (OTA Hot-Update)</h3>
      <div style="font-size:11.5px;color:#93c5fd;line-height:1.45;">
        Hệ thống kết nối trực tiếp tới kho GitHub chính thức (<code>phamngocthu661-lang/youtube-enterprise-studio</code>). Khách hàng chỉ cần bấm <strong>「🔄 Cập Nhật Ngay」</strong> là ứng dụng tự tải các tính năng mới và các Gói Key Kịch bản/Edit mới về máy mà <strong>không cần tải lại bộ cài `.exe`</strong> và <strong>giữ nguyên 100% dữ liệu kênh/Profile</strong>!
      </div>
      <div class="vault-box" id="otaStatusResultBox" style="max-height:165px;font-size:11.5px;color:#34d399;">
        Bấm 「🔍 Kiểm Tra Phiên Bản Mới Trên GitHub」 để kiểm tra...
      </div>
      <div style="margin-top:6px;padding-top:8px;border-top:1px solid var(--border);">
        <strong style="font-size:11.5px;color:#c084fc;">🚀 DÀNH CHO CHỦ PHẦN MỀM (ĐẨY BẢN NÂNG CẤP MỚI LÊN GITHUB CHO KHÁCH CẬP NHẬT):</strong>
        <div style="display:flex;gap:8px;margin-top:5px;">
          <input type="text" id="otaAdminCommitMsg" placeholder="Nhập ghi chú bản cập nhật (VD: Thêm Key Ngách mới & nâng cấp tính năng...)" />
          <button class="btn btn-purple" style="flex-shrink:0;" onclick="adminPublishUpdateToGithubNow()">🚀 Đẩy Lên GitHub (Publish OTA)</button>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;gap:8px;margin-top:8px;flex-wrap:wrap;">
        <div style="display:flex;gap:8px;">
          <button class="btn btn-outline" onclick="checkOtaUpdateNow()">🔍 Kiểm Tra Phiên Bản Mới Trên GitHub</button>
          <button class="btn btn-green" onclick="applyOtaUpdateNow()">🔄 Tải & Cập Nhật Tính Năng Mới Ngay (Không Tải Lại App)</button>
        </div>
        <button class="btn btn-outline" onclick="closeModals()">Đóng</button>
      </div>
    </div>
  </div>

  <div class="sidebar">
    <div class="brand">
      <h1>🖥️ YOUTUBE STUDIO PC APP</h1>
      <p>Ứng Dụng Desktop <strong id="appVersionBadge" style="color:#38bdf8;">v3.9.0</strong> • Tối Ưu Chuẩn <strong>Tối Đa 10 Kênh / 1 Máy</strong> • Hỗ Trợ Cập Nhật Từ Xa Qua GitHub OTA</p>
      <div style="margin-top:6px;font-size:11.5px;color:#34d399;font-weight:600;" id="pcSlotCapacityText">📊 Công suất máy: Đang tải... / 10 Kênh</div>
      <div style="margin-top:3px;font-size:11px;color:#fcd34d;font-weight:600;" id="sidebarLicenseBadge">🔑 Bản quyền: Đang kiểm tra...</div>
      <button class="btn btn-green" id="btnAddChannelSlot" style="width:100%;margin-top:8px;justify-content:center;font-size:11.5px;" onclick="addNewChannelKeyPrompt()">➕ Thêm Kênh / Key Mới (Nhật • Mỹ • Mexico)</button>
    </div>
    <div class="dept-list" id="deptList"></div>
  </div>

  <div class="main">
    <div class="top-header">
      <div class="top-info">
        <h2 id="curDeptName">Đang tải...</h2>
        <p id="curDeptMeta">Folder Kênh: ... | Profile: ...</p>
      </div>
      <div class="top-stats">
        <div class="stat-pill" style="cursor:pointer;border-color:#f59e0b;" onclick="openLicenseModal()">🔑 Bản Quyền: <strong id="statLicenseTier" style="color:#fcd34d;">MASTER</strong></div>
        <div class="stat-pill" style="cursor:pointer;border-color:#10b981;" onclick="openOtaModal()">☁️ OTA: <strong id="statOtaVersion" style="color:#34d399;">v3.9.0</strong></div>
        <div class="stat-pill">🤖 AI Brain: <strong id="statAiBrain">AUTO</strong></div>
        <div class="stat-pill">🔐 Đăng nhập: <strong id="statLogin">Kiểm tra...</strong></div>
        <div class="stat-pill">🛡️ TabGuard: <strong id="statTabs">0 / 1 Tab</strong></div>
        <div class="stat-pill">📺 Tiến độ Phiên: <strong id="statQuota">0 / 8 Bước</strong></div>
        <div class="stat-pill">⚡ Trạng thái: <strong id="statStatus">IDLE</strong></div>
        <button class="btn btn-danger" style="padding:6px 10px;font-size:11.5px;" onclick="quitPcApp()">📴 Thoát App</button>
      </div>
    </div>

    <div class="thought-banner">
      <div class="thought-title">🧠 LUỒNG SUY NGHĨ & QUYẾT ĐỊNH HIỆN TẠI CỦA AGENT AI (REAL-TIME AI COGNITIVE REASONING):</div>
      <div class="thought-body" id="aiThoughtBox">Đang tải luồng suy nghĩ của AI...</div>
    </div>

    <div class="action-bar">
      <button class="btn btn-green" onclick="openGmailLogin()">🔑 1. Mở Chrome Đăng Nhập Gmail & Kênh</button>
      <button class="btn" style="background:#0ea5e9;" onclick="verifyLoginNow()">🔐 Xác Nhận Đã Đăng Nhập Chưa</button>
      <button class="btn btn-warn" onclick="scanChannelAndAnalytics()">📊 2. Quét Kênh & Lấy Thông Số Studio</button>
      <button class="btn btn-outline" onclick="openChannelFolder()">📂 Mở Folder Kênh</button>
      <button class="btn btn-outline" style="border-color:#10b981;color:#6ee7b7;" onclick="openReadyVideosFolder()">📥 Mở Folder Bỏ Video Sẵn (.mp4)</button>
      <button class="btn btn-outline" style="border-color:#38bdf8;color:#bae6fd;" onclick="openProxyModal()">🌐 Gắn / Kiểm Tra Proxy & IP</button>
      <button class="btn btn-outline" style="border-color:#f59e0b;color:#fde68a;" onclick="openNicheRecipeModal()">🎬 Chọn Key Kịch Bản & Cách Edit Riêng</button>
      <button class="btn btn-outline" style="border-color:#ec4899;color:#fbcfe8;" onclick="openLicenseModal()">🔑 Mã Key Bản Quyền & Tạo Key</button>
      <button class="btn btn-outline" style="border-color:#22c55e;color:#bbf7d0;" onclick="openOtaModal()">☁️ Cập Nhật Từ Xa (GitHub OTA)</button>
      <button class="btn btn-outline" style="border-color:#a855f7;color:#e9d5ff;" onclick="configureAiModelPrompt()">🤖 Cấu Hình Model AI</button>
      <button class="btn btn-purple" onclick="startWarmup(false, 'GMAIL_ONLY')">📧 Nuôi Gmail & Hệ Sinh Thái (Mail + Báo + Search + Maps ~12p)</button>
      <button class="btn" style="background:#2563eb;" onclick="startWarmup(false, 'YOUTUBE_DEEP_ONLY')">📺 Chỉ Nuôi Kênh (Xem Sâu 3–7p & Bình Luận ~28p)</button>
      <button class="btn" onclick="startWarmup(false, 'FULL_OMNI')">🌐 Nuôi Kết Hợp Toàn Diện (Gmail + Báo + Maps + Kênh ~40p)</button>
      <button class="btn btn-outline" onclick="startWarmup(true, 'YOUTUBE_DEEP_ONLY')">⚡ Test Nhanh (9s)</button>
      <button class="btn btn-danger" onclick="stopChannel()">⏹️ Dừng</button>
    </div>

    <!-- HỒ SƠ KÊNH THẬT & THÔNG SỐ HÀNG NGÀY (FOLDER RIÊNG CỦA TỪNG KÊNH) -->
    <div class="channel-vault-card">
      <div class="vault-kv">
        <div class="section-title" style="margin-bottom:6px;">📁 HỒ SƠ KÊNH THẬT, CHROME PROFILE & PROXY RIÊNG CỦA KÊNH</div>
        <div><span class="lbl">• Chrome Profile cô lập (1 Kênh/1 Profile):</span> <strong id="vaultProfileDir" style="color:#fcd34d;">...</strong></div>
        <div><span class="lbl">• Proxy & Địa chỉ IP của Profile:</span> <strong id="vaultProxyStatus" style="color:#38bdf8;">...</strong></div>
        <div><span class="lbl">• Gói Key Kịch Bản & Cách Edit Video của Kênh:</span> <strong id="vaultNicheRecipe" style="color:#f472b6;">...</strong></div>
        <div><span class="lbl">• Thư mục dữ liệu riêng của kênh:</span> <strong id="vaultFolder" style="color:#93c5fd;">...</strong></div>
        <div><span class="lbl">• Cổng Xác Thực Đăng Nhập (Pre-Flight Gate):</span> <strong id="vaultLogin">...</strong></div>
        <div><span class="lbl">• Tên kênh thật quét được:</span> <strong id="vaultTitle" style="color:#34d399;">...</strong> (<span id="vaultHandle">...</span>)</div>
        <div><span class="lbl">• Subscribers & Số lượng Video:</span> <strong id="vaultSubs">...</strong> | <strong id="vaultVids">...</strong></div>
        <div><span class="lbl">• Lần quét thông số gần nhất:</span> <span id="vaultLastScan">...</span></div>
      </div>
      <div>
        <div class="section-title" style="margin-bottom:6px;">📈 BÁO CÁO PHÂN TÍCH THÔNG SỐ & KẾ HOẠCH PHÁT TRIỂN HÀNG NGÀY (DO AI LẬP)</div>
        <div class="vault-box" id="vaultGrowthPlan">Bấm nút 「📊 2. Quét Kênh & Lấy Thông Số Studio」 để AI quét toàn bộ thông số kênh thật và lập kế hoạch phát triển hôm nay.</div>
      </div>
    </div>

    <!-- TÁCH BIỆT 2 NHÁNH ĐỘC LẬP: (A) ĐẨY VIDEO LÊN TRƯỚC & HẸN GIỜ PUBLIC vs (B) NUÔI KÊNH & GMAIL ĐỘC LẬP -->
    <div class="channel-vault-card" style="grid-template-columns: 1.22fr 0.78fr;">
      <!-- NHÁNH A: ĐẨY VIDEO LÊN TRƯỚC & SETUP GIỜ PUBLIC (PRE-UPLOAD & SCHEDULE) -->
      <div style="display:flex;flex-direction:column;gap:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
          <span class="section-title">📤 PHẦN 1 (ĐỘC LẬP): ĐẨY VIDEO LÊN TRƯỚC & SETUP GIỜ PUBLIC (<span id="queueSummaryText" style="color:#34d399;">Đang quét...</span>)</span>
          <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
            <button class="btn btn-outline" id="btnToggleAutoPreUpload" style="padding:4px 8px;font-size:11px;" onclick="toggleAutoPreUpload()">🟣 Tự Động Đẩy Trước: TẮT</button>
            <button class="btn btn-outline" style="padding:4px 8px;font-size:11px;border-color:#10b981;color:#6ee7b7;" onclick="openReadyVideosFolder()">📥 Bỏ Video Sẵn (.mp4)</button>
            <button class="btn btn-outline" style="padding:4px 8px;font-size:11px;" onclick="changeBatchQueueDirPrompt()">📂 Đổi Folder Nguồn</button>
          </div>
        </div>

        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;background:#090d16;padding:7px 10px;border-radius:8px;border:1px solid var(--border);font-size:11.5px;">
          <span>🎬 <strong>Nguồn Video:</strong></span>
          <select id="videoSourceModeSelect" onchange="saveUploadScheduleSettings()" style="width:auto;padding:3px 7px;font-size:11px;">
            <option value="USER_SUPPLIED">📥 Tôi Cung Cấp Video Sẵn (Chuẩn máy nuôi 10 kênh)</option>
            <option value="HYBRID_AUTO">🔄 Linh Hoạt (Ưu tiên Video tôi cấp ➔ Tự sản xuất)</option>
            <option value="SELF_PRODUCED">⚙️ Tự Sản Xuất Video Trên Máy Này</option>
          </select>
          <span>⏰ <strong>Đẩy lên trước lúc:</strong></span>
          <input type="text" id="preUploadTriggerInput" value="13:30" style="width:58px;padding:3px 6px;font-size:11px;text-align:center;" />
          <span>🌟 <strong>Giờ Public:</strong></span>
          <input type="text" id="scheduledPublishTimeInput" value="20:00" style="width:58px;padding:3px 6px;font-size:11px;text-align:center;" />
          <button class="btn btn-outline" style="padding:3px 8px;font-size:11px;" onclick="saveUploadScheduleSettings()">💾 Lưu Giờ</button>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap;">
          <div style="font-size:11px;color:#94a3b8;">
            Folder Quét: <code id="queueDirText" style="color:#93c5fd;">D:\KEY NHẬT\20-30</code> + <code>08_READY_VIDEOS_TO_UPLOAD</code>
          </div>
          <div style="display:flex;gap:6px;align-items:center;">
            <select id="uploadVisibilitySelect" style="width:auto;background:#090d16;color:#f1f5f9;border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:11.5px;">
              <option value="SCHEDULE" selected>📅 Đẩy Lên Trước & Hẹn Giờ Public (Schedule — Khuyên dùng)</option>
              <option value="PRIVATE">🔒 Đẩy Lên Trước ở Chế Độ Riêng Tư (Private)</option>
              <option value="PUBLIC">🌐 Xuất Bản Công Khai Ngay + Ghim Comment (Public)</option>
            </select>
            <button class="btn btn-green" style="padding:5px 10px;font-size:11.5px;" onclick="uploadNextPendingEpisode()">📤 Đẩy Tập Tiếp Theo Lên Trước & Hẹn Giờ</button>
          </div>
        </div>

        <div class="vault-box" id="batchQueueListBox" style="max-height:125px;font-size:11.5px;">Đang tải danh sách các tập video sẵn sàng đẩy lên trước...</div>
      </div>

      <!-- NHÁNH B: NUÔI KÊNH & NUÔI GMAIL ĐỘC LẬP -->
      <div style="display:flex;flex-direction:column;gap:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
          <span class="section-title">🌿 PHẦN 2 (ĐỘC LẬP): TỰ ĐỘNG NUÔI KÊNH & GMAIL</span>
          <div style="display:flex;gap:6px;align-items:center;">
            <select id="autoWarmupModeSelect" onchange="saveUploadScheduleSettings()" style="width:auto;padding:3px 7px;font-size:11px;">
              <option value="FULL_OMNI">🌐 Nuôi Kết Hợp (Gmail + Báo + Maps + Kênh ~40p)</option>
              <option value="YOUTUBE_DEEP_ONLY">📺 Chỉ Nuôi Kênh (Xem Sâu 3–7p & Comment ~28p)</option>
              <option value="GMAIL_ONLY">📧 Nuôi Gmail & Hệ Sinh Thái (Mail + Báo + Search + Maps ~12p)</option>
            </select>
            <button class="btn btn-outline" id="btnToggleAutopilot" style="padding:4px 9px;font-size:11px;" onclick="toggleAutopilot()">🟢 Tự Động Nuôi: TẮT</button>
          </div>
        </div>
        <div class="vault-box" id="gmailAndAutopilotBox" style="max-height:175px;font-size:11.5px;">Đang tải trạng thái Cổng Đăng Nhập, Nuôi Gmail & Nuôi Kênh...</div>
      </div>
    </div>

    <!-- [v3.8] PHẦN 3 & 4: BẢNG TÍNH TOÁN LỘ TRÌNH TRONG NGÀY + CHẠY SONG SONG CHIA ĐÔI MÀN HÌNH + AI GIÁM SÁT TIẾN ĐỘ 24/7 -->
    <div class="channel-vault-card" style="grid-template-columns: 1.15fr 0.85fr;">
      <!-- PHẦN 3: BẢNG TÍNH TOÁN LỘ TRÌNH THỜI GIAN TRONG NGÀY & ĐIỀU PHỐI SONG SONG CHIA ĐÔI MÀN HÌNH -->
      <div style="display:flex;flex-direction:column;gap:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
          <span class="section-title">📐 PHẦN 3: BẢNG TÍNH TOÁN LỘ TRÌNH TRONG NGÀY & CHẠY SONG SONG CHIA ĐÔI MÀN HÌNH (<span id="timelineSummaryBadge" style="color:#34d399;">Đang tính...</span>)</span>
          <div style="display:flex;gap:6px;align-items:center;">
            <button class="btn btn-outline" style="padding:3px 8px;font-size:11px;" onclick="openTimelineMarkdownFile()">📄 Xem File Lộ Trình (.md)</button>
            <button class="btn btn-purple" style="padding:3px 8px;font-size:11px;" onclick="startBackgroundVideoProduction()">🎬⚡ Tự Sản Xuất Video Ngầm Ngay</button>
          </div>
        </div>

        <div style="display:flex;gap:7px;align-items:center;flex-wrap:wrap;background:#090d16;padding:7px 10px;border-radius:8px;border:1px solid var(--border);font-size:11.5px;">
          <span>🖥️ <strong>Màn Hình Trái (LEFT 50%):</strong></span>
          <select id="splitLeftChannelSelect" style="width:auto;padding:3px 7px;font-size:11px;"></select>
          <span>🖥️ <strong>Màn Hình Phải (RIGHT 50%):</strong></span>
          <select id="splitRightChannelSelect" style="width:auto;padding:3px 7px;font-size:11px;"></select>
          <label style="display:inline-flex;align-items:center;gap:4px;cursor:pointer;color:#93c5fd;">
            <input type="checkbox" id="chkAlsoProduceVideoBg" checked style="width:auto;" />
            <span>+ Vừa nuôi vừa Tạo Video ngầm</span>
          </label>
        </div>

        <div style="display:flex;gap:6px;flex-wrap:wrap;">
          <button class="btn btn-green" style="padding:5px 10px;font-size:11.5px;" onclick="runDualSplitScreenWarmup('GMAIL_ONLY')">📧⚡ Nuôi 2 Gmail Cùng Lúc (Chia Đôi Màn Hình)</button>
          <button class="btn" style="background:#2563eb;padding:5px 10px;font-size:11.5px;" onclick="runDualSplitScreenWarmup('YOUTUBE_DEEP_ONLY')">📺⚡ Nuôi 2 Kênh Cùng Lúc (Chia Đôi Màn Hình)</button>
          <button class="btn btn-warn" style="padding:5px 10px;font-size:11.5px;" onclick="runAllChannelsInPairs('GMAIL_ONLY')">🚀 Chạy Toàn Bộ Các Cặp (Nuôi Gmail Đôi)</button>
          <button class="btn btn-purple" style="padding:5px 10px;font-size:11.5px;" onclick="runAllChannelsInPairs('YOUTUBE_DEEP_ONLY')">🚀 Chạy Toàn Bộ Các Cặp (Nuôi Kênh Đôi + Tạo Video Ngầm)</button>
        </div>

        <div class="vault-box" id="dailyMasterTimelineBox" style="max-height:150px;font-size:11.5px;">Đang tính toán lộ trình Tạo Video + Đăng Video + Nuôi Kênh trong ngày...</div>
      </div>

      <!-- PHẦN 4: AI GIÁM SÁT TIẾN ĐỘ LIÊN TỤC 24/7 & TỰ ĐỘNG KHẮC PHỤC LỖI (AI SUPERVISOR WATCHDOG) -->
      <div style="display:flex;flex-direction:column;gap:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
          <span class="section-title">🛡️ PHẦN 4: AI GIÁM SÁT TIẾN ĐỘ & TỰ KHẮC PHỤC LỖI 24/7 (<span id="supervisorStatusBadge" style="color:#34d399;">ĐANG BẬT</span>)</span>
          <button class="btn btn-outline" style="padding:3px 8px;font-size:11px;border-color:#38bdf8;color:#bae6fd;" onclick="runAiSupervisorCheckNow()">🛠️ Quét & Khắc Phục Lỗi Ngay</button>
        </div>
        <div class="vault-box" id="aiSupervisorWatchdogBox" style="max-height:225px;font-size:11.5px;">Đang tải trạng thái AI Supervisor Watchdog & Tài nguyên phần cứng...</div>
      </div>
    </div>

    <div class="section-title">ĐỘI HÌNH 7 BÀN AGENT TRONG PHÒNG BAN (KẾT NỐI D:\KEY NHẬT\AGENT + MASTER DNA 20 ĐIỂM)</div>
    <div class="desks-grid" id="desksGrid"></div>

    <div class="bottom-grid">
      <div class="card-box">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span class="section-title">📟 NHẬT KÝ TƯ DUY AI, QUÉT KÊNH & KIỂM ĐỊNH TRANSCRIPT (MM:SS)</span>
          <button class="btn btn-outline" style="padding:4px 9px;font-size:11px;" onclick="refreshState()">🔄 Làm mới</button>
        </div>
        <div class="log-box" id="logBox"></div>

        <div style="background:var(--panel-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border);">
          <div style="font-size:11.5px;font-weight:700;color:#38bdf8;margin-bottom:4px;">💬 BÌNH LUẬN MỚI NHẤT DO AI TỰ SUY NGHĨ (ĐỌC TRANSCRIPT CÓ MỐC MM:SS):</div>
          <div id="latestCommentBox" style="font-size:12px;color:#e2e8f0;line-height:1.45;">
            Chưa có bình luận trong phiên này.
          </div>
        </div>
      </div>

      <div class="card-box">
        <span class="section-title">🧬 BÀN #7: AI COMMUNITY RESEARCH LOOP & TIẾN HÓA KỊCH BẢN</span>
        <div style="font-size:11.5px;color:var(--muted);">
          Đã phân tích <strong id="evoCount" style="color:#fff;">0</strong> bình luận & <strong id="evoPolls" style="color:#38bdf8;">0</strong> khảo sát Community Tab
        </div>
        <div style="font-size:11.5px;font-weight:700;color:#c084fc;margin-top:2px;">📌 Luật Tiêu đề đang áp dụng (Bàn #2):</div>
        <ul class="evo-list" id="evoTitleList"></ul>
        <div style="font-size:11.5px;font-weight:700;color:#34d399;margin-top:4px;">📌 Luật Kịch bản 20–25 phút đang áp dụng (Bàn #3):</div>
        <ul class="evo-list" id="evoScriptList"></ul>

        <div style="margin-top:4px;display:flex;flex-direction:column;gap:6px;">
          <textarea id="manualFeedbackInput" rows="2" placeholder="Dán bình luận khán giả hoặc kết quả Poll để AI phân tích nâng cấp..."></textarea>
          <button class="btn btn-purple" onclick="submitAudienceFeedback()">🧬 Để AI Phân Tích Góp Ý & Nâng Cấp Tiêu Đề + Kịch Bản</button>
        </div>
      </div>
    </div>
  </div>

<script>
let selectedChannelId = 'DEPT_01_JAPAN_K1';
let cachedChannels = [];
let cachedNicheRecipes = [];
let cachedLicenseState = {};
let cachedAdminKeysVault = {};
let cachedOtaManifest = {};

const DESKS_CONFIG = [
  { id: 1, icon: '👤', name: 'Bàn #1: Agent_Persona_Warmup', desc: 'AI quan sát màn hình thực tế, tự suy nghĩ chọn nguồn (Trang chủ, Tìm kiếm, Cột bên phải) đúng 4 trụ A/B/C/D Kênh 1, né chủ đề Kênh 2, khóa ≤ 2 Tab.' },
  { id: 2, icon: '🔍', name: 'Bàn #2: k1-title-planner', desc: 'Áp dụng công thức 【漫画】AGE + ACTION + CONSEQUENCE + LESSON, ưu tiên ハローワーク / シルバー人材センター / 60歳 再雇用 + Duplicate Guard.' },
  { id: 3, icon: '✍️', name: 'Bàn #3: k1-script-writer & auditor', desc: 'Kịch bản 20–25 phút (7.500–8.500 ký tự), OLD BELIEF -> COLLISION -> EXPERIMENT -> NEW BELIEF, kiểm định độc lập ≥ 96/100.' },
  { id: 4, icon: '🎬', name: 'Bàn #4: k1-v192-5a-producer', desc: 'Sản xuất Voice 3900 tự nhiên, 10 cảnh đầu 100% Veo3 + 90% ảnh Seinen Manga (50-60% B-roll giấu mặt) + Render GPU NVENC.' },
  { id: 5, icon: '🎨', name: 'Bàn #5: k1-seo-packaging', desc: 'Xuất K1_SEO_MASTER.docx kèm 3 ảnh Thumbnail A/B/C thật (16:9) chuẩn CTR cao cho khán giả Nhật 60–70+.' },
  { id: 6, icon: '📊', name: 'Bàn #6: Studio Scanner & Publisher', desc: 'Quét thông tin kênh & thông số YouTube Studio hàng ngày lưu vào Folder riêng; Upload Video, Hẹn giờ & Ghim bình luận.' },
  { id: 7, icon: '🧬', name: 'Bàn #7: Community Research Loop', desc: 'AI đọc kết quả Poll & Comment thật trên kênh để tìm pain point mới nạp ngược về Bàn #2 & Bàn #3.' }
];

async function refreshState() {
  try {
    const res = await fetch('/api/status?channel_id=' + encodeURIComponent(selectedChannelId));
    const data = await res.json();
    cachedChannels = data.channels || [];
    cachedNicheRecipes = data.niche_recipes || [];
    cachedLicenseState = data.license_state || {};
    cachedAdminKeysVault = data.admin_keys_vault || {};
    cachedOtaManifest = data.ota_version_manifest || {};
    renderSidebar();
    renderMain(data);
  } catch (e) { console.error(e); }
}

function renderSidebar() {
  const capEl = document.getElementById('pcSlotCapacityText');
  if (capEl) {
    capEl.innerText = `📊 Công suất máy: ${cachedChannels.length} / 10 Kênh (Mỗi Kênh 1 Profile Riêng)`;
    capEl.style.color = cachedChannels.length >= 10 ? '#fbbf24' : '#34d399';
  }
  const addBtn = document.getElementById('btnAddChannelSlot');
  if (addBtn) {
    if (cachedChannels.length >= 10) {
      addBtn.innerText = '🔒 Đã Đạt Giới Hạn Tối Đa (10/10 Kênh)';
      addBtn.style.opacity = '0.6';
    } else {
      addBtn.innerText = `➕ Thêm Kênh Mới (Slot #${cachedChannels.length + 1}/10)`;
      addBtn.style.opacity = '1';
    }
  }
  const box = document.getElementById('deptList');
  box.innerHTML = cachedChannels.map((ch, idx) => {
    const isAct = ch.channel_id === selectedChannelId;
    const isRun = ch.status && ch.status !== 'IDLE' && ch.status !== 'STOPPED';
    const logged = ch.logged_in ? '✅ Đã ĐN' : '⚠️ Chưa ĐN';
    const hasProxy = ch.proxy && ch.proxy.trim();
    const proxyBadge = hasProxy ? '🌐 Có Proxy' : '🏠 IP Gốc';
    return `
      <div class="dept-card ${isAct ? 'active' : ''}" onclick="selectChannel('${ch.channel_id}')">
        <div class="dept-title">[#${idx + 1}/10] ${escapeHtml(ch.department_name)}</div>
        <div style="font-size:11.5px;color:#93c5fd;">${escapeHtml(ch.detected_channel_title || ch.channel_title)}</div>
        <div class="dept-meta">
          <span class="badge ${isRun ? 'badge-run' : 'badge-idle'}">${logged} • ${escapeHtml(ch.status || 'IDLE')}</span>
          <span class="badge badge-tab">Port ${ch.cdp_port} • ${proxyBadge}</span>
        </div>
      </div>
    `;
  }).join('');
}

function renderMain(data) {
  const ch = (cachedChannels || []).find(c => c.channel_id === selectedChannelId) || cachedChannels[0];
  if (!ch) return;

  const summary = data.channel_summary || {};
  const idInfo = summary.identity || {};
  const isLogged = Boolean(idInfo.logged_in || ch.logged_in);

  document.getElementById('curDeptName').innerText = ch.department_name;
  document.getElementById('curDeptMeta').innerText = `Folder Kênh: ${summary.channel_folder || ch.channel_data_dir || ch.channel_folder} | Profile Chrome: ${ch.profile_dir}`;
  document.getElementById('statLogin').innerText = isLogged ? 'ĐÃ ĐĂNG NHẬP ✅' : 'CHƯA ĐĂNG NHẬP ⚠️';
  document.getElementById('statLogin').style.color = isLogged ? '#34d399' : '#fbbf24';
  document.getElementById('statTabs').innerText = `${ch.open_tabs_count || 0} / 1 Tab`;
  document.getElementById('statQuota').innerText = `${ch.today_watched_count || 0} / ${ch.today_target_quota || 8} Bước`;
  document.getElementById('statStatus').innerText = ch.status || 'IDLE';
  const aiCfg = data.ai_model_config || {};
  const memCnt = data.ai_session_memory_count || 0;
  const aiEl = document.getElementById('statAiBrain');
  if (aiEl) {
    aiEl.innerText = `${aiCfg.provider || 'AUTO'} (${memCnt} phiên nhớ)`;
  }
  document.getElementById('aiThoughtBox').innerText = ch.last_ai_thought || 'Sẵn sàng quan sát màn hình và suy nghĩ thao tác tiếp theo...';

  const profEl = document.getElementById('vaultProfileDir');
  if (profEl) {
    profEl.innerText = `${ch.profile_dir} (Port CDP: ${ch.cdp_port})`;
  }
  const prxEl = document.getElementById('vaultProxyStatus');
  if (prxEl) {
    const rawPrx = (ch.proxy || '').trim();
    const verIp = (ch.last_verified_ip || '').trim();
    if (rawPrx) {
      prxEl.innerText = `🌐 Đang gắn Proxy: ${rawPrx}` + (verIp ? ` | ✅ ${verIp}` : ' (Bấm 🌐 Gắn / Kiểm Tra Proxy để xác thực IP)');
      prxEl.style.color = '#34d399';
    } else {
      prxEl.innerText = `🏠 Mạng Gốc (Direct IP)` + (verIp ? ` | ${verIp}` : ' — Có thể gắn Proxy riêng bất cứ lúc nào');
      prxEl.style.color = '#38bdf8';
    }
  }
  const lic = data.license_state || {};
  const licBadge = document.getElementById('sidebarLicenseBadge');
  if (licBadge && lic.tier_code) {
    licBadge.innerText = `🔑 Bản quyền: ${lic.tier_code} (Tối đa ${lic.max_channels || 10} Kênh • Hạn: ${lic.expires_display || 'TRỌN ĐỜI'})`;
  }
  const topLic = document.getElementById('statLicenseTier');
  if (topLic && lic.tier_code) {
    topLic.innerText = `${lic.tier_code} (${lic.max_channels || 10}K)`;
  }
  const otaM = data.ota_version_manifest || {};
  const topOta = document.getElementById('statOtaVersion');
  if (topOta && otaM.version) {
    topOta.innerText = `v${otaM.version} (${otaM.total_niche_recipes || 8} Key Ngách)`;
  }
  const nicheRec = data.selected_channel_niche_recipe || {};
  const nicheEl = document.getElementById('vaultNicheRecipe');
  if (nicheEl && nicheRec.niche_name) {
    const sf = nicheRec.script_formula || {};
    const ef = nicheRec.video_edit_formula || {};
    nicheEl.innerText = `${nicheRec.niche_name} | ✍️ Kịch bản: ${sf.style_name || ''} | 🎞️ Edit: ${ef.edit_style_name || ''}`;
  }
  document.getElementById('vaultFolder').innerText = summary.channel_folder || ch.channel_data_dir || ch.channel_folder || '';
  document.getElementById('vaultLogin').innerText = isLogged
    ? `ĐÃ ĐĂNG NHẬP ✅ (${idInfo.gmail_account || idInfo.account_display_name || 'Đã xác thực session'})`
    : 'CHƯA ĐĂNG NHẬP ⚠️ (Hãy bấm nút số 1 để mở cửa sổ Chrome đăng nhập)';
  document.getElementById('vaultLogin').style.color = isLogged ? '#34d399' : '#fbbf24';
  document.getElementById('vaultTitle').innerText = idInfo.detected_channel_title || ch.channel_title || 'Chưa xác định';
  document.getElementById('vaultHandle').innerText = idInfo.detected_handle || 'Chưa có @handle';
  document.getElementById('vaultSubs').innerText = `Subscribers: ${idInfo.subscribers_text || 'Chưa quét'}`;
  document.getElementById('vaultVids').innerText = `Video: ${idInfo.videos_count_text || (summary.videos_count + ' video')}`;
  document.getElementById('vaultLastScan').innerText = idInfo.last_scanned_at || 'Chưa quét';
  if (summary.growth_plan_preview) {
    document.getElementById('vaultGrowthPlan').innerText = summary.growth_plan_preview;
  }

  const activeDesk = ch.active_desk || 0;
  document.getElementById('desksGrid').innerHTML = DESKS_CONFIG.map(d => `
    <div class="desk-card ${activeDesk === d.id ? 'active-desk' : ''}">
      <div class="desk-head">
        <span class="desk-num">${d.icon} ${d.name}</span>
        <span class="badge ${activeDesk === d.id ? 'badge-run' : 'badge-idle'}">${activeDesk === d.id ? 'ĐANG TƯ DUY' : 'Sẵn sàng'}</span>
      </div>
      <div class="desk-desc">${d.desc}</div>
    </div>
  `).join('');

  const logs = data.logs || [];
  const logBox = document.getElementById('logBox');
  logBox.innerHTML = logs.map(l => `<div>${escapeHtml(l)}</div>`).join('');
  logBox.scrollTop = logBox.scrollHeight;

  if (ch.last_generated_comment) {
    const c = ch.last_generated_comment;
    document.getElementById('latestCommentBox').innerHTML = `
      <div><strong>Mốc thời gian:</strong> <span style="color:#34d399;">${escapeHtml(c.timestamp)}</span> | <strong>Sắc thái:</strong> <span style="color:#c084fc;">${escapeHtml(c.style)}</span></div>
      <div style="font-size:11.5px;color:#cbd5e1;margin:3px 0;">🧠 <em>Suy nghĩ AI:</em> ${escapeHtml(c.ai_thought || '')}</div>
      <div style="font-size:11.5px;color:#94a3b8;margin:3px 0;">Trích đoạn Transcript: "${escapeHtml(c.referenced_line)}"</div>
      <div style="margin-top:4px;color:#fff;font-weight:600;">"${escapeHtml(c.comment_text)}"</div>
    `;
  }

  const evo = data.evolution || {};
  document.getElementById('evoCount').innerText = evo.harvested_comments_count || 0;
  document.getElementById('evoPolls').innerText = evo.community_polls_analyzed || 0;
  document.getElementById('evoTitleList').innerHTML = (evo.title_upgrade_directives || []).map(x => `<li>${escapeHtml(x)}</li>`).join('');
  document.getElementById('evoScriptList').innerHTML = (evo.script_upgrade_directives || []).map(x => `<li>${escapeHtml(x)}</li>`).join('');

  // Render Hàng Đợi Tập Video (Batch Folder Queue theo từng Key)
  const bq = data.batch_queue || {};
  const qDirEl = document.getElementById('queueDirText');
  if (qDirEl) {
    qDirEl.innerText = bq.parent_batch_dir || ch.batch_queue_dir || 'D:\\KEY NHẬT\\20-30';
  }
  const qSum = document.getElementById('queueSummaryText');
  if (qSum) {
    qSum.innerText = `Tổng: ${bq.total_episodes || 0} tập | Đã đăng: ${bq.uploaded_count || 0} | Chờ đăng: ${bq.pending_count || 0}`;
  }
  const bqBox = document.getElementById('batchQueueListBox');
  if (bqBox && bq.episodes) {
    bqBox.innerHTML = bq.episodes.map(ep => {
      const isUp = ep.status === 'UPLOADED';
      const upInfo = ep.uploaded_info || {};
      const schedTag = upInfo.scheduled_display ? ` ⏰ Hẹn: ${escapeHtml(upInfo.scheduled_display)}` : '';
      const srcBadge = ep.source_type === 'USER_DROP_FOLDER' ? '<span style="color:#6ee7b7;font-size:10px;">[Video Cấp Sẵn]</span> ' : '';
      const badge = isUp
        ? `<span style="color:#34d399;font-weight:700;">✅ ĐÃ ĐẨY LÊN (${escapeHtml(upInfo.video_id || 'OK')}${schedTag})</span>`
        : `<span style="color:#fbbf24;font-weight:700;">⏳ SẴN SÀNG ĐẨY TRƯỚC</span>`;
      const actionBtn = isUp
        ? (upInfo.youtube_url ? `<a href="${escapeHtml(upInfo.youtube_url)}" target="_blank" style="color:#60a5fa;text-decoration:none;font-size:11px;">🔗 Xem Video</a>` : '')
        : `<button class="btn btn-outline" style="padding:2px 7px;font-size:10.5px;" onclick="uploadSpecificEpisode('${escapeHtml(ep.episode_id)}')">📤 Đẩy Trước & Hẹn Giờ</button>`;
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;border-bottom:1px dashed rgba(255,255,255,0.07);gap:6px;">
        <div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
          ${srcBadge}<strong>Tập ${escapeHtml(ep.episode_id)}:</strong> ${badge} • <span style="color:#cbd5e1;">${escapeHtml((ep.parsed_title || '').slice(0, 40))}...</span>
          <span style="color:#94a3b8;font-size:10.5px;">(${ep.tags_count || 0} tags, ${ep.has_srt ? 'có .srt' : 'no srt'}, ${ep.video_size_mb || 0} MB)</span>
        </div>
        <div style="flex-shrink:0;">${actionBtn}</div>
      </div>`;
    }).join('');
  }

  // Render Trạng thái Tách Biệt: (A) Tự động Đẩy Video Lên Trước & Hẹn Giờ vs (B) Tự động Nuôi Kênh & Gmail
  const gm = data.gmail_trust_state || {};
  const ap = data.autopilot_schedule || {};
  const gmBox = document.getElementById('gmailAndAutopilotBox');
  const btnAp = document.getElementById('btnToggleAutopilot');
  const autoWarmOn = Boolean(ap.auto_warmup_enabled || ap.autopilot_enabled);
  const autoPreUpOn = Boolean(ap.auto_pre_upload_enabled || ap.auto_daily_upload_from_queue_enabled);
  if (btnAp) {
    btnAp.innerText = autoWarmOn ? '🟢 Tự Động Nuôi: ĐANG BẬT' : '⚪ Tự Động Nuôi: ĐANG TẮT';
    btnAp.style.borderColor = autoWarmOn ? '#10b981' : '#475569';
    btnAp.style.color = autoWarmOn ? '#34d399' : '#cbd5e1';
  }
  const btnPreUp = document.getElementById('btnToggleAutoPreUpload');
  if (btnPreUp) {
    btnPreUp.innerText = autoPreUpOn ? '🟣 Tự Động Đẩy Trước: ĐANG BẬT' : '⚪ Tự Động Đẩy Trước: ĐANG TẮT';
    btnPreUp.style.borderColor = autoPreUpOn ? '#a855f7' : '#475569';
    btnPreUp.style.color = autoPreUpOn ? '#e9d5ff' : '#cbd5e1';
  }
  const vSrcSel = document.getElementById('videoSourceModeSelect');
  if (vSrcSel && document.activeElement !== vSrcSel && ap.video_source_mode) {
    vSrcSel.value = ap.video_source_mode;
  }
  const wModeSel = document.getElementById('autoWarmupModeSelect');
  if (wModeSel && document.activeElement !== wModeSel && ap.warmup_mode) {
    wModeSel.value = ap.warmup_mode;
  }
  const preTrigInp = document.getElementById('preUploadTriggerInput');
  if (preTrigInp && document.activeElement !== preTrigInp && ap.pre_upload_trigger_time) {
    preTrigInp.value = ap.pre_upload_trigger_time;
  }
  const pubTimeInp = document.getElementById('scheduledPublishTimeInput');
  if (pubTimeInp && document.activeElement !== pubTimeInp && ap.scheduled_publish_time) {
    pubTimeInp.value = ap.scheduled_publish_time;
  }

  if (gmBox) {
    const alertsOk = gm.google_alerts_subscribed ? '✅ Đã đăng ký (Nhận thư mới hàng ngày)' : '⚠️ Chưa đăng ký';
    gmBox.innerHTML = `
      <div>• <strong>Cổng Kiểm Tra Đăng Nhập Trước Tác Vụ:</strong> <span style="color:#34d399;">🛡️ ĐANG BẬT 100% (Tự động chặn nếu chưa đăng nhập)</span></div>
      <div>• <strong>Thống kê Nuôi Gmail & Hệ Sinh Thái (~12p/phiên: Mail + Báo + Search + Maps):</strong> Đã chạy <strong>${gm.total_gmail_warmup_sessions || 0}</strong> phiên | Đọc <strong>${gm.total_emails_read || 0}</strong> thư | Click <strong>${gm.total_links_clicked_in_emails || 0}</strong> link | ⭐: <strong>${gm.total_starred_emails || 0}</strong> | Alerts: <span style="color:${gm.google_alerts_subscribed ? '#34d399' : '#fbbf24'};">${alertsOk}</span></div>
      <div style="margin-top:4px;padding-top:4px;border-top:1px solid rgba(255,255,255,0.08);">
        • <strong>Nhánh 1 — Tự động NUÔI (${escapeHtml(ap.warmup_mode || 'FULL_OMNI')}):</strong> <strong style="color:${autoWarmOn ? '#34d399' : '#94a3b8'};">${autoWarmOn ? 'ĐANG BẬT' : 'ĐANG TẮT'}</strong>
        (Sáng: <code>${escapeHtml(ap.today_morning_trigger_time || '09:30')}</code> | Chiều: <code>${escapeHtml(ap.today_afternoon_trigger_time || '15:30')}</code>)
      </div>
      <div>
        • <strong>Nhánh 2 — Tự động ĐẨY VIDEO TRƯỚC & HẸN GIỜ:</strong> <strong style="color:${autoPreUpOn ? '#c084fc' : '#94a3b8'};">${autoPreUpOn ? 'ĐANG BẬT' : 'ĐANG TẮT'}</strong>
        (Đẩy trước lúc: <code>${escapeHtml(ap.pre_upload_trigger_time || '13:30')}</code> ➔ Hẹn Public: <code>${escapeHtml(ap.scheduled_publish_time || '20:00')}</code>)
      </div>
      <div>• <strong>Lần chạy gần nhất:</strong> Nuôi: <span>${escapeHtml(ap.last_triggered_at || 'Chưa chạy')}</span> | Đẩy Video: <span>${escapeHtml(ap.last_pre_upload_at || 'Chưa đẩy')}</span></div>
    `;
  }

  // [v3.8] Render Dropdown chọn cặp kênh Chia Đôi Màn Hình (LEFT & RIGHT)
  const leftSel = document.getElementById('splitLeftChannelSelect');
  const rightSel = document.getElementById('splitRightChannelSelect');
  if (leftSel && rightSel && cachedChannels.length > 0) {
    const prevLeft = leftSel.value || selectedChannelId;
    const defaultRightChannel = cachedChannels.find(c => c.channel_id !== prevLeft) || cachedChannels[0];
    const prevRight = rightSel.value || (defaultRightChannel ? defaultRightChannel.channel_id : '');
    if (document.activeElement !== leftSel) {
      leftSel.innerHTML = cachedChannels.map((c, i) => `<option value="${c.channel_id}">[#${i + 1}] ${escapeHtml(c.department_name.slice(0, 28))} (Port ${c.cdp_port})</option>`).join('');
      leftSel.value = prevLeft;
    }
    if (document.activeElement !== rightSel) {
      rightSel.innerHTML = cachedChannels.map((c, i) => `<option value="${c.channel_id}">[#${i + 1}] ${escapeHtml(c.department_name.slice(0, 28))} (Port ${c.cdp_port})</option>`).join('');
      rightSel.value = prevRight;
    }
  }

  // [v3.8] Render Bảng Tính Toán Lộ Trình Thời Gian Trong Ngày (DailyMasterTimelineCalculator)
  const tl = data.daily_master_timeline || {};
  const par = tl.parallel_split_screen_totals || {};
  const seq = tl.sequential_1_window_totals || {};
  const prog = tl.today_completion_progress || {};
  const tlBadge = document.getElementById('timelineSummaryBadge');
  if (tlBadge && par.total_screen_active_hours_str) {
    tlBadge.innerText = `Tổng màn hình: ${par.total_screen_active_hours_str} (Tiết kiệm ${par.time_saved_pct || 0}% thời gian)`;
  }
  const tlBox = document.getElementById('dailyMasterTimelineBox');
  if (tlBox && tl.schedule_slots) {
    const slotsHtml = (tl.schedule_slots || []).map(s => {
      const stColor = s.slot_status === 'ACTIVE' ? '#34d399' : (s.slot_status === 'PASSED' ? '#64748b' : '#fbbf24');
      return `<div style="padding:3px 0;border-bottom:1px dashed rgba(255,255,255,0.07);">
        <strong style="color:${stColor};">[${escapeHtml(s.time_range)}]</strong> <strong>${escapeHtml(s.phase)}:</strong><br/>
        <span style="color:#93c5fd;">${escapeHtml(s.left_screen)}</span> | <span style="color:#c084fc;">${escapeHtml(s.right_screen)}</span><br/>
        <span style="color:#6ee7b7;font-size:10.5px;">${escapeHtml(s.background_task)}</span>
      </div>`;
    }).join('');
    tlBox.innerHTML = `
      <div style="margin-bottom:5px;padding-bottom:5px;border-bottom:1px solid rgba(255,255,255,0.1);">
        • <strong>So sánh (${tl.total_channels || 0} kênh):</strong> Chạy đơn tuần tự mất <strong>${escapeHtml(seq.grand_total_hours_str || '...')}</strong> ➔
        Chạy <strong>Chia Đôi Màn Hình + Tạo Video Ngầm</strong> chỉ mất <strong style="color:#34d399;">${escapeHtml(par.total_screen_active_hours_str || '...')}</strong>
        (Nuôi Gmail đôi: <code>${par.gmail_total_min || 0}p</code> | Nuôi Kênh đôi: <code>${par.youtube_1_session_min || 0}p/ca</code> | Đẩy Video trước: <code>${par.pre_upload_total_min || 0}p</code> | Tự tạo ngầm: <code>~${par.videos_auto_produced_in_background_during_warmup || 0} video</code>).<br/>
        • <strong>Tiến độ hoàn thành nhiệm vụ hôm nay:</strong> Đã nuôi <strong>${prog.warmup_completed_channels || 0}/${tl.total_channels || 0}</strong> kênh | Đã đẩy video <strong>${prog.upload_completed_channels || 0}/${tl.total_channels || 0}</strong> kênh | Hàng đợi sẵn sàng: <strong>${prog.ready_videos_in_queue_total || 0}</strong> video (Đạt <strong style="color:#34d399;">${prog.overall_completion_pct || 0}%</strong>).
      </div>
      ${slotsHtml}
    `;
  }

  // [v3.8] Render AI Giám Sát Tiến Độ 24/7 & Tự Động Khắc Phục Lỗi (AISupervisorWatchdog + BackgroundVideoProductionEngine)
  const sup = data.ai_supervisor || {};
  const hw = sup.hardware || {};
  const bgVid = data.bg_video_production || {};
  const supBox = document.getElementById('aiSupervisorWatchdogBox');
  if (supBox) {
    const jobsMap = bgVid.jobs || {};
    const curJob = jobsMap[selectedChannelId];
    const jobLine = curJob
      ? `<div>• <strong>Luồng Sản Xuất Video Ngầm (${escapeHtml(curJob.episode_id)}):</strong> <strong style="color:#c084fc;">${escapeHtml(curJob.status)} (${curJob.progress_pct || 0}% - ${escapeHtml(curJob.stage)})</strong></div>`
      : `<div>• <strong>Luồng Sản Xuất Video Ngầm:</strong> <span style="color:#34d399;">Sẵn sàng chạy song song khi đang nuôi Gmail/Kênh</span></div>`;
    const incList = (sup.recent_incidents || []).slice(0, 5).map(inc =>
      `<div style="font-size:10.5px;color:#fcd34d;margin-top:2px;">🛠️ [${escapeHtml((inc.timestamp || '').slice(11))}] <strong>${escapeHtml(inc.channel_id)}</strong> (${escapeHtml(inc.issue_type)}): ${escapeHtml(inc.action_taken)}</div>`
    ).join('') || '<div style="font-size:11px;color:#94a3b8;margin-top:2px;">✅ Chưa phát hiện sự cố treo Tab / lỗi Proxy / dừng Video nào.</div>';

    supBox.innerHTML = `
      <div>• <strong>Tài nguyên PC thời gian thực:</strong> RAM trống <strong style="color:#34d399;">${hw.ram_free_gb || 0} / ${hw.ram_total_gb || 0} GB</strong> (${hw.ram_used_pct || 0}%) | CPU: <strong>${hw.cpu_load_pct || 0}%</strong> | Trình duyệt mở: <strong>${hw.open_chrome_count || 0}</strong> cửa sổ</div>
      <div>• <strong>Đánh giá năng lực song song:</strong> Chia đôi 2 màn hình: <strong style="color:${hw.can_run_dual_split_screen ? '#34d399' : '#fbbf24'};">${hw.can_run_dual_split_screen ? '✅ ĐỦ TÀI NGUYÊN' : '⚠️ TẢI CAO'}</strong> | Vừa nuôi vừa tạo video ngầm: <strong style="color:${hw.can_run_background_video_prod ? '#34d399' : '#fbbf24'};">${hw.can_run_background_video_prod ? '✅ MƯỢT MÀ' : '⚠️ TẠM HOÃN'}</strong></div>
      ${jobLine}
      <div>• <strong>AI Supervisor 24/7:</strong> Đã quét <strong>${sup.total_checks_run || 0}</strong> vòng (12s/lần) | Tự động khắc phục <strong style="color:#34d399;">${sup.total_issues_healed || 0}</strong> lỗi | Lần quét cuối: <code>${escapeHtml(sup.last_check_time || '...')}</code></div>
      <div style="margin-top:4px;padding-top:4px;border-top:1px solid rgba(255,255,255,0.08);color:#93c5fd;">${escapeHtml(sup.last_supervisor_thought || '')}</div>
      <div style="margin-top:4px;"><strong>Nhật ký AI Tự Khắc Phục Sự Cố (Self-Healing):</strong>${incList}</div>
    `;
  }
}

function selectChannel(id) { selectedChannelId = id; refreshState(); }

function runDualSplitScreenWarmup(mode = 'GMAIL_ONLY') {
  const leftId = (document.getElementById('splitLeftChannelSelect') ? document.getElementById('splitLeftChannelSelect').value : selectedChannelId) || selectedChannelId;
  const rightId = (document.getElementById('splitRightChannelSelect') ? document.getElementById('splitRightChannelSelect').value : '') || '';
  const bgVid = document.getElementById('chkAlsoProduceVideoBg') ? document.getElementById('chkAlsoProduceVideoBg').checked : true;
  postAction('run_dual_split_screen_warmup', {
    left_channel_id: leftId,
    right_channel_id: rightId,
    warmup_mode: mode,
    also_produce_video_in_bg: bgVid
  });
}

function runAllChannelsInPairs(mode = 'GMAIL_ONLY') {
  const bgVid = document.getElementById('chkAlsoProduceVideoBg') ? document.getElementById('chkAlsoProduceVideoBg').checked : true;
  postAction('run_all_channels_in_pairs', {
    warmup_mode: mode,
    also_produce_video_in_bg: bgVid
  });
}

function startBackgroundVideoProduction() {
  postAction('start_background_video_production');
}

function runAiSupervisorCheckNow() {
  postAction('run_ai_supervisor_check_now');
}

function openTimelineMarkdownFile() {
  postAction('open_timeline_markdown_file');
}

async function postAction(action, extra = {}) {
  const res = await fetch('/api/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, channel_id: selectedChannelId, ...extra })
  });
  const out = await res.json();
  refreshState();
  return out;
}

function openGmailLogin() { postAction('open_gmail_login'); }
function verifyLoginNow() { postAction('verify_login_now'); }
function scanChannelAndAnalytics() { postAction('scan_channel_and_analytics'); }
function openChannelFolder() { postAction('open_channel_folder'); }
function openReadyVideosFolder() { postAction('open_ready_videos_folder'); }
function aiSingleCognitiveStep() { postAction('ai_single_cognitive_step'); }
function startWarmup(demo, mode = 'FULL_OMNI') { postAction('start_warmup', { demo_fast_mode: demo, warmup_mode: mode }); }
function runOmniTask(taskType) { postAction(taskType); }
function testTranscriptComment() { postAction('test_transcript_comment'); }
function stopChannel() { postAction('stop_channel'); }

function uploadNextPendingEpisode() {
  const vis = document.getElementById('uploadVisibilitySelect').value || 'SCHEDULE';
  const pubTime = (document.getElementById('scheduledPublishTimeInput') ? document.getElementById('scheduledPublishTimeInput').value.trim() : '20:00') || '20:00';
  postAction('upload_next_pending_episode', { visibility_mode: vis, scheduled_publish_time: pubTime });
}

function uploadSpecificEpisode(epId) {
  const vis = document.getElementById('uploadVisibilitySelect').value || 'SCHEDULE';
  const pubTime = (document.getElementById('scheduledPublishTimeInput') ? document.getElementById('scheduledPublishTimeInput').value.trim() : '20:00') || '20:00';
  postAction('upload_specific_episode', { episode_id: epId, visibility_mode: vis, scheduled_publish_time: pubTime });
}

function toggleAutopilot() {
  postAction('toggle_autopilot');
}

function toggleAutoPreUpload() {
  postAction('toggle_auto_pre_upload');
}

function saveUploadScheduleSettings() {
  const vSrc = document.getElementById('videoSourceModeSelect') ? document.getElementById('videoSourceModeSelect').value : 'USER_SUPPLIED';
  const wMode = document.getElementById('autoWarmupModeSelect') ? document.getElementById('autoWarmupModeSelect').value : 'FULL_OMNI';
  const preTime = document.getElementById('preUploadTriggerInput') ? document.getElementById('preUploadTriggerInput').value.trim() : '13:30';
  const pubTime = document.getElementById('scheduledPublishTimeInput') ? document.getElementById('scheduledPublishTimeInput').value.trim() : '20:00';
  postAction('save_upload_schedule_settings', {
    video_source_mode: vSrc,
    warmup_mode: wMode,
    pre_upload_trigger_time: preTime,
    scheduled_publish_time: pubTime
  });
}

function closeModals() {
  document.getElementById('aiConfigModal').style.display = 'none';
  document.getElementById('addChannelModal').style.display = 'none';
  const pm = document.getElementById('proxyConfigModal');
  if (pm) pm.style.display = 'none';
  const lm = document.getElementById('licenseManagerModal');
  if (lm) lm.style.display = 'none';
  const nm = document.getElementById('nicheRecipeModal');
  if (nm) nm.style.display = 'none';
  const om = document.getElementById('otaUpdaterModal');
  if (om) om.style.display = 'none';
}

function openLicenseModal() {
  const lic = cachedLicenseState || {};
  const box = document.getElementById('licenseCurrentStatusBox');
  if (box) {
    box.innerHTML = `
      <div>• <strong>Gói Bản Quyền Đang Kích Hoạt:</strong> <strong style="color:#fcd34d;">${escapeHtml(lic.tier_label || 'MASTER')}</strong> | <strong>Mã Máy (HWID):</strong> <code>${escapeHtml(lic.hardware_id || '')}</code></div>
      <div>• <strong>Mã Key Hiện Tại:</strong> <code>${escapeHtml(lic.license_key || '')}</code></div>
      <div>• <strong>Quyền Hạn:</strong> Tối đa <strong>${lic.max_channels || 10} Kênh / 1 Máy</strong> | Thời hạn: <strong>${escapeHtml(lic.expires_display || 'TRỌN ĐỜI')}</strong> | Gói Key Ngách đã mở: <strong>${(lic.unlocked_niche_keys || []).length} / ${lic.total_available_niche_recipes || 8} Ngách</strong></div>
    `;
  }
  renderAdminKeysVaultList();
  document.getElementById('licenseManagerModal').style.display = 'flex';
}

function renderAdminKeysVaultList() {
  const kBox = document.getElementById('adminGeneratedKeysListBox');
  const keys = (cachedAdminKeysVault && cachedAdminKeysVault.keys) || [];
  if (!kBox) return;
  kBox.innerHTML = keys.map(k => `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;border-bottom:1px dashed rgba(255,255,255,0.08);">
      <div>
        <strong style="color:#c084fc;">[${escapeHtml(k.customer_tag)}]</strong>
        <strong>${escapeHtml(k.tier_code)} (${k.max_channels}K • ${escapeHtml(k.niche_scope)}):</strong>
        <code style="color:#34d399;user-select:all;">${escapeHtml(k.license_key)}</code>
        <span style="color:#94a3b8;font-size:10px;">(Hạn: ${escapeHtml(k.expires_display)})</span>
      </div>
    </div>
  `).join('');
}

async function activateLicenseKeyNow() {
  const raw = document.getElementById('inputActivateLicenseKey').value.trim();
  const msgEl = document.getElementById('licenseActivateMsg');
  if (!raw) return;
  msgEl.innerText = '⏳ Đang kiểm tra chữ ký bảo mật HMAC-SHA256 của Mã Key...';
  const out = await postAction('activate_license_key', { license_key: raw });
  if (out && out.ok) {
    msgEl.style.color = '#34d399';
    msgEl.innerText = out.message || '✅ Kích hoạt thành công!';
    document.getElementById('inputActivateLicenseKey').value = '';
    setTimeout(openLicenseModal, 350);
  } else {
    msgEl.style.color = '#f87171';
    msgEl.innerText = `❌ ${(out && out.error) || 'Mã Key không hợp lệ!'}`;
  }
}

async function adminGenerateNewCustomerKey() {
  const tier = document.getElementById('keygenTierSelect').value || 'VIP10';
  const maxCh = parseInt(document.getElementById('keygenMaxChannels').value || '10', 10);
  const days = parseInt(document.getElementById('keygenValidDays').value || '365', 10);
  const tag = document.getElementById('keygenCustomerTag').value.trim() || 'KHACH01';
  const scope = document.getElementById('keygenNicheScope').value || 'ALL';
  const out = await postAction('admin_generate_customer_key', {
    tier_code: tier,
    max_channels: maxCh,
    valid_days: days,
    customer_tag: tag,
    niche_scope: scope
  });
  if (out && out.ok && out.new_key) {
    const msgEl = document.getElementById('licenseActivateMsg');
    msgEl.style.color = '#34d399';
    msgEl.innerText = `🎉 Đã tạo Mã Key mới cho [${out.new_key.customer_tag}]: ${out.new_key.license_key}`;
    setTimeout(openLicenseModal, 300);
  }
}

function openKeysMarkdownFile() {
  postAction('open_keys_markdown_file');
}

function openNicheRecipeModal() {
  const ch = (cachedChannels || []).find(c => c.channel_id === selectedChannelId) || cachedChannels[0] || {};
  const sel = document.getElementById('modalChannelNicheRecipeSelect');
  if (sel && cachedNicheRecipes.length > 0) {
    sel.innerHTML = cachedNicheRecipes.map(r =>
      `<option value="${escapeHtml(r.niche_key)}">${escapeHtml(r.niche_name)} (${escapeHtml(r.niche_key)})</option>`
    ).join('');
    const curKey = ch.niche_recipe_key || (ch.language === 'ja' ? 'KEY_JP_K1_MANGA' : (ch.language === 'es' ? 'KEY_MX_DONA_FAMILIA' : 'KEY_US_MAFIA_MAID'));
    sel.value = curKey;
  }
  previewSelectedNicheRecipeInModal();
  document.getElementById('nicheRecipeModal').style.display = 'flex';
}

function previewSelectedNicheRecipeInModal() {
  const sel = document.getElementById('modalChannelNicheRecipeSelect');
  const box = document.getElementById('nicheRecipeDetailPreviewBox');
  if (!sel || !box) return;
  const r = (cachedNicheRecipes || []).find(x => x.niche_key === sel.value) || cachedNicheRecipes[0] || {};
  const sf = r.script_formula || {};
  const ef = r.video_edit_formula || {};
  box.innerHTML = `
    <div>• <strong>Mã Key Ngách:</strong> <code style="color:#f472b6;">${escapeHtml(r.niche_key || '')}</code> | <strong>Mã Mở Khóa Riêng (Add-on):</strong> <code style="color:#fcd34d;">${escapeHtml(r.unlock_addon_code || '')}</code></div>
    <div style="margin-top:4px;color:#93c5fd;">✍️ <strong>CÁCH VIẾT KỊCH BẢN RIÊNG (${escapeHtml(sf.style_name || '')}):</strong></div>
    <div>  + <strong>Độ dài mục tiêu:</strong> ${escapeHtml(sf.target_length || '')} | <strong>DNA Tiêu đề:</strong> ${escapeHtml(sf.title_dna || '')}</div>
    <div>  + <strong>Cấu trúc kịch bản:</strong> ${escapeHtml(sf.narrative_arc || '')}</div>
    <div style="margin-top:4px;color:#34d399;">🎞️ <strong>CÁCH DỰNG & EDIT VIDEO RIÊNG (${escapeHtml(ef.edit_style_name || '')}):</strong></div>
    <div>  + <strong>Quy tắc Mở đầu (Hook):</strong> ${escapeHtml(ef.opening_hook_rule || '')}</div>
    <div>  + <strong>Quy tắc Hình ảnh & Nhịp cắt:</strong> ${escapeHtml(ef.body_visual_rule || '')}</div>
    <div>  + <strong>Hiệu ứng Camera & Âm thanh:</strong> ${escapeHtml(ef.camera_and_effects || '')} | ${escapeHtml(ef.audio_and_tts || '')}</div>
  `;
}

async function saveChannelNicheRecipeFromModal() {
  const sel = document.getElementById('modalChannelNicheRecipeSelect');
  if (!sel) return;
  await postAction('save_channel_niche_recipe', { niche_recipe_key: sel.value });
  closeModals();
}

async function addCustomNicheRecipeFromModal() {
  const keyId = document.getElementById('newNicheKeyId').value.trim();
  const name = document.getElementById('newNicheName').value.trim();
  const lang = document.getElementById('newNicheLang').value || 'ja';
  const sStyle = document.getElementById('newNicheScriptStyle').value.trim();
  const tDna = document.getElementById('newNicheTitleDna').value.trim();
  const eStyle = document.getElementById('newNicheEditStyle').value.trim();
  const effRule = document.getElementById('newNicheEffectsRule').value.trim();
  const stEl = document.getElementById('newNicheSaveStatus');
  if (!keyId || !name) {
    if (stEl) stEl.innerText = '⚠️ Vui lòng nhập Mã Key và Tên Ngách!';
    return;
  }
  const out = await postAction('add_custom_niche_recipe', {
    niche_key: keyId,
    niche_name: name,
    language: lang,
    script_style_name: sStyle,
    title_dna: tDna,
    edit_style_name: eStyle,
    camera_and_effects: effRule
  });
  if (out && out.ok) {
    if (stEl) stEl.innerText = `✅ Đã lưu Gói Key Ngách mới (${out.recipe.niche_key})!`;
    setTimeout(openNicheRecipeModal, 350);
  }
}

function openOtaModal() {
  const m = cachedOtaManifest || {};
  const box = document.getElementById('otaStatusResultBox');
  if (box) {
    box.innerHTML = `
      <div>• <strong>Phiên bản hiện tại trên máy:</strong> <strong style="color:#38bdf8;">v${escapeHtml(m.version || '3.9.0')}</strong> (${escapeHtml(m.build_date || '')})</div>
      <div>• <strong>Kho GitHub OTA kết nối:</strong> <code>${escapeHtml(m.github_url || 'https://github.com/phamngocthu661-lang/youtube-enterprise-studio')}</code></div>
      <div>• <strong>Số Gói Key Ngách đã tích hợp:</strong> <strong>${m.total_niche_recipes || 8} Gói Key</strong></div>
      <div style="margin-top:4px;color:#cbd5e1;">📌 <em>Ghi chú bản phát hành:</em> ${escapeHtml(m.release_notes || '')}</div>
    `;
  }
  document.getElementById('otaUpdaterModal').style.display = 'flex';
}

async function checkOtaUpdateNow() {
  const box = document.getElementById('otaStatusResultBox');
  box.style.color = '#fbbf24';
  box.innerText = '⏳ Đang kết nối kho GitHub OTA để kiểm tra phiên bản mới & Gói Key Ngách mới...';
  const out = await postAction('check_ota_update');
  if (out && out.ok) {
    box.style.color = out.has_update ? '#fbbf24' : '#34d399';
    box.innerHTML = `
      <div>• <strong>Kết quả kiểm tra lúc ${escapeHtml(out.checked_at)}:</strong> ${out.has_update ? '🔔 <strong>CÓ BẢN CẬP NHẬT MỚI TRÊN GITHUB!</strong>' : '✅ <strong>Máy đang ở phiên bản mới nhất!</strong>'}</div>
      <div>• <strong>Phiên bản trên máy:</strong> <code>v${escapeHtml(out.local_version)}</code> | <strong>Phiên bản trên GitHub:</strong> <code>v${escapeHtml(out.remote_version)}</code> (${out.remote_total_niche_recipes || 8} Gói Key Ngách)</div>
      <div>• <strong>Số mô-đun có thay đổi:</strong> <strong>${(out.changed_files || []).length} file</strong></div>
      <div style="margin-top:4px;color:#e2e8f0;">📝 <em>Nội dung cập nhật:</em> ${escapeHtml(out.remote_release_notes || '')}</div>
    `;
  } else {
    box.style.color = '#f87171';
    box.innerText = `⚠️ ${(out && out.error) || 'Không thể kiểm tra bản cập nhật.'}`;
  }
}

async function applyOtaUpdateNow() {
  const box = document.getElementById('otaStatusResultBox');
  box.style.color = '#fbbf24';
  box.innerText = '⏳ Đang tải các tính năng mới & Gói Key Ngách mới trực tiếp từ GitHub OTA (Không ảnh hưởng dữ liệu kênh)...';
  const out = await postAction('apply_ota_update');
  if (out && out.ok) {
    box.style.color = '#34d399';
    box.innerText = out.message || '✅ Đã cập nhật từ xa thành công!';
  } else {
    box.style.color = '#f87171';
    box.innerText = `❌ Lỗi cập nhật: ${(out && (out.error || (out.errors || []).join(', '))) || 'Không xác định'}`;
  }
}

async function adminPublishUpdateToGithubNow() {
  const msg = document.getElementById('otaAdminCommitMsg').value.trim();
  const box = document.getElementById('otaStatusResultBox');
  box.style.color = '#fbbf24';
  box.innerText = '⏳ Đang đóng gói version_manifest.json và đẩy (git push) lên kho GitHub OTA...';
  const out = await postAction('admin_publish_ota_to_github', { commit_message: msg });
  if (out && out.ok) {
    box.style.color = '#34d399';
    box.innerText = out.message || '🚀 Đã đẩy lên GitHub thành công!';
    document.getElementById('otaAdminCommitMsg').value = '';
  } else {
    box.style.color = '#f87171';
    box.innerText = `⚠️ ${(out && (out.message || out.error)) || 'Lỗi khi đẩy lên GitHub'}`;
  }
}

function openProxyModal() {
  const ch = (cachedChannels || []).find(c => c.channel_id === selectedChannelId) || cachedChannels[0] || {};
  document.getElementById('modalChannelProxyInput').value = ch.proxy || '';
  document.getElementById('proxyTestResultBox').innerText = ch.last_verified_ip
    ? `Lần xác thực gần nhất: ${ch.last_verified_ip}`
    : 'Bấm 「🔍 Kiểm Tra Kết Nối Proxy / IP」 để xem địa chỉ IP thực tế, Quốc gia, Thành phố và Độ trễ (ms).';
  document.getElementById('proxyConfigModal').style.display = 'flex';
}

async function testProxyInModal() {
  const rawPrx = document.getElementById('modalChannelProxyInput').value.trim();
  const box = document.getElementById('proxyTestResultBox');
  box.style.color = '#fbbf24';
  box.innerText = '⏳ Đang kiểm tra kết nối Proxy & truy vấn IP thực tế...';
  const out = await postAction('test_channel_proxy', { proxy: rawPrx });
  if (out && out.ok) {
    box.style.color = '#34d399';
    box.innerText = `✅ KẾT NỐI THÀNH CÔNG!\n• Địa chỉ IP: ${out.ip} (${out.proxy_mode})\n• Vị trí: ${out.city || ''} - ${out.country || ''} (${out.countryCode || ''}) | ISP: ${out.isp || ''}\n• Độ trễ phản hồi: ${out.latency_ms} ms`;
  } else {
    box.style.color = '#f87171';
    box.innerText = `❌ LỖI KẾT NỐI PROXY:\n${(out && out.error) || 'Không thể kết nối tới máy chủ Proxy. Vui lòng kiểm tra lại IP:Port:User:Pass.'}`;
  }
}

async function saveProxyFromModal() {
  const rawPrx = document.getElementById('modalChannelProxyInput').value.trim();
  const box = document.getElementById('proxyTestResultBox');
  box.style.color = '#fbbf24';
  box.innerText = '⏳ Đang lưu Proxy vào Profile kênh và xác thực địa chỉ IP...';
  const out = await postAction('save_channel_proxy', { proxy: rawPrx });
  if (out && out.ok) {
    closeModals();
  } else {
    box.style.color = '#f87171';
    box.innerText = `❌ Không thể lưu: ${(out && out.error) || 'Lỗi không xác định'}`;
  }
}

async function browseFolderForInput(inputId) {
  const cur = document.getElementById(inputId).value || '';
  const out = await postAction('pick_folder_dialog', { initial_dir: cur });
  if (out && out.selected_folder) {
    document.getElementById(inputId).value = out.selected_folder;
  }
}

async function changeBatchQueueDirPrompt() {
  const cur = document.getElementById('queueDirText').innerText || 'D:\\KEY NHẬT\\20-30';
  const out = await postAction('pick_folder_dialog', { initial_dir: cur });
  if (out && out.selected_folder) {
    await postAction('set_batch_queue_dir', { batch_queue_dir: out.selected_folder });
  }
}

function configureAiModelPrompt() {
  document.getElementById('aiConfigModal').style.display = 'flex';
}

async function saveAiConfigFromModal() {
  const pClean = document.getElementById('modalAiProvider').value || 'AUTO';
  const geminiKey = document.getElementById('modalGeminiKey').value.trim();
  const openaiKey = document.getElementById('modalOpenaiKey').value.trim();
  await postAction('save_ai_model_config', {
    provider: pClean,
    gemini_api_key: geminiKey || undefined,
    openai_api_key: openaiKey || undefined
  });
  closeModals();
}

function onNewLangChange() {
  const lang = document.getElementById('modalNewLang').value;
  const seedInput = document.getElementById('modalNewSeeds');
  if (lang === 'es') {
    seedInput.value = 'doña herencia familiar, drama familiar mexico, adultos mayores';
  } else if (lang === 'en') {
    seedInput.value = 'emotional family justice story, billionaire hidden legacy, abandoned house';
  } else {
    seedInput.value = '熟年離婚 漫画, シニア 人生劇場, 定年後 ドラマ';
  }
}

function addNewChannelKeyPrompt() {
  if (cachedChannels.length >= 10) {
    alert('⚠️ Máy tính này đã đạt giới hạn tối ưu tối đa 10 Kênh / 1 Máy (Slot #1 -> #10) để đảm bảo an toàn tài nguyên RAM/CPU và độ sạch của Chrome Profile!');
    return;
  }
  document.getElementById('addChannelModal').style.display = 'flex';
}

async function submitNewChannelFromModal() {
  const deptName = document.getElementById('modalNewDeptName').value.trim();
  if (!deptName) return;
  const lang = document.getElementById('modalNewLang').value || 'ja';
  const seedRaw = document.getElementById('modalNewSeeds').value || '';
  const queueDir = document.getElementById('modalNewQueueDir').value.trim();
  const proxyRaw = (document.getElementById('modalNewProxy') ? document.getElementById('modalNewProxy').value.trim() : '');
  const out = await postAction('add_new_channel_key', {
    department_name: deptName,
    language: lang,
    seed_keywords: seedRaw.split(',').map(s => s.trim()).filter(Boolean),
    batch_queue_dir: queueDir,
    proxy: proxyRaw
  });
  if (out && out.error) {
    alert(out.error);
    return;
  }
  closeModals();
}

async function quitPcApp() {
  await postAction('quit_app');
  window.close();
}

async function submitAudienceFeedback() {
  const raw = document.getElementById('manualFeedbackInput').value.trim();
  if (!raw) return;
  await postAction('ingest_feedback', { comments: raw.split('\n') });
  document.getElementById('manualFeedbackInput').value = '';
}

function escapeHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

setInterval(refreshState, 2200);
refreshState();
</script>
</body>
</html>
"""


class EnterpriseDashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            raw = DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if parsed.path == "/api/status":
            qs = parse_qs(parsed.query)
            reg = load_registry()
            channels = reg.get("channels", [])
            cid = (qs.get("channel_id") or [""])[0] or (channels[0]["channel_id"] if channels else "")

            selected_ch = None
            for ch in channels:
                ch_paths = ChannelScannerAndAnalyticsEngine.ensure_channel_folder_structure(ch)
                port = int(ch.get("cdp_port", 9301))
                if BrowserCDPManager.is_port_open(port):
                    pages = TabGuard.enforce_max_two_tabs(port)
                    ch["open_tabs_count"] = len(pages)
                else:
                    ch["open_tabs_count"] = 0

                # [v3.8.1] Đồng bộ trạng thái đăng nhập thực tế từ 01_CHANNEL_IDENTITY.json & Cookie Store của Profile
                if not ch.get("logged_in") and ch.get("status") != "LOGIN_REQUIRED":
                    try:
                        id_file = ch_paths.get("identity_json", "")
                        if id_file and os.path.isfile(id_file):
                            with open(id_file, "r", encoding="utf-8") as idf:
                                id_obj = json.load(idf)
                            if id_obj.get("logged_in"):
                                ch["logged_in"] = True
                                if id_obj.get("detected_channel_title"):
                                    ch["detected_channel_title"] = id_obj["detected_channel_title"]
                    except Exception:
                        pass
                if ch.get("channel_id") == cid:
                    selected_ch = ch
            save_registry(reg)

            evo = FeedbackEvolutionEngine.load_evolution_memory(cid) if cid else {}
            logs = read_channel_logs(cid) if cid else []
            channel_summary = (
                ChannelScannerAndAnalyticsEngine.load_channel_summary(selected_ch)
                if selected_ch
                else {}
            )
            ch_folder = os.path.join(BASE_DIR, "CHANNELS_DATA", cid) if cid else ""
            ch_batch_dir = (selected_ch.get("batch_queue_dir") if selected_ch else "") or r"D:\KEY NHẬT\20-30"
            batch_queue = (
                YouTubeStudioAutoUploader.scan_batch_folder_queue(ch_folder, ch_batch_dir)
                if ch_folder
                else {}
            )
            autopilot_sched = (
                DailyAutopilotScheduler.load_or_init_schedule(ch_folder, cid)
                if ch_folder
                else {}
            )
            gmail_trust_state = {}
            if ch_folder:
                gm_path = os.path.join(ch_folder, "11_GMAIL_TRUST_FARMING_STATE.json")
                if os.path.exists(gm_path):
                    try:
                        with open(gm_path, "r", encoding="utf-8") as gf:
                            gmail_trust_state = json.load(gf)
                    except Exception:
                        gmail_trust_state = {}

            ai_cfg = SHARED_AI_BRAIN.load_ai_model_config()
            ai_mem = SHARED_AI_BRAIN.load_session_memory(cid) if cid else {}
            daily_timeline = DailyMasterTimelineCalculator.calculate_daily_master_plan(channels)
            supervisor_state = AI_SUPERVISOR.get_status(channels)
            bg_video_state = BG_VIDEO_ENGINE.get_status()
            lic_state = LicenseKeyManager.get_current_license_state()
            admin_vault = LicenseKeyManager.ensure_initial_admin_key_vault()
            all_recipes = NicheRecipeRegistry.load_all_recipes()
            ch_lang = (selected_ch.get("language") if selected_ch else "ja") or "ja"
            default_niche_key = (
                "KEY_JP_K1_MANGA" if ch_lang == "ja" else ("KEY_MX_DONA_FAMILIA" if ch_lang == "es" else "KEY_US_MAFIA_MAID")
            )
            sel_niche_key = (selected_ch.get("niche_recipe_key") if selected_ch else None) or default_niche_key
            sel_recipe = NicheRecipeRegistry.get_recipe_by_key(sel_niche_key)
            ota_manifest = OTAUpdaterManager.get_local_manifest()

            self._send_json({
                "ok": True,
                "channels": channels,
                "selected_channel_id": cid,
                "channel_summary": channel_summary,
                "batch_queue": batch_queue,
                "autopilot_schedule": autopilot_sched,
                "gmail_trust_state": gmail_trust_state,
                "daily_master_timeline": daily_timeline,
                "ai_supervisor": supervisor_state,
                "bg_video_production": bg_video_state,
                "license_state": lic_state,
                "admin_keys_vault": admin_vault,
                "niche_recipes": all_recipes,
                "selected_channel_niche_recipe": sel_recipe,
                "ota_version_manifest": ota_manifest,
                "ai_model_config": {
                    "provider": ai_cfg.get("provider", "AUTO"),
                    "has_gemini_key": bool(ai_cfg.get("gemini_api_key")),
                    "has_openai_key": bool(ai_cfg.get("openai_api_key")),
                    "updated_at": ai_cfg.get("updated_at", ""),
                },
                "ai_session_memory_count": ai_mem.get("total_sessions_recorded", 0),
                "logs": logs,
                "evolution": evo,
            })
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8", errors="replace") or "{}")

        if parsed.path == "/api/ai_decision":
            cid = body.get("channel_id", "DEPT_01_JAPAN_K1")
            decision = body.get("decision", {})
            SHARED_AI_BRAIN.push_subagent_decision(cid, decision)
            ai_thought = decision.get("ai_thought", "")
            desk = int(body.get("desk", 1))
            if ai_thought:
                PERSONA_ENGINE.emit_log(
                    cid,
                    desk,
                    f"🧠 [Antigravity AI Agent Suy Nghĩ]: {ai_thought}",
                    {"last_ai_thought": ai_thought, "active_desk": desk},
                )
            self._send_json({"ok": True})
            return

        if parsed.path != "/api/action":
            self._send_json({"error": "Not found"}, status=404)
            return

        action = body.get("action", "")
        channel_id = body.get("channel_id") or body.get("dept_id") or "DEPT_01_JAPAN_K1"
        ch = get_channel_by_id(channel_id)
        if not ch:
            self._send_json({"ok": False, "error": "Channel not found"}, status=400)
            return

        cid = ch["channel_id"]
        port = int(ch["cdp_port"])
        paths = ChannelScannerAndAnalyticsEngine.ensure_channel_folder_structure(ch)

        if action in ("launch_browser", "open_gmail_login"):
            info = BrowserCDPManager.open_gmail_and_channel_login(
                profile_dir=ch["profile_dir"],
                cdp_port=port,
                proxy=ch.get("proxy", ""),
                channel_folder=paths["channel_folder"],
            )
            PERSONA_ENGINE.emit_log(
                cid,
                1,
                f"🔑 Đã bật nổi cửa sổ Chrome Profile ({ch['profile_dir']}) tại Port {port} lên màn hình chính (Tab #1: Đăng nhập Google/YouTube, Tab #2: YouTube Studio — Khóa cứng {info.get('open_tabs', 2)}/2 Tab).",
                {"open_tabs_count": info.get("open_tabs", 2)},
            )
            self._send_json(info)
            return

        if action == "scan_channel_and_analytics":
            def _scan_worker():
                update_channel_state(cid, {"status": "SCANNING_CHANNEL", "active_desk": 6})
                try:
                    ChannelScannerAndAnalyticsEngine.scan_channel_and_analytics(
                        channel=ch,
                        emit_log_fn=PERSONA_ENGINE.emit_log,
                    )
                finally:
                    update_channel_state(cid, {"status": "IDLE", "active_desk": 0})

            t = threading.Thread(target=_scan_worker, daemon=True)
            t.start()
            self._send_json({"ok": True, "scanning_started": True, "channel_folder": paths["channel_folder"]})
            return

        if action == "open_channel_folder":
            try:
                subprocess.Popen(["explorer.exe", paths["channel_folder"]])
            except Exception:
                pass
            self._send_json({"ok": True, "channel_folder": paths["channel_folder"]})
            return

        if action == "open_ready_videos_folder":
            ready_dir = os.path.join(paths["channel_folder"], "08_READY_VIDEOS_TO_UPLOAD")
            os.makedirs(ready_dir, exist_ok=True)
            try:
                subprocess.Popen(["explorer.exe", ready_dir])
            except Exception:
                pass
            PERSONA_ENGINE.emit_log(
                cid,
                6,
                f"📥 [Thư Mục Bỏ Video Sẵn]: Đã mở `{ready_dir}` — Bạn chỉ cần chép file `.mp4` (kèm hoặc không kèm SEO) vào đây để hệ thống Đẩy Lên Trước & Hẹn Giờ Public!",
            )
            self._send_json({"ok": True, "ready_videos_folder": ready_dir})
            return

        if action == "verify_login_now":
            def _verify_worker():
                update_channel_state(cid, {"status": "VERIFYING_LOGIN", "active_desk": 1})
                try:
                    BrowserCDPManager.launch_channel_browser(
                        profile_dir=ch["profile_dir"],
                        cdp_port=port,
                        proxy=ch.get("proxy", ""),
                        initial_url="https://www.youtube.com",
                        side_by_side_right=True,
                        channel_folder=paths["channel_folder"],
                    )
                    time.sleep(2.5)
                    tab1 = TabGuard.get_or_allocate_tab(port, slot=1)
                    pages = TabGuard.enforce_max_two_tabs(port, keep_tab_id=tab1["id"] if tab1 else None, max_tabs=1)
                    tid = tab1["id"] if tab1 else (pages[0]["id"] if pages else "")
                    chk = BrowserCDPManager.verify_google_and_youtube_login_before_task(
                        cdp_port=port,
                        target_id=tid,
                        check_mode="YOUTUBE",
                        emit_cb=lambda msg: PERSONA_ENGINE.emit_log(cid, 1, msg),
                    )
                    is_ok = bool(chk.get("logged_in"))
                    update_channel_state(
                        cid,
                        {
                            "logged_in": is_ok,
                            "status": "IDLE" if is_ok else "LOGIN_REQUIRED",
                            "active_desk": 0,
                        },
                    )
                    # Cập nhật luôn vào 01_CHANNEL_IDENTITY.json
                    try:
                        if os.path.isfile(paths["identity_json"]):
                            with open(paths["identity_json"], "r", encoding="utf-8") as idf:
                                id_data = json.load(idf)
                            id_data["logged_in"] = is_ok
                            if chk.get("detected_account"):
                                id_data["account_display_name"] = chk.get("detected_account")
                            with open(paths["identity_json"], "w", encoding="utf-8") as idf:
                                json.dump(id_data, idf, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                    if is_ok:
                        BrowserCDPManager.close_channel_browser(port)
                    else:
                        # Nếu chưa đăng nhập, giữ cửa sổ mở ở trang đăng nhập Google để người dùng đăng nhập luôn
                        TabGuard.navigate_tab(
                            port,
                            tid,
                            "https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fwww.youtube.com%2F",
                        )
                        BrowserCDPManager.bring_window_to_front(port, side_by_side_right=True)
                except Exception as e:
                    update_channel_state(cid, {"status": "IDLE", "active_desk": 0})
                    PERSONA_ENGINE.emit_log(cid, 1, f"⚠️ Lỗi kiểm tra đăng nhập: {e}")

            threading.Thread(target=_verify_worker, daemon=True).start()
            self._send_json({"ok": True, "verifying": True})
            return

        if action == "ai_single_cognitive_step":
            def _single_step():
                PERSONA_ENGINE.run_daily_persona_warmup_session(
                    channel=ch,
                    num_videos_override=1,
                    demo_fast_mode=True,
                )

            t = threading.Thread(target=_single_step, daemon=True)
            t.start()
            self._send_json({"ok": True, "started_single_cognitive_step": True})
            return

        if action == "open_studio_tab":
            BrowserCDPManager.launch_channel_browser(
                profile_dir=ch["profile_dir"],
                cdp_port=port,
                proxy=ch.get("proxy", ""),
                initial_url="https://www.youtube.com",
                side_by_side_right=True,
                channel_folder=paths["channel_folder"],
            )
            tab2 = TabGuard.get_or_allocate_tab(port, slot=2, target_url="https://studio.youtube.com")
            pages = TabGuard.enforce_max_two_tabs(port, keep_tab_id=tab2["id"] if tab2 else None)
            BrowserCDPManager.bring_window_to_front(port, side_by_side_right=True)
            PERSONA_ENGINE.emit_log(
                cid,
                6,
                f"🚀 [Bàn #6] Mở YouTube Studio trên Tab #2 (TabGuard: {len(pages)}/2 Tab).",
                {"active_desk": 6, "open_tabs_count": len(pages)},
            )
            self._send_json({"ok": True, "open_tabs": len(pages)})
            return

        if action == "pick_folder_dialog":
            init_dir = str(body.get("initial_dir") or BASE_DIR).strip()
            selected_folder = ""
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                selected_folder = filedialog.askdirectory(
                    initialdir=init_dir if os.path.isdir(init_dir) else BASE_DIR,
                    title="Chọn Thư Mục Chứa Các Tập Video Của Key",
                )
                root.destroy()
            except Exception:
                selected_folder = ""
            if selected_folder:
                selected_folder = os.path.normpath(selected_folder)
            self._send_json({"ok": True, "selected_folder": selected_folder})
            return

        if action == "quit_app":
            self._send_json({"ok": True, "quitting": True})
            threading.Thread(target=lambda: (time.sleep(0.4), os._exit(0)), daemon=True).start()
            return

        if action == "save_ai_model_config":
            saved_cfg = SHARED_AI_BRAIN.save_ai_model_config(body)
            PERSONA_ENGINE.emit_log(
                cid,
                1,
                f"🤖 [Cấu Hình Model AI v3.4]: Đã lưu chế độ `{saved_cfg.get('provider')}` vào `CHANNELS_DATA/ai_model_config.json` "
                f"(Gemini Key: {'ĐÃ CÀI' if saved_cfg.get('gemini_api_key') else 'CHƯA'} | OpenAI Key: {'ĐÃ CÀI' if saved_cfg.get('openai_api_key') else 'CHƯA'}).",
            )
            self._send_json({"ok": True, "provider": saved_cfg.get("provider")})
            return

        if action == "start_warmup":
            demo_mode = bool(body.get("demo_fast_mode", False))
            w_mode = str(body.get("warmup_mode") or "FULL_OMNI").strip().upper()
            num_override = 3 if demo_mode else None

            def _worker():
                PERSONA_ENGINE.run_daily_persona_warmup_session(
                    channel=ch,
                    num_videos_override=num_override,
                    demo_fast_mode=demo_mode,
                    warmup_mode=w_mode,
                )

            t = threading.Thread(target=_worker, daemon=True)
            ACTIVE_THREADS[cid] = t
            t.start()
            self._send_json({"ok": True, "started": True, "warmup_mode": w_mode})
            return

        if action in (
            "setup_google_alerts",
            "warmup_gmail",
            "warmup_news",
            "warmup_google_search",
            "warmup_google_maps",
            "warmup_shorts",
        ):
            def _omni_worker():
                update_channel_state(cid, {"status": f"RUNNING_{action.upper()}", "active_desk": 1})
                try:
                    PERSONA_ENGINE.run_omni_specific_task(ch, action)
                finally:
                    BrowserCDPManager.close_channel_browser(port)
                    update_channel_state(cid, {"status": "IDLE", "active_desk": 0, "open_tabs_count": 0})

            t = threading.Thread(target=_omni_worker, daemon=True)
            ACTIVE_THREADS[cid] = t
            t.start()
            self._send_json({"ok": True, "started_omni_task": action})
            return

        if action == "upload_next_pending_episode":
            vis_mode = body.get("visibility_mode", "SCHEDULE")
            pub_date = str(body.get("scheduled_publish_date") or "").strip()
            pub_time = str(body.get("scheduled_publish_time") or "20:00").strip()
            ch_batch_dir = ch.get("batch_queue_dir") or r"D:\KEY NHẬT\20-30"

            def _upload_next_worker():
                update_channel_state(cid, {"status": "PRE_UPLOADING_AND_SCHEDULING", "active_desk": 6})
                try:
                    YouTubeStudioAutoUploader.upload_next_pending_episode_from_queue(
                        channel=ch,
                        parent_batch_dir=ch_batch_dir,
                        visibility_mode=vis_mode,
                        scheduled_publish_date=pub_date,
                        scheduled_publish_time=pub_time,
                        emit_log_fn=PERSONA_ENGINE.emit_log,
                    )
                finally:
                    update_channel_state(cid, {"status": "IDLE", "active_desk": 0, "open_tabs_count": 0})

            t = threading.Thread(target=_upload_next_worker, daemon=True)
            ACTIVE_THREADS[cid] = t
            t.start()
            self._send_json({"ok": True, "started_upload_next": True, "visibility_mode": vis_mode, "scheduled_publish_time": pub_time})
            return

        if action == "upload_specific_episode":
            ep_id = str(body.get("episode_id", "")).strip()
            vis_mode = body.get("visibility_mode", "SCHEDULE")
            pub_date = str(body.get("scheduled_publish_date") or "").strip()
            pub_time = str(body.get("scheduled_publish_time") or "20:00").strip()
            ch_batch_dir = ch.get("batch_queue_dir") or r"D:\KEY NHẬT\20-30"
            q_info = YouTubeStudioAutoUploader.scan_batch_folder_queue(
                paths["channel_folder"], parent_batch_dir=ch_batch_dir, language=ch.get("language", "ja")
            )
            target_ep = next((e for e in q_info.get("episodes", []) if str(e.get("episode_id")) == ep_id), None)
            if not target_ep:
                self._send_json({"ok": False, "error": f"Không tìm thấy Tập {ep_id}"}, status=400)
                return

            def _upload_spec_worker():
                update_channel_state(cid, {"status": f"PRE_UPLOADING_EP_{ep_id}", "active_desk": 6})
                try:
                    YouTubeStudioAutoUploader.execute_studio_upload_workflow(
                        channel=ch,
                        video_file_path=target_ep["video_file_path"],
                        seo_file_path=target_ep["seo_file_path"],
                        srt_file_path=target_ep.get("srt_file_path", ""),
                        timestamps_file_path=target_ep.get("timestamps_file_path", ""),
                        episode_id=ep_id,
                        visibility_mode=vis_mode,
                        scheduled_publish_date=pub_date,
                        scheduled_publish_time=pub_time,
                        emit_log_fn=PERSONA_ENGINE.emit_log,
                        auto_close_browser_when_done=True,
                    )
                finally:
                    update_channel_state(cid, {"status": "IDLE", "active_desk": 0, "open_tabs_count": 0})

            t = threading.Thread(target=_upload_spec_worker, daemon=True)
            ACTIVE_THREADS[cid] = t
            t.start()
            self._send_json({"ok": True, "started_upload_episode": ep_id, "visibility_mode": vis_mode, "scheduled_publish_time": pub_time})
            return

        if action == "test_channel_proxy":
            proxy_raw = str(body.get("proxy") if "proxy" in body else ch.get("proxy", "")).strip()
            check_res = BrowserCDPManager.verify_proxy_or_direct_ip(proxy_raw=proxy_raw, profile_dir=ch["profile_dir"])
            if check_res.get("ok"):
                ip_summary = f"IP: {check_res.get('ip')} ({check_res.get('city')}, {check_res.get('countryCode')}) - {check_res.get('latency_ms')}ms"
                update_channel_state(cid, {"last_verified_ip": ip_summary})
                PERSONA_ENGINE.emit_log(
                    cid,
                    1,
                    f"🌐 [Kiểm Tra Proxy / IP]: Kết nối thành công -> {ip_summary} | Chế độ: {check_res.get('proxy_mode')}.",
                )
            else:
                PERSONA_ENGINE.emit_log(
                    cid,
                    1,
                    f"⚠️ [Kiểm Tra Proxy / IP]: Lỗi kết nối -> {check_res.get('error')}",
                )
            self._send_json(check_res)
            return

        if action == "save_channel_proxy":
            proxy_raw = str(body.get("proxy") or "").strip()
            proxy_cfg = BrowserCDPManager.parse_and_prepare_proxy_for_profile(ch["profile_dir"], proxy_raw)
            if proxy_raw and not proxy_cfg.get("enabled"):
                self._send_json({"ok": False, "error": proxy_cfg.get("error", "Định dạng Proxy không hợp lệ")}, status=400)
                return

            check_res = BrowserCDPManager.verify_proxy_or_direct_ip(proxy_raw=proxy_raw, profile_dir=ch["profile_dir"])
            ip_summary = (
                f"IP: {check_res.get('ip')} ({check_res.get('city')}, {check_res.get('countryCode')}) - {check_res.get('latency_ms')}ms"
                if check_res.get("ok")
                else "Chưa xác thực IP"
            )
            update_channel_state(cid, {"proxy": proxy_raw, "last_verified_ip": ip_summary})

            # Nếu trình duyệt của kênh đang mở, đóng lại để lần mở tiếp theo áp dụng Proxy mới ngay lập tức
            if BrowserCDPManager.is_port_open(port):
                BrowserCDPManager.close_channel_browser(port)

            PERSONA_ENGINE.emit_log(
                cid,
                1,
                f"🌐 [Cấu Hình Proxy Kênh]: Đã lưu `{proxy_cfg.get('display_masked')}` vào Chrome Profile riêng `{ch['profile_dir']}` ({ip_summary}).",
            )
            self._send_json({"ok": True, "proxy": proxy_raw, "proxy_info": proxy_cfg, "ip_check": check_res})
            return

        if action == "set_batch_queue_dir":
            new_dir = str(body.get("batch_queue_dir", "")).strip()
            if new_dir:
                update_channel_state(cid, {"batch_queue_dir": new_dir})
                PERSONA_ENGINE.emit_log(
                    cid,
                    6,
                    f"📂 [Cấu hình Hàng Đợi Key]: Đã cập nhật thư mục Hàng đợi Upload của kênh sang `{new_dir}`.",
                )
            self._send_json({"ok": True, "batch_queue_dir": new_dir})
            return

        if action == "add_new_channel_key":
            reg = load_registry()
            channels = reg.get("channels", [])
            if len(channels) >= MAX_CHANNELS_PER_PC:
                self._send_json(
                    {
                        "ok": False,
                        "error": f"Máy tính này đã đạt giới hạn tối ưu tối đa {MAX_CHANNELS_PER_PC}/{MAX_CHANNELS_PER_PC} kênh!",
                    },
                    status=400,
                )
                return

            used_ports = {int(c.get("cdp_port", 0)) for c in channels}
            next_num = len(channels) + 1
            new_port = 9300 + next_num
            while new_port in used_ports:
                new_port += 1

            lang = str(body.get("language", "ja")).strip().lower()
            if lang not in ("ja", "en", "es"):
                lang = "en"
            new_cid = f"DEPT_{next_num:02d}_{lang.upper()}_KEY"
            existing_ids = {str(c.get("channel_id")) for c in channels}
            if new_cid in existing_ids:
                new_cid = f"DEPT_{next_num:02d}_{lang.upper()}_{new_port}"

            new_profile = os.path.join(BASE_DIR, "PROFILES", f"KENH_{next_num:02d}_{lang.upper()}")
            existing_profs = {str(c.get("profile_dir", "")).lower() for c in channels}
            if new_profile.lower() in existing_profs:
                new_profile = os.path.join(BASE_DIR, "PROFILES", f"KENH_{next_num:02d}_{lang.upper()}_{new_port}")

            dept_name = str(body.get("department_name") or f"Phòng Ban #{next_num:02d} ({lang.upper()})").strip()
            seeds = body.get("seed_keywords") or []
            b_dir = str(body.get("batch_queue_dir") or "").strip()
            proxy_raw = str(body.get("proxy") or "").strip()
            if proxy_raw:
                BrowserCDPManager.parse_and_prepare_proxy_for_profile(new_profile, proxy_raw)

            new_ch = {
                "channel_id": new_cid,
                "department_name": dept_name,
                "channel_title": dept_name,
                "niche": dept_name,
                "language": lang,
                "profile_dir": new_profile,
                "cdp_port": new_port,
                "proxy": proxy_raw,
                "last_verified_ip": "",
                "seed_keywords": seeds,
                "batch_queue_dir": b_dir,
                "today_target_quota": 8,
                "today_watched_count": 0,
                "status": "IDLE",
                "active_desk": 0,
                "open_tabs_count": 0,
            }
            channels.append(new_ch)
            reg["channels"] = channels
            save_registry(reg)
            ChannelScannerAndAnalyticsEngine.ensure_channel_folder_structure(new_ch)
            self._send_json({"ok": True, "new_channel": new_ch})
            return

        if action == "toggle_autopilot":
            cur_sched = DailyAutopilotScheduler.load_or_init_schedule(paths["channel_folder"], cid)
            new_state = not bool(cur_sched.get("auto_warmup_enabled", cur_sched.get("autopilot_enabled", False)))
            updated = DailyAutopilotScheduler.update_schedule_config(
                paths["channel_folder"],
                cid,
                {"auto_warmup_enabled": new_state, "autopilot_enabled": new_state},
            )
            PERSONA_ENGINE.emit_log(
                cid,
                1,
                f"🌿 [Tự Động NUÔI Kênh & Gmail]: Đã {'BẬT (ON)' if new_state else 'TẮT (OFF)'} nhánh Tự Động Nuôi Độc Lập "
                f"(Chế độ: {updated.get('warmup_mode', 'FULL_OMNI')} | Sáng: {updated.get('today_morning_trigger_time')} | Chiều: {updated.get('today_afternoon_trigger_time')}).",
            )
            self._send_json({"ok": True, "autopilot_schedule": updated})
            return

        if action == "toggle_auto_pre_upload":
            cur_sched = DailyAutopilotScheduler.load_or_init_schedule(paths["channel_folder"], cid)
            new_state = not bool(cur_sched.get("auto_pre_upload_enabled", False))
            updated = DailyAutopilotScheduler.update_schedule_config(
                paths["channel_folder"],
                cid,
                {"auto_pre_upload_enabled": new_state, "auto_daily_upload_from_queue_enabled": new_state},
            )
            PERSONA_ENGINE.emit_log(
                cid,
                6,
                f"📤 [Tự Động ĐẨY VIDEO TRƯỚC & HẸN GIỜ PUBLIC]: Đã {'BẬT (ON)' if new_state else 'TẮT (OFF)'} nhánh Tự Động Đẩy Video Trước Độc Lập "
                f"(Đẩy trước lúc: {updated.get('pre_upload_trigger_time')} ➔ Hẹn giờ Public: {updated.get('scheduled_publish_time')}).",
            )
            self._send_json({"ok": True, "autopilot_schedule": updated})
            return

        if action == "save_upload_schedule_settings":
            updates = {}
            if "video_source_mode" in body:
                updates["video_source_mode"] = str(body["video_source_mode"]).strip().upper()
            if "warmup_mode" in body:
                updates["warmup_mode"] = str(body["warmup_mode"]).strip().upper()
            if "pre_upload_trigger_time" in body:
                updates["pre_upload_trigger_time"] = str(body["pre_upload_trigger_time"]).strip() or "13:30"
            if "scheduled_publish_time" in body:
                updates["scheduled_publish_time"] = str(body["scheduled_publish_time"]).strip() or "20:00"
            updated = DailyAutopilotScheduler.update_schedule_config(paths["channel_folder"], cid, updates)
            PERSONA_ENGINE.emit_log(
                cid,
                6,
                f"💾 [Lưu Cấu Hình Nguồn Video & Giờ Hẹn]: Nguồn={updated.get('video_source_mode')} | Chế độ Nuôi={updated.get('warmup_mode')} | "
                f"Giờ Đẩy Video Trước={updated.get('pre_upload_trigger_time')} ➔ Giờ Vàng Public={updated.get('scheduled_publish_time')}.",
            )
            self._send_json({"ok": True, "autopilot_schedule": updated})
            return

        if action == "stop_channel":
            PERSONA_ENGINE.stop_channel(cid)
            BrowserCDPManager.close_channel_browser(port)
            PERSONA_ENGINE.emit_log(
                cid,
                0,
                "🛑 Đã dừng tác vụ, lưu Cookie và ĐÓNG LUÔN cửa sổ Chrome Profile để giải phóng máy!",
                {"status": "IDLE", "active_desk": 0, "open_tabs_count": 0},
            )
            self._send_json({"ok": True, "browser_closed": True})
            return

        if action == "test_transcript_comment":
            BrowserCDPManager.launch_channel_browser(
                profile_dir=ch["profile_dir"],
                cdp_port=port,
                proxy=ch.get("proxy", ""),
                initial_url="https://www.youtube.com",
                side_by_side_right=True,
                channel_folder=paths["channel_folder"],
            )
            pages = TabGuard.enforce_max_two_tabs(port)
            tid = pages[-1]["id"] if pages else ""
            transcript_data = TranscriptExtractor.extract_from_active_video_tab(port, tid, cid) if tid else {}
            comment_obj = MeaningfulCommentGenerator.build_timestamp_comment(
                transcript_data, channel=ch, language=ch.get("language", "ja")
            )
            if transcript_data.get("existing_comments"):
                FeedbackEvolutionEngine.ingest_comments_and_community_feedback(
                    cid, transcript_data["existing_comments"]
                )
            PERSONA_ENGINE.emit_log(
                cid,
                1,
                f"💬 [AI Đọc Transcript ({transcript_data.get('segments_count', 0)} đoạn) -> Tự Viết Bình Luận tại mốc {comment_obj.get('timestamp')}]: "
                f"\"{comment_obj.get('comment_text')}\" | Suy nghĩ AI: {comment_obj.get('ai_thought', '')}",
                {
                    "last_generated_comment": comment_obj,
                    "last_ai_thought": comment_obj.get("ai_thought", ""),
                    "active_desk": 1,
                },
            )
            self._send_json({"ok": True, "transcript": transcript_data, "comment": comment_obj})
            return

        if action == "ingest_feedback":
            comments = body.get("comments", [])
            evo = FeedbackEvolutionEngine.ingest_comments_and_community_feedback(
                cid, comments, community_feedback=comments
            )
            PERSONA_ENGINE.emit_log(
                cid,
                7,
                f"🧬 [Bàn #7 - AI Community Research Loop] Đã suy nghĩ phân tích {len(comments)} góp ý từ Comment/Community Tab và nâng cấp Luật Tiêu Đề (Bàn #2) + Kịch Bản (Bàn #3)!",
                {
                    "active_desk": 7,
                    "last_ai_thought": evo.get("last_ai_evolution_thought", "Đã phân tích sâu phản hồi khán giả để cập nhật DNA Kênh 1."),
                },
            )
            self._send_json({"ok": True, "evolution": evo})
            return

        if action == "run_dual_split_screen_warmup":
            left_cid = str(body.get("left_channel_id") or cid).strip()
            right_cid = str(body.get("right_channel_id") or "").strip()
            w_mode = str(body.get("warmup_mode") or "GMAIL_ONLY").strip().upper()
            bg_vid = bool(body.get("also_produce_video_in_bg", True))
            demo = bool(body.get("demo_fast_mode", False))

            ch_left = get_channel_by_id(left_cid) or ch
            ch_right = get_channel_by_id(right_cid) if right_cid and right_cid != left_cid else None
            res = PARALLEL_COORDINATOR.launch_dual_split_screen_warmup(
                channel_left=ch_left,
                channel_right=ch_right,
                warmup_mode=w_mode,
                demo_fast_mode=demo,
                also_produce_video_in_bg=bg_vid,
            )
            self._send_json(res)
            return

        if action == "run_all_channels_in_pairs":
            w_mode = str(body.get("warmup_mode") or "GMAIL_ONLY").strip().upper()
            bg_vid = bool(body.get("also_produce_video_in_bg", True))
            demo = bool(body.get("demo_fast_mode", False))
            all_chs = load_registry().get("channels", [])
            res = PARALLEL_COORDINATOR.run_all_channels_in_split_screen_pairs(
                channels=all_chs,
                warmup_mode=w_mode,
                demo_fast_mode=demo,
                also_produce_video_in_bg=bg_vid,
            )
            self._send_json(res)
            return

        if action == "start_background_video_production":
            topic_hint = str(body.get("topic_hint") or "").strip()
            res = BG_VIDEO_ENGINE.start_background_video_production(ch, custom_topic_hint=topic_hint)
            self._send_json(res)
            return

        if action == "run_ai_supervisor_check_now":
            res = AI_SUPERVISOR.inspect_and_heal_all_channels()
            self._send_json(res)
            return

        if action == "open_timeline_markdown_file":
            all_chs = load_registry().get("channels", [])
            DailyMasterTimelineCalculator.calculate_daily_master_plan(all_chs)
            md_path = DailyMasterTimelineCalculator.TIMELINE_MD_PATH
            try:
                os.startfile(md_path)
            except Exception:
                pass
            self._send_json({"ok": True, "timeline_md_path": md_path})
            return

        if action == "activate_license_key":
            raw_key = str(body.get("license_key") or "").strip()
            res = LicenseKeyManager.activate_license_key(raw_key)
            if res.get("ok"):
                PERSONA_ENGINE.emit_log(cid, 0, f"🔑 [Bản Quyền]: {res.get('message')}")
            self._send_json(res)
            return

        if action == "admin_generate_customer_key":
            tier = str(body.get("tier_code") or "VIP10")
            max_ch = int(body.get("max_channels") or 10)
            valid_days = int(body.get("valid_days") or 365)
            tag = str(body.get("customer_tag") or "KHACH01")
            scope = str(body.get("niche_scope") or "ALL")
            res = LicenseKeyManager.admin_create_new_customer_key(
                tier_code=tier,
                max_channels=max_ch,
                valid_days=valid_days,
                niche_scope=scope,
                customer_tag=tag,
            )
            if res.get("ok"):
                nk = res["new_key"]
                PERSONA_ENGINE.emit_log(
                    cid,
                    0,
                    f"👑 [Admin KeyGen]: Đã tạo Mã Key mới cho khách [{nk['customer_tag']}]: `{nk['license_key']}` ({nk['max_channels']} kênh | Hạn: {nk['expires_display']}).",
                )
            self._send_json(res)
            return

        if action == "open_keys_markdown_file":
            md_path = LicenseKeyManager.export_keys_markdown_guide()
            try:
                os.startfile(md_path)
            except Exception:
                pass
            self._send_json({"ok": True, "keys_md_path": md_path})
            return

        if action == "save_channel_niche_recipe":
            niche_key = str(body.get("niche_recipe_key") or "KEY_JP_K1_MANGA").strip()
            rec = NicheRecipeRegistry.get_recipe_by_key(niche_key)
            update_channel_state(cid, {"niche_recipe_key": rec["niche_key"], "niche": rec["niche_name"]})
            PERSONA_ENGINE.emit_log(
                cid,
                2,
                f"🎬 [Gói Key Ngách]: Đã áp dụng Key 『{rec['niche_name']}』 (`{rec['niche_key']}`) -> Kịch bản: {rec['script_formula']['style_name']} | Edit Video: {rec['video_edit_formula']['edit_style_name']}.",
            )
            self._send_json({"ok": True, "recipe": rec})
            return

        if action == "add_custom_niche_recipe":
            res = NicheRecipeRegistry.add_or_update_custom_niche_recipe(
                niche_key=str(body.get("niche_key") or ""),
                niche_name=str(body.get("niche_name") or ""),
                language=str(body.get("language") or "ja"),
                market=str(body.get("market") or ""),
                script_style_name=str(body.get("script_style_name") or ""),
                target_length=str(body.get("target_length") or ""),
                title_dna=str(body.get("title_dna") or ""),
                narrative_arc=str(body.get("narrative_arc") or ""),
                edit_style_name=str(body.get("edit_style_name") or ""),
                opening_hook_rule=str(body.get("opening_hook_rule") or ""),
                body_visual_rule=str(body.get("body_visual_rule") or ""),
                camera_and_effects=str(body.get("camera_and_effects") or ""),
                audio_and_tts=str(body.get("audio_and_tts") or ""),
            )
            OTAUpdaterManager.build_local_version_manifest()
            if res.get("ok"):
                r_obj = res["recipe"]
                PERSONA_ENGINE.emit_log(
                    cid,
                    2,
                    f"➕ [Kho Key Ngách]: Đã tích hợp Gói Key Ngách mới 『{r_obj['niche_name']}』 (`{r_obj['niche_key']}`) kèm công thức Kịch bản & Edit Video riêng!",
                )
            self._send_json(res)
            return

        if action == "check_ota_update":
            res = OTAUpdaterManager.check_for_remote_updates()
            self._send_json(res)
            return

        if action == "apply_ota_update":
            res = OTAUpdaterManager.apply_remote_ota_update()
            if res.get("ok"):
                PERSONA_ENGINE.emit_log(cid, 0, f"☁️ [GitHub OTA Hot-Update]: {res.get('message')}")
            self._send_json(res)
            return

        if action == "admin_publish_ota_to_github":
            commit_msg = str(body.get("commit_message") or "").strip()
            res = OTAUpdaterManager.admin_publish_update_to_github(commit_message=commit_msg)
            if res.get("ok"):
                PERSONA_ENGINE.emit_log(cid, 0, f"🚀 [Publish GitHub OTA]: {res.get('message')}")
            self._send_json(res)
            return

        self._send_json({"ok": False, "error": f"Unknown action: {action}"}, status=400)


def autopilot_daemon_loop() -> None:
    """
    [v3.7] Luồng nền kiểm tra lịch hẹn Autopilot mỗi 45 giây — TÁCH BIỆT 2 NHÁNH ĐỘC LẬP:
    1. Nhánh `auto_pre_upload_enabled`:
       - Vào lúc `pre_upload_trigger_time` (ví dụ `13:30` trưa), tự động kiểm tra thư mục Video Cấp Sẵn (`08_READY_VIDEOS_TO_UPLOAD` + `batch_queue_dir`),
         ĐẨY VIDEO LÊN TRƯỚC và cài đặt giờ Public tự động vào `scheduled_publish_time` (ví dụ `20:00` tối) để đạt hiệu quả cao nhất!
    2. Nhánh `auto_warmup_enabled`:
       - Tự động chạy phiên Nuôi theo chế độ đã chọn (`FULL_OMNI`, `YOUTUBE_DEEP_ONLY`, hoặc `GMAIL_ONLY`).
    3. Thực thi tuần tự từng kênh một (`max_concurrent_channels = 1`), và mọi tác vụ đều có Cổng Kiểm Tra Đăng Nhập Trước Khi Chạy!
    """
    while True:
        try:
            reg = load_registry()
            all_channels = reg.get("channels", [])
            if any(c.get("status") not in (None, "IDLE", "STOPPED", "LOGIN_REQUIRED") for c in all_channels):
                time.sleep(45)
                continue

            now_dt = datetime.now()
            today_str = now_dt.strftime("%Y-%m-%d")
            now_hm = now_dt.strftime("%H:%M")
            for ch in all_channels:
                cid = ch.get("channel_id")
                if not cid:
                    continue
                if ch.get("status") not in (None, "IDLE", "STOPPED"):
                    continue
                ch_folder = os.path.join(BASE_DIR, "CHANNELS_DATA", cid)
                sched = DailyAutopilotScheduler.load_or_init_schedule(ch_folder, cid)
                if sched.get("today_date") != today_str:
                    sched = DailyAutopilotScheduler.update_schedule_config(
                        ch_folder,
                        cid,
                        {
                            "today_date": today_str,
                            "morning_done_today": False,
                            "afternoon_done_today": False,
                            "pre_upload_done_today": False,
                        },
                    )

                # NHÁNH 1 (ĐỘC LẬP): TỰ ĐỘNG ĐẨY VIDEO LÊN TRƯỚC & SETUP GIỜ PUBLIC
                if sched.get("auto_pre_upload_enabled") and not sched.get("pre_upload_done_today"):
                    pre_up_time = sched.get("pre_upload_trigger_time", "13:30")
                    pub_time = sched.get("scheduled_publish_time", "20:00")
                    if now_hm >= pre_up_time:
                        DailyAutopilotScheduler.update_schedule_config(
                            ch_folder,
                            cid,
                            {
                                "pre_upload_done_today": True,
                                "last_pre_upload_at": f"{today_str} {now_hm} (Hẹn Public: {pub_time})",
                            },
                        )
                        ch_batch_dir = ch.get("batch_queue_dir") or r"D:\KEY NHẬT\20-30"
                        threading.Thread(
                            target=YouTubeStudioAutoUploader.upload_next_pending_episode_from_queue,
                            kwargs={
                                "channel": ch,
                                "parent_batch_dir": ch_batch_dir,
                                "visibility_mode": "SCHEDULE",
                                "scheduled_publish_time": pub_time,
                                "emit_log_fn": PERSONA_ENGINE.emit_log,
                            },
                            daemon=True,
                        ).start()
                        break

                # NHÁNH 2 (ĐỘC LẬP): TỰ ĐỘNG NUÔI KÊNH & GMAIL
                if sched.get("auto_warmup_enabled") or sched.get("autopilot_enabled"):
                    m_time = sched.get("today_morning_trigger_time", "09:30")
                    a_time = sched.get("today_afternoon_trigger_time", "15:30")
                    w_mode = sched.get("warmup_mode", "FULL_OMNI")
                    if not sched.get("morning_done_today") and now_hm >= m_time and now_dt.hour < 13:
                        DailyAutopilotScheduler.update_schedule_config(
                            ch_folder,
                            cid,
                            {
                                "morning_done_today": True,
                                "last_triggered_at": f"{today_str} {now_hm} (Sáng - {w_mode})",
                            },
                        )
                        threading.Thread(
                            target=PERSONA_ENGINE.run_daily_persona_warmup_session,
                            kwargs={"channel": ch, "num_videos_override": None, "demo_fast_mode": False, "warmup_mode": w_mode},
                            daemon=True,
                        ).start()
                        break
                    elif not sched.get("afternoon_done_today") and now_hm >= a_time and now_dt.hour >= 14:
                        DailyAutopilotScheduler.update_schedule_config(
                            ch_folder,
                            cid,
                            {
                                "afternoon_done_today": True,
                                "last_triggered_at": f"{today_str} {now_hm} (Chiều - {w_mode})",
                            },
                        )
                        threading.Thread(
                            target=PERSONA_ENGINE.run_daily_persona_warmup_session,
                            kwargs={"channel": ch, "num_videos_override": None, "demo_fast_mode": False, "warmup_mode": w_mode},
                            daemon=True,
                        ).start()
                        break
        except Exception:
            pass
        time.sleep(45)


def main():
    os.makedirs(LOGS_DIR, exist_ok=True)
    reg = load_registry()
    for ch in reg.get("channels", []):
        ChannelScannerAndAnalyticsEngine.ensure_channel_folder_structure(ch)
    DailyMasterTimelineCalculator.calculate_daily_master_plan(reg.get("channels", []))
    AI_SUPERVISOR.start_background_watchdog_loop()
    threading.Thread(target=autopilot_daemon_loop, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), EnterpriseDashboardHandler)
    print(f"[YouTube Enterprise AI Studio] Server listening on http://127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()

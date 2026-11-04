# -*- coding: utf-8 -*-
"""
YOUTUBE ENTERPRISE MULTI-AGENT STUDIO v3.9 — NATIVE WINDOWS PC DESKTOP APPLICATION (OTA HOT-UPDATE READY)
Chạy trực tiếp dưới dạng Phần mềm Desktop Windows độc lập (Không hiện cửa sổ CMD đen,
không có thanh địa chỉ trình duyệt, hỗ trợ Cập Nhật Từ Xa Qua GitHub OTA không cần tải lại .exe).
"""

import importlib.util
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer

# Ưu tiên nạp code mới nhất từ thư mục ngoài đĩa cứng (nơi chứa .exe) để hỗ trợ OTA Hot-Update không cần tải lại .exe
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR in sys.path:
    sys.path.remove(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# Nạp động các mô-đun bên ngoài thư mục cài đặt nếu đã được cập nhật qua GitHub OTA
def _preload_external_ota_modules() -> None:
    ext_engine_dir = os.path.join(BASE_DIR, "engine")
    if os.path.isdir(ext_engine_dir):
        for fname in os.listdir(ext_engine_dir):
            if fname.endswith(".py") and fname != "__init__.py":
                mod_name = f"engine.{fname[:-3]}"
                fpath = os.path.join(ext_engine_dir, fname)
                try:
                    spec = importlib.util.spec_from_file_location(mod_name, fpath)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        sys.modules[mod_name] = mod
                        spec.loader.exec_module(mod)
                except Exception:
                    pass
    ext_srv = os.path.join(BASE_DIR, "youtube_enterprise_server.py")
    if os.path.isfile(ext_srv):
        try:
            spec = importlib.util.spec_from_file_location("youtube_enterprise_server", ext_srv)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["youtube_enterprise_server"] = mod
                spec.loader.exec_module(mod)
        except Exception:
            pass

_preload_external_ota_modules()

from youtube_enterprise_server import (
    AI_SUPERVISOR,
    DailyMasterTimelineCalculator,
    EnterpriseDashboardHandler,
    HOST,
    PORT,
    autopilot_daemon_loop,
    load_registry,
    ChannelScannerAndAnalyticsEngine,
)


def _is_server_listening(host: str = HOST, port: int = PORT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except Exception:
        return False


def start_background_engine() -> None:
    """Khởi động Engine điều khiển, AI Supervisor 24/7 và bộ hẹn giờ Autopilot trong luồng ngầm."""
    reg = load_registry()
    for ch in reg.get("channels", []):
        ChannelScannerAndAnalyticsEngine.ensure_channel_folder_structure(ch)
    DailyMasterTimelineCalculator.calculate_daily_master_plan(reg.get("channels", []))

    if not _is_server_listening(HOST, PORT):
        AI_SUPERVISOR.start_background_watchdog_loop()
        t_auto = threading.Thread(target=autopilot_daemon_loop, daemon=True)
        t_auto.start()

        def _serve():
            try:
                server = ThreadingHTTPServer((HOST, PORT), EnterpriseDashboardHandler)
                server.serve_forever()
            except Exception:
                pass

        t_srv = threading.Thread(target=_serve, daemon=True)
        t_srv.start()

        for _ in range(30):
            if _is_server_listening(HOST, PORT):
                break
            time.sleep(0.1)


def launch_pc_desktop_window() -> None:
    start_background_engine()
    app_url = f"http://{HOST}:{PORT}"
    app_title = "🎬 YouTube Enterprise Multi-Agent Studio v3.5 — PC Desktop App (Nhật • Mỹ • Mexico)"

    # Ưu tiên 1: Mở cửa sổ Windows Desktop Native bằng PyWebView (Microsoft Edge WebView2)
    try:
        import webview  # type: ignore

        window = webview.create_window(
            title=app_title,
            url=app_url,
            width=1420,
            height=880,
            min_size=(1020, 660),
            resizable=True,
            text_select=True,
        )
        webview.start()
        os._exit(0)
        return
    except Exception:
        pass

    # Ưu tiên 2 (Khi copy sang máy tính mới chưa cài pywebview): Mở cửa sổ App Mode độc lập (Không thanh địa chỉ, không tab)
    browser_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    browser_exe = next((p for p in browser_candidates if os.path.isfile(p)), None)
    if browser_exe:
        ui_shell_dir = os.path.join(BASE_DIR, "CHANNELS_DATA", "_PC_APP_UI_SHELL")
        os.makedirs(ui_shell_dir, exist_ok=True)
        t0 = time.time()
        proc = subprocess.Popen(
            [
                browser_exe,
                f"--app={app_url}",
                f"--user-data-dir={ui_shell_dir}",
                "--window-size=1420,880",
                "--window-position=40,40",
                "--no-first-run",
                "--no-default-browser-check",
            ]
        )
        proc.wait()
        # Nếu cửa sổ _PC_APP_UI_SHELL đã mở sẵn từ trước, Chrome sẽ chuyển tiêu điểm sang cửa sổ cũ và thoát ngay (<3s).
        # Khi đó giữ Server chạy ngầm cho đến khi người dùng bấm nút 「📴 Thoát App」.
        if (time.time() - t0) < 3.5:
            while True:
                time.sleep(30)
        os._exit(0)


if __name__ == "__main__":
    launch_pc_desktop_window()

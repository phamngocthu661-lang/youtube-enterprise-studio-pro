# -*- coding: utf-8 -*-
"""
Bộ Quản Lý Đa Profile Chrome Cố Định + Khóa Cứng Tối Đa 2 Tab (TabGuard) + Hỗ Trợ Proxy
Dành cho Hệ Thống Tập Đoàn Agent Quản Lý & Nuôi Đa Kênh YouTube (Port 8077)
- Tích hợp cơ chế `_spawn_on_interactive_desktop` qua `schtasks /IT` + CDP `Browser.setWindowBounds` / `Page.bringToFront`
  để cửa sổ Chrome luôn hiện nổi trực tiếp trên màn hình Desktop thật của người dùng (kể cả khi Server chạy ngầm).
- Loại bỏ các cờ dòng lệnh nhạy cảm (`--disable-blink-features=AutomationControlled`) để đăng nhập Gmail & YouTube Studio
  mượt 100% không bị Google cảnh báo bảo mật.
"""

import base64
from datetime import datetime
import json
import os
import random
import subprocess
import threading
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

BASE_STUDIO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

PORT_LOCKS: Dict[int, threading.Lock] = {}


def get_port_lock(port: int) -> threading.Lock:
    if port not in PORT_LOCKS:
        PORT_LOCKS[port] = threading.Lock()
    return PORT_LOCKS[port]


def find_chrome_executable() -> str:
    for path in CHROME_CANDIDATES:
        if os.path.isfile(path):
            return path
    return "chrome.exe"


class TabGuard:
    """
    Bộ Khóa Cứng 1 Tab Đang Dùng (Single Active Tab Lock):
    - Chỉ mở duy nhất 1 Tab đang sử dụng để tương tác/xem video/quét kênh.
    - Bất kỳ tab nào không dùng hoặc tab thừa sinh ra đều bị đóng ngay lập tức.
    """

    MAX_TABS = 1

    @staticmethod
    def list_page_targets(cdp_port: int, timeout: float = 3.0) -> List[Dict[str, Any]]:
        url = f"http://127.0.0.1:{cdp_port}/json/list"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "YouTubeEnterpriseTabGuard/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                items = json.loads(resp.read().decode("utf-8", errors="replace"))
            pages = []
            for item in items:
                if item.get("type") != "page":
                    continue
                page_url = item.get("url", "")
                if page_url.startswith("devtools://") or page_url.startswith("chrome-extension://"):
                    continue
                pages.append(item)
            return pages
        except Exception:
            return []

    @classmethod
    def enforce_max_two_tabs(cls, cdp_port: int, keep_tab_id: Optional[str] = None, max_tabs: int = 1) -> List[Dict[str, Any]]:
        """
        Kiểm tra số lượng tab hiện tại. Nếu > max_tabs (mặc định = 1 tab duy nhất) thì đóng ngay mọi tab không dùng.
        """
        limit = max(1, int(max_tabs or cls.MAX_TABS))
        pages = cls.list_page_targets(cdp_port)
        if len(pages) <= limit:
            return pages

        kept: List[Dict[str, Any]] = []
        to_close: List[Dict[str, Any]] = []

        if keep_tab_id:
            for p in pages:
                if p.get("id") == keep_tab_id and len(kept) < limit:
                    kept.append(p)
        for p in pages:
            if p in kept:
                continue
            if len(kept) < limit:
                kept.append(p)
            else:
                to_close.append(p)

        for extra in to_close:
            tid = extra.get("id")
            if tid:
                cls.close_tab(cdp_port, tid)

        return kept

    @staticmethod
    def close_tab(cdp_port: int, target_id: str) -> bool:
        try:
            BrowserCDPManager.send_cdp_command(cdp_port, target_id, "Target.closeTarget", {"targetId": target_id}, timeout=2.0)
        except Exception:
            pass
        try:
            url = f"http://127.0.0.1:{cdp_port}/json/close/{target_id}"
            with urllib.request.urlopen(url, timeout=2.5) as _:
                return True
        except Exception:
            return False

    @classmethod
    def get_or_allocate_tab(cls, cdp_port: int, slot: int = 1, target_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Luôn dùng 1 Tab duy nhất đang hoạt động và đóng ngay tất cả các tab dư thừa không dùng.
        """
        pages = cls.enforce_max_two_tabs(cdp_port, max_tabs=1)

        if not pages:
            new_url = target_url or "https://www.youtube.com"
            created = cls._open_new_tab(cdp_port, new_url)
            return created

        target = pages[0]
        cls.enforce_max_two_tabs(cdp_port, keep_tab_id=target["id"], max_tabs=1)
        if target_url:
            cls.navigate_tab(cdp_port, target["id"], target_url)
        return target

    @staticmethod
    def _open_new_tab(cdp_port: int, url: str) -> Optional[Dict[str, Any]]:
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{cdp_port}/json/new?{url}",
                method="PUT",
                headers={"User-Agent": "YouTubeEnterpriseTabGuard/1.0"},
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{cdp_port}/json/new?{url}", timeout=4.0) as resp:
                    return json.loads(resp.read().decode("utf-8", errors="replace"))
            except Exception:
                return None

    @classmethod
    def navigate_tab(cls, cdp_port: int, target_id: str, url: str) -> bool:
        js = f"window.location.href = {json.dumps(url)}; true;"
        res = BrowserCDPManager.eval_js(cdp_port, target_id, js)
        return res is not None


class BrowserCDPManager:
    """
    Quản lý vòng đời Chrome Profile của từng Phòng Ban (Kênh) + Giao tiếp CDP
    """

    @staticmethod
    def is_port_open(cdp_port: int) -> bool:
        import socket
        try:
            with socket.create_connection(("127.0.0.1", int(cdp_port)), timeout=0.12):
                pass
            with urllib.request.urlopen(f"http://127.0.0.1:{cdp_port}/json/version", timeout=0.45) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def close_browser_on_port(cls, cdp_port: int) -> bool:
        """
        Đóng phiên Chrome đang mở trên cổng CDP (ví dụ khi muốn khởi động lại lên Interactive Desktop).
        """
        pages = TabGuard.list_page_targets(cdp_port)
        if not pages:
            return False
        try:
            import websocket  # type: ignore
            ws_url = pages[0].get("webSocketDebuggerUrl")
            if ws_url:
                ws = websocket.create_connection(ws_url, timeout=2.5)
                ws.send(json.dumps({"id": 1, "method": "Browser.close", "params": {}}))
                ws.close()
                time.sleep(1.0)
                return True
        except Exception:
            pass
        return False

    @classmethod
    def get_split_screen_bounds(cls, window_slot: str = "RIGHT") -> Dict[str, Any]:
        """
        [v3.8] Tính toán tọa độ chia đôi màn hình (Split-Screen Dual Browser):
        - "LEFT"  : Nửa màn hình bên Trái (x=0, y=0, w=50%, h=100%-taskbar)
        - "RIGHT" : Nửa màn hình bên Phải (x=50%, y=0, w=50%, h=100%-taskbar)
        - "FULL"  : Cửa sổ rộng mặc định ở giữa màn hình
        """
        screen_w, screen_h = 1920, 1080
        try:
            import ctypes
            user32 = ctypes.windll.user32
            w = int(user32.GetSystemMetrics(0))
            h = int(user32.GetSystemMetrics(1))
            if w >= 1024 and h >= 600:
                screen_w, screen_h = w, h
        except Exception:
            pass

        usable_h = max(680, screen_h - 48)
        half_w = max(640, screen_w // 2)
        slot = str(window_slot or "RIGHT").upper().strip()
        if slot == "LEFT":
            return {"left": 0, "top": 0, "width": half_w, "height": usable_h, "windowState": "normal", "slot": "LEFT"}
        if slot == "FULL":
            return {
                "left": 60,
                "top": 20,
                "width": max(1180, screen_w - 120),
                "height": max(700, usable_h - 20),
                "windowState": "normal",
                "slot": "FULL",
            }
        return {
            "left": half_w,
            "top": 0,
            "width": half_w,
            "height": usable_h,
            "windowState": "normal",
            "slot": "RIGHT",
        }

    @classmethod
    def bring_window_to_front(
        cls,
        cdp_port: int,
        side_by_side_right: bool = True,
        window_slot: Optional[str] = None,
    ) -> bool:
        """
        Đưa cửa sổ Chrome của kênh hiện nổi lên phía trước màn hình người dùng
        bằng lệnh CDP `Browser.setWindowBounds` + `Page.bringToFront`.
        [v3.8] Hỗ trợ chia đôi màn hình `window_slot = "LEFT" | "RIGHT" | "FULL"`.
        """
        pages = TabGuard.list_page_targets(cdp_port)
        if not pages:
            return False
        effective_slot = window_slot if window_slot else ("RIGHT" if side_by_side_right else "FULL")
        calc_bounds = cls.get_split_screen_bounds(effective_slot)
        bounds = {
            "left": calc_bounds["left"],
            "top": calc_bounds["top"],
            "width": calc_bounds["width"],
            "height": calc_bounds["height"],
            "windowState": "normal",
        }
        try:
            import websocket  # type: ignore
            for p in pages:
                ws_url = p.get("webSocketDebuggerUrl")
                if not ws_url:
                    continue
                try:
                    ws = websocket.create_connection(ws_url, timeout=2.5)
                    ws.send(json.dumps({"id": 1, "method": "Browser.getWindowForTarget", "params": {}}))
                    r = json.loads(ws.recv())
                    wid = (r.get("result") or {}).get("windowId")
                    if wid:
                        ws.send(
                            json.dumps(
                                {
                                    "id": 2,
                                    "method": "Browser.setWindowBounds",
                                    "params": {"windowId": wid, "bounds": bounds},
                                }
                            )
                        )
                        ws.recv()
                    ws.send(json.dumps({"id": 3, "method": "Page.bringToFront", "params": {}}))
                    ws.recv()
                    ws.close()
                    return True
                except Exception:
                    pass
        except Exception:
            pass
        return False

    @classmethod
    def parse_and_prepare_proxy_for_profile(cls, profile_dir: str, proxy_raw: str) -> Dict[str, Any]:
        """
        [v3.6] Bộ Quản Lý & Cô Lập Proxy Riêng Cho Từng Chrome Profile (1 Profile = 1 Kênh = 1 Proxy Độc Lập):
        Hỗ trợ tự động nhận diện mọi định dạng Proxy phổ biến:
        1. `IP:Port` (ví dụ: `103.22.33.44:8080`)
        2. `IP:Port:Username:Password` (ví dụ: `103.22.33.44:8080:myuser:mypass`)
        3. `http://user:pass@IP:Port` hoặc `http://IP:Port`
        4. `socks5://user:pass@IP:Port` hoặc `socks5://IP:Port`
        Nếu Proxy có Username & Password, tự động sinh Chrome Extension xác thực riêng biệt nằm trong
        `PROFILES/<KENH>/_proxy_auth_ext` và gắn cờ chống rò rỉ WebRTC IP (`disable_non_proxied_udp`).
        """
        raw = (proxy_raw or "").strip()
        if not raw:
            return {
                "enabled": False,
                "scheme": "",
                "host": "",
                "port": "",
                "username": "",
                "password": "",
                "chrome_args_str": "",
                "chrome_args_list": [],
                "display_masked": "Mạng Gốc (Direct IP)",
            }

        scheme = "http"
        host = ""
        port = ""
        username = ""
        password = ""

        if "://" in raw:
            parts_scheme = raw.split("://", 1)
            scheme = parts_scheme[0].strip().lower() or "http"
            rest = parts_scheme[1].strip()
        else:
            rest = raw

        if "@" in rest:
            auth_part, host_part = rest.rsplit("@", 1)
            if ":" in auth_part:
                username, password = auth_part.split(":", 1)
            else:
                username = auth_part
            if ":" in host_part:
                host, port = host_part.rsplit(":", 1)
            else:
                host = host_part
        else:
            colon_parts = rest.split(":")
            if len(colon_parts) == 2:
                host, port = colon_parts[0], colon_parts[1]
            elif len(colon_parts) >= 4:
                host = colon_parts[0]
                port = colon_parts[1]
                username = colon_parts[2]
                password = ":".join(colon_parts[3:])
            else:
                host = rest

        host = host.strip()
        port = port.strip()
        username = username.strip()
        password = password.strip()

        if not host or not port:
            return {
                "enabled": False,
                "error": f"Định dạng Proxy không hợp lệ: {raw}",
                "chrome_args_str": "",
                "chrome_args_list": [],
                "display_masked": f"Lỗi định dạng ({raw})",
            }

        proxy_server_val = f"{scheme}://{host}:{port}"
        args_list = [
            f"--proxy-server={proxy_server_val}",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
            "--enforce-webrtc-ip-permission-check",
        ]
        args_str = (
            f'--proxy-server="{proxy_server_val}" '
            f"--force-webrtc-ip-handling-policy=disable_non_proxied_udp "
            f"--enforce-webrtc-ip-permission-check "
        )

        # Nếu có Username & Password -> Tự động tạo Chrome Proxy Auth Extension riêng trong thư mục Profile của kênh
        if username and password:
            ext_dir = os.path.join(profile_dir, "_proxy_auth_ext")
            os.makedirs(ext_dir, exist_ok=True)
            manifest_json = {
                "version": "1.0.0",
                "manifest_version": 2,
                "name": "Channel Dedicated Proxy Auth",
                "permissions": [
                    "proxy",
                    "tabs",
                    "unlimitedStorage",
                    "storage",
                    "<all_urls>",
                    "webRequest",
                    "webRequestBlocking",
                ],
                "background": {"scripts": ["background.js"]},
                "minimum_chrome_version": "22.0.0",
            }
            bg_js = (
                "var config = {\n"
                '    mode: "fixed_servers",\n'
                "    rules: {\n"
                "      singleProxy: {\n"
                f'        scheme: "{scheme}",\n'
                f'        host: "{host}",\n'
                f"        port: parseInt({port})\n"
                "      },\n"
                '      bypassList: ["localhost", "127.0.0.1"]\n'
                "    }\n"
                "  };\n"
                'chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});\n'
                "function callbackFn(details) {\n"
                "    return {\n"
                "        authCredentials: {\n"
                f'            username: {json.dumps(username)},\n'
                f'            password: {json.dumps(password)}\n'
                "        }\n"
                "    };\n"
                "}\n"
                "chrome.webRequest.onAuthRequired.addListener(\n"
                "    callbackFn,\n"
                '    {urls: ["<all_urls>"]},\n'
                '    ["blocking"]\n'
                ");\n"
            )
            try:
                with open(os.path.join(ext_dir, "manifest.json"), "w", encoding="utf-8") as mf:
                    json.dump(manifest_json, mf, indent=2)
                with open(os.path.join(ext_dir, "background.js"), "w", encoding="utf-8") as bf:
                    bf.write(bg_js)
                args_list.append(f"--load-extension={ext_dir}")
                args_str += f'--load-extension="{ext_dir}" '
            except Exception:
                pass

        masked = f"{scheme.upper()}://{host}:{port}" + (f" (Auth: {username}:***)" if username else " (IP Whitelist)")
        return {
            "enabled": True,
            "scheme": scheme,
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "chrome_args_str": args_str,
            "chrome_args_list": args_list,
            "display_masked": masked,
        }

    @classmethod
    def verify_proxy_or_direct_ip(cls, proxy_raw: str = "", profile_dir: str = "") -> Dict[str, Any]:
        """
        [v3.6] Kiểm tra kết nối Proxy hoặc IP trực tiếp của kênh:
        Trả về địa chỉ IP thực tế ra mạng (External IP), Quốc gia, Thành phố, Nhà mạng (ISP) và Độ trễ (ms).
        """
        t0 = time.time()
        parsed = cls.parse_and_prepare_proxy_for_profile(profile_dir or BASE_STUDIO_DIR, proxy_raw)
        if proxy_raw and proxy_raw.strip() and not parsed.get("enabled"):
            return {"ok": False, "error": parsed.get("error", "Proxy không hợp lệ")}

        handlers = []
        if parsed.get("enabled"):
            scheme = parsed["scheme"]
            host = parsed["host"]
            port = parsed["port"]
            user = parsed["username"]
            pw = parsed["password"]
            if user and pw:
                proxy_url = f"{scheme}://{user}:{pw}@{host}:{port}"
            else:
                proxy_url = f"{scheme}://{host}:{port}"
            handlers.append(urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))

        opener = urllib.request.build_opener(*handlers)
        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/?fields=status,message,country,countryCode,regionName,city,isp,query",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with opener.open(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            latency_ms = int((time.time() - t0) * 1000)
            if data.get("status") == "success":
                return {
                    "ok": True,
                    "ip": data.get("query", ""),
                    "country": data.get("country", ""),
                    "countryCode": data.get("countryCode", ""),
                    "city": data.get("city", ""),
                    "isp": data.get("isp", ""),
                    "latency_ms": latency_ms,
                    "proxy_mode": parsed.get("display_masked", "Direct IP"),
                }
        except Exception as e:
            err_msg = str(e)
            # Dự phòng qua ipinfo.io
            try:
                req2 = urllib.request.Request(
                    "https://ipinfo.io/json",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                )
                with opener.open(req2, timeout=8.0) as resp2:
                    data2 = json.loads(resp2.read().decode("utf-8", errors="replace"))
                latency_ms = int((time.time() - t0) * 1000)
                return {
                    "ok": True,
                    "ip": data2.get("ip", ""),
                    "country": data2.get("country", ""),
                    "countryCode": data2.get("country", ""),
                    "city": data2.get("city", ""),
                    "isp": data2.get("org", ""),
                    "latency_ms": latency_ms,
                    "proxy_mode": parsed.get("display_masked", "Direct IP"),
                }
            except Exception:
                return {
                    "ok": False,
                    "error": f"Không thể kết nối qua Proxy ({parsed.get('display_masked')}): {err_msg}",
                    "proxy_mode": parsed.get("display_masked", "Direct IP"),
                }
        return {"ok": False, "error": "Không lấy được thông tin IP"}

    @classmethod
    def _spawn_on_interactive_desktop(
        cls,
        profile_dir: str,
        cdp_port: int,
        proxy: str = "",
        initial_url: str = "https://www.youtube.com",
        channel_folder: Optional[str] = None,
        window_slot: str = "RIGHT",
    ) -> str:
        """
        Khởi chạy Chrome trực tiếp trên Interactive Desktop của người dùng (Session 1)
        thông qua Windows Task Scheduler (`/IT`) + tạo file `.bat` mở nhanh trong thư mục kênh.
        Đảm bảo mỗi Profile 1 Kênh riêng biệt + Gắn Proxy độc lập (hỗ trợ cả IP:Port và IP:Port:User:Pass).
        [v3.8] Hỗ trợ chia đôi màn hình `window_slot = "LEFT" | "RIGHT" | "FULL"`.
        """
        os.makedirs(profile_dir, exist_ok=True)
        chrome_exe = find_chrome_executable()
        proxy_cfg = cls.parse_and_prepare_proxy_for_profile(profile_dir, proxy)
        proxy_arg = proxy_cfg.get("chrome_args_str", "")
        b = cls.get_split_screen_bounds(window_slot)
        win_pos_arg = f"--window-position={b['left']},{b['top']} --window-size={b['width']},{b['height']}"

        bat_content = (
            f"@echo off\n"
            f"chcp 65001 >nul\n"
            f'start "" "{chrome_exe}" '
            f"--remote-debugging-port={cdp_port} --remote-allow-origins=* "
            f'--user-data-dir="{profile_dir}" '
            f"--no-first-run --no-default-browser-check "
            f"--disable-background-timer-throttling --disable-renderer-backgrounding "
            f"--disable-backgrounding-occluded-windows "
            f"{proxy_arg}"
            f'{win_pos_arg} --new-window "{initial_url}"\n'
        )

        os.makedirs(BASE_STUDIO_DIR, exist_ok=True)
        bat_path = os.path.join(BASE_STUDIO_DIR, f"MO_PROFILE_PORT_{cdp_port}.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        if channel_folder:
            os.makedirs(channel_folder, exist_ok=True)
            ch_bat = os.path.join(channel_folder, "MO_PROFILE_DANG_NHAP_KENH.bat")
            with open(ch_bat, "w", encoding="utf-8") as f:
                f.write(bat_content)

        task_name = f"YouTubeEnterpriseChrome_{cdp_port}"
        try:
            subprocess.run(
                [
                    "schtasks",
                    "/Create",
                    "/TN",
                    task_name,
                    "/TR",
                    f'"{bat_path}"',
                    "/SC",
                    "ONCE",
                    "/ST",
                    "00:00",
                    "/IT",
                    "/F",
                ],
                capture_output=True,
                timeout=5,
            )
            subprocess.run(["schtasks", "/Run", "/TN", task_name], capture_output=True, timeout=5)
        except Exception:
            popen_args = [
                chrome_exe,
                f"--remote-debugging-port={cdp_port}",
                "--remote-allow-origins=*",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                f"--window-position={b['left']},{b['top']}",
                f"--window-size={b['width']},{b['height']}",
            ]
            popen_args.extend(proxy_cfg.get("chrome_args_list", []))
            popen_args.extend(["--new-window", initial_url])
            subprocess.Popen(popen_args)
        return bat_path

    @classmethod
    def launch_channel_browser(
        cls,
        profile_dir: str,
        cdp_port: int,
        proxy: str = "",
        initial_url: str = "https://www.youtube.com",
        side_by_side_right: bool = True,
        channel_folder: Optional[str] = None,
        force_restart: bool = False,
        window_slot: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Khởi chạy Chrome thật với thư mục Profile cố định của kênh và cổng CDP riêng.
        Luôn đưa cửa sổ nổi lên màn hình chính của người dùng.
        [v3.8] Hỗ trợ chia đôi màn hình `window_slot = "LEFT" | "RIGHT" | "FULL"`.
        """
        os.makedirs(profile_dir, exist_ok=True)
        effective_slot = window_slot if window_slot else ("RIGHT" if side_by_side_right else "FULL")

        if force_restart and cls.is_port_open(cdp_port):
            cls.close_browser_on_port(cdp_port)
            time.sleep(1.0)

        if cls.is_port_open(cdp_port):
            pages = TabGuard.enforce_max_two_tabs(cdp_port)
            cls.bring_window_to_front(cdp_port, side_by_side_right=side_by_side_right, window_slot=effective_slot)
            return {
                "ok": True,
                "already_running": True,
                "cdp_port": cdp_port,
                "profile_dir": profile_dir,
                "open_tabs": len(pages),
                "window_slot": effective_slot,
            }

        bat_path = cls._spawn_on_interactive_desktop(
            profile_dir=profile_dir,
            cdp_port=cdp_port,
            proxy=proxy,
            initial_url=initial_url,
            channel_folder=channel_folder,
            window_slot=effective_slot,
        )

        for _ in range(22):
            time.sleep(0.4)
            if cls.is_port_open(cdp_port):
                break

        pages = TabGuard.enforce_max_two_tabs(cdp_port)
        cls.bring_window_to_front(cdp_port, side_by_side_right=side_by_side_right, window_slot=effective_slot)
        return {
            "ok": cls.is_port_open(cdp_port),
            "already_running": False,
            "cdp_port": cdp_port,
            "profile_dir": profile_dir,
            "launcher_bat": bat_path,
            "open_tabs": len(pages),
            "window_slot": effective_slot,
        }

    @classmethod
    def open_gmail_and_channel_login(
        cls,
        profile_dir: str,
        cdp_port: int,
        proxy: str = "",
        channel_folder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Mở cửa sổ Chrome Profile của kênh nổi lên màn hình chính để người dùng đăng nhập Gmail & Kênh YouTube:
        - Tab #1: Trang đăng nhập Google / YouTube (`https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com`)
        - Tab #2: YouTube Studio (`https://studio.youtube.com`)
        - Khóa cứng tối đa 2 Tab.
        """
        login_url = "https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fwww.youtube.com%2F"
        info = cls.launch_channel_browser(
            profile_dir=profile_dir,
            cdp_port=cdp_port,
            proxy=proxy,
            initial_url=login_url,
            side_by_side_right=True,
            channel_folder=channel_folder,
        )
        tab1 = TabGuard.get_or_allocate_tab(cdp_port, slot=1)
        if tab1:
            cur_url = tab1.get("url", "")
            if "youtube.com" in cur_url:
                has_avatar = cls.eval_js(
                    cdp_port,
                    tab1["id"],
                    "Boolean(document.querySelector('button#avatar-btn'))",
                )
                if not has_avatar:
                    TabGuard.navigate_tab(cdp_port, tab1["id"], login_url)
            elif "accounts.google.com" not in cur_url:
                TabGuard.navigate_tab(cdp_port, tab1["id"], login_url)

        pages = TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=tab1["id"] if tab1 else None, max_tabs=1)
        cls.bring_window_to_front(cdp_port, side_by_side_right=True)
        info["open_tabs"] = len(pages)
        return info

    @classmethod
    def send_cdp_command(cls, cdp_port: int, target_id: str, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 8.0) -> Optional[Dict[str, Any]]:
        pages = TabGuard.list_page_targets(cdp_port)
        ws_url = None
        for p in pages:
            if p.get("id") == target_id:
                ws_url = p.get("webSocketDebuggerUrl")
                break
        if not ws_url and pages:
            ws_url = pages[0].get("webSocketDebuggerUrl")
        if not ws_url:
            return None

        try:
            import websocket  # type: ignore
            ws = websocket.create_connection(ws_url, timeout=timeout)
            try:
                msg_id = random.randint(1000, 999999)
                payload = {"id": msg_id, "method": method, "params": params or {}}
                ws.send(json.dumps(payload))
                deadline = time.time() + timeout
                while time.time() < deadline:
                    raw = ws.recv()
                    data = json.loads(raw)
                    if data.get("id") == msg_id:
                        return data.get("result")
            finally:
                ws.close()
        except Exception:
            return None
        return None

    @classmethod
    def eval_js(cls, cdp_port: int, target_id: str, expression: str, await_promise: bool = True, timeout: float = 10.0) -> Any:
        with get_port_lock(cdp_port):
            res = cls.send_cdp_command(
                cdp_port,
                target_id,
                "Runtime.evaluate",
                {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": await_promise,
                },
                timeout=timeout,
            )
            if not res:
                return None
            return res.get("result", {}).get("value")

    _last_mouse_pos: Dict[int, tuple] = {}

    @classmethod
    def hardware_bezier_move_and_click(
        cls, cdp_port: int, target_id: str, target_x: float, target_y: float, click: bool = True
    ) -> bool:
        """
        [ANTI-BOTGUARD v3.0] Di chuyển chuột theo đường cong Bézier bậc 3 có gia tốc người thật
        và bấm chuột bằng lệnh phần cứng CDP `Input.dispatchMouseEvent` -> Đảm bảo 100% `event.isTrusted === true`!
        Không bao giờ dùng `el.click()` của JS hay sửa đổi CSS/DOM trên trang YouTube.
        """
        pages = TabGuard.list_page_targets(cdp_port)
        ws_url = None
        for p in pages:
            if p.get("id") == target_id:
                ws_url = p.get("webSocketDebuggerUrl")
                break
        if not ws_url and pages:
            ws_url = pages[0].get("webSocketDebuggerUrl")
        if not ws_url:
            return False

        start_x, start_y = cls._last_mouse_pos.get(cdp_port, (random.randint(320, 680), random.randint(220, 480)))
        end_x = max(12.0, float(target_x) + random.uniform(-3.5, 3.5))
        end_y = max(12.0, float(target_y) + random.uniform(-2.5, 2.5))

        # Tạo 2 điểm điều khiển đường cong Bézier tự nhiên
        ctrl1_x = start_x + (end_x - start_x) * random.uniform(0.22, 0.42) + random.uniform(-45, 45)
        ctrl1_y = start_y + (end_y - start_y) * random.uniform(0.18, 0.38) + random.uniform(-35, 35)
        ctrl2_x = start_x + (end_x - start_x) * random.uniform(0.62, 0.84) + random.uniform(-30, 30)
        ctrl2_y = start_y + (end_y - start_y) * random.uniform(0.60, 0.85) + random.uniform(-25, 25)

        steps = random.randint(9, 15)
        try:
            import websocket  # type: ignore
            ws = websocket.create_connection(ws_url, timeout=6.0)
            try:
                msg_id = 100
                for i in range(1, steps + 1):
                    t = i / float(steps)
                    # Ease-in-out smoothing
                    u = 1.0 - t
                    bx = (u**3) * start_x + 3 * (u**2) * t * ctrl1_x + 3 * u * (t**2) * ctrl2_x + (t**3) * end_x
                    by = (u**3) * start_y + 3 * (u**2) * t * ctrl1_y + 3 * u * (t**2) * ctrl2_y + (t**3) * end_y
                    msg_id += 1
                    ws.send(
                        json.dumps(
                            {
                                "id": msg_id,
                                "method": "Input.dispatchMouseEvent",
                                "params": {"type": "mouseMoved", "x": round(bx, 1), "y": round(by, 1)},
                            }
                        )
                    )
                    ws.recv()
                    time.sleep(random.uniform(0.012, 0.028))

                cls._last_mouse_pos[cdp_port] = (end_x, end_y)

                if click:
                    time.sleep(random.uniform(0.04, 0.11))
                    msg_id += 1
                    ws.send(
                        json.dumps(
                            {
                                "id": msg_id,
                                "method": "Input.dispatchMouseEvent",
                                "params": {
                                    "type": "mousePressed",
                                    "x": round(end_x, 1),
                                    "y": round(end_y, 1),
                                    "button": "left",
                                    "buttons": 1,
                                    "clickCount": 1,
                                },
                            }
                        )
                    )
                    ws.recv()
                    time.sleep(random.uniform(0.065, 0.145))
                    msg_id += 1
                    ws.send(
                        json.dumps(
                            {
                                "id": msg_id,
                                "method": "Input.dispatchMouseEvent",
                                "params": {
                                    "type": "mouseReleased",
                                    "x": round(end_x, 1),
                                    "y": round(end_y, 1),
                                    "button": "left",
                                    "buttons": 0,
                                    "clickCount": 1,
                                },
                            }
                        )
                    )
                    ws.recv()
                return True
            finally:
                ws.close()
        except Exception:
            return False

    @classmethod
    def hardware_press_key(cls, cdp_port: int, target_id: str, key: str, code: str, vk: int) -> bool:
        """
        Gửi phím bấm phần cứng thực tế (`isTrusted: true`) qua CDP `Input.dispatchKeyEvent`.
        """
        cls.send_cdp_command(
            cdp_port,
            target_id,
            "Input.dispatchKeyEvent",
            {"type": "keyDown", "key": key, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk},
            timeout=2.5,
        )
        time.sleep(random.uniform(0.05, 0.12))
        cls.send_cdp_command(
            cdp_port,
            target_id,
            "Input.dispatchKeyEvent",
            {"type": "keyUp", "key": key, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk},
            timeout=2.5,
        )
        return True

    @classmethod
    def human_type_in_selector(cls, cdp_port: int, target_id: str, selector: str, text: str, press_enter: bool = True) -> bool:
        """
        [ANTI-BOTGUARD v3.0] Di chuột Bézier tới ô input, click chuột thật (`isTrusted: true`),
        xóa nội dung cũ bằng phím Backspace và gõ từng ký tự với nhịp độ Gaussian tự nhiên.
        """
        rect = cls.eval_js(
            cdp_port,
            target_id,
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return null;
                const r = el.getBoundingClientRect();
                if (r.width <= 0 || r.height <= 0) return null;
                return {{ x: r.left + r.width * 0.35, y: r.top + r.height * 0.5, len: (el.value || '').length }};
            }})()
            """,
        )
        if not rect:
            return False

        cls.hardware_bezier_move_and_click(cdp_port, target_id, rect["x"], rect["y"], click=True)
        time.sleep(random.uniform(0.18, 0.35))

        # Nếu ô tìm kiếm đang có chữ cũ, bấm Ctrl+A và Backspace bằng phím cứng
        if rect.get("len", 0) > 0:
            cls.send_cdp_command(
                cdp_port,
                target_id,
                "Input.dispatchKeyEvent",
                {"type": "keyDown", "key": "a", "code": "KeyA", "windowsVirtualKeyCode": 65, "modifiers": 2},
                timeout=2.0,
            )
            cls.send_cdp_command(
                cdp_port,
                target_id,
                "Input.dispatchKeyEvent",
                {"type": "keyUp", "key": "a", "code": "KeyA", "windowsVirtualKeyCode": 65, "modifiers": 0},
                timeout=2.0,
            )
            time.sleep(0.08)
            cls.hardware_press_key(cdp_port, target_id, "Backspace", "Backspace", 8)
            time.sleep(0.18)

        for idx, ch in enumerate(text):
            cls.send_cdp_command(
                cdp_port,
                target_id,
                "Input.insertText",
                {"text": ch},
                timeout=3.0,
            )
            # Nhịp gõ phím biến thiên Gaussian + nghỉ nhẹ giữa các cụm từ
            base_delay = max(0.055, min(0.28, random.gauss(0.115, 0.045)))
            if ch in (" ", "　") or (idx > 0 and idx % random.randint(4, 7) == 0):
                base_delay += random.uniform(0.12, 0.32)
            time.sleep(base_delay)

        if press_enter:
            time.sleep(random.uniform(0.32, 0.75))
            cls.hardware_press_key(cdp_port, target_id, "Enter", "Enter", 13)
        return True

    @classmethod
    def human_scroll(
        cls,
        cdp_port: int,
        target_id: str,
        min_px: int = 280,
        max_px: int = 750,
        direction: int = 1,
        distance: Optional[int] = None,
    ) -> None:
        """
        [ANTI-BOTGUARD v3.0] Cuộn trang bằng con lăn chuột phần cứng (`Input.dispatchMouseEvent` type `mouseWheel`)
        chia thành 3–6 nấc lăn chuột tự nhiên (`event.isTrusted === true`), tuyệt đối không chỉ dùng `window.scrollBy`.
        """
        total_delta = (distance if distance is not None else random.randint(min_px, max_px)) * direction
        ticks = random.randint(3, 6)
        mx, my = cls._last_mouse_pos.get(cdp_port, (random.randint(420, 680), random.randint(320, 560)))

        pages = TabGuard.list_page_targets(cdp_port)
        ws_url = None
        for p in pages:
            if p.get("id") == target_id:
                ws_url = p.get("webSocketDebuggerUrl")
                break
        if not ws_url and pages:
            ws_url = pages[0].get("webSocketDebuggerUrl")
        if not ws_url:
            return

        try:
            import websocket  # type: ignore
            ws = websocket.create_connection(ws_url, timeout=5.0)
            try:
                for i in range(ticks):
                    tick_y = int(total_delta / ticks + random.uniform(-18, 18))
                    ws.send(
                        json.dumps(
                            {
                                "id": 300 + i,
                                "method": "Input.dispatchMouseEvent",
                                "params": {
                                    "type": "mouseWheel",
                                    "x": round(mx, 1),
                                    "y": round(my, 1),
                                    "deltaX": 0,
                                    "deltaY": tick_y,
                                },
                            }
                        )
                    )
                    ws.recv()
                    time.sleep(random.uniform(0.045, 0.115))
            finally:
                ws.close()
        except Exception:
            pass

    @classmethod
    def human_browse_scroll_pattern(cls, cdp_port: int, target_id: str, fast_mode: bool = False) -> None:
        """
        Mô phỏng cử chỉ người thật đang lăn chuột tìm kiếm và đọc tiêu đề trên danh sách YouTube:
        - Lăn chuột xuống nhẹ 280–420px -> dừng 1.5–2.2s rà mắt qua tiêu đề
        - Lăn chuột xuống tiếp 320–480px -> dừng 1.6–2.4s đọc tiêu đề
        - Lăn ngược nhẹ lên 180–260px như đang cân nhắc chọn video phù hợp nhất.
        """
        pause_scale = 0.55 if fast_mode else 1.0
        time.sleep(random.uniform(1.1, 1.8) * pause_scale)
        cls.human_scroll(cdp_port, target_id, min_px=260, max_px=390, direction=1)
        time.sleep(random.uniform(1.4, 2.2) * pause_scale)

        cls.human_scroll(cdp_port, target_id, min_px=310, max_px=460, direction=1)
        time.sleep(random.uniform(1.5, 2.4) * pause_scale)

        cls.human_scroll(cdp_port, target_id, min_px=200, max_px=320, direction=1)
        time.sleep(random.uniform(1.2, 1.9) * pause_scale)
        cls.human_scroll(cdp_port, target_id, min_px=190, max_px=290, direction=-1)
        time.sleep(random.uniform(1.1, 1.7) * pause_scale)

    @classmethod
    def human_scroll_to_and_click_video(
        cls,
        cdp_port: int,
        target_id: str,
        video_href: str,
        video_title: str = "",
    ) -> bool:
        """
        [ANTI-BOTGUARD v3.0 - ZERO DOM MUTATION & HARDWARE CLICK]:
        - Không bao giờ sửa `style.outline` trên trang YouTube.
        - Lăn chuột phần cứng (`mouseWheel`) đưa thẻ video vào vùng nhìn thấy trên màn hình,
          dừng 1.2s đọc tiêu đề, sau đó di chuột Bézier tới đúng tiêu đề và bấm chuột thật (`isTrusted: true`).
        """
        vid_id = ""
        if "v=" in (video_href or ""):
            vid_id = video_href.split("v=")[1].split("&")[0]

        js_get_video_box = f"""
        (() => {{
            const vidId = {json.dumps(vid_id)};
            const titleSub = {json.dumps((video_title or '')[:28])};
            const candidates = Array.from(document.querySelectorAll('a#video-title, a#video-title-link, a.yt-lockup-metadata-view-model__title, h3 a[href*="/watch?v="]'));
            for (const a of candidates) {{
                if (a.offsetParent === null) continue;
                const h = a.href || '';
                const t = (a.innerText || a.getAttribute('title') || '').trim();
                if ((vidId && h.includes('v=' + vidId)) || (titleSub && t.includes(titleSub))) {{
                    const r = a.getBoundingClientRect();
                    return {{
                        found: true,
                        x: r.left + Math.min(r.width * 0.45, 180),
                        y: r.top + r.height * 0.5,
                        top: r.top,
                        bottom: r.bottom,
                        vh: window.innerHeight
                    }};
                }}
            }}
            return {{ found: false }};
        }})()
        """
        # Cuộn bằng con lăn chuột thật cho tới khi thẻ video nằm trong tầm mắt (140px .. innerHeight - 120px)
        for _ in range(5):
            box = cls.eval_js(cdp_port, target_id, js_get_video_box) or {}
            if not box.get("found"):
                break
            top_y = float(box.get("top", 0))
            vh = float(box.get("vh", 900))
            if 130 <= top_y <= (vh - 120):
                break
            diff = int(top_y - (vh * 0.45))
            if abs(diff) < 60:
                break
            cls.human_scroll(cdp_port, target_id, distance=abs(diff), direction=1 if diff > 0 else -1)
            time.sleep(random.uniform(0.45, 0.85))

        box_final = cls.eval_js(cdp_port, target_id, js_get_video_box) or {}
        if box_final.get("found") and 60 <= float(box_final.get("y", 0)) <= float(box_final.get("vh", 900)) - 40:
            time.sleep(random.uniform(0.95, 1.55))
            if cls.hardware_bezier_move_and_click(cdp_port, target_id, box_final["x"], box_final["y"], click=True):
                return True

        if video_href:
            return TabGuard.navigate_tab(cdp_port, target_id, video_href)
        return False

    @classmethod
    def check_and_skip_youtube_ads(cls, cdp_port: int, target_id: str, max_wait_sec: float = 9.0) -> Dict[str, Any]:
        """
        [ANTI-BOTGUARD v3.0] Kiểm tra quảng cáo trên YouTube Player (#movie_player.ad-showing):
        - Chờ hết thời gian đếm ngược rồi di chuột Bézier bấm nút Bỏ qua (Skip Ad) bằng chuột phần cứng (`isTrusted: true`).
        """
        js_check_ad = r"""
        (() => {
            const player = document.querySelector('#movie_player');
            const isAdShowing = Boolean(
                (player && player.classList.contains('ad-showing')) ||
                document.querySelector('.ytp-ad-player-overlay, .ytp-ad-player-overlay-layout')
            );
            const overlayClose = document.querySelector('.ytp-ad-overlay-close-button');
            let overlayRect = null;
            if (overlayClose && overlayClose.offsetParent !== null) {
                const r = overlayClose.getBoundingClientRect();
                overlayRect = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
            }
            const skipBtn = document.querySelector(
                'button.ytp-skip-ad-button, button.ytp-ad-skip-button, button.ytp-ad-skip-button-modern, .ytp-skip-ad-button'
            );
            let skipRect = null;
            const canSkipNow = Boolean(
                skipBtn &&
                skipBtn.offsetParent !== null &&
                window.getComputedStyle(skipBtn).display !== 'none' &&
                window.getComputedStyle(skipBtn).opacity !== '0'
            );
            if (canSkipNow && skipBtn) {
                const sr = skipBtn.getBoundingClientRect();
                if (sr.width > 0 && sr.height > 0) {
                    skipRect = { x: sr.left + sr.width / 2, y: sr.top + sr.height / 2 };
                }
            }
            return { is_ad_showing: isAdShowing, can_skip_now: canSkipNow, skip_rect: skipRect, overlay_rect: overlayRect };
        })()
        """
        status = cls.eval_js(cdp_port, target_id, js_check_ad) or {}
        if status.get("overlay_rect"):
            ov = status["overlay_rect"]
            cls.hardware_bezier_move_and_click(cdp_port, target_id, ov["x"], ov["y"], click=True)

        if not status.get("is_ad_showing") and not status.get("can_skip_now"):
            return {"ad_detected": False, "skipped": False}

        deadline = time.time() + max_wait_sec
        while time.time() < deadline:
            if status.get("can_skip_now") and status.get("skip_rect"):
                time.sleep(random.uniform(0.75, 1.45))
                sr = status["skip_rect"]
                clicked = cls.hardware_bezier_move_and_click(cdp_port, target_id, sr["x"], sr["y"], click=True)
                return {"ad_detected": True, "skipped": bool(clicked)}
            time.sleep(1.0)
            status = cls.eval_js(cdp_port, target_id, js_check_ad) or {}
            if not status.get("is_ad_showing"):
                return {"ad_detected": True, "skipped": True}

        return {"ad_detected": True, "skipped": False}

    @classmethod
    def perform_human_player_micro_interaction(cls, cdp_port: int, target_id: str) -> str:
        """
        [ANTI-BOTGUARD v3.0] Tương tác với màn hình Video Player bằng Phím Cứng & Chuột Cứng (`isTrusted: true`):
        - Di chuột Bézier qua màn hình video để đánh thức thanh công cụ.
        - Chọn ngẫu nhiên 1 thao tác bằng phím/chuột phần cứng thật:
          1. Tua tới nhẹ (+5s / +10s) bằng phím cứng `ArrowRight` (`isTrusted: true`, hiện hiệu ứng >> 5 giây của YouTube)
          2. Tua lùi lại (-5s / -10s) bằng phím cứng `ArrowLeft` (`isTrusted: true`, hiện hiệu ứng << 5 giây của YouTube)
          3. Tăng hoặc giảm âm lượng bằng phím mũi tên hoặc thanh âm lượng
          4. Bấm chuột thật vào nút Bánh răng Cài đặt chỉnh độ phân giải (1080p / 720p)
          5. Bấm phím cứng `k` (hoặc click màn hình video) để tạm dừng 2.5s đọc chữ rồi bấm xem tiếp
        """
        player_box = cls.eval_js(
            cdp_port,
            target_id,
            r"""
            (() => {
                const p = document.querySelector('#movie_player, video');
                if (!p) return { x: 420, y: 280 };
                const r = p.getBoundingClientRect();
                return { x: r.left + r.width * 0.48, y: r.top + r.height * 0.52 };
            })()
            """,
        ) or {"x": 420, "y": 280}

        # Đánh thức thanh công cụ bằng đường di chuột Bézier tự nhiên
        cls.hardware_bezier_move_and_click(cdp_port, target_id, player_box["x"], player_box["y"], click=False)

        choice = random.choice(["SEEK_FORWARD", "REWIND", "ADJUST_VOLUME", "CHANGE_RESOLUTION", "PAUSE_RESUME"])

        if choice == "SEEK_FORWARD":
            presses = random.choice([1, 2])
            for _ in range(presses):
                cls.hardware_press_key(cdp_port, target_id, "ArrowRight", "ArrowRight", 39)
                time.sleep(random.uniform(0.22, 0.45))
            return f"⏩ Bấm phím cứng ArrowRight tua tới +{presses * 5} giây (isTrusted=true)"

        if choice == "REWIND":
            presses = random.choice([1, 2])
            for _ in range(presses):
                cls.hardware_press_key(cdp_port, target_id, "ArrowLeft", "ArrowLeft", 37)
                time.sleep(random.uniform(0.22, 0.45))
            return f"⏪ Bấm phím cứng ArrowLeft tua lùi -{presses * 5} giây (isTrusted=true)"

        if choice == "ADJUST_VOLUME":
            # Bấm phím cứng 'm' nếu đang bị mute hoặc chỉnh âm lượng
            new_vol = round(random.uniform(0.42, 0.84), 2)
            vol_pct = int(new_vol * 100)
            cls.eval_js(
                cdp_port,
                target_id,
                f"(() => {{ const v = document.querySelector('video'); if (v) {{ v.muted = false; v.volume = {new_vol}; }} return {vol_pct}; }})()",
            )
            return f"🔊 Điều chỉnh âm lượng video sang mức {vol_pct}%"

        if choice == "CHANGE_RESOLUTION":
            gear_rect = cls.eval_js(
                cdp_port,
                target_id,
                r"""
                (() => {
                    const btn = document.querySelector('button.ytp-settings-button');
                    if (!btn) return null;
                    const r = btn.getBoundingClientRect();
                    return r.width > 0 ? { x: r.left + r.width / 2, y: r.top + r.height / 2 } : null;
                })()
                """,
            )
            if gear_rect:
                cls.hardware_bezier_move_and_click(cdp_port, target_id, gear_rect["x"], gear_rect["y"], click=True)
                time.sleep(0.75)
                q_rect = cls.eval_js(
                    cdp_port,
                    target_id,
                    r"""
                    (() => {
                        const items = Array.from(document.querySelectorAll('.ytp-settings-menu .ytp-menuitem'));
                        const qItem = items.find(el => {
                            const t = (el.innerText || '').toLowerCase();
                            return t.includes('chất lượng') || t.includes('quality') || t.includes('画質') || t.includes('1080p') || t.includes('720p');
                        });
                        if (!qItem) return null;
                        const r = qItem.getBoundingClientRect();
                        return r.width > 0 ? { x: r.left + r.width / 2, y: r.top + r.height / 2 } : null;
                    })()
                    """,
                )
                if q_rect:
                    cls.hardware_bezier_move_and_click(cdp_port, target_id, q_rect["x"], q_rect["y"], click=True)
                    time.sleep(0.75)
                    res_rect = cls.eval_js(
                        cdp_port,
                        target_id,
                        r"""
                        (() => {
                            const items = Array.from(document.querySelectorAll('.ytp-quality-menu .ytp-menuitem, .ytp-settings-menu .ytp-menuitem'));
                            const target = items.find(el => {
                                const t = (el.innerText || '');
                                return (t.includes('1080p') || t.includes('720p')) && !t.toLowerCase().includes('premium');
                            });
                            if (!target) return null;
                            const r = target.getBoundingClientRect();
                            return r.width > 0 ? { x: r.left + r.width / 2, y: r.top + r.height / 2, label: (target.innerText || '').trim().split('\n')[0] } : null;
                        })()
                        """,
                    )
                    if res_rect:
                        cls.hardware_bezier_move_and_click(cdp_port, target_id, res_rect["x"], res_rect["y"], click=True)
                        return f"⚙️ Di chuột Bézier bấm chọn độ phân giải {res_rect.get('label', '1080p HD')} (isTrusted=true)"
                # Đóng menu nếu chưa chọn
                cls.hardware_bezier_move_and_click(cdp_port, target_id, gear_rect["x"], gear_rect["y"], click=True)
            return "⚙️ Di chuột kiểm tra thanh cài đặt độ phân giải 1080p HD"

        # PAUSE_RESUME bằng phím cứng 'k' (phím tắt chuẩn của YouTube Player)
        cls.hardware_press_key(cdp_port, target_id, "k", "KeyK", 75)
        time.sleep(random.uniform(2.1, 3.4))
        cls.hardware_press_key(cdp_port, target_id, "k", "KeyK", 75)
        return "⏯️ Bấm phím cứng 'K' tạm dừng 2.5 giây đọc chữ trên màn hình rồi bấm xem tiếp (isTrusted=true)"

    @classmethod
    def apply_channel_locale_and_timezone_emulation(
        cls, cdp_port: int, target_id: str, language: str = "ja"
    ) -> Dict[str, Any]:
        """
        [v3.1] Đồng bộ Múi Giờ (Timezone) & Ngôn Ngữ Bản Địa (Accept-Language) theo từng Kênh:
        - Kênh Nhật (ja): Múi giờ Asia/Tokyo (GMT+9), Accept-Language: ja-JP,ja;q=0.9
        - Kênh Mỹ (en): Múi giờ America/New_York, Accept-Language: en-US,en;q=0.9
        - Kênh Mexico (es): Múi giờ America/Mexico_City, Accept-Language: es-MX,es;q=0.9
        """
        if language == "ja":
            tz_id = "Asia/Tokyo"
            accept_lang = "ja-JP,ja;q=0.9,vi;q=0.8,en-US;q=0.7"
        elif language == "es":
            tz_id = "America/Mexico_City"
            accept_lang = "es-MX,es;q=0.9,en-US;q=0.8"
        else:
            tz_id = "America/New_York"
            accept_lang = "en-US,en;q=0.9"

        cls.send_cdp_command(cdp_port, target_id, "Emulation.setTimezoneOverride", {"timezoneId": tz_id}, timeout=2.0)
        cls.send_cdp_command(cdp_port, target_id, "Network.enable", {}, timeout=2.0)
        cls.send_cdp_command(
            cdp_port,
            target_id,
            "Network.setExtraHTTPHeaders",
            {"headers": {"Accept-Language": accept_lang}},
            timeout=2.0,
        )
        return {"ok": True, "timezone": tz_id, "accept_language": accept_lang}

    @classmethod
    def setup_google_alerts_subscriptions(
        cls,
        cdp_port: int,
        target_id: str,
        language: str = "ja",
        channel_folder: str = "",
        emit_cb=None,
        force: bool = False,
        custom_topics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        [v3.2 - MULTI-KEY ACTIVE GMAIL FARMING] Tự động đăng ký nhận bản tin `Google Alerts` hằng ngày theo đúng Ngôn Ngữ & Từ Khóa của Key:
        - Nếu kênh có `custom_topics` / `seed_keywords` riêng (ví dụ: Key Nhật Drama, Key Mafia Mỹ, Key Homeless Mỹ, Key Bà Cô Mexico...), tự động lấy 3 chủ đề của chính Key đó!
        - Hỗ trợ đa quốc gia: `google.co.jp/alerts` (Nhật), `google.com.mx/alerts` (Mexico), `google.com/alerts` (Mỹ).
        """
        state_path = os.path.join(channel_folder, "11_GMAIL_TRUST_FARMING_STATE.json") if channel_folder else ""
        state_data: Dict[str, Any] = {}
        if state_path and os.path.exists(state_path):
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
            except Exception:
                state_data = {}

        if state_data.get("google_alerts_subscribed") and not force:
            return {
                "ok": True,
                "already_subscribed": True,
                "topics": state_data.get("subscribed_topics", []),
            }

        if custom_topics and len(custom_topics) > 0:
            topics = [str(t).strip()[:45] for t in custom_topics[:3] if str(t).strip()]
        elif language == "ja":
            topics = ["定年後の仕事", "60代 再就職 ハローワーク", "年金 65歳 働き方"]
        elif language == "es":
            topics = ["historias de familia México", "adultos mayores pensión México", "herencia familiar leyes"]
        else:
            topics = ["emotional family life stories", "abandoned property restoration", "personal finance retirement"]

        if language == "ja":
            alerts_url = "https://www.google.co.jp/alerts?hl=ja"
        elif language == "es":
            alerts_url = "https://www.google.com.mx/alerts?hl=es-419"
        else:
            alerts_url = "https://www.google.com/alerts?hl=en"
        TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=target_id, max_tabs=1)
        if emit_cb:
            emit_cb(
                f"🔔 [Nuôi Gmail Chủ Động - Google Alerts]: Mở {alerts_url} để đăng ký nhận bản tin tự động hằng ngày ({', '.join(topics)})..."
            )
        TabGuard.navigate_tab(cdp_port, target_id, alerts_url)
        time.sleep(3.8)

        created_topics: List[str] = []
        for topic in topics:
            # Tìm ô nhập chủ đề Google Alerts và danh sách cảnh báo đã có
            check_info = cls.eval_js(
                cdp_port,
                target_id,
                f"""
                (() => {{
                    const bodyText = document.body ? (document.body.innerText || '') : '';
                    const alreadyHas = bodyText.includes({json.dumps(topic)});
                    const inp = document.querySelector('#query_div input[type="text"], input[placeholder*="アラート"], input[placeholder*="alert"], input[type="text"]');
                    if (!inp) return {{ found_input: false, already_has: alreadyHas }};
                    const r = inp.getBoundingClientRect();
                    return {{
                        found_input: r.width > 0,
                        already_has: alreadyHas,
                        x: r.left + r.width * 0.35,
                        y: r.top + r.height * 0.5
                    }};
                }})()
                """,
            ) or {}

            if check_info.get("already_has"):
                created_topics.append(topic)
                continue

            if check_info.get("found_input"):
                cls.hardware_bezier_move_and_click(
                    cdp_port, target_id, check_info.get("x", 400), check_info.get("y", 220), click=True
                )
                time.sleep(0.35)
                # Xóa trắng ô nhập và gõ từng ký tự bằng phím cứng
                cls.eval_js(
                    cdp_port,
                    target_id,
                    """
                    (() => {
                        const inp = document.querySelector('#query_div input[type="text"], input[type="text"]');
                        if (inp) { inp.value = ''; inp.focus(); }
                        return true;
                    })()
                    """,
                )
                for ch_char in topic:
                    cls.send_cdp_command(
                        cdp_port,
                        target_id,
                        "Input.dispatchKeyEvent",
                        {"type": "char", "text": ch_char, "unmodifiedText": ch_char},
                        timeout=1.5,
                    )
                    time.sleep(random.uniform(0.05, 0.12))
                time.sleep(1.1)

                btn_info = cls.eval_js(
                    cdp_port,
                    target_id,
                    r"""
                    (() => {
                        const btn = document.querySelector('#create_alert, span.create_alert, div[role="button"]#create_alert');
                        if (btn) {
                            const r = btn.getBoundingClientRect();
                            if (r.width > 0) return { x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                        }
                        const allBtns = Array.from(document.querySelectorAll('span[role="button"], div[role="button"], button'));
                        const match = allBtns.find(b => {
                            const t = (b.innerText || '').trim();
                            return t.includes('アラートを作成') || t.toLowerCase().includes('create alert') || t.includes('Tạo cảnh báo');
                        });
                        if (match) {
                            const r = match.getBoundingClientRect();
                            if (r.width > 0) return { x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                        }
                        return null;
                    })()
                    """,
                )
                if btn_info:
                    cls.hardware_bezier_move_and_click(cdp_port, target_id, btn_info["x"], btn_info["y"], click=True)
                    created_topics.append(topic)
                    if emit_cb:
                        emit_cb(f"✅ [Google Alerts]: Đã đăng ký nhận bản tin email hằng ngày cho chủ đề 「{topic}」!")
                    time.sleep(1.8)

        if state_path:
            state_data["google_alerts_subscribed"] = True
            state_data["subscribed_topics"] = topics
            state_data["alerts_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                os.makedirs(os.path.dirname(state_path), exist_ok=True)
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        return {"ok": True, "subscribed_topics": created_topics or topics}

    @classmethod
    def warmup_gmail_inbox(
        cls,
        cdp_port: int,
        target_id: str,
        emit_cb=None,
        channel_folder: str = "",
        language: str = "ja",
        custom_topics: Optional[List[str]] = None,
        demo_fast_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        [ANTI-BOTGUARD v3.8.2] Chu Trình Nuôi Gmail Chuyên Sâu Như Người Thật (~3.5 – 4.5 Phút Riêng Phần Hộp Thư):
        1. Tự động kiểm tra & đăng ký Google Alerts theo đúng ngôn ngữ & từ khóa của Key.
        2. Mở Hòm thư Chính (#inbox), ưu tiên đọc 2–3 thư Chưa Đọc (Unread `tr.zA.zE`) bằng chuột Bézier & con lăn vật lý, dừng đọc kỹ từng đoạn 25–40 giây/thư.
        3. Click vào đường link an toàn bên trong nội dung Email (bài báo / thông báo Google / YouTube), cuộn đọc trang đích 25–35s rồi quay về Gmail.
        4. Gắn Ngôi Sao (`Star` ⭐) bằng chuột cứng (`isTrusted: true`) cho 1 email quan trọng để tăng tương tác hộp thư.
        5. Kiểm tra sang Tab Cập nhật (`#category/updates`) / Quảng cáo (`#category/promotions`) (15–20s) VÀ kiểm tra mục Thư rác (`#spam`) — giải cứu thư hợp lệ về Inbox.
        6. Gõ tìm kiếm nội bộ trên thanh Search của Gmail (`input[name="q"]`), đọc kết quả tìm kiếm 15–20s và lưu báo cáo vào `11_GMAIL_TRUST_FARMING_STATE.json`.
        """
        TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=target_id, max_tabs=1)
        cls.apply_channel_locale_and_timezone_emulation(cdp_port, target_id, language=language)

        # Bước 1: Đảm bảo tài khoản đã đăng ký Google Alerts để ngày nào cũng có thư mới gửi về
        if channel_folder and not demo_fast_mode:
            cls.setup_google_alerts_subscriptions(
                cdp_port,
                target_id,
                language=language,
                channel_folder=channel_folder,
                emit_cb=emit_cb,
                force=False,
                custom_topics=custom_topics,
            )

        # Bước 2: Mở Hòm thư đến chính (#inbox)
        if emit_cb:
            emit_cb("📧 [Nuôi Gmail Chuyên Sâu - Bước 1/5]: Mở Hòm thư Chính (https://mail.google.com/mail/u/0/#inbox) kiểm tra và rà soát danh sách thư...")
        TabGuard.navigate_tab(cdp_port, target_id, "https://mail.google.com/mail/u/0/#inbox")
        time.sleep(2.5 if demo_fast_mode else random.uniform(4.8, 6.5))

        cls.human_scroll(cdp_port, target_id, min_px=180, max_px=320, direction=1)
        time.sleep(1.0 if demo_fast_mode else random.uniform(2.8, 4.2))
        cls.human_scroll(cdp_port, target_id, min_px=160, max_px=280, direction=-1)
        time.sleep(0.8 if demo_fast_mode else random.uniform(2.2, 3.5))

        js_scan_emails = r"""
        (() => {
            const rows = Array.from(document.querySelectorAll('tr.zA'));
            return rows.slice(0, 12).map((r, idx) => {
                const senderEl = r.querySelector('.yW span[email], .yW span');
                const subjEl = r.querySelector('.bog span, .y6 span');
                const starEl = r.querySelector('span.T-KT');
                const rect = r.getBoundingClientRect();
                const starRect = starEl ? starEl.getBoundingClientRect() : null;
                const isUnread = r.classList.contains('zE');
                const isStarred = starEl ? (starEl.classList.contains('T-KT-Jp') || (starEl.getAttribute('aria-label') || '').includes('Starred') || (starEl.getAttribute('aria-label') || '').includes('Có gắn dấu sao')) : false;
                return {
                    index: idx,
                    is_unread: isUnread,
                    is_starred: isStarred,
                    sender: senderEl ? senderEl.innerText.trim() : 'Google / Dịch vụ',
                    subject: subjEl ? subjEl.innerText.trim() : (r.innerText || '').trim().slice(0, 60),
                    x: rect.left + Math.min(rect.width * 0.42, 270),
                    y: rect.top + rect.height * 0.5,
                    star_x: starRect && starRect.width > 0 ? starRect.left + starRect.width * 0.5 : 0,
                    star_y: starRect && starRect.height > 0 ? starRect.top + starRect.height * 0.5 : 0
                };
            }).filter(item => item.subject && item.subject.length > 1 && item.y > 80);
        })()
        """
        emails = cls.eval_js(cdp_port, target_id, js_scan_emails) or []
        read_subjects: List[str] = []
        clicked_links_in_mail: List[str] = []
        starred_count = 0
        rescued_spam_count = 0

        # Bước 2B: Gắn ngôi sao (Star ⭐) cho 1 email quan trọng nếu chưa gắn sao
        unstarred = [e for e in emails if not e.get("is_starred") and e.get("star_x", 0) > 10]
        if unstarred and random.random() < 0.80:
            star_target = unstarred[0]
            cls.hardware_bezier_move_and_click(
                cdp_port, target_id, star_target["star_x"], star_target["star_y"], click=True
            )
            starred_count += 1
            if emit_cb:
                emit_cb(
                    f"⭐ [Tương tác Gmail - Gắn Ngôi Sao]: Đã di chuột Bézier bấm gắn dấu sao quan trọng cho thư 「{star_target.get('subject', '')[:50]}」 (isTrusted=true)."
                )
            time.sleep(1.0 if demo_fast_mode else random.uniform(2.0, 3.2))

        # Bước 3: Mở đọc kỹ 2-3 email (Ưu tiên thư Chưa Đọc `is_unread == True`, dừng đọc 25-40s/thư) + Click vào link an toàn bên trong thư
        if emails:
            unread_pool = [e for e in emails if e.get("is_unread")]
            read_pool = [e for e in emails if not e.get("is_unread")]
            ordered_pool = unread_pool + read_pool
            max_pick = 1 if demo_fast_mode else random.choice([2, 3])
            pick_count = min(max_pick, len(ordered_pool))
            picked_emails = ordered_pool[:pick_count]

            for mail_idx, em in enumerate(picked_emails, start=1):
                subj = em.get("subject", "Email")
                sender = em.get("sender", "")
                unread_badge = "🆕 [THƯ MỚI CHƯA ĐỌC]" if em.get("is_unread") else "📩 [Thư trong hộp thư]"
                if emit_cb:
                    emit_cb(
                        f"{unread_badge} ({mail_idx}/{pick_count}) Di chuột Bézier click mở đọc kỹ thư từ 「{sender}」: “{subj[:65]}”..."
                    )
                cls.hardware_bezier_move_and_click(cdp_port, target_id, em.get("x", 360), em.get("y", 240), click=True)
                time.sleep(2.0 if demo_fast_mode else random.uniform(4.2, 6.2))

                # Cuộn đọc nội dung thư chậm rãi như người thật (3-4 nhịp cuộn, mỗi nhịp dừng đọc 5.5 - 9.0 giây)
                scroll_rounds = 1 if demo_fast_mode else random.randint(3, 4)
                for sc_i in range(scroll_rounds):
                    cls.human_scroll(cdp_port, target_id, min_px=180, max_px=340, direction=1)
                    pause_s = 1.5 if demo_fast_mode else random.uniform(5.5, 9.0)
                    time.sleep(pause_s)
                if not demo_fast_mode:
                    cls.human_scroll(cdp_port, target_id, min_px=140, max_px=240, direction=-1)
                    time.sleep(random.uniform(2.5, 4.0))

                # Quét tìm đường link bài viết/thông báo an toàn bên trong nội dung email (.a3s a)
                safe_link = cls.eval_js(
                    cdp_port,
                    target_id,
                    r"""
                    (() => {
                        const anchors = Array.from(document.querySelectorAll('.a3s a[href^="http"], div[role="listitem"] a[href^="http"]'));
                        const badWords = ['unsubscribe', 'optout', '退会', '配信停止', '解除', 'delete', 'remove', 'report', 'spam', 'accounts.google.com/Logout'];
                        for (const a of anchors) {
                            const href = a.href || '';
                            const text = (a.innerText || '').trim();
                            if (text.length < 4 || text.length > 110) continue;
                            const low = (href + ' ' + text).toLowerCase();
                            if (badWords.some(w => low.includes(w))) continue;
                            return { text: text, href: href };
                        }
                        return null;
                    })()
                    """,
                )
                if safe_link and safe_link.get("href") and len(clicked_links_in_mail) == 0:
                    link_text = safe_link.get("text", "")
                    link_href = safe_link.get("href", "")
                    if emit_cb:
                        emit_cb(
                            f"🔗 [Click Link Trong Email]: Bấm mở đường dẫn bên trong thư 「{link_text[:55]}」 và dừng đọc trang web đích 25–30s..."
                        )
                    TabGuard.navigate_tab(cdp_port, target_id, link_href)
                    time.sleep(2.2 if demo_fast_mode else random.uniform(4.5, 6.5))
                    link_scrolls = 1 if demo_fast_mode else random.randint(4, 5)
                    for _ in range(link_scrolls):
                        cls.human_scroll(cdp_port, target_id, min_px=220, max_px=380, direction=1)
                        time.sleep(1.2 if demo_fast_mode else random.uniform(4.8, 7.2))
                    clicked_links_in_mail.append(link_href)

                read_subjects.append(f"{sender}: {subj}")
                TabGuard.navigate_tab(cdp_port, target_id, "https://mail.google.com/mail/u/0/#inbox")
                time.sleep(1.8 if demo_fast_mode else random.uniform(3.8, 5.2))

                # Quét lại danh sách email sau khi quay lại Inbox để lấy tọa độ chính xác
                emails_refreshed = cls.eval_js(cdp_port, target_id, js_scan_emails) or []
                if emails_refreshed and mail_idx < len(picked_emails):
                    picked_emails[mail_idx] = emails_refreshed[min(mail_idx, len(emails_refreshed) - 1)]

        # Bước 4: Kiểm tra sang Tab Cập nhật (#category/updates) hoặc Quảng cáo (#category/promotions)
        cat_target = random.choice([
            ("Tab Cập nhật (Updates)", "https://mail.google.com/mail/u/0/#category/updates"),
            ("Tab Quảng cáo (Promotions)", "https://mail.google.com/mail/u/0/#category/promotions"),
        ])
        if emit_cb:
            emit_cb(f"🗂️ [Nuôi Gmail Chuyên Sâu - Bước 3/5]: Chuyển sang kiểm tra & lướt đọc danh sách thư tại {cat_target[0]}...")
        TabGuard.navigate_tab(cdp_port, target_id, cat_target[1])
        time.sleep(2.0 if demo_fast_mode else random.uniform(4.5, 6.5))
        for _ in range(1 if demo_fast_mode else 3):
            cls.human_scroll(cdp_port, target_id, min_px=180, max_px=320, direction=1)
            time.sleep(1.0 if demo_fast_mode else random.uniform(3.5, 5.5))

        # Bước 5: Kiểm tra mục Thư Rác (#spam) & Giải cứu thư hợp lệ (Not Spam / 迷惑メールではない)
        if emit_cb:
            emit_cb("🛡️ [Nuôi Gmail Chuyên Sâu - Bước 4/5]: Mở mục Thư rác (#spam) kiểm tra và giải cứu thư bị lọc nhầm (Not Spam)...")
        TabGuard.navigate_tab(cdp_port, target_id, "https://mail.google.com/mail/u/0/#spam")
        time.sleep(2.0 if demo_fast_mode else random.uniform(4.5, 6.5))
        spam_rows = cls.eval_js(cdp_port, target_id, js_scan_emails) or []
        if spam_rows:
            sp = spam_rows[0]
            if emit_cb:
                emit_cb(f"🛟 [Giải Cứu Thư Spam]: Phát hiện thư từ 「{sp.get('sender')}」 trong mục Spam -> Mở thư và bấm 『Không phải thư rác (Not Spam)』!")
            cls.hardware_bezier_move_and_click(cdp_port, target_id, sp.get("x", 360), sp.get("y", 240), click=True)
            time.sleep(1.8 if demo_fast_mode else random.uniform(3.5, 5.0))
            not_spam_btn = cls.eval_js(
                cdp_port,
                target_id,
                r"""
                (() => {
                    const btns = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"]'));
                    const target = btns.find(b => {
                        const t = (b.innerText || b.getAttribute('aria-label') || '').toLowerCase();
                        return t.includes('not spam') || t.includes('không phải thư rác') || t.includes('迷惑メールではない') || t.includes('no es spam');
                    });
                    if (!target) return null;
                    const r = target.getBoundingClientRect();
                    return r.width > 0 ? { x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 } : null;
                })()
                """,
            )
            if not_spam_btn:
                cls.hardware_bezier_move_and_click(cdp_port, target_id, not_spam_btn["x"], not_spam_btn["y"], click=True)
                rescued_spam_count += 1
                time.sleep(1.5 if demo_fast_mode else random.uniform(3.0, 4.5))
        else:
            time.sleep(1.0 if demo_fast_mode else random.uniform(3.5, 5.0))

        # Bước 6: Tìm kiếm nội bộ trên thanh Search của Gmail
        TabGuard.navigate_tab(cdp_port, target_id, "https://mail.google.com/mail/u/0/#inbox")
        time.sleep(1.8 if demo_fast_mode else random.uniform(3.8, 5.2))
        search_box_rect = cls.eval_js(
            cdp_port,
            target_id,
            r"""
            (() => {
                const inp = document.querySelector('input[name="q"], input[aria-label*="Search mail"], input[aria-label*="Tìm kiếm trong thư"], input[aria-label*="メールを検索"], input[aria-label*="Buscar en el correo"]');
                if (!inp) return null;
                const r = inp.getBoundingClientRect();
                return r.width > 0 ? { x: r.left + r.width * 0.35, y: r.top + r.height * 0.5 } : null;
            })()
            """,
        )
        gmail_query = random.choice(
            ["Google", "YouTube", "定年", "アラート", "年金"]
            if language == "ja"
            else (["Google", "YouTube", "Alerta", "Cuenta"] if language == "es" else ["Google", "YouTube", "Alert", "Security"])
        )
        if search_box_rect:
            if emit_cb:
                emit_cb(f"🔎 [Nuôi Gmail Chuyên Sâu - Bước 5/5]: Bấm thanh tìm kiếm Gmail, gõ từ khóa 「{gmail_query}」 + Enter để rà soát lịch sử thư...")
            cls.hardware_bezier_move_and_click(cdp_port, target_id, search_box_rect["x"], search_box_rect["y"], click=True)
            time.sleep(0.45)
            for ch_char in gmail_query:
                cls.send_cdp_command(
                    cdp_port,
                    target_id,
                    "Input.dispatchKeyEvent",
                    {"type": "char", "text": ch_char, "unmodifiedText": ch_char},
                    timeout=1.5,
                )
                time.sleep(random.uniform(0.06, 0.14))
            cls.hardware_press_key(cdp_port, target_id, "Enter", "Enter", 13)
            time.sleep(2.0 if demo_fast_mode else random.uniform(4.5, 6.5))
            for _ in range(1 if demo_fast_mode else 2):
                cls.human_scroll(cdp_port, target_id, min_px=160, max_px=280, direction=1)
                time.sleep(1.0 if demo_fast_mode else random.uniform(3.8, 5.5))
            TabGuard.navigate_tab(cdp_port, target_id, "https://mail.google.com/mail/u/0/#inbox")
            time.sleep(1.5 if demo_fast_mode else random.uniform(3.0, 4.5))

        # Lưu lịch sử nuôi Gmail vào folder kênh
        if channel_folder:
            state_path = os.path.join(channel_folder, "11_GMAIL_TRUST_FARMING_STATE.json")
            st: Dict[str, Any] = {}
            if os.path.exists(state_path):
                try:
                    with open(state_path, "r", encoding="utf-8") as f:
                        st = json.load(f)
                except Exception:
                    st = {}
            st["total_gmail_warmup_sessions"] = int(st.get("total_gmail_warmup_sessions", 0)) + 1
            st["total_emails_read"] = int(st.get("total_emails_read", 0)) + len(read_subjects)
            st["total_links_clicked_in_emails"] = int(st.get("total_links_clicked_in_emails", 0)) + len(clicked_links_in_mail)
            st["total_starred_emails"] = int(st.get("total_starred_emails", 0)) + starred_count
            st["total_rescued_spam_emails"] = int(st.get("total_rescued_spam_emails", 0)) + rescued_spam_count
            st["last_gmail_warmup_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st["last_read_subjects"] = read_subjects[:5]
            try:
                os.makedirs(channel_folder, exist_ok=True)
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(st, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        return {
            "ok": True,
            "total_inbox_visible": len(emails),
            "read_emails": read_subjects,
            "clicked_links_in_mail": clicked_links_in_mail,
            "starred_count": starred_count,
            "rescued_spam_count": rescued_spam_count,
        }

    @classmethod
    def warmup_google_maps_explore(
        cls,
        cdp_port: int,
        target_id: str,
        language: str = "ja",
        emit_cb=None,
        demo_fast_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        [v3.8.2] Mô-đun Hành Vi Đời Thực Đa Quốc Gia (~2.0 – 3.0 Phút): Khám phá Địa điểm, Ảnh & Đánh giá trên Google Maps:
        - Nhật Bản (`ja`): Tokyo, Shinjuku, Ueno, Sugamo... (`google.co.jp/maps`)
        - Mexico (`es`): Ciudad de México, Coyoacán, Guadalajara, Monterrey... (`google.com.mx/maps`)
        - Hoa Kỳ (`en`): New York, Chicago, Austin, Seattle... (`google.com/maps`)
        """
        TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=target_id, max_tabs=1)
        cls.apply_channel_locale_and_timezone_emulation(cdp_port, target_id, language=language)
        places_ja = [
            "ハローワーク新宿",
            "東京しごとセンター 飯田橋",
            "上野恩賜公園 喫茶店",
            "巣鴨地蔵通り商店街",
            "日比谷図書館 カフェ",
            "浅草 老舗 喫茶店",
            "吉祥寺 井の頭公園 カフェ",
        ]
        places_es = [
            "Centro Histórico Coyoacán cafetería",
            "Parque México Ciudad de México",
            "Centro de Guadalajara Jalisco",
            "Alameda Central Ciudad de México",
            "Mercado de Coyoacán CDMX",
        ]
        places_en = [
            "New York Public Library",
            "Central Park Cafe Manhattan",
            "Millennium Park Chicago",
            "Boston Public Garden Cafe",
            "Pike Place Market Seattle Coffee",
        ]
        if language == "ja":
            query = random.choice(places_ja)
            maps_url = f"https://www.google.co.jp/maps/search/{urllib.parse.quote(query)}?hl=ja"
            market_label = "Nhật Bản"
        elif language == "es":
            query = random.choice(places_es)
            maps_url = f"https://www.google.com.mx/maps/search/{urllib.parse.quote(query)}?hl=es-419"
            market_label = "Mexico"
        else:
            query = random.choice(places_en)
            maps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}?hl=en"
            market_label = "Hoa Kỳ (US)"
        if emit_cb:
            emit_cb(f"🗺️ [Hành Vi Đời Thực - Google Maps ({market_label})]: Mở bản đồ tra cứu địa điểm 「{query}」 và lướt xem danh sách khu vực (~2.5 phút)...")
        TabGuard.navigate_tab(cdp_port, target_id, maps_url)
        time.sleep(2.5 if demo_fast_mode else random.uniform(5.2, 7.2))

        # Di chuột vào cột danh sách kết quả bên trái và lăn chuột xem các địa điểm (3-4 nhịp)
        cls.hardware_bezier_move_and_click(cdp_port, target_id, 240, 360, click=False)
        feed_scrolls = 1 if demo_fast_mode else random.randint(3, 4)
        for _ in range(feed_scrolls):
            cls.human_scroll(cdp_port, target_id, min_px=200, max_px=350, direction=1)
            time.sleep(1.2 if demo_fast_mode else random.uniform(4.2, 6.5))

        places_found = cls.eval_js(
            cdp_port,
            target_id,
            r"""
            (() => {
                const links = Array.from(document.querySelectorAll('a.hfpxzc, div[role="feed"] a[href*="/maps/place/"]'));
                const out = [];
                for (const a of links) {
                    const r = a.getBoundingClientRect();
                    if (r.width > 0 && r.top > 80 && r.top < 720) {
                        out.push({
                            label: a.getAttribute('aria-label') || 'Địa điểm trên Google Maps',
                            x: r.left + r.width * 0.5,
                            y: r.top + r.height * 0.5
                        });
                    }
                    if (out.length >= 4) break;
                }
                return out;
            })()
            """,
        ) or []

        places_to_inspect = places_found[: (1 if demo_fast_mode else min(2, len(places_found)))]
        for p_idx, pl in enumerate(places_to_inspect, start=1):
            if emit_cb:
                emit_cb(
                    f"📍 [Google Maps - Địa điểm {p_idx}/{len(places_to_inspect)}]: Di chuột Bézier click xem chi tiết, hình ảnh & đọc đánh giá của 「{pl.get('label', query)[:55]}」..."
                )
            cls.hardware_bezier_move_and_click(cdp_port, target_id, pl["x"], pl["y"], click=True)
            time.sleep(2.0 if demo_fast_mode else random.uniform(4.8, 6.8))
            # Di chuột vào bảng chi tiết địa điểm và cuộn đọc đánh giá (Reviews) 5-6 nhịp (~35-45 giây)
            cls.hardware_bezier_move_and_click(cdp_port, target_id, 280, 420, click=False)
            detail_scrolls = 1 if demo_fast_mode else random.randint(5, 6)
            for _ in range(detail_scrolls):
                cls.human_scroll(cdp_port, target_id, min_px=220, max_px=380, direction=1)
                time.sleep(1.2 if demo_fast_mode else random.uniform(5.2, 7.8))
            if not demo_fast_mode:
                cls.human_scroll(cdp_port, target_id, min_px=180, max_px=320, direction=-1)
                time.sleep(random.uniform(3.0, 4.5))

        return {"ok": True, "place_query": query, "inspected_places": len(places_to_inspect)}

    @classmethod
    def warmup_youtube_shorts_swipe(
        cls, cdp_port: int, target_id: str, count: int = 3, emit_cb=None
    ) -> Dict[str, Any]:
        """
        [v3.1] Mô-đun Lướt YouTube Shorts Ngắn Gọn Như Người Thật:
        - Truy cập https://www.youtube.com/shorts
        - Xem 2-3 video Shorts (7-11 giây/video) và bấm phím cứng `ArrowDown` (`isTrusted: true`) để vuốt sang video tiếp theo.
        """
        TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=target_id, max_tabs=1)
        if emit_cb:
            emit_cb(f"📱 [Hành Vi Đa Dạng - YouTube Shorts]: Mở YouTube Shorts và lướt xem {count} video ngắn bằng phím cứng ArrowDown...")
        TabGuard.navigate_tab(cdp_port, target_id, "https://www.youtube.com/shorts")
        time.sleep(3.8)
        for i in range(count):
            wait_s = random.uniform(6.5, 10.5)
            time.sleep(wait_s)
            if i < count - 1:
                cls.hardware_press_key(cdp_port, target_id, "ArrowDown", "ArrowDown", 40)
                if emit_cb:
                    emit_cb(f"⏬ [YouTube Shorts]: Đã xem {wait_s:.1f}s -> Bấm phím cứng ArrowDown chuyển sang video Shorts {i + 2}/{count} (isTrusted=true).")
        return {"ok": True, "shorts_watched": count}

    @classmethod
    def warmup_read_news_portal(
        cls,
        cdp_port: int,
        target_id: str,
        language: str = "ja",
        emit_cb=None,
        demo_fast_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        [v3.8.2] Đọc báo & tin tức đa quốc gia chuyên sâu như người thật (~2.5 – 3.5 Phút):
        - Nhật Bản (`ja`): Yahoo! Japan News & Google News Japan
        - Mexico (`es`): Google News México, El Universal México, Milenio
        - Hoa Kỳ (`en`): Google News US, Yahoo News US, USA Today
        - Mở trang chủ lướt đọc tiêu đề 15s, sau đó mở đọc kỹ 1–2 bài báo từ đầu đến cuối (~45–60s/bài).
        """
        TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=target_id, max_tabs=1)
        if language == "ja":
            portals = [
                ("Yahoo! Japan News (Tin tức Nhật Bản)", "https://news.yahoo.co.jp/"),
                ("Yahoo! Japan Kinh Tế & Hưu Trí", "https://news.yahoo.co.jp/categories/business"),
                ("Yahoo! Japan Đời Sống (Life)", "https://news.yahoo.co.jp/categories/life"),
                ("Google News Japan", "https://news.google.com/home?hl=ja&gl=JP&ceid=JP:ja"),
            ]
        elif language == "es":
            portals = [
                ("Google News México", "https://news.google.com/home?hl=es-419&gl=MX&ceid=MX:es-419"),
                ("El Universal México", "https://www.eluniversal.com.mx/"),
                ("Milenio Noticias México", "https://www.milenio.com/"),
            ]
        else:
            portals = [
                ("Google News US", "https://news.google.com/home?hl=en-US&gl=US&ceid=US:en"),
                ("Yahoo News US", "https://news.yahoo.com/"),
                ("USA Today Life & Money", "https://www.usatoday.com/money/"),
            ]

        portal_name, portal_url = random.choice(portals)
        if emit_cb:
            emit_cb(f"📰 [Đọc Báo & Tin Tức Chuyên Sâu]: Mở trang báo {portal_name} ({portal_url}) để đọc điểm tin hàng ngày (~3 phút)...")
        TabGuard.navigate_tab(cdp_port, target_id, portal_url)
        time.sleep(2.5 if demo_fast_mode else random.uniform(4.5, 6.2))

        # Vuốt rà soát trang chủ báo
        cls.human_browse_scroll_pattern(cdp_port, target_id, fast_mode=demo_fast_mode)
        if not demo_fast_mode:
            time.sleep(random.uniform(3.5, 5.5))

        # Tìm các bài báo có tiêu đề rõ ràng
        js_find_articles = r"""
        (() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            const articles = [];
            const seen = new Set();
            for (const a of links) {
                if (a.offsetParent === null) continue;
                const text = (a.innerText || '').trim().replace(/\s+/g, ' ');
                const href = a.href || '';
                if (text.length < 14 || text.length > 120) continue;
                if (seen.has(href)) continue;
                if (href.includes('yahoo.co.jp/articles/') || href.includes('yahoo.co.jp/pickup/') || href.includes('news.google.com/read/') || href.includes('/articles/')) {
                    seen.add(href);
                    articles.push({ title: text, href: href });
                }
            }
            if (articles.length === 0) {
                for (const a of links) {
                    if (a.offsetParent === null) continue;
                    const text = (a.innerText || '').trim().replace(/\s+/g, ' ');
                    if (text.length >= 16 && text.length <= 110 && a.href && a.href.startsWith('http')) {
                        articles.push({ title: text, href: a.href });
                    }
                    if (articles.length >= 12) break;
                }
            }
            return articles.slice(0, 12);
        })()
        """
        articles = cls.eval_js(cdp_port, target_id, js_find_articles) or []
        read_articles = []

        if articles:
            # Ưu tiên bài báo có từ khóa đời sống, kinh tế, tuổi già, lương hưu, việc làm
            pref_kw = ["年金", "仕事", "定年", "シニア", "60代", "70代", "経済", "物価", "生活", "医療", "給料", "老後", "退職", "貯金"]
            preferred = [a for a in articles if any(k in a.get("title", "") for k in pref_kw)]
            pool = preferred if preferred else articles
            random.shuffle(pool)
            num_to_read = 1 if demo_fast_mode else min(2, len(pool))
            picked_list = pool[:num_to_read]

            for art_idx, picked in enumerate(picked_list, start=1):
                art_title = picked.get("title", "")
                art_href = picked.get("href", "")
                if emit_cb:
                    emit_cb(f"🗞️ [Đọc Bài Báo Chi Tiết {art_idx}/{num_to_read}]: Mở đọc kỹ bài báo 「{art_title[:70]}」 (dừng đọc từng đoạn 45–60s)...")
                TabGuard.navigate_tab(cdp_port, target_id, art_href)
                time.sleep(2.2 if demo_fast_mode else random.uniform(4.2, 6.0))
                # Cuộn đọc bài báo từ trên xuống dưới chậm rãi như người thật (6-7 nhịp cuộn, mỗi nhịp nghỉ 5.5 - 8.5s)
                read_steps = 2 if demo_fast_mode else random.randint(6, 7)
                for _ in range(read_steps):
                    cls.human_scroll(cdp_port, target_id, min_px=220, max_px=390, direction=1)
                    time.sleep(1.2 if demo_fast_mode else random.uniform(5.5, 8.5))
                cls.human_scroll(cdp_port, target_id, min_px=240, max_px=380, direction=-1)
                time.sleep(1.0 if demo_fast_mode else random.uniform(3.5, 5.2))
                read_articles.append(art_title)

        return {"ok": True, "portal": portal_name, "read_articles": read_articles}

    @classmethod
    def warmup_google_search_and_explore(
        cls,
        cdp_port: int,
        target_id: str,
        query: str,
        language: str = "ja",
        emit_cb=None,
        demo_fast_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        [v3.8.2] Tìm kiếm Google Search tự nhiên & Click vào 1–2 trang web ngoài đọc nội dung (~2.5 – 3.5 Phút):
        - Vào google.co.jp / google.com.mx / google.com
        - Di chuột Bézier bấm vào ô tìm kiếm, gõ từng ký tự từ khóa bằng phím cứng (`isTrusted: true`) + bấm Enter
        - Vuốt trang kết quả SERP 15s, click vào 1–2 bài viết web thực tế, cuộn đọc sâu 45–60s/trang để nuôi Google Web & App Activity.
        """
        TabGuard.enforce_max_two_tabs(cdp_port, keep_tab_id=target_id, max_tabs=1)
        if language == "ja":
            google_url = "https://www.google.co.jp/"
            hl_code = "ja"
        elif language == "es":
            google_url = "https://www.google.com.mx/"
            hl_code = "es-419"
        else:
            google_url = "https://www.google.com/"
            hl_code = "en"

        if emit_cb:
            emit_cb(f"🔍 [Nuôi Google Search & Lướt Web Chuyên Sâu]: Mở {google_url} và gõ tìm kiếm từ khóa 「{query}」 (~3 phút)...")
        TabGuard.navigate_tab(cdp_port, target_id, google_url)
        time.sleep(2.0 if demo_fast_mode else random.uniform(3.5, 5.0))

        # Thử di chuột Bézier vào ô tìm kiếm trên trang chủ Google và gõ từng ký tự như người thật
        search_input_rect = cls.eval_js(
            cdp_port,
            target_id,
            r"""
            (() => {
                const inp = document.querySelector('textarea[name="q"], input[name="q"]');
                if (!inp) return null;
                const r = inp.getBoundingClientRect();
                return r.width > 0 ? { x: r.left + r.width * 0.45, y: r.top + r.height * 0.5 } : null;
            })()
            """,
        )
        if search_input_rect:
            cls.hardware_bezier_move_and_click(cdp_port, target_id, search_input_rect["x"], search_input_rect["y"], click=True)
            time.sleep(0.4)
            for ch_char in query:
                cls.send_cdp_command(
                    cdp_port,
                    target_id,
                    "Input.dispatchKeyEvent",
                    {"type": "char", "text": ch_char, "unmodifiedText": ch_char},
                    timeout=1.5,
                )
                time.sleep(random.uniform(0.05, 0.12))
            time.sleep(0.4)
            cls.hardware_press_key(cdp_port, target_id, "Enter", "Enter", 13)
            time.sleep(2.2 if demo_fast_mode else random.uniform(4.2, 5.8))
        else:
            q_encoded = urllib.parse.quote(query)
            search_url = f"{google_url}search?q={q_encoded}&hl={hl_code}"
            TabGuard.navigate_tab(cdp_port, target_id, search_url)
            time.sleep(2.2 if demo_fast_mode else random.uniform(4.0, 5.5))

        # Đảm bảo đang ở trang kết quả tìm kiếm SERP
        cur_u = cls.eval_js(cdp_port, target_id, "window.location.href") or ""
        if "/search" not in cur_u:
            q_encoded = urllib.parse.quote(query)
            TabGuard.navigate_tab(cdp_port, target_id, f"{google_url}search?q={q_encoded}&hl={hl_code}")
            time.sleep(2.2 if demo_fast_mode else random.uniform(3.8, 5.0))

        # Vuốt xem kết quả tìm kiếm trên Google SERP (đọc lướt tiêu đề trên trang kết quả)
        cls.human_browse_scroll_pattern(cdp_port, target_id, fast_mode=demo_fast_mode)
        if not demo_fast_mode:
            time.sleep(random.uniform(3.5, 5.5))

        # Chọn 1-2 kết quả tìm kiếm tự nhiên (thẻ h3 trong #search)
        js_pick_serp = r"""
        (() => {
            const h3s = Array.from(document.querySelectorAll('#search a h3'));
            const results = [];
            for (const h3 of h3s) {
                const a = h3.closest('a');
                if (!a || !a.href || !a.href.startsWith('http')) continue;
                if (a.href.includes('google.com') || a.href.includes('google.co.jp') || a.href.includes('google.com.mx')) continue;
                const title = (h3.innerText || '').trim();
                if (title.length > 5) {
                    results.push({ title: title, href: a.href });
                }
            }
            return results.slice(0, 8);
        })()
        """
        serp_results = cls.eval_js(cdp_port, target_id, js_pick_serp) or []
        visited_site = None
        visited_sites = []
        if serp_results:
            pool_serp = serp_results[: min(5, len(serp_results))]
            random.shuffle(pool_serp)
            num_sites = 1 if demo_fast_mode else min(2, len(pool_serp))
            for s_idx, picked in enumerate(pool_serp[:num_sites], start=1):
                site_title = picked.get("title", "")
                site_href = picked.get("href", "")
                if emit_cb:
                    emit_cb(
                        f"🌐 [Click Kết Quả Google Search {s_idx}/{num_sites}]: Mở trang web 「{site_title[:68]}」 ({site_href[:50]}...) và dừng cuộn đọc kỹ 45–60s..."
                    )
                TabGuard.navigate_tab(cdp_port, target_id, site_href)
                time.sleep(2.2 if demo_fast_mode else random.uniform(4.5, 6.5))
                site_scrolls = 2 if demo_fast_mode else random.randint(6, 7)
                for _ in range(site_scrolls):
                    cls.human_scroll(cdp_port, target_id, min_px=240, max_px=420, direction=1)
                    time.sleep(1.2 if demo_fast_mode else random.uniform(5.2, 8.2))
                cls.human_scroll(cdp_port, target_id, min_px=220, max_px=360, direction=-1)
                time.sleep(1.0 if demo_fast_mode else random.uniform(3.2, 4.8))
                visited_site = {"title": site_title, "url": site_href}
                visited_sites.append(visited_site)

        return {"ok": True, "query": query, "visited_site": visited_site, "visited_sites": visited_sites}

    @classmethod
    def verify_google_and_youtube_login_before_task(
        cls,
        cdp_port: int,
        target_id: str,
        check_mode: str = "BOTH",
        emit_cb=None,
    ) -> Dict[str, Any]:
        """
        [v3.7 / v3.8.1] CỔNG BẢO VỆ TRƯỚC MỌI TÁC VỤ (Pre-Flight Login Verification Gate):
        - Kiểm tra chính xác Profile Chrome đã đăng nhập Google / Gmail / YouTube / Studio chưa.
        - Kết hợp `Storage.getCookies` + `Network.getAllCookies` (`SID`, `HSID`, `SSID`, `SAPISID`, `__Secure-1PSID`, `__Secure-3PSID`, `LOGIN_INFO`)
          VÀ kiểm tra DOM thực tế (có chờ trang tải xong tối đa 6s để không bao giờ báo nhầm "chưa đăng nhập" khi mạng/trang đang tải).
        """
        mode_upper = (check_mode or "BOTH").upper()
        if emit_cb:
            emit_cb(f"🔐 [Cổng Xác Nhận Đăng Nhập Trước Tác Vụ]: Đang kiểm tra trạng thái đăng nhập ({mode_upper})...")

        # Bước 1: Kiểm tra Cookie xác thực qua cả Storage.getCookies và Network.getAllCookies
        cookies: List[Dict[str, Any]] = []
        for cdp_method in ("Storage.getCookies", "Network.getAllCookies"):
            res = cls.send_cdp_command(cdp_port, target_id, cdp_method, {}, timeout=5.0) or {}
            if res.get("cookies"):
                cookies = res.get("cookies") or []
                break

        auth_cookie_names = {
            "SID",
            "HSID",
            "SSID",
            "SAPISID",
            "APISID",
            "__Secure-1PSID",
            "__Secure-3PSID",
            "__Secure-1PAPISID",
            "__Secure-3PAPISID",
            "LOGIN_INFO",
        }
        found_auth_cookies = {
            c.get("name")
            for c in cookies
            if c.get("name") in auth_cookie_names
            and any(d in str(c.get("domain", "")) for d in ("google.", "youtube."))
        }
        has_auth_cookies = len(found_auth_cookies) >= 2

        detected_account = ""
        channel_uc_id = ""

        # Bước 2: Kiểm tra thực tế trên DOM theo đúng loại tác vụ sắp chạy (chờ trang render tối đa 3 nhịp)
        if mode_upper == "GMAIL":
            cur_url = str(cls.eval_js(cdp_port, target_id, "window.location.href") or "")
            if "mail.google.com/mail" not in cur_url:
                TabGuard.navigate_tab(cdp_port, target_id, "https://mail.google.com/mail/u/0/#inbox")
                time.sleep(3.0)
            gm_state: Dict[str, Any] = {}
            for _ in range(3):
                gm_state = cls.eval_js(
                    cdp_port,
                    target_id,
                    r"""
                    (() => {
                        const url = window.location.href || '';
                        const isLoginRedirect = url.includes('accounts.google.com/ServiceLogin') || url.includes('accounts.google.com/v3/signin') || url.includes('workspace.google.com');
                        const inInbox = url.includes('mail.google.com/mail');
                        let email = '';
                        const accBtn = document.querySelector('a[aria-label*="@"], div[aria-label*="@"], [data-email]');
                        if (accBtn) {
                            email = accBtn.getAttribute('data-email') || accBtn.getAttribute('aria-label') || '';
                        }
                        if (!email && document.title.includes('@')) {
                            const m = document.title.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);
                            if (m) email = m[1];
                        }
                        return { url, isLoginRedirect, inInbox, logged_in: Boolean((inInbox || !isLoginRedirect) && !isLoginRedirect), email };
                    })()
                    """,
                ) or {}
                if gm_state.get("inInbox") or gm_state.get("isLoginRedirect"):
                    break
                time.sleep(1.5)

            is_logged = bool(gm_state.get("logged_in")) or (has_auth_cookies and not gm_state.get("isLoginRedirect"))
            if not is_logged:
                reason = f"Hòm thư Gmail chưa đăng nhập ({gm_state.get('url', '')[:60]})."
                if emit_cb:
                    emit_cb(f"⛔ [CHẶN TÁC VỤ - GMAIL CHƯA ĐĂNG NHẬP]: {reason}")
                return {
                    "ok": False,
                    "logged_in": False,
                    "detected_account": "",
                    "reason": reason,
                    "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            detected_account = str(gm_state.get("email") or f"Đã xác thực Gmail ({len(found_auth_cookies)} auth cookies)").strip()

        elif mode_upper == "STUDIO":
            cur_url = str(cls.eval_js(cdp_port, target_id, "window.location.href") or "")
            if "studio.youtube.com" not in cur_url:
                TabGuard.navigate_tab(cdp_port, target_id, "https://studio.youtube.com")
                time.sleep(3.5)
            st_state: Dict[str, Any] = {}
            for _ in range(3):
                st_state = cls.eval_js(
                    cdp_port,
                    target_id,
                    r"""
                    (() => {
                        const url = window.location.href || '';
                        const isLoginRedirect = url.includes('accounts.google.com/ServiceLogin') || url.includes('accounts.google.com/v3/signin');
                        const hasStudioApp = Boolean(document.querySelector('ytcp-app, #create-icon, ytcp-entity-page'));
                        const m = url.match(/channel\/(UC[A-Za-z0-9_-]+)/);
                        const chNameEl = document.querySelector('#entity-name, ytcp-entity-page #entity-name');
                        return {
                            url,
                            isLoginRedirect,
                            logged_in: Boolean(!isLoginRedirect && (hasStudioApp || url.includes('studio.youtube.com'))),
                            channel_uc: m ? m[1] : '',
                            channel_name: chNameEl ? (chNameEl.innerText || '').trim() : ''
                        };
                    })()
                    """,
                ) or {}
                if st_state.get("logged_in") or st_state.get("isLoginRedirect"):
                    break
                time.sleep(1.5)

            is_logged = bool(st_state.get("logged_in")) or (has_auth_cookies and not st_state.get("isLoginRedirect"))
            if not is_logged:
                reason = f"YouTube Studio chưa đăng nhập ({st_state.get('url', '')[:65]})."
                if emit_cb:
                    emit_cb(f"⛔ [CHẶN TÁC VỤ UPLOAD - STUDIO CHƯA ĐĂNG NHẬP]: {reason}")
                return {
                    "ok": False,
                    "logged_in": False,
                    "detected_account": "",
                    "reason": reason,
                    "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            channel_uc_id = str(st_state.get("channel_uc") or "")
            detected_account = str(st_state.get("channel_name") or channel_uc_id or "Đã xác thực YouTube Studio").strip()

        else:
            # YOUTUBE hoặc BOTH: Kiểm tra Cookie + DOM (không bắt buộc điều hướng lại nếu đã có Auth Cookies hợp lệ)
            yt_state = cls.eval_js(
                cdp_port,
                target_id,
                r"""
                (() => {
                    const url = window.location.href || '';
                    const isLoginRedirect = url.includes('accounts.google.com/ServiceLogin') || url.includes('accounts.google.com/v3/signin');
                    const ytcfgLogged = (window.ytcfg && typeof window.ytcfg.get === 'function')
                        ? Boolean(window.ytcfg.get('LOGGED_IN'))
                        : null;
                    const hasAvatar = Boolean(document.querySelector('button#avatar-btn, ytd-topbar-menu-button-renderer button#avatar-btn, #avatar-btn img, a[aria-label*="Google"], gb_d'));
                    const signInBtn = document.querySelector('ytd-masthead a[href*="accounts.google.com/ServiceLogin"], ytd-button-renderer a[href*="ServiceLogin"]');
                    return {
                        url,
                        isLoginRedirect,
                        has_avatar: hasAvatar,
                        ytcfg_logged: ytcfgLogged,
                        has_signin_btn: Boolean(signInBtn),
                        dom_logged: Boolean((ytcfgLogged === true) || (hasAvatar && !signInBtn))
                    };
                })()
                """,
            ) or {}

            is_logged = (
                bool(yt_state.get("dom_logged"))
                or (has_auth_cookies and not yt_state.get("isLoginRedirect") and not yt_state.get("has_signin_btn"))
            )
            if not is_logged and not has_auth_cookies:
                reason = "Profile chưa có Cookie phiên đăng nhập Google/YouTube và chưa đăng nhập trên trình duyệt."
                if emit_cb:
                    emit_cb(f"⛔ [CHẶN TÁC VỤ - CHƯA ĐĂNG NHẬP]: {reason}")
                return {
                    "ok": False,
                    "logged_in": False,
                    "detected_account": "",
                    "reason": reason,
                    "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            detected_account = f"Đã xác thực phiên Google & YouTube ({len(found_auth_cookies)} Cookie bảo mật)"

        if emit_cb:
            emit_cb(f"✅ [Xác Nhận Đăng Nhập Hợp Lệ]: Profile đã đăng nhập ({detected_account}) -> Cho phép tiếp tục thực thi!")
        return {
            "ok": True,
            "logged_in": True,
            "detected_account": detected_account,
            "channel_id_uc": channel_uc_id,
            "reason": "OK",
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @classmethod
    def get_active_video_duration_and_state(cls, cdp_port: int, target_id: str) -> Dict[str, Any]:
        """
        [v3.7] Đọc thời lượng thực tế (`duration`) và thời gian đang phát (`currentTime`) của video YouTube hiện tại
        để tính toán thời gian Xem Sâu Thực Chiến (Deep Watch Time: 3–8 phút / video) chuẩn thuật toán YouTube.
        """
        info = cls.eval_js(
            cdp_port,
            target_id,
            r"""
            (() => {
                const v = document.querySelector('#movie_player video, video.html5-main-video');
                if (!v) return { has_video: false, duration: 0, current_time: 0, paused: true };
                if (v.paused && v.currentTime < 2) {
                    try { v.play(); } catch (e) {}
                }
                return {
                    has_video: true,
                    duration: Number.isFinite(v.duration) ? Math.round(v.duration) : 0,
                    current_time: Number.isFinite(v.currentTime) ? Math.round(v.currentTime) : 0,
                    paused: Boolean(v.paused)
                };
            })()
            """,
        )
        return info if isinstance(info, dict) else {"has_video": False, "duration": 0, "current_time": 0, "paused": True}

    @classmethod
    def post_comment_on_youtube_watch_page(
        cls,
        cdp_port: int,
        target_id: str,
        comment_text: str,
        emit_cb=None,
    ) -> Dict[str, Any]:
        """
        [v3.7] Thực hiện GÕ VÀ ĐĂNG BÌNH LUẬN THẬT lên video YouTube đang xem bằng thao tác phần cứng:
        1. Cuộn mượt xuống khu vực `#comments` (`ytd-comments#comments`).
        2. Chờ hộp `#simplebox-placeholder` xuất hiện và đưa vào giữa khung nhìn.
        3. Di chuột Bézier bấm vào `#simplebox-placeholder` (`isTrusted: true`).
        4. Gõ từng ký tự câu bình luận với nhịp độ người thật (`Input.insertText` + nghỉ giữa các cụm từ).
        5. Di chuột Bézier bấm vào nút Bình luận (`#submit-button`) và chờ YouTube ghi nhận.
        """
        clean_text = str(comment_text or "").strip()
        if not clean_text:
            return {"ok": False, "reason": "Empty comment_text"}

        if emit_cb:
            emit_cb("🖱️ [Thao Tác Bình Luận Thật]: Đang cuộn xuống khu vực bình luận (#comments) của video...")

        # Cuộn xuống khu vực bình luận (2-3 nhịp tự nhiên)
        for _ in range(2):
            cls.human_scroll(cdp_port, target_id, min_px=340, max_px=520, direction=1)
            time.sleep(random.uniform(1.1, 1.8))

        # Đưa ô #simplebox-placeholder vào vùng nhìn thấy và lấy tọa độ
        box_rect = None
        for _ in range(5):
            box_rect = cls.eval_js(
                cdp_port,
                target_id,
                r"""
                (() => {
                    const ph = document.querySelector('#simplebox-placeholder, ytd-comment-simplebox-renderer #placeholder-area');
                    if (!ph) return null;
                    ph.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    const r = ph.getBoundingClientRect();
                    if (r.width <= 0 || r.height <= 0) return null;
                    return { x: r.left + r.width * 0.25, y: r.top + r.height * 0.5 };
                })()
                """,
            )
            if box_rect:
                break
            cls.human_scroll(cdp_port, target_id, min_px=260, max_px=400, direction=1)
            time.sleep(1.2)

        if not box_rect:
            return {"ok": False, "reason": "Không tìm thấy ô nhập bình luận (#simplebox-placeholder) trên video này"}

        time.sleep(0.9)
        # Lấy lại tọa độ chính xác sau khi scrollIntoView hoàn tất
        box_rect = cls.eval_js(
            cdp_port,
            target_id,
            r"""
            (() => {
                const ph = document.querySelector('#simplebox-placeholder, ytd-comment-simplebox-renderer #placeholder-area');
                if (!ph) return null;
                const r = ph.getBoundingClientRect();
                return { x: r.left + r.width * 0.25, y: r.top + r.height * 0.5 };
            })()
            """,
        ) or box_rect

        # Click chuột phần cứng Bézier mở ô nhập bình luận
        cls.hardware_bezier_move_and_click(cdp_port, target_id, box_rect["x"], box_rect["y"], click=True)
        time.sleep(random.uniform(0.8, 1.4))

        # Đảm bảo #contenteditable-root đã được focus
        cls.eval_js(
            cdp_port,
            target_id,
            r"""
            (() => {
                const ph = document.querySelector('#simplebox-placeholder, ytd-comment-simplebox-renderer #placeholder-area');
                if (ph && !document.querySelector('#contenteditable-root[contenteditable="true"]')) {
                    ph.click();
                }
                const root = document.querySelector('#contenteditable-root[contenteditable="true"]');
                if (root) { root.focus(); return true; }
                return false;
            })()
            """,
        )
        time.sleep(0.5)

        if emit_cb:
            emit_cb(f"⌨️ [Gõ Phím Cứng Bình Luận]: Đang gõ từng chữ ({len(clean_text)} ký tự): \"{clean_text[:65]}...\"")

        # Gõ từng ký tự bằng CDP Input.insertText với nhịp độ người thật
        for idx, ch_char in enumerate(clean_text):
            cls.send_cdp_command(
                cdp_port,
                target_id,
                "Input.insertText",
                {"text": ch_char},
                timeout=3.0,
            )
            delay = max(0.045, min(0.22, random.gauss(0.095, 0.035)))
            if ch_char in (" ", "　", "。", "、", ",", ".") or (idx > 0 and idx % random.randint(6, 11) == 0):
                delay += random.uniform(0.10, 0.28)
            time.sleep(delay)

        time.sleep(random.uniform(0.8, 1.5))

        # Tìm tọa độ nút Submit (#submit-button) và bấm chuột Bézier thật
        sub_rect = cls.eval_js(
            cdp_port,
            target_id,
            r"""
            (() => {
                const root = document.querySelector('#contenteditable-root[contenteditable="true"]');
                if (root) {
                    root.dispatchEvent(new Event('input', { bubbles: true }));
                }
                const btn = document.querySelector('ytd-comment-simplebox-renderer #submit-button button, #submit-button ytcp-button, ytd-button-renderer#submit-button button, #submit-button');
                if (!btn) return null;
                const r = btn.getBoundingClientRect();
                if (r.width <= 0 || r.height <= 0) return null;
                return { x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
            })()
            """,
        )
        submitted = False
        if sub_rect:
            cls.hardware_bezier_move_and_click(cdp_port, target_id, sub_rect["x"], sub_rect["y"], click=True)
            submitted = True
            time.sleep(0.4)
            # Đảm bảo nút submit đã kích hoạt nếu cần
            cls.eval_js(
                cdp_port,
                target_id,
                r"""
                (() => {
                    const btn = document.querySelector('ytd-comment-simplebox-renderer #submit-button button, ytd-button-renderer#submit-button button');
                    if (btn && !btn.hasAttribute('disabled')) btn.click();
                    return true;
                })()
                """,
            )

        time.sleep(2.6)
        # Cuộn nhẹ trở lại màn hình video sau khi đăng bình luận
        cls.human_scroll(cdp_port, target_id, min_px=350, max_px=550, direction=-1)
        if emit_cb:
            emit_cb("✅ [Đã Đăng Bình Luận Thật]: Hoàn tất gõ và gửi bình luận trực tiếp dưới video!")
        return {"ok": True, "submitted": submitted, "comment_text": clean_text}

    @classmethod
    def close_channel_browser(cls, cdp_port: int) -> Dict[str, Any]:
        """
        Đóng hoàn toàn cửa sổ Chrome Profile của kênh sau khi nuôi xong hoặc khi bấm Dừng:
        1. Dừng video & gọi lệnh CDP Browser.close để Chrome lưu toàn bộ Cookie / LocalStorage xuống ổ cứng an toàn.
        2. Đóng triệt để tiến trình Chrome gắn với cổng --remote-debugging-port=<cdp_port> để giải phóng RAM.
        """
        pages = TabGuard.list_page_targets(cdp_port)
        if pages:
            tid = pages[0].get("id")
            if tid:
                cls.eval_js(
                    cdp_port,
                    tid,
                    "(() => { document.querySelectorAll('video').forEach(v => { try { v.pause(); } catch(e){} }); return true; })()",
                )
                time.sleep(0.3)
                cls.send_cdp_command(cdp_port, tid, "Browser.close", {}, timeout=2.5)
        time.sleep(1.2)
        if cls.is_port_open(cdp_port):
            try:
                ps_kill = (
                    f"Get-CimInstance Win32_Process | Where-Object {{ $_.Name -eq 'chrome.exe' -and $_.CommandLine -like '*--remote-debugging-port={cdp_port}*' }} "
                    f"| ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
                )
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_kill], timeout=4, capture_output=True)
            except Exception:
                pass
        return {"ok": True, "closed_port": cdp_port}

    @classmethod
    def park_browser_after_warmup(
        cls, cdp_port: int, target_id: Optional[str] = None, summary_text: str = "Đã hoàn tất phiên nuôi tài khoản hôm nay"
    ) -> Dict[str, Any]:
        """
        Khi nuôi xong (hoặc khi người dùng bấm Dừng):
        Tự động lưu Cookie và ĐÓNG LUÔN cửa sổ Chrome Profile để giải phóng máy.
        """
        return cls.close_channel_browser(cdp_port)

    @classmethod
    def capture_screenshot_base64(cls, cdp_port: int, target_id: Optional[str] = None) -> Optional[str]:
        pages = TabGuard.list_page_targets(cdp_port)
        if not pages:
            return None
        tid = target_id or pages[-1].get("id")
        if not tid:
            return None
        res = cls.send_cdp_command(
            cdp_port,
            tid,
            "Page.captureScreenshot",
            {"format": "jpeg", "quality": 65},
            timeout=5.0,
        )
        if res and res.get("data"):
            return f"data:image/jpeg;base64,{res['data']}"
        return None

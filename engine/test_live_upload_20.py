import sys
import time

sys.path.insert(0, r"D:\YOUTUBE_ENTERPRISE_STUDIO")
from engine.browser_cdp_manager import BrowserCDPManager, TabGuard


def main():
    port = 9301
    pages = TabGuard.list_page_targets(port)
    if not pages:
        return
    tid = pages[0]["id"]
    BrowserCDPManager.eval_js(
        port,
        tid,
        r"""
        (() => {
            const cancelBtns = Array.from(document.querySelectorAll('ytcp-dialog button, tp-yt-paper-dialog button'));
            const huy = cancelBtns.find(b => (b.innerText || '').trim() === 'Hủy');
            if (huy) huy.click();
        })()
        """,
    )
    time.sleep(0.8)
    TabGuard.navigate_tab(port, tid, "https://studio.youtube.com/channel/UCvYcAYX8D6aaxmW-MWZzJqw/videos/upload")
    print("OK")


if __name__ == "__main__":
    main()

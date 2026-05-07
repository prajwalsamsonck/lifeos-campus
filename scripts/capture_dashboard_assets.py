from __future__ import annotations

import sys
import time
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:5000"
OUT_DIR = Path("assets/screenshots")


def _wait_for(page, ms: int = 1300) -> None:
    page.wait_for_timeout(ms)


def _capture_element(page, selector: str, out_path: Path, label: str) -> bool:
    try:
        locator = page.locator(selector).first
        if locator.count() == 0:
            print(f"[WARN] {label}: selector not found: {selector}")
            return False
        locator.scroll_into_view_if_needed()
        _wait_for(page, 1200)
        locator.screenshot(path=str(out_path))
        print(f"[OK]   {label}: {out_path}")
        return True
    except PlaywrightTimeoutError:
        print(f"[WARN] {label}: timeout while locating {selector}")
        return False
    except Exception as exc:  # pragma: no cover
        print(f"[WARN] {label}: failed ({exc})")
        return False


def _append_frame(page, frames: list[Image.Image], wait_ms: int = 900) -> None:
    _wait_for(page, wait_ms)
    raw = page.screenshot(full_page=False, type="png")
    img = Image.open(BytesIO(raw)).convert("RGB")
    frames.append(img)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    targets = {
        "main-dashboard.png": ("http://127.0.0.1:5000/", None, "Main Dashboard"),
        "digital-twin.png": ("http://127.0.0.1:5000/", "#twin-wrap", "Digital Twin section"),
        "agent-reasoning.png": ("http://127.0.0.1:5000/", "#agent-reasoning-card", "Agent Reasoning section"),
        "counterfactual-impact.png": (
            "http://127.0.0.1:5000/",
            "#counterfactual-impact-card",
            "Counterfactual Impact section",
        ),
        "behavioral-dna.png": ("http://127.0.0.1:5000/", ".pattern-wrap", "Behavioral DNA section"),
        "judge-demo.png": ("http://127.0.0.1:5000/demo", None, "Judge Demo state"),
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            color_scheme="dark",
            device_scale_factor=2,
        )
        page = context.new_page()
        page.set_default_timeout(15000)

        try:
            page.goto(BASE_URL, wait_until="domcontentloaded")
            _wait_for(page, 1800)
        except Exception:
            print(
                "[ERROR] Could not reach dashboard at http://127.0.0.1:5000.\n"
                "Start it first with: python dashboard.py"
            )
            browser.close()
            return 1

        # Capture required PNG screenshots.
        for filename, (url, selector, label) in targets.items():
            out_path = OUT_DIR / filename
            page.goto(url, wait_until="domcontentloaded")
            _wait_for(page, 1700)

            if filename == "main-dashboard.png":
                page.screenshot(path=str(out_path), full_page=False, type="png")
                print(f"[OK]   {label}: {out_path}")
                continue

            if filename == "judge-demo.png":
                # Enter demo mode and try launching Judge Demo tour.
                btn = page.locator("#judge-start")
                if btn.count() > 0:
                    try:
                        btn.first.click(timeout=6000)
                        _wait_for(page, 3200)
                    except Exception:
                        print("[WARN] Judge Demo button click failed; capturing current /demo state.")
                else:
                    print("[WARN] Judge Demo button not found on /demo page.")
                page.screenshot(path=str(out_path), full_page=False, type="png")
                print(f"[OK]   {label}: {out_path}")
                continue

            if selector:
                _capture_element(page, selector, out_path, label)

        # Build a 15–30s GIF sequence.
        gif_path = OUT_DIR / "judge-demo.gif"
        frames: list[Image.Image] = []

        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
        _append_frame(page, frames, 1200)  # hero
        _append_frame(page, frames, 900)

        for selector in [
            "#twin-wrap",
            "#agent-reasoning-card",
            "#counterfactual-impact-card",
            ".log-wrap",
            ".pattern-wrap",
        ]:
            loc = page.locator(selector).first
            if loc.count() == 0:
                print(f"[WARN] GIF step missing selector: {selector}")
                continue
            loc.scroll_into_view_if_needed()
            _append_frame(page, frames, 1200)
            _append_frame(page, frames, 900)

        page.goto(f"{BASE_URL}/demo", wait_until="domcontentloaded")
        _append_frame(page, frames, 1200)
        start_btn = page.locator("#judge-start")
        if start_btn.count() > 0:
            try:
                start_btn.first.click(timeout=6000)
                # Capture transitions for ~9s.
                for _ in range(8):
                    _append_frame(page, frames, 1150)
            except Exception:
                print("[WARN] GIF: could not trigger Judge Demo, capturing static demo frames.")
                for _ in range(6):
                    _append_frame(page, frames, 1000)
        else:
            print("[WARN] GIF: judge start button missing, capturing static demo frames.")
            for _ in range(6):
                _append_frame(page, frames, 1000)

        if not frames:
            print("[ERROR] No frames captured for GIF.")
            browser.close()
            return 1

        # ~19-22s depending on frame count and duration.
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=900,
            loop=0,
            optimize=True,
        )
        print(f"[OK]   Judge demo GIF: {gif_path}")

        browser.close()

    print("\nAsset capture complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Рендер HTML-макетов в PNG через Playwright (Chromium).

Использование:
  python3 render.py <html> <out.png> <width> <height>   — один файл
  python3 render.py --batch <jobs.json>                   — список [{html, out, w, h}]
"""
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def render_jobs(jobs):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(device_scale_factor=1)
        page = await ctx.new_page()
        for job in jobs:
            w, h = int(job["w"]), int(job["h"])
            await page.set_viewport_size({"width": w, "height": h})
            await page.goto(Path(job["html"]).resolve().as_uri(), wait_until="networkidle")
            await page.evaluate("document.fonts.ready")
            try:
                await page.wait_for_selector("body[data-ready]", timeout=6000)
            except Exception:
                print("WARN no data-ready", job["html"], flush=True)
            await page.wait_for_timeout(120)
            overflow = await page.evaluate(
                "() => Array.from(document.querySelectorAll('[data-fit]')).filter(e => e.scrollHeight > e.clientHeight + 2 || e.scrollWidth > e.clientWidth + 2).map(e => e.dataset.fit)"
            )
            out = Path(job["out"])
            out.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": w, "height": h})
            print(("OVERFLOW " + ",".join(overflow) + " ") if overflow else "", "ok", out.name, flush=True)
        await browser.close()


def main():
    if sys.argv[1] == "--batch":
        jobs = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    else:
        jobs = [{"html": sys.argv[1], "out": sys.argv[2], "w": sys.argv[3], "h": sys.argv[4]}]
    asyncio.run(render_jobs(jobs))


if __name__ == "__main__":
    main()

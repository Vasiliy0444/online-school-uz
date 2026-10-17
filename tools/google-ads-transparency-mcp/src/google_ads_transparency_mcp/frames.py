"""Turn ad creatives into local files a vision model can look at.

Image ads resolve to a static asset URL, so they only need fetching. Video ads
resolve to a YouTube id, so they need downloading and sampling: a handful of
small JPEG frames is enough to tell what is on screen, and far cheaper than the
video. Both paths return local paths, never bytes.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests

from .config import proxy_hint, proxy_settings

# Small enough to stay cheap for vision analysis, large enough to read a logo
# or a line of on-screen text.
DEFAULT_FRAMES = 8
DEFAULT_WIDTH = 320


class FrameExtractionError(RuntimeError):
    """Downloading or sampling a creative failed."""


def _require(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise FrameExtractionError(
            f"{binary} is not on PATH — install it to sample video creatives."
        )
    return path


def _run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        raise FrameExtractionError(f"{cmd[0]} failed: {' / '.join(tail)}")
    return proc


def download_image(image_url: str, out_dir: str | Path, name: str = "creative") -> str:
    """Fetch a static image creative to disk. Returns the local path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(image_url, timeout=30, proxies=proxy_settings())
    except requests.RequestException as exc:
        raise FrameExtractionError(
            f"Could not fetch {image_url}{proxy_hint()}: {exc}"
        ) from exc
    if resp.status_code != 200 or not resp.content:
        raise FrameExtractionError(
            f"image fetch returned HTTP {resp.status_code} for {image_url}"
        )
    suffix = {
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }.get(resp.headers.get("content-type", "").split(";")[0], ".jpg")
    path = out / f"{name}{suffix}"
    path.write_bytes(resp.content)
    return str(path)


def _probe_duration(ffprobe: str, video_path: str) -> float:
    proc = _run([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "json", video_path,
    ], timeout=60)
    try:
        return float(json.loads(proc.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return 0.0


def extract_video_frames(
    video_url: str,
    out_dir: str | Path,
    frames: int = DEFAULT_FRAMES,
    width: int = DEFAULT_WIDTH,
    full_quality: bool = False,
) -> dict:
    """Download a video creative and sample frames from it.

    Two modes, because the two uses pull in opposite directions. The default is
    sized for vision analysis: smallest stream, small JPEGs, cheap. Pass
    ``full_quality`` to keep the best stream and write frames at native
    resolution, which is what a deck or a slide needs.

    Set ``width`` to 0 to skip downscaling entirely.

    Returns {video_path, duration, frames: [paths]}.
    """
    ytdlp = _require("yt-dlp")
    ffmpeg = _require("ffmpeg")
    ffprobe = _require("ffprobe")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        template = os.path.join(tmp, "video.%(ext)s")
        selector = (
            "bestvideo[height<=1080]+bestaudio/best"
            if full_quality
            # Smallest thing that still decodes; ads are short so this is quick.
            else "worstvideo[height<=360]+worstaudio/worst[height<=360]/worst"
        )
        _run([
            ytdlp, "--quiet", "--no-warnings", "--no-playlist",
            "-f", selector, "-o", template, video_url,
        ])
        downloaded = sorted(Path(tmp).glob("video.*"))
        if not downloaded:
            raise FrameExtractionError(f"yt-dlp produced no file for {video_url}")
        video_path = str(downloaded[0])

        duration = _probe_duration(ffprobe, video_path)
        pattern = str(out / "frame_%02d.jpg")
        # Spread the sample across the whole clip rather than clustering at the
        # start, which is where most ads are still showing a title card.
        rate = f"{frames}/{duration:.3f}" if duration > 0 else "1"
        video_filter = f"fps={rate}"
        if width > 0:
            video_filter += f",scale={width}:-2"
        _run([
            ffmpeg, "-v", "error", "-y", "-i", video_path,
            "-vf", video_filter, "-frames:v", str(frames),
            "-q:v", "2" if full_quality else "5", pattern,
        ])

        kept = str(out / Path(video_path).name)
        shutil.copy2(video_path, kept)

    frame_paths = sorted(str(p) for p in out.glob("frame_*.jpg"))
    if not frame_paths:
        raise FrameExtractionError(f"ffmpeg produced no frames for {video_url}")
    return {"video_path": kept, "duration": round(duration, 2), "frames": frame_paths}

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import json
import os
import shutil
import subprocess


def process_options() -> dict:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def find_tool(name: str, root: Path) -> str:
    candidates = [root / "tools" / f"{name}.exe",
                  Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Links" / f"{name}.exe"]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(f"{name} is missing. Place it in {root / 'tools'}")


@dataclass(frozen=True)
class MediaInfo:
    width: int
    height: int
    fps: Fraction
    duration: float
    audio: bool


def probe(path: Path, ffprobe: str) -> MediaInfo:
    result = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                            capture_output=True, text=True, check=True, timeout=30, **process_options())
    data = json.loads(result.stdout)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if not video:
        raise ValueError("No video stream in this file")
    raw_rate = video.get("avg_frame_rate", "0/0")
    if raw_rate in ("0/0", "0/1"):
        raw_rate = video["r_frame_rate"]
    fps = Fraction(raw_rate)
    if not 0 < fps <= 240:
        raise ValueError("Unsupported source frame rate")
    return MediaInfo(video["width"], video["height"], fps,
                     float(data["format"].get("duration", video.get("duration", 0))),
                     any(s["codec_type"] == "audio" for s in data["streams"]))

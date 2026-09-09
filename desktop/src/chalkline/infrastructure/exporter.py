"""Bounded-memory native export; no browser readback and no shell scripts."""
from pathlib import Path
from threading import Event
import math
import os
import shutil
import subprocess
import uuid

from chalkline.domain.timeline import plan_clip
from chalkline.infrastructure.media import find_tool, probe, process_options
from chalkline.rendering.annotations import check_supported, overlay_image
from PySide6.QtGui import QImage


class ExportCancelled(Exception):
    pass


class Exporter:
    def __init__(self, root: Path, cancel: Event | None = None, progress=None):
        self.root = Path(root)
        self.cancel = cancel or Event()
        self.progress = progress or (lambda fraction, message: None)
        self.ffmpeg = find_tool("ffmpeg", root)
        self.ffprobe = find_tool("ffprobe", root)
        self.process = None

    def stop(self):
        self.cancel.set()
        process = self.process
        if process and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def check_cancel(self):
        if self.cancel.is_set():
            raise ExportCancelled("Export cancelled; existing exports were kept")

    def run(self, args: list[str], log: Path):
        self.check_cancel()
        with log.open("ab") as stderr:
            self.process = subprocess.Popen([self.ffmpeg, "-hide_banner", "-loglevel", "warning", "-y", *args],
                                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=stderr,
                                            **process_options())
            code = self.process.wait()
        self.check_cancel()
        if code:
            raise RuntimeError(f"FFmpeg failed ({code}). See {log}")

    def export(self, source: Path, mark: dict, offset: float, settings: dict,
               destination: Path, require_4k=True) -> Path:
        self.check_cancel()
        check_supported(mark)
        if settings.get("music") or settings.get("voiceover"):
            raise ValueError("Audio mixing is not implemented in this prototype yet")
        info = probe(source, self.ffprobe)
        if require_4k and (info.width, info.height) != (3840, 2160):
            raise ValueError("True 4K export requires a 3840 x 2160 source; no automatic upscaling")
        if info.width % 2 or info.height % 2:
            raise ValueError("H.264 export requires even source dimensions")
        plan = plan_clip(mark, offset, info.duration, settings.get("hold", 3) if settings.get("autoFreeze", True) else 0)
        total_seconds = sum(s.duration for s in plan)
        if total_seconds > 600:
            raise ValueError("Prototype export is limited to 10 minutes per clip")
        destination = Path(destination)
        if destination.exists():
            raise FileExistsError("Choose a new output name; existing exports are never overwritten")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(destination.parent).free < max(512*1024**2, total_seconds*20*1024**2):
            raise ValueError("Insufficient export-drive space for intermediates and final output")
        # Job work always follows the output drive; each job owns only its UUID directory.
        job = destination.parent / ".chalkline-temp" / uuid.uuid4().hex
        job.mkdir(parents=True)
        log_root = self.root / "logs"
        log_root.mkdir(parents=True, exist_ok=True)
        log = log_root / f"export-{job.name}.log"
        partial = destination.with_name(f".{destination.stem}-{job.name}.partial.mp4")
        rate = f"{info.fps.numerator}/{info.fps.denominator}"
        fps = float(info.fps)
        completed = 0
        cumulative = 0.0
        pieces = []
        try:
            for index, segment in enumerate(plan):
                self.check_cancel()
                frame_count = max(1, round((cumulative+segment.duration)*fps)-round(cumulative*fps))
                cumulative += segment.duration
                length = frame_count/fps
                output = job / f"piece-{index:04}.mp4"
                if segment.kind == "freeze":
                    still = job / f"freeze-{index:04}.png"
                    self.run(["-ss", str(segment.start), "-i", str(source), "-frames:v", "1", str(still)], log)
                    inputs = ["-loop", "1", "-framerate", rate, "-i", str(still)]
                else:
                    inputs = ["-ss", str(segment.start), "-t", str(segment.end-segment.start), "-i", str(source)]
                inputs += ["-f", "rawvideo", "-pixel_format", "rgba", "-video_size", f"{info.width}x{info.height}",
                           "-framerate", rate, "-i", "pipe:0"]
                silent = segment.kind == "freeze" or not info.audio or settings.get("muteOriginal", False)
                if silent:
                    inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
                    audio = "[2:a]atrim=duration="+str(length)+",asetpts=PTS-STARTPTS[a]"
                else:
                    remaining = segment.rate
                    tempo = []
                    while remaining < .5:
                        tempo.append("atempo=0.5")
                        remaining *= 2
                    tempo.append(f"atempo={remaining}")
                    audio = "[0:a]asetpts=PTS-STARTPTS,"+",".join(tempo)+f",apad,atrim=duration={length}[a]"
                graph = (f"[0:v]setpts=(PTS-STARTPTS)/{segment.rate},fps={rate},"
                         f"tpad=stop_mode=clone:stop_duration=1[base];"
                         "[base][1:v]overlay=0:0:shortest=1,format=yuv420p[v];"+audio)
                command = [self.ffmpeg, "-hide_banner", "-loglevel", "warning", "-y", *inputs,
                           "-filter_complex_threads", "1", "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                           "-t", str(length), "-r", rate, "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                           "-threads", "4", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                           "-video_track_timescale", str(info.fps.numerator), str(output)]
                with log.open("ab") as stderr:
                    self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                                    stderr=stderr, **process_options())
                    try:
                        for frame in range(frame_count):
                            self.check_cancel()
                            time = segment.start if segment.kind == "freeze" else min(segment.end, segment.start+frame/fps*segment.rate)
                            image = overlay_image(info.width, info.height, mark, time, settings, segment.kind == "freeze")
                            image = image.convertToFormat(QImage.Format.Format_RGBA8888)
                            self.process.stdin.write(image.constBits())
                            completed += 1
                            if frame % 5 == 0:
                                self.progress(min(.95, completed/max(1, total_seconds*fps)*.95), f"Rendering segment {index+1}/{len(plan)}")
                        self.process.stdin.close()
                        code = self.process.wait()
                    except Exception:
                        if self.process.poll() is None:
                            self.process.terminate()
                        self.process.wait()
                        self.check_cancel()
                        raise RuntimeError(f"Export stream failed. See {log}")
                self.check_cancel()
                if code:
                    raise RuntimeError(f"FFmpeg failed ({code}). See {log}")
                pieces.append(output)
            listing = job / "pieces.txt"
            listing.write_text("".join(f"file '{p.name}'\n" for p in pieces), encoding="utf-8")
            self.progress(.96, "Joining and verifying output")
            self.run(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(partial)], log)
            output_info = probe(partial, self.ffprobe)
            if (output_info.width, output_info.height) != (info.width, info.height):
                raise RuntimeError("Output dimensions failed validation")
            if abs(output_info.duration-total_seconds) > max(.25, len(plan)*.06):
                raise RuntimeError("Output duration failed validation")
            self.check_cancel()
            if destination.exists():
                raise FileExistsError("Output name was created by another operation")
            partial.rename(destination)
            self.progress(1.0, f"Export complete: {destination.name}")
            return destination
        finally:
            partial.unlink(missing_ok=True)
            # Only this job's known UUID directory is removed; never a shared work folder.
            if job.parent.resolve() == (destination.parent / ".chalkline-temp").resolve():
                shutil.rmtree(job)
            self.process = None

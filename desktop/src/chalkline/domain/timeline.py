"""Source-time to output-time mapping shared by preview and export."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Segment:
    kind: str
    start: float
    end: float
    rate: float = 1.0
    hold: float = 0.0

    @property
    def duration(self) -> float:
        return self.hold if self.kind == "freeze" else (self.end - self.start) / self.rate


def finite(value, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def clip_bounds(mark: dict, offset: float, duration: float) -> tuple[float, float]:
    moment = finite(mark["t"], "Tag time") + finite(offset, "Offset")
    before, after = finite(mark.get("pre", 2), "Before"), finite(mark.get("post", 7), "After")
    if before < 0 or after < 0:
        raise ValueError("Clip before/after durations must be non-negative")
    start, end = max(0.0, moment - before), min(duration, moment + after)
    if end <= start:
        raise ValueError("Clip lies outside the source or has no duration")
    return start, end


def freeze_stops(mark: dict, start: float, end: float, hold: float) -> list[tuple[float, float]]:
    stops = []
    for shape in mark.get("shapes", []):
        if shape.get("tool") != "ground" and shape.get("t") is not None:
            stops.append((finite(shape["t"], "Shape time"), hold))
    for freeze in mark.get("freezes", []):
        stops.append((finite(freeze["at"], "Freeze time"), finite(freeze["hold"], "Freeze hold")))
    merged = []
    for time, seconds in sorted(stops):
        if merged and abs(merged[-1][0] - time) < 0.15:
            merged[-1] = (merged[-1][0], max(merged[-1][1], seconds))
        else:
            merged.append((time, seconds))
    # v212 merges before excluding clip-edge stops, including zero-hold beats.
    return [(time, seconds) for time, seconds in merged if seconds > 0 and start+.1 < time < end-.1]


def plan_clip(mark: dict, offset: float, duration: float, hold: float = 3) -> list[Segment]:
    start, end = clip_bounds(mark, offset, duration)
    freezes = freeze_stops(mark, start, end, hold)
    zones = mark.get("slow", [])
    if isinstance(zones, dict):
        zones = [zones]  # legacy single-zone format
    slow = []
    for zone in zones:
        a, b = max(start, finite(zone["from"], "Slow start")), min(end, finite(zone["to"], "Slow end"))
        rate = finite(zone.get("rate", 0.25), "Slow rate")
        if not 0 < rate <= 1:
            raise ValueError("Slow rate must be greater than zero and at most one")
        if b > a:
            slow.append((a, b, rate))
    cuts = sorted({start, end, *(t for t, _ in freezes), *(t for a, b, _ in slow for t in (a, b))})
    result = []
    for a, b in zip(cuts, cuts[1:]):
        rate = next((r for s, e, r in slow if s <= (a+b)/2 < e), 1.0)
        result.append(Segment("motion", a, b, rate))
        for time, seconds in freezes:
            if abs(time - b) < 1e-6:
                result.append(Segment("freeze", time, time, hold=seconds))
    return result


def locate(segments: list[Segment], output_time: float) -> tuple[Segment, float]:
    elapsed = 0.0
    for segment in segments:
        if output_time < elapsed + segment.duration:
            return segment, segment.start if segment.kind == "freeze" else segment.start + (output_time-elapsed)*segment.rate
        elapsed += segment.duration
    return segments[-1], segments[-1].end

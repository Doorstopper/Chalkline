"""Shared CPU image/preview painter. Prototype tools fail closed on export.

Unported shapes survive project round trips; never silently omit them in exports.
"""
import math
import os
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPen, QPolygonF
from chalkline.rendering.text_layout import paint_text

SUPPORTED_TOOLS = {"arrow", "line", "circle", "text", "pen", "zone", "ground"}
COLORS = {"ours": "#50D890", "theirs": "#FF6B6B", "space": "#FFC93C",
          "path": "#68BFFF", "ball": "#FFFFFF", "flood": "#FFC93C"}


def ensure_fonts():
    """Qt offscreen doesn't discover Windows fonts; register the OS font explicitly."""
    if 'Segoe UI' not in QFontDatabase.families():
        font = Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts'/'segoeui.ttf'
        if font.is_file():
            QFontDatabase.addApplicationFont(str(font))
    if not QFontDatabase.families():
        raise RuntimeError('No fonts available for native annotation rendering')


def alpha_at(shape: dict, time: float, hold: float, burn_all: bool, freezing=False) -> float:
    if burn_all:
        return 1.0
    if shape.get("tool") == "ground" and shape.get("kf") and "linger" not in shape and not shape.get("keep"):
        return float(time >= shape["kf"][0]["t"] - 0.1)
    if "t" not in shape:
        return 0.0
    beat = shape["t"]
    if shape.get("keep"):
        return float(time >= beat - 0.1)
    linger = shape.get("linger")
    if linger == 0:
        return float(abs(time-beat) < 0.3 if freezing else beat-0.1 <= time <= beat+0.15)
    end = beat + max(linger if linger and linger > 0 else hold, 0.1)
    if time < beat-0.05 or time > end:
        return 0.0
    return max(0.0, min(1.0, (end-time)/0.5)) if linger and linger > 0 else 1.0


def ground_center(shape: dict, time: float) -> dict:
    keys = sorted(shape.get("kf", []), key=lambda k: k["t"])
    if not keys:
        return shape["a"]
    if time <= keys[0]["t"]:
        return keys[0]
    for a, b in zip(keys, keys[1:]):
        if time <= b["t"]:
            f = (time-a["t"])/max(1e-9, b["t"]-a["t"])
            return {"x": a["x"]+(b["x"]-a["x"])*f, "y": a["y"]+(b["y"]-a["y"])*f}
    return keys[-1]


def check_supported(mark: dict) -> None:
    unsupported = sorted({s.get("tool", "unknown") for s in mark.get("shapes", [])} - SUPPORTED_TOOLS)
    if unsupported:
        raise ValueError("Prototype cannot export these tools yet: " + ", ".join(unsupported))
    if any(s.get("plane") or s.get("bow") is not None or s.get("label") or s.get("w")
           for s in mark.get("shapes", [])):
        raise ValueError("Plane, curved/labelled lines and resized text are preserved but not export-ready yet")


def paint_annotations(painter: QPainter, width: int, height: int, mark: dict,
                      time: float, settings: dict, freezing=False) -> None:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scale = width / 900.0
    def point(value):
        return QPointF(value.get("x", 0)*width, value.get("y", 0)*height)
    for shape in mark.get("shapes", []):
        tool = shape.get("tool")
        if tool not in SUPPORTED_TOOLS:
            continue
        opacity = alpha_at(shape, time, settings.get("hold", 3), settings.get("burnAll", False), freezing)
        if opacity <= 0:
            continue
        painter.save()
        painter.setOpacity(opacity)
        color = QColor(COLORS.get(shape.get("color"), shape.get("color", "#FF795E")))
        pen = QPen(color, 3.2*scale*settings.get("lineWt", 1))
        painter.setPen(pen)
        a, b = point(shape.get("a", {})), point(shape.get("b", {}))
        if tool in ("arrow", "line"):
            painter.drawLine(a, b)
            if tool == "arrow":
                angle = math.atan2(b.y()-a.y(), b.x()-a.x())
                reach = 15*scale
                head = QPolygonF([b, QPointF(b.x()-reach*math.cos(angle-.45), b.y()-reach*math.sin(angle-.45)),
                                  QPointF(b.x()-reach*math.cos(angle+.45), b.y()-reach*math.sin(angle+.45))])
                painter.setBrush(color)
                painter.drawPolygon(head)
        elif tool == "circle":
            painter.drawEllipse(QRectF(a, b).normalized())
        elif tool == "ground":
            center = point(ground_center(shape, time))
            radius = shape.get("r", .035)*width
            painter.drawEllipse(center, radius, radius*.42)
        elif tool == "text":
            paint_text(painter, shape, width, height, color)
        elif tool in ("pen", "zone"):
            points = QPolygonF([point(p) for p in shape.get("pts", [])])
            if tool == "zone":
                fill = QColor(color)
                fill.setAlpha(45)
                painter.setBrush(fill)
                painter.drawPolygon(points)
            else:
                painter.drawPolyline(points)
        painter.restore()
    caption = mark.get("caption", "")
    if caption:
        painter.fillRect(QRectF(0, height-75*scale, width, 75*scale), QColor(10, 15, 23, 220))
        painter.setPen(QColor("#F3F0E8"))
        font = QFont("Segoe UI")
        font.setPixelSize(round(22*scale))
        painter.setFont(font)
        painter.drawText(QRectF(25*scale, height-65*scale, width-50*scale, 60*scale), 0x1000, caption)


def overlay_image(width: int, height: int, mark: dict, time: float, settings: dict, freezing=False) -> QImage:
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        paint_annotations(painter, width, height, mark, time, settings, freezing)
    finally:
        painter.end()
    return image

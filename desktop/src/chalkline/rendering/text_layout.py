"""One measurement/wrapping path for note placement, preview and export."""
from dataclasses import dataclass
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QFontMetricsF


@dataclass
class TextLayout:
    font: QFont
    lines: list[str]
    line_height: float
    width: float
    font_size: float


def measure_text(shape, width):
    scale = width/900
    size = shape.get('fs', 19)*scale
    font = QFont('Segoe UI')
    font.setPixelSize(max(1, round(size)))
    font.setWeight(QFont.Weight.DemiBold)
    metrics = QFontMetricsF(font)
    left = shape.get('a', {}).get('x', 0)
    cap = max(.15, min(2/3, .97-left))
    fraction = min(shape['w'], cap) if shape.get('w') else cap
    limit = max(20*scale, fraction*width)
    lines = []
    for paragraph in str(shape.get('text', '')).split('\n'):
        current = ''
        for word in paragraph.split():
            trial = current+' '+word if current else word
            if current and metrics.horizontalAdvance(trial) > limit:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    natural = max((metrics.horizontalAdvance(line) for line in lines), default=0)
    return TextLayout(font, lines, size*1.16, max(fraction*width, natural) if shape.get('w') else natural, size)


def place_notes(shape, column, row, width, height):
    # A preset chooses a new anchor; the previous one must not constrain wrapping.
    layout = measure_text({**shape, 'a': {'x': .04, 'y': .06}}, width)
    box_width = min(.92, layout.width/width)
    box_height = min(.9, len(layout.lines)*layout.line_height/height)
    x = (.04, .5-box_width/2, .96-box_width)[column]
    y = (.06, .5-box_height/2, .94-box_height)[row]
    shape['a'] = {'x': max(.01, min(.98, x)), 'y': max(.02, min(.96, y))}


def paint_text(painter, shape, width, height, color):
    layout = measure_text(shape, width)
    x, y = shape['a']['x']*width, shape['a']['y']*height
    pad = layout.font_size*.74
    painter.fillRect(QRectF(x-6*width/900, y-pad, layout.width+12*width/900,
                           (len(layout.lines)-1)*layout.line_height+2*pad), QColor(6, 13, 10, 209))
    painter.setFont(layout.font)
    painter.setPen(color)
    metrics = QFontMetricsF(layout.font)
    baseline = (metrics.ascent()-metrics.descent())/2
    for index, line in enumerate(layout.lines):
        painter.drawText(QPointF(x, y+index*layout.line_height+baseline), line)

"""Notes are ordinary legacy-compatible text annotations, one per beat or clip."""
from copy import deepcopy
from chalkline.domain.clips import COLORS
from chalkline.domain.timeline import clip_bounds, finite, freeze_stops


def validate_style(color, size, column, row):
    if color not in COLORS or not 10 <= finite(size, 'Text size') <= 60:
        raise ValueError('Choose a notes colour and text size between 10 and 60.')
    if column not in (0, 1, 2) or row not in (0, 1, 2):
        raise ValueError('Choose one of the nine notes positions.')
    return {'color': color, 'size': size, 'column': column, 'row': row}


def find_note(mark, at=None):
    for index, shape in enumerate(mark.get('shapes', [])):
        if shape.get('tool') != 'text' or not shape.get('_notes'):
            continue
        if at is None and shape.get('keep'):
            return index
        if at is not None and not shape.get('keep') and abs(shape.get('t', 0)-at) < .15:
            return index
    return None


def freeze_note_context(mark, position, offset, duration, hold, *, snap=False):
    """None means no nearby freeze; an empty text value means a blank freeze.

    Navigation reads this context without changing the saved clip draft. Explicit
    loading uses Apply's half-second snap; automatic loading requires a resting beat.
    """
    if not mark or duration <= 0:
        return None
    position = finite(position, 'Playhead')
    start, end = clip_bounds(mark, offset, duration)
    near = min(freeze_stops(mark, start, end, hold),
               key=lambda stop: abs(stop[0]-position), default=None)
    if near is None:
        return None
    distance = abs(near[0]-position)
    within_range = distance <= .5 if snap else distance < .15
    if not within_range:
        return None
    index = find_note(mark, near[0])
    shape = mark['shapes'][index] if index is not None else {}
    return {'at': near[0], 'text': shape.get('text', ''),
            'color': shape.get('color') if shape.get('color') in COLORS else ''}


def apply_notes(mark, text, mode, position, offset, duration, hold, style):
    if mode not in ('freeze', 'clip'):
        raise ValueError('Choose freeze or whole clip.')
    text = text.rstrip()
    if not text.strip():
        raise ValueError('Write some notes first.')
    validate_style(style['color'], style['size'], style['column'], style['row'])
    position = finite(position, 'Playhead')
    hold = finite(hold, 'Hold')
    if not 0 <= hold <= 30:
        raise ValueError('Hold must be between 0 and 30 seconds.')
    start, end = clip_bounds(mark, offset, duration)
    at = start
    if mode == 'freeze':
        at = position if start < position < end else mark['t']+offset
        stops = freeze_stops(mark, start, end, hold)
        near = min(stops, key=lambda p: abs(p[0]-at), default=None)
        if near is not None and abs(near[0]-at) <= .5:
            at = near[0]
    result = deepcopy(mark)
    result['notes'] = text
    index = find_note(result, at if mode == 'freeze' else None)
    created = index is None
    shapes = result.setdefault('shapes', [])
    if created:
        index = len(shapes)
        shapes.append({'tool': 'text', '_notes': True, 'a': {'x': .04, 'y': .06}})
    shape = shapes[index]
    shape.update(text=text, color=style['color'], fs=style['size'], t=at)
    shape.pop('w', None)
    if mode == 'freeze':
        shape.pop('keep', None)
        shape['linger'] = 0
        freezes = result.setdefault('freezes', [])
        if not any(abs(f['at']-at) < .15 for f in freezes):
            freezes.append({'at': at, 'hold': hold or 3})
            freezes.sort(key=lambda f: f['at'])
    else:
        shape['keep'] = 1
        shape.pop('linger', None)
    return result, index, created

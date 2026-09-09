"""Lossless markup creation and edits in normalized source coordinates."""
from copy import deepcopy
import math
from chalkline.domain.timeline import finite

TOOLS = ('arrow', 'line', 'circle', 'pen', 'zone', 'ground', 'text')
COLORS = ('ours', 'theirs', 'space', 'path', 'ball', 'flood')


def point(x, y):
    return {'x': max(0, min(1, finite(x, 'X'))), 'y': max(0, min(1, finite(y, 'Y')))}


def make_shape(tool, a, b, at, color='space', size=19, points=None, text=''):
    if tool not in TOOLS or color not in COLORS:
        raise ValueError('Choose a drawing tool and colour.')
    shape = dict(tool=tool, color=color, t=finite(at, 'Drawing time'), linger=0, a=deepcopy(a), b=deepcopy(b))
    if tool == 'text':
        if not text.strip():
            raise ValueError('Enter annotation text.')
        shape.update(text=text, fs=size)
    elif tool == 'pen':
        shape['pts'] = deepcopy(points or [a, b])
    elif tool == 'zone':
        shape['pts'] = [deepcopy(a), {'x': b['x'], 'y': a['y']}, deepcopy(b), {'x': a['x'], 'y': b['y']}]
    elif tool == 'ground':
        shape['r'] = max(.005, min(.5, math.hypot(b['x']-a['x'], (b['y']-a['y'])*9/16)))
    return shape


def edit_shape(shape, field, value, duration):
    result = deepcopy(shape)
    if field == 'color':
        if value not in COLORS:
            raise ValueError('Choose a markup colour.')
        result['color'] = value
    elif field == 'fs':
        size = finite(value, 'Text size')
        if shape.get('tool') != 'text' or not 10 <= size <= 60:
            raise ValueError('Text size must be between 10 and 60.')
        result['fs'] = size
    elif field == 'text':
        if shape.get('tool') != 'text' or not isinstance(value, str) or not value.strip():
            raise ValueError('Enter annotation text.')
        result['text'] = value
    elif field == 't':
        at = finite(value, 'Drawing time')
        if not 0 <= at <= duration:
            raise ValueError('Drawing time must be inside the footage.')
        if shape.get('tool') == 'ground' and shape.get('kf'):
            # Moving the ring's start must move its motion path in time too,
            # matching the web markup timeline's source-time translation.
            delta = at - finite(shape.get('t'), 'Original drawing time')
            if not isinstance(result['kf'], list):
                raise ValueError('Ground tracking keyframes must be a list.')
            for keyframe in result['kf']:
                if not isinstance(keyframe, dict):
                    raise ValueError('A ground tracking keyframe is invalid.')
                keyframe['t'] = finite(keyframe.get('t'), 'Keyframe time') + delta
        result['t'] = at
    elif field == 'linger':
        linger = finite(value, 'Display duration')
        if not 0 <= linger <= 30:
            raise ValueError('Display duration must be between 0 and 30 seconds.')
        result.pop('keep', None)
        result['linger'] = linger
    elif field == 'keep':
        result.pop('linger', None)
        result['keep'] = 1
    else:
        raise ValueError('Unsupported markup change.')
    return result


def move_shape(shape, dx, dy):
    if shape.get('tool') not in TOOLS or shape.get('plane') or shape.get('bow') is not None:
        raise ValueError('Moving this specialist geometry is not available yet.')
    result = deepcopy(shape)
    points = [result[k] for k in ('a', 'b') if isinstance(result.get(k), dict)]
    points += result.get('pts', []) + result.get('kf', [])
    if not points:
        raise ValueError('This drawing has no editable position.')
    dx, dy = finite(dx, 'X movement'), finite(dy, 'Y movement')
    dx = max(-min(p['x'] for p in points), min(dx, 1-max(p['x'] for p in points)))
    dy = max(-min(p['y'] for p in points), min(dy, 1-max(p['y'] for p in points)))
    for p in points:
        p['x'] += dx
        p['y'] += dy
    return result

"""Validated edits retain absolute source times and unknown legacy fields."""
from copy import deepcopy
import math
from chalkline.domain.timeline import clip_bounds, finite


def snap(value, step=.1):
    return round(math.floor(finite(value, 'Time')/step+.5)*step, 6)


def slow_zones(mark):
    zones = mark.get('slow', [])
    return [zones] if isinstance(zones, dict) else zones


def drag_timing(mark, kind, index, edge, source_time, offset, duration):
    """Move one raw timing entry without sorting or changing its neighbours.

    Coordinates are absolute source seconds, including for offset projects.
    """
    edges = {'freezes': ('at',), 'slow': ('from', 'to')}
    if kind not in edges or edge not in edges[kind]:
        raise ValueError('Choose a freeze point or a slow-motion edge.')
    entries = slow_zones(mark) if kind == 'slow' else mark.get('freezes', [])
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(entries):
        raise ValueError('This timing point no longer exists.')
    wanted = snap(finite(source_time, 'Drag time'))
    start, end = clip_bounds(mark, finite(offset, 'Offset'), finite(duration, 'Video duration'))
    entry = deepcopy(entries[index])
    if kind == 'freezes':
        entry['at'] = max(start, min(end, wanted))
    else:
        keep = 'to' if edge == 'from' else 'from'
        other = finite(entry[keep], f'Slow {keep}')
        low = start if edge == 'from' else max(start, other + .1)
        high = min(end, other - .1) if edge == 'from' else end
        if high < low - 1e-8:
            raise ValueError('There is no room for this edge. Move the other edge or widen the clip first.')
        entry[edge] = max(low, min(high, wanted))
    result = deepcopy(mark)
    updated = deepcopy(entries)
    updated[index] = entry
    result[kind] = updated[0] if kind == 'slow' and isinstance(mark.get('slow'), dict) else updated
    return result


def update_timing(mark, kind, index, values, offset, duration):
    result = deepcopy(mark)
    entries = deepcopy(slow_zones(mark) if kind == 'slow' else mark.get('freezes', []))
    if kind not in ('slow', 'freezes') or index < -1 or index >= len(entries):
        raise ValueError('This timing point no longer exists.')
    start, end = clip_bounds(mark, offset, duration)
    entry = {} if index == -1 else entries[index]
    def bounded(value):
        return max(start, min(end, snap(value)))
    if kind == 'freezes':
        hold = finite(values['hold'], 'Freeze hold')
        if not .5 <= hold <= 30:
            raise ValueError('Freeze hold must be between 0.5 and 30 seconds.')
        entry.update(at=bounded(values['at']), hold=snap(hold, .5))
    else:
        rate = finite(values['rate'], 'Slow rate')
        if rate not in (.1, .25, .5):
            raise ValueError('Choose 0.1, 0.25 or 0.5 speed.')
        a, b = sorted((bounded(values['from']), bounded(values['to'])))
        if b-a < .1-1e-8:
            raise ValueError('A slow section must span at least 0.1 source seconds.')
        entry.update({'from': a, 'to': b, 'rate': rate})
    if index == -1:
        entries.append(entry)
    entries.sort(key=lambda e: e['from' if kind == 'slow' else 'at'])
    result[kind] = entries
    return result


def remove_timing(mark, kind, index):
    if kind not in ('slow', 'freezes'):
        raise ValueError('Unknown timing type.')
    result = deepcopy(mark)
    entries = deepcopy(slow_zones(mark) if kind == 'slow' else mark.get('freezes', []))
    if not 0 <= index < len(entries):
        raise ValueError('This timing point no longer exists.')
    entries.pop(index)
    if entries:
        result[kind] = entries
    else:
        result.pop(kind, None)
    return result

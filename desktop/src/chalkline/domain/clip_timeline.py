"""Source-time strip geometry and lossless clip trimming."""
from copy import deepcopy
from .timeline import clip_bounds, finite, freeze_stops
from .timing_edits import slow_zones, snap


def strip_model(mark, offset, duration, settings, window=None):
    if not mark or duration <= 0:
        return {}
    start, end = clip_bounds(mark, offset, duration)
    pad = max(1.5, (end-start)*.5)
    left, right = max(0, start-pad), min(duration, end+pad)
    if window:
        left, right = window
    hold = settings.get('hold', 3) if settings.get('autoFreeze', True) else 0
    # Keep every manual point addressable even when playback merges nearby beats.
    # Auto beats are read-only hints; moving them would mean moving annotations.
    manual = mark.get('freezes', [])
    freezes = [dict(at=f['at'], end=f['at'], index=i, label=f"Freeze: {f['hold']:g}s",
                    kind='freezes', automatic=False, active=start+.1<f['at']<end-.1)
               for i, f in enumerate(manual) if left <= f['at'] <= right]
    for at, seconds in freeze_stops(mark, 0, duration, hold):
        if not left <= at <= right:
            continue
        if not any(abs(f['at']-at)<.15 for f in manual):
            freezes.append(dict(at=at, end=at, index=-1, label=f'Automatic freeze: {seconds:g}s',
                                kind='freezes', automatic=True, active=start+.1<at<end-.1))
    slow = [dict(at=max(left, z['from']), end=min(right, z['to']), sourceFrom=z['from'], sourceTo=z['to'], index=i,
                 label=f"Slow: {z['rate']:g}x", kind='slow', active=z['to']>start and z['from']<end)
            for i, z in enumerate(slow_zones(mark)) if z['to']>left and z['from']<right]
    marks = [dict(at=s['t'], end=s['t'], index=i, label=s.get('tool', 'Drawing'), kind='markup', active=start<=s['t']<=end)
             for i, s in enumerate(mark.get('shapes', []))
             if s.get('t') is not None and left <= s['t'] <= right and s.get('tool') != 'ground']
    return dict(start=start, end=end, left=left, right=right, tag=mark['t']+offset,
                freezes=freezes, slow=slow, marks=marks)


def trim_edge(mark, edge, source_time, offset, duration):
    if edge not in ('start', 'end'):
        raise ValueError('Choose the start or end handle.')
    source_time = finite(source_time, 'Trim time')
    tag = finite(mark['t'], 'Tag time') + finite(offset, 'Offset')
    if not 0 <= tag <= duration:
        raise ValueError('The tag is outside the footage; check the match offset before trimming.')
    start, end = clip_bounds(mark, offset, duration)
    result = deepcopy(mark)
    if edge == 'start':
        before = max(0, min(3600, tag, snap(tag-source_time, .5)))
        if end-(tag-before) < .1:
            before = min(tag, max(before, .1-(end-tag)))
        result['pre'] = before
    else:
        after = max(0, min(3600, duration-tag, snap(source_time-tag, .5)))
        if tag+after-start < .1:
            after = min(duration-tag, max(after, .1-(tag-start)))
        result['post'] = after
    clip_bounds(result, offset, duration)
    return result


def set_trim(mark, before, after, offset, duration):
    before, after = finite(before, 'Before'), finite(after, 'After')
    if not all(0 <= value <= 3600 for value in (before, after)):
        raise ValueError('Before and after must be between 0 and 3600 seconds.')
    result = deepcopy(mark)
    result.update(pre=before, post=after)
    clip_bounds(result, offset, duration)
    return result

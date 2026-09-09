"""Source-time navigation independent of Qt playback and display sort order."""
import math
from chalkline.domain.clips import clip_rows

RATES = (.1, .25, .5, 1, 1.5, 2, 3)


def adjacent_clip(session, player_filter, selected_id, direction):
    rows = sorted(clip_rows(session, player_filter), key=lambda m: m['t'])
    if not rows:
        return None
    index = next((i for i, m in enumerate(rows) if m['id'] == selected_id), None)
    if index is None:
        return rows[0 if direction > 0 else -1]['id']
    return rows[max(0, min(len(rows)-1, index + (1 if direction > 0 else -1)))]['id']


def next_markup(mark, position, duration):
    times = sorted({s['t'] for s in mark.get('shapes', [])
                    if isinstance(s.get('t'), (int, float)) and math.isfinite(s['t']) and 0 <= s['t'] <= duration})
    return next((t for t in times if t > position + .05), times[0] if times else None)


def review_offset(segments, source_time):
    """Seek into a plan without replaying earlier freeze holds."""
    elapsed = 0
    for segment in segments:
        if segment.kind == 'freeze' and abs(source_time-segment.start) < .000001:
            return elapsed
        if segment.kind == 'motion' and source_time < segment.end:
            return elapsed + max(0, source_time-segment.start)/segment.rate
        elapsed += segment.duration
    return elapsed

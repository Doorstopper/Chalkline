"""Tag and list semantics retained from the v212 Studio."""
from copy import deepcopy
import math
import time
import uuid

COLORS = ('ours', 'theirs', 'space', 'path', 'ball', 'flood')
TAG_KEYS = 'QWERTYUIOP'
DEFAULT_PADS = [
    {'label': label, 'color': color, 'pre': 2, 'post': 7, 'ask': ask}
    for label, color, ask in (
        ('On the ball', 'ours', 'What could you see before it came to you?'),
        ('Off the ball', 'space', 'Where were you? Where could you have been?'),
        ('Passing option', 'path', 'Who else was on? Why did you choose that one?'),
        ('Defending', 'theirs', 'Which way were you sending them?'),
        ('Goal or chance', 'flood', 'What started this? Go back three passes.'),
        ('Team shape', 'ball', 'Are we too close together or too far apart?'),
        ('Attacking', 'path', 'What was on before the final ball?'),
    )
]


def pads_for(session):
    # Empty pads in the first native prototype meant "not implemented".
    return session.get('pads') or deepcopy(DEFAULT_PADS)


def players_of(mark):
    return [str(p).strip() for p in mark.get('players', [mark.get('player', '')]) if str(p).strip()]


def set_players(mark, names):
    seen = set()
    result = []
    for name in names:
        name = name.strip()
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            result.append(name)
    mark['players'] = result
    mark.pop('player', None)


def make_mark(session, pad, index, position, playing, lag):
    at = max(0, position - (lag if playing else 0)) - session.get('offset', 0)
    return {'id': uuid.uuid4().hex, 't': at, 'padIndex': index,
            'label': pad['label'], 'color': pad['color'], 'ask': pad.get('ask', ''),
            'pre': pad.get('pre', 2), 'post': pad.get('post', 7),
            'caption': '', 'shapes': [], 'player': session.get('defaultPlayer', '').strip(),
            'u': round(time.time()*1000)}


def validate_pad(pad):
    result = deepcopy(pad)
    result['label'] = str(result.get('label', '')).strip()
    if not result['label']:
        raise ValueError('Each pad needs a label.')
    if result.get('color') not in COLORS:
        raise ValueError('Choose a pad colour from the list.')
    for key in ('pre', 'post'):
        value = float(result[key])
        if not math.isfinite(value) or not 0 <= value <= 3600:
            raise ValueError('Before and after must be between 0 and 3600 seconds.')
        result[key] = value
    return result


def clip_rows(session, player_filter='__all'):
    marks = session['marks']
    # Numbers belong to source chronology, independent of display grouping/filter.
    numbers = {m['id']: i+1 for i, m in enumerate(sorted(marks, key=lambda m: m['t']))}
    order = session.get('clipSort', 'time')
    rows = []
    for mark in marks:
        players = players_of(mark)
        if player_filter == '__none' and players:
            continue
        if player_filter not in ('__all', '__none') and player_filter.casefold() not in [p.casefold() for p in players]:
            continue
        group = {'player': players[0] if players else 'Team', 'category': mark.get('label', ''),
                 'kind': {'highlight': 'Highlights', 'learning': 'Learning'}.get(mark.get('kind'), 'Other clips')}.get(order, '')
        rows.append({**mark, 'number': numbers[mark['id']], 'playerText': ', '.join(players), 'group': group,
                     'displayTime': mark['t'] + session.get('offset', 0)})
    def key(mark):
        if order == 'kind':
            return ({'highlight': 0, 'learning': 1}.get(mark.get('kind'), 2), mark['t'])
        if order == 'player':
            players = players_of(mark)
            return (not bool(players), (players[0] if players else '').casefold(), mark['t'])
        if order == 'category':
            return (mark.get('label', '').casefold(), mark['t'])
        return (mark['t'],)
    return sorted(rows, key=key)


def delete_marks(session, ids):
    ids = set(ids)
    removed = [m['id'] for m in session['marks'] if m['id'] in ids]
    session['tomb'] = list(dict.fromkeys([*session.get('tomb', []), *removed]))
    session['marks'] = [m for m in session['marks'] if m['id'] not in ids]

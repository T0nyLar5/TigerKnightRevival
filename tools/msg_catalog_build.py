"""msg_catalog_build.py -> notes/re/protocol_catalog.md
Combines tools/msg_catalog.py (registry id->class), notes/battle/msg_dictionary.md (body layouts),
server/battle_server.py + battle_proto.py (handled/sent) and the newest 3 battleserver logs (counts)."""
import re, sys, os, json, subprocess, glob, time

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DLL = "C:/Program Files (x86)/Steam/steamapps/common/Tiger Knight/Binaries/Win32/SyncClient.dll"
PY = os.path.join(R, 'tools', '.venv', 'Scripts', 'python.exe')
cat = json.loads(subprocess.check_output([PY, '-I', os.path.join(R, 'tools', 'msg_catalog.py'), DLL]))
fs = sorted({int(x['dec'], 16) for x in cat} | {int(x['enc'], 16) for x in cat})


def own(x):
    if not x['classes']:
        return False
    s = int(x['site'], 16); d = int(x['dec'], 16)
    return not any(s < f < d for f in fs)


MANUAL = {0x2721: 'MsgReqMove', 0x2737: 'MsgReqPosition', 0x2738: 'MsgReqMoveActionStart', 0x2739: 'MsgReqMoveActionEnd'}
rows = {}
for x in cat:
    i = x['id']
    if own(x):
        rows[i] = (x['classes'][0], 'dll-registry (own codec)')
    elif i in MANUAL:
        rows[i] = (MANUAL[i], 'notes/log verified, registry ambiguous')
    else:
        rows[i] = ('?(id %#x)' % i, 'registry: codec shared / class unresolved')

body = {}
for ln in open(os.path.join(R, 'notes/battle/msg_dictionary.md'), encoding='utf8'):
    if not ln.startswith('| 0x'):
        continue
    c = [t.strip() for t in ln.split('|')]
    for h in (re.findall(r'0x[0-9a-fA-F]{3,4}', c[1]) if len(re.findall(r'0x[0-9a-fA-F]{3,4}', c[1])) == 1 else []):
        body.setdefault(int(h, 16), c[4][:90])

bs = open(os.path.join(R, 'server/battle_server.py'), encoding='utf8').read()
bp = open(os.path.join(R, 'server/battle_proto.py'), encoding='utf8').read()
consts = {m.group(1): int(m.group(2), 16) for m in re.finditer(r'^(T_\w+)\s*=\s*(0x[0-9A-Fa-f]+)', bp, re.M)}
impl = {}
for m in re.finditer(r'0x([0-9a-fA-F]{3,4})\b', bs):
    v = int(m.group(1), 16)
    if 0x3e8 <= v < 0x5000:
        impl[v] = impl.get(v, 0) + 1
for m in re.finditer(r'P\.(T_\w+)', bs):
    if m.group(1) in consts:
        impl[consts[m.group(1)]] = impl.get(consts[m.group(1)], 0) + 1
name2id = {n: i for i, (n, _) in rows.items()}

logs = sorted(glob.glob(os.path.join(R, 'server/logs/battleserver_*.log')))[-3:]
rc = {}; sc = {}
for lg in logs:
    for ln in open(lg, encoding='utf8', errors='replace'):
        if ' RAW ' in ln:
            continue
        m = re.match(r'^[\d:.]+ (RECV|SEND)\b(.*)', ln)
        if not m:
            continue
        d = rc if m.group(1) == 'RECV' else sc
        t = re.search(r'type_0x([0-9a-f]+)', m.group(2)) or re.search(r'\b0x([0-9a-f]{3,4})\b', m.group(2))
        if t:
            v = int(t.group(1), 16)
        else:
            n = re.search(r'\b(Msg[A-Za-z0-9]+)\b', m.group(2))
            if not n or n.group(1) not in name2id:
                continue
            v = name2id[n.group(1)]
        d[v] = d.get(v, 0) + 1


def dirof(i, n):
    if i in (0x3e9, 0x3f4, 0x279c):
        return 'C>S'
    if n.startswith('MsgReq'):
        return 'C>S'
    if n.startswith('MsgCmd'):
        return 'S>C'
    if i in (0x3ea, 0x3ec, 0x3ee, 0x2715):
        return 'S>C'
    if i == 0x3eb:
        return 'both'
    return 'C>S' if 0x2710 <= i < 0x4e20 else ('S>C' if i >= 0x4e20 else '?')


CATS = [('tutorial/training', r'Tutorial|Challenge|Training|Dummy'),
        ('match flow/spawn/teleport', r'Connect|Ping|Loading|CountDown|AddPlayer|AddCreature|ReBorn|Reborn|Sync\b|CmdSync|Framework|Match|GameRestart|GameOver|Born|Teleport|Seek|Package|Split|Quit|Pause|Time|MD5|Plugin|NetError|NetLog|ClientSystem|PlayerCache|Observer|Watch|Enter|Leave|Siege|Flag|Occupy|Round|Champion'),
        ('movement', r'Move|Position|Bodyturn|BodyTurn|Jump|Dir\b|Pos\b|Run|Sprint|Walk|Ghost|Stand|Crouch|Follow|Ride|Mount|PolyArea|Break\b'),
        ('combat', r'Hit|Attack|Shot|Block|Shield|Weapon|Damage|Hurt|Kill|Dead|Die|Skill|Cut|Stagger|Push|Bounce|Assault|Strike|Bullet|Ammo|Fire|Arrow|Durab|Ballista|Catapult|Cannon|Pole|Hew|Slash|Parry|Dodge|Combo|Stab|Defen|Duel|Energy|Rage|Heal|Health|Poison|Buff|Mc[A-Z]|Throw|Spear|Ambush'),
        ('troops/AI', r'Troop|Soldier|Squad|Army|Ai[A-Z]|Order|Formation|Command|Animal|Detect|Creature|Summon|Horse|Camp'),
        ('results/rewards', r'Result|Reward|Score|Exp|Gold|Rank|Stat|Win|Lose|Mvp|Honor|Achiev|Settle'),
        ('chat/social', r'Chat|Voice|Emotion|Emoji|Friend|Team|Tip|Message|Speak|Shout|Talk|Say|Vote|Report|Gesture|Taunt')]


def cat_of(n):
    for c, p in CATS:
        if re.search(p, n):
            return c
    return 'other'


CORE = r'Connect|Ping|Framework|Loading|CountDown|AddPlayer|AddCreature|ReBorn|CmdSync\b|CmdSync$|PlayStateChange|ReqMove|Position|Bodyturn|MoveAction|ControlAi|Tutorial|Ghost|MatchEnd'


def prio(i, n, c):
    if re.search(CORE, n) and 'MD5' not in n:
        return 'core-to-play'
    if c == 'chat/social' or re.search(r'NetLog|NetError|Plugin|Voice|Emotion|Gesture|Taunt|Report|Vote', n):
        return 'ignorable'
    if c != 'other':
        return 'nice-to-have'
    return 'ignorable'


st = {'total': 0, 'handled': 0, 'unh_seen': 0, 'never': 0}
tbl = []
for i in sorted(rows):
    n, src = rows[i]; d = dirof(i, n); c = cat_of(n); p = prio(i, n, c)
    r = rc.get(i, 0); s = sc.get(i, 0); h = (i in impl) or s > 0
    st['total'] += 1
    if h:
        st['handled'] += 1; status = 'handled/sent'
    elif r or s:
        st['unh_seen'] += 1; status = 'UNHANDLED-seen'
    else:
        st['never'] += 1; status = 'never seen'
    tbl.append((i, n, d, c, p, status, r, s, body.get(i, 'unknown'), src))
core_un = [t for t in tbl if t[4] == 'core-to-play' and t[5] != 'handled/sent']
seen_un = [t for t in tbl if t[5] == 'UNHANDLED-seen']
H = ['# Battle protocol catalog (SyncClient.dll Win32) - generated %s' % time.strftime('%Y-%m-%d'),
     'Generated by `tools\\msg_catalog_build.py` (registry extraction `tools\\msg_catalog.py`). Rerun the script instead of hand-editing the table.',
     '',
     '## Summary',
     '- Total registered message ids: **%d** (ids 0x3e9..0x4f4a; registry init fn 0x10093050 calls 0x10092c10 with (id, encoder, decoder)).' % st['total'],
     '- Handled/sent by battle_server.py in some variant (id literal or P.T_ constant referenced): **%d**' % st['handled'],
     '- Unhandled but seen in the newest 3 logs (%s): **%d**' % (', '.join(os.path.basename(l)[13:-4] for l in logs), st['unh_seen']),
     '- Never seen in those logs: **%d**' % st['never'],
     '- Names: id -> class name via shared_ptr<MsgX> RTTI only (the DLL has no id-name table). Rule (checked against ~20 known ids): the class whose sp_counted ctor is the last one below the decoder function, with no other codec function in between. About 40 ids (mostly Req 0x271d-0x27bf) have a shared codec: name "?(id)" = unresolved (46 classes without own codec are listed at the bottom; matching needs decompiling senders). Hypothesis (H) overall; "own codec" rows are likely right.',
     '- Direction from name prefix (Req=C>S, Cmd=S>C); exceptions exist (client sends 0x4e3e PlayStateChange, verified). Slave (in-frame) Sync.dll messages 1,2,3,7,8,9,200,401-403 are in notes/battle/msg_dictionary.md, not here.',
     '- Body layout: only where notes/battle/msg_dictionary.md has it; otherwise "unknown" (decode needs the decoder at `dec`, see tools/msg_catalog.py output).',
     '- Counts = RECV / SEND lines in the 3 newest battleserver logs (SEND from our own log lines).',
     '- Categories/priorities are keyword heuristics on the name (core-to-play = connect/ping/loading/spawn/move/position/tutorial/sync); review before relying on them.',
     '',
     '### Unhandled core-to-play messages']
for t in core_un[:30]:
    H.append('- %#x %s (%s, %s, recv=%d) %s' % (t[0], t[1], t[2], t[5], t[6], t[8][:60]))
H += ['', '### Unhandled but seen in logs (client sends, server ignores)']
for t in sorted(seen_un, key=lambda t: -t[6])[:40]:
    H.append('- %#x %s recv=%d send=%d [%s/%s]' % (t[0], t[1], t[6], t[7], t[3], t[4]))
H += ['', '## Table', '| id | name | dir | category | priority | status | recv | send | body layout | name source |', '|---|---|---|---|---|---|---|---|---|---|']
for t in tbl:
    H.append('| 0x%x | %s | %s | %s | %s | %s | %d | %d | %s | %s |' % (t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8].replace('|', '/'), t[9]))
used = {v[0] for v in rows.values() if not v[0].startswith('?')}
allc = sorted(set(re.findall(rb'sp_counted_impl_p@U(Msg\w+?)@@@', open(DLL, 'rb').read())))
un = [c.decode() for c in allc if c.decode() not in used]
H += ['', '## Classes with RTTI but no own registry codec (%d); their ids are among the "?" rows' % len(un), ', '.join(un)]
open(os.path.join(R, 'notes/re/protocol_catalog.md'), 'w', encoding='utf8').write('\n'.join(H) + '\n')
print(st, len(core_un))

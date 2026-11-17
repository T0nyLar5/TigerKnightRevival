"""SyncClient wire protocol helpers (shared by battle_server.py and the self-test).
See notes/battle/sync_protocol.md (old sections 8 and 10) for the evidence behind every constant.

Stream : both directions are XORed with a fixed keystream, one independent counter per direction,
         ks[n] = A[n%256] ^ B[(n//256)%256]            (confirmed by real traffic, client->server)
Frame  : u16 len (includes these 4 header bytes) | u16 type | body          (little endian)
Body   : "old" messages (0x3e9) use fixed u32s; all others use protobuf-style LEB128 varints,
         strings are u16 length + bytes.
"""
import struct

# ---- message types ---------------------------------------------------------------------------
T_CONNECT = 0x3E9           # c->s  4 x u32 fixed: 1, playerId, 1, token                 [confirmed]
T_CONNECT_ACK = 0x3EA       # s->c  varint code                                          [layout from DLL, effect guessed]
T_PING = 0x3EB              # both  varint a, varint b ; client answers with its own time + echo of b
T_MD5CHECK = 0x3EC          # s->c  varint, string, string (client data check)
T_PINGVAL = 0x3EE           # s->c  varint playerId, varint ping
T_CLIENT_INFO = 0x3F4       # c->s  varint 0, string " [Win64]"                         [confirmed]
T_FRAMEWORK = 0x2715        # s->c  frame: varint f1, varint frameNo, u8 flag, string payload
T_REQ_PLAYER_BODYTURN = 0x2754   # c->s MsgReqPlayerBodyturn: uvar uid, u8 a, u8 b, u8 c, 2 x 1-byte-varint-ish (codec 0x100535b0) [H layout, M meaning]
T_CMD_PLAY_STATE_CHANGE = 0x4E3E  # c->s seen: MsgCmdPlayStateChange: uvar uid, u16-varint state, u8 bool (codec 0x10065fb0/0x100661a0)
T_SELF_PING = 0x279C        # c->s  varint, varint                                       [confirmed]
# --- Sync.dll slave messages (payload INSIDE MsgFramework frames; header u16 len|u16 type) ---
# Primitives (Sync.dll 0x10003630/0x1000a3d0/0x10003870/0x10001260): uvar = LEB128, svar = zigzag LEB128,
# f16 = IEEE half float (2 bytes LE, table-converted), bool = 1 byte.
S_ADD_PLAYER = 1            # uid uvar | kind svar | f0c uvar | f10 uvar | 7 x f16 (pos xyz, dir xyz, extra) | bool
S_ADD_PERSON = 2            # reader 0x1003be20 (uid,kind,f0c,f10,6 x f16,uvar,f16,uvar): not sent yet
S_ADD_CREATURE = 3          # same reader as 2: not sent yet
S_INIT = 7                  # header only: Sync.dll dispatcher 0x10034630 just calls callback vtable+4 (no body read) [H]
S_BATTLE_START = 8          # header only: sets running flag [slave+0x2c], calls callback vtable+0x14 [guess: begin battle]
T_CMD_SYNC = 0x4E20         # s->c  varint + string(u16 len + bytes) [H, SyncClient 0x10060aa0/0x1008be30]; slave vtable+0x50 is a no-op, client only sets synced flag
T_CMD_ADD_PLAYER = 0x4E22   # s->c top-level (SyncClient b41c0 -> vtable+0x1bc = 0x100afab0): creates PlayerCtl; see notes step 5
T_CMD_REBORN = 0x4E80       # s->c top-level (b41c0 -> 0x100b00b0 "OnProcess_MsgCmdReBorn"): spawns the pawn in UE3; see notes step 5
T_USER_LOADING_FINISH = 0x4E91  # varint f1, varint n, n x string
T_LOADING_COMPLETE = 0x4E92     # varint
T_COUNTDOWN = 0x4E96            # varint f1, varint state, varint value

NAMES = {
    0x3E9: "MsgConnect", 0x3EA: "MsgConnectAck", 0x3EB: "MsgPing", 0x3EC: "MsgMD5Check",
    0x3ED: "MsgInitiativeQuit", 0x3EE: "MsgPingVal", 0x3EF: "MsgReqPause", 0x3F0: "MsgCheckTime",
    0x3F4: "MsgClientSystemInfo", 0x3F5: "MsgLoadPlayerCache", 0x2712: "MsgSplitPkg",
    0x2713: "MsgSplitCompressPackage", 0x2714: "MsgPackage", 0x2715: "MsgFramework",
    0x279C: "MsgReqSelfPing", 0x2754: "MsgReqPlayerBodyturn", 0x4E3E: "MsgCmdPlayStateChange", 0x4E24: "MsgCmdBodyTurn", 1: "SlaveAddPlayer", 2: "SlaveAddCreature", 3: "SlaveAddPerson", 7: "SlaveInit", 8: "SlaveBattleStart", 0x4E20: "MsgCmdSync", 0x4E22: "MsgCmdAddPlayer", 0x4E80: "MsgCmdReBorn", 0x4E21: "MsgCmdTerrainType",
    0x4E91: "MsgCmdUserLoadingFinish", 0x4E92: "MsgCmdLoadingComplete",
    0x4E93: "MsgCmdSyncTutorialStage", 0x4E96: "MsgCmdCountDownUpdate",
}


# ---- stream cipher ---------------------------------------------------------------------------
def _tables():
    a, al = [], 0x1F
    for _ in range(256):
        a.append(al)
        al = ((((al << 5) & 0xFF) + 0xFD) * al + 7) & 0xFF
    b, cl = [], 0x3F
    for _ in range(256):
        al = (cl * 0x7A) & 0xFF
        al = (al - 0x31) & 0xFF
        al = (al * cl) & 0xFF
        b.append(cl)
        cl = (al - 0x1B) & 0xFF
    return a, b


KA, KB = _tables()


class StreamCrypt:
    """One direction of a connection: XOR with the keystream, counter advances per byte."""

    def __init__(self):
        self.pos = 0

    def apply(self, data):
        p = self.pos
        out = bytes(c ^ KA[(p + i) & 255] ^ KB[((p + i) >> 8) & 255] for i, c in enumerate(data))
        self.pos = p + len(data)
        return out


# ---- primitives ------------------------------------------------------------------------------
def varint(v):
    v &= 0xFFFFFFFFFFFFFFFF
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def read_varint(buf, off):
    v, shift = 0, 0
    while True:
        b = buf[off]
        off += 1
        v |= (b & 0x7F) << shift
        if not b & 0x80:
            return v, off
        shift += 7


def lstr(s):
    if isinstance(s, str):
        s = s.encode("utf-8")
    return struct.pack("<H", len(s)) + s


def read_lstr(buf, off):
    n = struct.unpack_from("<H", buf, off)[0]
    return buf[off + 2:off + 2 + n], off + 2 + n


def frame(mtype, body=b""):
    return struct.pack("<HH", 4 + len(body), mtype) + body


def split_frames(buf):
    """Return (list of (type, body), remaining bytes)."""
    out, off = [], 0
    while len(buf) - off >= 4:
        ln, typ = struct.unpack_from("<HH", buf, off)
        if ln < 4:
            raise ValueError("bad frame length %d at +%d" % (ln, off))
        if len(buf) - off < ln:
            break
        out.append((typ, bytes(buf[off + 4:off + ln])))
        off += ln
    return out, bytes(buf[off:])


# ---- server -> client builders -----------------------------------------------------------------
def msg_connect_ack(code=0):
    return frame(T_CONNECT_ACK, varint(code))


def msg_ping(a, b):
    return frame(T_PING, varint(a) + varint(b))


def msg_user_loading_finish(names, f1=0):
    body = varint(f1) + varint(len(names)) + b"".join(lstr(n) for n in names)
    return frame(T_USER_LOADING_FINISH, body)


def msg_loading_complete(v=0):
    return frame(T_LOADING_COMPLETE, varint(v))


def msg_countdown(state, value=0, f1=0):
    return frame(T_COUNTDOWN, varint(f1) + varint(state) + varint(value))


def msg_framework(frame_no, payload=b"", flag=0, f1=None):
    """One lockstep frame. payload = concatenated inner messages (each len|type|body).
    flag 2 would mean 'fragment, more follows' (client reassembles by frame_no)."""
    if f1 is None:
        f1 = frame_no
    return frame(T_FRAMEWORK, varint(f1) + varint(frame_no) + bytes([flag]) + lstr(payload))


def svar(v):
    return varint(((v << 1) ^ (v >> 63)) & 0xFFFFFFFFFFFFFFFF)


def f16(x):
    return struct.pack("<e", x)


def msg_add_player(uid, kind=0, f0c=0, f10=0, pos=(0.0, 0.0, 0.0), dirv=(1.0, 0.0, 0.0), extra=0.0, flag=False):
    body = varint(uid) + svar(kind) + varint(f0c) + varint(f10)
    for x in tuple(pos) + tuple(dirv) + (extra,):
        body += f16(x)
    body += bytes([1 if flag else 0])
    return frame(S_ADD_PLAYER, body)


def msg_add_person(uid, kind=0, f0c=0, f10=0, pos=(0.0, 0.0, 0.0), dirv=(1.0, 0.0, 0.0), a=0, b=0.0, c=0, mtype=S_ADD_PERSON):
    """Msg 2 (AddPerson) / 3 (AddCreature): uid,kind(svar),f0c,f10, 6 x f16, uvar a, f16 b, uvar c  [reader 0x1003be20, H]"""
    body = varint(uid) + svar(kind) + varint(f0c) + varint(f10)
    for x in tuple(pos) + tuple(dirv):
        body += f16(x)
    body += varint(a) + f16(b) + varint(c)
    return frame(mtype, body)


def msg_slave_init():
    return frame(S_INIT)


def msg_cmd_sync(v=0, blob=b""):
    return frame(T_CMD_SYNC, varint(v) + lstr(blob))


def _dataset(uid, n=80, alive=1, camp=1):
    """DataSet = n raw u32 LE. Indices read by SyncClient 0x100afab0/0x100b15d0: [0]=uid, [2]=alive(0 -> 'dead'),
    [0x10]=camp, [0x3e],[0x44],[0x49] used too (config ids, unknown) -> 0. n must be >= 74 (reads index 0x49)."""
    ds = [0] * n
    ds[0], ds[2], ds[0x10] = uid, alive, camp
    return varint(n) + struct.pack("<%dI" % n, *ds)


def msg_cmd_add_player(uid, name="tiger", is_self=True, ptype=0):
    """MsgCmdAddPlayer 0x4e22 [layout H from deserializer 0x10061820]:
    uvar a | u8 isSelf | svar ptype(0 normal,1 pending-list,2 watcher) | str name | uvar | uvar | str | 4 x uvar |
    vec<u8> (uvar n + bytes) | uvar N + N*4 raw (DataSet) | str"""
    b = varint(0) + bytes([1 if is_self else 0]) + svar(ptype) + lstr(name)
    b += varint(0) + varint(0) + lstr("") + varint(0) * 4 + varint(0) + _dataset(uid) + lstr("")
    return frame(T_CMD_ADD_PLAYER, b)


def msg_cmd_reborn(uid, name="tiger"):
    """MsgCmdReBorn 0x4e80 [layout H from deserializer 0x10070290]: uvar uid | uvar N + N*4 raw (DataSet) | str name | vec<u8>"""
    return frame(T_CMD_REBORN, varint(uid) + _dataset(uid) + lstr(name) + varint(0))


def msg_battle_start():
    return frame(S_BATTLE_START)


# ---- decoding for logs ---------------------------------------------------------------------------
def describe(mtype, body):
    name = NAMES.get(mtype, "type_0x%x" % mtype)
    try:
        if mtype == T_CONNECT and len(body) == 16:
            f = struct.unpack("<4I", body)
            return "%s f1=%d playerId=%d f3=%d token=%d" % (name, *f)
        if mtype == T_CLIENT_INFO:
            v, off = read_varint(body, 0)
            s, _ = read_lstr(body, off)
            return "%s v=%d str=%r" % (name, v, s.decode("utf-8", "replace"))
        if mtype in (T_SELF_PING, T_PING, T_PINGVAL, T_COUNTDOWN, T_CONNECT_ACK, T_LOADING_COMPLETE):
            vals, off = [], 0
            while off < len(body):
                v, off = read_varint(body, off)
                vals.append(v)
            return "%s varints=%s" % (name, vals)
        if mtype == T_FRAMEWORK:
            f1, off = read_varint(body, 0)
            fno, off = read_varint(body, off)
            flag = body[off]
            pl, _ = read_lstr(body, off + 1)
            inner = ""
            if pl:
                try:
                    subs, _ = split_frames(pl)
                    inner = " inner=[" + "; ".join(describe(t, b) for t, b in subs) + "]"
                except Exception:
                    inner = " " + pl.hex(" ")
            return "%s f1=%d frame=%d flag=%d payload=%dB%s" % (name, f1, fno, flag, len(pl), inner)
        if mtype == S_ADD_PLAYER and len(body) >= 20:
            off = 0
            uid, off = read_varint(body, off)
            k, off = read_varint(body, off)
            a, off = read_varint(body, off)
            b, off = read_varint(body, off)
            fl = struct.unpack_from("<7e", body, off)
            return "SlaveAddPlayer uid=%d kind=%d f0c=%d f10=%d floats=%s flag=%d" % (
                uid, (k >> 1) ^ -(k & 1), a, b, [round(x, 2) for x in fl], body[off + 14])
        if mtype == T_CMD_SYNC:
            v, off = read_varint(body, 0)
            s, _ = read_lstr(body, off)
            return "MsgCmdSync v=%d blob=%dB" % (v, len(s))
        if mtype in (S_ADD_PERSON, S_ADD_CREATURE):
            o = 0
            uid, o = read_varint(body, o)
            k, o = read_varint(body, o)
            a, o = read_varint(body, o)
            b, o = read_varint(body, o)
            fl = struct.unpack_from("<6e", body, o)
            return "Slave%s uid=%d kind=%d f0c=%d f10=%d floats=%s tail=%s" % (
                "AddCreature" if mtype == 2 else "AddPerson", uid, (k >> 1) ^ -(k & 1), a, b,
                [round(x, 2) for x in fl], body[o + 12:].hex(" "))
        if mtype == T_USER_LOADING_FINISH:
            f1, off = read_varint(body, 0)
            n, off = read_varint(body, off)
            names = []
            for _ in range(n):
                s, off = read_lstr(body, off)
                names.append(s.decode("utf-8", "replace"))
            return "%s f1=%d users=%s" % (name, f1, names)
    except Exception as e:  # logging must never crash the server
        return "%s (decode error %r) body=%s" % (name, e, body.hex(" "))
    return "%s body=%s" % (name, body.hex(" "))


# ===================================================================================================
# Variants 7-9 helpers (2026-11-05, notes/research_free_1105.md).  Everything below is NEW; the builders above
# are untouched so variants 0-6 behave exactly as before.
# ===================================================================================================
T_CMD_ADD_CREATURE = 0x4E23      # top-level: creates SoldierCtl etc.   body = uvar uid | uvar N | N x u32 DataSet   [H]
T_CMD_CONTROL_AI_PLAYER = 0x4E4A  # top-level: "you now run the AI of PlayerCtl uid"  body = uvar uid               [M]
NAMES.update({0x4E23: "MsgCmdAddCreature", 0x4E4A: "MsgCmdControlAiPlayer"})

DATASET_N = 132      # UE3 spawn code reads DataSet[0x7e]; the client re-serializes the message into a 0x400-byte buffer
                     # (SyncClient 0x100afab0), so N must be >= 127 and (4*N + ~60) < 1024  ->  132 is safe on both sides.
# Real equipment of soldier 112011 (soldiers.txt / armytype.txt, decrypted 2026-11-05): used for hero + troops.
GEAR_112011 = {0x18: 17000011, 0x19: 17100001, 0x1A: 17200001, 0x1B: 17300001, 0x1E: 18051001, 0x1F: 18052001}


# V19: on foot.  0x4e..0x55 = armytype.txt skilltype1..8 of 112011 (1021, 1022, 0...) [L]; 0x4c = soldiers.txt nFlagId; 0x56 hair; 0x4b = Energy 100 [L]
GEAR_FOOT_FULL = dict(GEAR_112011)
GEAR_FOOT_FULL.update({0x4B: 100, 0x4C: 15710100, 0x4E: 1021, 0x4F: 1022, 0x56: 1})
# V20: mounted.  armytype 111025 (cavalry): armor 17200105, weapon 18052005, horse 16000005 (horse.txt), saddle 15910105 (horsearmor.txt), skills 1111/1112/1113
# V21: V19 + config-id slots [0x3e],[0x44],[0x49],[0x4a] = soldier id 112011 (guess: client looks the speed row up by id)
GEAR_FOOT_IDS = dict(GEAR_FOOT_FULL)
GEAR_FOOT_IDS.update({0x3E: 112011, 0x44: 112011, 0x49: 112011, 0x4A: 112011})
# V24: V21 + direction slots [5,6,7] = (1,0,0) raw f32
GEAR_FOOT_DIR = dict(GEAR_FOOT_IDS)
GEAR_FOOT_DIR.update({5: 0x3F800000, 6: 0, 7: 0})
GEAR_MOUNTED_FULL = {0x1A: 17200105, 0x1E: 18052005, 0x22: 16000005, 0x23: 15910105,
                     0x4B: 100, 0x4C: 15710100, 0x4D: 1, 0x4E: 1111, 0x4F: 1112, 0x52: 1113, 0x56: 1}


def f32bits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def dataset_v2(uid, camp=1, hp=200, extra=None, n=DATASET_N):
    """DataSet with the slots whose meaning is now known.  From the Kingdom exe log string
    '+Remote Player team %d, health %d, weapon %d %d %d %d, helmetID %d, shawlID %d, armorID %d, shoesID %d':
    [0]=uid [2]=health (0 = dead) [3]=(max?)health [0x10]=team [0x18..0x1b]=helmet/shawl/armor/shoes ids (armor.txt)
    [0x1e..0x21]=weapon1..4 ids [0x22]=horse. Unit type [1]: 1 soldier, 2 horse, 4 boss. Everything else 0."""
    ds = [0] * n
    ds[0], ds[2], ds[3], ds[0x10] = uid, hp, hp, camp
    for k, v in (extra or {}).items():
        ds[k] = v
    return varint(n) + struct.pack("<%dI" % n, *ds)


def msg_cmd_add_player_v2(uid, name="tiger", is_self=True, camp=1, ds_extra=None, hp=200, a=0, face=b""):
    b = varint(a) + bytes([1 if is_self else 0]) + svar(0) + lstr(name)
    b += varint(0) + varint(0) + lstr("") + varint(0) * 4 + varint(0) + dataset_v2(uid, camp, hp, ds_extra) + lstr(face)
    return frame(T_CMD_ADD_PLAYER, b)


def msg_cmd_reborn_v2(uid, name="tiger", camp=1, ds_extra=None, hp=200):
    return frame(T_CMD_REBORN, varint(uid) + dataset_v2(uid, camp, hp, ds_extra) + lstr(name) + varint(0))


def msg_cmd_add_creature(uid, owner_uid, camp=1, soldier_class=1, ctype=1, hp=130, ds_extra=None):
    """0x4e23 (SyncClient 0x100afdc0): DataSet[1]=creature type (1 SoldierCtl), [0x32]=[0x35]=owner/hero uid (REQUIRED, else
    the soldier is silently dropped), [0x33]=soldier class 1..4 (= soldiers.txt SoldierKind: 1 foot, 2 archer, 3 cavalry, 4 horse archer)."""
    ex = {1: ctype, 0x32: owner_uid, 0x33: soldier_class, 0x35: owner_uid}
    ex.update(ds_extra or {})
    return frame(T_CMD_ADD_CREATURE, varint(uid) + dataset_v2(uid, camp, hp, ex))


def msg_control_ai_player(uid):
    return frame(T_CMD_CONTROL_AI_PLAYER, varint(uid))

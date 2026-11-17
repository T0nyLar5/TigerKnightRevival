"""Self-test for server/battle_server.py with a fake client that uses the REAL captured bytes.
Runs the server on a spare port (7791), checks framing/encryption/sequence, then kills it."""
import os, socket, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
import battle_proto as P

PORT = 7791
REAL_CONNECT_RAW = bytes.fromhex("34f5ff903d21129f09aa4eebb5b9ca7729 9586c3".replace(" ", ""))   # from battle_20261104_230356.log
REAL_INFO_RAW = bytes.fromhex("23d176cc08b53e3bff3ed3c9366 12b".replace(" ", ""))
ok = True


def check(c, msg):
    global ok
    print(("PASS " if c else "FAIL ") + msg)
    ok = ok and c


# sanity: our cipher turns the captured plaintext into the captured ciphertext
cc = P.StreamCrypt()
plain = bytes.fromhex("1400e9030100000011270000010000003930 0000".replace(" ", ""))
check(cc.apply(plain) == REAL_CONNECT_RAW, "cipher reproduces real captured MsgConnect bytes")
check(cc.apply(bytes.fromhex("0f00f4030008002 05b57696e36345d".replace(" ", ""))) == REAL_INFO_RAW, "cipher continues correctly for 0x3f4 (stream offset 20)")

def run_variant(v):
    print("=== variant %d ===" % v)
    global PORT
    PORT = 7791
    srv = subprocess.Popen([os.path.join(ROOT, "tools", ".venv", "Scripts", "python.exe"), "-I",
                            os.path.join(ROOT, "server", "battle_server.py"), str(PORT), "--variant", str(v)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        s = None
        for _ in range(50):
            try:
                s = socket.create_connection(("127.0.0.1", PORT), timeout=1); break
            except OSError:
                time.sleep(0.1)
        check(s is not None, "server accepts TCP connection")
        s.sendall(REAL_CONNECT_RAW)          # exactly the captured bytes
        time.sleep(0.4)
        s.sendall(REAL_INFO_RAW)             # captured 0x3f4
        rx = P.StreamCrypt()
        buf = b""
        msgs = []
        s.settimeout(0.3)
        end = time.time() + (2.5 if v < 4 else 7)
        while time.time() < end:
            try:
                d = s.recv(65536)
                if not d:
                    break
                buf += rx.apply(d)
            except socket.timeout:
                pass
        got, rest = P.split_frames(buf)
        check(rest == b"", "all reply bytes decrypt to whole well-framed messages (no trailing bytes)")
        types = [t for t, _ in got]
        check(len(got) > 10 and types[0] == P.T_CONNECT_ACK, "first reply is MsgConnectAck, %d messages in 2.5 s" % len(got))
        fws = [P.read_varint(b, P.read_varint(b, 0)[1])[0] for t, b in got if t == P.T_FRAMEWORK]
        check(len(fws) > 20 and fws == list(range(1, len(fws) + 1)), "frames advance 1..%d" % len(fws))
        check(any(t == P.T_LOADING_COMPLETE for t in types), "start sequence (LoadingComplete) sent")
        check(any(t == P.T_USER_LOADING_FINISH for t in types), "start sequence (UserLoadingFinish) sent")
        # slave messages travel inside frame payloads: find AddPlayer(1) then BattleStart(8)
        inner = []
        for t, b in got:
            if t == P.T_FRAMEWORK:
                o = P.read_varint(b, P.read_varint(b, 0)[1])[1] + 1
                pl, _ = P.read_lstr(b, o)
                sub, _ = P.split_frames(pl)
                inner += sub
        itypes = [t for t, _ in inner]
        check(P.S_BATTLE_START in itypes and (v == 6 or (P.S_ADD_PLAYER in itypes and itypes.index(P.S_ADD_PLAYER) < itypes.index(P.S_BATTLE_START))),
              "frame payloads carry slave AddPlayer then BattleStart")
        ap = P.msg_add_player(10001, kind=2, f0c=3, f10=4, pos=(1.5, -2.0, 0.25))
        check(P.split_frames(ap)[0][0][0] == 1 and "uid=10001 kind=2 f0c=3 f10=4" in P.describe(1, ap[4:]) and "[1.5, -2.0, 0.25" in P.describe(1, ap[4:]),
              "AddPlayer encode/decode round-trip")
        check(P.msg_battle_start() == bytes([4, 0, 8, 0]), "BattleStart is a bare 4-byte header")

        exp = {0: [1, 8], 1: [7, 1, 8], 2: [1, 8], 3: [7, 1, 2, 2, 2, 8], 4: [7, 1, 2, 2, 2, 8, 8], 5: [7, 1, 8], 6: [7, 8]}[v]
        sl = [t for t in itypes if t in (1, 2, 3, 7, 8)]
        check(sl[:len(exp)] == exp or (v == 4 and sl[:len(exp) - 1] == exp[:-1]), "v%d slave order %s (got %s)" % (v, exp, sl))
        check((P.T_CMD_SYNC in types) == (v >= 2), "v%d CmdSync top-level presence" % v)
        if v >= 2:
            check(types.index(P.T_CMD_SYNC) < types.index(P.T_FRAMEWORK), "CmdSync before first frame")
        if v >= 5:
            check(P.T_CMD_ADD_PLAYER in types and types.index(P.T_CMD_ADD_PLAYER) < types.index(P.T_FRAMEWORK), "v%d top-level MsgCmdAddPlayer before first frame" % v)
            check(P.T_CMD_REBORN in types and types.index(P.T_CMD_REBORN) > types.index(P.T_CMD_ADD_PLAYER), "v%d top-level MsgCmdReBorn after AddPlayer" % v)
            ap5 = dict((t, b) for t, b in got)[P.T_CMD_ADD_PLAYER]
            check(ap5[0:1] == bytes([0]) and ap5[1] == 1, "AddPlayer body starts uvar 0, isSelf=1")
            rb = dict((t, b) for t, b in got)[P.T_CMD_REBORN]
            o = P.read_varint(rb, 0)[1]
            n, o = P.read_varint(rb, o)
            check(P.read_varint(rb, 0)[0] == 10001 and n >= 74 and int.from_bytes(rb[o:o + 4], "little") == 10001, "ReBorn uid + DataSet[0]=uid, N>=74")
        print("types:", [hex(t) for t in types[:12]], "...")
        s.close()
    finally:
        srv.kill(); srv.wait()

for _v in range(7):
    run_variant(_v)

    # encode / round-trip of the new builders
    pe = P.msg_add_person(20001, kind=1, pos=(1.0, 2.0, 0.5), a=3, b=0.5, c=4)
    check("uid=20001 kind=1" in P.describe(2, pe[4:]), "AddPerson encode/decode")
    check(P.msg_slave_init() == bytes([4, 0, 7, 0]), "Init is bare header")
    cs = P.msg_cmd_sync(0, b"")
    check(cs == bytes([7, 0, 0x20, 0x4e, 0, 0, 0]) and "MsgCmdSync" in P.describe(0x4e20, cs[4:]), "CmdSync = varint + empty u16 string")

def run_variant_new(v):
    """variants 7-9 (corrected order, DataSet N=132, troops, bot)"""
    print("=== variant %d (new) ===" % v)
    srv = subprocess.Popen([os.path.join(ROOT, "tools", ".venv", "Scripts", "python.exe"), "-I",
                            os.path.join(ROOT, "server", "battle_server.py"), "7791", "--variant", str(v)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        s = None
        for _ in range(50):
            try:
                s = socket.create_connection(("127.0.0.1", 7791), timeout=1); break
            except OSError:
                time.sleep(0.1)
        check(s is not None, "server accepts TCP connection")
        s.sendall(REAL_CONNECT_RAW)
        time.sleep(0.4)
        s.sendall(REAL_INFO_RAW)
        rx = P.StreamCrypt(); buf = b""; s.settimeout(0.3)
        end = time.time() + 8.5
        while time.time() < end:
            try:
                d = s.recv(65536)
                if not d: break
                buf += rx.apply(d)
            except socket.timeout:
                pass
        got, rest = P.split_frames(buf)
        check(rest == b"", "v%d all bytes well framed" % v)
        # linear event list: (kind, type, body) in arrival order, frames expanded into their inner messages
        ev = []
        for t, b in got:
            if t == P.T_FRAMEWORK:
                o = P.read_varint(b, P.read_varint(b, 0)[1])[1] + 1
                pl, _ = P.read_lstr(b, o)
                for it, ib in P.split_frames(pl)[0]:
                    ev.append(("slave", it, ib))
            else:
                ev.append(("top", t, b))
        def idx(kind, typ, uid=None):
            for i, (k, t, b) in enumerate(ev):
                if k == kind and t == typ and (uid is None or P.read_varint(b, 0)[0] == uid or (t == 0x4e22 and False)):
                    return i
            return -1
        i_ap = [i for i, (k, t, b) in enumerate(ev) if k == "top" and t == P.T_CMD_ADD_PLAYER]
        i_sp = [i for i, (k, t, b) in enumerate(ev) if k == "slave" and t == P.S_ADD_PLAYER]
        i_rb = [i for i, (k, t, b) in enumerate(ev) if k == "top" and t == P.T_CMD_REBORN]
        i_bs = idx("slave", P.S_BATTLE_START)
        i_lc = idx("top", P.T_LOADING_COMPLETE)
        check(len(i_ap) == (2 if v >= 9 else 1) and len(i_sp) == len(i_ap) and len(i_rb) == len(i_ap), "v%d one AddPlayer/slave AddPlayer/ReBorn per hero(+bot)" % v)
        check(max(i_ap) < min(i_sp), "v%d PlayerCtl (0x4e22) before any slave AddPlayer" % v)
        check(max(i_sp) < min(i_rb), "v%d ReBorn only after slave unit exists" % v)
        check(max(i_rb) < i_lc < i_bs, "v%d ReBorn < LoadingComplete < BattleStart" % v)
        # DataSet sizes + contents
        for k, t, b in ev:
            if k == "top" and t in (P.T_CMD_ADD_PLAYER, P.T_CMD_REBORN, P.T_CMD_ADD_CREATURE):
                if t == P.T_CMD_ADD_PLAYER:
                    o = 1 + 1                        # uvar 0, isSelf
                    _, o = P.read_varint(b, 2)       # ptype svar
                    o = 2 + 1                        # (single-byte svar 0)
                    s_, o = P.read_lstr(b, o)        # name
                    for _i in range(2): _, o = P.read_varint(b, o)
                    s_, o = P.read_lstr(b, o)
                    for _i in range(4): _, o = P.read_varint(b, o)
                    _, o = P.read_varint(b, o)       # vec<u8> count (0)
                elif t == P.T_CMD_REBORN:
                    uid_, o = P.read_varint(b, 0)
                else:
                    uid_, o = P.read_varint(b, 0)
                n, o = P.read_varint(b, o)
                ds = [int.from_bytes(b[o + 4 * j:o + 4 * j + 4], "little") for j in range(n)]
                check(n == P.DATASET_N and n >= 127 and ds[2] > 0 and ds[0x10] in (1, 2) and ds[0x1E] == 18051001 and len(b) + 4 < 1000,
                      "v%d 0x%x DataSet N=%d uid=%d hp=%d camp=%d gear ok, size %d < 1024" % (v, t, n, ds[0], ds[2], ds[0x10], len(b) + 4))
                if t == P.T_CMD_ADD_CREATURE:
                    check(ds[1] == 1 and ds[0x32] == 10001 and ds[0x35] == 10001 and ds[0x33] == 1, "troop DataSet type=1 owner=10001 class=1")
        if v >= 8:
            i_ac = [i for i, (k, t, b) in enumerate(ev) if k == "top" and t == P.T_CMD_ADD_CREATURE]
            i_pe = [i for i, (k, t, b) in enumerate(ev) if k == "slave" and t == 3]
            check(len(i_ac) == 3 and len(i_pe) == 3 and max(i_ac) < min(i_pe) and max(i_rb) < min(i_ac), "v%d 3 troops: 0x4e23 x3 then slave Person x3, after hero ReBorn" % v)
            pe = [b for k, t, b in ev if k == "slave" and t == 3][0]
            check("uid=20001 kind=1" in P.describe(3, pe), "troop slave Person kind=1")
        else:
            check(not any(t in (P.T_CMD_ADD_CREATURE, P.T_CMD_CONTROL_AI_PLAYER) for k, t, b in ev), "v%d sends no troops/AI" % v)
        if v >= 9:
            i_ai = idx("top", P.T_CMD_CONTROL_AI_PLAYER)
            check(i_ai > max(i_rb) and P.read_varint(ev[i_ai][2], 0)[0] == 30001, "v9 ControlAiPlayer(30001) after its ReBorn")
        cds = [P.read_varint(b, P.read_varint(b, 0)[1])[0] for k, t, b in ev if k == "top" and t == P.T_COUNTDOWN]
        check(cds == [1, 2, 2, 2, 2, 3], "v%d countdown states 1,2,2,2,2,3 (got %s)" % (v, cds))
        s.close()
    finally:
        srv.kill(); srv.wait()

for _v in (7, 8, 9):
    run_variant_new(_v)

def run_variant_bisect(v):
    """variants 10-14: 11-04 baseline (+ late spawn / lone CmdSync / lone 0x4e22)"""
    print("=== variant %d (bisect) ===" % v)
    srv = subprocess.Popen([os.path.join(ROOT, "tools", ".venv", "Scripts", "python.exe"), "-I",
                            os.path.join(ROOT, "server", "battle_server.py"), "7791", "--variant", str(v)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        s = None
        for _ in range(50):
            try:
                s = socket.create_connection(("127.0.0.1", 7791), timeout=1); break
            except OSError:
                time.sleep(0.1)
        check(s is not None, "server accepts TCP connection")
        s.sendall(REAL_CONNECT_RAW); time.sleep(0.4); s.sendall(REAL_INFO_RAW)
        rx = P.StreamCrypt(); buf = b""; s.settimeout(0.3)
        end = time.time() + (7.5 if v >= 16 else 6.5)
        while time.time() < end:
            try:
                d = s.recv(65536)
                if not d: break
                buf += rx.apply(d)
            except socket.timeout:
                pass
        got, rest = P.split_frames(buf)
        check(rest == b"", "v%d all bytes well framed" % v)
        ev = []
        for t, b in got:
            if t == P.T_FRAMEWORK:
                o = P.read_varint(b, P.read_varint(b, 0)[1])[1] + 1
                pl, _ = P.read_lstr(b, o)
                for it, ib in P.split_frames(pl)[0]:
                    ev.append(("slave", it, ib))
            else:
                ev.append(("top", t, b))
        tops = [t for k, t, b in ev if k == "top"]
        # baseline part: ConnectAck, Ping, [optional lone CmdSync / 0x4e22], then loading sequence; nothing else before it
        head = [t for t in tops if t not in (P.T_FRAMEWORK,)]
        want_head = [P.T_CONNECT_ACK, P.T_PING]
        if v == 13: want_head += [P.T_CMD_SYNC]
        if v in (14, 15, 16, 17, 18): want_head += [P.T_CMD_ADD_PLAYER]
        want_head += [P.T_USER_LOADING_FINISH, P.T_LOADING_COMPLETE, P.T_COUNTDOWN, P.T_COUNTDOWN, P.T_COUNTDOWN]
        check(head[:len(want_head)] == want_head, "v%d top-level order = 11-04 baseline%s" % (v, {13: " + CmdSync", 14: " + 0x4e22", 15: " + 0x4e22", 16: " + 0x4e22", 17: " + 0x4e22", 18: " + 0x4e22"}.get(v, "")))
        # in-frame loading messages as on 11-04: [UserLoadingFinish+LoadingComplete], cd1, cd2, cd3
        fr = [(P.read_varint(b, P.read_varint(b, 0)[1])[0], b) for t, b in got if t == P.T_FRAMEWORK]
        inframe = [it for k, it, ib in ev if k == "slave"]
        check(inframe[:5] == [P.T_USER_LOADING_FINISH, P.T_LOADING_COMPLETE, P.T_COUNTDOWN, P.T_COUNTDOWN, P.T_COUNTDOWN][:5] or v in (11, 12) and inframe[:5] == [P.T_USER_LOADING_FINISH, P.T_LOADING_COMPLETE, P.T_COUNTDOWN, P.T_COUNTDOWN, P.T_COUNTDOWN],
              "v%d in-frame loading messages first (got %s)" % (v, [hex(x) for x in inframe[:6]]))
        fws = [f for f, _ in fr]
        check(fws == list(range(1, len(fws) + 1)) and len(fws) > 50, "v%d frames contiguous 1..%d" % (v, len(fws)))
        # nothing hero-related for the baseline-like variants
        n_ap = tops.count(P.T_CMD_ADD_PLAYER)
        n_sp = sum(1 for k, t, b in ev if k == "slave" and t == P.S_ADD_PLAYER)
        n_rb = tops.count(P.T_CMD_REBORN)
        if v in (10, 13):
            check(n_ap == 0 and n_sp == 0 and n_rb == 0 and P.S_BATTLE_START not in [t for k, t, b in ev if k == "slave"], "v%d sends no hero/spawn messages" % v)
        if v == 13:
            check(tops.count(P.T_CMD_SYNC) == 1, "v13 exactly one CmdSync")
        if v in (14, 15, 16, 17):
            check(n_ap == 1 and n_sp == 0 and n_rb == 0, "v%d exactly one top-level 0x4e22, no slave AddPlayer, no ReBorn" % v)
            check(tops.count(P.T_CMD_SYNC) == 0, "v%d never sends CmdSync" % v)
        if v == 18:
            check(n_ap == 1 and n_sp == 1 and n_rb == 0, "v18 one 0x4e22 + one slave AddPlayer, no ReBorn")
            check(tops.count(P.T_CMD_SYNC) == 0, "v18 never sends CmdSync")
        if v in (14, 15):
            check(P.S_BATTLE_START not in [t for k, t, b in ev if k == "slave"], "v%d no BattleStart" % v)
        if v >= 16:
            check([t for k, t, b in ev if k == "slave"].count(P.S_BATTLE_START) == 1, "v16+ exactly one in-frame BattleStart")
            cds = [P.read_varint(b, P.read_varint(b, 0)[1])[0:2] for k, t, b in ev if k == "top" and t == P.T_COUNTDOWN]
            check(len(cds) >= 7, "v16 extra top-level countdown messages (got %d)" % len(cds))
        if v in (15, 16, 17, 18):
            # client-side messages: 0x4e3e must be echoed verbatim (top-level), 0x2754 must not be echoed, no reply to MD5Check
            tx = P.StreamCrypt(); tx.apply(bytes(20 + 15))   # advance past the captured connect + info bytes (stream offset 35)
            s.sendall(tx.apply(P.frame(0x4E3E, bytes.fromhex("914e920301")) + P.frame(0x2754, bytes.fromhex("914ee819f80000")) + P.frame(P.T_MD5CHECK, bytes.fromhex("914e"))))
            time.sleep(0.5)
            buf2 = b""
            s.settimeout(0.3)
            end2 = time.time() + 0.8
            while time.time() < end2:
                try:
                    d = s.recv(65536)
                    if not d: break
                    buf2 += rx.apply(d)
                except socket.timeout:
                    pass
            got2, _ = P.split_frames(buf2)
            t2 = [(t, b) for t, b in got2 if t != P.T_FRAMEWORK and t != P.T_COUNTDOWN]
            if v == 17:
                check((0x4E3E, bytes.fromhex("914e920301")) not in t2, "v17 does NOT echo 0x4e3e")
            else:
                check((0x4E3E, bytes.fromhex("914e920301")) in t2, "v%d echoes 0x4e3e verbatim" % v)
            check(all(t not in (0x2754, P.T_MD5CHECK, P.T_CMD_SYNC) for t, b in t2), "v%d does not echo 0x2754 / reply MD5Check / CmdSync" % v)
        if v in (11, 12):
            ilc = [i for i, (k, t, b) in enumerate(ev) if k == "top" and t == P.T_LOADING_COMPLETE][0]
            icd = max(i for i, (k, t, b) in enumerate(ev) if k == "slave" and t == P.T_COUNTDOWN)
            ia = [i for i, (k, t, b) in enumerate(ev) if k == "top" and t == P.T_CMD_ADD_PLAYER]
            isp = [i for i, (k, t, b) in enumerate(ev) if k == "slave" and t == P.S_ADD_PLAYER]
            irb = [i for i, (k, t, b) in enumerate(ev) if k == "top" and t == P.T_CMD_REBORN]
            ibs = [i for i, (k, t, b) in enumerate(ev) if k == "slave" and t == P.S_BATTLE_START]
            check(len(ia) == len(isp) == len(irb) == len(ibs) == 1, "v%d one 0x4e22, slave AddPlayer, ReBorn, BattleStart" % v)
            if len(ia) == len(isp) == len(irb) == len(ibs) == 1:
                check(ilc < ia[0] and icd < isp[0], "v%d hero spawn only AFTER LoadingComplete + countdown" % v)
                check((ia[0] < isp[0]) == (v == 11), "v%d order: %s" % (v, "0x4e22 then slave AddPlayer" if v == 11 else "slave AddPlayer then 0x4e22"))
                check(max(ia[0], isp[0]) < irb[0] < ibs[0], "v%d ReBorn after both, BattleStart last" % v)
        s.close()
    finally:
        srv.kill(); srv.wait()

for _v in (10, 11, 12, 13, 14, 15, 16, 17, 18):
    run_variant_bisect(_v)
print("RESULT", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)

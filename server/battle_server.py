"""Fake battle (Sync master) server for the UE3 battle client.  TCP 127.0.0.1:7777, stdlib only.

What it does (details and confidence per message: notes/battle/sync_protocol.md (old section 10)):
  * decrypts + logs every client message (same keystream as battle_probe.py)
  * on MsgConnect(0x3e9): replies MsgConnectAck(0x3ea), then pings
  * starts a lockstep frame loop: MsgFramework(0x2715) every 50 ms with an advancing frame number
    (50 ms = default 'frame interval' field of the Sync.dll master config, 0x101f8058 = 0x32)
  * after the client info (0x3f4) arrives (or 1.5 s), injects the best-guess "loading finished" sequence:
    MsgCmdUserLoadingFinish, MsgCmdLoadingComplete, MsgCmdCountDownUpdate(1,2,3), both as the payload of a
    frame AND as top-level messages (we do not know which path the client really wants -> data for next run)
  * client requests (MsgReq*) cannot be turned into MsgCmd* (mapping unknown): only logged.

usage: battle_server.py [port] [--variant N] [--frame-ms N] [--name NAME] [--no-start] [--no-toplevel] [--no-inframe] [--no-spawn]
"""
import asyncio, datetime, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import battle_proto as P

args = sys.argv[1:]


def opt(flag, default=None, cast=str):
    if flag in args:
        i = args.index(flag)
        v = cast(args[i + 1])
        del args[i:i + 2]
        return v
    return default


def flag(f):
    if f in args:
        args.remove(f)
        return True
    return False


VARIANT = opt("--variant", 0, int)
VARIANT_DESC = {
    0: "step3: AddPlayer + BattleStart in frames",
    1: "msg7 Init, AddPlayer, BattleStart",
    2: "CmdSync(0,empty) top-level first, then AddPlayer + BattleStart",
    3: "CmdSync, Init, AddPlayer, 3x AddPerson troops, BattleStart",
    4: "same as 3 but 1 msg per 10 frames and BattleStart again after loading sequence (timing)",
    5: "UE3-side order: top-level MsgCmdAddPlayer(0x4e22) after CmdSync, then frames Init+slave AddPlayer+BattleStart, top-level MsgCmdReBorn(0x4e80), loading sequence",
    6: "like 5 but no slave AddPlayer (SyncClient may register it itself) and ReBorn sent 1 s after the loading sequence",
    7: "CORRECTED 5: DataSet N=132 with real health/team/gear, slave AddPlayer at a real map-17 nav point, ReBorn only AFTER the slave unit exists, then loading/BattleStart/countdown (1 s apart)",
    8: "7 + one squad of 3 foot soldiers (top-level 0x4e23 with owner=hero, then slave AddPerson kind=1 a=1)",
    9: "8 + one enemy bot (0x4e22 isSelf=0 camp 2, slave AddPlayer, ReBorn, then 0x4e4a ControlAiPlayer)",
    10: "BISECT baseline = EXACT 2026-11-04 behaviour (no CmdSync, no spawn; only loading sequence top-level + in frames). Known to pass the loading screen",
    11: "BISECT: 10, then 2.5 s AFTER the loading/countdown: top-level 0x4e22, frames Init+slave AddPlayer, ReBorn, BattleStart",
    12: "BISECT: like 11 but slave AddPlayer (frame) comes BEFORE the top-level 0x4e22",
    13: "BISECT: 10 + only the top-level CmdSync(0,empty) right after ConnectAck (tests CmdSync alone)",
    14: "BISECT: 10 + only the top-level 0x4e22 AddPlayer right after ConnectAck (tests early PlayerCtl alone; no spawn)",
    15: "14 (one hero via 0x4e22, spawns) + RELAY: echo client 0x4e3e MsgCmdPlayStateChange verbatim (top-level), decode+log 0x2754 MsgReqPlayerBodyturn (no Cmd counterpart found, not echoed), MD5Check no reply. Never CmdSync",
    16: "15 + UNFREEZE: slave BattleStart(8) in a frame at +3 s and countdown (2,2)(2,1)(2,0)(3,0) 1 s apart (value 0 = unfreeze script events, flag 0x20000 -> hero may move/attack)",
    17: "16 WITHOUT the 0x4e3e echo (hypothesis: echoing the client's own PlayStateChange re-applies state 402/26/... to the hero and locks walking). 0x2754 and every unknown Req only logged. Never CmdSync",
    18: "16 (with echo) + a Sync slave unit for the hero: frame Init(7) + slave AddPlayer(uid, kind 0, camp 1, pos 0,0,0 = DataSet pos) at +0.4 s, NO ReBorn (hypothesis: walking needs the Sync-side unit; may duplicate the hero). Never CmdSync",
    19: "18 + hero DataSet slots filled, on foot: [0x4e],[0x4f]=armytype skilltype1/2 (1021,1022), [0x4c] flagId 15710100, [0x56]=1, [0x4b]=100 (Energy). soldiers.txt MaxSpeed 5.09. Hypothesis: zero slots block ground walk. Never CmdSync",
    21: "19 + soldier id 112011 in the 4 config-id slots [0x3e,0x44,0x49,0x4a] AND in the first field of 0x4e22; slave AddPlayer kind=1 (valid agentparam key). Guess: client looks up speed by id. Never CmdSync",
    23: "21 + RELAY the client's movement Reqs as their Cmd counterparts (same body, top-level): 0x2738->0x4e50 MoveActionStart, 0x2739->0x4e51 MoveActionEnd, 0x2721->0x4eca GhostPosition. Hypothesis: lockstep wants the move confirmed. 0x2737 not relayed (no Cmd id known). Never CmdSync",
    24: "21 + hero DataSet direction slots [5,6,7] = (1,0,0) f32 (zero direction vector might zero ground velocity; air control still works). Never CmdSync",
    25: "24 base + ONE server move-release: after the countdown (+8 s) send Cmd 0x4e51 MoveActionEnd (uid, mode 1) and (uid, mode 2) = 'no move action active' in case the hero is stuck in a move state. Hero HP 200/max 200 already sent (DataSet[2],[3]); 0x4e22 'dying' field is 0. Never CmdSync",
    26: "24 base + after the countdown (+8 s) a full move cycle from the server: Cmd 0x4e50 MoveActionStart (uid, mode 1, velocity 0,0,0), 0.3 s later Cmd 0x4e51 End (uid, mode 1). Unlike V23 nothing is echoed. Never CmdSync",
    27: "24 base + at +8 s (hero exists) re-run BattleStart + countdown (3,0)(2,0)(3,0) 0.5 s apart. Guess from native analysis: state 3 clears a flag at the local controller +0x838 bit 4, state 2/0 sets GameEngine flag. Never CmdSync",
    28: "24 base + at +8 s BattleStart + countdown (1,0)(2,0)(3,0) 0.5 s apart (second guess: full prepare->tick->run cycle after the hero exists)",
    30: "V28 + hero spawned at a VALID navmesh point of the map (TK_MAPID, default 17: x=9.3 y=4.5 z=-1.0 m) in slave AddPlayer AND DataSet pos slots [9],[10]",
    31: "V30 but ONLY the slave AddPlayer position is moved (DataSet untouched)",
    32: "V30 but spawned 3 m higher (falls onto the ground; in case the pawn started inside the floor)",
    33: "V30 + at +10 s the SERVER starts the hero walking: Cmd 0x4e50 MoveActionStart (uid, mode 1, velocity (4.5,0,0) m/s) re-sent every 500 ms for 10 s, then 0x4e51 End. Frames (0x2715, 50 ms) were ALWAYS sent, so no extra frame msg",
    34: "V30 + at +10 s a GhostPosition stream: Cmd 0x4eca (uid, x,y,z) every 50 ms, x advancing 4.5 m/s from the spawn point for 10 s (server drives the position)",
    35: "V30 + 33 and 34 together (MoveActionStart velocity + GhostPosition stream), 15 s long",
    36: "V30 + at +10 s IN-FRAME slave msg 200 (WalkerSlave seek/move-to; layout from Sync.dll deserializer 0x1003c9c0: uid, 5 x f16 (target x,y,z,0,0), bool 1, f16 speed 4.5, f16 0.5) toward spawn+30 m on x, re-sent every 2 s for 10 s. RISK: if the hero unit is not a WalkerSlave the DLL may crash",
    37: "V30 + hero DataSet float slots [0x26],[0x27] = 1.0 (raw f32). Static (Win64 exe 0x140aee73f/0x140aee765): the local controller fPersonToHorseMaxSpeedFactor(+0x7A4)/fPersonToSelfMaxSpeedFactor(+0x7A8) = max(DataSet float [0x27]/[0x26], 1e-4); unset = 1e-4 = hero creeps. UNTESTED",
    38: "V37 (the WORKING WALK BASE) + SERVER ECHO of the hero's own position: every client MsgReqPosition 0x2737 (uid, f32 x,y,z metres, y=up) is answered with top-level Cmd 0x4eca GhostPosition (uid, f16 x,y,z, SAME axis order). Hypothesis: the client pulls the pawn back to its stale sync-side position (start point) once it is >~10 m away; 0x4eca feeds that position. NOT echoed: 0x2721 (its y is always 0 = velocity-like, echoing it as a position in V23 put the hero at y=0 and broke jump), 0x2738/0x2739 (move actions). Also logs 0x273e/0x2778 (sprint attempts)",
    39: "V38 but the echoed 0x4eca body uses swapped axes (x, z, y) in case the client expects UE order (z up) instead of sync order (y up). Test only if V38 changes nothing",
    44: "V37 + OWN TROOPS only: at +12 s 3x top-level 0x4e23 (owner = hero, camp 1) then 0.3 s later slave msg 3 AddPerson (kind 1, a 1) 2-4 m from the hero spawn (DataSet pos slots set). Suggested map 3. UNTESTED",
    45: "V44 + at +16 s ONE enemy hero (uid 30001, camp 0): 0x4e22 isSelf=0, slave AddPlayer, 0x4e80 ReBorn, 0x4e4a ControlAiPlayer, 15 m from the hero. No battle end. UNTESTED",
    47: "V44 + (a) slave AddPlayer pos = map spawn (V37 sent 0,0,0 so on map 3 the hero landed at 325,326 = top-right) (b) hero gear/weapons from player.json suit 0 (TK_SUIT). Troops at +12 s. UNTESTED",
    48: "V47 + hero face bytes in the top-level AddPlayer (player.json faces56) + DataSet 0x4c = banner item type. UNTESTED (face format is a guess)",
    49: "V47 + ONE enemy AI general (uid 30001, camp 0, same code as V45) at +22 s (10 s after the hero really exists), 20 m in front of the hero (+x; env TK_ENEMY_DIST). Isolates: does a visible enemy make the game 'really started' (troops/combo)? UNTESTED",
    50: "V47 + server replies to action Reqs: 0x2774 ContinusCutNew -> Cmd 0x4ed5 (req body + 3xf16 0 + uvar 0), 0x273e Assault -> Cmd 0x4e55 DoAssault (uid, 1, 0). Opt-in extras env TK_V50_EXTRA=block,swing,weapon. Field values are guesses, wire layouts decoded from SyncClient. UNTESTED",
    51: "V49 + V50 (enemy general + action replies). UNTESTED",
    52: "V51 + army id from the lobby hand-off (last_prebattle.json armyid, 2-star default 112014) in hero/troop/enemy soldier-type slots instead of hard-coded 112011; hero slots [0x44],[0x49],[0x4a] zeroed (suspects for the scoreboard total 112011); enemy gets speed slots 0x26/0x27 = 1.0. UNTESTED",
    46: "V45 + at +20 s three ENEMY troops (uids 30101-3, owner = enemy hero, camp 0) next to the enemy hero. No battle end. UNTESTED",
    43: "V37 (identical walk base) + answers client MsgReqTutorialStep 0x2750 (uvar uid, step) with top-level Cmd 0x4e93 CmdSyncTutorialStage (uvar uid, uvar step; SyncClient codec 0x10074140, handler 0x100b3740 only acts in tutorial mode 0xb, else logs 'Not Tutorial Mode'). Hypothesis: the training-ground NPC/challenge/tutorial flow waits for this server confirm. UNTESTED",
    41: "V37 + IN-FRAME relay (0x2715 frame payload) of every client position report 0x2737 (uid, f32 x,y,z) as Sync.dll slave msg 401 (0x191, same layout; dispatcher 0x100348c0 -> WalkerSlave 0x1005ace0). Hypothesis: the real master feeds the client position back to the sync unit so the pawn SmoothLocation target moves with the hero (fixes the ~10 m pull-back). No top-level Cmd sent",
    42: "V41 + also relay 0x2738 MoveActionStart as slave msg 402 and 0x2739 MoveActionEnd as slave msg 403 in-frame (same layouts). Try only if V41 changes nothing",
    29: "24 base + at +5 s own troops (3x 0x4e23 + slave msg 3, owner = hero) and ONE AI enemy hero (uid 30001, camp 0: 0x4e22 isSelf=0, slave AddPlayer, 0x4e80, then 0x4e4a ControlAiPlayer), verbose logging; +150 s MsgCmdMatchEnd(1) to test the win screen. Never CmdSync",
    22: "19 + after the 0x4e3e echo, a second 0x4e3e (state 402, flag 0) 400 ms later, in case 402 = 'rooted/locked' state. Never CmdSync",
    20: "19 but MOUNTED: cavalry armytype 111025 gear, horse 16000005 in [0x22], horse armor 15910105 in [0x23], [0x4d]=1, skills 1111/1112/1113. Never CmdSync",
}
if VARIANT not in VARIANT_DESC:
    print("unknown --variant %d (valid: %s)" % (VARIANT, sorted(VARIANT_DESC)))
    sys.exit(2)
NEWVAR = VARIANT                # 44/45/46 = V37 base + troops / enemy / enemy troops
TROOPS_ON = NEWVAR in (44, 45, 46, 47, 48, 49, 50, 51, 52)
V47 = NEWVAR in (47, 48, 49, 50, 51, 52)       # spawn pos in slave AddPlayer + owner gear from player.json
V48 = NEWVAR == 48            # + face bytes
ENEMY_ON = NEWVAR in (45, 46, 49, 51, 52)
V49 = NEWVAR in (49, 51, 52)       # enemy general later (+22 s) and 20 m away
V50 = NEWVAR in (50, 51, 52)
V52 = NEWVAR == 52            # army id from lobby hand-off; scoreboard-total suspects zeroed       # server replies to action Reqs (combo, sprint; opt-in extras)
V50_EXTRA = set(x.strip() for x in os.environ.get("TK_V50_EXTRA", "").split(",") if x.strip())
ETROOPS_ON = NEWVAR == 46
TUT = (VARIANT == 43)          # V43 = V37 behaviour + tutorial-step reply
if TUT or TROOPS_ON:
    VARIANT = 37
def _v50_table():
    """Req -> (Cmd id, body, note). Layouts decoded from SyncClient.dll writers (notes/reports/20261108_HHMM_v47_followup.md); values marked 'guess' are unverified."""
    z3 = P.f16(0.0) * 3
    t = {
        0x2774: lambda b: (0x4ED5, b + z3 + P.varint(0), "ContinusCutNew: uid,u8 stage,u8 dir (copied) + f16x3 0 + uvar 0 [guess]"),
        0x273E: lambda b: (0x4E55, b + P.varint(1) + P.varint(0), "DoAssault: uid,u8 1,uvar 0 [guess]"),
    }
    if "block" in V50_EXTRA:
        t[0x2735] = lambda b: (0x4E2F, b, "Block: identical layout (shared writer 0x1004f220)")
        t[0x2736] = lambda b: (0x4E30, b, "BlockCancel: identical layout (uid only)")
    if "swing" in V50_EXTRA:
        t[0x272F] = lambda b: (0x4E27, b + P.varint(0), "MeleeHewUp: req body + uvar 0 [guess]")
    if "weapon" in V50_EXTRA:
        t[0x272D] = lambda b: (0x4E25, b + P.varint(0), "ChangeWeapon: req body (uid,A,B) + uvar 0 [pure guess]")
    return t


V50_REPLY = _v50_table() if V50 else {}
V23_RELAY = {0x2738: 0x4E50, 0x2739: 0x4E51, 0x2721: 0x4ECA}
FRAME_MS = opt("--frame-ms", 50, int)
PLAYER_NAME = opt("--name", "tiger")
NO_START = flag("--no-start")
NO_TOP = flag("--no-toplevel")
NO_FRAME = flag("--no-inframe")
NO_SPAWN = flag("--no-spawn")
PORT = int(args[0]) if args else 7777
HOST = "127.0.0.1"
LOGDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOGDIR, exist_ok=True)
LOGFILE = os.path.join(LOGDIR, "battleserver_%s.log" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))


def log(msg):
    line = "%s %s" % (datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], msg)
    try:
        print(line, flush=True)
    except Exception:
        pass
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class Conn:
    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.rx, self.tx = P.StreamCrypt(), P.StreamCrypt()
        self.peer = writer.get_extra_info("peername")
        self.player_id = 10001
        self.frame_no = 0
        self.pending = []          # inner messages for the next frame payload
        self.started = False
        self.closed = False
        self.quiet_frames = 0

    def send(self, data, why):
        """Encrypt + write; every non-frame send is logged in full."""
        plain = data
        self.writer.write(self.tx.apply(data))
        if why:
            off = 0
            while off < len(plain):
                ln, typ = int.from_bytes(plain[off:off + 2], "little"), int.from_bytes(plain[off + 2:off + 4], "little")
                log("SEND %s: %s" % (why, P.describe(typ, plain[off + 4:off + ln])))
                off += ln

    # ---- variants 7-9 (notes/battle/variants_7_9_recheck.md) -----------------------------------------------------
    HERO_POS = (-2.7, 4.4, 2.3)      # dense nav-mesh point of map 17 (PK_CL_Yanwuchang_005_Nav.terrain), y = up
    BOT_UID = 30001
    TROOP_UIDS = (20001, 20002, 20003)

    def at(self, ms, fn):
        asyncio.get_event_loop().call_later(ms / 1000.0, lambda: (not self.closed) and fn())

    def army_id(self):
        """V52: troop type = lobby choice (last_prebattle.json armyid, kept in the lobby's listed 2-star stage), env TK_ARMY overrides, default 112014 (Lv5, 2-star)."""
        if not V52:
            return 112011
        try:
            return int(os.environ["TK_ARMY"])
        except (KeyError, ValueError):
            pass
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "last_prebattle.json"), encoding="utf-8") as f:
                a = int(json.load(f).get("armyid") or 0)
            if a:
                return a
        except Exception:
            pass
        return 112014

    def hero_hp(self):
        """V47+: player start life from unit_default.ini [player] nLifeMale=300 / nLifeFemale=280 (sex from player.json; env TK_HP overrides). Older variants keep 200."""
        if not V47:
            return 200
        try:
            return int(os.environ["TK_HP"])
        except (KeyError, ValueError):
            pass
        try:
            import json as _j
            sex = _j.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "player.json"), encoding="utf-8")).get("sex", 0)
            return 280 if int(sex) == 1 else 300
        except Exception:
            return 300

    def hero_gear(self):
        """DataSet extras for the hero: V19/V20 fill the mobility-like slots (notes/battle_state.md 8c)."""
        if VARIANT in (19, 22):
            return P.GEAR_FOOT_FULL
        if VARIANT in (30, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42):      # DataSet pos slots [9],[10] = spawn x,z as raw f32 (ReBorn dispatcher 0x100b4ec0) + slave pos
            sx, _sy, sz = self.spawn_pos()
            g = dict(P.GEAR_FOOT_DIR)
            g[9], g[10] = P.f32bits(sx), P.f32bits(sz)
            if VARIANT in (37, 38, 39, 41, 42):
                g[0x26], g[0x27] = P.f32bits(1.0), P.f32bits(1.0)   # person-to-self / person-to-horse max speed factor
            if V47:
                g.update(self.owner_gear())
            if V52:
                army = self.army_id()
                for k in (0x3E,):
                    g[k] = army
                for k in (0x44, 0x49, 0x4A):          # were 112011 (V21 guess); scoreboard showed total troops = 112011
                    g[k] = 0
                log("V52 HERO army=%d in [0x3e]; [0x44],[0x49],[0x4a]=0" % army)
            return g
        if VARIANT in (24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42):
            return P.GEAR_FOOT_DIR
        if VARIANT in (21, 23):
            return P.GEAR_FOOT_IDS
        if VARIANT == 20:
            return P.GEAR_MOUNTED_FULL
        return P.GEAR_112011

    def owner_gear(self):
        """V47: DataSet equipment slots from player.json suits[TK_SUIT|0]: suit pos -> bag item id -> items[].type (= armor/meleeweapon/rangedweapon.txt id).
        0x18 helmet(pos1) 0x19 shawl(4) 0x1a armor(2) 0x1b shoes(3); 0x1e..0x21 weapon1..4 (pos 6..9). Horse/saddle left out (on foot)."""
        out = {}
        try:
            pj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "player.json")
            with open(pj, encoding="utf-8") as f:
                d = json.load(f)
            suit = None
            try:    # lobby hand-off (written when Ready is pressed): the suit slot the owner actually chose
                with open(os.path.join(os.path.dirname(pj), "last_prebattle.json"), encoding="utf-8") as f2:
                    suit = json.load(f2).get("suit_row") or None
            except Exception:
                suit = None
            if not suit:
                suit = d["suits"][int(os.environ.get("TK_SUIT", "") or 0)]
            tmap = {str(it.get("id")): int(it.get("type", 0)) for it in d.get("items", [])}
            for slot, pos in ((0x18, 1), (0x19, 4), (0x1A, 2), (0x1B, 3), (0x1E, 6), (0x1F, 7), (0x20, 8), (0x21, 9)):
                t = tmap.get(str(suit.get(str(pos), "")), 0)
                if t:
                    out[slot] = t
            if V48:
                bt = tmap.get(str(suit.get("15", "")), 0)      # banner
                if bt:
                    out[0x4C] = bt
            log("V47 GEAR from player.json suit: %s" % {hex(k): v for k, v in out.items()})
        except Exception as e:
            log("V47 GEAR: failed to read player.json (%r), keeping defaults" % (e,))
        return out

    def face_bytes(self):
        """V48 (guess): 56 face sliders as one byte each (player.json faces56 / created_role_req.faces 0..100)."""
        try:
            pj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "player.json")
            with open(pj, encoding="utf-8") as f:
                d = json.load(f)
            return bytes(max(0, min(255, int(x))) for x in d["faces56"])
        except Exception as e:
            log("V48 FACE: failed (%r)" % (e,))
            return b""

    # V30-32: valid spawn per map, sync metres (x, y=up, z). 17/21: centre of a navmesh quad / vertex of Nav.terrain; 3/11: mapindex Camp1Pos.
    SPAWN_BY_MAP = {17: (9.3, 4.5, -1.0), 21: (14.6, 8.2, 135.0), 3: (-404.78, 46.6, -121.19), 11: (308.1, 35.8, -106.9)}

    def spawn_pos(self):
        try:
            mid = int(os.environ.get("TK_MAPID", "") or 17)
        except ValueError:
            mid = 17
        x, y, z = self.SPAWN_BY_MAP.get(mid, self.SPAWN_BY_MAP[17])
        ov = os.environ.get("TK_SPAWN", "").strip()          # test override "x,y,z" (sync metres)
        if ov:
            try:
                x, y, z = [float(v) for v in ov.split(",")]
            except ValueError:
                pass
        return (x, y + (3.0 if VARIANT == 32 else 0.0), z)

    def v7_connect(self):
        """right after ConnectAck: create the PlayerCtl objects (top-level 0x4e22) BEFORE any slave unit exists."""
        self.send(P.msg_cmd_add_player_v2(self.player_id, PLAYER_NAME, True, camp=1, ds_extra=self.hero_gear(), hp=self.hero_hp(), face=(self.face_bytes() if V48 else b""), a=(self.army_id() if VARIANT in (21, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42) else 0)), "add_player(hero, top-level)")
        if VARIANT == 9:
            self.send(P.msg_cmd_add_player_v2(self.BOT_UID, "bot1", False, camp=2, ds_extra=P.GEAR_112011), "add_player(bot, top-level)")

    def start_sequence_v7(self):
        """Timeline (ms after the client info arrives).  Each slave message goes into its own 50 ms frame.
        0: Init(7) | 50: slave AddPlayer hero (+ bot) | ~400: ReBorn hero (+bot) [unit exists now] | ~700: troops |
        ~1000: UserLoadingFinish + LoadingComplete | ~1200: BattleStart(8) | ~1300: AI control | countdown 1 s apart"""
        pid = self.player_id
        hx, hy, hz = self.HERO_POS
        log("START SEQUENCE v%d (corrected order): hero uid=%d pos=%s name=%r" % (VARIANT, pid, self.HERO_POS, PLAYER_NAME))
        self.pending.append(P.msg_slave_init())
        self.pending.append(P.msg_add_player(pid, kind=0, f10=1, pos=self.HERO_POS))
        if VARIANT == 9:
            self.pending.append(P.msg_add_player(self.BOT_UID, kind=0, f10=2, pos=(hx + 12.0, hy, hz)))
        rb_ds = self.hero_gear() if VARIANT in (37, 38, 39, 41, 42) else P.GEAR_112011      # V37: ReBorn builds a fresh PlayerCtl DataSet (SyncClient 0x100ee480), so 0x26/0x27 must be in it too
        self.at(450, lambda: self.send(P.msg_cmd_reborn_v2(pid, PLAYER_NAME, camp=1, ds_extra=rb_ds, hp=self.hero_hp()), "reborn(hero, after unit exists)"))
        if VARIANT == 9:
            self.at(550, lambda: self.send(P.msg_cmd_reborn_v2(self.BOT_UID, "bot1", camp=2, ds_extra=P.GEAR_112011), "reborn(bot)"))
        if VARIANT in (8, 9):
            def troops():
                for i, u in enumerate(self.TROOP_UIDS):
                    self.send(P.msg_cmd_add_creature(u, pid, camp=1, soldier_class=1, ds_extra=P.GEAR_112011), "add_creature(troop %d, top-level)" % u)
                for i, u in enumerate(self.TROOP_UIDS):
                    # slave Person (msg 2 in this repo's numbering = layout of AddPerson; see notes research_troops sec.0 for the swap):
                    # soldiers are Persons -> slave msg 3.  kind=1 (agentparam.txt: 1 = soldier), a=1.
                    self.pending.append(P.msg_add_person(u, kind=1, f10=1, pos=(hx + 2.0 * (i + 1), hy, hz + 2.0), a=1, mtype=3))
            self.at(800, troops)
        def loaded():
            self.send(P.msg_user_loading_finish([PLAYER_NAME], f1=0), "start(top-level)")
            self.send(P.msg_loading_complete(0), "start(top-level)")
        self.at(1300, loaded)
        self.at(1500, lambda: self.pending.append(P.msg_battle_start()))
        if VARIANT == 9:
            self.at(1700, lambda: self.send(P.msg_control_ai_player(self.BOT_UID), "control_ai_player(bot)"))
        # Countdown per Kingdom exe 0xebfb00: state 1 = prepare (freeze, timer UI); state 2 = tick, value = seconds left, and
        # (2,0) fires the "unfreeze" script events + sets GameEngine flag 0x20000 + vtable+0x6c4; state 3 = running.
        for k, (st, val) in enumerate([(1, 3), (2, 3), (2, 2), (2, 1), (2, 0), (3, 0)]):
            self.at(2000 + 1000 * k, lambda st=st, val=val: self.send(P.msg_countdown(st, val), "countdown"))
        self.at(7100, lambda: self.pending.append(P.msg_battle_start()))   # unfreeze events once more after the countdown ended

    def start_sequence_bisect(self, msgs, cds):
        """variants 10-14: byte-for-byte the 2026-11-04 loading sequence (top-level + in-frame, same timing), then optionally a late hero spawn."""
        log("START SEQUENCE (bisect v%d = 11-04 baseline): name=%r" % (VARIANT, PLAYER_NAME))
        for m in msgs + cds:
            self.send(m, "start(top-level)")
        self.pending.append(b"".join(msgs))
        for m in cds:
            self.pending.append(m)
        if VARIANT in (11, 12):
            self.at(2500, self.late_spawn)
        if VARIANT in (18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42):
            self.at(400, lambda: (self.pending.append(P.msg_slave_init()), self.pending.append(P.msg_add_player(self.player_id, kind=(1 if VARIANT in (21, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42) else 0), f10=1, pos=(self.spawn_pos() if (VARIANT in (30, 31, 32, 33, 34, 35, 36) or V47) else (0.0, 0.0, 0.0))))))
        if VARIANT in (25, 26):
            self.at(8000, self.v25_move_cmds)
        if VARIANT in (27, 28, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42):
            self.at(8000, self.v27_recountdown)
        if VARIANT in (33, 34, 35, 36):
            self.at(10000, self.v33_walk)
        if TROOPS_ON:
            self.at(12000, self.v44_troops)
        if ENEMY_ON:
            self.at(22000 if V49 else 16000, self.v45_enemy)
        if ETROOPS_ON:
            self.at(20000, self.v46_enemy_troops)
        if VARIANT == 29:
            self.at(5000, self.v29_troops)
            self.at(6000, self.v29_enemy)
            self.at(150000, self.v29_end)
        if VARIANT in (16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42):
            self.at(3000, lambda: self.pending.append(P.msg_battle_start()))
            for k, (st, val) in enumerate([(2, 2), (2, 1), (2, 0), (3, 0)]):
                self.at(3200 + 1000 * k, lambda st=st, val=val: self.send(P.msg_countdown(st, val), "countdown(unfreeze)"))

    def _squad(self, tag, uids, owner, camp, base, ds_base):
        """shared by V44/V46: top-level 0x4e23 per soldier, 0.3 s later slave AddPerson (kind 1, a 1) near base (sync metres, y up)."""
        bx, by, bz = base
        ex0 = dict(P.GEAR_112011)
        ex0.update({0x3F: self.army_id(), 0x43: self.army_id(), 0x47: self.army_id()})
        poss = {u: (bx + 2.0 * (i + 1), by, bz + 2.0) for i, u in enumerate(uids)}
        log("%s TROOPS: uids=%s owner=%d camp=%d base=%s" % (tag, list(uids), owner, camp, base))
        for u in uids:
            ex = dict(ex0)
            ex[9], ex[10] = P.f32bits(poss[u][0]), P.f32bits(poss[u][2])
            self.send(P.msg_cmd_add_creature(u, owner, camp=camp, soldier_class=1, ds_extra=ex), "%s add_creature(%d)" % (tag, u))
        def units():
            for u in uids:
                self.pending.append(P.msg_add_person(u, kind=1, f10=camp, pos=poss[u], a=1, mtype=3))
            log("%s TROOPS: slave AddPerson queued" % tag)
        self.at(300, units)

    def v44_troops(self):
        sx, sy, sz = self.spawn_pos()
        self._squad("V44", self.TROOP_UIDS, self.player_id, 1, (sx, sy, sz), None)

    def v45_enemy(self):
        sx, sy, sz = self.spawn_pos()
        b = self.BOT_UID
        d = 15.0
        if V49:
            try:
                d = float(os.environ.get("TK_ENEMY_DIST", "20"))
            except ValueError:
                d = 20.0
        ex = dict(P.GEAR_FOOT_DIR)
        ex[9], ex[10] = P.f32bits(sx + d), P.f32bits(sz)
        if V52:
            ex[0x3E] = self.army_id()
            ex[0x44] = ex[0x49] = ex[0x4A] = 0
            ex[0x26] = ex[0x27] = P.f32bits(1.0)
        log("V45 ENEMY: uid=%d camp=0 at (%.1f,%.1f,%.1f)" % (b, sx + d, sy, sz))
        self.send(P.msg_cmd_add_player_v2(b, "enemy1", False, camp=0, ds_extra=ex, a=self.army_id()), "v45 add_player(enemy, top-level)")
        self.at(300, lambda: self.pending.append(P.msg_add_player(b, kind=1, f10=0, pos=(sx + d, sy, sz))))
        self.at(800, lambda: self.send(P.msg_cmd_reborn_v2(b, "enemy1", camp=0, ds_extra=ex), "v45 reborn(enemy)"))
        self.at(1500, lambda: self.send(P.msg_control_ai_player(b), "v45 control_ai_player(enemy)"))

    def v46_enemy_troops(self):
        sx, sy, sz = self.spawn_pos()
        self._squad("V46", (30101, 30102, 30103), self.BOT_UID, 0, (sx + 15.0, sy, sz + 3.0), None)

    def v29_troops(self):
        """V29 step 1: own squad.  Top-level 0x4e23 first (creates SoldierCtl; owner [0x32]/[0x35] = hero uid), 0.3 s later slave msg 3 AddPerson (kind=1, a=1).
        Guess: soldier-id slots [0x3f],[0x43],[0x47] = 112011 (OnSyncSpawnAI takes a SoldierID, SoldiersManager.GetSoldierInfoBySoldierID)."""
        pid = self.player_id
        ex = dict(P.GEAR_112011)
        ex.update({0x3F: 112011, 0x43: 112011, 0x47: 112011})
        log("V29 TROOPS: adding %s owner=%d camp=1" % (self.TROOP_UIDS, pid))
        for u in self.TROOP_UIDS:
            self.send(P.msg_cmd_add_creature(u, pid, camp=1, soldier_class=1, ds_extra=ex), "v29 add_creature(troop %d)" % u)
        def units():
            for i, u in enumerate(self.TROOP_UIDS):
                self.pending.append(P.msg_add_person(u, kind=1, f10=1, pos=(2.0 * (i + 1), 0.0, 2.0), a=1, mtype=3))
            log("V29 TROOPS: slave AddPerson queued")
        self.at(300, units)

    def v29_enemy(self):
        """V29 step 2: one AI enemy hero.  KingdomSyncGame.PostBeginPlay creates teams 0, 1, 255 only, so enemy camp = 0 (hero = 1).
        Order as for the hero: 0x4e22 isSelf=0 -> slave AddPlayer -> 0x4e80 ReBorn -> 0x4e4a ControlAiPlayer (handler needs a PlayerCtl)."""
        b = self.BOT_UID
        log("V29 ENEMY: uid=%d camp=0 (AI hero)" % b)
        self.send(P.msg_cmd_add_player_v2(b, "enemy1", False, camp=0, ds_extra=P.GEAR_FOOT_DIR, a=112011), "v29 add_player(enemy, top-level)")
        self.at(300, lambda: self.pending.append(P.msg_add_player(b, kind=1, f10=0, pos=(12.0, 0.0, 0.0))))
        self.at(800, lambda: self.send(P.msg_cmd_reborn_v2(b, "enemy1", camp=0, ds_extra=P.GEAR_FOOT_DIR), "v29 reborn(enemy)"))
        self.at(1500, lambda: self.send(P.msg_control_ai_player(b), "v29 control_ai_player(enemy)"))

    def v29_end(self):
        """V29 step 3 (guess): MsgCmdMatchEnd 0x4e73 varint 1 -> presumably script OnSyncEndGame(1) (win); plus slave BattleEnd."""
        log("V29 END: MatchEnd(1) + slave BattleEnd")
        self.send(P.frame(0x4E73, P.varint(1)), "v29 MatchEnd(win)")
        self.pending.append(P.frame(9, b""))

    def v27_recountdown(self):
        """V27/28 (notes/battle/walk_gate_v27_mod.md): re-run the countdown AFTER the hero exists (state 3 clears bit 4 of a local-controller flag at +0x838, state 2/0 sets engine flag 0x20000)."""
        seq = [(3, 0), (2, 0), (3, 0)] if VARIANT == 27 else [(1, 0), (2, 0), (3, 0)]
        self.pending.append(P.msg_battle_start())
        for k, (st, val) in enumerate(seq):
            self.at(500 * k, lambda st=st, val=val: self.send(P.msg_countdown(st, val), "v%d re-countdown(%d,%d)" % (VARIANT, st, val)))

    def v33_walk(self):
        """V33-35: the server drives the hero (hypothesis: pawn Location follows the Sync unit / server Cmds, local velocity is overwritten).
        Velocity units: f16 metres/s (jump = (0,6,0) seen in real ReqMoveActionStart), position f16 sync metres, y = up."""
        pid = self.player_id
        x0, y0, z0 = self.spawn_pos()
        spd = 4.5
        secs = 15 if VARIANT == 35 else 10
        log("V%d WALK: uid=%d from (%.2f,%.2f,%.2f) speed %.1f m/s along +x for %d s" % (VARIANT, pid, x0, y0, z0, spd, secs))
        if VARIANT == 36:
            for k in range(5):
                def seek(k=k):
                    body = P.varint(pid) + b"".join(P.f16(v) for v in (x0 + 30.0, y0, z0, 0.0, 0.0)) + b"" + P.f16(spd) + P.f16(0.5)
                    m = P.frame(200, body)
                    log("V36 slave msg 200 (WalkerSeek) queued: %s" % m.hex(" "))
                    self.pending.append(m)
                self.at(2000 * k, seek)
        if VARIANT in (33, 35):
            for k in range(secs * 2):
                self.at(500 * k, lambda: self.send(P.frame(0x4E50, P.varint(pid) + P.varint(1) + P.f16(spd) + P.f16(0.0) + P.f16(0.0)), "v%d Cmd MoveActionStart mode 1 vel (%.1f,0,0)" % (VARIANT, spd)))
            self.at(500 * secs * 2, lambda: self.send(P.frame(0x4E51, P.varint(pid) + P.varint(1)), "v%d Cmd MoveActionEnd" % VARIANT))
        if VARIANT in (34, 35):
            n = secs * 20
            for k in range(n):
                def gp(k=k):
                    x = x0 + spd * 0.05 * (k + 1)
                    self.send(P.frame(0x4ECA, P.varint(pid) + P.f16(x) + P.f16(y0) + P.f16(z0)), "v%d Cmd GhostPosition x=%.2f" % (VARIANT, x) if k % 10 == 0 else None)
                self.at(50 * k, gp)

    def v25_move_cmds(self):
        pid = self.player_id
        if VARIANT == 25:
            for mode in (1, 2):
                self.send(P.frame(0x4E51, P.varint(pid) + P.varint(mode)), "v25 Cmd MoveActionEnd mode %d" % mode)
        elif VARIANT == 26:
            self.send(P.frame(0x4E50, P.varint(pid) + P.varint(1) + P.f16(0.0) + P.f16(0.0) + P.f16(0.0)), "v26 Cmd MoveActionStart mode 1 vel 0")
            self.at(300, lambda: self.send(P.frame(0x4E51, P.varint(pid) + P.varint(1)), "v26 Cmd MoveActionEnd mode 1"))

    def late_spawn(self):
        """hero spawn AFTER the loading screen is done (11: PlayerCtl first; 12: slave unit first)."""
        pid = self.player_id
        log("LATE SPAWN v%d: hero uid=%d" % (VARIANT, pid))
        ap = lambda: self.send(P.msg_cmd_add_player_v2(pid, PLAYER_NAME, True, camp=1, ds_extra=P.GEAR_112011), "add_player(hero, top-level, late)")
        self.pending.append(P.msg_slave_init())
        if VARIANT == 11:
            ap()
            self.pending.append(P.msg_add_player(pid, kind=0, f10=1, pos=self.HERO_POS))
            rb_at = 450
        else:
            self.pending.append(P.msg_add_player(pid, kind=0, f10=1, pos=self.HERO_POS))
            self.at(300, ap)
            rb_at = 750
        self.at(rb_at, lambda: self.send(P.msg_cmd_reborn_v2(pid, PLAYER_NAME, camp=1, ds_extra=P.GEAR_112011), "reborn(hero, late)"))
        self.at(rb_at + 500, lambda: self.pending.append(P.msg_battle_start()))

    def start_sequence(self):
        if self.started or NO_START:
            return
        self.started = True
        if VARIANT in (7, 8, 9):
            return self.start_sequence_v7()
        msgs = [P.msg_user_loading_finish([PLAYER_NAME], f1=0), P.msg_loading_complete(0)]
        cds = [P.msg_countdown(1, 3), P.msg_countdown(2, 3), P.msg_countdown(3, 0)]
        log("START SEQUENCE: inframe=%s toplevel=%s name=%r" % (not NO_FRAME, not NO_TOP, PLAYER_NAME))
        if VARIANT >= 10:
            return self.start_sequence_bisect(msgs, cds)
        if not NO_SPAWN:
            # Sync.dll slave messages (frame payload only), layouts from Sync.dll readers (notes/battle/sync_protocol.md).
            seq = []
            if VARIANT in (1, 3, 4, 5, 6):
                seq.append(P.msg_slave_init())
            if VARIANT != 6:
                seq.append(P.msg_add_player(self.player_id, pos=(0.0, 0.0, 0.0)))
            if VARIANT in (3, 4):
                for i in range(3):
                    seq.append(P.msg_add_person(20001 + i, pos=(2.0 * (i + 1), 0.0, 0.0)))
            seq.append(P.msg_battle_start())
            for m in seq:
                log("SPAWN SEQUENCE v%d: %s" % (VARIANT, P.describe(int.from_bytes(m[2:4], "little"), m[4:])))
            for m in seq:
                self.pending.append(m)
                if VARIANT == 4:
                    self.pending.extend([b""] * 9)
        if VARIANT == 5 and not NO_SPAWN:
            self.send(P.msg_cmd_reborn(self.player_id, PLAYER_NAME), "reborn(top-level)")
        if not NO_TOP:
            for m in msgs + cds:
                self.send(m, "start(top-level)")
        if VARIANT == 6 and not NO_SPAWN:
            asyncio.get_event_loop().call_later(1.0, lambda: self.send(P.msg_cmd_reborn(self.player_id, PLAYER_NAME), "reborn(top-level, late)"))
        if not NO_FRAME:
            # spread over the next frames so each frame carries one logical step
            self.pending.append(b"".join(msgs))
            for m in cds:
                self.pending.append(m)
            if VARIANT == 4 and not NO_SPAWN:
                self.pending.append(P.msg_battle_start())

    async def frame_loop(self):
        t0 = time.monotonic()
        n = 0
        try:
            while not self.closed:
                n += 1
                await asyncio.sleep(max(0.0, t0 + n * FRAME_MS / 1000.0 - time.monotonic()))
                if self.closed:
                    break
                self.frame_no += 1
                payload = self.pending.pop(0) if self.pending else b""
                data = P.msg_framework(self.frame_no, payload)
                verbose = payload or self.frame_no <= 5
                self.send(data, "frame" if verbose else None)
                if not verbose and self.frame_no % 100 == 0:
                    log("... sent frame %d (empty frames not logged individually)" % self.frame_no)
                if self.frame_no % 100 == 0:
                    await self.writer.drain()
                if self.frame_no == 100:
                    self.send(P.msg_ping(int(time.monotonic() * 1000) & 0x7FFFFFFF, 1), "ping")
        except (ConnectionError, asyncio.CancelledError):
            pass
        except Exception as e:
            log("frame loop error: %r" % (e,))

    def on_message(self, typ, body):
        try:
            desc = P.describe(typ, body)
        except Exception as e:
            desc = "type_0x%x body=%s (describe failed: %r)" % (typ, body.hex(" "), e)
        log("RECV%s %s" % (" [after spawn]" if self.started else "", desc))
        if typ == P.T_CONNECT:
            if len(body) == 16:
                import struct
                self.player_id = struct.unpack("<4I", body)[1]
            self.send(P.msg_connect_ack(0), "reply")
            self.send(P.msg_ping(int(time.monotonic() * 1000) & 0x7FFFFFFF, 0), "ping")
            if 2 <= VARIANT <= 9 or VARIANT == 13:
                self.send(P.msg_cmd_sync(0, b""), "cmdsync (snapshot guess)")
            if VARIANT in (7, 8, 9, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42):
                self.v7_connect()
            elif 5 <= VARIANT <= 6:
                self.send(P.msg_cmd_add_player(self.player_id, PLAYER_NAME, True), "add_player(top-level, UE3 side)")
            if not hasattr(self, "task"):
                self.task = asyncio.ensure_future(self.frame_loop())
                asyncio.get_event_loop().call_later(1.5, self.start_sequence)
        elif typ == P.T_CLIENT_INFO:
            asyncio.get_event_loop().call_later(0.3, self.start_sequence)
        elif VARIANT == 17 and typ == P.T_CMD_PLAY_STATE_CHANGE:
            log("  (v17: 0x4e3e NOT echoed)")
        elif VARIANT in (15, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42) and typ == P.T_CMD_PLAY_STATE_CHANGE:
            # client-originated MsgCmdPlayStateChange (uid, u16 state, bool): the original master broadcast Cmds to all players
            self.send(P.frame(typ, body), "RELAY 0x4e3e echo (verbatim)")
            if VARIANT == 22 and body[-1:] == b"\x01":
                self.at(400, lambda: self.send(P.frame(typ, body[:-1] + b"\x00"), "v22: 0x4e3e flag cleared"))
        elif VARIANT in (15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42) and typ == P.T_REQ_PLAYER_BODYTURN:
            self.nturn = getattr(self, "nturn", 0) + 1
            log("  RELAY-CANDIDATE 0x2754 #%d (not echoed: no Cmd counterpart found)" % self.nturn)
        elif VARIANT in (38, 39) and typ == 0x2737:
            try:
                import struct as _st
                uid, i = 0, 0
                sh = 0
                while True:
                    c = body[i]; i += 1; uid |= (c & 0x7F) << sh; sh += 7
                    if c < 0x80:
                        break
                x, y, z = _st.unpack("<3f", body[i:i + 12])
                self.n_echo = getattr(self, "n_echo", 0) + 1
                out = (x, y, z) if VARIANT == 38 else (x, z, y)
                self.send(P.frame(0x4ECA, P.varint(uid) + P.f16(out[0]) + P.f16(out[1]) + P.f16(out[2])),
                          ("v%d ECHO #%d 0x2737 (%.2f,%.2f,%.2f) -> Cmd 0x4eca" % (VARIANT, self.n_echo, x, y, z)) if self.n_echo % 20 == 1 else None)
            except Exception as e:
                log("  v%d echo failed: %r" % (VARIANT, e))
        elif VARIANT in (41, 42) and typ in (0x2737, 0x2738, 0x2739):
            # V41/V42: relay the client's move input INSIDE the next 0x2715 frame as the Sync.dll slave message of the same layout
            # (Sync.dll dispatcher 0x100348c0: 0x191=401 uid+3xf32 position -> WalkerSlave 0x1005ace0; 402 uid,uvar,3xf16 ; 403 uid,uvar)
            smap = {0x2737: 401, 0x2738: 402, 0x2739: 403}
            if typ == 0x2737 or VARIANT == 42:
                self.pending.append(P.frame(smap[typ], body))
                self.n_slv = getattr(self, "n_slv", {})
                self.n_slv[typ] = self.n_slv.get(typ, 0) + 1
                if self.n_slv[typ] % 20 == 1:
                    log("  v%d IN-FRAME slave %d <- client 0x%x #%d body=%s" % (VARIANT, smap[typ], typ, self.n_slv[typ], body.hex(" ")))
        elif VARIANT in (38, 39, 41, 42) and typ in (0x273E, 0x2778, 0x273A):
            log("  SPRINT/STYLE CANDIDATE req 0x%x body=%s (no reply known)" % (typ, body.hex(" ")))
        elif VARIANT == 23 and typ in V23_RELAY:
            self.send(P.frame(V23_RELAY[typ], body), "v23 RELAY 0x%x -> 0x%x" % (typ, V23_RELAY[typ]))
        elif V50 and typ in V50_REPLY:
            try:
                out_t, out_body, note = V50_REPLY[typ](body)
                if out_t is not None:
                    self.send(P.frame(out_t, out_body), "V50 REPLY 0x%x -> Cmd 0x%x (%s) req=%s" % (typ, out_t, note, body.hex(" ")))
            except Exception as e:
                log("  V50 reply failed for 0x%x: %r" % (typ, e))
        elif TUT and typ == 0x2750:
            self.send(P.frame(0x4E93, body), "v43 REPLY CmdSyncTutorialStage 0x4e93 <- ReqTutorialStep body=%s" % body.hex(" "))
        elif typ == P.T_SELF_PING:
            pass  # client latency probe; reply format unknown, nothing seems to be required
        elif typ not in (P.T_PING,):
            log("  (unhandled client message, logged only)")


async def handle(reader, writer):
    c = Conn(reader, writer)
    log("TCP CONNECT from %s:%s" % c.peer)
    buf = b""
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            log("RAW RECV %d bytes (stream offset %d): %s" % (len(data), c.rx.pos, data.hex(" ")))
            buf += c.rx.apply(data)
            try:
                msgs, buf = P.split_frames(buf)
            except ValueError as e:
                log("FRAMING ERROR %s; remaining plaintext %s" % (e, buf.hex(" ")))
                buf = b""
                continue
            for typ, body in msgs:
                c.on_message(typ, body)
    except Exception as e:
        log("TCP error: %r" % (e,))
    finally:
        c.closed = True
        log("TCP CLOSED %s:%s (rx %d bytes, tx %d bytes, frames sent %d)" % (c.peer[0], c.peer[1], c.rx.pos, c.tx.pos, c.frame_no))
        try:
            writer.close()
        except Exception:
            pass


async def main():
    srv = await asyncio.start_server(handle, HOST, PORT)
    log("VARIANT %d: %s" % (43 if TUT else VARIANT, VARIANT_DESC[43 if TUT else VARIANT]))
    log("battle_server listening TCP %s:%d  frame=%dms name=%r start=%s" % (HOST, PORT, FRAME_MS, PLAYER_NAME, not NO_START))
    log("logfile: %s" % LOGFILE)
    async with srv:
        await srv.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

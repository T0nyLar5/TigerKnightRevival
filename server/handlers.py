# -*- coding: utf-8 -*-
"""Route handlers for the fake lobby server.

HOW TO ADD A ROUTE:  write  def my_route(req, st): return {...}  and add one line to ROUTES at the bottom.
  req = request body (dict).   st = State (st.player = saved player dict, st.save() writes player.json).
Every response must carry "code": 0 (success is 0, not 200).   Tags: [C] confirmed from notes, [G] guessed.
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
PLAYER_FILE = os.path.join(DATA_DIR, "player.json")

# What to answer for routes that have no handler. Change with  lobby.py --unknown-code N
UNKNOWN_CODE = 0

DEFAULT_PLAYER = {
    "steamid": "",
    "uid": "10001",           # role uid (string in the protocol)
    "name": "",               # filled from steamid on first login
    "level": 60, "experience": 999999999, "sex": 0,   # 60 = max level (Lua BattleSettlement clamps display at "Lv60")
    "helpPanel": 0xFFFF,      # bitmask of seen help panels (Lua stages 1-4); all set = no overlays
    "gold": 100000, "copper": 100000, "score": 0, "generalexp": 0, "exploit": 0,
    "tutorialStep": 5,        # >= 4 skips the tutorial
    "faceicon": 0, "faceframe": 0, "tp": "hk", "sname": "",
    "jade": 0, "fleecoin": 0,
    # filled by tools/unlock_all.py (see its docstring); handlers below serve these lists
    "ranks": {},            # nation(str) -> [rank ids] open in the soldier tech tree
    "sciences": [],         # [{id, type}] open tech nodes
    "soldierexp": [],       # [{country, stage, exp}] max 20 rows read by the DLL
    "soldiers": [],         # owned soldier rows (getSoldier row layout)
    "heroes": [],           # owned hero rows (loadRoleAssistant row layout)
    "equiplst": [],
    "items": [],            # bag rows {id(str),type,uid(str),endurance,num,timeout,commonused} (loadRoleItem push pages)
}


class State:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.created = not os.path.exists(PLAYER_FILE)
        self.player = dict(DEFAULT_PLAYER)
        if not self.created:
            try:
                with open(PLAYER_FILE, "r", encoding="utf-8") as f:
                    self.player.update(json.load(f))
            except Exception:
                self.created = True
        cr = self.player.get("created_role_req")      # character saved by an older build that did not unwrap "params"
        if isinstance(cr, dict) and "params" in cr and not self.player.get("faces56"):
            _apply_create(self.player, cr["params"])
            self.player["created_role_req"] = cr["params"]
            self.player["tutorialStep"] = max(int(self.player.get("tutorialStep", 5)), 5)
            self.created = True      # forces a save below
        pl = self.player      # always max level / all help panels seen (user request)
        fix = (pl.get("level", 0) < 60 or pl.get("experience", 0) < 999999999 or pl.get("helpPanel", 0) != 0xFFFF)
        pl["level"] = max(pl.get("level", 0), 60)
        pl["experience"] = max(pl.get("experience", 0), 999999999)
        pl["helpPanel"] = 0xFFFF
        if self.created or fix:
            self.save()

    def save(self):
        tmp = PLAYER_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.player, f, ensure_ascii=False, indent=2)
        os.replace(tmp, PLAYER_FILE)


def ok(**kw):
    d = {"code": 0}
    d.update(kw)
    return d


def _account(p):
    return {"tp": p["tp"], "uid": p["uid"], "name": p["name"], "level": p["level"], "sex": p["sex"],
            "gold": p["gold"], "score": p["score"], "copper": p["copper"], "generalexp": p["generalexp"],
            "exploit": p["exploit"], "sname": p["sname"], "faces": _faces_list(p, 56), "faceicon": p["faceicon"],
            "faceframe": p["faceframe"], "vipvalidtimesec": 0, "native": p.get("native", 0)}


# ---------------------------------------------------------------- login  [C]
def auth(req, st):
    p = st.player
    sid = str(req.get("name", ""))
    if sid and p["steamid"] != sid:
        p["steamid"] = sid
        if not p["name"]:
            p["name"] = "騎士" + sid[-4:]
        st.save()
    if not p["name"]:
        p["name"] = "騎士0001"
        st.save()
    return ok(uid=p["uid"], accounts=[_account(p)])   # exactly ONE account -> client sends entry by itself


def entry(req, st):
    return ok(uid=st.player["uid"], restore=False, csid=1, forbidtime=0, chatnum=[0])


# ---------------------------------------------------------------- data loading  [C schema, G order]
# Character-creation test mode (launcher 一鍵測試_捏角色.bat sets TK_NEW_CHAR=1): getRoleState reports tutorialStep 0
# so Login.lua On_GetRoleState -> Login_TutorialMode_Force_Complete -> BeginCreateRole -> CreatRole_Gender/Face/Nation [G, static].
# The value is NOT written to player.json; normal mode is untouched.
NEW_CHAR_MODE = os.environ.get("TK_NEW_CHAR") == "1"
_newchar_done = False


def get_role_state(req, st):
    step = st.player["tutorialStep"]
    if NEW_CHAR_MODE and not _newchar_done:
        step = 0
        print("[NEWCHAR] getRoleState -> tutorialStep 0 (character creation should open)", flush=True)
    return ok(uid=st.player["uid"], tutorialStep=step, vipvalidtimesec=0, forbidtalktime=0)


def _backup_player_once():
    bak = PLAYER_FILE + ".before_newchar"
    if not os.path.exists(bak) and os.path.exists(PLAYER_FILE):
        import shutil
        shutil.copyfile(PLAYER_FILE, bak)


def check_nick_name(req, st):                 # req {name?}  [G] always available
    print("[checkNickName] req=%s" % json.dumps(req, ensure_ascii=False), flush=True)
    return ok()


def _faces_list(p, n=None):
    f = p.get("faces56")
    if not isinstance(f, list) or not f:
        return [0] * (n or 56)
    f = [int(x) for x in f if isinstance(x, (int, float))]
    return f[:n] if n else f


def _unwrap(req):
    """Real client requests for some routes arrive as {"params": {...}} (VERIFIED newUser log 2026-11-07 23:06); accept both."""
    if isinstance(req, dict) and isinstance(req.get("params"), dict):
        return req["params"]
    return req if isinstance(req, dict) else {}


def _apply_create(p, req):
    """Copy the character-creation request fields into the saved player (name/sex/native/voice/face icon/frame/56 face values)."""
    if isinstance(req.get("name"), str) and req["name"]:
        p["name"] = req["name"]
    for k in ("sex", "native", "voice", "faceicon", "faceframe"):
        if isinstance(req.get(k), int):
            p[k] = req[k]
    fs = req.get("faces")
    if isinstance(fs, str):
        try:
            p["faces56"] = [int(x) for x in fs.split(",") if x.strip() != ""]
        except ValueError:
            pass
    elif isinstance(fs, list):
        p["faces56"] = [int(x) for x in fs if isinstance(x, (int, float))]


def new_user(req, st):                        # RegisterRole(name, gender, head, faceData, hair, scars, nation, preview, headId, 0)
    # VERIFIED request (2026-11-07 log): {"params": {faceframe, faceicon, faces:"0,50,..(56 ints)", name, native(nation 1-3), sex, voice}}
    # DLL response parser (PoClientDLL case 13, static): {code, uid, sex, native, voice, name, faces:[int]} -> then Lua cb 5.
    global _newchar_done
    print("[newUser] req=%s" % json.dumps(req, ensure_ascii=False)[:1500], flush=True)
    _backup_player_once()
    p = st.player
    req = _unwrap(req)
    _apply_create(p, req)
    p["created_role_req"] = req               # raw request kept for later analysis
    p["tutorialStep"] = max(int(p.get("tutorialStep", 5)), 5)   # never re-open creation / tutorial on later logins
    st.save()
    _newchar_done = True
    r = ok(uid=p["uid"], sex=p["sex"], native=p.get("native", 0), voice=p.get("voice", 0), name=p["name"],
           faces=_faces_list(p))
    if os.environ.get("TK_NEWCHAR_PUSH", "1") == "1":     # guess: tell the client the role state is now >= 4 (cb 9 On_RoleStateUpdate)
        r["_push_after"] = [("turorialInfo", {"msgs": [{"tutorial": 5}]})]
    return r


def use_change_face_card(req, st):            # in-lobby appearance editor (Store disguise item) [G]
    print("[useChangeFaceCard] req=%s" % json.dumps(req, ensure_ascii=False)[:1500], flush=True)
    _backup_player_once()
    req = _unwrap(req)
    _apply_create(st.player, req)
    st.player["changeface_req"] = req
    st.save()
    return ok()


def get_self_info(req, st):
    p = st.player
    info = {"identity": 0, "uid": p["uid"], "name": p["name"], "level": p["level"], "experience": p["experience"],
            "sex": p["sex"], "gold": p["gold"], "barracksnum": 200, "score": p["score"], "copper": p["copper"],
            "fleecoin": p["fleecoin"], "generalexp": p["generalexp"], "vipvalidtimesec": 0, "noviciatestage": 99,
            "helpPanel": 0xFFFF, "liveShow": False, "signinMonth": 0, "signinData": 0, "resigninNum": 0,
            "onlinedate": 0, "onlinetime": 0, "onlinehadreward": 0, "faces": _faces_list(p, 56),
            "faceicon": p["faceicon"], "faceframe": p["faceframe"], "autosupplyflag": False,
            "autorecruitflag": False, "voice": p.get("voice", 0), "exploit": p["exploit"],
            "pveinfo": {"degree1Win": 0, "degree2Win": 0, "degree3Win": 0}, "native": p.get("native", 0), "cheatnum": 0,
            "cheatnumtotal": 0,
            # forbidmatch MUST be an object: the DLL does info["forbidmatch"]["forbid"] / ["outTime"]. A scalar here
            # makes jsoncpp's operator[] treat the int as a map pointer -> access violation (notes/crash/analysis.md)
            "forbidmatch": {"forbid": False, "outTime": 0},
            "hungup": 0, "maliciouslogout": 0, "jade": p["jade"],
            "tutorialAward": [True] * 5,                      # array of bool, DLL reads at most 5
            # array of {country, stage, exp} (DLL reads at most 20); country 1..3 = Wei/Shu/Wu [G]
            "soldierexp": (p["soldierexp"] or [{"country": c, "stage": 1, "exp": 0} for c in (1, 2, 3)])[:20],
            "forbidtalktime": 0, "ceVal": 0, "preCeVal": 0}
    return ok(info=info)


def set_help_panel(req, st):
    """req {val:uint} = ONE help-panel bit the client just saw (1,2,4,8 = stages 1-4); resp only {code} [C DLL case 242]."""
    p = st.player
    p["helpPanel"] = int(p.get("helpPanel", 0)) | int(req.get("val", 0) or 0) | 0xFFFF
    st.save()
    return ok()


def query_server_time(req, st):
    offset = -(time.altzone if time.daylight and time.localtime().tm_isdst else time.timezone) // 3600
    return ok(ServerTime=int(time.time()), DeltaUTC=offset)


def load_prop_bar(req, st):
    return ok(propbar=[])


# Role suit = what the hero wears. Client positions (Lua Store.lua tSuit[pos]) -> loadRoleSuit key. Values are bag item ids (str), "0" = empty.
SUIT_POS_KEY = {1: "helmet", 2: "armor", 3: "shoes", 4: "shawl", 5: "horse", 6: "weapon1", 7: "weapon2", 8: "weapon3", 9: "weapon4",
                10: "saddle", 11: "hoof", 12: "strike", 13: "horseadd", 14: "fashion", 15: "banner", 16: "markflag",
                17: "flee_helmet", 18: "flee_shawl", 19: "flee_armor", 20: "flee_shoes",
                21: "fashion1", 22: "fashion2", 23: "fashion3", 24: "fashion4", 25: "fashion5", 26: "fashion6", 27: "fashion7"}


def _suit_rows(st):
    """player.suits = list (index = suit no.) of {pos(str): itemid(str)}; always at least one suit."""
    su = st.player.get("suits")
    if not isinstance(su, list) or not su:
        su = st.player["suits"] = [{}]
    return su


def _suit_obj(d):
    # [C] the DLL parses every suit value with asString and maps it through a string->internal-id table, so "0" becomes a NON-zero id
    # whose bag lookup fails (Lua then errors in Show_PlayerEquip / Store_HandleEquip: blank tab, dead paging, equip click silent).
    # An empty slot must therefore be OMITTED (the parser leaves the memset 0).
    o = {}
    for pos, iid in d.items():
        k = SUIT_POS_KEY.get(int(pos))
        if k and iid not in ("", None, 0, "0"):
            o[k] = str(iid)
    return o


def load_role_suit(req, st):                  # resp {suits:[{helmet..: itemid str}]} [C keys]
    return ok(suits=[_suit_obj(d) for d in _suit_rows(st)])


def exch_role_equipment(req, st):             # req {command:[{itemid,pos,suit}]}  (itemid ""/0 = take off). Success is driven by the push updateRoleEquip [C case 29]
    cmds = req.get("command") or []
    if isinstance(cmds, dict):
        cmds = [cmds]
    su = _suit_rows(st)
    pushed = []
    for c in cmds:
        if not isinstance(c, dict):
            continue
        try:
            pos = int(c.get("pos", 0))
            sno = int(c.get("suit", 0) or 0)
        except (TypeError, ValueError):
            continue
        iid = c.get("itemid", "")
        iid = "" if iid in ("", None, 0, "0") else str(iid)
        while len(su) <= sno:
            su.append({})
        if iid:
            su[sno][str(pos)] = iid
            pushed.append({"itemid": iid, "suit": sno, "pos": pos})
        else:                                   # take off: omit itemid (a "0" string would map to a non-zero internal id) [C]
            su[sno].pop(str(pos), None)
            pushed.append({"suit": sno, "pos": pos})
    print("[exchRoleEquipment] req=%s -> %s" % (json.dumps(req), json.dumps(pushed)), flush=True)
    st.save()
    r = ok()
    if pushed:
        r["_push"] = [("updateRoleEquip", {"suits": pushed})]
    return r


def increase_role_suit(req, st):              # resp {ind}: new suit index
    su = _suit_rows(st)
    su.append({})
    st.save()
    return ok(ind=len(su) - 1)


def query_all_assets(req, st):
    return ok(start=0, assets=[])


def paged_empty(req, st):
    """Single empty final page for the paged list routes [G]."""
    return ok(isfinal=True, serialNum=0, pageindex=0, totalpage=1, totalsize=0, pagesize=0, items=[])


def join_chat_channel(req, st):
    # chat is a second Pomelo server; we have none. host/port point back at ourselves, harmless if unused [G]
    # channel/port/degree/token are uint in the DLL parser, host is a string [C]
    return ok(channel=0, port=3015, degree=0, token=0, host="127.0.0.1")


def get_chat_connectors_info(req, st):
    return ok(chatDegree=[0])


def chat_channel_info(req, st):
    return ok(channel="", users=[])


def match_restore(req, st):
    return ok(addr=[], subGameMode=0, gameMode=0, token="", playerId=0, camp=0, mapId=0, gameType=0)


# ---- replies for routes that used to get a bare {"code":0}  [C schema from PoClientDLL parsers, see notes]
def load_role_item(req, st):
    # Rows arrive as push "loadRoleItem" pages (see notes/lobby/state_and_actions.md section 5), the response is only the ack [C].
    rows = st.player.get("items") or []
    serie = req.get("serieNum", 0) if isinstance(req, dict) else 0
    r = ok(isfinal=1, capacity=max(100, len(rows) + 100), serieNum=serie, items=[])          # capacity value [G]
    now = time.time()
    if now - getattr(st, "_item_push_t", 0) < 5:      # the client sends every init request twice; a 2nd push of the same ids is rejected (ItemDataManager.cpp:252)
        rows = []
    else:
        st._item_push_t = now
    if rows:
        r["_push"] = [("loadRoleItem", pg) for pg in _pages(rows, 50, serie, capacity=max(100, len(rows) + 100))]
    return r


def req_store_info(req, st):
    return ok(version=0, isfinal=1, serieNum=0, items=[])


def load_role_email(req, st):
    return ok(curDaySend=0, isfinal=1, serieNum=0, items=[])


def load_role_task(req, st):
    # each task: {taskid, complete, sche1, sche2, sche3, notaward:bool}
    return ok(dailyTasks=[], dailyRefreshCount=0, limittimeTasks=[], commonTasks=[])


def get_sign_in_info(req, st):
    # the DLL key really is spelled "singninCount"
    return ok(signinMonth=0, signinData=0, resigninNum=0, singninCount=0, signinreward=[], treegiftdate=0)


def get_online_info(req, st):
    return ok(onlinedate=0, onlinetime=0, onlinehadreward=0)


def query_vip_buy_sort(req, st):
    # parser reads only vipBuySorts (code kept for safety). Rows from notes/scripts/ui/lua_config/VIP.lua: days / gold / rebate
    return {"code": 0, "vipBuySorts": [{"days": 7, "gold": 780, "rebate": 780}, {"days": 30, "gold": 1600, "rebate": 1600},
                            {"days": 180, "gold": 7800, "rebate": 9600}, {"days": 360, "gold": 12800, "rebate": 19200}]}


def charge_get_list(req, st):
    return ok(data=[])            # rows: {id, num, steps:[uint]}


def get_battle_profit_multi_info(req, st):
    # rows: {id, des, deadline:[{type,date1,date2,week:[]}], armytype:[], gamemode:[{main,sub}], winjudge:bool,
    # isArmyFirstWin:bool, times, moneymulti, expmulti, armyexpmulti, heroexpmulti, generalexpmulti, exploitmulti}
    # Empty = no bonus events; Lua SodierCard_ManyExp returns early on an empty table.
    return ok(data=[])


def load_store_buy_limit(req, st):
    # limitinfo rows: {itemtypeid, num}; fleebox must be an OBJECT {buycnt, buytime} (the parser indexes into it)
    return ok(limitinfo=[], fleebox={"buycnt": 0, "buytime": 0})


def get_role_equipment(req, st):
    return ok(equiplst=list(st.player.get("equiplst") or []))          # array of uint [C]


SOLDIER_ROW = {"id": 0, "amount": 0, "sequence": 0, "exp": 0, "helmet": 0, "shoes": 0, "armor": 0, "shawl": 0, "horse": 0,
               "saddle": 0, "hoof": 0, "strike": 0, "horseadd": 0, "weapon1": 0, "weapon2": 0, "weapon3": 0, "weapon4": 0,
               "fashion": 0, "skill1": 0, "skill2": 0, "skill3": 0, "skill4": 0, "skill5": 0, "skill6": 0, "skill7": 0,
               "skill8": 0, "lastwinTime": 0}


def _pages(rows, size, serie, **extra):
    """Split rows into paged push bodies {totalsize,pagesize,totalpage,pageindex,isfinal,serieNum,items,...} [C keys from DLL 0x10002500]."""
    chunks = [rows[i:i + size] for i in range(0, len(rows), size)] or [[]]
    out = []
    for i, ch in enumerate(chunks):
        d = dict(extra)
        d.update(totalsize=len(rows), pagesize=size, totalpage=len(chunks), pageindex=i,
                 isfinal=1 if i == len(chunks) - 1 else 0, serieNum=serie, items=ch)
        out.append(d)
    return out


_SOLDIER_SUBKIND = None


def _playable_soldiers(rows):
    """Hide special/NPC troops (soldiers.txt SoldierSubKind 8xxx, e.g. 812024) from the barracks / 戰備 list: they have no icon and were picked as the default army [client log 02:35]."""
    global _SOLDIER_SUBKIND
    if _SOLDIER_SUBKIND is None:
        _SOLDIER_SUBKIND = {}
        try:
            fn = os.path.join(HERE, "..", "notes", "decrypted", "cfg", "sync_config", "config", "soldiers.txt")
            with open(fn, encoding="utf-8-sig") as f:
                for line in f:
                    c = line.rstrip(chr(10)).split(chr(9))
                    if c[0].isdigit() and len(c) > 4:
                        _SOLDIER_SUBKIND[int(c[0])] = c[4]
        except Exception:
            _SOLDIER_SUBKIND = {}
    if not _SOLDIER_SUBKIND:
        return rows
    return [x for x in rows if not _SOLDIER_SUBKIND.get(int(x["id"]), "0").startswith("8")]


_SOLDIER_LEVEL = None
DEFAULT_ARMY = 112014                                    # 2-star (stage 2, Lv5) default / fallback troop
_STAGE_LEVELS = {1: (1, 4), 2: (5, 7), 3: (8, 10)}     # EArmyStagLev (notes\scripts\ui\LuaScript\ServerEnum.lua)


def _soldier_level(sid):
    """soldiers.txt Level column (index 9), 1-10."""
    global _SOLDIER_LEVEL
    if _SOLDIER_LEVEL is None:
        _SOLDIER_LEVEL = {}
        try:
            fn = os.path.join(HERE, "..", "notes", "decrypted", "cfg", "sync_config", "config", "soldiers.txt")
            with open(fn, encoding="utf-8-sig") as f:
                for line in f:
                    c = line.rstrip(chr(10)).split(chr(9))
                    if c[0].isdigit() and len(c) > 9 and c[9].isdigit():
                        _SOLDIER_LEVEL[int(c[0])] = int(c[9])
        except Exception:
            _SOLDIER_LEVEL = {}
    return _SOLDIER_LEVEL.get(int(sid), 0)


def _max_army_class():
    return int(os.environ.get("TK_ARMYCLASS", "1") or 1)


def _effective_army(st, army):
    """Troop the battle uses. The 戰備 list shows the stage max_class+1 only (owner test 2026-11-08: maxArmyClass 2 listed only
    3-star, Lv 8-10). An owned troop outside that stage is replaced by the first owned listed troop; ids the owner does not own are kept as sent."""
    lo, hi = _STAGE_LEVELS.get(_max_army_class() + 1, (0, 0))
    owned = [int(x["id"]) for x in _playable_soldiers(st.player["soldiers"])]
    def listed(sid):
        return sid in owned and lo <= _soldier_level(sid) <= hi
    if army and (army not in owned or listed(army)):
        return army                              # not an owned playable troop (e.g. test / tutorial id): keep as sent
    if listed(DEFAULT_ARMY):                     # owner 2026-11-08: fixed 2-star (medium) default 112014 (Lv5)
        return DEFAULT_ARMY
    for sid in owned:
        if listed(sid):
            return sid
    return army


def get_soldier(req, st):
    # The response only carries code/isfinal/serieNum [C]; the rows arrive as server PUSH "getSoldier" pages (items = SOLDIER_ROW) [C layout, G delivery]
    serie = req.get("serieNum", 1)
    r = ok(isfinal=1, serieNum=serie)
    rows = _playable_soldiers(st.player["soldiers"])
    if rows:
        r["_push"] = [("getSoldier", pg) for pg in _pages(rows, 50, serie)]
    return r


def _hero_wire(h):
    r = dict(h)
    hf = r.get("haveflag", True)
    r["haveflag"] = bool(any(hf)) if isinstance(hf, list) else bool(hf)
    return r


def load_role_assistant(req, st):
    # heros rows: {id, exp, coatmask, haveflag[], idcoat, timevalid, loyalty, forwardhero}
    # [C] DLL parser: haveflag is a JSON BOOLEAN (type 5, asBool); an array/int there reads as false = "not owned".
    # forwardhero is a TOP-LEVEL uint, not per row.
    rows = [_hero_wire(h) for h in st.player["heroes"]]
    fw = next((h["id"] for h in st.player["heroes"] if h.get("forwardhero")), 0)
    return ok(heros=rows, forwardhero=fw)


# ---- tech tree actions  [C request/response keys from the DLL builders/parsers, G client-side effects]
def _rank_nation(rank):
    return 999 if rank == 999 else rank // 100


def open_rank(req, st):                       # req {rankid, prerank}  resp {code, rank}
    rk = int(req.get("rankid", 0))
    lst = st.player["ranks"].setdefault(str(_rank_nation(rk)), [])
    if rk and rk not in lst:
        lst.append(rk)
        st.save()
    return ok(rank=rk)


def open_science(req, st):                    # req {scitechid, scitechtype}  resp {code, scitechid, scitechtype}
    tid, tt = int(req.get("scitechid", 0)), int(req.get("scitechtype", 0))
    if tid and not any(x["id"] == tid for x in st.player["sciences"]):
        st.player["sciences"].append({"id": tid, "type": tt})
        st.save()
    r = ok(scitechid=tid, scitechtype=tt)
    # The ack alone does NOTHING on success: the frontend ack handler (vtable slot 0x2bc, FUN_00878bf0) only posts
    # on_ScienceTypeOpenFail when code!=0. The success path (Lua TechTree_UpdateOpenTech -> hides "NormalWaiting")
    # is driven by the PUSH openTechType {techlist:[{techid,techtype}]} [C DLL dispatcher case 23]. Without it the
    # "NormalWaiting" overlay stays up forever = the freeze seen when unlocking equipment in the soldier tech tree.
    if tid:
        r["_push"] = [("openTechType", {"techlist": [{"techid": tid, "techtype": tt}]})]
    return r


def buy_soldier(req, st):                     # req {armyid}  resp {code, armyid}; establishArmy push carries the new row
    aid = int(req.get("armyid", 0))
    sold = st.player["soldiers"]
    row = next((x for x in sold if x["id"] == aid), None)
    if row is None and aid:
        row = dict(SOLDIER_ROW, id=aid, sequence=len(sold) + 1)
        sold.append(row)
        st.save()
    r = ok(armyid=aid)
    if row is not None:
        r["_push"] = [("establishArmy", {"soldiers": [row]})]
    return r


def sell_soldier(req, st):
    aid = int(req.get("armyid", 0))
    st.player["soldiers"] = [x for x in st.player["soldiers"] if x["id"] != aid]
    st.save()
    return ok(armyid=aid)


# soldier slots by itemtype sort1 = (id // 100000) % 100 (Lua Store.lua ITEMTYPE_SORT_1_*) [C]; the stored values are item TYPES [G]
_SOLDIER_SORT_FIELD = {70: "helmet", 71: "shawl", 72: "armor", 73: "shoes", 60: "horse", 58: "fashion"}
_SOLDIER_POS_FIELD = {1: "helmet", 2: "armor", 3: "shoes", 4: "shawl", 5: "horse", 6: "weapon1", 7: "weapon2", 8: "weapon3",
                      9: "weapon4", 10: "saddle", 11: "hoof", 12: "strike", 13: "horseadd", 14: "fashion"}


def _item_type_of(st, data):
    """data may be an item type (8 digits) or a bag item id."""
    if data >= 1000000:
        return data
    for it in st.player.get("items", []):
        if str(it.get("id")) == str(data):
            return int(it.get("type", 0))
    return data


def _free_slot(row, names):
    for n in names:
        if not row.get(n):
            return n
    return names[0]


def _equip_field(row, itype):
    sort1 = (itype // 100000) % 100
    if sort1 in _SOLDIER_SORT_FIELD:
        return _SOLDIER_SORT_FIELD[sort1]
    if 80 <= sort1 <= 84:
        return _free_slot(row, ["weapon1", "weapon2", "weapon3", "weapon4"])
    if sort1 == 59:           # horse equipment; sort2 unknown -> first free of saddle/hoof/strike/horseadd [G]
        return _free_slot(row, ["saddle", "hoof", "strike", "horseadd"])
    return None


def oper_army_attr(req, st):                  # req {armyid, opertype 0 sequence|1 recruit|2 autoequip|3 unequip, data}  [C enum ServerEnum.lua]
    aid = int(req.get("armyid", 0) or 0)
    ot = int(req.get("opertype", 0) or 0)
    data = req.get("data", 0)
    data = int(data[0] if isinstance(data, list) and data else (data or 0))
    row = next((x for x in st.player["soldiers"] if x["id"] == aid), None)
    log = "[oper_army_attr] armyid=%s opertype=%s data=%s" % (aid, ot, data)
    if row is not None:
        if ot == 0:
            row["sequence"] = data
        elif ot == 1:
            row["amount"] = data
        elif ot == 2:
            itype = _item_type_of(st, data)
            f = _equip_field(row, itype)
            log += " type=%s -> %s" % (itype, f)
            if f:
                row[f] = itype
        elif ot == 3:
            f = _SOLDIER_POS_FIELD.get(data)
            log += " -> %s" % f
            if f:
                row[f] = 0
        st.save()
    print(log, flush=True)
    r = ok(armyid=aid, opertype=ot, data=data)
    if row is not None:
        r["_push"] = [("establishArmy", {"soldiers": [row]})]
    return r


def buy_role_equipment(req, st):              # req {scitechtype, equiptype}
    et = int(req.get("equiptype", 0) or 0)
    r = ok(scitechtype=req.get("scitechtype", 0), equiptype=et, itemtypeid=et, scitechid=req.get("scitechtype", 0))
    if et and et not in st.player["equiplst"]:
        st.player["equiplst"].append(et)
        st.save()
    # [G] TechTree_UpdatePlayerBuyTech draws the "Warehouse" icon: the bought hero gear is meant to land in the bag, so append a bag item (push appendItem, DLL case 26)
    items = st.player.setdefault("items", [])
    if et and not any(int(i.get("type", 0)) == et for i in items):
        nid = max([int(i["id"]) for i in items] + [0]) + 1
        row = {"id": str(nid), "type": et, "uid": str(st.player.get("uid", "10001")), "endurance": 100, "num": 1, "timeout": 0, "commonused": 0}
        items.append(row)
        st.save()
        r["_push"] = [("appendItem", {"items": [row]})]
    print("[buyRoleEquipment] req=%s pushed=%s" % (json.dumps(req), bool(r.get("_push"))), flush=True)
    return r


def buy_soldier_equipment(req, st):           # req {scitechid, equiptype}; bought list is global (everything is unlocked anyway) [G]
    et = int(req.get("equiptype", 0) or 0)
    se = st.player.setdefault("soldier_equip", {})
    lst = se.setdefault("all", [])
    if et and et not in lst:
        lst.append(et)
        st.save()
    return ok(scitechid=req.get("scitechid", 0), equiptype=req.get("equiptype", 0))


def get_soldier_equipment(req, st):           # req {rank}; resp {equiplst:[uint], rank}
    se = st.player.get("soldier_equip") or {}
    lst = list(dict.fromkeys(list(se.get("all", [])) + list(se.get(str(req.get("rank", 0)), []))))
    return ok(rank=req.get("rank", 0), equiplst=lst)


# ---- heroes / lieutenants (loadRoleAssistant rows; fujiang.txt ids 101001.. and 8xxxxx)
def _hero_id(req):
    for k in ("assistantid", "heroid", "id", "herotype", "hero"):
        if req.get(k):
            return int(req[k])
    return 0


def recruit_role_assistant(req, st):          # req {assistantid, data}; resp {code}. Success is the push updateHero {hero row} [C case 17]
    hid = _hero_id(req)
    row = next((h for h in st.player["heroes"] if h["id"] == hid), None)
    if row is None and hid:
        row = {"id": hid, "exp": 0, "coatmask": 15, "haveflag": True, "idcoat": 0, "timevalid": 0, "loyalty": 100, "forwardhero": 0}
        st.player["heroes"].append(row)
        st.save()
    r = ok(assistantid=hid, herotype=hid, heroid=hid, id=hid, data=req.get("data", 0))   # [G] OnOperHero looked up hero_type key 0 -> echo the id under every plausible name
    if row is not None:
        body = _hero_wire(row)
        body["hero"] = _hero_wire(row)
        r["hero"] = _hero_wire(row)                         # [G] OnOperHero reads a hero_type key from the reply (was 0): also give the whole row, in case it lives there
        r["haveflag"] = True
        r["_push"] = [("updateHero", body)]
    print("[recruit] req=%s" % json.dumps(req), flush=True)
    return r


def forward_role_assistant(req, st):          # set the lieutenant that goes to battle; push forwardHero {id} [C case 25]
    hid = _hero_id(req)
    for h in st.player["heroes"]:
        h["forwardhero"] = 1 if h["id"] == hid else 0
    st.save()
    print("[forward] req=%s" % json.dumps(req), flush=True)
    r = ok(assistantid=hid, herotype=hid, heroid=hid, id=hid, data=req.get("data", 0))
    if hid:
        r["_push"] = [("forwardHero", {"id": hid})]
    return r


def ack_logged(name):
    def h(req, st):
        print("[%s] req=%s" % (name, json.dumps(req)), flush=True)
        return ok()
    return h


def query_perfect_rank_info(req, st):
    return ok(rankinfo=[])


def enumerate_friends(req, st):
    # both arrays hold {uid, name, sex, level, vip, state, syndName}; empty = no friends
    return ok(friendsInfo=[], freqs=[])


def get_black_list(req, st):
    return ok(list=[])


def get_rank_open_info(req, st):
    # The frontend switches on `nation` (1 Wei, 2 Shu, 3 Wu, 5, 8, 999) to pick which init flag to set, so the reply MUST
    # echo the requested nation; a missing nation (=0) leaves the loading screen stuck [C]. isfinal must be 1.
    nation = req.get("nation", 0)
    serie = req.get("serieNum", 1)
    r = ok(nation=nation, serieNum=serie, isfinal=1)
    rows = [{"rank": x, "nation": nation} for x in st.player["ranks"].get(str(nation), [])]
    if rows:   # rows arrive as push "getRankOpenInfo" pages {nation, ..., items:[{rank,nation}]} [C layout]
        r["_push"] = [("getRankOpenInfo", pg) for pg in _pages(rows, 100, serie, nation=nation)]
    return r


def query_science_type_open_info(req, st):
    serie = req.get("serieNum", 1)
    r = ok(isfinal=1, serieNum=serie)
    ids = [x["id"] for x in st.player["sciences"]]
    # the push is named "ScienceType" open info, so also list the science_type ids (rows' "type"); ranges do not collide [G]
    ids += sorted({x["type"] for x in st.player["sciences"] if x.get("type", 0) >= 100000})
    if ids:    # push "queryScienceTypeOpenInfo" pages, items = plain uint ids [C layout, G meaning = tech node ids]
        r["_push"] = [("queryScienceTypeOpenInfo", pg) for pg in _pages(ids, 250, serie)]
    return r


def query_match_mode_time(req, st):
    return ok(modes=[])                          # rows {mode, subMode, startHour, endHour, startDay, endDay}


def req_challenge_base_info(req, st):
    return ok(challengephase=0, proficiency=[], firstcomplete=[], topscore=[])


def get_syn_info(req, st):
    # `data` and `data.flag` are indexed by the parser, so they must be objects [C]
    return ok(data={"id": "", "name": "", "aim": "", "city": "", "master": "", "creater": "", "deputy": "",
                    "createDate": 0, "level": 0, "checkType": 0, "capacity": 0, "curCapacity": 0, "memberNum": 0,
                    "totalCont": 0, "flag": {"id": 0, "color": 0, "icon": 0, "iconPos": 0}})


# ---------------------------------------------------------------- battle launch (see notes/battle/launch_flow.md)
BATTLE_ADDR = {"ip": "127.0.0.1", "port": 7777}   # server/battle_server.py listens here
BATTLE_TOKEN = 12345
MAP_BY_MODE = {1: 11, 4: 12, 5: 17}               # gamemode -> mapId (see notes/map_ids.md): 11 xinshou tutorial, 12 taofa tutorial, 17 XunLianChang [id->theme C, id->umap G]
DEFAULT_MAP_ID = 17                               # 1 = 'SyncTest' which does not exist in CookedPC


def game_startup(st, mode=1, sub=0, process=1, map_id=None, army=0):
    """Push body for `gameStartup` (DLL parser 0x10011f9b): {"msgs":[{playerInfos[],addr[],process,subMode,gameMode,token,playerId,camp,mapId}]} [C keys, nesting from jsonkeys]."""
    p = st.player
    try:
        pid = int(p["uid"])
    except Exception:
        pid = 10001
    msg = {"playerInfos": [{"roleId": str(p["uid"]), "name": p["name"], "camp": 1, "heroType": 0, "armyType": int(army),
                            "sname": p["sname"], "vip": 0}],
           "addr": [dict(BATTLE_ADDR)], "process": int(process), "subMode": int(sub), "gameMode": int(mode),
           "token": BATTLE_TOKEN, "playerId": pid, "camp": 1,
           "mapId": map_id if map_id is not None else MAP_BY_MODE.get(int(mode), DEFAULT_MAP_ID)}
    if os.environ.get("TK_MAPID", "").strip().isdigit():          # launcher override (一鍵測試_選版本.bat)
        msg["mapId"] = int(os.environ["TK_MAPID"])
    return ("gameStartup", {"msgs": [msg]})


# ---- pre-battle troop selection window "Combat_Readiness" (see notes/lobby/prebattle_troop_select.md)
# Real flow [C Lua/DLL keys, G server behaviour]: joinMatch -> push matchRoomPrepareInfo (window opens, 50 s timer, player picks
# troop/suit) -> Ready (or timeout) sends prepareMatchRoom {suit,armyid,roomId,usepvetoken} -> reply {code,suit,armyid}
# -> push matchRoomPrepare {armyid,roomId,uid} -> push gameStartup (playerInfos[].armyType = chosen army).
# NOTE uid and roomId MUST be JSON strings (DLL asString on a number throws -> abort() "Runtime Error"); the rest are uint/bool.
# TK_PREBATTLE: unset = only gameMode 2 (vs computer / crusade); "0" = off; "all" = every joinMatch mode; or a list like "2,3".
def _prebattle_on(mode):
    v = os.environ.get("TK_PREBATTLE", "").strip().lower()
    if v in ("0", "off", "no"):
        return False
    if v == "all":
        return True
    if v:
        return str(mode) in [x.strip() for x in v.split(",")]
    return int(mode) == 2


def match_room_prepare_info(st, mode, sub, process, map_id=None):
    """Push body for `matchRoomPrepareInfo` [C keys from DLL parser: mode, subMode, mapId, maxArmyClass, roomId, roleInfos[...]]."""
    p = st.player
    try:
        uid = int(p["uid"])
    except Exception:
        uid = 10001
    mid = map_id if map_id is not None else MAP_BY_MODE.get(int(mode), DEFAULT_MAP_ID)
    if os.environ.get("TK_MAPID", "").strip().isdigit():
        mid = int(os.environ["TK_MAPID"])
    st.prebattle = {"mode": int(mode), "sub": int(sub), "process": int(process), "map": mid, "roomId": "1", "army": 0}
    role = {"uid": str(uid), "level": int(p.get("level", 60)), "camp": 1, "armyType": _effective_army(st, int(getattr(st, "last_army", 0) or 0)), "vip": 0, "bAi": 0,
            "faceicon": int(p.get("faceicon", 0)), "faceframe": int(p.get("faceframe", 0)), "name": p["name"]}
    return ("matchRoomPrepareInfo", {"msgs": [{"mode": int(mode), "subMode": int(sub), "mapId": mid, "maxArmyClass": _max_army_class(),
                                               "roomId": "1", "roleInfos": [role]}]})


def join_match(req, st):
    """Tutorial (challenge-training -> start) sends {mode:1, process:N,...}; other single modes use the same route. Reply ok, then launch push [C keys, G behaviour]."""
    mode = int(req.get("mode", 1) or 1)
    sub = req.get("subMode", 0) or 0
    if isinstance(sub, list):                    # real client sends subMode as a list, e.g. [0]
        sub = sub[0] if sub else 0
    process = req.get("process", 1) or 1
    r = ok()
    if _prebattle_on(mode):
        pi = match_room_prepare_info(st, mode, sub, process)
        # the client runs the joinMatch callback (matching overlay) AFTER our push if both arrive together and the overlay hides the window -> delay [client log 02:32:23]
        r["_push_after"] = [(pi[0], pi[1], float(os.environ.get("TK_PREBATTLE_DELAY", "2.5")))]
    else:
        r["_push_after"] = [game_startup(st, mode, sub, process)]
    return r


def prepare_match_room(req, st):
    """Ready pressed (or the 50 s timer ended).  req {suit, armyid, roomId, usepvetoken}; resp {code, suit, armyid} [C keys]."""
    pb = getattr(st, "prebattle", None)
    army = _effective_army(st, int(req.get("armyid", 0) or 0))
    suit = int(req.get("suit", 0) or 0)
    r = ok(suit=suit, armyid=army)
    if pb is None:                               # no window was opened by us: just answer
        return r
    pb["army"] = army
    _save_prebattle(st, army, suit)
    try:
        uid = int(st.player["uid"])
    except Exception:
        uid = 10001
    r["_push_after"] = [("matchRoomPrepare", {"msgs": [{"armyid": army, "roomId": str(req.get("roomId", pb["roomId"])), "uid": str(uid)}]}),
                        game_startup(st, pb["mode"], pb["sub"], pb["process"], pb["map"], army=army)]
    return r


def req_role_prebattle_info(req, st):
    """Client sends {suit, armyid, hero1, hero2} when a troop is selected; remember it for the prepare window / gameStartup. Reply shape unknown -> {code:0}."""
    a = int(req.get("armyid", 0) or 0)
    if a and a in {int(x["id"]) for x in _playable_soldiers(st.player["soldiers"])}:
        st.last_army = a
    return ok()


def _save_prebattle(st, army, suit):
    """Hand-off for battle_server.py: server/data/last_prebattle.json = {armyid, suit, suit_row (equipment ids of that suit slot)}."""
    try:
        suits = st.player.get("suits") or []
        row = suits[suit] if 0 <= suit < len(suits) else {}
        with open(os.path.join(DATA_DIR, "last_prebattle.json"), "w", encoding="utf-8") as f:
            json.dump({"armyid": army, "suit": suit, "suit_row": row}, f)
    except Exception:
        pass


def chg_match_room_battle_info(req, st):
    """Troop/suit changed inside the window.  req {suit, armyid, roomId}; resp {code, suit, armyid} [C keys]."""
    pb = getattr(st, "prebattle", None)
    army = _effective_army(st, int(req.get("armyid", 0) or 0))
    if pb is not None:
        pb["army"] = army
    return ok(suit=int(req.get("suit", 0) or 0), armyid=army)


def create_pve_battle(req, st):               # req {itemid, zone}  resp {code, mapid, degree, roomId}
    return ok(mapid=1, degree=1, roomId="1")


def start_pve_battle(req, st):
    r = ok()
    r["_push_after"] = [game_startup(st, 6, 0, 1)]
    return r


def custom_start_game(req, st):               # only reachable once a custom room exists (createCustomRoom is not implemented)
    r = ok()
    r["_push_after"] = [game_startup(st, 1, 0, 1)]
    return r


def set_tutorial(req, st):                    # resp {code, tutorial}
    return ok(tutorial=max(int(req.get("tutorial", 5) or 5), 5))


def empty_ok(req, st):
    return ok()


# ---------------------------------------------------------------- THE ROUTE TABLE  (route -> function)
ROUTES = {
    # login [C]
    "connector.entryHandler.auth": auth,
    "connector.entryHandler.entry": entry,
    "connector.entryHandler.queryServerTime": query_server_time,
    "connector.entryHandler.heartbeat": empty_ok,
    # core data [C schema]
    "userstate.userHandler.getRoleState": get_role_state,
    "userstate.userHandler.newUser": new_user,
    "userstate.userHandler.checkNickName": check_nick_name,
    "userstate.userHandler.useChangeFaceCard": use_change_face_card,
    "userstate.userHandler.getSelfInfo": get_self_info,
    "userstate.userHandler.setHelpPanel": set_help_panel,
    "userstate.userHandler.loadPropBar": load_prop_bar,
    "userstate.userHandler.loadRoleSuit": load_role_suit,
    "userstate.assetsHandler.queryAllAssets": query_all_assets,
    # chat [G]
    "userstate.userHandler.joinChatChannel": join_chat_channel,
    "userstate.userHandler.getChatConnectorsInfo": get_chat_connectors_info,
    "userstate.chatHandler.getChannelInfo": chat_channel_info,
    "userstate.chatHandler.changeChannel": empty_ok,
    "userstate.chatHandler.channelChat": empty_ok,
    "userstate.chatHandler.privateChat": empty_ok,
    "userstate.chatHandler.privateChannelChat": empty_ok,
    "userstate.chatHandler.leavePrivateChannel": empty_ok,
    "userstate.chatHandler.FriendTalk": empty_ok,
    "userstate.chatHandler.rtChatByName": empty_ok,
    # restore [C schema]
    "userstate.matchHandler.restore": match_restore,
    # paged lists: one empty final page [G]
    "userstate.userHandler.loadRoleItem": load_role_item,
    "userstate.userHandler.reqStoreInfo": req_store_info,
    "userstate.emailHandler.loadRoleEmail": load_role_email,
    "userstate.userHandler.loadTechInfo": paged_empty,
    "userstate.userHandler.loadRoleTask": load_role_task,
    # login-time extras that used to fall through to {"code":0}
    "userstate.userHandler.getSignInInfo": get_sign_in_info,
    "userstate.userHandler.getOnlineInfo": get_online_info,
    "userstate.userHandler.queryVipBuySort": query_vip_buy_sort,
    "userstate.chargeHandler.getList": charge_get_list,
    "userstate.userHandler.getBattleProfitMultiInfo": get_battle_profit_multi_info,
    "userstate.userHandler.loadStoreBuyLimit": load_store_buy_limit,
    # init chain after getSelfInfo (frontend LoadLoginMsg steps 5..23, see notes/lobby/login_flow.md) [C schemas]
    "userstate.userHandler.getRoleEquipment": get_role_equipment,
    "userstate.userHandler.getSoldier": get_soldier,
    "userstate.userHandler.loadRoleAssistant": load_role_assistant,
    "userstate.friendHandler.enumerateFriends": enumerate_friends,
    "userstate.friendHandler.getBlackList": get_black_list,
    "userstate.userHandler.getRankOpenInfo": get_rank_open_info,
    "userstate.userHandler.queryScienceTypeOpenInfo": query_science_type_open_info,
    # tech tree / soldier actions
    "userstate.userHandler.openRank": open_rank,
    "userstate.userHandler.openScience": open_science,
    "userstate.userHandler.buySoldier": buy_soldier,
    "userstate.userHandler.sellSoldier": sell_soldier,
    "userstate.userHandler.operArmyAttr": oper_army_attr,
    "userstate.userHandler.exchRoleEquipment": exch_role_equipment,
    "userstate.userHandler.increaseRoleSuit": increase_role_suit,
    "userstate.userHandler.recruitRoleAssistant": recruit_role_assistant,
    "userstate.userHandler.forwardRoleAssistant": forward_role_assistant,
    "userstate.userHandler.employRoleAssistant": ack_logged("employRoleAssistant"),
    "userstate.userHandler.dismissRoleAssistant": ack_logged("dismissRoleAssistant"),
    "userstate.userHandler.buyRoleEquipment": buy_role_equipment,
    "userstate.userHandler.buySoldierEquipment": buy_soldier_equipment,
    "userstate.userHandler.getSoldierEquipment": get_soldier_equipment,
    "userstate.userHandler.queryPerfectRankInfo": query_perfect_rank_info,
    "userstate.matchHandler.queryMatchModeTime": query_match_mode_time,
    "userstate.matchHandler.reqChallengeBaseInfo": req_challenge_base_info,
    "userstate.syndicateHandler.getSynInfo": get_syn_info,
    # battle launch
    "userstate.matchHandler.joinMatch": join_match,
    "userstate.matchHandler.prepareMatchRoom": prepare_match_room,
    "userstate.userHandler.reqRolePreBattleInfo": req_role_prebattle_info,   # client sends it when a troop is selected {suit,armyid,hero1,hero2}; reply shape unknown
    "userstate.matchHandler.chgMatchRoomBattleInfo": chg_match_room_battle_info,
    "userstate.matchHandler.createPveBattle": create_pve_battle,
    "userstate.matchHandler.startPveBattle": start_pve_battle,
    "userstate.customRoomHandler.startGame": custom_start_game,
    "userstate.matchHandler.clientStartGameFail": empty_ok,
    "userstate.matchHandler.leaveMatch": empty_ok,
    "userstate.matchHandler.queryCrusadeMatchPunish": empty_ok,
    "userstate.userHandler.setTutorial": set_tutorial,
    # everything else: not listed -> UNHANDLED log + {"code": UNKNOWN_CODE}
}

# Plain Traditional Chinese one-liners for the user's console. route -> (request text, reply text)
FRIENDLY = {
    "connector.entryHandler.auth": ("收到登入請求", "已回覆登入成功"),
    "connector.entryHandler.entry": ("收到進入遊戲請求", "已回覆進入遊戲成功"),
    "connector.entryHandler.queryServerTime": ("收到伺服器時間請求", "已回覆伺服器時間"),
    "userstate.userHandler.getRoleState": ("收到角色狀態請求", "已回覆角色狀態（跳過新手教學）"),
    "userstate.userHandler.getSelfInfo": ("收到玩家資料請求", "已回覆玩家資料"),
    "userstate.userHandler.loadPropBar": ("收到道具欄請求", "已回覆道具欄（空）"),
    "userstate.userHandler.loadRoleSuit": ("收到裝備套裝請求", "已回覆裝備套裝"),
    "userstate.userHandler.exchRoleEquipment": ("收到穿脫裝備請求", "已記錄裝備並推送 updateRoleEquip"),
    "userstate.userHandler.recruitRoleAssistant": ("收到招募副將請求", "已加入副將並推送 updateHero"),
    "userstate.assetsHandler.queryAllAssets": ("收到資產請求", "已回覆資產（空）"),
    "userstate.userHandler.joinChatChannel": ("收到加入聊天頻道請求", "已回覆聊天頻道"),
    "userstate.userHandler.getChatConnectorsInfo": ("收到聊天伺服器資訊請求", "已回覆聊天伺服器資訊"),
    "userstate.matchHandler.restore": ("收到戰鬥恢復請求", "已回覆（沒有可恢復的戰鬥）"),
    "userstate.matchHandler.joinMatch": ("收到「出戰」請求", "已回覆成功，並通知遊戲啟動戰鬥程式（連到 127.0.0.1:7777）"),
    "userstate.matchHandler.startPveBattle": ("收到開始PVE戰鬥請求", "已回覆成功，並通知遊戲啟動戰鬥程式"),
    "userstate.userHandler.setHelpPanel": ("收到教學提示已讀", "已記錄"),
}

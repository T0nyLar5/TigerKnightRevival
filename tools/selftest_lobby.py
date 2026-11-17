# -*- coding: utf-8 -*-
"""Self-test for server/lobby.py. Start lobby.py first (default 127.0.0.1:3015), then:
   tools\\.venv\\Scripts\\python.exe -I tools\\selftest_lobby.py [port]
Exit code 0 = all checks passed."""
import json
import socket
import ssl
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3015


def pkg(t, b=b""):
    return bytes([t]) + len(b).to_bytes(3, "big") + b


def varint(v):
    out = bytearray()
    while True:
        b = v & 0x7f
        v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v:
            return bytes(out)


class Client:
    def __init__(self):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        self.s = ctx.wrap_socket(socket.create_connection(("127.0.0.1", PORT)), server_hostname="front1-hk.tk.99.com")
        self.s.settimeout(5)
        self.buf = b""
        self.id = 0

    def read_pkg(self):
        while True:
            if len(self.buf) >= 4:
                n = int.from_bytes(self.buf[1:4], "big")
                if len(self.buf) >= 4 + n:
                    t, body = self.buf[0], self.buf[4:4 + n]
                    self.buf = self.buf[4 + n:]
                    return t, body
            d = self.s.recv(65536)
            if not d:
                raise EOFError("server closed")
            self.buf += d

    def request(self, route, body):
        self.id += 1
        r = route.encode()
        self.s.sendall(pkg(4, bytes([0]) + varint(self.id) + bytes([len(r)]) + r + json.dumps(body).encode()))
        self.pushes = []
        while True:
            t, b = self.read_pkg()
            assert t == 4, "expected data package, got %d" % t
            if b[0] >> 1 == 3:                       # server push: [flag][routelen][route][json]
                rl = b[1]
                self.pushes.append((b[2:2 + rl].decode(), json.loads(b[2 + rl:].decode("utf-8"))))
                continue
            break
        assert b[0] >> 1 == 2, "expected response"
        rid, off, shift = 0, 1, 0
        while True:
            m = b[off]
            off += 1
            rid |= (m & 0x7f) << shift
            shift += 7
            if not m & 0x80:
                break
        assert rid == self.id, "response id %d != %d" % (rid, self.id)
        return json.loads(b[off:].decode("utf-8"))


fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + str(info) if info else ""))
    if not cond:
        fails.append(name)


c = Client()
c.s.sendall(pkg(1, json.dumps({"sys": {"type": "desktop", "version": "0.3.5-release"}}).encode()))
t, b = c.read_pkg()
hs = json.loads(b)
check("handshake", t == 1 and hs.get("code") == 200 and hs["sys"]["heartbeat"] == 10, hs)
c.s.sendall(pkg(2))
c.s.sendall(pkg(3))
t, b = c.read_pkg()
check("heartbeat reply", t == 3)

r = c.request("connector.entryHandler.auth", {"name": "10000000000000001", "psw": "ab" * 40, "type": "steam", "version": "1.1.111"})
check("auth code 0, one account", r["code"] == 0 and len(r["accounts"]) == 1 and r["accounts"][0]["tp"] == "hk", r)
uid = r["accounts"][0]["uid"]
r = c.request("connector.entryHandler.entry", {"uid": uid, "name": "10000000000000001", "psw": "x", "type": "steam", "version": "1.1.111"})
check("entry", r["code"] == 0 and r["restore"] is False and r["csid"] == 1 and r["chatnum"] == [0], r)
r = c.request("userstate.userHandler.getRoleState", {})
check("getRoleState tutorialStep>=4", r["code"] == 0 and r["tutorialStep"] >= 4, r)
r = c.request("userstate.userHandler.getSelfInfo", {})
check("getSelfInfo", r["code"] == 0 and r["info"]["level"] >= 1 and r["info"]["name"], r["info"]["name"])
# Shape rules learnt from the 2026-11-04 crash (notes/crash/analysis.md): the DLL indexes INTO these, so a scalar crashes the client.
info = r["info"]
check("getSelfInfo.forbidmatch is object {forbid,outTime}", isinstance(info.get("forbidmatch"), dict)
      and "forbid" in info["forbidmatch"] and "outTime" in info["forbidmatch"], info.get("forbidmatch"))
check("getSelfInfo.pveinfo is object", isinstance(info.get("pveinfo"), dict))
check("getSelfInfo.tutorialAward = 5 bools", isinstance(info["tutorialAward"], list) and len(info["tutorialAward"]) == 5
      and all(isinstance(x, bool) for x in info["tutorialAward"]))
check("getSelfInfo.soldierexp rows {country,stage,exp}, <=20, countries 1-3",
      isinstance(info["soldierexp"], list) and 3 <= len(info["soldierexp"]) <= 20
      and all(isinstance(e, dict) and {"country", "stage", "exp"} <= set(e) for e in info["soldierexp"])
      and {e["country"] for e in info["soldierexp"]} >= {1, 2, 3})
check("getSelfInfo.faces = 56 uints (DLL loop cmp 0x38)", len(info["faces"]) == 56)
r = c.request("connector.entryHandler.queryServerTime", {})
check("queryServerTime", r.get("ServerTime", 0) > 1.7e9, r)
for route, key in (("userstate.userHandler.loadPropBar", "propbar"), ("userstate.userHandler.loadRoleSuit", "suits"),
                   ("userstate.assetsHandler.queryAllAssets", "assets"), ("userstate.userHandler.loadRoleItem", "items"),
                   ("userstate.userHandler.getChatConnectorsInfo", "chatDegree"), ("userstate.userHandler.joinChatChannel", "host")):
    r = c.request(route, {})
    check(route.split(".")[-1], r["code"] == 0 and key in r, r)
# routes that used to get a bare {"code":0}; value = (key, type that must be an array / object / absent-of-scalars)
r = c.request("userstate.userHandler.getSignInInfo", {})
check("getSignInInfo", r["code"] == 0 and r["signinreward"] == [] and "singninCount" in r, r)
r = c.request("userstate.userHandler.getOnlineInfo", {})
check("getOnlineInfo", r["code"] == 0 and {"onlinedate", "onlinetime", "onlinehadreward"} <= set(r), r)
r = c.request("userstate.userHandler.queryVipBuySort", {})
check("queryVipBuySort", isinstance(r["vipBuySorts"], list) and all({"days", "gold", "rebate"} <= set(x) for x in r["vipBuySorts"]), r)
r = c.request("userstate.chargeHandler.getList", {})
check("chargeHandler.getList", r["code"] == 0 and r["data"] == [], r)
r = c.request("userstate.userHandler.getBattleProfitMultiInfo", {})
check("getBattleProfitMultiInfo", r["code"] == 0 and r["data"] == [], r)
r = c.request("userstate.userHandler.loadStoreBuyLimit", {})
check("loadStoreBuyLimit (fleebox object)", r["code"] == 0 and r["limitinfo"] == [] and isinstance(r["fleebox"], dict)
      and {"buycnt", "buytime"} <= set(r["fleebox"]), r)
for route, keys in (("userstate.emailHandler.loadRoleEmail", ("curDaySend", "isfinal", "serieNum")),
                    ("userstate.userHandler.reqStoreInfo", ("version", "isfinal", "serieNum")),
                    ("userstate.userHandler.loadRoleItem", ("capacity", "isfinal", "serieNum")),
                    ("userstate.userHandler.loadRoleTask", ("dailyTasks", "dailyRefreshCount", "limittimeTasks", "commonTasks")),
                    ("userstate.userHandler.loadTechInfo", ("code",))):
    r = c.request(route, {})
    check(route.split(".")[-1] + " keys", r.get("code", 0) == 0 and all(k in r for k in keys), r)
r = c.request("userstate.userHandler.joinChatChannel", {})
check("joinChatChannel uint fields are ints", all(isinstance(r[k], int) for k in ("channel", "port", "degree", "token")) and isinstance(r["host"], str), r)
r = c.request("userstate.matchHandler.restore", {})
check("matchHandler.restore", r["code"] == 0 and "addr" in r)
# init chain after getSelfInfo (frontend steps 5..23): rank reply MUST echo nation or the loading screen sticks
r = c.request("userstate.userHandler.getRoleEquipment", {})
check("getRoleEquipment equiplst array", r["code"] == 0 and isinstance(r["equiplst"], list), r)
r = c.request("userstate.userHandler.getSoldier", {"serieNum": 1})
check("getSoldier isfinal+serieNum", r["code"] == 0 and r["isfinal"] == 1 and r["serieNum"] == 1, r)
r = c.request("userstate.userHandler.loadRoleAssistant", {})
check("loadRoleAssistant heros array", r["code"] == 0 and isinstance(r["heros"], list), r)
r = c.request("userstate.friendHandler.enumerateFriends", {})
check("enumerateFriends arrays", r["code"] == 0 and r["friendsInfo"] == [] and r["freqs"] == [], r)
for nation in (1, 2, 3, 5, 8, 999):
    r = c.request("userstate.userHandler.getRankOpenInfo", {"nation": nation, "serieNum": 1})
    check("getRankOpenInfo echoes nation %d" % nation, r["code"] == 0 and r["nation"] == nation and r["isfinal"] == 1, r)
r = c.request("userstate.friendHandler.getBlackList", {})
check("getBlackList", r["code"] == 0 and r["list"] == [], r)
r = c.request("userstate.userHandler.queryScienceTypeOpenInfo", {"serieNum": 1})
check("queryScienceTypeOpenInfo", r["code"] == 0 and r["isfinal"] == 1, r)
r = c.request("userstate.matchHandler.queryMatchModeTime", {})
check("queryMatchModeTime modes array", r["modes"] == [], r)
r = c.request("userstate.matchHandler.reqChallengeBaseInfo", {})
check("reqChallengeBaseInfo arrays", all(r[k] == [] for k in ("proficiency", "firstcomplete", "topscore")), r)
r = c.request("userstate.syndicateHandler.getSynInfo", {})
check("getSynInfo data/flag are objects", isinstance(r["data"], dict) and isinstance(r["data"]["flag"], dict), r)
# ---- unlocked-state checks (player.json produced by tools/unlock_all.py); pushes carry the paged rows ----
import os
pj = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server", "data", "player.json"), encoding="utf-8"))
if pj.get("ranks"):
    r = c.request("userstate.userHandler.getSelfInfo", {})
    se = r["info"]["soldierexp"]
    check("soldierexp <=20 rows, all exp>=99999999", 1 <= len(se) <= 20 and all(e["exp"] >= 99999999 for e in se), len(se))
    check("currencies maxed (uint32 safe)", r["info"]["gold"] == 99999999 and r["info"]["copper"] == 99999999
          and r["info"]["generalexp"] == 99999999 and r["info"]["jade"] == 99999999 and r["info"]["gold"] < 2 ** 31)
    for nation in (1, 2, 3, 5, 8, 999):
        r = c.request("userstate.userHandler.getRankOpenInfo", {"nation": nation, "serieNum": 1})
        pg = [b for rt, b in c.pushes if rt == "getRankOpenInfo"]
        rows = [x for b in pg for x in b["items"]]
        check("rank push nation %d" % nation, r["nation"] == nation and rows and all(x["nation"] == nation and isinstance(x["rank"], int) for x in rows)
              and pg[-1]["isfinal"] == 1, len(rows))
    r = c.request("userstate.userHandler.queryScienceTypeOpenInfo", {"serieNum": 1})
    pg = [b for rt, b in c.pushes if rt == "queryScienceTypeOpenInfo"]
    ids = [x for b in pg for x in b["items"]]
    check("science push: paged uint ids, last page isfinal", len(ids) > 500 and all(isinstance(x, int) for x in ids)
          and pg[-1]["isfinal"] == 1 and all(b["isfinal"] == 0 for b in pg[:-1]), (len(pg), len(ids)))
    r = c.request("userstate.userHandler.openRank", {"rankid": 123, "prerank": 122})
    check("openRank echo", r == {"code": 0, "rank": 123}, r)
    r = c.request("userstate.userHandler.openScience", {"scitechid": 10101, "scitechtype": 2})
    check("openScience echo", r["code"] == 0 and r["scitechid"] == 10101 and r["scitechtype"] == 2, r)
    check("openScience pushes openTechType (clears the NormalWaiting overlay)", any(x[0] == "openTechType" and x[1].get("techlist") == [{"techid": 10101, "techtype": 2}] for x in c.pushes), c.pushes)
    r = c.request("userstate.userHandler.exchRoleEquipment", {"command": [{"itemid": "1256", "pos": 14, "suit": 0}]})
    check("exchRoleEquipment pushes updateRoleEquip", r == {"code": 0} and any(x[0] == "updateRoleEquip" and x[1]["suits"] == [{"itemid": "1256", "suit": 0, "pos": 14}] for x in c.pushes), (r, c.pushes))
    r = c.request("userstate.userHandler.loadRoleSuit", {})
    check("loadRoleSuit returns equipped item (all keys str)", r["suits"][0]["fashion"] == "1256" and all(isinstance(v, str) for v in r["suits"][0].values()), r)
    r = c.request("userstate.userHandler.exchRoleEquipment", {"command": [{"itemid": "", "pos": 14, "suit": 0}]})
    r = c.request("userstate.userHandler.loadRoleSuit", {})
    check("unequip clears slot", "fashion" not in r["suits"][0], r)
    r = c.request("userstate.userHandler.recruitRoleAssistant", {"assistantid": 803000, "data": 0})
    check("recruitRoleAssistant pushes updateHero", r.get("code") == 0 and any(x[0] == "updateHero" and x[1]["hero"]["id"] == 803000 for x in c.pushes), (r, c.pushes))
    r = c.request("userstate.userHandler.buySoldier", {"armyid": 101006})
    check("buySoldier + establishArmy push", r == {"code": 0, "armyid": 101006} and c.pushes and c.pushes[0][0] == "establishArmy"
          and c.pushes[0][1]["soldiers"][0]["id"] == 101006 and len(c.pushes[0][1]["soldiers"][0]) == 27, c.pushes)
    r = c.request("userstate.userHandler.getSoldier", {"serieNum": 1})
    pg = [b for rt, b in c.pushes if rt == "getSoldier"]
    check("getSoldier pushes owned row", r["isfinal"] == 1 and pg and pg[-1]["items"][-1]["id"] == 101006, r)
    r = c.request("userstate.userHandler.sellSoldier", {"armyid": 101006})
    check("sellSoldier", r == {"code": 0, "armyid": 101006}, r)
    for route, body, key in (("operArmyAttr", {"armyid": 1, "opertype": 2, "data": 3}, "opertype"),
                             ("buyRoleEquipment", {"scitechtype": 1, "equiptype": 2}, "equiptype"),
                             ("buySoldierEquipment", {"scitechid": 1, "equiptype": 2}, "equiptype"),
                             ("getSoldierEquipment", {"rank": 101}, "equiplst"), ("queryPerfectRankInfo", {}, "rankinfo")):
        r = c.request("userstate.userHandler." + route, body)
        check(route, r["code"] == 0 and key in r, r)
# ---- Part 1: help panels / max level
check("getSelfInfo.helpPanel marks all panels seen (bits 1-4)", info["helpPanel"] & 0xF == 0xF, info["helpPanel"])
check("getSelfInfo level 60 + big experience", info["level"] == 60 and info["experience"] >= 1000000, (info["level"], info["experience"]))
check("auth account level 60", c.request("connector.entryHandler.auth", {"name": "10000000000000001", "psw": "x", "type": "steam", "version": "1.1.111"})["accounts"][0]["level"] == 60)
for v in (1, 2, 4, 8):
    r = c.request("userstate.userHandler.setHelpPanel", {"val": v})
    check("setHelpPanel val=%d -> {code:0}" % v, r == {"code": 0}, r)
r = c.request("userstate.userHandler.getSelfInfo", {})
check("helpPanel stays full after setHelpPanel", r["info"]["helpPanel"] & 0xF == 0xF)
# ---- Part 2: battle launch push (arrives AFTER the response)
def after_push():
    t, b = c.read_pkg()
    assert t == 4 and b[0] >> 1 == 3, "expected push"
    rl = b[1]
    return b[2:2 + rl].decode(), json.loads(b[2 + rl:].decode("utf-8"))


def check_startup(name, route, body, mode):
    r = c.request(route, body)
    check(name + " response code 0", r["code"] == 0, r)
    if r["code"] != 0:
        return
    rt, pb = after_push()
    m = pb["msgs"][0] if rt == "gameStartup" else {}
    check(name + " -> gameStartup push to 127.0.0.1:7777", rt == "gameStartup" and m.get("addr") == [{"ip": "127.0.0.1", "port": 7777}]
          and m.get("gameMode") == mode and m["playerInfos"][0]["roleId"] == uid and m["playerId"] == int(uid)
          and all(isinstance(m[k], int) for k in ("process", "subMode", "gameMode", "token", "playerId", "camp", "mapId")), pb)
    print("   push:", json.dumps(pb))


check_startup("joinMatch tutorial", "userstate.matchHandler.joinMatch", {"mode": 1, "process": 1, "halfwayjoin": False, "zone": 0, "direct": False}, 1)
# ---- pre-battle troop window (joinMatch mode 2 -> matchRoomPrepareInfo -> prepareMatchRoom -> matchRoomPrepare + gameStartup)
r = c.request("userstate.matchHandler.joinMatch", {"mode": 2, "process": 1, "subMode": [4]})
check("joinMatch mode2 response code 0", r["code"] == 0, r)
rt, pb = after_push()
mi = pb["msgs"][0] if pb.get("msgs") else {}
check("joinMatch mode2 -> matchRoomPrepareInfo (window), no gameStartup yet", rt == "matchRoomPrepareInfo" and mi.get("mode") == 2
      and mi.get("subMode") == 4 and mi.get("roomId") and mi["roleInfos"][0]["uid"] == uid and isinstance(mi["roomId"], str) and isinstance(mi.get("mapId"), int), pb)
r = c.request("userstate.matchHandler.prepareMatchRoom", {"suit": 0, "armyid": 812001, "roomId": "1", "usepvetoken": 0})
check("prepareMatchRoom reply {code,suit,armyid}", r.get("code") == 0 and r.get("armyid") == 812001 and "suit" in r, r)
rt, pb = after_push()
check("then push matchRoomPrepare {armyid,roomId,uid}", rt == "matchRoomPrepare" and pb["msgs"][0].get("armyid") == 812001 and pb["msgs"][0].get("uid") == uid, pb)
rt, pb = after_push()
check("then push gameStartup with playerInfos[0].armyType = 812001, gameMode 2, subMode 4", rt == "gameStartup" and pb["msgs"][0]["gameMode"] == 2
      and pb["msgs"][0]["subMode"] == 4 and pb["msgs"][0]["playerInfos"][0]["armyType"] == 812001, pb)
r = c.request("userstate.matchHandler.chgMatchRoomBattleInfo", {"suit": 0, "armyid": 812002, "roomId": "1"})
check("chgMatchRoomBattleInfo reply", r.get("code") == 0 and r.get("armyid") == 812002, r)
r = c.request("userstate.matchHandler.createPveBattle", {"itemid": 0, "zone": 0})
check("createPveBattle reply", r["code"] == 0 and "mapid" in r and "roomId" in r, r)
check_startup("startPveBattle", "userstate.matchHandler.startPveBattle", {}, 6)
r = c.request("some.unknown.route", {"x": 1})
check("unknown route -> code 0", r == {"code": 0}, r)
c.s.close()
print("\nALL PASSED" if not fails else "\nFAILED: %s" % fails)
sys.exit(1 if fails else 0)

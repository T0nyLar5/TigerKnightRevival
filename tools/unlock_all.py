# -*- coding: utf-8 -*-
r"""unlock_all.py [--game-dir DIR] [--dry]  -- write the "everything unlocked" state into server/data/player.json.

Backs up the current player.json to server/data/backups/player_<timestamp>.json first, then updates it in place.
Run:  tools\.venv\Scripts\python.exe -I tools\unlock_all.py

ID sources (the game's real tables rank_tree/armytype/fujiang/itemtype live in the encrypted config.cfg, NOT cracked):
  * rank ids  = file names of frontend/bin/data/TechTreeData/<id>.zqk  (1xx Wei=nation 1, 2xx Shu=2, 3xx Wu=3, 5xx Roman=5, 8xx Special=8, 999 exploit)
  * tech ids  = ids >= 1000 inside those .zqk files, with their 3rd column as tech type [G for the meaning of the type]
  * currencies are uint32 in the DLL parser (asUInt); 99,999,999 fits
Soldier (armytype) / hero / item ids are unknown, so those lists are NOT pre-filled; buying through the tech tree is accepted
by the server and stored (handlers.py buySoldier etc.).
"""
import argparse
import json
import os
import re
import shutil
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYER = os.path.join(ROOT, "server", "data", "player.json")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight"
BIG = 99999999
MAX_LEVEL = 60
ALL_ITEMS = False
MAX_EXP = 999999999
NATIONS = (1, 2, 3, 4, 5, 8)      # ENationType: Wei Shu Wu xiliang Roman Special
STAGES = (1, 2, 3)                # ERankStage 1..3 (low/mid/high)


def nation_of(rank):
    if rank == 999:
        return 999
    return rank // 100


def read_tree_data(game_dir):
    d = os.path.join(game_dir, "frontend", "bin", "data", "TechTreeData")
    ranks, techs = {}, {}
    for fn in sorted(os.listdir(d)):
        m = re.fullmatch(r"(\d+)\.zqk", fn)
        if not m:
            continue
        rank = int(m.group(1))
        ranks.setdefault(nation_of(rank), []).append(rank)
        with open(os.path.join(d, fn), "r", encoding="utf-8", errors="replace") as f:
            txt = f.read()
        body = txt.split("[Head_end]", 1)[-1]
        for line in body.splitlines():
            nums = [t for t in re.split(r"\s+", line.replace("@", " ")) if t.isdigit()]
            for i in range(0, len(nums) - 2, 3):
                tid, _lvl, ttype = int(nums[i]), int(nums[i + 1]), int(nums[i + 2])
                if tid >= 1000:
                    techs[tid] = ttype
    return ranks, techs


CFG = os.path.join(ROOT, "notes", "decrypted", "cfg", "frontend_config", "config")


def read_table(name):
    """Decrypted cfg table (tools/cfgdec.py): line 1 = column names, line 2 = types, line 3 = comments. -> list of dicts (str values)."""
    fn = os.path.join(CFG, name + ".txt")
    if not os.path.exists(fn):
        return []
    with open(fn, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.read().split(chr(10))
    cols = lines[0].rstrip(chr(13)).split(chr(9))
    rows = []
    for ln in lines[3:]:
        ln = ln.rstrip(chr(13))
        if not ln.strip():
            continue
        v = ln.split(chr(9))
        v += [""] * (len(cols) - len(v))
        rows.append(dict(zip(cols, v)))
    return rows


def num(x, d=0):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return d


def build_everything(p):
    """Soldiers (armytype), heroes (hero_type), bag items (itemtype), science nodes (science_tree), role equipment (science_type)."""
    stats = {}
    # soldiers: keep any rows the server already stored (buySoldier), add the rest with empty equipment (the safe layout the client accepted)
    from_srv = {x["id"]: x for x in p.get("soldiers", []) if isinstance(x, dict) and "id" in x}
    rows = list(from_srv.values())
    seq = max([x.get("sequence", 0) for x in rows] + [0])
    valid = {num(r.get("army_type")) for r in read_table("rank_tree")} - {0}      # soldier ids the tech tree knows (have art)
    for a in read_table("armytype"):
        aid = num(a.get("id"))
        if aid in (999999, 812012) or (valid and aid not in valid):      # 999999 dummy row, 812012 氐人團 has no art (user saw blank card) ; 999999 = dummy row (no art -> broken thumbnail)
            continue
        if aid and aid not in from_srv:
            seq += 1
            rows.append({"id": aid, "amount": num(a.get("recruit_limit"), 20), "sequence": seq, "exp": 0, "helmet": 0, "shoes": 0,
                         "armor": 0, "shawl": 0, "horse": 0, "saddle": 0, "hoof": 0, "strike": 0, "horseadd": 0, "weapon1": 0,
                         "weapon2": 0, "weapon3": 0, "weapon4": 0, "fashion": 0, "skill1": 0, "skill2": 0, "skill3": 0, "skill4": 0,
                         "skill5": 0, "skill6": 0, "skill7": 0, "skill8": 0, "lastwinTime": 0})
    rows = [x for x in rows if x["id"] != 999999]
    if rows:
        p["soldiers"] = rows
    stats["soldiers"] = len(p.get("soldiers", []))
    # heroes (loadRoleAssistant row layout from the DLL; coat/flag semantics are a best guess)
    # lieutenants (fujiang ids, loadRoleAssistant rows): NOT pre-owned. The client lists every fujiang as "not owned" and the buy
    # flow (recruitRoleAssistant -> push updateHero) adds the row; pre-owning all made purchases invisible [G].
    p.setdefault("heroes", [])   # keep lieutenants already bought in-game
    # DLC / gift-pack-only lieutenants (高顺 101014, 孙尚香 303014, 大乔 303024, 马克里努斯 501005): 101014 and 303024 are NOT in hero_type
    # (no shop entry) and the others are gift-pack items (lua_config/giftpackage.lua), so the shop never lists them. Pre-own them.
    for _hid in (101014, 303014, 303024, 501005):
        if not any(h["id"] == _hid for h in p["heroes"]):
            p["heroes"].append({"id": _hid, "exp": 0, "coatmask": 15, "haveflag": True, "idcoat": 0, "timevalid": 0, "loyalty": 100, "forwardhero": 0})
    stats["heroes"] = len(p.get("heroes", []))
    # bag: MERGE (existing rows such as bought items are kept). Default = equipment only (known-good subset, 170).
    # --all-items (ALL_ITEMS) = every plain item (itemtype.type == 0: equipment, horses, consumables, cosmetics ...); stackables x99.
    # Gift packs (type 1-4) are left out: opening them would be a server feature.
    items = [x for x in p.get("items", []) if isinstance(x, dict)]
    have = {x.get("type") for x in items}
    nid = max([num(x.get("id")) for x in items] + [0])
    added = 0
    for it in read_table("itemtype"):
        iid = num(it.get("id"))
        if not iid or num(it.get("type")) != 0 or iid in have:
            continue
        is_equip = it.get("Position", "").strip() not in ("", "0")
        if not is_equip and not ALL_ITEMS:
            continue
        nid += 1
        added += 1
        have.add(iid)
        items.append({"id": str(nid), "type": iid, "uid": "10001", "endurance": 100 if is_equip else 0,
                      "num": 1 if is_equip else 99, "timeout": 0, "commonused": 0})
    p["items"] = items
    stats["items_added"] = added
    stats["items"] = len(p.get("items", []))
    # science nodes: every science_tree row (id + its science_type id); merged with the zqk ids by main()
    sci = {}
    for r in read_table("science_tree"):
        sid = num(r.get("id"))
        if sid:
            sci[sid] = num(r.get("type"))
    stats["science_tree_rows"] = len(sci)
    # role equipment (getRoleEquipment equiplst = equipment item ids): every sci_type 1 (equipment) entry's sci_id
    equip_ids = {num(r.get("id")) for r in read_table("itemtype") if r.get("Position", "").strip() not in ("", "0")}
    eq = sorted({num(r.get("sci_id")) for r in read_table("science_type") if num(r.get("sci_type")) == 1 and num(r.get("sci_id"))})
    eq = [e for e in eq if e in {num(r.get("id")) for r in read_table("itemtype")}]      # drop ids missing from itemtype (e.g. 17000001)
    if eq:
        p["equiplst"] = eq
    stats["role_equipment"] = len(p.get("equiplst", []))
    return sci, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-dir", default=GAME)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--all-items", action="store_true", help="put every plain itemtype row (type 0) into the bag, stackables x99")
    a = ap.parse_args()
    global ALL_ITEMS
    ALL_ITEMS = a.all_items
    p = json.load(open(PLAYER, "r", encoding="utf-8")) if os.path.exists(PLAYER) else {}
    ranks, techs = read_tree_data(a.game_dir)
    if not a.dry and os.path.exists(PLAYER):
        bdir = os.path.join(os.path.dirname(PLAYER), "backups")
        os.makedirs(bdir, exist_ok=True)
        b = os.path.join(bdir, "player_%s.json" % time.strftime("%Y%m%d_%H%M%S"))
        shutil.copy2(PLAYER, b)
        print("backup ->", b)
    for k in ("gold", "copper", "generalexp", "exploit", "jade", "fleecoin"):
        p[k] = BIG
    p["level"] = MAX_LEVEL      # Lua BattleSettlement clamps display at "Lv60" for level>=61 -> max = 60
    p["experience"] = MAX_EXP   # role_levexp table is in encrypted config.cfg; large value keeps the bar full
    p["helpPanel"] = 0xFFFF     # all help-panel bits seen (Lua uses stages 1-4)
    p["ranks"] = {str(n): v for n, v in sorted(ranks.items())}
    sci, stats = build_everything(p)
    merged = dict(sci)
    for i, t in techs.items():
        merged.setdefault(i, t)          # zqk-only ids keep the zqk "type" column
    p["sciences"] = [{"id": i, "type": t} for i, t in sorted(merged.items())]
    print("everything:", stats, "sciences:", len(p["sciences"]))
    p["soldierexp"] = [{"country": c, "stage": s, "exp": BIG} for c in NATIONS for s in STAGES]
    p.setdefault("soldiers", [])      # owned soldier rows (all armytype ids via build_everything)
    p.setdefault("heroes", [])        # owned hero rows (all hero_type ids)
    p.setdefault("equiplst", [])      # role equipment ids
    p.setdefault("items", [])
    p.setdefault("soldier_equip", {}) # rank -> [equip tech ids]
    print("ranks:", {n: len(v) for n, v in ranks.items()}, "techs:", len(techs))
    if not a.dry:
        tmp = PLAYER + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, indent=2)
        os.replace(tmp, PLAYER)
        print("wrote", PLAYER)


if __name__ == "__main__":
    main()

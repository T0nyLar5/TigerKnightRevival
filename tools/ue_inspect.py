r"""UE3 runtime inspector for Tiger Knight (Win64). Finds the hero Pawn through the object table (no position scan).
Usage: tools\.venv\Scripts\python.exe -I tools\ue_inspect.py [--fix] [--static] [--selftest] [--watch] [--props] [--exp]
  --watch    option 4: state names, PlayerInput axes, Acceleration/Velocity sampled every 0.25 s for 8 s while the user holds W
  --exp      option 6: write SyncVelocity/SyncAccelerate to the hero for 5 s and watch Location
  --time     option 7: time dilation / Base / HardAttach / WorldInfo.TimeSeconds, hero Location sampled 3 s (read only)
  --coll     option 8: hero collision cylinder / Floor / collide bits / nearby actors (read only)
  --lift     option 9: lift the hero z by N units once, sample Location 5 s while the user holds W
  --pin      option B: 10 s, write LastValidServerLocation (+TooFar=0) = hero Location every 10 ms while W is held
  --syncscan option C: scan memory for copies of the hero position (SmoothLocation target), narrow, then drive them
  --speed    option 10: list Speed|Rate|Scale|Modifier... float/int fields of the hero, optionally write one by name (y)
  --props    option 5: list hero pawn class-chain properties matching a typed filter
  --static   only print the static (file-only, deterministic) GNames/GObjObjects candidate RVAs, no game needed
  --fix      after showing values, ask y/n, then raise hero GroundSpeed/AirSpeed/AccelRate if they are 0/tiny
Method: (1) from the exe file: .data range + candidate TArray globals (static refs);
(2) in the running game: find GNames (TArray<FNameEntry*>, entry 0 = "None", 1 = "ByteProperty") and GObjObjects
(TArray<UObject*>), learn the UObject layout (Name/Class/Outer offsets) by self-check (the object "Class" has Class == itself),
find UProperty objects by name and read their Offset field, then list live Pawn / PlayerController objects."""
import os, re, struct, sys, math, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
GAME_EXE = r"C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight\Binaries\Win64\Kingdom-Win64-Shipping.exe"
OUT = os.path.join(ROOT, "server", "logs", "pawn_probe_last.txt")
PHYS = {0: "None", 1: "Walking", 2: "Falling", 3: "Swimming", 4: "Flying", 5: "Rotating", 6: "Projectile",
        7: "Interpolating", 8: "Spider", 9: "Ladder", 10: "RigidBody", 11: "Soft", 12: "Custom"}
FIX_GROUND, FIX_AIR, FIX_ACCEL = 450.0, 450.0, 2048.0
PAWN_FLOATS = ["GroundSpeed", "WaterSpeed", "AirSpeed", "LadderSpeed", "AccelRate", "JumpZ"]


# ---------------- static part (file only, deterministic) ----------------
def static_info(path=GAME_EXE):
    """returns (imagebase, sizeofimage, data_rva, data_size, [(rva, refs)] candidates for TArray globals)"""
    import pefile
    d = open(path, 'rb').read()
    p = pefile.PE(path, fast_load=True)
    base = p.OPTIONAL_HEADER.ImageBase
    t = [s for s in p.sections if s.Name.startswith(b'.text')][0]
    ds = [s for s in p.sections if s.Name.startswith(b'.data')][0]
    code = d[t.PointerToRawData:t.PointerToRawData + t.SizeOfRawData]
    tva = t.VirtualAddress
    lo, hi = ds.VirtualAddress, ds.VirtualAddress + ds.Misc_VirtualSize
    # mov r64,[rip+d32] followed (<=8 bytes) by mov r64,[r64+r64*8]  == "global TArray<ptr> indexed by number"
    pat = re.compile(rb'[\x48\x4c]\x8b[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....(?=.{0,8}?[\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f]\x8b[\x04\x0c\x14\x1c\x24\x2c\x34\x3c][\xc0-\xff])', re.S)
    cnt = {}
    for m in pat.finditer(code):
        i = m.start()
        tg = tva + i + 7 + struct.unpack('<i', code[i + 3:i + 7])[0]
        if lo <= tg < hi:
            cnt[tg] = cnt.get(tg, 0) + 1
    cands = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))
    return base, p.OPTIONAL_HEADER.SizeOfImage, lo, ds.Misc_VirtualSize, cands


# ---------------- memory access ----------------
class ProcMem:
    def __init__(self, h):
        import pawn_probe as pp
        self.pp, self.h = pp, h

    def read(self, a, n):
        if a < 0x10000 or a > 0x7fffffffffff:
            return None
        b = self.pp.rpm(self.h, a, n)
        return b if b and len(b) == n else None

    def write(self, a, data):
        return bool(self.pp.k32.WriteProcessMemory(self.h, self.pp.ctypes.c_void_p(a), data, len(data), None))


def module_base(pid, exe):
    import ctypes, ctypes.wintypes as wt

    class ME(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD), ("GlblcntUsage", wt.DWORD),
                    ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p), ("modBaseSize", wt.DWORD),
                    ("hModule", wt.HANDLE), ("szModule", ctypes.c_char * 256), ("szExePath", ctypes.c_char * 260)]
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateToolhelp32Snapshot.restype = wt.HANDLE
    k.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    k.Module32First.argtypes = [wt.HANDLE, ctypes.POINTER(ME)]
    k.Module32Next.argtypes = [wt.HANDLE, ctypes.POINTER(ME)]
    snap = k.CreateToolhelp32Snapshot(0x8 | 0x10, pid)
    me = ME()
    me.dwSize = ctypes.sizeof(me)
    ok = k.Module32First(snap, ctypes.byref(me))
    res = None
    while ok:
        if me.szModule.decode('mbcs', 'replace').lower() == exe.lower():
            res = (me.modBaseAddr, me.modBaseSize)
            break
        ok = k.Module32Next(snap, ctypes.byref(me))
    k.CloseHandle(snap)
    return res


# ---------------- UE3 structures ----------------
def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def u64(b, o):
    return struct.unpack_from('<Q', b, o)[0]


def decode_name(b, so):
    seg = b[so:]
    if len(seg) > 3 and seg[1] == 0 and seg[0] != 0 and seg[3] == 0:        # UTF-16
        e = 0
        while e + 1 < len(seg) and (seg[e] or seg[e + 1]):
            e += 2
        return seg[:e].decode('utf-16le', 'replace')
    e = seg.find(b'\0')
    return seg[:e if e >= 0 else len(seg)].decode('latin-1')


def read_big(mem, addr, n, chunk=1 << 20):
    out = bytearray()
    off = 0
    while off < n:
        b = mem.read(addr + off, min(chunk, n - off))
        if b is None:
            return None
        out += b
        off += len(b)
    return bytes(out)


class Names:
    def __init__(self, mem, ptr_arr, count, stroff):
        self.mem, self.count, self.stroff, self.c = mem, count, stroff, {}
        raw = read_big(mem, ptr_arr, count * 8)
        self.ptrs = struct.unpack('<%dQ' % count, raw) if raw else ()
        self.rev = {}

    def get(self, i):
        if i in self.c:
            return self.c[i]
        s = None
        if 0 <= i < len(self.ptrs) and self.ptrs[i]:
            b = self.mem.read(self.ptrs[i], 0x60)
            if b:
                s = decode_name(b, self.stroff)
        self.c[i] = s
        return s

    def build_reverse(self):
        for i in range(len(self.ptrs)):
            n = self.get(i)
            if n is not None:
                self.rev.setdefault(n, []).append(i)


def find_tarrays(mem, base, data_rva, data_size, lo=500, hi=16_000_000):
    """all .data slots that look like TArray<ptr>: (slot_rva, data_ptr, count, max)"""
    raw = read_big(mem, base + data_rva, data_size & ~7)
    if not raw:
        return []
    q = struct.unpack('<%dQ' % (len(raw) // 8), raw)
    out = []
    for i in range(len(q) - 1):
        p = q[i]
        if p < 0x10000 or p > 0x7fffffffffff or p & 7:
            continue
        n, m = q[i + 1] & 0xffffffff, q[i + 1] >> 32
        if lo < n <= m <= hi:
            out.append((data_rva + i * 8, p, n, m))
    return out


def try_gnames(mem, p):
    b = mem.read(p, 16)
    if not b:
        return None
    e0 = mem.read(u64(b, 0), 0x60)
    e1 = mem.read(u64(b, 8), 0x60)
    if not e0 or not e1:
        return None
    for so in range(4, 0x40, 2):
        if (e0[so:so + 5] == b'None\0' or e0[so:so + 10] == b'N\0o\0n\0e\0\0\0') and decode_name(e1, so) == "ByteProperty":
            return so
    return None


class Objs:
    """GObjObjects + learned layout"""
    def __init__(self, mem, names, parr, count, base, imgsize):
        self.mem, self.names, self.base, self.img = mem, names, base, imgsize
        raw = read_big(mem, parr, count * 8)
        self.ptrs = struct.unpack('<%dQ' % count, raw) if raw else ()
        self.nameoff = self.classoff = self.outeroff = None
        self.hdr = {}

    def in_img(self, v):
        return self.base <= v < self.base + self.img

    def learn(self, limit=60000):
        """the object 'Class' has Class == itself and name 'Class'"""
        votes = {}
        good_vt = 0
        for o in self.ptrs[:limit]:
            if not o:
                continue
            h = self.mem.read(o, 0x90)
            if not h:
                continue
            if self.in_img(u64(h, 0)):
                good_vt += 1
            for c in range(0x18, 0x88, 8):
                if u64(h, c) == o:
                    for nn in range(0x08, 0x88, 4):
                        if nn != c and u32(h, nn) < self.names.count and self.names.get(u32(h, nn)) == "Class":
                            votes[(nn, c)] = votes.get((nn, c), 0) + 1
        if not votes or good_vt < 10:
            return False
        (self.nameoff, self.classoff), _ = max(votes.items(), key=lambda kv: (kv[1], -abs(kv[0][1] - kv[0][0] - 8)))
        return True

    def header(self, o):
        h = self.hdr.get(o)
        if h is None:
            h = self.mem.read(o, 0x90) or b''
            self.hdr[o] = h
        return h

    def name(self, o):
        h = self.header(o)
        if len(h) < 0x90:
            return None
        s = self.names.get(u32(h, self.nameoff))
        num = u32(h, self.nameoff + 4)
        return s if not num else "%s_%d" % (s, num - 1)

    def cls(self, o):
        h = self.header(o)
        return u64(h, self.classoff) if len(h) >= 0x90 else 0

    def outer(self, o):
        h = self.header(o)
        return u64(h, self.outeroff) if len(h) >= 0x90 and self.outeroff is not None else 0

    def clsname(self, o):
        c = self.cls(o)
        return self.name(c) if c else None


def inspect(mem, base, imgsize, data_rva, data_size, static_cands, log, minname=500, minobj=3000):
    """returns dict result or None. log(str) prints."""
    t0 = time.time()
    arrays = find_tarrays(mem, base, data_rva, data_size, minname)
    log("TArray 候選 %d 個（.data 範圍）" % len(arrays))
    srv = {r for r, _ in static_cands}
    arrays.sort(key=lambda a: (a[0] not in srv, a[0]))     # static candidates first
    names = None
    for rva, p, n, m in arrays:
        so = try_gnames(mem, p)
        if so is not None:
            names = Names(mem, p, n, so)
            gn_rva, gn_n = rva, n
            break
    if not names:
        log("找不到 GNames（名稱表）。遊戲可能還沒載完，進入戰鬥後再試。")
        return None
    names.build_reverse()
    objs = None
    for rva, p, n, m in sorted(arrays, key=lambda a: -a[2]):
        if rva == gn_rva or n < minobj:
            continue
        ob = Objs(mem, names, p, n, base, imgsize)
        if ob.ptrs and ob.learn():
            objs, go_rva = ob, rva
            break
    if not objs:
        log("找不到 GObjObjects（物件表）。")
        return None
    R = dict(gn_rva=gn_rva, gn_n=gn_n, go_rva=go_rva, go_n=len(objs.ptrs), nameoff=objs.nameoff, classoff=objs.classoff, strof=names.stroff)
    rev = names.rev
    want = set(PAWN_FLOATS) | {"Physics", "Velocity", "Acceleration", "Pawn", "IgnoreMoveInput", "bIgnoreMoveInput"}
    widx = {}
    for w in want:
        for i in rev.get(w, []):
            widx[i] = w
    ones = {}
    for o in objs.ptrs:
        if not o:
            continue
        h = objs.header(o)
        if len(h) < 0x90:
            continue
        ni = u32(h, objs.nameoff)
        if ni in widx:
            ones.setdefault(widx[ni], []).append(o)
    for gs in ones.get("GroundSpeed", []):
        h = objs.header(gs)
        for q in range(0x18, 0x88, 8):
            ob = u64(h, q)
            if ob and q != objs.classoff and objs.name(ob) == "Pawn":
                objs.outeroff = q
                break
        if objs.outeroff is not None:
            break
    if objs.outeroff is None:
        log("找不到屬性 GroundSpeed 的所屬類別 (Outer)。")
        return None
    R['outeroff'] = objs.outeroff

    def props(name, outers):
        return [o for o in ones.get(name, []) if objs.name(objs.outer(o)) in outers and (objs.clsname(o) or "").endswith("Property")]
    pf = {}
    for n in PAWN_FLOATS:
        pl = props(n, {"Pawn"})
        if pl:
            pf[n] = pl[0]
    if len(pf) < 5:
        log("Pawn 的速度屬性找不齊（找到 %s）。" % list(pf))
        return None
    hs = {n: mem.read(pf[n], 0x140) for n in pf}
    best = None
    for k in range(0x58, 0x130, 4):
        vals = [u32(hs[n], k) for n in pf]
        if len(set(vals)) == len(vals) and all(v % 4 == 0 and 0 < v < 0x2000 for v in vals) and max(vals) - min(vals) <= 0x80:
            sc = 1 if vals == sorted(vals) else 0
            if all(any(u32(hs[n], k - d) == 4 for d in (0x14, 0x18, 0x1c, 0x20)) for n in pf):
                sc += 2
            if best is None or sc > best[0]:
                best = (sc, k)
    if not best:
        log("無法判定 UProperty.Offset 欄位位置。")
        return None
    PK = best[1]
    R['propoff'] = PK
    offs = {n: u32(hs[n], PK) for n in pf}

    def poff(name, outers):
        pl = props(name, outers)
        if not pl:
            return None
        h = mem.read(pl[0], 0x140)
        return u32(h, PK) if h else None
    ext = dict(Physics=poff("Physics", {"Actor"}), Velocity=poff("Velocity", {"Actor"}),
               Acceleration=poff("Acceleration", {"Pawn"}), CtlPawn=poff("Pawn", {"Controller"}),
               Ignore=poff("bIgnoreMoveInput", {"Controller", "PlayerController"}) or poff("IgnoreMoveInput", {"Controller", "PlayerController"}))
    R['offs'], R['ext'] = offs, ext
    pawns, ctrls = [], []
    for o in objs.ptrs:
        if not o:
            continue
        cn = objs.clsname(o)
        if not cn or cn == "Class":
            continue
        on = objs.name(o)
        if on is None or on.startswith("Default__"):
            continue
        if "Pawn" in cn:
            pawns.append((o, cn, on))
        elif "PlayerController" in cn:
            ctrls.append((o, cn, on))
    R['pawns'], R['ctrls'] = pawns, ctrls
    R['secs'] = time.time() - t0

    def fl(o, off, n=1):
        b = mem.read(o + off, 4 * n) if off is not None else None
        return list(struct.unpack('<%df' % n, b)) if b else None
    R['fl'] = fl
    hero = None
    for c, cn, on in ctrls:
        if ext['CtlPawn'] is not None:
            b = mem.read(c + ext['CtlPawn'], 8)
            pp = u64(b, 0) if b else 0
            if pp:
                hero = pp
                break
    R['hero'] = hero
    R['objs'], R['names'], R['mem'] = objs, names, mem
    return R


def fmtf(v):
    if v is None:
        return "?"
    return "%g" % round(v[0], 3) if math.isfinite(v[0]) else "壞值"


def report(mem, R):
    L = []
    ext, offs, fl = R['ext'], R['offs'], R['fl']
    L.append("GNames=exe+0x%x(%d名) GObjObjects=exe+0x%x(%d物件) 位移:名稱+0x%x 類別+0x%x 外層+0x%x 屬性Offset欄+0x%x (%.0f秒)" % (
        R['gn_rva'], R['gn_n'], R['go_rva'], R['go_n'], R['nameoff'], R['classoff'], R['outeroff'], R['propoff'], R['secs']))
    L.append("Pawn屬性位移: " + " ".join("%s=+0x%x" % (k, v) for k, v in offs.items()) +
             " | Physics=%s Velocity=%s Accel=%s Controller.Pawn=%s Ignore=%s" % tuple(
                 ("+0x%x" % ext[k]) if ext[k] is not None else "?" for k in ("Physics", "Velocity", "Acceleration", "CtlPawn", "Ignore")))
    L.append("控制器 %d 個、Pawn %d 個（不含 Default__）" % (len(R['ctrls']), len(R['pawns'])))
    for c, cn, on in R['ctrls'][:3]:
        pw = 0
        if ext['CtlPawn'] is not None:
            b = mem.read(c + ext['CtlPawn'], 8)
            pw = u64(b, 0) if b else 0
        ig = mem.read(c + ext['Ignore'], 4) if ext['Ignore'] is not None else None
        L.append("  控制器 %s [%s] 位址 0x%X Pawn=0x%X IgnoreMoveInput原始=%s" % (on, cn, c, pw, "0x%08X" % u32(ig, 0) if ig else "?"))
    hero = R['hero']
    pinfo = {p[0]: p for p in R['pawns']}
    shown = [hero] if hero else []
    seen_cls = {pinfo[hero][1]} if hero in pinfo else set()
    for p, cn, on in R['pawns']:
        if p != hero and len(shown) < 3 and cn not in seen_cls:
            shown.append(p)
            seen_cls.add(cn)
    ce = []
    for p in shown:
        info = pinfo.get(p, (p, "?", "?"))
        ph = mem.read(p + ext['Physics'], 1) if ext['Physics'] is not None else None
        phv = ph[0] if ph else None
        vel = fl(p, ext['Velocity'], 3)
        acc = fl(p, ext['Acceleration'], 3)
        L.append("%s %s [%s] 0x%X GroundSpeed=%s AirSpeed=%s AccelRate=%s JumpZ=%s Physics=%s(%s) Velocity=%s Accel=%s" % (
            "【英雄】" if p == hero else "[其他]", info[2], info[1], p, fmtf(fl(p, offs.get('GroundSpeed'))), fmtf(fl(p, offs.get('AirSpeed'))),
            fmtf(fl(p, offs.get('AccelRate'))), fmtf(fl(p, offs.get('JumpZ'))), "?" if phv is None else phv,
            PHYS.get(phv, "?") if phv is not None else "?", [round(x, 2) for x in vel] if vel else "?", [round(x, 2) for x in acc] if acc else "?"))
        if p == hero:
            ce = ["Cheat Engine「手動加入位址」(Float): GroundSpeed=%X AirSpeed=%X AccelRate=%X JumpZ=%X ; Physics(Byte)=%X" % (
                p + offs['GroundSpeed'], p + offs['AirSpeed'], p + offs['AccelRate'], p + offs['JumpZ'], p + (ext['Physics'] or 0))]
    if not hero:
        L.append("找不到英雄（控制器的 Pawn 是空的）。請確認英雄已出現在場上再執行；上面 [其他] 是場上別的 Pawn。")
    return L + ce


# ---------------- class-chain property walker (options 4/5) ----------------
VEC_NAMES = ("Velocity", "Acceleration", "Location", "Rotation", "Rot", "Dir")
PIN_FLOATS = ["aForward", "aStrafe", "aBaseY", "aBaseX", "aUp", "RawJoyUp", "RawJoyRight", "aMouseX"]
FLAG_RE = re.compile(r"Move|Lock|Freeze|Stun|Ignore|Sync")
DEF_FILTER = "Move|Accel|Speed|Phys|Lock|Sync"


class Walker:
    """learns UStruct SuperField / Children / UField.Next offsets from live objects, then lists properties of a class chain"""
    def __init__(self, R):
        self.R, self.mem, self.objs, self.PK = R, R['mem'], R['objs'], R['propoff']
        self.sf = self.ch = self.nx = None
        self.cache, self.hc = {}, {}

    def hd(self, o):
        h = self.hc.get(o)
        if h is None:
            h = self.mem.read(o, 0x140) or b''
            self.hc[o] = h
        return h

    def up(self, c, sf=None):
        sf = self.sf if sf is None else sf
        h = self.hd(c)
        return u64(h, sf) if len(h) >= 0x140 else 0

    def chain(self, c, sf=None):
        out = []
        while c and len(out) < 30 and c not in out:
            out.append(c)
            c = self.up(c, sf)
        return out

    def learn(self, hero):
        o = self.objs
        c0 = o.cls(hero)
        h0 = self.hd(c0)
        for off in range(0x58, 0x130, 8):
            v = u64(h0, off)
            if not v or v == c0 or o.clsname(v) != "Class":
                continue
            names = [o.name(x) for x in self.chain(c0, off)]
            if "Object" in names and "Pawn" in names and len(names) >= 3:
                self.sf = off
                break
        if self.sf is None:
            return False
        pawn = [x for x in self.chain(c0) if o.name(x) == "Pawn"][0]
        hp = self.hd(pawn)
        best = (0, None, None)
        for ch in range(0x58, 0x130, 8):
            c1 = u64(hp, ch)
            if not c1 or o.outer(c1) != pawn:
                continue
            for nx in range(0x58, 0x130, 8):
                n, cur, seen = 0, c1, set()
                while cur and cur not in seen and n < 3000 and o.outer(cur) == pawn:
                    seen.add(cur)
                    n += 1
                    hh = self.hd(cur)
                    cur = u64(hh, nx) if len(hh) >= 0x140 else 0
                if n > best[0]:
                    best = (n, ch, nx)
        if best[0] < 5:
            return False
        self.ch, self.nx = best[1], best[2]
        return True

    def class_props(self, c):
        """[(name, typename, offset)] declared directly in class c"""
        if c in self.cache:
            return self.cache[c]
        o, out, cur, seen = self.objs, [], u64(self.hd(c), self.ch), set()
        while cur and cur not in seen and len(seen) < 3000 and o.outer(cur) == c:
            seen.add(cur)
            tn = o.clsname(cur) or ""
            if tn.endswith("Property"):
                out.append((o.name(cur), tn, u32(self.hd(cur), self.PK)))
            cur = u64(self.hd(cur), self.nx)
        self.cache[c] = out
        return out

    def props(self, obj):
        """[(owner, name, type, off)] over the class chain, most derived first"""
        res = []
        for c in self.chain(self.objs.cls(obj)):
            for n, t, off in self.class_props(c):
                res.append((self.objs.name(c), n, t, off))
        return res

    def find(self, obj, name):
        for ow, n, t, off in self.props(obj):
            if n == name:
                return t, off
        return None

    def state(self, obj):
        o, mem = self.objs, self.mem
        for off in (0x20, 0x18, 0x28, 0x30):
            b = mem.read(obj + off, 8)
            fp = u64(b, 0) if b else 0
            fr = mem.read(fp, 0x20) if fp else None
            if not fr:
                continue
            for fo in (8, 0, 16):
                t = u64(fr, fo)
                if t and o.clsname(t) == "State":
                    nd = u64(fr, 0)
                    return "%s%s" % (o.name(t), "" if nd == t or not nd else " (node %s)" % o.name(nd))
        return "?"

    def val(self, obj, name, typ, off):
        mem, o = self.mem, self.objs
        a = obj + off
        if typ in ("FloatProperty", "StructProperty") and name in VEC_NAMES:
            b = mem.read(a, 12)
            return list(struct.unpack('<3f', b)) if b else None
        if typ == "FloatProperty":
            b = mem.read(a, 4)
            return struct.unpack('<f', b)[0] if b else None
        if typ == "IntProperty":
            b = mem.read(a, 4)
            return struct.unpack('<i', b)[0] if b else None
        if typ == "ByteProperty":
            b = mem.read(a, 1)
            return b[0] if b else None
        if typ == "BoolProperty":
            bv = self.boolv(obj, name)   # decoded with BitMask (True/False); raw dword only if the mask is unknown
            if bv is not None:
                return "True" if bv else "False"
            b = mem.read(a, 4)
            return ("0x%X?" % u32(b, 0)) if b else None
        if typ in ("ObjectProperty", "ClassProperty", "InterfaceProperty"):
            b = mem.read(a, 8)
            p = u64(b, 0) if b else 0
            return (o.name(p) or "0x%X" % p) if p else "null"
        if typ == "StructProperty":
            b = mem.read(a, 12)
            if not b:
                return None
            if any(v in name for v in VEC_NAMES):
                return list(struct.unpack('<3f', b))
            return "0x" + b[:8].hex()
        return "-"


def ff(v, w=6):
    if v is None:
        return "?".rjust(w)
    if isinstance(v, list):
        return "(" + ",".join(ff(x, 0).strip() for x in v) + ")"
    if isinstance(v, float):
        return ("%.2f" % v if math.isfinite(v) and abs(v) < 1e6 else "bad").rjust(w)
    return str(v).rjust(w)


def get_hero_ctrl(R):
    hero, ext, ctl = R['hero'], R['ext'], None
    for c, cn, on in R['ctrls']:
        b = R['mem'].read(c + ext['CtlPawn'], 8) if ext['CtlPawn'] is not None else None
        if b and u64(b, 0) == hero:
            ctl = c
            break
    if ctl is None and R['ctrls']:
        ctl = R['ctrls'][0][0]
    return hero, ctl


def setup_watch(R, log):
    hero, ctl = get_hero_ctrl(R)
    if not hero or not ctl:
        log("找不到英雄或控制器，請確認英雄已出現在場上。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構（SuperField/Children/Next 位移）。")
        return None
    return W, hero, ctl


def watch(R, log, wait_fn=None, secs=8.0, step=0.25, sleep=time.sleep):
    st = setup_watch(R, log)
    if not st:
        return None
    W, hero, ctl = st
    o, L = R['objs'], []
    L.append("類別結構位移: SuperField+0x%x Children+0x%x Next+0x%x StateFrame=+0x20" % (W.sf, W.ch, W.nx))
    L.append("英雄 %s [%s]  控制器 %s [%s]" % (o.name(hero), o.clsname(hero), o.name(ctl), o.clsname(ctl)))
    L.append("控制器狀態: %s | 英雄狀態: %s" % (W.state(ctl), W.state(hero)))
    pin = W.find(ctl, "PlayerInput")
    pi = 0
    if pin:
        b = R['mem'].read(ctl + pin[1], 8)
        pi = u64(b, 0) if b else 0
    L.append("PlayerInput 物件: %s" % ((o.name(pi) + " [%s]" % o.clsname(pi)) if pi else "找不到(null)"))
    items = []        # (label, obj, type, off, name)
    for n in PIN_FLOATS:
        f = W.find(pi, n) if pi else None
        if f:
            items.append((n, pi, f[0], f[1], n))
    pf = {n: W.find(hero, n) for n in ("Acceleration", "Velocity", "Physics")}
    ig = [(n, W.find(ctl, n)) for n in ("bIgnoreMoveInput", "bIgnoreLookInput", "IgnoreMoveInput", "IgnoreLookInput")]
    flags, seen = [], set()
    for obj in (ctl, hero):
        for ow, n, t, off in W.props(obj):
            if t in ("BoolProperty", "ByteProperty") and FLAG_RE.search(n) and (obj, n) not in seen and len(flags) < 15 and n != "Physics":
                seen.add((obj, n))
                flags.append(("%s%s" % ("C." if obj == ctl else "P.", n), obj, t, off, n))
    L.append("輸入欄位找到: " + (" ".join(i[0] for i in items) or "無") + " | 沒找到: " + (" ".join(n for n in PIN_FLOATS if not any(i[0] == n for i in items)) or "無"))
    L.append("控制器忽略輸入: " + " ".join("%s=%s" % (n, ff(W.val(ctl, n, f[0], f[1]), 0)) for n, f in ig if f))
    L.append("相關旗標(%d): " % len(flags) + " ".join("%s=%s" % (f[0], ff(W.val(f[1], f[4], f[2], f[3]), 0)) for f in flags))
    for l in L:
        log(l)
    if wait_fn:
        wait_fn()
    short = {"aForward": "aFwd", "aStrafe": "aStr", "aBaseY": "aBsY", "aBaseX": "aBsX", "aUp": "aUp", "RawJoyUp": "rJUp", "RawJoyRight": "rJRt", "aMouseX": "aMsX"}
    hdr = " t    " + " ".join(short.get(i[0], i[0])[:6].rjust(6) for i in items) + " | Accel(x,y,z) | Vel(x,y,z) | phys"
    log(hdr)
    rows = [hdr]
    prev_flags, changes, prev_st = None, [], (W.state(ctl), W.state(hero))
    n = int(round(secs / step))
    for k in range(n + 1):
        t = k * step
        vals = [W.val(i[1], i[4], i[2], i[3]) for i in items]
        acc = W.val(hero, "Acceleration", *pf["Acceleration"]) if pf["Acceleration"] else None
        vel = W.val(hero, "Velocity", *pf["Velocity"]) if pf["Velocity"] else None
        ph = W.val(hero, "Physics", *pf["Physics"]) if pf["Physics"] else None
        row = "%4.2f " % t + " ".join(ff(v) for v in vals) + " | " + ff(acc, 0) + " | " + ff(vel, 0) + " | " + str(ph)
        st2 = (W.state(ctl), W.state(hero))
        if st2 != prev_st:
            row += "  狀態變 C=%s P=%s" % st2
            prev_st = st2
        fv = [W.val(f[1], f[4], f[2], f[3]) for f in flags]
        if prev_flags is not None:
            for f, a, b in zip(flags, prev_flags, fv):
                if a != b:
                    changes.append("t=%.2f %s %s->%s" % (t, f[0], a, b))
        prev_flags = fv
        rows.append(row)
        log(row)
        if k < n:
            sleep(step)
    tail = "旗標變化: " + ("; ".join(changes[:8]) if changes else "全程無變化")
    log(tail)
    return L + rows + [tail]


def list_props(R, log, filt=None):
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    try:
        rx = re.compile(filt or DEF_FILTER, re.I)
    except re.error:
        rx = re.compile(DEF_FILTER, re.I)
    o, out = R['objs'], []
    for ow, n, t, off in W.props(hero):
        if rx.search(n):
            raw = ""
            if t == "BoolProperty":
                rb = R['mem'].read(hero + off, 4) if 'mem' in R else None
                raw = "" if not rb else "  (原始 0x%X)" % u32(rb, 0)
            out.append("%-14s %-24s %-12s +0x%03X = %s%s" % (ow[:14], n, t.replace("Property", ""), off, ff(W.val(hero, n, t, off), 0), raw))
    L = ["英雄 %s [%s] 屬性（過濾 %s，共 %d 個，最多顯示 40）" % (o.name(hero), o.clsname(hero), rx.pattern, len(out))] + out[:40]
    for l in L:
        log(l)
    return L


SPEED_RE = r"Speed|Rate|Scale|Modifier|Mult|Factor|Weight|Slow|Stall|Lazy"


BOOL_RE = r"Slow|Stall|Lock|Move|Turn|Stun|Freeze|Block|Ignore|Stop|Drag|Walk|Run|Sync|Fall|Down|Dead|Stagger|Action"


def bool_listing(R, log, W, hero, ctl, maxn=45):
    """BoolProperties of hero and controller that look slow/stall/lock/move related, decoded with BitMask (True/False + raw dword)."""
    o, rx, L = R['objs'], re.compile(BOOL_RE, re.I), []
    for obj, label in ((hero, "英雄"), (ctl, "控制器")):
        if not obj:
            continue
        rows, seen = [], set()
        for ow, n, t, off in W.props(obj):
            if t == "BoolProperty" and rx.search(n) and (n, off) not in seen:
                seen.add((n, off))
                bv = W.boolv(obj, n)
                rb = R['mem'].read(obj + off, 4) if 'mem' in R else None
                rows.append((bv is not False, "%-14s %-26s +0x%03X = %-5s (原始 0x%X)" % (
                    ow[:14], n, off, "?" if bv is None else ("True" if bv else "False"), u32(rb, 0) if rb else 0)))
        rows.sort(key=lambda r: not r[0])   # True / unknown first
        head = "%s %s 的 bool 欄位（名稱含 slow/stall/lock/move/turn...，共 %d 個；True 排前面，最多 %d 個；已用 BitMask 解碼，位移 %s）" % (
            label, o.name(obj), len(rows), maxn, "0x%X" % W.bm if getattr(W, 'bm', None) else "未學到")
        L.append(head)
        L += [r[1] for r in rows[:maxn]]
    for l in L:
        log(l)
    return L


def speed_fields(R, log, mem, can_write, ask=input):
    """option 10: float/int properties of the hero class chain matching SPEED_RE (max 40 lines) + write one chosen property by name (y to confirm)"""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    rx = re.compile(SPEED_RE, re.I)
    o, out, seen = R['objs'], [], set()
    for ow, n, t, off in W.props(hero):
        if t in ("FloatProperty", "IntProperty") and rx.search(n) and (n, off) not in seen:
            seen.add((n, off))
            out.append("%-14s %-34s %-5s +0x%03X = %s" % (ow[:14], n, t.replace("Property", ""), off, ff(W.val(hero, n, t, off), 0)))
    L = ["英雄 %s 速度相關欄位（Float/Int，符合 %s，共 %d 個，最多顯示 40）" % (o.name(hero), rx.pattern, len(out))] + out[:40]
    for l in L:
        log(l)
    L += bool_listing(R, log, W, hero, ctl)
    nm = ask("要改哪一個欄位？輸入名稱（例如 ReplicatedMovementSpeedModifier），不改請直接按 Enter：").strip()
    if not nm:
        return L
    hit = [(ow, n, t, off) for ow, n, t, off in W.props(hero) if n == nm and t in ("FloatProperty", "IntProperty")]
    if not hit:
        log("找不到名為 %s 的 Float/Int 欄位。" % nm)
        return L
    ow, n, t, off = hit[0]
    if not can_write:
        log("沒有寫入權限，請用系統管理員身分執行。")
        return L
    old = W.val(hero, n, t, off)
    try:
        newv = float(ask("%s 目前是 %s，要改成多少？" % (n, ff(old, 0))).strip())
    except ValueError:
        log("不是數字，取消。")
        return L
    if ask("確定把 %s 從 %s 改成 %s？(y/n)：" % (n, ff(old, 0), newv)).strip().lower() != "y":
        log("已取消，沒有修改。")
        return L
    data = struct.pack('<f', newv) if t == "FloatProperty" else struct.pack('<i', int(newv))
    ok = mem.write(hero + off, data)
    back = W.val(hero, n, t, off)
    log("寫入%s，讀回 %s = %s。回遊戲按住 W 看英雄會不會走。" % ("成功" if ok else "可能失敗", n, ff(back, 0)))
    L.append("wrote %s +0x%X: %s -> %s (read back %s)" % (n, off, ff(old, 0), newv, ff(back, 0)))
    return L


def experiment(R, log, mem, speed=3.0, mode="1", secs=5.0, step=0.5, sleep=time.sleep):
    """option 6: write SyncVelocity / SyncAccelerate (vectors) on the hero for secs, re-write every 20 ms, print every step"""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    F = {n: W.find(hero, n) for n in ("SyncVelocity", "SyncAccelerate", "Velocity", "Acceleration", "Location", "Health", "Physics")}
    for n in ("SyncVelocity", "SyncAccelerate"):
        if not F[n]:
            log("找不到屬性 %s，無法做實驗。" % n)
            return None

    def vec(n):
        if not F.get(n):
            return None
        b = mem.read(hero + F[n][1], 12)
        return list(struct.unpack('<3f', b)) if b else None

    def put(n, v):
        return mem.write(hero + F[n][1], struct.pack('<3f', *v))
    targets = {"1": ["SyncVelocity"], "2": ["SyncAccelerate"], "3": ["SyncVelocity", "SyncAccelerate"], "4": ["Velocity"]}[mode]
    scale = 100.0 if mode == "4" else 1.0
    v = [speed * scale, 0.0, 0.0]
    L = ["實驗：寫入 %s = (%g,0,0) 共 %.0f 秒（每 20 毫秒重寫一次）" % ("+".join(targets), v[0], secs),
         "英雄 %s  Health=%s Physics=%s" % (R['objs'].name(hero), ff(W.val(hero, "Health", *F["Health"]), 0) if F["Health"] else "?", ff(W.val(hero, "Physics", *F["Physics"]), 0) if F["Physics"] else "?"),
         " t   | Location(x,y,z) | Velocity | SyncVelocity | SyncAccelerate | Accel"]
    for l in L:
        log(l)
    ok = True
    t0 = time.time()
    nxt = 0.0
    while True:
        t = time.time() - t0
        if t > secs + 1e-9:
            break
        for n in targets:
            ok = put(n, v) and ok
        if t >= nxt:
            row = "%4.1f | %s | %s | %s | %s | %s" % (t, ff(vec("Location"), 0), ff(vec("Velocity"), 0), ff(vec("SyncVelocity"), 0), ff(vec("SyncAccelerate"), 0), ff(vec("Acceleration"), 0))
            log(row)
            L.append(row)
            nxt += step
        sleep(0.02)
    for n in targets:
        put(n, [0.0, 0.0, 0.0])
    end = "完成，已把 %s 寫回 0。寫入%s。若 Location 的 x 數字一直在變大 = 英雄真的在滑動。" % ("+".join(targets), "成功" if ok else "失敗(請用系統管理員身分執行)")
    log(end)
    return L + [end]


def time_check(R, log, mem, secs=3.0, step=0.3, sleep=time.sleep):
    """option 7 (read only): rule time dilation / attachment in or out. Hero flags + WorldInfo dilation + TimeSeconds vs real time."""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    o = R['objs']
    rx = re.compile(r"Dilation|^Base$|HardAttach|Movable|^Role$|^RemoteRole$|bStatic|bHidden|bCollideWorld|bIgnoreForces|CollisionType|^Physics$|LifeSpan|bBlockActors|bDeleteMe|^Owner$|Attach|^bCanTeleport|bJustTeleported|Smooth", re.I)
    L = ["英雄 %s [%s]" % (o.name(hero), o.clsname(hero))]
    for ow, n, t, off in W.props(hero):
        if rx.search(n):
            L.append("  hero %-14s %-24s %-8s +0x%03X = %s" % (ow[:14], n, t.replace("Property", ""), off, ff(W.val(hero, n, t, off), 0)))
    wi = W.find(hero, "WorldInfo")
    wio = 0
    if wi:
        b = mem.read(hero + wi[1], 8)
        wio = u64(b, 0) if b else 0
    ts = None
    if wio:
        L.append("WorldInfo %s [%s]" % (o.name(wio), o.clsname(wio)))
        wrx = re.compile(r"Dilation|TimeSeconds|DeltaSeconds|Pauser|PlayersOnly|GameSpeed|Speed", re.I)
        for ow, n, t, off in W.props(wio):
            if wrx.search(n):
                L.append("  world %-14s %-24s %-8s +0x%03X = %s" % (ow[:14], n, t.replace("Property", ""), off, ff(W.val(wio, n, t, off), 0)))
        ts = W.find(wio, "TimeSeconds")
    else:
        L.append("找不到英雄的 WorldInfo 屬性（只列英雄旗標）。")
    loc = W.find(hero, "Location")
    for l in L:
        log(l)
    log("取樣 %.0f 秒：real(秒) | WorldInfo.TimeSeconds | Location" % secs)
    t0, nxt = time.time(), 0.0
    rows = []
    while True:
        t = time.time() - t0
        if t > secs:
            break
        if t >= nxt:
            tsv = None
            if ts and wio:
                b = mem.read(wio + ts[1], 4)
                tsv = struct.unpack('<f', b)[0] if b else None
            lv = None
            if loc:
                b = mem.read(hero + loc[1], 12)
                lv = list(struct.unpack('<3f', b)) if b else None
            row = "%4.2f | %s | %s" % (t, ff(tsv, 0) if tsv is not None else "?", ff(lv, 0))
            log(row)
            rows.append((t, tsv))
            nxt += step
        sleep(0.02)
    good = [(a, b) for a, b in rows if b is not None]
    end = "（TimeSeconds 增加量 / 真實秒數 = 實際時間倍率；約 1.0 = 沒有時間膨脹）"
    if len(good) >= 2 and good[-1][0] > good[0][0]:
        end = "時間倍率 = %.3f。" % ((good[-1][1] - good[0][1]) / (good[-1][0] - good[0][0])) + end
    log(end)
    return L + [end]


def _w_prop_obj(self, obj, name):
    """(propObject, typename, offset) for the first property called name on obj's class chain"""
    o = self.objs
    for c in self.chain(o.cls(obj)):
        cur, seen = u64(self.hd(c), self.ch), set()
        while cur and cur not in seen and len(seen) < 3000 and o.outer(cur) == c:
            seen.add(cur)
            if o.name(cur) == name:
                return cur, o.clsname(cur), u32(self.hd(cur), self.PK)
            cur = u64(self.hd(cur), self.nx)
    return None


def _w_learn_bm(self, obj):
    """find the UBoolProperty.BitMask offset: the dword position (after Offset_Internal) where all bool properties hold a single bit"""
    if getattr(self, 'bm', None) is not None:
        return self.bm
    o, bools = self.objs, []
    for c in self.chain(o.cls(obj)):
        cur, seen = u64(self.hd(c), self.ch), set()
        while cur and cur not in seen and len(seen) < 3000 and o.outer(cur) == c:
            seen.add(cur)
            if o.clsname(cur) == "BoolProperty":
                bools.append(cur)
            cur = u64(self.hd(cur), self.nx)
    best = (0, None)
    for off in range(self.PK + 4, 0x138, 4):
        vals = [u32(self.hd(b), off) for b in bools]
        ok = sum(1 for v in vals if v and (v & (v - 1)) == 0)
        if len(vals) >= 3 and ok >= 0.95 * len(vals) and len(set(vals)) >= 2 and ok > best[0]:
            best = (ok, off)
    self.bm = best[1]
    return self.bm


def _w_boolv(self, obj, name):
    """True / False for a bool property decoded with its BitMask, None if unknown"""
    p = self.prop_obj(obj, name)
    if not p or p[1] != "BoolProperty" or self.learn_bm(obj) is None:
        return None
    mask = u32(self.hd(p[0]), self.bm)
    b = self.mem.read(obj + p[2], 4)
    return None if not b or not mask else bool(u32(b, 0) & mask)


Walker.prop_obj, Walker.learn_bm, Walker.boolv = _w_prop_obj, _w_learn_bm, _w_boolv


def _bs(v):
    return "?" if v is None else ("1" if v else "0")


def collision_check(R, log, mem, near=300.0, maxn=15):
    """option 8 (read only): hero collision cylinder, Floor, collide bits, step height, mesh translation, actors within near units"""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    o = R['objs']

    def vec(obj, n):
        f = W.find(obj, n)
        b = mem.read(obj + f[1], 12) if f else None
        return list(struct.unpack('<3f', b)) if b else None

    def flt(obj, n):
        f = W.find(obj, n)
        b = mem.read(obj + f[1], 4) if f else None
        return struct.unpack('<f', b)[0] if b else None

    def objp(obj, n):
        f = W.find(obj, n)
        b = mem.read(obj + f[1], 8) if f else None
        return u64(b, 0) if b else 0
    L = ["英雄 %s [%s]" % (o.name(hero), o.clsname(hero)), "Location = %s" % ff(vec(hero, "Location"), 0)]
    seen = set()
    for pn in ("CylinderComponent", "CollisionComponent"):
        c = objp(hero, pn)
        if not W.find(hero, pn):
            L.append("%s: 沒有這個屬性" % pn)
        elif not c:
            L.append("%s = null（沒有碰撞圓柱！）" % pn)
        else:
            L.append("%s = %s [%s] CollisionRadius=%s CollisionHeight=%s%s" % (
                pn, o.name(c), o.clsname(c), ff(flt(c, "CollisionRadius"), 0), ff(flt(c, "CollisionHeight"), 0), "（同上）" if c in seen else ""))
            seen.add(c)
    L.append("Floor = %s（腳下地面法線；全 0 = 沒有地面資訊）" % ff(vec(hero, "Floor"), 0))
    L.append("bCollideWorld=%s bBlockActors=%s bCollideActors=%s（1=開 0=關 ?=讀不到；已依 BitMask 解碼，BitMask 位移 %s）" % (
        _bs(W.boolv(hero, "bCollideWorld")), _bs(W.boolv(hero, "bBlockActors")), _bs(W.boolv(hero, "bCollideActors")),
        "0x%X" % W.bm if getattr(W, 'bm', None) else "未學到"))
    L.append("MaxStepHeight=%s WalkableFloorZ=%s" % (ff(flt(hero, "MaxStepHeight"), 0), ff(flt(hero, "WalkableFloorZ"), 0)))
    m = objp(hero, "Mesh")
    if m:
        L.append("Mesh = %s [%s] Translation=%s" % (o.name(m), o.clsname(m), ff(vec(m, "Translation"), 0)))
    else:
        L.append("Mesh = null 或找不到")
    hl = vec(hero, "Location")
    rows, isact = [], {}
    if hl:
        for p in o.ptrs:
            if not p or p == hero:
                continue
            c = o.cls(p)
            if not c:
                continue
            if c not in isact:
                ok = "Actor" in [o.name(x) for x in W.chain(c)] and not (o.name(c) or "").endswith("Component")
                f = W.find(p, "Location") if ok else None
                isact[c] = f[1] if f else None
            off = isact[c]
            if not off:
                continue
            nm = o.name(p) or ""
            if nm.startswith("Default__"):
                continue
            b = mem.read(p + off, 12)
            if not b:
                continue
            v = struct.unpack('<3f', b)
            if not all(math.isfinite(x) and abs(x) < 1e7 for x in v):
                continue
            d = math.sqrt(sum((a - c2) ** 2 for a, c2 in zip(v, hl)))
            if d <= near:
                rows.append((d, p, nm, o.clsname(p), v))
    rows.sort(key=lambda r: r[0])
    L.append("英雄 %.0f 單位內的其他 Actor（%d 個，最多列 %d）：" % (near, len(rows), maxn))
    for d, p, nm, cn, v in rows[:maxn]:
        L.append("  %-26s [%-22s] 距離%6.1f 位置%s bBlockActors=%s" % (nm[:26], (cn or "?")[:22], d, ff(list(v), 0), _bs(W.boolv(p, "bBlockActors"))))
    if hl and not rows:
        L.append("  （沒有）")
    for l in L:
        log(l)
    return L


def lift_experiment(R, log, mem, height=150.0, wait_fn=None, secs=5.0, step=0.25, sleep=time.sleep):
    """option 9: one write of Location.z += height and Velocity = 0, then sample Location every step for secs. Writes nothing else."""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    fl, fv = W.find(hero, "Location"), W.find(hero, "Velocity")
    if not fl or not fv:
        log("找不到 Location 或 Velocity 屬性。")
        return None

    def loc():
        b = mem.read(hero + fl[1], 12)
        return list(struct.unpack('<3f', b)) if b else None
    if not loc():
        log("讀不到 Location。")
        return None
    if wait_fn:
        wait_fn()
    l0 = loc()
    ok = mem.write(hero + fl[1], struct.pack('<3f', l0[0], l0[1], l0[2] + height))
    ok = mem.write(hero + fv[1], struct.pack('<3f', 0.0, 0.0, 0.0)) and ok
    L = ["已把英雄 Location z 加 %g：%s -> %s，Velocity 設 0。寫入%s。請一直按住 W。" % (
        height, ff(l0, 0), ff([l0[0], l0[1], l0[2] + height], 0), "成功" if ok else "失敗(請用系統管理員身分執行)")]
    log(L[0])
    t0, nxt, first = time.time(), 0.0, None
    while True:
        t = time.time() - t0
        if t > secs + 1e-9:
            break
        if t >= nxt:
            lv = loc()
            first = first or lv
            row = "剩 %.1f 秒 | Location %s" % (max(0.0, secs - t), ff(lv, 0))
            log(row)
            L.append(row)
            nxt += step
        sleep(0.02)
    lv = loc()
    if lv and first:
        end = "結束。x 變化 %.2f、y 變化 %.2f、z 變化 %.2f（x/y 有大變化 = 懸空時可走 -> 原本卡在地板裡；幾乎不變 = 不是碰撞）" % (
            lv[0] - first[0], lv[1] - first[1], lv[2] - first[2])
    else:
        end = "結束（讀不到位置）"
    log(end)
    return L + [end]


PIN_RE = r"Location|Pos"
PIN_SKIP = r"Velocity|Accel|Rotation|Scale"


def pin_experiment(R, log, mem, mode="1", wait_fn=None, secs=10.0, step=0.01, sleep=time.sleep):
    """option B: every ~10 ms write LastValidServerLocation (mode 2: + every other 12-byte Location/Pos struct field of KingdomSyncPawn
    at +0x1D00..0x1E00) = hero Location, and TooFarFromServerLocationTime = 0. Prints Location start/end."""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    fl = W.find(hero, "Location")
    flv = W.find(hero, "LastValidServerLocation")
    ftf = W.find(hero, "TooFarFromServerLocationTime")
    if not fl or not flv:
        log("找不到 Location 或 LastValidServerLocation 欄位。")
        return None
    targets = [("LastValidServerLocation", flv[1])]
    if mode == "2":
        rx, sk = re.compile(PIN_RE, re.I), re.compile(PIN_SKIP, re.I)
        for ow, n, t, off in W.props(hero):
            if t == "StructProperty" and 0x1D00 <= off < 0x1E00 and rx.search(n) and not sk.search(n) \
                    and off != flv[1] and all(off != x[1] for x in targets):
                targets.append((n, off))
    L = ["要鎖定的欄位（都會被寫成英雄目前 Location）：" + ", ".join("%s+0x%X" % x for x in targets)
         + (("；另把 TooFarFromServerLocationTime+0x%X 歸零" % ftf[1]) if ftf else "")]
    log(L[0])

    def loc():
        b = mem.read(hero + fl[1], 12)
        return list(struct.unpack('<3f', b)) if b else None
    l0 = loc()
    if not l0:
        log("讀不到 Location。")
        return None
    if wait_fn:
        wait_fn()
    first = loc() or l0
    t0, nxt, nw, okw = time.time(), 0.0, 0, True
    while True:
        t = time.time() - t0
        if t > secs + 1e-9:
            break
        cur = loc()
        if cur:
            raw = struct.pack('<3f', *cur)
            for n, off in targets:
                okw = mem.write(hero + off, raw) and okw
            if ftf:
                okw = mem.write(hero + ftf[1], struct.pack('<f', 0.0)) and okw
            nw += 1
        if t >= nxt:
            row = "剩 %.1f 秒 | Location %s" % (max(0.0, secs - t), ff(cur, 0))
            log(row)
            L.append(row)
            nxt += 1.0
        sleep(step)
    last = loc()
    end = "結束：共寫入 %d 次%s。Location 起點 %s -> 終點 %s" % (nw, "" if okw else "（有寫入失敗，請用系統管理員身分執行）", ff(first, 0), ff(last, 0))
    if last:
        end += "；x 變化 %.1f、y 變化 %.1f（變化很大 = 鎖定這些欄位就能走；幾乎不變 = 不是這些欄位）" % (last[0] - first[0], last[1] - first[1])
    log(end)
    return L + [end]


# ---------------- option C: sync-unit memory scan ----------------
SCAN_TOL_UU = 0.5
# (name, numpy dtype, itemsize, k = stored value per 1 UU)
SCAN_COMBOS = [("f32", "<f4", 4, 1.0), ("f32", "<f4", 4, 0.01), ("f64", "<f8", 8, 1.0), ("f64", "<f8", 8, 0.01),
               ("int*1000", "<i4", 4, 10.0), ("int*10000", "<i4", 4, 100.0), ("int*65536", "<i4", 4, 655.36)]
SCAN_PERMS = {"xyz": (0, 1, 2), "xzy": (0, 2, 1)}   # stored[i] holds UU axis perm[i] (sync metres use y=up)
SCAN_EXCL = 0x4000


def space_name(c):
    if c["name"].startswith("int"):
        return "公尺×%g" % (c["k"] * 100)
    return "UU" if c["k"] == 1.0 else "公尺"


def read_any(mem, a, n):
    pp = getattr(mem, "pp", None)
    if pp is not None and hasattr(mem, "h"):
        return pp.rpm(mem.h, a, n)
    return mem.read(a, n)


def _cfmt(c):
    return "<3" + ("f" if c["name"] == "f32" else "d" if c["name"] == "f64" else "i")


def cand_read(mem, c):
    """candidate -> position in UU [x,y,z] (or None)."""
    b = mem.read(c["addr"], 3 * c["sz"])
    if not b:
        return None
    st = struct.unpack(_cfmt(c), b)
    uu = [0.0, 0.0, 0.0]
    for i, ax in enumerate(c["perm"]):
        uu[ax] = st[i] / c["k"]
    return uu


def cand_write(mem, c, uu):
    st = [uu[ax] * c["k"] for ax in c["perm"]]
    if c["name"].startswith("int"):
        st = [int(round(v)) for v in st]
    return mem.write(c["addr"], struct.pack(_cfmt(c), *st))


def scan_memory(mem, regions, pos, excl=None, cap_per=60, chunk=16 << 20, log=print, tol=SCAN_TOL_UU):
    """Scan regions [(base,size)] for 3-number patterns equal to pos (UU) in every combo/permutation. Returns candidate dicts."""
    import numpy as np
    pats = []
    for name, dt, sz, k in SCAN_COMBOS:
        for pn, perm in SCAN_PERMS.items():
            if pn == "xzy" and abs(pos[1] - pos[2]) < tol:
                continue
            pats.append(dict(name=name, dt=dt, sz=sz, k=k, perm=perm, pn=pn, vals=[pos[ax] * k for ax in perm], tol=tol * k))
    found, cnt, total, rl = [], {}, 0, list(regions)
    allb = sum(s for _, s in rl)
    done_mb = 0
    for base, size in rl:
        off = 0
        while off < size:
            n = min(chunk + 32, size - off)
            start = off
            off += chunk
            b = read_any(mem, base + start, n)
            if not b:
                continue
            total += len(b)
            for dt in ("<f4", "<f8", "<i4"):
                ps = [p for p in pats if p["dt"] == dt]
                sz = ps[0]["sz"]
                cntv = len(b) // sz
                if cntv < 3:
                    continue
                arr = np.frombuffer(b, dtype=dt, count=cntv)
                for p in ps:
                    key = (p["name"], p["k"], p["pn"])
                    if cnt.get(key, 0) >= cap_per:
                        continue
                    v0, v1, v2 = p["vals"]
                    idx = np.nonzero(np.abs(arr[:-2] - v0) <= p["tol"])[0]
                    if not len(idx):
                        continue
                    ok = (np.abs(arr[idx + 1] - v1) <= p["tol"]) & (np.abs(arr[idx + 2] - v2) <= p["tol"])
                    for i in idx[ok]:
                        byte = int(i) * sz
                        if byte >= chunk:
                            continue
                        addr = base + start + byte
                        if excl and excl[0] <= addr < excl[1]:
                            continue
                        found.append(dict(addr=addr, name=p["name"], sz=sz, k=p["k"], perm=p["perm"], pn=p["pn"]))
                        cnt[key] = cnt.get(key, 0) + 1
                        if cnt[key] >= cap_per:
                            break
            if total // (512 << 20) > done_mb:
                done_mb = total // (512 << 20)
                log("  掃描進度：已讀 %.0f / %.0f MB，找到 %d 個" % (total / 1048576, allb / 1048576, len(found)))
    seen, out = set(), []
    for c in found:   # one address matched by several combos: keep the first (f32 first)
        if c["addr"] not in seen:
            seen.add(c["addr"])
            out.append(c)
    return out


def cand_text(i, c, v):
    return "#%d  0x%X  %s(%s, 順序 %s)  = %s" % (i, c["addr"], c["name"], space_name(c), c["pn"], ff(v, 0) if v else "?")


def narrow(mem, cands, hero_now, hero_old, tolr=2.0, moved=3.0):
    """Keep candidates that track the hero's new position, or stay at the old one. Returns [(cand, kind)]."""
    hm = math.dist(hero_old, hero_now) > moved
    out = []
    for c in cands:
        v = cand_read(mem, c)
        if not v:
            continue
        near_now = math.dist(v, hero_now) <= tolr
        near_old = math.dist(v, hero_old) <= tolr
        if hm and near_now:
            out.append((c, "跟著英雄走"))
        elif hm and near_old:
            out.append((c, "留在舊位置不動"))
        elif not hm and near_now:
            out.append((c, "英雄沒動、數值也沒動"))
    return out


def sync_scan(R, log, mem, regions, ask=input, countdown=None, sleep=time.sleep, secs=10.0, hold=6):
    """option C: scan for the hero's position elsewhere in memory (the SmoothLocation pull target), narrow, then drive it."""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    fl, fv = W.find(hero, "Location"), W.find(hero, "Velocity")
    if not fl:
        log("找不到 Location 欄位。")
        return None

    def hloc():
        b = mem.read(hero + fl[1], 12)
        return list(struct.unpack("<3f", b)) if b else None

    def hvel():
        b = mem.read(hero + fv[1], 12) if fv else None
        return list(struct.unpack("<3f", b)) if b else [0.0, 0.0, 0.0]
    L = []
    p0 = hloc()
    if not p0:
        log("讀不到 Location。")
        return None
    log("英雄目前位置 (UU) = %s；換成公尺 = %s。開始掃描整個遊戲記憶體（約 1 分鐘，請讓英雄站著不要動）..." % (ff(p0, 0), ff([v / 100 for v in p0], 0)))
    cands = scan_memory(mem, regions, p0, excl=(hero, hero + SCAN_EXCL), log=log)
    L.append("掃描 1：%d 個候選，英雄 %s" % (len(cands), ff(p0, 0)))
    if not cands:
        log("沒有找到任何符合英雄位置的數字。")
        return L
    log("找到 %d 個候選（只列前 30 個）：" % len(cands))
    for i, c in enumerate(cands[:30]):
        row = cand_text(i, c, cand_read(mem, c))
        log(row)
        L.append(row)
    surv = [(c, "未篩選") for c in cands]
    for rnd in (1, 2):
        s = ask("\n篩選第 %d 輪：按 Enter 後倒數 5 秒；請切回遊戲，一直按住 W 並連續跳躍 %d 秒讓英雄真的移動，然後停下來。不想再篩請輸入 n 再按 Enter：" % (rnd, hold)).strip().lower()
        if s == "n":
            break
        start = hloc() or p0
        if countdown:
            countdown()
        for _ in range(hold):
            sleep(1)
        now = hloc() or start
        res = narrow(mem, [c for c, _ in surv], now, start)
        log("第 %d 輪：英雄 %s -> %s，剩 %d 個候選：" % (rnd, ff(start, 0), ff(now, 0), len(res)))
        L.append("篩選 %d：%s -> %s 剩 %d" % (rnd, ff(start, 0), ff(now, 0), len(res)))
        if not res:
            log("全部被淘汰（沒有數字符合英雄新舊位置）。同步位置可能不是這幾種格式；結束。")
            return L
        surv = res[:30]
        for i, (c, kind) in enumerate(surv):
            row = cand_text(i, c, cand_read(mem, c)) + "  [" + kind + "]"
            log(row)
            L.append(row)
        if len(surv) <= 5:
            break
    sel = ask("\n要推哪幾個？輸入編號（逗號分隔），直接按 Enter = 全部：").strip()
    pick = [c for c, _ in surv]
    if sel:
        try:
            ids = [int(x) for x in sel.replace("，", ",").split(",") if x.strip()]
            pick = [surv[i][0] for i in ids if 0 <= i < len(surv)] or pick
        except ValueError:
            pass
    md = ask("推法：1 = 每 10 毫秒把候選的 x 加 3 UU（預設）；2 = 每次都把候選改成英雄現在位置加速度：").strip() or "1"
    ask("\n準備好了：按 Enter 後有 5 秒倒數，請切回遊戲並一直按住 W。之後 %d 秒會一直寫入候選。" % int(secs))
    if countdown:
        countdown()
    first = hloc() or p0
    t0, nxt, nw, okw = time.time(), 0.0, 0, True
    over, last = {id(c): 0 for c in pick}, {}
    while True:
        t = time.time() - t0
        if t > secs + 1e-9:
            break
        cur, vel = hloc(), hvel()
        for c in pick:
            v = cand_read(mem, c)
            if v is None:
                continue
            if id(c) in last and math.dist(v, last[id(c)]) > 0.5:
                over[id(c)] += 1   # something else changed it after our last write
            if md == "2" and cur:
                nv = [cur[i] + vel[i] * 0.01 for i in range(3)]
            else:
                nv = [v[0] + 3.0, v[1], v[2]]
            okw = cand_write(mem, c, nv) and okw
            last[id(c)] = nv
        nw += 1
        if t >= nxt:
            row = "剩 %.0f 秒 | 英雄 %s" % (max(0.0, secs - t), ff(cur, 0))
            log(row)
            L.append(row)
            nxt += 1.0
        sleep(0.01)
    end = hloc() or first
    msg = "結束：寫入 %d 輪%s。英雄 起點 %s -> 終點 %s；x 變化 %.1f、y 變化 %.1f（變化很大 = 這些候選就是拉住英雄的同步位置）" % (
        nw, "" if okw else "（有寫入失敗，請用系統管理員身分執行）", ff(first, 0), ff(end, 0), end[0] - first[0], end[1] - first[1])
    log(msg)
    L.append(msg)
    for c in pick:
        row = "候選 0x%X 被遊戲改回去 %d 次（次數多 = 遊戲每幀都在更新它，很可能就是真正的同步位置）" % (c["addr"], over[id(c)])
        log(row)
        L.append(row)
    return L


# ---------------- option D: drive the stuck sync copies ----------------
def neighbours(mem, c, before=24, total=64):
    """Raw 64 bytes around a candidate -> dict {rel_offset: dword}"""
    b = mem.read(c["addr"] - before, total)
    if not b:
        return {}
    return {i - before: u32(b, i) for i in range(0, total - 3, 4)}


def slot_text(rel, d):
    f = struct.unpack("<f", struct.pack("<I", d))[0]
    if d == 0:
        return None
    if math.isfinite(f) and 1e-4 < abs(f) < 1e7:
        return "%+d:f%s" % (rel, ("%.3f" % f))
    return "%+d:0x%X" % (rel, d)


def neighbour_lines(i, c, nb):
    items = [t for t in (slot_text(r, d) for r, d in sorted(nb.items())) if t]
    rows = ["#%d 0x%X(%s) 周圍 64 位元組（相對位移:數值；0 省略；f=浮點）：" % (i, c["addr"], c["name"])]
    for k in range(0, len(items), 5):
        rows.append("    " + "  ".join(items[k:k + 5]))
    return rows[:5]


def drive_cands(mem, pick, hloc, hdir, mode, secs, log, sleep=time.sleep, step=0.01, adv=4.5):
    """mode 1: write cands = hero's current Location each tick; mode 2: cands = start + dir*adv*ticks. Returns summary dict."""
    first = hloc()
    p = list(first)
    t0, nxt, ticks, okw = time.time(), 0.0, 0, True
    over, last = {id(c): 0 for c in pick}, {}
    ds = hdir() if mode == 2 else None
    while True:
        t = time.time() - t0
        if t > secs + 1e-9:
            break
        cur = hloc()
        if mode == 2:
            ds = hdir() or ds
            p = [p[i] + ds[i] * adv for i in range(3)]
            tgt = p
        else:
            tgt = cur
        for c in pick:
            v = cand_read(mem, c)
            if v is None:
                continue
            if id(c) in last and math.dist(v, last[id(c)]) > 0.5:
                over[id(c)] += 1
            okw = cand_write(mem, c, tgt) and okw
            last[id(c)] = list(tgt)
        ticks += 1
        if t >= nxt:
            log("  剩 %.0f 秒 | 英雄 %s | 寫入目標 %s" % (max(0.0, secs - t), ff(cur, 0), ff(tgt, 0)))
            nxt += 1.0
        sleep(step)
    return dict(first=first, end=hloc(), ticks=ticks, okw=okw, over=over)


def stuck_drive(R, log, mem, regions, ask=input, countdown=None, sleep=time.sleep, secs=10.0, hold=6):
    """option D: scan like C, jump away once, keep only copies that STAY at the old position, show their neighbours, then drive them."""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    fl, fr, fa = W.find(hero, "Location"), W.find(hero, "Rotation"), W.find(hero, "Acceleration")
    if not fl:
        log("找不到 Location 欄位。")
        return None

    def hloc():
        b = mem.read(hero + fl[1], 12)
        return list(struct.unpack("<3f", b)) if b else None

    def hdir():
        """unit horizontal direction in UU: Acceleration if non-zero, else facing from Rotation yaw (65536 = 360 deg)"""
        if fa:
            b = mem.read(hero + fa[1], 12)
            if b:
                x, y, _ = struct.unpack("<3f", b)
                n = math.hypot(x, y)
                if n > 1.0:
                    return [x / n, y / n, 0.0]
        if fr:
            b = mem.read(hero + fr[1], 12)
            if b:
                yaw = struct.unpack("<3i", b)[1] * math.pi / 32768.0
                return [math.cos(yaw), math.sin(yaw), 0.0]
        return [1.0, 0.0, 0.0]
    L = []
    p0 = hloc()
    if not p0:
        log("讀不到 Location。")
        return None
    log("英雄目前位置 (UU) = %s。開始掃描整個遊戲記憶體（約 1 分鐘，請讓英雄站著不要動）..." % ff(p0, 0))
    cands = scan_memory(mem, regions, p0, excl=(hero, hero + SCAN_EXCL), log=log)
    L.append("掃描：%d 個候選，英雄 %s" % (len(cands), ff(p0, 0)))
    if not cands:
        log("沒有找到任何符合英雄位置的數字。")
        return L
    ask("\n掃描完成（%d 個候選）。按 Enter 後倒數 5 秒；請切回遊戲，連續跳躍並按住 W 約 %d 秒，讓英雄跑到離出生點很遠的地方，然後停下來：" % (len(cands), hold))
    start = hloc() or p0
    if countdown:
        countdown()
    for _ in range(hold):
        sleep(1)
    now = hloc() or start
    if math.dist(start, now) <= 3.0:
        log("英雄幾乎沒移動（%s -> %s），無法分辨哪些副本會跟著走。請重跑並確實跳遠一點。" % (ff(start, 0), ff(now, 0)))
        L.append("英雄沒移動，中止")
        return L
    res = [c for c, k in narrow(mem, cands, now, start) if k == "留在舊位置不動"]
    log("英雄 %s -> %s；卡住不動的副本共 %d 個（跟著英雄走的已丟掉）：" % (ff(start, 0), ff(now, 0), len(res)))
    L.append("跳遠：%s -> %s，卡住副本 %d 個" % (ff(start, 0), ff(now, 0), len(res)))
    if not res:
        log("沒有任何副本留在舊位置。結束。")
        return L
    pick = res[:12]
    snap0 = {}
    for i, c in enumerate(pick):
        v = cand_read(mem, c)
        snap0[id(c)] = neighbours(mem, c)
        row = cand_text(i, c, v)
        log(row)
        L.append(row)
    log("--- 卡住副本周圍的欄位（找速度/狀態欄位，最多 6 個副本）---")
    for i, c in enumerate(pick[:6]):
        for row in neighbour_lines(i, c, snap0[id(c)]):
            log(row)
            L.append(row)
    sel = ask("\n要推哪幾個？輸入編號（逗號分隔），直接按 Enter = 全部：").strip()
    if sel:
        try:
            ids = [int(x) for x in sel.replace("，", ",").split(",") if x.strip()]
            pick = [pick[i] for i in ids if 0 <= i < len(pick)] or pick
        except ValueError:
            pass
    md = ask("推法：1 = 每 10 毫秒把它們寫成英雄現在位置（預設）；2 = 沿英雄面向/W 方向每 10 毫秒前進 4.5 UU；3 = 先 1 再 2，各 %d 秒：" % int(secs)).strip() or "1"
    modes = [1, 2] if md == "3" else [2 if md == "2" else 1]
    pre = {id(c): cand_read(mem, c) for c in pick}
    for m in modes:
        ask("\n推法 %d：按 Enter 後倒數 5 秒，請切回遊戲並一直按住 W。之後 %d 秒會一直寫入。" % (m, int(secs)))
        if countdown:
            countdown()
        cur_pre = {id(c): cand_read(mem, c) for c in pick}
        drift = [i for i, c in enumerate(pick) if cur_pre[id(c)] and pre[id(c)] and math.dist(cur_pre[id(c)], pre[id(c)]) > 0.5]
        r = drive_cands(mem, pick, hloc, hdir, m, secs, log, sleep=sleep)
        e, f = r["end"] or r["first"], r["first"]
        msg = "推法 %d 結束：寫入 %d 輪%s。英雄 起點 %s -> 終點 %s；x 變化 %.1f、y 變化 %.1f（變化很大 = 同步位置找到了）" % (
            m, r["ticks"], "" if r["okw"] else "（有寫入失敗，請用系統管理員身分執行）", ff(f, 0), ff(e, 0), e[0] - f[0], e[1] - f[1])
        log(msg)
        L.append(msg)
        L.append("推之前，副本在沒人寫的情況下自己變動的編號：%s" % (drift if drift else "無（不會自己動）"))
        log(L[-1])
        for i, c in enumerate(pick):
            row = "候選#%d 0x%X 被遊戲改回去 %d 次（0 = 遊戲不更新它；很多 = 每幀被覆蓋）" % (i, c["addr"], r["over"][id(c)])
            log(row)
            L.append(row)
        pre = {id(c): cand_read(mem, c) for c in pick}
    log("--- 推完後，周圍欄位有變動的（相對位移:舊值->新值，最多 6 個副本）---")
    for i, c in enumerate(pick[:6]):
        n0, n1 = snap0.get(id(c), {}), neighbours(mem, c)
        diff = ["%+d:0x%X->0x%X" % (k, n0[k], n1[k]) for k in sorted(n1) if k in n0 and n0[k] != n1[k] and k not in (0, 4, 8)][:8]
        row = "#%d 周圍變動：%s" % (i, "  ".join(diff) if diff else "無")
        log(row)
        L.append(row)
    return L


# ---------------- option E: root motion / animation state ----------------
RMM_DEFAULT = ["RMM_Translate", "RMM_Velocity", "RMM_Ignore", "RMM_Accel", "RMM_Relative"]   # UE3 order (fallback only)
RM_MESH_PROPS = ["RootMotionMode", "PreviousRMM", "RootMotionRotationMode", "RootMotionAccelScale", "RootMotionDelta",
                 "RootMotionVelocity", "RootMotionRotationScale", "bPauseAnims", "bForceRefpose", "bUpdateSkelWhenNotRendered",
                 "bNoSkeletonUpdate", "bTickAnimNodesWhenNotRendered", "bIgnoreControllers", "bUseRawData"]
RM_PAWN_RE = r"Anim|Move|Stance|Action|Mode|Posture|State|Gait|Sprint|Run|Walk"
RM_NODE_RE = r"Seq|Weight|Active|Rate|Playing|Loop|Speed|Mode|State|Time|Child"


def rm_enum_names(R):
    """ERootMotionMode value names read from the live UEnum (fallback: UE3 default order). Returns (names, from_game)"""
    o, mem = R['objs'], R['mem']
    for p in o.ptrs:
        if not p or o.name(p) != "ERootMotionMode":
            continue
        for off in range(0x30, 0x120, 8):
            b = mem.read(p + off, 12)
            if not b:
                continue
            ptr, cnt = u64(b, 0), u32(b, 8)
            if not ptr or not (2 <= cnt <= 12):
                continue
            raw = mem.read(ptr, 8 * cnt)
            if not raw:
                continue
            nm = [R['names'].get(u32(raw, i * 8)) for i in range(cnt)]
            if all(x and x.startswith("RMM_") for x in nm):
                return nm, True
    return RMM_DEFAULT, False


def _rm_read(W, obj, n, t, off):
    mem = W.mem
    if t == "NameProperty":
        b = mem.read(obj + off, 8)
        if not b:
            return None
        return W.R['names'].get(u32(b, 0)) or "idx%d" % u32(b, 0)
    if t == "StructProperty":
        b = mem.read(obj + off, 12)
        return list(struct.unpack('<3f', b)) if b else None
    return W.val(obj, n, t, off)


def _rm_s(v):
    return v if isinstance(v, str) else ff(v, 0).strip()


def rm_info(R, log, W, hero, maxlines=40):
    """prints mesh + root motion props + animation state. Returns (lines, mesh, enum_names) or None"""
    mem, o = R['mem'], R['objs']
    fm = W.find(hero, "Mesh")
    if not fm:
        log("找不到 Pawn.Mesh 欄位。")
        return None
    b = mem.read(hero + fm[1], 8)
    mesh = u64(b, 0) if b else 0
    if not mesh:
        log("Pawn.Mesh 是空的。")
        return None
    en, real = rm_enum_names(R)
    L = ["Mesh = %s [%s] (0x%X)；ERootMotionMode %s：%s" % (
        o.name(mesh), o.clsname(mesh), mesh, "讀自遊戲" if real else "猜的(UE3預設順序)", ",".join("%d=%s" % (i, x) for i, x in enumerate(en)))]
    byname = {n: (t, off) for ow, n, t, off in W.props(mesh)}
    row = []
    for n in RM_MESH_PROPS:
        if n in byname:
            t, off = byname[n]
            v = _rm_read(W, mesh, n, t, off)
            if n in ("RootMotionMode", "PreviousRMM") and isinstance(v, int):
                v = "%d(%s)" % (v, en[v] if v < len(en) else "?")
            row.append("%s=%s" % (n, _rm_s(v)))
        else:
            row.append("%s=無" % n)
    for i in range(0, len(row), 3):
        L.append("  " + "  ".join(row[i:i + 3]))
    for n in ("AnimTreeTemplate", "Animations", "SkeletalMesh", "PhysicsAsset"):
        if n in byname:
            t, off = byname[n]
            L.append("  %s = %s" % (n, _rm_s(_rm_read(W, mesh, n, t, off))))
    rx, st = re.compile(RM_PAWN_RE, re.I), []
    for ow, n, t, off in W.props(hero):
        if t in ("ByteProperty", "NameProperty") and rx.search(n) and n not in [x[0] for x in st]:
            st.append((n, "%s=%s" % (n, _rm_s(_rm_read(W, hero, n, t, off)))))
    L.append("英雄的 Byte/Name 狀態欄位（名稱含 Anim/Move/State/Mode 等，共 %d，列前 12）：" % len(st))
    for i in range(0, min(len(st), 12), 3):
        L.append("  " + "  ".join(x[1] for x in st[i:i + 3]))
    nodes, seqs = [], []
    for p in o.ptrs:
        if not p:
            continue
        cn = o.clsname(p) or ""
        if "AnimNode" not in cn:
            continue
        sc = W.find(p, "SkelComponent")
        if not sc:
            continue
        bb = mem.read(p + sc[1], 8)
        if not bb or u64(bb, 0) != mesh:
            continue
        nodes.append(p)
        if "Sequence" in cn:
            seqs.append(p)
        if len(nodes) > 300:
            break
    L.append("掛在此 Mesh 的 AnimNode 共 %d 個（AnimNodeSequence 類 %d 個）" % (len(nodes), len(seqs)))
    nrx = re.compile(RM_NODE_RE, re.I)

    def node_line(p):
        parts = []
        for ow, n, t, off in W.props(p):
            if t in ("FloatProperty", "NameProperty", "ByteProperty", "BoolProperty", "IntProperty") and nrx.search(n) \
                    and not n.startswith(("Node", "Debug")) and len(parts) < 7:
                parts.append("%s=%s" % (n, _rm_s(_rm_read(W, p, n, t, off))))
        return "  %s [%s] %s" % ((o.name(p) or "?")[-20:], o.clsname(p), " ".join(parts))
    L.append("AnimNodeSequence（最多 10 個；看 AnimSeqName、Rate、bPlaying；全部 Rate=0 或 bPlaying=False = 跑步動畫沒在播）：")
    L += [node_line(p) for p in seqs[:10]]
    others = [p for p in nodes if p not in seqs]
    L.append("其他 AnimNode（Blend/StateMachine/Kingdom 自訂，最多 8 個）：")
    L += [node_line(p) for p in others[:8]]
    L = L[:maxlines]
    for l in L:
        log(l)
    return L, mesh, en


def _rm_setbool(W, obj, name, val):
    p = W.prop_obj(obj, name)
    if not p or p[1] != "BoolProperty" or W.learn_bm(obj) is None:
        return None
    mask = u32(W.hd(p[0]), W.bm)
    b = W.mem.read(obj + p[2], 4)
    if not b or not mask:
        return None
    v = u32(b, 0)
    v = (v | mask) if val else (v & ~mask & 0xFFFFFFFF)
    return W.mem.write(obj + p[2], struct.pack('<I', v))


def rm_experiment(R, log, mem, mode="1", wait_fn=None, secs=10.0, step=0.01, sleep=time.sleep):
    """mode 1: RootMotionMode=RMM_Ignore + bPauseAnims=False every ~10 ms; mode 2: RMM_Velocity + RootMotionAccelScale=(1,1,1).
    Prints hero Location start/end and restores the original values."""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    r = rm_info(R, lambda x: None, W, hero)
    if not r:
        log("找不到 Mesh。")
        return None
    _, mesh, en = r
    fl, frm = W.find(hero, "Location"), W.find(mesh, "RootMotionMode")
    if not fl or not frm:
        log("找不到 Location 或 Mesh.RootMotionMode。")
        return None
    wn = "RMM_Ignore" if mode == "1" else "RMM_Velocity"
    want = en.index(wn) if wn in en else (2 if mode == "1" else 1)
    fas = W.find(mesh, "RootMotionAccelScale") if mode == "2" else None
    orig_m = mem.read(mesh + frm[1], 1)
    orig_as = mem.read(mesh + fas[1], 12) if fas else None
    pp = W.prop_obj(mesh, "bPauseAnims")
    orig_pause = W.boolv(mesh, "bPauseAnims") if pp else None

    def loc():
        b = mem.read(hero + fl[1], 12)
        return list(struct.unpack('<3f', b)) if b else None
    if not loc() or not orig_m:
        log("讀不到 Location 或 RootMotionMode。")
        return None
    L = ["原始 RootMotionMode=%d；要寫入 %d(%s)%s；bPauseAnims 原值 %s" % (
        orig_m[0], want, wn, "；RootMotionAccelScale 設 (1,1,1)" if fas else "", orig_pause)]
    log(L[0])
    if wait_fn:
        wait_fn()
    first = loc() or [0, 0, 0]
    t0, nxt, nw, okw = time.time(), 0.0, 0, True
    while True:
        t = time.time() - t0
        if t > secs + 1e-9:
            break
        okw = mem.write(mesh + frm[1], bytes([want])) and okw
        if mode == "1" and pp:
            _rm_setbool(W, mesh, "bPauseAnims", False)
        if fas:
            okw = mem.write(mesh + fas[1], struct.pack('<3f', 1.0, 1.0, 1.0)) and okw
        nw += 1
        if t >= nxt:
            row = "剩 %.1f 秒 | Location %s" % (max(0.0, secs - t), ff(loc(), 0))
            log(row)
            L.append(row)
            nxt += 1.0
        sleep(step)
    last = loc()
    mem.write(mesh + frm[1], orig_m)
    if orig_as:
        mem.write(mesh + fas[1], orig_as)
    if pp and orig_pause is not None:
        _rm_setbool(W, mesh, "bPauseAnims", orig_pause)
    end = "結束：寫入 %d 次%s，已還原原值。Location 起點 %s -> 終點 %s" % (nw, "" if okw else "（有寫入失敗，請用系統管理員身分執行）", ff(first, 0), ff(last, 0))
    if last and first:
        end += "；x 變化 %.1f、y 變化 %.1f（變化很大 = root motion 就是原因；幾乎不變 = 不是）" % (last[0] - first[0], last[1] - first[1])
    log(end)
    return L + [end]


def rootmotion(R, log):
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    r = rm_info(R, log, W, hero)
    return r[0] if r else None


# ---- key F: challenge / control gate check (11-07 09:00) ----
GATE_FACTORS = [("fForwardSpeedFactor", 1.0), ("fBackSpeedFactor", 0.6), ("fRightSpeedFactor", 0.9), ("fLeftSpeedFactor", 0.9),
                ("fForwardWhenHoldSpeedFactor", 0.6), ("fBackWhenHoldSpeedFactor", 0.45), ("fRightWhenHoldSpeedFactor", 0.5),
                ("fLeftWhenHoldSpeedFactor", 0.5)]   # values from DefaultWeapon.ini [KingdomGame.KingdomWeapon]
GATE_CTL_RE = r"Factor|Attenuation|MoveRate"
GATE_BOOL_RE = r"Ignore|Cinematic|Challenge|Choos|Choice|Start|Begun|Ready|Wait|CountDown|Lock|Control|Battle|Enable|Freeze|End|Over|Reset"
STAGE_NAMES = ["HUIKAN", "GEDANG", "SHEJIAN", "QIZHAN", "SHIZHAN"]
PLAYMODE_NAMES = ["TUTORIAL", "CHALLENGE", "CHALLENGE_EX"]


def gate_objects(R):
    """(game, gri) live objects: class name 'Kingdom*Game' (KingdomChallengeGame...) and *GameReplicationInfo"""
    o, game, gri = R['objs'], None, None
    for p in o.ptrs:
        if not p:
            continue
        cn = o.clsname(p)
        if not cn or cn == "Class":
            continue
        on = o.name(p) or ""
        if on.startswith("Default__"):
            continue
        if game is None and cn.startswith("Kingdom") and cn.endswith("Game"):
            game = p
        elif gri is None and cn.endswith("GameReplicationInfo"):
            gri = p
    return game, gri


def _gate_rows(W, obj, rx_any, own_kw=None, types=("BoolProperty", "ByteProperty", "IntProperty", "FloatProperty"), maxn=30):
    rows, seen = [], set()
    for ow, n, t, off in W.props(obj):
        if t not in types or (n, off) in seen:
            continue
        if not (rx_any.search(n) or (own_kw and own_kw in ow)):
            continue
        seen.add((n, off))
        v = W.val(obj, n, t, off)
        extra = ""
        if n == "CurrentStage" and isinstance(v, int) and 0 <= v < len(STAGE_NAMES):
            extra = " (%s)" % STAGE_NAMES[v]
        if n == "PlayMode" and isinstance(v, int) and 0 <= v < len(PLAYMODE_NAMES):
            extra = " (%s)" % PLAYMODE_NAMES[v]
        vs = v if isinstance(v, str) else ff(v, 0).strip()
        rows.append("  %-14s %-30s %-5s +0x%03X = %s%s" % (ow[:14], n, t.replace("Property", ""), off, vs, extra))
    return rows[:maxn]


def gate_check(R, log):
    """option F (read only): controller/hero state, challenge Game fields, GRI match flags, controller speed factors"""
    hero, ctl = get_hero_ctrl(R)
    if not hero or not ctl:
        log("找不到英雄或控制器（請確認已在戰鬥中）。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學習類別結構。")
        return None
    o = R['objs']
    game, gri = gate_objects(R)
    L = ["控制器 %s [%s] 狀態=%s | 英雄 %s 狀態=%s" % (o.name(ctl), o.clsname(ctl), W.state(ctl), o.name(hero), W.state(hero))]
    L.append("控制器的移動係數（Factor/Attenuation/MoveRate；0 = 可疑）：")
    L += _gate_rows(W, ctl, re.compile(GATE_CTL_RE), types=("FloatProperty",), maxn=40)
    L.append("控制器的開關（Ignore/Cinematic/Lock/Battle...）：")
    L += _gate_rows(W, ctl, re.compile(GATE_BOOL_RE), types=("BoolProperty", "ByteProperty"), maxn=30)
    if game:
        L.append("遊戲規則物件 %s [%s] 狀態=%s：" % (o.name(game), o.clsname(game), W.state(game)))
        L += _gate_rows(W, game, re.compile(GATE_BOOL_RE), own_kw="Challenge", types=("BoolProperty", "ByteProperty", "IntProperty"), maxn=40)
    else:
        L.append("找不到遊戲規則物件（*Game）。")
    if gri:
        L.append("GRI %s [%s] 狀態=%s：" % (o.name(gri), o.clsname(gri), W.state(gri)))
        L += _gate_rows(W, gri, re.compile(r"Match|CountDown|Time|Begun|Over|Start"), types=("BoolProperty", "IntProperty", "ByteProperty"), maxn=20)
    for l in L:
        log(l)
    return L


def _gate_write(W, obj, name, val):
    p = W.find(obj, name)
    if not p:
        return False
    t, off = p
    if t == "BoolProperty":
        return bool(_rm_setbool(W, obj, name, bool(val)))
    if t == "FloatProperty":
        return W.mem.write(obj + off, struct.pack('<f', float(val)))
    if t == "IntProperty":
        return W.mem.write(obj + off, struct.pack('<i', int(val)))
    if t == "ByteProperty":
        return W.mem.write(obj + off, bytes([int(val) & 0xFF]))
    return False


def _gate_raw(W, obj, name):
    p = W.find(obj, name)
    if not p:
        return None
    t, off = p
    return (off, W.mem.read(obj + off, 4))


def gate_experiment(R, log, mem, mode="1", wait_fn=None, secs=10.0, step=0.01, sleep=time.sleep):
    """mode 1: controller direction speed factors that read 0 -> DefaultWeapon.ini values.
    mode 2: open challenge gate: Game.IsChallengeEnd/IsPlayerChoosing/bTimerCountDown=False, controller bIgnoreMoveInput=0.
    mode 3: both. Re-writes every ~10 ms for secs while the user holds W, prints Location every 1 s, restores originals."""
    hero, ctl = get_hero_ctrl(R)
    if not hero or not ctl:
        log("找不到英雄或控制器。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學習類別結構。")
        return None
    game, _ = gate_objects(R)
    plan = []                                   # (obj, name, value)
    if mode in ("1", "3"):
        for n, v in GATE_FACTORS:
            p = W.find(ctl, n)
            if p and p[0] == "FloatProperty":
                cur = W.val(ctl, n, p[0], p[1])
                if cur is not None and abs(cur) < 1e-6:
                    plan.append((ctl, n, v))
    if mode in ("2", "3"):
        if game:
            for n in ("IsChallengeEnd", "IsPlayerChoosing", "bTimerCountDown"):
                if W.find(game, n):
                    plan.append((game, n, False))
        if W.find(ctl, "bIgnoreMoveInput"):
            plan.append((ctl, "bIgnoreMoveInput", 0))
    if not plan:
        log("沒有需要寫的欄位（係數都不是 0，或找不到欄位），這個方向可以排除。")
        return ["gate_experiment mode %s: nothing to write" % mode]
    orig = [(obj, n, _gate_raw(W, obj, n)) for obj, n, v in plan]
    L = ["要寫入：" + ", ".join("%s=%s" % (n, v) for obj, n, v in plan)]
    log(L[0])
    fl = W.find(hero, "Location")

    def loc():
        b = mem.read(hero + fl[1], 12) if fl else None
        return list(struct.unpack('<3f', b)) if b else None
    if wait_fn:
        wait_fn()
    first = loc()
    t0, nxt, nw, okw = time.time(), 0.0, 0, True
    while True:
        t = time.time() - t0
        if t > secs + 1e-9:
            break
        for obj, n, v in plan:
            okw = _gate_write(W, obj, n, v) and okw
        nw += 1
        if t >= nxt:
            row = "剩 %.1f 秒 | Location %s" % (max(0.0, secs - t), ff(loc(), 0))
            log(row)
            L.append(row)
            nxt += 1.0
        sleep(step)
    last = loc()
    for obj, n, r in orig:
        if r and r[1]:
            mem.write(obj + r[0], r[1])
    end = "結束：寫入 %d 次%s，已還原。Location 起點 %s -> 終點 %s" % (nw, "" if okw else "（有寫入失敗，請用系統管理員身分執行）", ff(first, 0), ff(last, 0))
    if first and last:
        d = ((last[0] - first[0]) ** 2 + (last[1] - first[1]) ** 2) ** 0.5
        end += "；水平移動 %.1f（超過 100 = 這個欄位就是走路的開關）" % d
    log(end)
    return L + [end]


# ---- key G: PersonToSelf / PersonToHorse max speed factor (11-07 10:00) ----
FACTOR_NAMES = ("fPersonToSelfMaxSpeedFactor", "fPersonToHorseMaxSpeedFactor")


def factor_read(R, log):
    """read both controller factors; returns (W, ctl, hero, lines) or None"""
    hero, ctl = get_hero_ctrl(R)
    if not hero or not ctl:
        log("找不到英雄或控制器（請確認已在戰鬥中）。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學習類別結構。")
        return None
    L = ["控制器 %s [%s]" % (R['objs'].name(ctl), R['objs'].clsname(ctl))]
    for n in FACTOR_NAMES:
        p = W.find(ctl, n)
        if p:
            L.append("  %s +0x%03X = %s（正常應為 1.0；約 0 就是走不動的原因）" % (n, p[1], ff(W.val(ctl, n, p[0], p[1]), 0).strip()))
        else:
            L.append("  找不到欄位 %s" % n)
    for l in L:
        log(l)
    return W, ctl, hero, L


def factor_experiment(R, log, mem, mode="1", wait_fn=None, secs=10.0, step=0.01, sleep=time.sleep, value=1.0):
    """mode 1: write both factors = value every ~step s for secs while the user holds W, restore at the end.
    mode 2: write once, leave it (no restore)."""
    r = factor_read(R, lambda x: None)
    if not r:
        log("找不到英雄或控制器。")
        return None
    W, ctl, hero, _ = r
    plan = [(n, W.find(ctl, n)) for n in FACTOR_NAMES]
    plan = [(n, p) for n, p in plan if p and p[0] == "FloatProperty"]
    if not plan:
        log("找不到係數欄位。")
        return None
    orig = [(p[1], mem.read(ctl + p[1], 4)) for n, p in plan]
    fl = W.find(hero, "Location")

    def loc():
        b = mem.read(hero + fl[1], 12) if fl else None
        return list(struct.unpack('<3f', b)) if b else None
    pk = struct.pack('<f', float(value))
    if mode == "2":
        okw = all(mem.write(ctl + p[1], pk) for n, p in plan)
        back = ", ".join("%s=%s" % (n, ff(W.val(ctl, n, p[0], p[1]), 0).strip()) for n, p in plan)
        end = "寫入%s一次（不還原）：%s。請回遊戲自由走走看（W 或 Shift+W）。" % ("成功" if okw else "可能失敗（請用系統管理員身分執行）", back)
        log(end)
        return [end]
    if wait_fn:
        wait_fn()
    first = loc()
    t0, nxt, nw, okw = time.time(), 0.0, 0, True
    L = ["寫入 " + ", ".join("%s=%s" % (n, value) for n, p in plan)]
    while True:
        t = time.time() - t0
        if t > secs + 1e-9:
            break
        for n, p in plan:
            okw = mem.write(ctl + p[1], pk) and okw
        nw += 1
        if t >= nxt:
            row = "剩 %.1f 秒 | Location %s" % (max(0.0, secs - t), ff(loc(), 0))
            log(row)
            L.append(row)
            nxt += 1.0
        sleep(step)
    last = loc()
    for off, raw in orig:
        if raw:
            mem.write(ctl + off, raw)
    end = "結束：寫入 %d 次%s，已還原。Location 起點 %s -> 終點 %s" % (nw, "" if okw else "（有寫入失敗，請用系統管理員身分執行）", ff(first, 0), ff(last, 0))
    if first and last:
        d = ((last[0] - first[0]) ** 2 + (last[1] - first[1]) ** 2) ** 0.5
        end += "；水平移動 %.1f（超過 100 = 這個係數就是走路的開關）" % d
    log(end)
    return L + [end]


def controller_set_field(R, log, mem, can_write, ask=input):
    """generic: write a Float/Int field of the CONTROLLER by name (y to confirm)"""
    r = factor_read(R, lambda x: None)
    if not r:
        log("找不到英雄或控制器。")
        return None
    W, ctl, hero, _ = r
    nm = ask("要改控制器的哪個 Float/Int 欄位？輸入名稱（例如 fPersonToSelfMaxSpeedFactor），不改請按 Enter：").strip()
    if not nm:
        return []
    hit = [(ow, n, t, off) for ow, n, t, off in W.props(ctl) if n == nm and t in ("FloatProperty", "IntProperty")]
    if not hit:
        log("控制器上找不到名為 %s 的 Float/Int 欄位。" % nm)
        return []
    if not can_write:
        log("沒有寫入權限，請用系統管理員身分執行。")
        return []
    ow, n, t, off = hit[0]
    old = W.val(ctl, n, t, off)
    try:
        newv = float(ask("%s 目前是 %s，要改成多少？" % (n, ff(old, 0).strip())).strip())
    except ValueError:
        log("不是數字，取消。")
        return []
    if ask("確定把 %s 從 %s 改成 %s？(y/n)：" % (n, ff(old, 0).strip(), newv)).strip().lower() != "y":
        log("已取消，沒有修改。")
        return []
    ok = mem.write(ctl + off, struct.pack('<f', newv) if t == "FloatProperty" else struct.pack('<i', int(newv)))
    back = W.val(ctl, n, t, off)
    row = "寫入%s，讀回 %s = %s。回遊戲試走。" % ("成功" if ok else "可能失敗", n, ff(back, 0).strip())
    log(row)
    return ["controller wrote %s +0x%X: %s -> %s (read back %s)" % (n, off, ff(old, 0).strip(), newv, ff(back, 0).strip())]


# ---- key I: combined presets (11-07 12:00) ----
# All earlier tests changed ONE group at a time. A preset writes many non-conflicting groups TOGETHER every ~10 ms.
PRESET_DS_SIG = (17000011, 17100001, 17200001, 17300001)    # hero DataSet[0x18..0x1b] gear ids sent by the server (V19+)
PRESET_DS_BASE = 0x18


def _g_factor():
    g = [("ctl", n, v) for n, v in GATE_FACTORS]
    g += [("ctl", "fPersonToSelfMaxSpeedFactor", 1.0), ("ctl", "fPersonToHorseMaxSpeedFactor", 1.0),
          ("ds", 0x26, 1.0), ("ds", 0x27, 1.0)]
    return g


def _g_flags():
    return [("game", "IsChallengeEnd", False), ("game", "IsPlayerChoosing", False), ("game", "bTimerCountDown", False),
            ("game", "bGameReady", True), ("ctl", "bIgnoreMoveInput", False), ("ctl", "bIgnoreLookInput", False),
            ("gri", "bMatchHasBegun", True)]


def _g_pins():
    g = [("hero", "LastValidServerLocation", "LOC"), ("hero", "TooFarFromServerLocationTime", 0.0)]
    g += [("hero", n, False) for n in ("bSlowMove_DTS", "bTurnSlow", "bSlowDown", "bLockSpeed", "bLockLocation")]
    return g


def _g_speed():
    return [("hero", "NormalRunSpeed", 900.0), ("hero", "QuickRunSpeed", 1000.0), ("hero", "QuickRunSpeedWithGroundOnlyEquip", 1000.0),
            ("hero", "GroundSpeed", 900.0), ("hero", "AirSpeed", 900.0), ("hero", "AccelRate", 4000.0),
            ("hero", "ReplicatedMovementSpeedModifier", 3.0), ("hero", "MaxModifier", 3.0)]


def _g_extra():
    return [("ctl", "fMaxSpeedAttenuationValueOnGround", 0.0), ("ctl", "fMaxAccelAttenuationValueOnGround", 0.0),
            ("ctl", "fPlayerMoveStrafeSpeedFactor", 1.0), ("ctl", "fPlayerTurnSlowSpeedFactor", 1.0),
            ("hero", "CustomTimeDilation", 1.0)]


PRESET_NAMES = {1: "P1 速度係數(含DataSet 0x26/0x27)", 2: "P2 = P1 + 挑戰/比賽旗標", 3: "P3 = P2 + 伺服器位置/慢速旗標",
                4: "P4 = P3 + 加大速度", 5: "P5 全開 = P4 + 衰減/縮放/時間膨脹"}


def preset_items(n):
    """cumulative item list for preset n (1..5); later items with the same (target, name) override earlier ones"""
    gs = [_g_factor, _g_flags, _g_pins, _g_speed, _g_extra][:max(1, min(5, n))]
    d = {}
    for f in gs:
        for t, k, v in f():
            d[(t, k)] = v
    return [(t, k, v) for (t, k), v in d.items()]


def find_dataset(mem, regions, chunk=16 << 20, cap=8):
    """addresses of copies of the hero DataSet (N x u32) in game memory, found by the gear-id signature at slots 0x18..0x1b"""
    sig = struct.pack('<4I', *PRESET_DS_SIG)
    out = []
    for base, size in regions:
        off = 0
        while off < size and len(out) < cap:
            nb = min(chunk + 16, size - off)
            b = read_any(mem, base + off, nb)
            if b:
                i = b.find(sig)
                while i >= 0 and i < chunk and len(out) < cap:
                    a = base + off + i - PRESET_DS_BASE * 4
                    d = mem.read(a, 0x30 * 4)
                    if d and u32(d, 0) and 0 < u32(d, 8) < 100000:      # uid != 0, health plausible
                        out.append(a)
                    i = b.find(sig, i + 1)
            off += chunk
    return out


def preset_run(R, log, mem, n, regions=None, wait_fn=None, ask=input, secs=10.0, step=0.01, free_secs=60.0, sleep=time.sleep):
    hero, ctl = get_hero_ctrl(R)
    if not hero or not ctl:
        log("找不到英雄或控制器（請確認已在戰鬥中）。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學習類別結構。")
        return None
    game, gri = gate_objects(R)
    objs = {"hero": hero, "ctl": ctl, "game": game, "gri": gri}
    items, missing, orig = [], [], []
    for t, k, v in preset_items(n):
        if t == "ds":
            continue
        o = objs.get(t)
        p = W.find(o, k) if o else None
        if not p:
            missing.append("%s.%s" % (t, k))
            continue
        ty, off = p
        sz = 12 if ty == "StructProperty" else 1 if ty == "ByteProperty" else 4
        if (v == "LOC") != (ty == "StructProperty") or ty not in ("BoolProperty", "FloatProperty", "IntProperty", "ByteProperty", "StructProperty"):
            missing.append("%s.%s(型別 %s 不符)" % (t, k, ty))
            continue
        r = mem.read(o + off, sz)
        if r is None:
            missing.append("%s.%s(讀不到)" % (t, k))
            continue
        items.append((o, k, v, ty, off))
        orig.append((o + off, r))
    dsa = []
    dvals = [(k, v) for t, k, v in preset_items(n) if t == "ds"]
    if dvals:
        dsa = find_dataset(mem, regions or [])
    dorig = [(a + k * 4, mem.read(a + k * 4, 4)) for a in dsa for k, v in dvals]
    L = ["預設組 %s：寫入欄位 %d 個、DataSet 副本 %d 份" % (PRESET_NAMES.get(n, n), len(items), len(dsa))]
    L.append("  會寫：" + ", ".join("%s=%s" % (k, ("目前位置" if v == "LOC" else v)) for o, k, v, ty, off in items))
    if dvals:
        L.append("  DataSet[0x26],[0x27]=1.0：%s" % (("已找到 %s" % ", ".join("0x%X" % a for a in dsa)) if dsa else "沒找到（略過這項）"))
    if missing:
        L.append("  找不到/略過：" + ", ".join(missing))
    for l in L:
        log(l)
    fl = W.find(hero, "Location")

    def loc():
        b = mem.read(hero + fl[1], 12) if fl else None
        return list(struct.unpack('<3f', b)) if b else None

    def tick():
        ok = True
        cur = None
        for o, k, v, ty, off in items:
            if ty == "BoolProperty":
                ok = bool(_rm_setbool(W, o, k, bool(v))) and ok
            elif v == "LOC":
                cur = cur or mem.read(hero + fl[1], 12)
                ok = bool(cur and mem.write(o + off, cur)) and ok
            elif ty == "FloatProperty":
                ok = mem.write(o + off, struct.pack('<f', float(v))) and ok
            elif ty == "IntProperty":
                ok = mem.write(o + off, struct.pack('<i', int(v))) and ok
            else:
                ok = mem.write(o + off, bytes([int(v) & 0xFF])) and ok
        for a in dsa:
            for k, v in dvals:
                ok = mem.write(a + k * 4, struct.pack('<f', float(v))) and ok
        return ok

    def drive(total, every, tag):
        first = loc()
        t0, nxt, nw, okw = time.time(), 0.0, 0, True
        while True:
            t = time.time() - t0
            if t > total + 1e-9:
                break
            okw = tick() and okw
            nw += 1
            if t >= nxt:
                row = "%s剩 %.0f 秒 | Location %s" % (tag, max(0.0, total - t), ff(loc(), 0))
                log(row)
                L.append(row)
                nxt += every
            sleep(step)
        last = loc()
        end = "%s結束：寫入 %d 次%s。Location 起點 %s -> 終點 %s" % (tag, nw, "" if okw else "（有寫入失敗，請用系統管理員身分執行）", ff(first, 0), ff(last, 0))
        if first and last:
            d = ((last[0] - first[0]) ** 2 + (last[1] - first[1]) ** 2) ** 0.5
            end += "；水平移動 %.1f（超過 100 = 這個組合有效）" % d
        log(end)
        L.append(end)
    try:
        if wait_fn:
            wait_fn()
        drive(secs, 1.0, "")
        a = ask("\n要再寫 %d 秒讓你自由走走看（W、Shift+W、跳躍都試試）嗎？(y/n)：" % int(free_secs)).strip().lower()
        if a == "y":
            log("開始自由走 %d 秒，請回遊戲操作..." % int(free_secs))
            drive(free_secs, 5.0, "自由走 ")
    finally:
        for a_, r in orig + dorig:
            if r:
                mem.write(a_, r)
        log("已把所有被改的欄位還原成原本的值。")
    return L


PROBE_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server", "logs", "pawn_probe_last.txt")


def addr_probe(R, log, modbase, out_path=PROBE_OUT):
    """key H: print absolute addresses for Cheat Engine (read-only). Returns the lines or None."""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學習類別結構。")
        return None
    mem = R['mem']

    def fl(a):
        b = mem.read(a, 4)
        return "%.3f" % struct.unpack('<f', b)[0] if b else "?"
    rows = [("英雄物件 (Pawn)", hero, None), ("控制器 (Controller)", ctl or 0, None)]
    for lab, n in (("Location.X（位置 X）", "Location"), ("Velocity.X（速度 X）", "Velocity"),
                   ("Acceleration.X（加速度 X）", "Acceleration")):
        p = W.find(hero, n)
        rows.append((lab, hero + p[1] if p else 0, "float"))
    p = W.find(hero, "Physics")
    rows.append(("Physics（1 Byte，走路=1）", hero + p[1] if p else 0, "byte"))
    L = ["=" * 60, "  Cheat Engine 用的位址（都是十六進位，直接複製貼上）", "=" * 60]
    for lab, a, kind in rows:
        if not a:
            L.append("  %-28s : 找不到" % lab)
            continue
        cur = ""
        if kind == "float":
            cur = "   目前值 %s  （CE 類型選 Float）" % fl(a)
        elif kind == "byte":
            b = mem.read(a, 1)
            cur = "   目前值 %s  （CE 類型選 Byte）" % (b[0] if b else "?")
        L.append("  %-28s : %X%s" % (lab, a, cur))
    L.append("  %-28s : %X   (Kingdom-Win64-Shipping.exe 基址)" % ("遊戲主模組基址", modbase))
    L.append("  （CE 顯示的 Kingdom-Win64-Shipping.exe+偏移 = 位址 - 基址）")
    L.append("=" * 60)
    for l in L:
        log(l)
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(chr(10).join(L) + chr(10))
        log("已存到 %s" % os.path.normpath(out_path))
    except OSError:
        pass
    return L


# ---------------- option J: hero sync object ("leash target") ----------------
LEASH_OBJ_RVA = 0x195F340   # Win64 exe global DAT_14195f340 = hero sync/state object (+0x14 base pos, +0x20 working pos)
LEASH_PAWN_RVA = 0x195F338  # global DAT_14195f338 = local hero pawn
LEASH_OFFS = (0x14, 0x20)


def leash_experiment(R, log, mem, modbase, wait_fn=None, secs=60.0, step=0.01, sleep=time.sleep, write=True):
    """option J: read DAT_14195f340 (hero sync object); report obj+0x14/+0x20 vs hero Location (read-only).
    write=True: every ~10 ms copy hero Location into obj+0x14 and obj+0x20 (a snap-back to that target becomes a no-op),
    restore the originals at the end. Hypothesis: FUN_140ae0370 teleports the pawn to obj+0x20 (= obj+0x14 + collision push)."""
    hero, ctl = get_hero_ctrl(R)
    if not hero:
        log("找不到英雄。")
        return None
    W = Walker(R)
    if not W.learn(hero):
        log("無法學到類別結構。")
        return None
    fl = W.find(hero, "Location")
    if not fl:
        log("找不到 Location 欄位。")
        return None
    mem_ = mem

    def rq(a):
        b = mem_.read(a, 8)
        return struct.unpack('<Q', b)[0] if b else 0

    def v3(a):
        b = mem_.read(a, 12)
        return list(struct.unpack('<3f', b)) if b else None
    obj, gp = rq(modbase + LEASH_OBJ_RVA), rq(modbase + LEASH_PAWN_RVA)
    L = ["全域 DAT_14195f340（英雄同步物件）= 0x%X；DAT_14195f338（本機英雄）= 0x%X；找到的英雄 = 0x%X %s"
         % (obj, gp, hero, "（一致）" if gp == hero else "（不一致！這個位址可能不對）")]
    log(L[0])
    if not obj:
        log("同步物件指標是 0（戰鬥還沒開始或位址不對）。")
        return L
    loc = v3(hero + fl[1])
    orig = {o: v3(obj + o) for o in LEASH_OFFS}
    L.append("英雄 Location %s；obj+0x14 %s；obj+0x20 %s（obj+0x14 若停在出生點附近 = 拉回目標就是它）"
             % (ff(loc, 0), ff(orig[0x14], 0), ff(orig[0x20], 0)))
    log(L[1])
    if not write or not loc:
        return L
    if wait_fn:
        wait_fn()
    first = v3(hero + fl[1]) or loc
    t0, nxt, nw, okw = time.time(), 0.0, 0, True
    try:
        while True:
            t = time.time() - t0
            if t > secs + 1e-9:
                break
            cur = v3(hero + fl[1])
            if cur:
                raw = struct.pack('<3f', *cur)
                for o in LEASH_OFFS:
                    okw = mem_.write(obj + o, raw) and okw
                nw += 1
            if t >= nxt:
                dist = ((cur[0] - first[0]) ** 2 + (cur[1] - first[1]) ** 2) ** 0.5 if cur else -1
                row = "剩 %.0f 秒 | Location %s | 離起點 %.0f" % (max(0.0, secs - t), ff(cur, 0), dist)
                log(row)
                L.append(row)
                nxt += 5.0
            sleep(step)
    finally:
        for o in LEASH_OFFS:
            if orig[o]:
                mem_.write(obj + o, struct.pack('<3f', *orig[o]))
    end = "結束：共寫入 %d 次%s（已還原原值）。" % (nw, "" if okw else "（有寫入失敗，請用系統管理員身分執行）")
    log(end)
    return L + [end]


def process_age_sec(pid):
    """seconds since the process was created (None if unknown); does NOT touch process memory."""
    try:
        import ctypes
        from ctypes import wintypes as wt
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.OpenProcess.restype = wt.HANDLE
        h = k.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return None
        c, e, kt, ut = (wt.FILETIME(), wt.FILETIME(), wt.FILETIME(), wt.FILETIME())
        ok = k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut))
        k.CloseHandle(h)
        if not ok:
            return None
        t = ((c.dwHighDateTime << 32) | c.dwLowDateTime) / 1e7 - 11644473600
        return max(0.0, time.time() - t)
    except Exception:
        return None


def walk_helper_loop(mem, modbase, locoff, alive_fn, log, step=0.015, status_every=10.0, sleep=time.sleep, max_secs=None):
    """walk helper: forever copy the hero pawn Location into the hero sync object (+0x14, +0x20).
    Re-reads the global pawn/object pointers every pass, so respawn / new battle in the same process is followed.
    Returns why it stopped ('exit' = game process gone, 'timeout')."""
    def rq(a):
        b = mem.read(a, 8)
        return struct.unpack('<Q', b)[0] if b else 0
    t0 = tl = time.time()
    nw = nfail = 0
    state = "wait"
    lastp = lasto = 0
    while True:
        now = time.time()
        if max_secs is not None and now - t0 > max_secs:
            return "timeout"
        pawn, obj = rq(modbase + LEASH_PAWN_RVA), rq(modbase + LEASH_OBJ_RVA)
        ok = False
        if pawn and obj:
            b = mem.read(pawn + locoff, 12)
            if b:
                v = struct.unpack('<3f', b)
                if all(abs(x) < 1e7 for x in v):   # sane numbers only (NaN fails the compare)
                    ok = all([mem.write(obj + o, b) for o in LEASH_OFFS])
        if ok:
            nw += 1
            nfail = 0
            if state != "run" or pawn != lastp or obj != lasto:
                log("英雄在場，保護中（英雄 0x%X）" % pawn)
            state, lastp, lasto = "run", pawn, obj
        else:
            nfail += 1
            if state == "run":
                log("英雄不見了（可能死亡或離開戰鬥），等待重新出現...")
                state = "wait"
            if nfail % 50 == 0 and not alive_fn():
                return "exit"
        if now - tl >= status_every:
            tl = now
            log("[%s] 狀態：%s，已寫入 %d 次" % (time.strftime("%H:%M:%S"), "保護中" if state == "run" else "等待英雄", nw))
            if not alive_fn():
                return "exit"
        sleep(step if state == "run" else 0.2)


def walk_helper(min_age=45.0, poll=2.0):
    """--walkhelper entry: poll for the game WITHOUT opening it, then attach once and keep the leash running."""
    import pawn_probe as pp
    print("走路輔助：等待遊戲程式出現（還沒碰遊戲，不會影響登入）...", flush=True)
    last = 0
    while True:
        exe, pid = pp.find_pid()
        if pid:
            age = process_age_sec(pid)
            if age is None or age >= min_age:
                break
            if time.time() - last > 10:
                print("遊戲已啟動 %.0f 秒，再等一下（滿 %d 秒才會連上）..." % (age, min_age), flush=True)
                last = time.time()
        time.sleep(poll)
    base, img, drva, dsz, cands = static_info()
    while True:
        exe, pid = pp.find_pid()
        if not pid:
            time.sleep(poll)
            continue
        h, can_write = pp.open_proc(pid)
        if not h or not can_write:
            print("沒有寫入權限，請用系統管理員身分執行（用「走路輔助.bat」會自動處理）。")
            return 1
        mb = module_base(pid, exe)
        if not mb:
            time.sleep(poll)
            continue
        mem = ProcMem(h)
        print("已連上 %s (pid %d)，找英雄中（約 10-40 秒）..." % (exe, pid), flush=True)
        R = inspect(mem, mb[0], mb[1], drva, dsz, cands, lambda *x: None)
        if not R:
            print("還找不到英雄，5 秒後重試（請確認已經進入戰鬥、英雄已出現）。", flush=True)
            time.sleep(5)
            continue
        hero, ctl = get_hero_ctrl(R)
        W = Walker(R)
        fl = W.find(hero, "Location") if hero and W.learn(hero) else None
        if not fl:
            print("找不到英雄位置欄位，5 秒後重試。", flush=True)
            time.sleep(5)
            continue
        print("走路輔助啟動：英雄走路不會再被拉回起點。關閉遊戲會自動結束；要停止請關掉這個視窗。", flush=True)
        why = walk_helper_loop(mem, mb[0], fl[1], lambda: bool(pp.find_pid()[1]), lambda t: print(t, flush=True))
        print("遊戲已關閉，走路輔助結束。" if why == "exit" else "結束。", flush=True)
        return 0


def save(lines):
    try:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass


def do_fix(mem, R):
    offs, fl, hero = R['offs'], R['fl'], R['hero']
    if not hero:
        print("沒有找到英雄，不修改。")
        return 1
    ref = None
    for p, cn, on in R['pawns']:
        if p != hero:
            g = fl(p, offs['GroundSpeed'])
            if g and math.isfinite(g[0]) and 50 <= g[0] <= 3000:
                ref = g[0]
                break
    gs = ref or FIX_GROUND
    plan = []
    for name, tiny, val in (("GroundSpeed", 10, gs), ("AirSpeed", 10, gs), ("AccelRate", 100, FIX_ACCEL)):
        cur = fl(hero, offs[name])
        if cur is None or not math.isfinite(cur[0]) or cur[0] < tiny:
            plan.append((name, cur[0] if cur else None, val))
    if not plan:
        print("英雄的 GroundSpeed / AirSpeed / AccelRate 都不是 0 或很小，不需要修改（問題不在這裡）。")
        return 0
    print("\n將要修改：" + "；".join("%s %s -> %g" % (n, c, v) for n, c, v in plan) + "（其他都不動）")
    if input("確定要改嗎？輸入 y 確認，其他任意鍵取消：").strip().lower() != 'y':
        print("已取消，沒有改任何東西。")
        return 0
    for n, c, v in plan:
        ok = mem.write(hero + offs[n], struct.pack('<f', v))
        print("  寫入 %s = %g %s，讀回 %s" % (n, v, "成功" if ok else "失敗(請用系統管理員身分執行)", fmtf(fl(hero, offs[n]))))
    print("已改完。回到遊戲按 W / A / S / D 試試能不能走，再告訴我結果。")
    return 0


# ---------------- selftest with a synthetic game heap ----------------
class MockMem:
    def __init__(self):
        self.regs = []

    def add(self, base, size):
        b = bytearray(size)
        self.regs.append((base, b))
        return b

    def read(self, a, n):
        for base, b in self.regs:
            if base <= a and a + n <= base + len(b):
                return bytes(b[a - base:a - base + n])
        return None

    def write(self, a, data):
        for base, b in self.regs:
            if base <= a and a + len(data) <= base + len(b):
                b[a - base:a - base + len(data)] = data
                return True
        return False


def build_mock():
    BASE, IMG = 0x7ff600000000, 0x2000000
    DRVA, DSZ = 0x100000, 0x20000
    m = MockMem()
    mod = m.add(BASE, IMG)
    HB = 0x20000000
    heap = m.add(HB, 0x400000)
    bump = [0x1000]

    def alloc(n):
        a = bump[0]
        bump[0] += (n + 15) & ~15
        return HB + a, a
    nm = ["None", "ByteProperty", "IntProperty", "BoolProperty", "FloatProperty", "ObjectProperty", "Class", "Object", "Pawn", "Actor",
          "Controller", "PlayerController", "KingdomPawn", "Default__KingdomPawn", "KingdomPlayerController", "Core", "KingdomSyncAIPawn",
          "GroundSpeed", "WaterSpeed", "AirSpeed", "LadderSpeed", "AccelRate", "JumpZ", "Physics", "Velocity", "Location", "Acceleration",
          "bIgnoreMoveInput", "fPersonToSelfMaxSpeedFactor", "fPersonToHorseMaxSpeedFactor", "Hero1", "Soldier1", "Soldier2", "KController0", "PlayerInput", "State", "Walking", "PlayerWalking", "bMoveLocked", "PlayerInput0", "CylinderComponent", "CollisionComponent", "CollisionRadius", "CollisionHeight", "Floor", "MaxStepHeight", "WalkableFloorZ", "Mesh", "Translation", "bCollideWorld", "bBlockActors", "bCollideActors", "SkeletalMeshComponent", "CylComp0", "SkelMesh0", "Tree1"] + PIN_FLOATS + ["Filler%d" % i for i in range(400)]
    ni = {s: i for i, s in enumerate(nm)}
    ptrs_a, ptrs_o = alloc(len(nm) * 8)
    for i, s in enumerate(nm):
        a, o = alloc(0x40)
        heap[o:o + 4] = struct.pack('<I', i)
        heap[o + 0x18:o + 0x18 + len(s) + 1] = s.encode() + b'\0'
        heap[ptrs_o + i * 8:ptrs_o + i * 8 + 8] = struct.pack('<Q', a)
    objl = []

    def mk(name, cls, outer, size=0x400):
        a, o = alloc(size)
        heap[o:o + 8] = struct.pack('<Q', BASE + 0x1234)
        heap[o + 0x40:o + 0x48] = struct.pack('<Q', outer)
        heap[o + 0x48:o + 0x50] = struct.pack('<II', ni[name], 0)
        heap[o + 0x50:o + 0x58] = struct.pack('<Q', cls if cls else a)
        objl.append(a)
        return a, o
    cc, _ = mk("Class", 0, 0)
    pclass = {}
    for n in ("Object", "Actor", "Pawn", "Controller", "PlayerController", "KingdomPawn", "KingdomPlayerController", "FloatProperty",
              "ObjectProperty", "ByteProperty", "BoolProperty", "KingdomSyncAIPawn", "CylinderComponent", "SkeletalMeshComponent"):
        pclass[n] = mk(n, cc, 0)[0]

    PROPLINK = {}

    def prop(name, kind, outer, off, es, mask=1):
        a, o = mk(name, pclass[kind], pclass[outer], 0x140)
        if kind == "BoolProperty":
            heap[o + 0xb8:o + 0xbc] = struct.pack('<I', mask)
        PROPLINK.setdefault(outer, []).append(a)
        heap[o + 0x68:o + 0x70] = struct.pack('<II', 1, es)
        heap[o + 0x90:o + 0x94] = struct.pack('<I', off)
        return a
    prop("GroundSpeed", "FloatProperty", "Actor", 0x10, 4)         # decoy under another class
    for i, n in enumerate(PAWN_FLOATS):
        prop(n, "FloatProperty", "Pawn", 0x2f0 + 4 * i, 4)
    prop("Physics", "ByteProperty", "Actor", 0x7c, 1)
    prop("Velocity", "FloatProperty", "Actor", 0x90, 12)
    prop("Acceleration", "FloatProperty", "Pawn", 0x2d0, 12)
    prop("Pawn", "ObjectProperty", "Controller", 0x2a0, 8)
    prop("bIgnoreMoveInput", "BoolProperty", "PlayerController", 0x3a0, 4)
    prop("fPersonToSelfMaxSpeedFactor", "FloatProperty", "KingdomPlayerController", 0x7a8, 4)
    prop("fPersonToHorseMaxSpeedFactor", "FloatProperty", "KingdomPlayerController", 0x7a4, 4)
    pclass["PlayerInput"] = mk("PlayerInput", cc, 0)[0]
    pclass["State"] = mk("State", cc, 0)[0]
    for i, n in enumerate(PIN_FLOATS[:6]):
        prop(n, "FloatProperty", "PlayerInput", 0x100 + 4 * i, 4)
    prop("PlayerInput", "ObjectProperty", "PlayerController", 0x3b0, 8)
    prop("bMoveLocked", "BoolProperty", "Pawn", 0x310, 4)
    prop("Location", "FloatProperty", "Actor", 0xa0, 12)
    prop("Floor", "FloatProperty", "Pawn", 0xb0, 12)
    prop("MaxStepHeight", "FloatProperty", "Pawn", 0x2e0, 4)
    prop("WalkableFloorZ", "FloatProperty", "Pawn", 0x2e4, 4)
    prop("CylinderComponent", "ObjectProperty", "Pawn", 0x320, 8)
    prop("Mesh", "ObjectProperty", "Pawn", 0x330, 8)
    prop("CollisionComponent", "ObjectProperty", "Actor", 0x340, 8)
    prop("bCollideActors", "BoolProperty", "Actor", 0x3c0, 4, 1)
    prop("bBlockActors", "BoolProperty", "Actor", 0x3c0, 4, 2)
    prop("bCollideWorld", "BoolProperty", "Actor", 0x3c0, 4, 4)
    prop("CollisionRadius", "FloatProperty", "CylinderComponent", 0x100, 4)
    prop("CollisionHeight", "FloatProperty", "CylinderComponent", 0x104, 4)
    prop("Translation", "FloatProperty", "SkeletalMeshComponent", 0x110, 12)
    stw, _ = mk("Walking", pclass["State"], 0)
    stm, _ = mk("PlayerWalking", pclass["State"], 0)
    sup = {"Pawn": "Actor", "Controller": "Actor", "PlayerController": "Controller", "KingdomPawn": "Pawn",
           "KingdomPlayerController": "PlayerController", "KingdomSyncAIPawn": "KingdomPawn", "Actor": "Object", "PlayerInput": "Object", "CylinderComponent": "Object", "SkeletalMeshComponent": "Object"}
    for k, v in sup.items():
        heap[pclass[k] - HB + 0x68:pclass[k] - HB + 0x70] = struct.pack('<Q', pclass[v])
    for cn, plist in PROPLINK.items():
        heap[pclass[cn] - HB + 0x70:pclass[cn] - HB + 0x78] = struct.pack('<Q', plist[0])
        for a, b in zip(plist, plist[1:] + [0]):
            heap[a - HB + 0x60:a - HB + 0x68] = struct.pack('<Q', b)
    for i in range(200):
        mk("Filler%d" % i, pclass["Object"], 0)
    mk("Default__KingdomPawn", pclass["KingdomPawn"], 0)
    hero, ho = mk("Hero1", pclass["KingdomPawn"], 0)
    ai, ao = mk("Soldier1", pclass["KingdomSyncAIPawn"], 0)
    ctl, co = mk("KController0", pclass["KingdomPlayerController"], 0)
    heap[ho + 0x2f0:ho + 0x308] = struct.pack('<6f', 0, 0, 0, 0, 0, 600)
    heap[ho + 0x7c] = 1
    heap[ao + 0x2f0:ao + 0x308] = struct.pack('<6f', 380, 380, 380, 380, 1800, 600)
    heap[co + 0x2a0:co + 0x2a8] = struct.pack('<Q', hero)
    heap[co + 0x7a4:co + 0x7ac] = struct.pack('<2f', 0.0001, 0.0001)
    pin, pio = mk("PlayerInput0", pclass["PlayerInput"], 0)
    heap[co + 0x3b0:co + 0x3b8] = struct.pack('<Q', pin)
    heap[pio + 0x100:pio + 0x118] = struct.pack('<6f', 1.0, 0, 0.5, 0, 0, 0)
    heap[ho + 0x310] = 1
    cyl, cyo = mk("CylComp0", pclass["CylinderComponent"], 0)
    msh, mso = mk("SkelMesh0", pclass["SkeletalMeshComponent"], 0)
    tree, tro = mk("Tree1", pclass["KingdomSyncAIPawn"], 0)
    heap[cyo + 0x100:cyo + 0x108] = struct.pack('<2f', 34.0, 88.0)
    heap[mso + 0x110:mso + 0x11c] = struct.pack('<3f', 0, 0, -88.0)
    heap[ho + 0x320:ho + 0x328] = struct.pack('<Q', cyl)
    heap[ho + 0x340:ho + 0x348] = struct.pack('<Q', cyl)
    heap[ho + 0x330:ho + 0x338] = struct.pack('<Q', msh)
    heap[ho + 0xa0:ho + 0xac] = struct.pack('<3f', 100, 0, 500)
    heap[ho + 0xb0:ho + 0xbc] = struct.pack('<3f', 0, 0, 1)
    heap[ho + 0x2e0:ho + 0x2e8] = struct.pack('<2f', 35.0, 0.7)
    heap[ho + 0x3c0:ho + 0x3c4] = struct.pack('<I', 5)
    heap[ao + 0xa0:ao + 0xac] = struct.pack('<3f', 200, 0, 500)
    heap[tro + 0xa0:tro + 0xac] = struct.pack('<3f', 5000, 0, 500)
    heap[tro + 0x3c0:tro + 0x3c4] = struct.pack('<I', 2)
    heap[ao + 0x3c0:ao + 0x3c4] = struct.pack('<I', 2)
    for obj_o, st in ((ho, stw), (co, stm)):
        fa, fo = alloc(0x40)
        heap[fo:fo + 16] = struct.pack('<QQ', pclass["Pawn"], st)
        heap[obj_o + 0x20:obj_o + 0x28] = struct.pack('<Q', fa)
    arr_a, arr_o = alloc(len(objl) * 8)
    for i, a in enumerate(objl):
        heap[arr_o + i * 8:arr_o + i * 8 + 8] = struct.pack('<Q', a)
    mod[DRVA + 0x100:DRVA + 0x110] = struct.pack('<QII', ptrs_a, len(nm), len(nm) + 100)
    mod[DRVA + 0x300:DRVA + 0x310] = struct.pack('<QII', arr_a, len(objl), len(objl) + 100)
    mod[DRVA + 0x500:DRVA + 0x510] = struct.pack('<QII', HB + 0x1000, 150, 170)      # decoy TArray
    return m, BASE, IMG, DRVA, DSZ, hero


def fl_off_for_test(R, hero):
    W = Walker(R)
    W.learn(hero)
    return W.find(hero, "Location")[1]


def selftest():
    m, base, img, drva, dsz, hero = build_mock()
    msgs = []
    R = inspect(m, base, img, drva, dsz, [], msgs.append, minname=100, minobj=100)
    assert R, msgs
    assert R['gn_rva'] == drva + 0x100 and R['go_rva'] == drva + 0x300, R
    assert (R['nameoff'], R['classoff'], R['outeroff'], R['propoff']) == (0x48, 0x50, 0x40, 0x90), R
    assert R['hero'] == hero
    out = report(m, R)
    print("\n".join(out))
    assert any("Physics=1(Walking)" in l and "GroundSpeed=0 " in l for l in out)
    out = []
    L = watch(R, out.append, secs=1.0, step=0.25, sleep=lambda x: None)
    print("\n".join(out))
    assert L and any("aFwd" in l for l in L) and any("PlayerWalking" in l for l in L) and any("Walking" in l for l in L)
    assert any("P.bMoveLocked=True" in l for l in L)
    out = []
    L = list_props(R, out.append, "Move|Phys")
    print("\n".join(out))
    assert any("bMoveLocked" in l for l in L) and any("Physics" in l for l in L)
    out = []
    L = experiment(R, out.append, m, 3.0, "3", secs=0.1, step=0.05, sleep=lambda x: time.sleep(0.01))
    print("\n".join(out))
    assert L is None and any("SyncVelocity" in l for l in out)  # mock hero has no Sync props
    out = []
    L = collision_check(R, out.append, m)
    print("\n".join(out))
    j = "\n".join(L)
    assert "CollisionRadius=34.00 CollisionHeight=88.00" in j and "bCollideWorld=1 bBlockActors=0 bCollideActors=1" in j
    assert "Floor = (0.00,0.00,1.00)" in j and "Translation=(0.00,0.00,-88.00)" in j and "MaxStepHeight=35.00" in j
    assert "Soldier1" in j and "Tree1" not in j and "1 個" in j and "bBlockActors=1" in j
    out = []
    L = lift_experiment(R, out.append, m, 150.0, secs=0.3, step=0.1, sleep=lambda x: time.sleep(0.01))
    print("\n".join(out))
    assert L and "506" not in L[0] and "650.00" in L[0] and "成功" in L[0]
    b = m.read(hero + 0xa0, 12)
    assert struct.unpack('<3f', b) == (100.0, 0.0, 650.0)
    out = []
    L = pin_experiment(R, out.append, m, "2", secs=0.2, step=0.01, sleep=lambda x: time.sleep(0.005))
    assert L is None and any("LastValidServerLocation" in x for x in out)  # mock hero has no such field
    # option C offline test: hero pos (100,0,508.7); plant f32 UU, f32 metres (x,up,z), and an int*1000 copy
    pos = (100.0, 0.0, 508.7)
    m2 = MockMem()
    reg = m2.add(0x100000, 1 << 16)
    struct.pack_into("<3f", reg, 0x100, 100.2, 0.1, 508.6)
    struct.pack_into("<3f", reg, 0x200, 1.0, 5.087, 0.0)
    struct.pack_into("<3i", reg, 0x300, 1000, 5087, 0)
    struct.pack_into("<3d", reg, 0x400, 100.0, 0.0, 508.7)
    cs = scan_memory(m2, [(0x100000, 1 << 16)], pos, excl=(0x100000 + 0x400, 0x100000 + 0x408), log=lambda x: None)
    kinds = {(c["addr"] - 0x100000, c["name"], c["pn"]) for c in cs}
    assert (0x100, "f32", "xyz") in kinds and (0x200, "f32", "xzy") in kinds and (0x300, "int*1000", "xzy") in kinds, kinds
    c0 = [c for c in cs if c["addr"] == 0x100000 + 0x200][0]
    assert abs(cand_read(m2, c0)[2] - 508.7) < 0.1 and cand_write(m2, c0, [110.0, 0.0, 508.7])
    assert abs(cand_read(m2, c0)[0] - 110.0) < 0.01
    assert narrow(m2, [c0], [110.0, 0, 508.7], [100.0, 0, 508.7])[0][1] == "跟著英雄走"
    out = []
    answers = iter(["", "n", "", "1", ""])
    L = sync_scan(R, out.append, m, [(0x100000, 1 << 16)], ask=lambda q: next(answers), secs=0.1, hold=0, sleep=lambda x: time.sleep(0.005))
    print(chr(10).join(out))
    assert L is None or isinstance(L, list)   # mock hero lacks sync data: just must not crash
    # option D offline test: stuck copy, drive modes, neighbours
    m3 = MockMem()
    r3 = m3.add(0x200000, 1 << 12)
    struct.pack_into("<3f", r3, 0x100, 1.0, 0.0, 5.07)
    struct.pack_into("<f", r3, 0x114, 4.5)
    cd = {"addr": 0x200100, "name": "f32", "sz": 4, "k": 0.01, "perm": (0, 1, 2), "pn": "xyz"}
    cur = [100.0, 0.0, 507.0]
    out = []
    r = drive_cands(m3, [cd], lambda: list(cur), lambda: [1.0, 0.0, 0.0], 1, 0.1, out.append, sleep=lambda x: time.sleep(0.005))
    assert abs(cand_read(m3, cd)[0] - 100.0) < 0.01 and r["ticks"] > 3 and r["over"][id(cd)] == 0, r
    r = drive_cands(m3, [cd], lambda: list(cur), lambda: [1.0, 0.0, 0.0], 2, 0.1, out.append, sleep=lambda x: time.sleep(0.005))
    assert cand_read(m3, cd)[0] > 100.0 + 4.5 * 3, cand_read(m3, cd)
    nl = neighbour_lines(0, cd, neighbours(m3, cd))
    assert any("+20:f4.500" in x for x in nl), nl
    out = []
    answers = iter(["", "", "", "1", "", ""])
    L = stuck_drive(R, out.append, m, [(0x100000, 1 << 16)], ask=lambda q: next(answers, ""), secs=0.1, hold=0, sleep=lambda x: time.sleep(0.005))
    print(chr(10).join(out[:12]))
    assert L is None or isinstance(L, list)
    out = []
    L = speed_fields(R, out.append, m, False, ask=lambda q: "")
    print(chr(10).join(out[:12]))
    assert any("bMoveLocked" in l and "True" in l for l in L), L
    out = []
    L = rootmotion(R, out.append)
    assert L and "Mesh" in L[0]   # mock mesh has no root-motion props: must not crash
    L = rm_experiment(R, out.append, m, "1", secs=0.1, step=0.05, sleep=lambda x: None)
    assert L is None
    out = []
    L = gate_check(R, out.append)
    print(chr(10).join(out[:8]))
    assert L and "KController0" in L[0]
    L = gate_experiment(R, out.append, m, "3", secs=0.05, step=0.01, sleep=lambda x: None)
    assert L is not None
    out = []
    _w, co, _h, _l = factor_read(R, lambda x: None)
    L = factor_experiment(R, out.append, m, "1", secs=0.05, step=0.01, sleep=lambda x: None)
    assert L and any("起點" in x for x in L), L
    assert abs(struct.unpack('<f', m.read(co + 0x7a8, 4))[0] - 0.0001) < 1e-6   # restored
    L = factor_experiment(R, out.append, m, "2")
    assert struct.unpack('<2f', m.read(co + 0x7a4, 8)) == (1.0, 1.0), out
    L = controller_set_field(R, out.append, m, True, ask=(lambda it: lambda q: next(it))(iter(["fPersonToSelfMaxSpeedFactor", "2.5", "y"])))
    assert L and abs(struct.unpack('<f', m.read(co + 0x7a8, 4))[0] - 2.5) < 1e-6, (L, out)
    print(chr(10).join(out[:6]))
    # key I presets
    assert len(preset_items(1)) < len(preset_items(2)) < len(preset_items(3)) < len(preset_items(4)) < len(preset_items(5))
    assert len({(t, k) for t, k, v in preset_items(5)}) == len(preset_items(5))      # no conflicting duplicates
    plant = 0x20000000 + 0x300000
    ds = [0] * 132
    ds[0], ds[2], ds[3] = 10001, 200, 200
    ds[0x18:0x1c] = PRESET_DS_SIG
    m.write(plant, struct.pack("<132I", *ds))
    assert find_dataset(m, [(0x20000000 + 0x2ff000, 0x4000)]) == [plant]
    sv0 = m.read(co + 0x7a8, 4)
    for pn in (1, 3, 5):
        out = []
        L = preset_run(R, out.append, m, pn, regions=[(0x20000000 + 0x2ff000, 0x4000)], secs=0.05, step=0.01, free_secs=0.05,
                       ask=lambda q: "y", sleep=lambda x: None)
        assert L and any("起點" in x for x in L) and any("自由走" in x for x in L), (pn, out)
        assert struct.unpack('<2f', m.read(plant + 0x26 * 4, 8)) == (0.0, 0.0), "ds not restored"
        assert m.read(co + 0x7a8, 4) == sv0, "ctl factor not restored"
    print(chr(10).join(out[:4]))
    import tempfile
    tp = os.path.join(tempfile.mkdtemp(), "x", "probe.txt")
    out = []
    L = addr_probe(R, out.append, base, out_path=tp)
    assert L and any("Location.X" in x and ("%X" % (hero + 0xa0)) in x for x in L), L
    assert any("Velocity.X" in x for x in L) and os.path.exists(tp)
    print(chr(10).join(L[:6]))
    # option J offline test: plant DAT_14195f340 pointer + object; copy then restore
    objp = hero + 0x3000
    assert m.write(base + LEASH_OBJ_RVA, struct.pack('<Q', objp)) and m.write(objp + 0x14, struct.pack('<3f', 0.5, -0.6, 0.0))
    out = []
    L = leash_experiment(R, out.append, m, base, secs=0.2, step=0.01, sleep=lambda x: time.sleep(0.005))
    assert L and any("一致" in x for x in L), out
    assert m.read(objp + 0x14, 12) == struct.pack('<3f', 0.5, -0.6, 0.0), "obj not restored"
    # walk helper loop offline test: follows hero, stops when the "process" is gone
    flo = fl_off_for_test(R, hero)
    m.write(base + LEASH_PAWN_RVA, struct.pack('<Q', hero))
    m.write(hero + flo, struct.pack('<3f', 11.0, 22.0, 33.0))
    out = []
    why = walk_helper_loop(m, base, flo, lambda: True, out.append, step=0.002, sleep=lambda x: time.sleep(0.002), max_secs=0.3)
    assert why == "timeout" and m.read(objp + 0x14, 12) == struct.pack('<3f', 11.0, 22.0, 33.0) and m.read(objp + 0x20, 12) == m.read(objp + 0x14, 12), out
    m.write(base + LEASH_PAWN_RVA, struct.pack('<Q', 0))
    out = []
    why = walk_helper_loop(m, base, flo, lambda: False, out.append, status_every=0.05, sleep=lambda x: time.sleep(0.01), max_secs=3.0)
    assert why == "exit", (why, out)
    print("selftest OK")
    return 0


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    a = sys.argv[1:]
    if "--selftest" in a:
        return selftest()
    if "--walkhelper" in a:
        return walk_helper()
    base, img, drva, dsz, cands = static_info()
    if "--static" in a:
        print("exe: ImageBase 0x%x SizeOfImage 0x%x  .data RVA 0x%x size 0x%x" % (base, img, drva, dsz))
        print("靜態候選（程式碼裡以 *8 索引的全域 TArray，RVA:引用數）:", " ".join("0x%x:%d" % c for c in cands[:12]))
        return 0
    import pawn_probe as pp
    exe, pid = pp.find_pid()
    if not pid:
        print("找不到遊戲程式 (Kingdom-Win64-Shipping.exe)。請先進入戰鬥、英雄出現後再執行。")
        return 1
    h, can_write = pp.open_proc(pid)
    if not h:
        print("無法讀取遊戲記憶體（權限不足）。請對「英雄速度檢查.bat」按右鍵 -> 以系統管理員身分執行。")
        return 1
    mb = module_base(pid, exe)
    if not mb:
        print("讀不到遊戲主模組位址。")
        return 1
    mem = ProcMem(h)
    print("已連上 %s (pid %d) 基址 0x%X，掃描中（約 10-40 秒）..." % (exe, pid, mb[0]))
    R = inspect(mem, mb[0], mb[1], drva, dsz, cands, print)
    if not R:
        return 1
    if "--watch" in a:
        def wait_fn():
            input("\n準備好了：按 Enter 後有 5 秒倒數，請在倒數時切回遊戲視窗，然後「一直按住 W」直到記錄結束（共 8 秒）。")
            for i in range(5, 0, -1):
                print("  %d ..." % i, flush=True)
                time.sleep(1)
            print("  開始！請按住 W", flush=True)
        L = watch(R, print, wait_fn=wait_fn)
        if L:
            save(L)
        return 0 if L else 1
    if "--exp" in a:
        if not can_write:
            print("沒有寫入權限，請用系統管理員身分執行。")
            return 1
        sp = input("速度（預設 3.0，直接按 Enter）：").strip()
        try:
            sp = float(sp) if sp else 3.0
        except ValueError:
            sp = 3.0
        md = input("寫哪一個？1=SyncVelocity（預設） 2=SyncAccelerate 3=兩個都寫 4=直接寫 UE 的 Velocity（x100）：").strip() or "1"
        if md not in ("1", "2", "3", "4"):
            md = "1"
        input("按 Enter 後馬上開始寫入 5 秒；請先把遊戲視窗放在旁邊看得到英雄的位置，寫入時看英雄有沒有往前滑。")
        L = experiment(R, print, mem, sp, md)
        if L:
            save(L)
        return 0 if L else 1
    if "--coll" in a:
        L = collision_check(R, print, mem)
        if L:
            save(L)
        return 0 if L else 1
    if "--lift" in a:
        if not can_write:
            print("沒有寫入權限，請用系統管理員身分執行。")
            return 1
        hs = input("要把英雄升高多少單位？（預設 150，直接按 Enter）：").strip()
        try:
            hs = float(hs) if hs else 150.0
        except ValueError:
            hs = 150.0

        def wait_fn():
            input("\n準備好了：按 Enter 後有 5 秒倒數，請在倒數時切回遊戲視窗並「一直按住 W」。倒數結束時英雄會被升高，之後記錄 5 秒。")
            for i in range(5, 0, -1):
                print("  %d ..." % i, flush=True)
                time.sleep(1)
        L = lift_experiment(R, print, mem, hs, wait_fn=wait_fn)
        if L:
            save(L)
        return 0 if L else 1
    if "--pin" in a:
        if not can_write:
            print("沒有寫入權限，請用系統管理員身分執行。")
            return 1
        md = input("鎖定哪些欄位？1 = 只鎖 LastValidServerLocation（預設）；2 = 再加上 +0x1D00~0x1E00 內其他名稱含 Location/Pos 的欄位：").strip()

        def wait_fn():
            input("\n準備好了：按 Enter 後有 5 秒倒數，請在倒數時切回遊戲視窗並「一直按住 W」。之後 10 秒會一直把伺服器位置欄位寫成英雄目前位置。")
            for i in range(5, 0, -1):
                print("  %d ..." % i, flush=True)
                time.sleep(1)
        L = pin_experiment(R, print, mem, "2" if md == "2" else "1", wait_fn=wait_fn)
        if L:
            save(L)
        return 0 if L else 1
    if "--syncscan" in a:
        if not can_write:
            print("沒有寫入權限，請用系統管理員身分執行。")
            return 1

        def countdown():
            for i in range(5, 0, -1):
                print("  %d ..." % i, flush=True)
                time.sleep(1)
            print("  開始！請按住 W", flush=True)
        L = sync_scan(R, print, mem, list(__import__("pawn_probe").regions(h)), countdown=countdown)
        if L:
            save(L)
        return 0 if L else 1
    if "--stuck" in a:
        if not can_write:
            print("沒有寫入權限，請用系統管理員身分執行。")
            return 1

        def countdown():
            for i in range(5, 0, -1):
                print("  %d ..." % i, flush=True)
                time.sleep(1)
            print("  開始！請按住 W", flush=True)
        L = stuck_drive(R, print, mem, list(__import__("pawn_probe").regions(h)), countdown=countdown)
        if L:
            save(L)
        return 0 if L else 1
    if "--rootmotion" in a:
        L = rootmotion(R, print)
        if not L:
            return 1
        save(L)
        md = input("\n接著做實驗嗎？1 = RootMotionMode 改 RMM_Ignore 並取消暫停動畫；2 = 改 RMM_Velocity + AccelScale(1,1,1)；直接按 Enter = 結束：").strip()
        if md in ("1", "2"):
            if not can_write:
                print("沒有寫入權限，請用系統管理員身分執行。")
                return 1

            def wait_fn():
                input("\n按 Enter 後有 5 秒倒數，請切回遊戲並「一直按住 W」。之後 10 秒會一直寫入，結束時自動還原。")
                for i in range(5, 0, -1):
                    print("  %d ..." % i, flush=True)
                    time.sleep(1)
                print("  開始！請按住 W", flush=True)
            L2 = rm_experiment(R, print, mem, md, wait_fn=wait_fn)
            if L2:
                save(L + L2)
        return 0
    if "--leash" in a:
        L = leash_experiment(R, print, mem, mb[0], write=False)
        if not L:
            return 1
        save(L)
        if not can_write:
            print("沒有寫入權限，請用系統管理員身分執行才能做實驗。")
            return 0
        if input("\n做實驗嗎？（60 秒內一直把「拉回目標」寫成英雄目前位置）輸入 y = 開始，其他 = 結束：").strip().lower() != "y":
            return 0

        def wait_fn():
            input("\n按 Enter 後有 5 秒倒數，請切回遊戲並往同一個方向一直走，超過起點 12 公尺以上，看會不會被拉回起點。")
            for i in range(5, 0, -1):
                print("  %d ..." % i, flush=True)
                time.sleep(1)
        L2 = leash_experiment(R, print, mem, mb[0], wait_fn=wait_fn)
        if L2:
            save(L + L2)
        return 0
    if "--addr" in a:
        return 0 if addr_probe(R, print, mb[0]) else 1
    if "--factor" in a:
        r = factor_read(R, print)
        if not r:
            return 1
        save(r[3])
        md = input("\n接著做什麼？1 = 10 秒內一直把兩個係數寫成 1.0（要一直按住 W，結束自動還原）；2 = 只寫一次 1.0 然後不還原（之後自己走走看）；3 = 改控制器的任一個欄位（輸入名稱和數值）；直接按 Enter = 結束：").strip()
        if md in ("1", "2", "3") and not can_write:
            print("沒有寫入權限，請用系統管理員身分執行。")
            return 1
        if md == "3":
            L2 = controller_set_field(R, print, mem, can_write)
            if L2:
                save(r[3] + L2)
        elif md in ("1", "2"):
            def wait_fn():
                input("\n按 Enter 後有 5 秒倒數，請切回遊戲並「一直按住 W」。之後 10 秒會一直寫入，結束時自動還原。")
                for i in range(5, 0, -1):
                    print("  %d ..." % i, flush=True)
                    time.sleep(1)
                print("  開始！請按住 W", flush=True)
            L2 = factor_experiment(R, print, mem, md, wait_fn=wait_fn)
            if L2:
                save(r[3] + L2)
        return 0
    if "--gate" in a:
        L = gate_check(R, print)
        if not L:
            return 1
        save(L)
        md = input("\n接著做實驗嗎？1 = 把是 0 的移動係數改成正常值；2 = 打開挑戰模式的開關；3 = 兩個都做；直接按 Enter = 結束：").strip()
        if md in ("1", "2", "3"):
            if not can_write:
                print("沒有寫入權限，請用系統管理員身分執行。")
                return 1

            def wait_fn():
                input("\n按 Enter 後有 5 秒倒數，請切回遊戲並「一直按住 W」。之後 10 秒會一直寫入，結束時自動還原。")
                for i in range(5, 0, -1):
                    print("  %d ..." % i, flush=True)
                    time.sleep(1)
                print("  開始！請按住 W", flush=True)
            L2 = gate_experiment(R, print, mem, md, wait_fn=wait_fn)
            if L2:
                save(L + L2)
        return 0
    if "--preset" in a:
        if not can_write:
            print("沒有寫入權限，請用系統管理員身分執行。")
            return 1
        for k in sorted(PRESET_NAMES):
            print("  %d = %s" % (k, PRESET_NAMES[k]))
        md = input("選哪一組？輸入 1 到 5（直接按 Enter = 5 全開）：").strip()
        n = int(md) if md in ("1", "2", "3", "4", "5") else 5
        regions = list(__import__("pawn_probe").regions(h))

        def wait_fn():
            input("\n按 Enter 後有 5 秒倒數，請切回遊戲並「一直按住 W」。之後 10 秒會一直寫入，結束時會問你要不要再寫 60 秒自由走，最後自動還原。")
            for i in range(5, 0, -1):
                print("  %d ..." % i, flush=True)
                time.sleep(1)
            print("  開始！請按住 W", flush=True)
        L = preset_run(R, print, mem, n, regions=regions, wait_fn=wait_fn)
        if L:
            save(L)
        return 0 if L else 1
    if "--speed" in a:
        L = speed_fields(R, print, mem, can_write)
        if L:
            save(L)
        return 0 if L else 1
    if "--time" in a:
        L = time_check(R, print, mem)
        if L:
            save(L)
        return 0 if L else 1
    if "--props" in a:
        f = input("輸入屬性名稱過濾（正規表示式，直接按 Enter 用預設 %s）：" % DEF_FILTER).strip()
        L = list_props(R, print, f or None)
        if L:
            save(L)
        return 0 if L else 1
    lines = report(mem, R)
    print("\n".join(lines))
    save(lines)
    if "--fix" in a:
        if not can_write:
            print("沒有寫入權限，請用系統管理員身分執行。")
            return 1
        return do_fix(mem, R)
    return 0


if __name__ == "__main__":
    sys.exit(main())

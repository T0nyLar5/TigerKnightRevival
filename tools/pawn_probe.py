r"""Hero pawn speed probe. Run WHILE standing in battle (after one jump, then stand still).
Usage: tools\.venv\Scripts\python.exe -I tools\pawn_probe.py [--fix] [--log FILE] [--selftest]
Reads the last 0x2737 ReqPosition from the newest server\logs\battleserver_*.log, scans the game's
private RW memory for that float triple, and looks near each hit for the UE3 Pawn speed block
(GroundSpeed, WaterSpeed, AirSpeed, LadderSpeed, AccelRate, JumpZ). --fix writes 450/450/2048 to the chosen one."""
import ctypes, ctypes.wintypes as wt, glob, itertools, math, os, re, struct, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXES = ["Kingdom-Win64-Shipping.exe", "Kingdom-Win32-Shipping.exe"]
WIN = 0x800
FIX_GROUND, FIX_AIR, FIX_ACCEL = 450.0, 450.0, 2048.0


# ---------- log parsing (same decoding as tools\battle_moves.py) ----------
def uv(b, i):
    r = 0
    s = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7f) << s
        s += 7
        if c < 0x80:
            return r, i


def last_position(path, tail=8_000_000):
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        f.seek(max(0, size - tail))
        data = f.read().decode('utf-8', 'replace')
    last = None
    for m in re.finditer(r"(\d\d:\d\d:\d\d\.\d+) RECV [^\n]*?type_0x2737 body=([0-9a-f ]*)", data):
        last = m
    if not last:
        return None
    b = bytes.fromhex(last[2].replace(' ', ''))
    _, i = uv(b, 0)
    return last[1], struct.unpack('<3f', b[i:i + 12])


# ---------- scanning logic (pure, testable) ----------
def make_patterns(pos):
    """exact byte patterns of the triple in every axis order and a few unit scales."""
    out = {}
    for sc in (1.0, 100.0, 0.01):
        v = [struct.unpack('<f', struct.pack('<f', c * sc))[0] for c in pos]
        for perm in itertools.permutations(range(3)):
            p = struct.pack('<3f', *[v[k] for k in perm])
            out.setdefault(p, "x%g %s" % (sc, ''.join('xyz'[k] for k in perm)))
    return out


def find_all(buf, pat):
    i = buf.find(pat)
    while i >= 0:
        yield i
        i = buf.find(pat, i + 1)


def plausible(v):
    return math.isfinite(v) and 0.0 <= v <= 20000.0


def speed_candidates(buf, base):
    """buf = bytes of a window, base = address of buf[0]. Returns [(score, addr, [6 floats])]."""
    res = []
    for off in range(0, len(buf) - 24 + 1, 4):
        f = struct.unpack_from('<6f', buf, off)
        if not all(plausible(x) for x in f):
            continue
        g, w, a, l, acc, j = f
        if not (100 <= j <= 2000):      # JumpZ must be a real jump value (jumping works)
            continue
        s = 1
        if abs(j - 600) < 1:
            s += 2
        if any(abs(x - d) < 0.01 for x, d in ((acc, 2048), (g, 450), (g, 600), (a, 450), (g, 440), (acc, 4096))):
            s += 2
        if g == w == a == l == acc == 0:
            s += 1                      # all-zero block before JumpZ = the hypothesis
        if sum(1 for x in f[:5] if x == 0 or 1 <= x <= 5000) == 5:
            s += 1
        res.append((s, base + off, list(f)))
    return res


def analyse(read, hits, cap=20):
    """read(addr, n) -> bytes or None. hits = [(addr, label)]. Returns sorted candidates."""
    seen = {}
    for addr, label in hits:
        lo = max(0, addr - WIN)
        b = read(lo, 2 * WIN + 12)
        if not b:
            continue
        for s, a, f in speed_candidates(b, lo):
            d = abs(a - addr)
            if a not in seen or seen[a][0] < s:
                seen[a] = (s, a, f, addr, label, d)
    c = sorted(seen.values(), key=lambda t: (-t[0], t[5]))
    return c[:cap]


# ---------- Windows process memory ----------
k32 = ctypes.WinDLL('kernel32', use_last_error=True)


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("PartitionId", wt.WORD), ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t


def find_pid():
    for exe in EXES:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + exe, "/FO", "CSV", "/NH"],
                             capture_output=True, text=True).stdout
        for line in out.splitlines():
            p = [x.strip('"') for x in line.split('","')]
            if len(p) > 1 and p[0].lower() == exe.lower():
                return exe, int(p[1])
    return None, None


def open_proc(pid):
    rw = 0x0400 | 0x0008 | 0x0010 | 0x0020   # QUERY + VM_OPERATION + VM_READ + VM_WRITE
    h = k32.OpenProcess(rw, False, pid)
    if h:
        return h, True
    h = k32.OpenProcess(0x0400 | 0x0010, False, pid)
    return h, False


def rpm(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got))
    return buf.raw[:got.value] if got.value else None


def regions(h):
    addr = 0
    mbi = MBI()
    while addr < 0x7FFFFFFEFFFF and k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        base = mbi.BaseAddress or 0
        if mbi.State == 0x1000 and mbi.Type == 0x20000 and mbi.Protect in (0x04, 0x40):
            yield base, mbi.RegionSize
        nxt = base + mbi.RegionSize
        if nxt <= addr:
            break
        addr = nxt


def scan(h, pats, chunk=16 << 20):
    hits = []
    total = 0
    for base, size in regions(h):
        off = 0
        while off < size:
            n = min(chunk + 11, size - off)      # 11 bytes overlap so no hit is lost at a chunk edge
            b = rpm(h, base + off, n)
            if b:
                total += len(b)
                for pat, label in pats.items():
                    for i in find_all(b, pat):
                        if i >= chunk:
                            continue             # belongs to the next chunk
                        hits.append((base + off + i, label))
            off += chunk
    return hits, total


# ---------- main ----------
def fmt(i, c):
    s, a, f, hit, label, d = c
    return "%2d. 位址 0x%X  地面速度=%g 水速=%g 空速=%g 梯速=%g 加速=%g 跳力=%g  (分數%d, 離座標%+d)" % (
        i, a, f[0], f[1], f[2], f[3], f[4], f[5], s, a - hit)


def selftest():
    pos = (1.0, 4.17, 0.0001)
    pats = make_patterns(pos)
    mem = bytearray(0x4000)
    mem[0x2000:0x2018] = struct.pack('<6f', 0, 0, 0, 0, 0, 600)
    mem[0x2300:0x230c] = struct.pack('<3f', pos[1], pos[0], pos[2])
    mem[0x100:0x118] = struct.pack('<6f', 1, 2, 3, 4, 5, 6)
    B = 0x10000000
    hits = [(B + i, lab) for p, lab in pats.items() for i in find_all(bytes(mem), p)]
    assert len(hits) == 1, hits
    c = analyse(lambda a, n: bytes(mem[a - B:a - B + n]) if a >= B else bytes(mem[0:n]), hits)
    print(c[:2])
    assert c and c[0][1] == B + 0x2000 and c[0][2][5] == 600
    print("selftest OK:", fmt(1, c[0]))


def main():
    a = sys.argv[1:]
    if "--selftest" in a:
        return selftest()
    fix = "--fix" in a
    logp = a[a.index("--log") + 1] if "--log" in a else None
    if not logp:
        logs = sorted(glob.glob(os.path.join(ROOT, "server", "logs", "battleserver_*.log")))
        if not logs:
            print("找不到戰鬥伺服器紀錄檔 (server\\logs\\battleserver_*.log)。請先跑過一次戰鬥測試。")
            return 1
        logp = logs[-1]
    lp = last_position(logp)
    if not lp:
        print("紀錄檔裡沒有位置訊息 (0x2737)：", logp)
        print("請先在遊戲裡跳一下（按空白鍵），站著不動，再執行本程式。")
        return 1
    ts, pos = lp
    print("紀錄檔：%s\n最後一筆位置（%s）：x=%.4f y=%.4f z=%.4f" % (os.path.basename(logp), ts, *pos))
    exe, pid = find_pid()
    if not pid:
        print("找不到遊戲程式 (Kingdom-Win64-Shipping.exe)。請先進入戰鬥、站在場地裡，再執行本檔案。")
        return 1
    h, can_write = open_proc(pid)
    if not h:
        print("無法讀取遊戲記憶體（權限不足，錯誤碼 %d）。" % ctypes.get_last_error())
        print("請對「英雄速度檢查.bat」按右鍵 -> 以系統管理員身分執行。")
        return 1
    print("已連上 %s (pid %d)，掃描中（約 10-60 秒）..." % (exe, pid))
    t = time.time()
    hits, total = scan(h, make_patterns(pos))
    print("掃描 %d MB，找到 %d 個座標位置，用時 %.0f 秒" % (total >> 20, len(hits), time.time() - t))
    if not hits:
        print("沒找到座標。可能英雄之後又動過；請跳一下、站定不動，重新執行。")
        return 1
    cands = analyse(lambda ad, n: rpm(h, ad, n), hits[:400])
    if not cands:
        print("座標附近沒有找到像速度表的資料（連續 6 個數、最後一個是 100~2000 的跳力）。")
        b = rpm(h, hits[0][0] - 0x40, 0x80)
        if b:
            print("第一個座標位置附近原始資料(float)：", [round(x, 3) for x in struct.unpack('<%df' % (len(b) // 4), b[:len(b) // 4 * 4])])
        return 1
    out = [fmt(i + 1, c) for i, c in enumerate(cands)]
    print("\n候選（第 1 個最可能；請把下面整段貼給我）：")
    print("\n".join(out))
    try:
        with open(os.path.join(ROOT, "server", "logs", "pawn_probe_last.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(out))
    except OSError:
        pass
    if fix:
        if not can_write:
            print("沒有寫入權限，請用系統管理員身分執行。")
            return 1
        ans = input("\n要修改第幾個候選？（直接按 Enter = 第 1 個，輸入 n = 取消）：").strip().lower()
        if ans == 'n':
            print("已取消，沒有改任何東西。")
            return 0
        idx = int(ans) - 1 if ans.isdigit() and 0 < int(ans) <= len(cands) else 0
        ad = cands[idx][1]
        for off, val in ((0, FIX_GROUND), (8, FIX_AIR), (16, FIX_ACCEL)):
            k32.WriteProcessMemory(h, ctypes.c_void_p(ad + off), struct.pack('<f', val), 4, None)
        b = rpm(h, ad, 24)
        print("寫入後讀回：", [round(x, 3) for x in struct.unpack('<6f', b)] if b and len(b) == 24 else "讀不到")
        print("已改完。現在回到遊戲按 W / A / S / D 試試能不能走，再告訴我結果。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

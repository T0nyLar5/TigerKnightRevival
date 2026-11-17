"""Compact summary of newest lobby / battle logs and game client log (<= ~40 lines).
Usage: summarize_logs.py [lobby.log] [battle.log] [client.txt]   (no args = newest of each)"""
import glob, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight\frontend\bin"
HEX = re.compile(r"[0-9A-Fa-f]{60,}")
out = []

def red(s, n=None):
    s = HEX.sub("<hex>", s)
    s = re.sub(r'("psw"\s*:\s*")[^"]{20,}', r'\1<redacted>', s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if n else s

def newest(pat):
    f = glob.glob(pat)
    return max(f, key=os.path.getmtime) if f else None

def lines(path, enc="utf-8"):
    with open(path, encoding=enc, errors="replace") as fh:
        return fh.read().splitlines()

def lobby(p):
    L = lines(p)
    reqs = [l for l in L if "<< REQUEST" in l]
    unh = collections.OrderedDict()
    for i, l in enumerate(L):
        m = re.search(r"UNHANDLED route=(\S+) body=(.*)", l)
        if m:
            r = unh.setdefault(m.group(1), [0, red(m.group(2), 120)]); r[0] += 1
    errs = [l for l in L if re.search(r"handler error|Traceback|exception|Exception", l)]
    cerr = [l for l in L if "connection error" in l]
    closes = sum("CONNECTION CLOSED" in l or "client closed" in l for l in L)
    out.append(f"[lobby] {os.path.basename(p)}: {len(reqs)} requests, {closes} closes, {len(cerr)} conn errors, {len(errs)} handler errors")
    if unh:
        out.append("  UNHANDLED: " + "; ".join(f"{k} x{v[0]} body={v[1]}" for k, v in list(unh.items())[:8]))
        if len(unh) > 8: out.append(f"  ... +{len(unh)-8} more unhandled routes")
    for l in errs[:3]: out.append("  ERR " + red(l, 140))
    for l in cerr[-1:]: out.append("  last conn error: " + red(l, 120))
    out.append("  last requests: " + " | ".join(re.sub(r".*route=(\S+).*", r"\1", l) for l in reqs[-5:]))

def battle(p):
    L = lines(p)
    conns = sum(("TCP CONNECT" in l) or ("CONNECTION" in l and "OPEN" in l.upper()) for l in L)
    cnt = {"C>S": collections.Counter(), "S>C": collections.Counter()}
    first = {}
    for i, l in enumerate(L):
        m = re.search(r"frame at \+\d+: len=(\d+) type=(0x[0-9a-f]+) body=([0-9a-f ]*)", l)
        d = "C>S" if m else None
        if m: name, body = m.group(2), m.group(3)
        else:
            m = re.search(r"\b(RECV|SEND)\b[^:]*?\b(Msg\w+)(.*)", l)
            if not m: continue
            d = "C>S" if m.group(1) == "RECV" else "S>C"; name, body = m.group(2), m.group(3)
        cnt[d][name] += 1
        if (d, name) not in first: first[(d, name)] = red(body.strip(), 40)
    errs = [l for l in L if re.search(r"error|Traceback|exception", l, re.I)]
    out.append(f"[battle] {os.path.basename(p)}: {conns} connections, {len(errs)} errors")
    vl = [l for l in L if re.search(r"VARIANT \d+", l)]
    out.append("  variant: " + (re.sub(r"^\S+ ", "", vl[0])[:110] if vl else "unknown (older server, = step3 / variant 0)"))
    after = [red(re.sub(r"^\S+ RECV \[after spawn\] ", "", l), 80) for l in L if "[after spawn]" in l and "SelfPing" not in l and "MsgPing" not in l]
    if after: out.append("  client msgs after spawn (other than pings): " + " | ".join(after[:6]))
    for d in cnt:
        if cnt[d]: out.append(f"  {d}: " + ", ".join(f"{k} x{v}" for k, v in cnt[d].most_common(10)))
    nf = [f"{d} {n}: {b}" for (d, n), b in first.items()]
    if nf: out.append("  first seen: " + " | ".join(nf[:8]))
    for l in errs[-3:]: out.append("  ERR " + red(l, 140))

def game(p, newer_than):
    L = lines(p, "gbk")
    pat = re.compile(r"ERR|Err|fail|crash|500")
    L2 = [l for l in L if "RegisterCallBack OK" not in l]
    seen, hits = set(), []
    for l in L2:
        if pat.search(l):
            k = re.sub(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d ", "", red(l))
            k = re.sub(r"\d+", "#", k)
            if k not in seen: seen.add(k); hits.append(red(l, 150))
    out.append(f"[game] {os.path.basename(p)}: {len(L)} lines, {len(hits)} distinct error lines (last 10)")
    for h in hits[-10:]: out.append("  " + h)
    dmps = [f for f in glob.glob(os.path.join(GAME, "CRASH*.dmp")) if newer_than is None or os.path.getmtime(f) > newer_than]
    out.append("  crash dump newer than lobby log: " + (", ".join(os.path.basename(d) for d in dmps) if dmps else "none"))

def main():
    a = sys.argv[1:]
    lp = a[0] if len(a) > 0 else newest(os.path.join(ROOT, "server", "logs", "lobby_*.log"))
    bp = a[1] if len(a) > 1 else newest(os.path.join(ROOT, "server", "logs", "battle*_*.log"))
    gp = a[2] if len(a) > 2 else newest(os.path.join(GAME, "log", "client*.txt"))
    if lp: lobby(lp)
    else: out.append("[lobby] no log")
    if bp: battle(bp)
    else: out.append("[battle] no log")
    if gp: game(gp, os.path.getmtime(lp) if lp else None)
    else: out.append("[game] no log")
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    print("\n".join(out))
main()

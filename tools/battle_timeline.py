r"""Compact per-second timeline of a battle server log.
Usage: tools\.venv\Scripts\python.exe -I tools\battle_timeline.py [log] [--from S] [--to S] [--only 0x2754,0x2737] [--max-lines 60]
Default log = newest server\logs\battleserver_*.log. Seconds are counted from 'TCP CONNECT'.
Prefix: '<' client->server, '>' server->client. Names: see notes\battle\msg_dictionary.md
"""
import argparse, glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(HERE, "..", "server", "logs")

# id -> short name (single source for this script; mirrors notes/battle/msg_dictionary.md)
NAMES = {
    0x3e9: "Connect", 0x3ea: "ConnectAck", 0x3eb: "Ping", 0x3ec: "MD5Check", 0x3ee: "PingVal",
    0x3f4: "ClientInfo", 0x2715: "Framework", 0x279c: "SelfPing",
    0x2721: "ReqMove", 0x2737: "ReqPosition", 0x2738: "MoveStart", 0x2739: "MoveEnd",
    0x2754: "CamTurn", 0x272f: "Req272f", 0x2732: "Req2732", 0x2722: "Req2722",
    0x4e20: "CmdSync", 0x4e22: "AddPlayer", 0x4e23: "AddCreature", 0x4e3e: "PlayStateChange",
    0x4e4a: "ControlAi", 0x4e50: "CmdMoveStart", 0x4e51: "CmdMoveEnd", 0x4e73: "MatchEnd",
    0x4e80: "ReBorn", 0x4e91: "UserLoadingFinish", 0x4e92: "LoadingComplete",
    0x4e96: "CountDown", 0x4eca: "CmdGhostPos",
}
SLAVE = {"SlaveAddPlayer": "s1 AddPlayer", "SlaveAddCreature": "s2 AddCreature",
         "SlaveAddPerson": "s3 AddPerson", "SlaveInit": "s7 Init", "SlaveBattleStart": "s8 BattleStart",
         "SlaveBattleEnd": "s9 BattleEnd"}
# long log names (from battle_proto.NAMES) -> id
LONG = {"MsgConnect": 0x3e9, "MsgConnectAck": 0x3ea, "MsgPing": 0x3eb, "MsgMD5Check": 0x3ec,
        "MsgPingVal": 0x3ee, "MsgClientSystemInfo": 0x3f4, "MsgFramework": 0x2715,
        "MsgReqSelfPing": 0x279c, "MsgReqPlayerBodyturn": 0x2754, "MsgCmdPlayStateChange": 0x4e3e,
        "MsgCmdSync": 0x4e20, "MsgCmdAddPlayer": 0x4e22, "MsgCmdAddCreature": 0x4e23,
        "MsgCmdControlAiPlayer": 0x4e4a, "MsgCmdReBorn": 0x4e80, "MsgCmdUserLoadingFinish": 0x4e91,
        "MsgCmdLoadingComplete": 0x4e92, "MsgCmdCountDownUpdate": 0x4e96}

T = re.compile(r"^(\d\d):(\d\d):(\d\d)\.(\d+) (.*)")
TOK = re.compile(r"type_0x([0-9a-f]+)|\b(Msg[A-Za-z0-9]+|Slave[A-Za-z]+)\b")


def label(tok_hex, tok_name):
    if tok_name in SLAVE:
        return SLAVE[tok_name]
    i = int(tok_hex, 16) if tok_hex else LONG.get(tok_name)
    if i is None:
        return tok_name
    return "0x%x %s" % (i, NAMES.get(i, tok_hex and ("type_" + tok_hex) or tok_name))


def ident(lab):
    m = re.match(r"0x([0-9a-f]+) ", lab)
    return int(m.group(1), 16) if m else None


def events(path):
    t0 = None
    for line in open(path, encoding="utf-8", errors="replace"):
        m = T.match(line)
        if not m:
            continue
        h, mi, s, ms, rest = m.groups()
        t = int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000.0
        if rest.startswith("TCP CONNECT"):
            t0 = t
        if t0 is None:
            continue
        if rest.startswith("RECV"):
            m2 = TOK.search(rest.split(" body=")[0])
            if m2:
                yield t - t0, "<", label(*m2.groups())
        elif rest.startswith("SEND"):
            if "inner=[" in rest:
                for part in rest.split("inner=[", 1)[1].split("; "):
                    m2 = TOK.search(part)
                    if m2:
                        yield t - t0, ">", label(*m2.groups())
            elif "frame: MsgFramework" not in rest:
                head = rest.split(": ", 1)[-1]
                m2 = TOK.search(head) or TOK.search(rest)
                if m2:
                    yield t - t0, ">", label(*m2.groups())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?")
    ap.add_argument("--from", dest="t_from", type=float, default=0)
    ap.add_argument("--to", dest="t_to", type=float, default=1e9)
    ap.add_argument("--only", help="comma list of ids, e.g. 0x2754,0x4e22 (slave: 1,3,8 not filterable by id; use names)")
    ap.add_argument("--max-lines", type=int, default=60)
    a = ap.parse_args()
    path = a.log
    if not path:
        logs = glob.glob(os.path.join(LOGDIR, "battleserver_*.log"))
        if not logs:
            sys.exit("no battleserver_*.log found")
        path = max(logs)  # names embed the timestamp
    only = {int(x, 0) for x in a.only.split(",")} if a.only else None
    rows = {}
    for t, d, lab in events(path):
        if not a.t_from <= t < a.t_to:
            continue
        if only is not None and ident(lab) not in only:
            continue
        sec = int(t)
        cell = rows.setdefault(sec, {})
        cell[(d, lab)] = cell.get((d, lab), 0) + 1
    out = ["# %s" % os.path.basename(path)]
    for sec in sorted(rows):
        for d in "<>":
            items = ["%s%s" % (lab, " x%d" % n if n > 1 else "") for (dd, lab), n in rows[sec].items() if dd == d]
            if items:
                out.append("%4ds %s %s" % (sec, d, ", ".join(items)))
    if len(out) - 1 > a.max_lines:
        extra = len(out) - 1 - a.max_lines
        out = out[:a.max_lines + 1] + ["... %d more lines (use --from/--to/--only/--max-lines)" % extra]
    print("\n".join(out))


main()

# -*- coding: utf-8 -*-
"""Tiger Knight fake lobby server v1.  Python standard library only.

  python -I server/lobby.py                 listen on 127.0.0.1:3010-3019, TLS, answer routes from handlers.py
  python -I server/lobby.py --unknown-code 500   unknown routes get {"code":500} instead of {"code":0}
  python -I server/lobby.py --ports 3015
Routes live in handlers.py (ROUTES table).  Logs: console + server/logs/lobby_<timestamp>.log
"""
import argparse
import asyncio
import datetime
import json
import os
import ssl
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # needed because python -I does not add the script directory

import handlers  # noqa: E402
import pomelo as P  # noqa: E402

LOG_DIR = os.path.join(HERE, "logs")


class Log:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.path = os.path.join(LOG_DIR, "lobby_%s.log" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.f = open(self.path, "a", encoding="utf-8", buffering=1)

    def __call__(self, msg=""):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        for line in str(msg).split("\n"):
            out = "[%s] %s" % (ts, line)
            try:
                print(out, flush=True)
            except Exception:
                print(out.encode("ascii", "replace").decode(), flush=True)
            self.f.write(out + "\n")


log = Log()
state = None
conn_counter = 0


def redact(obj):
    """Copy of a request body with secrets (psw) replaced by their length."""
    if isinstance(obj, dict):
        return {k: ("<redacted len=%d>" % len(str(v)) if k == "psw" else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def handle_request(m, say, send):
    route = m["route"] or ("<route code %s>" % m["route_code"])
    try:
        req = json.loads(m["body"].decode("utf-8")) if m["body"] else {}
    except Exception:
        req = {}
    friendly = handlers.FRIENDLY.get(route)
    say("<< REQUEST id=%s route=%s body=%s" % (m["id"], route, js(redact(req))))
    if friendly:
        say("✔ " + friendly[0])
    fn = handlers.ROUTES.get(route)
    if fn is None:
        say("!!!! UNHANDLED route=%s body=%s" % (route, js(redact(req))))
        say("⚠ 遊戲要求了一個我們還沒做的功能：%s（已回覆 code=%d，請把記錄檔交給 Claude）" % (route, handlers.UNKNOWN_CODE))
        resp = {"code": handlers.UNKNOWN_CODE}
    else:
        try:
            resp = fn(req, state)
        except Exception as e:
            say("!! handler for %s crashed: %r" % (route, e))
            say("✘ 處理 %s 時發生錯誤，已回覆 code=500" % route)
            resp = {"code": 500}
    pushes = resp.pop("_push", []) if isinstance(resp, dict) else []
    after = resp.pop("_push_after", []) if isinstance(resp, dict) else []
    for proute, pbody in pushes:          # server pushes (paged data rows) go out BEFORE the response
        send(P.encode_push(proute, pbody))
        say(">> PUSH route=%s body=%s" % (proute, js(pbody)[:300]))
    if m["type"] == P.MSG_REQUEST:
        send(P.encode_response(m["id"], resp))
        say(">> RESPONSE id=%s route=%s body=%s" % (m["id"], route, js(resp)))
        if friendly and resp.get("code") == 0:
            say("✔ " + friendly[1])
    else:
        say("   (notify: no response sent)")
    for item in after:                    # pushes that must arrive AFTER the response (e.g. gameStartup)
        proute, pbody = item[0], item[1]
        if len(item) > 2 and item[2] > 0:   # (route, body, delay_s): sent later so the client UI has finished handling the response
            asyncio.get_event_loop().call_later(item[2], lambda r=proute, b=pbody: (send(P.encode_push(r, b)), say(">> PUSH(delayed) route=%s body=%s" % (r, js(b)[:300]))))
            continue
        send(P.encode_push(proute, pbody))
        say(">> PUSH(after) route=%s body=%s" % (proute, js(pbody)))
        if proute == "gameStartup":
            say("✔ 已通知遊戲啟動戰鬥程式（連線位址 127.0.0.1:7777）")


async def serve_connection(reader, writer, port):
    global conn_counter
    conn_counter += 1
    peer = writer.get_extra_info("peername")
    tag = "#%d:%d" % (conn_counter, port)

    def say(m):
        for i, line in enumerate(str(m).split("\n")):
            log(("[%s] " % tag if i == 0 else "    ") + line)

    say("=== CONNECTION OPENED from %s:%s ===" % (peer[0], peer[1]))
    say("✔ 遊戲連線進來了（埠 %d）" % port)
    start = time.time()
    try:
        first = await asyncio.wait_for(reader.read(65536), 60)
        if not first:
            say("client closed without sending anything")
            return
        if P.looks_like_tls(first):
            while not P.tls_record_complete(first):
                more = await asyncio.wait_for(reader.read(65536), 10)
                if not more:
                    break
                first += more
            ctx = P.get_ctx(say)
            if ctx is None:
                say("✘ 找不到憑證，無法建立加密連線")
                return
            chan = P.TLSChannel(reader, writer, ctx, first)
            try:
                await chan.handshake(time.time() + 15)
            except (ssl.SSLError, ConnectionError, asyncio.TimeoutError) as e:
                say("TLS HANDSHAKE FAILED: %r" % (e,))
                say("✘ 加密連線失敗（遊戲不接受憑證？）")
                return
            say("TLS OK (%s)" % chan.obj.version())
            say("✔ 加密連線成功")
        else:
            say("plaintext connection")
            chan = P.PlainChannel(reader, writer, first)
        parser = P.PackageParser()
        while True:
            try:
                data = await chan.read(300)
            except asyncio.TimeoutError:
                say("no data for 300s, closing")
                return
            except ssl.SSLError as e:
                say("TLS error: %s" % e)
                return
            if not data:
                say("client closed the connection")
                say("✔ 遊戲已斷線")
                return
            try:
                pkgs = parser.feed(data)
            except ValueError as e:
                say("!! %s; closing" % e)
                return
            for t, body in pkgs:
                if t == P.PKG_HANDSHAKE:
                    say("<< HANDSHAKE %s" % body.decode("utf-8", "replace"))
                    chan.write(P.pkg_encode(P.PKG_HANDSHAKE, js(P.HANDSHAKE_RESP).encode()))
                    say(">> HANDSHAKE RESPONSE %s" % js(P.HANDSHAKE_RESP))
                    say("✔ 已回覆遊戲的打招呼（握手）")
                elif t == P.PKG_ACK:
                    say("<< handshake ack (client accepted our handshake)")
                elif t == P.PKG_HEARTBEAT:
                    chan.write(P.pkg_encode(P.PKG_HEARTBEAT))
                    say("<< heartbeat / >> heartbeat reply")
                elif t == P.PKG_DATA:
                    try:
                        m = P.decode_msg(body)
                    except Exception as e:
                        say("!! cannot decode data message: %r hex=%s" % (e, body[:100].hex()))
                        continue
                    handle_request(m, say, chan.write)
                elif t == P.PKG_KICK:
                    say("<< kick")
    except (ConnectionError, OSError, asyncio.TimeoutError) as e:
        say("connection error: %r" % (e,))
    except Exception as e:
        say("handler error: %r" % (e,))
    finally:
        say("=== CONNECTION CLOSED (%.1fs) ===" % (time.time() - start))
        try:
            writer.close()
        except Exception:
            pass


async def amain(args):
    servers = []
    for port in args.ports:
        try:
            s = await asyncio.start_server(lambda r, w, p=port: serve_connection(r, w, p), args.host, port)
            servers.append(s)
            log("listening on %s:%d" % (args.host, port))
        except OSError as e:
            log("!! port %d unavailable (%s); skipping" % (port, e.strerror or e))
    if not servers:
        log("✘ 一個埠都開不起來。是不是已經有另一個監聽程式或假伺服器開著？請先關掉它再試。")
        return 1
    log("player file: %s%s" % (handlers.PLAYER_FILE, " (newly created)" if state.created else ""))
    log("log file: %s" % log.path)
    log("✔ 假伺服器已就緒（%d 個埠）。現在可以啟動遊戲了。關閉這個視窗或按 Ctrl+C 即可停止。" % len(servers))
    while True:
        await asyncio.sleep(0.5)


def parse_ports(spec):
    ports = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            ports += range(int(lo), int(hi) + 1)
        else:
            ports.append(int(part))
    return ports


def main():
    global state
    ap = argparse.ArgumentParser(description="Tiger Knight fake lobby server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--ports", default="3010-3019")
    ap.add_argument("--unknown-code", type=int, default=0, help="code for routes without a handler (default 0)")
    a = ap.parse_args()
    a.ports = parse_ports(a.ports)
    handlers.UNKNOWN_CODE = a.unknown_code
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    state = handlers.State()
    if P.get_ctx(log) is None:
        log("✘ 沒有憑證，無法啟動")
        return 1
    try:
        return asyncio.run(amain(a)) or 0
    except KeyboardInterrupt:
        log("stopped by user (Ctrl+C)")
        return 0


if __name__ == "__main__":
    sys.exit(main())

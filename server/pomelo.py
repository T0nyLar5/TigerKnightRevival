# -*- coding: utf-8 -*-
"""Pomelo framing + TLS helpers for the fake lobby server (stdlib only).
Same wire logic as probe.py (proven against the real client), but importable without side effects."""
import asyncio
import json
import os
import shutil
import ssl
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.join(HERE, "certs")
HOSTNAME = "front1-hk.tk.99.com"
GIT_OPENSSL = r"C:\Program Files\Git\usr\bin\openssl.exe"

PKG_HANDSHAKE, PKG_ACK, PKG_HEARTBEAT, PKG_DATA, PKG_KICK = 1, 2, 3, 4, 5
PKG_NAMES = {1: "HANDSHAKE", 2: "HANDSHAKE_ACK", 3: "HEARTBEAT", 4: "DATA", 5: "KICK"}
MSG_REQUEST, MSG_NOTIFY, MSG_RESPONSE, MSG_PUSH = 0, 1, 2, 3
HANDSHAKE_RESP = {"code": 200, "sys": {"heartbeat": 10, "useDict": False}}


def pkg_encode(ptype, body=b""):
    return bytes([ptype]) + len(body).to_bytes(3, "big") + body


def varint_decode(data, off):
    v, shift = 0, 0
    while off < len(data):
        m = data[off]
        off += 1
        v |= (m & 0x7f) << shift
        shift += 7
        if not m & 0x80:
            return v, off
    raise ValueError("truncated varint")


def varint_encode(v):
    out = bytearray()
    while True:
        b = v & 0x7f
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def decode_msg(body):
    flag = body[0]
    mtype, compressed = flag >> 1, flag & 1
    off = 1
    msg = {"type": mtype, "compressed": bool(compressed), "id": None, "route": None, "route_code": None}
    if mtype in (MSG_REQUEST, MSG_RESPONSE):
        msg["id"], off = varint_decode(body, off)
    if mtype != MSG_RESPONSE:
        if compressed:
            msg["route_code"] = int.from_bytes(body[off:off + 2], "big")
            off += 2
        else:
            n = body[off]
            off += 1
            msg["route"] = body[off:off + n].decode("utf-8", "replace")
            off += n
    msg["body"] = body[off:]
    return msg


def encode_response(msg_id, obj):
    return pkg_encode(PKG_DATA, bytes([MSG_RESPONSE << 1]) + varint_encode(msg_id)
                      + json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def encode_push(route, obj):
    r = route.encode()
    return pkg_encode(PKG_DATA, bytes([MSG_PUSH << 1, len(r)]) + r
                      + json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


class PackageParser:
    """Incremental splitter: feed(bytes) -> [(type, body)]. Raises ValueError on garbage."""

    def __init__(self):
        self.buf = b""

    def feed(self, data):
        self.buf += data
        out = []
        while len(self.buf) >= 4:
            t = self.buf[0]
            n = int.from_bytes(self.buf[1:4], "big")
            if t not in PKG_NAMES or n > (1 << 20):
                raise ValueError("not a Pomelo package (type=%d len=%d)" % (t, n))
            if len(self.buf) < 4 + n:
                break
            out.append((t, self.buf[4:4 + n]))
            self.buf = self.buf[4 + n:]
        return out


# ---------------------------------------------------------------- certificate / TLS
def ensure_cert(say=print):
    cert, key = os.path.join(CERT_DIR, "cert.pem"), os.path.join(CERT_DIR, "key.pem")
    if os.path.exists(cert) and os.path.exists(key):
        return cert, key
    exe = next((c for c in (GIT_OPENSSL, shutil.which("openssl")) if c and os.path.exists(c)), None)
    if not exe:
        say("!! openssl.exe not found (Git for Windows); cannot create certificate")
        return None
    os.makedirs(CERT_DIR, exist_ok=True)
    cnf = os.path.join(CERT_DIR, "openssl_min.cnf")
    with open(cnf, "w") as f:
        f.write("[req]\ndistinguished_name=dn\nprompt=no\n[dn]\nCN=%s\n" % HOSTNAME)
    cmd = [exe, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", cert, "-days", "3650",
           "-sha256", "-subj", "/CN=%s" % HOSTNAME, "-config", cnf,
           "-addext", "subjectAltName=DNS:%s,DNS:*.tk.99.com,IP:127.0.0.1" % HOSTNAME]
    r = subprocess.run(cmd, env=dict(os.environ, OPENSSL_CONF=cnf), capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or not os.path.exists(cert):
        say("!! openssl failed: " + (r.stderr or r.stdout))
        return None
    return cert, key


_ctx = None


def get_ctx(say=print):
    global _ctx
    if _ctx is None:
        paths = ensure_cert(say)
        if not paths:
            return None
        c = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        c.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
        try:
            c.set_ciphers("ALL:@SECLEVEL=0")
        except ssl.SSLError:
            pass
        c.load_cert_chain(*paths)
        _ctx = c
    return _ctx


def looks_like_tls(b):
    return len(b) >= 3 and b[0] == 0x16 and b[1] == 0x03 and b[2] <= 0x04


def tls_record_complete(b):
    return len(b) >= 5 and len(b) >= 5 + int.from_bytes(b[3:5], "big")


class PlainChannel:
    def __init__(self, reader, writer, first=b""):
        self.r, self.w, self.pending = reader, writer, first

    async def read(self, timeout):
        if self.pending:
            d, self.pending = self.pending, b""
            return d
        return await asyncio.wait_for(self.r.read(65536), timeout)

    def write(self, data):
        self.w.write(data)


class TLSChannel:
    def __init__(self, reader, writer, ctx, first):
        self.r, self.w = reader, writer
        self.inc, self.out = ssl.MemoryBIO(), ssl.MemoryBIO()
        self.obj = ctx.wrap_bio(self.inc, self.out, server_side=True)
        self.inc.write(first)

    def _flush(self):
        d = self.out.read()
        if d:
            self.w.write(d)

    async def handshake(self, deadline):
        while True:
            try:
                self.obj.do_handshake()
                self._flush()
                return
            except ssl.SSLWantReadError:
                self._flush()
                raw = await asyncio.wait_for(self.r.read(65536), max(0.1, deadline - time.time()))
                if not raw:
                    raise ConnectionAbortedError("client closed during TLS handshake")
                self.inc.write(raw)

    async def read(self, timeout):
        end = time.time() + timeout
        while True:
            try:
                d = self.obj.read(65536)
                self._flush()
                return d
            except ssl.SSLWantReadError:
                self._flush()
                raw = await asyncio.wait_for(self.r.read(65536), max(0.05, end - time.time()))
                if not raw:
                    return b""
                self.inc.write(raw)
            except ssl.SSLZeroReturnError:
                return b""

    def write(self, data):
        self.obj.write(data)
        self._flush()

#!/usr/bin/env python3
"""LZO1X stream tokenizer: yields (kind, ip0, ip1, op0, op1, lit_ip) per token. kind 'L' literal run (bytes src[lit_ip:lit_ip+op1-op0]),
'M' match, 'E' end marker. Mirrors tools/lzo1x.py (the reference decoder logic)."""
def tokens(src):
    ip = 0; op = 0; out = []; st = 'loop'
    if src[0] > 17:
        t = src[0] - 17; out.append(('L', 0, 1 + t, op, op + t, 1)); ip = 1 + t; op += t; st = 'next' if t < 4 else 'first'
    while True:
        trail = None; t0 = ip
        if st == 'loop':
            t = src[ip]; ip += 1
            if t < 16:
                if t == 0:
                    while src[ip] == 0: t += 255; ip += 1
                    t += 15 + src[ip]; ip += 1
                out.append(('L', t0, ip + t + 3, op, op + t + 3, ip)); ip += t + 3; op += t + 3; st = 'first'; continue
        if st == 'first':
            t = src[ip]; ip += 1
            if t < 16:
                ip += 1; out.append(('M', t0, ip, op, op + 3, None)); op += 3; trail = t & 3
        elif st == 'next':
            t = src[ip]; ip += 1
            if t < 16:
                ip += 1; out.append(('M', t0, ip, op, op + 2, None)); op += 2; trail = t & 3
        if trail is None:
            if t >= 64:
                ip += 1; ln = (t >> 5) + 1; trail = t & 3
            elif t >= 32:
                ln = t & 31
                if ln == 0:
                    while src[ip] == 0: ln += 255; ip += 1
                    ln += 31 + src[ip]; ip += 1
                d = src[ip] | src[ip+1] << 8; ip += 2; ln += 2; trail = d & 3
            else:
                ln = t & 7
                if ln == 0:
                    while src[ip] == 0: ln += 255; ip += 1
                    ln += 7 + src[ip]; ip += 1
                d = src[ip] | src[ip+1] << 8; ip += 2
                if (d >> 2) == 0 and not (t & 8):
                    out.append(('E', t0, ip, op, op, None)); return out
                ln += 2; trail = d & 3
            out.append(('M', t0, ip, op, op + ln, None)); op += ln
        if trail:
            out.append(('L', ip, ip + trail, op, op + trail, ip)); ip += trail; op += trail; st = 'next'
        else:
            st = 'loop'

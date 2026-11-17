"""Pure-python LZO1X decompressor (no deps)."""
def decompress(src):
    ip = 0; o = bytearray()
    def copy_match(m, ln):
        if m < 0: raise ValueError('bad lzo distance')
        for _ in range(ln): o.append(o[m]); m += 1
    st = 'loop'
    if src[0] > 17:
        t = src[0] - 17; ip = 1
        o += src[ip:ip+t]; ip += t
        st = 'next' if t < 4 else 'first'
    while True:
        trail = None
        if st == 'loop':
            t = src[ip]; ip += 1
            if t < 16:
                if t == 0:
                    while src[ip] == 0: t += 255; ip += 1
                    t += 15 + src[ip]; ip += 1
                o += src[ip:ip+t+3]; ip += t + 3
                st = 'first'; continue
        if st == 'first':
            t = src[ip]; ip += 1
            if t < 16:
                copy_match(len(o) - 0x801 - (t >> 2) - (src[ip] << 2), 3); ip += 1
                trail = t & 3
        elif st == 'next':
            t = src[ip]; ip += 1
            if t < 16:
                copy_match(len(o) - 1 - (t >> 2) - (src[ip] << 2), 2); ip += 1
                trail = t & 3
        if trail is None:
            if t >= 64:
                copy_match(len(o) - 1 - ((t >> 2) & 7) - (src[ip] << 3), (t >> 5) + 1); ip += 1
                trail = t & 3
            elif t >= 32:
                ln = t & 31
                if ln == 0:
                    while src[ip] == 0: ln += 255; ip += 1
                    ln += 31 + src[ip]; ip += 1
                d = src[ip] | src[ip+1] << 8; ip += 2
                copy_match(len(o) - 1 - (d >> 2), ln + 2); trail = d & 3
            else:
                ln = t & 7
                if ln == 0:
                    while src[ip] == 0: ln += 255; ip += 1
                    ln += 7 + src[ip]; ip += 1
                d = src[ip] | src[ip+1] << 8; ip += 2
                m = len(o) - ((t & 8) << 11) - (d >> 2)
                if m == len(o): return bytes(o)
                copy_match(m - 0x4000, ln + 2); trail = d & 3
        if trail:
            o += src[ip:ip+trail]; ip += trail; st = 'next'
        else:
            st = 'loop'

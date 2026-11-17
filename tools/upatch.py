#!/usr/bin/env python3
"""Data-driven script mods for KingdomGame.u ("rule book"). Add a dict to PATCHES to add a mod.
Each patch: export path in the package, and edits = list of (old_hex, new_hex) of EQUAL length. The old bytes must occur
EXACTLY once inside that export's serialized data (safety anchor), they are replaced in a copy of the plain package, then
upenc.py re-compresses/re-encrypts only the touched chunks.
usage:
  upatch.py list
  upatch.py build [--only a,b] [--with c] [--out server/mods/KingdomGame.u] [--orig PATH_TO_ORIGINAL_TK01_FILE]
                  [--inplace 0|1 (1: patch literal bytes inside the original LZO stream, file size unchanged)] [--force-chunks 3,..  (re-encode even if unchanged)]
     (needs tools/work/KingdomGame_plain.u = `updec.py plain <orig> tools/work/KingdomGame_plain.u`)
  upatch.py verify-full OUT      (slow, ~10 min: decode the whole output with updec and compare with the patched plain)"""
import sys, os, shutil, hashlib, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import upkg, upenc

GAME_U = r'C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight\KingdomGame\CookedPC\KingdomGame.u'
ORIG_SHA256 = '75bb7a42ffb40db005b8c1650fe8c32e845896c522733396bed558b88e6b4f90'   # unmodified Steam file, 156001509 bytes
BASE_PLAIN = os.path.join(HERE, 'work', 'KingdomGame_plain.u')
NEW_PLAIN = os.path.join(HERE, 'work', 'KingdomGame_patched_plain.u')

def const_false_cond(old_hex):
    """JumpIfNot <target> <cond...>  ->  JumpIfNot <target> EX_False + EX_Nothing padding: the 'if (cond) {zero input}' body is skipped."""
    b = bytes.fromhex(old_hex); assert b[0] == 0x07
    return (b[:3] + b'\x28' + b'\x0b' * (len(b) - 4)).hex()

# UnrealScript token facts: 07 JumpIfNot(u16 target, expr), 28 EX_False, 0b EX_Nothing.
_MOVE_OLD = ('071b0a84847219190174faffff09006afaffff00016afaffff090011faffff000111faffff2a16184c00811919190174faffff09006afa'
             'ffff00016afaffff090011faffff000111faffff0a009affffff002d019affffff1616182000190174faffff090076ffffff001b1027'
             '0000000000001616')
_LOOK_OLD = ('07e60a84847219190174faffff09006afaffff00016afaffff090011faffff000111faffff2a16184c00811919190174faffff09006afa'
             'ffff00016afaffff090011faffff000111faffff0a009affffff002d019affffff1616182000190174faffff090077ffffff001b0b'
             '270000000000001616')

def jump_over(old_hex):
    """JumpIfNot <target> <cond>  ->  Jump <target> <cond-as-dead-statement>: ONE byte changes (0x07 -> 0x06). The body is always skipped.
    Unlike const_false_cond this keeps the token structure, so the engine's in-memory script size (pointers are 8 bytes in memory,
    4 on disk: ScriptBytecodeSize != ScriptStorageSize) stays identical and UStruct::Serialize's size check still passes."""
    b = bytes.fromhex(old_hex); assert b[0] == 0x07
    return (b'' + b[1:]).hex()

PATCHES = [
    dict(name='walk_move_gate', default=True, export='KingdomPlayerInput.PlayerInput',
         desc='PlayerInput(): never zero aForward/aStrafe/aUp (JumpIfNot->Jump, 1 byte; skip GRI==none || !bMatchHasBegun || IsMoveInputIgnored())',
         edits=[(_MOVE_OLD, jump_over(_MOVE_OLD))]),
    dict(name='walk_look_gate', default=False, export='KingdomPlayerInput.PlayerInput',
         desc='PlayerInput(): never zero aTurn/aLookUp (same 1-byte gate removal for look input)',
         edits=[(_LOOK_OLD, jump_over(_LOOK_OLD))]),
    dict(name='walk_move_gate_old', default=False, export='KingdomPlayerInput.PlayerInput',
         desc='BROKEN (user test 11-05: game fails): condition replaced by EX_False+113 EX_Nothing; changes in-memory script size',
         edits=[(_MOVE_OLD, const_false_cond(_MOVE_OLD))]),
]

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 22), b''): h.update(blk)
    return h.hexdigest()

def apply_patches(names):
    pk = upkg.Pkg(BASE_PLAIN); shutil.copyfile(BASE_PLAIN, NEW_PLAIN)
    with open(NEW_PLAIN, 'r+b') as f:
        for p in PATCHES:
            if p['name'] not in names: continue
            (idx,) = pk.find(p['export']); e = pk.exports[idx]; data = bytes(pk.data(idx))
            for old, new in p['edits']:
                o, n = bytes.fromhex(old), bytes.fromhex(new); assert len(o) == len(n), 'length must not change'
                assert data.count(o) == 1, '%s: anchor found %d times' % (p['name'], data.count(o))
                at = e['off'] + data.index(o); f.seek(at); f.write(n)
                print('patched %s at plain file offset %#x (+%d in export, %d bytes)' % (p['name'], at, data.index(o), len(o)))
    pk.m.close(); pk.f.close()

def main(a):
    if not a or a[0] == 'list':
        for p in PATCHES: print(("[x] " if p["default"] else "[ ] ") + p["name"], "-", p["desc"])
        return
    if a[0] == 'verify-full':
        subprocess.check_call([sys.executable, '-I', os.path.join(HERE, 'updec.py'), 'plain', a[1], os.path.join(HERE, 'work', 'verify_plain.u')])
        print('equal' if sha256(os.path.join(HERE, 'work', 'verify_plain.u')) == sha256(NEW_PLAIN) else 'MISMATCH'); return
    assert a[0] == 'build'
    opt = {'--only': None, '--with': '', '--out': os.path.join(ROOT, 'server', 'mods', 'KingdomGame.u'), '--orig': GAME_U,
           '--inplace': '1', '--force-chunks': ''}
    for i in range(1, len(a), 2): opt[a[i]] = a[i+1]
    names = set(opt['--only'].split(',')) if opt['--only'] else {p['name'] for p in PATCHES if p['default']}
    names |= set(x for x in opt['--with'].split(',') if x)
    print('orig sha256 check ...'); assert sha256(opt['--orig']) == ORIG_SHA256, 'orig is not the unmodified game file'
    print('patches:', sorted(names)); apply_patches(names)
    os.makedirs(os.path.dirname(opt['--out']), exist_ok=True)
    upenc.encode(opt['--orig'], BASE_PLAIN, NEW_PLAIN, opt['--out'], inplace=opt['--inplace'] == '1',
                 force={int(x) for x in opt['--force-chunks'].split(',') if x})
    print('out sha256', sha256(opt['--out']))

if __name__ == '__main__': main(sys.argv[1:])

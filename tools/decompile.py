r"""Ghidra headless helper. Usage:
  decompile.py <binary> <addr|name> [more...] [--out file]
  decompile.py <binary> --xref <addr|name|string> [more...] [--out file]
First call imports+analyzes (slow); later calls reuse the project (fast).
Run with the tools venv python (-I)."""
import os, subprocess, sys, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
GH = os.path.join(HERE, "ghidra_12.2_PUBLIC", "support", "analyzeHeadless.bat")
PROJ = os.environ.get("TK_GHIDRA_PROJ") or os.path.join(HERE, "ghidra_projects")  # per-agent copy avoids project locks
SCRIPTS = os.path.join(HERE, "ghidra_scripts")

def find_jdk():
    r"""Ghidra 12.2 needs JDK 25+. Look in tools\jdk* or JAVA_HOME_25."""
    import glob
    c = glob.glob(os.path.join(HERE, "jdk*")) + glob.glob(os.path.join(HERE, "jdk*", "jdk*"))
    c = [d for d in c if os.path.exists(os.path.join(d, "bin", "javac.exe"))]
    return c[0] if c else os.environ.get("JAVA_HOME_25")

def main():
    a = sys.argv[1:]
    outf = None
    if "--out" in a:
        i = a.index("--out"); outf = a[i + 1]; del a[i:i + 2]
    mode = "dec"
    if "--xref" in a:
        a.remove("--xref"); mode = "xref"
    if len(a) < 2:
        print(__doc__); sys.exit(1)
    src, targets = os.path.abspath(a[0]), a[1:]
    # analyzeHeadless.bat breaks on "(x86)" in paths: import from a staged copy
    stage = os.path.join(PROJ, "_in"); os.makedirs(stage, exist_ok=True)
    binary = os.path.join(stage, os.path.basename(src))
    if not os.path.exists(binary) or os.path.getmtime(binary) < os.path.getmtime(src):
        shutil.copy2(src, binary)
    name = os.path.basename(binary)
    pname = name.replace(".", "_")
    os.makedirs(PROJ, exist_ok=True)
    tmp = os.path.join(tempfile.mkdtemp(prefix="tkdec_"), "out.txt")
    base = [GH, PROJ, pname]
    post = ["-scriptPath", SCRIPTS, "-postScript", "TkDecomp.java", tmp, mode] + targets
    if os.path.exists(os.path.join(PROJ, pname + ".gpr")):
        cmd = base + ["-process", name, "-noanalysis"] + post
    else:
        cmd = base + ["-import", binary, "-overwrite"] + post
    env = dict(os.environ)
    jdk = find_jdk()
    if jdk:
        env["JAVA_HOME"] = jdk; env["PATH"] = os.path.join(jdk, "bin") + os.pathsep + env["PATH"]
    if not jdk:
        print("// Ghidra 12.2 needs JDK 25+ (only 21 found). Unpack a JDK 25 into tools/jdk25/ (see notes/ghidra_usage.md)"); sys.exit(2)
    # Felix (OSGi) fails with "data file must be inside the data dir" using the default %APPDATA% dirs:
    # give Ghidra clean, absolute settings/cache dirs inside the repo.
    gh = os.path.join(HERE, "ghidra_home").replace("\\", "/")
    os.makedirs(gh + "/settings", exist_ok=True); os.makedirs(gh + "/cache", exist_ok=True)
    env["JAVA_TOOL_OPTIONS"] = "-Dapplication.settingsdir=%s/settings -Dapplication.cachedir=%s/cache" % (gh, gh)
    env.setdefault("GHIDRA_HEADLESS_MAXMEM", "8G")  # 2G default OOMs on the 21 MB Kingdom exe
    p = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace", cwd=HERE)
    if os.path.exists(tmp):
        txt = open(tmp, encoding="utf-8", errors="replace").read()
    else:
        txt = "// no output; ghidra log tail:\n" + "\n".join((p.stdout + p.stderr).splitlines()[-25:])
    shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
    if outf:
        open(outf, "w", encoding="utf-8").write(txt); print("wrote", outf, len(txt), "chars")
    else:
        sys.stdout.reconfigure(errors="replace"); print(txt)

main()

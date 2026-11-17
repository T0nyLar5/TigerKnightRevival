// Headless helper. args: <outfile> <mode: dec|xref> <target>...
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.mem.*;
import java.io.*;
import java.util.*;

public class TkDecomp extends GhidraScript {
    PrintWriter out;
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        out = new PrintWriter(new OutputStreamWriter(new FileOutputStream(a[0]), "UTF-8"));
        String mode = a[1];
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        for (int i = 2; i < a.length; i++) {
            String t = a[i];
            try {
                if (mode.equals("xref")) xref(t); else dec(di, t);
            } catch (Exception e) { out.println("// error " + t + ": " + e); }
        }
        out.close();
    }

    List<Address> resolve(String t) {
        List<Address> r = new ArrayList<>();
        try {
            String h = t.toLowerCase().startsWith("0x") ? t.substring(2) : t;
            if (h.matches("[0-9a-fA-F]{5,16}") || t.toLowerCase().startsWith("0x")) {
                r.add(currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(Long.parseUnsignedLong(h, 16)));
                return r;
            }
        } catch (Exception e) {}
        SymbolIterator it = currentProgram.getSymbolTable().getSymbols(t);
        while (it.hasNext()) r.add(it.next().getAddress());
        if (r.isEmpty()) {
            SymbolIterator all = currentProgram.getSymbolTable().getAllSymbols(true);
            String lt = t.toLowerCase();
            while (all.hasNext() && r.size() < 5) {
                Symbol s = all.next();
                if (s.getSymbolType() == SymbolType.FUNCTION && s.getName().toLowerCase().contains(lt)) r.add(s.getAddress());
            }
        }
        return r;
    }

    void dec(DecompInterface di, String t) {
        for (Address ad : resolve(t)) {
            Function f = getFunctionContaining(ad);
            if (f == null) { try { disassemble(ad); f = createFunction(ad, null); } catch (Exception ex) { f = null; } }
            if (f == null) { out.println("// no function at " + ad + " (" + t + ")"); continue; }
            DecompileResults r = di.decompileFunction(f, 120, monitor);
            out.println("// ==== " + f.getName() + " @ " + f.getEntryPoint() + " (req " + t + ")");
            if (r.decompileCompleted()) out.println(r.getDecompiledFunction().getC());
            else out.println("// decompile failed: " + r.getErrorMessage());
        }
    }

    void xref(String t) throws Exception {
        List<Address> addrs = resolve(t);
        if (addrs.isEmpty()) {
            // string search in defined data
            String lt = t.toLowerCase();
            for (Data d : currentProgram.getListing().getDefinedData(true)) {
                Object v = d.getValue();
                if (v instanceof String && ((String) v).toLowerCase().contains(lt)) addrs.add(d.getAddress());
                if (addrs.size() >= 10) break;
            }
        }
        for (Address ad : addrs) {
            out.println("// xrefs to " + ad + " (" + t + ")");
            int n = 0;
            for (Reference rf : getReferencesTo(ad)) {
                Function f = getFunctionContaining(rf.getFromAddress());
                out.println("  " + rf.getFromAddress() + " " + rf.getReferenceType() + " in " + (f == null ? "?" : f.getName() + "@" + f.getEntryPoint()));
                if (++n >= 60) { out.println("  ..."); break; }
            }
        }
    }
}

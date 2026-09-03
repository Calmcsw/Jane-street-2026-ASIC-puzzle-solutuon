#!/usr/bin/env python3
"""
netlist_to_json.py - Drive Yosys to read a structural gate-level Verilog
netlist (as produced by spice2v.py) plus the sky130_fd_sc_hd behavioral cell
models, and emit a Yosys JSON netlist (`write_json`) suitable for rendering
with netlistsvg/digitaljs.

This does NOT synthesize or optimize anything. It only:
  1. Reads the structural netlist + the PDK's cell behavioral models
  2. Runs `hierarchy` so Yosys resolves cell instances against real module
     definitions (giving each cell its true function/type, not a blackbox)
  3. Writes out JSON (`write_json`) - a graph of cells/ports/connections

Usage:
    ./netlist_to_json.py NETLIST.v --top TOPMODULE -o OUTPUT.json
                          [--cell-lib PATH_TO_VERILOG_MODELS]

By default it looks for the sky130_fd_sc_hd behavioral models under the PDK
install produced earlier in this session
(jane/pdk_install/share/pdk/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v).
Override with --cell-lib if your cells live elsewhere, or pass it multiple
times to include more than one library file.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

DEFAULT_PDK_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "pdk_install", "share", "pdk"
)
DEFAULT_CELL_LIB = os.path.join(
    DEFAULT_PDK_ROOT, "sky130A", "libs.ref", "sky130_fd_sc_hd", "verilog",
    "sky130_fd_sc_hd.v"
)

YOSYS_CANDIDATES = ["yosys", "yowasp-yosys"]


def find_yosys():
    for candidate in YOSYS_CANDIDATES:
        from shutil import which
        path = which(candidate)
        if path:
            return path
    sys.exit("error: no 'yosys' or 'yowasp-yosys' found on PATH. "
              "Install with: pip3 install --user yowasp-yosys "
              "(and `ln -sf $(python3 -m site --user-base)/bin/yowasp-yosys "
              "$(python3 -m site --user-base)/bin/yosys`)")


SPECIFY_RE = re.compile(r'^[ \t]*specify\b.*?^[ \t]*endspecify\b.*?$',
                         re.DOTALL | re.MULTILINE)


def strip_specify_blocks(src):
    """Remove `specify ... endspecify` timing-check blocks. Yosys's Verilog
    frontend can choke on some conditional-timing-check syntax inside these
    blocks, and we don't need timing data for netlist visualization anyway."""
    return SPECIFY_RE.sub('', src)


def fixup_inout_ports_for_netlistsvg(json_path):
    """netlistsvg's JSON schema only allows port direction 'input' or
    'output' (no 'inout'), but our source netlists may legitimately declare
    'inout' ports (e.g. power/ground rails with no direction info in the
    original SPICE). Rewrite any 'inout' to 'input' purely for
    netlistsvg/digitaljs rendering compatibility - this does not change the
    underlying Verilog netlist, only the JSON copy used for visualization."""
    import json
    with open(json_path) as f:
        data = json.load(f)
    changed = 0
    for module in data.get("modules", {}).values():
        for port in module.get("ports", {}).values():
            if port.get("direction") == "inout":
                port["direction"] = "input"
                changed += 1
        for cell in module.get("cells", {}).values():
            port_directions = cell.get("port_directions", {})
            for pin, direction in port_directions.items():
                if direction == "inout":
                    port_directions[pin] = "input"
                    changed += 1
    if changed:
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
    return changed


POWER_PIN_RE = re.compile(r'^(VGND|VPWR|VNB|VPB|VDD|VSS|GND)$', re.IGNORECASE)


def strip_power_pins(json_path):
    """Remove power/ground rail ports (VGND/VPWR/VNB/VPB/...) from every
    module's port list and every cell instance's connections/port_directions.
    These are supply nets connected to (almost) every single cell, so
    rendering them adds a huge amount of visual clutter without conveying
    any real logic-signal information. Purely cosmetic for
    netlistsvg/digitaljs rendering; does not touch the Verilog netlist."""
    import json
    with open(json_path) as f:
        data = json.load(f)
    removed = 0
    for module in data.get("modules", {}).values():
        ports = module.get("ports", {})
        for name in list(ports.keys()):
            if POWER_PIN_RE.match(name):
                del ports[name]
                removed += 1
        if "port_directions" in module:
            for name in list(module["port_directions"].keys()):
                if POWER_PIN_RE.match(name):
                    del module["port_directions"][name]
        for cell in module.get("cells", {}).values():
            connections = cell.get("connections", {})
            for name in list(connections.keys()):
                if POWER_PIN_RE.match(name):
                    del connections[name]
                    removed += 1
            port_directions = cell.get("port_directions", {})
            for name in list(port_directions.keys()):
                if POWER_PIN_RE.match(name):
                    del port_directions[name]
    if removed:
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
    return removed


def preprocess_cell_lib(path, tmp_dir):
    """Copy a cell-library Verilog file into tmp_dir with specify blocks
    stripped, returning the new path. If the file has no specify blocks,
    the original path is returned unchanged."""
    with open(path) as f:
        src = f.read()
    if 'specify' not in src:
        return path
    stripped = strip_specify_blocks(src)
    out_path = os.path.join(tmp_dir, os.path.basename(path))
    with open(out_path, 'w') as f:
        f.write(stripped)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("netlist", help="Structural Verilog netlist (e.g. puzzle.v)")
    ap.add_argument("--top", required=True, help="Top-level module name")
    ap.add_argument("-o", "--output", default=None,
                     help="Output JSON path (default: <netlist>.json)")
    ap.add_argument("--cell-lib", action="append", default=None,
                     help="Verilog file with cell behavioral models "
                          "(repeatable). Default: sky130_fd_sc_hd.v from the PDK install")
    ap.add_argument("--keep-going", action="store_true",
                     help="Don't stop on missing/blackbox cell modules "
                          "(pass -nostrict-hier equivalent by ignoring hierarchy errors)")
    ap.add_argument("--strip-power-pins", action="store_true",
                     help="Remove VGND/VPWR/VNB/VPB power-rail ports from "
                          "every module/cell in the output JSON, purely for "
                          "cleaner netlistsvg/digitaljs rendering")
    ap.add_argument("--full-cell-bodies", action="store_true",
                     help="Read cell libraries normally (with full internal "
                          "cell bodies) instead of the default '-lib' "
                          "blackbox mode. Blackbox mode (default) only keeps "
                          "each standard cell's port list, discarding its "
                          "internal gate-level/UDP implementation - this "
                          "avoids downstream tools choking on internal "
                          "primitives (e.g. UDP-based flip-flop models) "
                          "and is all we need since we never want to view "
                          "inside a standard cell's own internals anyway.")
    args = ap.parse_args()

    yosys = find_yosys()
    cell_libs = args.cell_lib or [DEFAULT_CELL_LIB]
    for lib in cell_libs:
        if not os.path.isfile(lib):
            sys.exit("error: cell library not found: %s" % lib)
    if not os.path.isfile(args.netlist):
        sys.exit("error: netlist not found: %s" % args.netlist)

    out_path = args.output or (args.netlist.rsplit(".", 1)[0] + ".json")

    with tempfile.TemporaryDirectory(prefix="netlist_to_json_") as tmp_dir:
        processed_libs = [preprocess_cell_lib(lib, tmp_dir) for lib in cell_libs]

        lib_flag = "-sv" if args.full_cell_bodies else "-sv -lib"
        read_cmds = []
        for lib in processed_libs:
            read_cmds.append('read_verilog %s "%s"' % (lib_flag, lib))
        read_cmds.append('read_verilog -sv "%s"' % args.netlist)

        hierarchy_cmd = "hierarchy -top %s" % args.top
        if args.keep_going:
            hierarchy_cmd += " -keep_positionals"

        script = "; ".join(read_cmds + [
            hierarchy_cmd,
            'write_json "%s"' % out_path,
        ])

        cmd = [yosys, "-p", script]
        print("Running: %s" % " ".join(cmd), file=sys.stderr)
        result = subprocess.run(cmd)
        if result.returncode != 0:
            sys.exit("yosys failed with exit code %d" % result.returncode)

    changed = fixup_inout_ports_for_netlistsvg(out_path)
    if changed:
        print("Rewrote %d inout port direction(s) to 'input' for "
              "netlistsvg/digitaljs schema compatibility" % changed, file=sys.stderr)
    if args.strip_power_pins:
        removed = strip_power_pins(out_path)
        if removed:
            print("Stripped %d power-rail port reference(s) for cleaner "
                  "rendering" % removed, file=sys.stderr)
    print("Wrote %s" % out_path, file=sys.stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
generate_skin.py - Build a custom netlistsvg "skin" SVG file that renders
common sky130_fd_sc_hd standard cells as recognizable gate/mux/flip-flop
symbols (AND/OR/NAND/NOR/XOR/XNOR/NOT/BUF shapes, a D flip-flop box, a mux
box) instead of netlistsvg's generic labeled-rectangle fallback.

Cell types not covered here (the many AOI/OAI compound gates such as
a21o/o221a/etc.) are intentionally left uncovered: netlistsvg falls back to
its built-in "generic" box renderer for any cell type it doesn't recognize,
which is still perfectly readable (a labeled box with real pin names), and
hand-drawing accurate shapes for ~30 compound-gate variants is not worth the
effort for a visualization aid. Run generate_skin.py with --stats <json>
to print type coverage.

Usage:
    ./generate_skin.py -o sky130_skin.svg
"""
import argparse

HEADER = '''<svg xmlns="http://www.w3.org/2000/svg"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:s="https://github.com/nturley/netlistsvg"
  width="800" height="300">
  <s:properties>
    <s:layoutEngine
      org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers="35"
      org.eclipse.elk.spacing.nodeNode="35"
      org.eclipse.elk.layered.layering.strategy="LONGEST_PATH"
    />
  </s:properties>
<style>
svg {
  stroke:#000;
  fill:none;
}
text {
  fill:#000;
  stroke:none;
  font-size:9px;
  font-weight: bold;
  font-family: "Courier New", monospace;
}
.nodelabel {
  text-anchor: middle;
}
.inputPortLabel {
  text-anchor: end;
}
.outputPortLabel {
  text-anchor: start;
}
</style>
'''
FALLBACK_ENTRIES = '''
  <g s:type="inputExt" s:width="30" s:height="20">
    <text x="15" y="-4" class="nodelabel $cell_id" s:attribute="ref">input</text>
    <s:alias val="$_inputExt_"/>
    <path d="M0,0 L0,20 L15,20 L30,10 L15,0 Z" class="$cell_id"/>
    <g s:x="28" s:y="10" s:pid="Y"/>
  </g>

  <g s:type="constant" s:width="30" s:height="20">
    <text x="15" y="-4" class="nodelabel $cell_id" s:attribute="ref">constant</text>
    <s:alias val="$_constant_"/>
    <rect width="30" height="20" class="$cell_id"/>
    <g s:x="30" s:y="10" s:pid="Y"/>
  </g>

  <g s:type="outputExt" s:width="30" s:height="20">
    <text x="15" y="-4" class="nodelabel $cell_id" s:attribute="ref">output</text>
    <s:alias val="$_outputExt_"/>
    <path d="M30,0 L30,20 L15,20 L0,10 L15,0 Z" class="$cell_id"/>
    <g s:x="0" s:y="10" s:pid="A"/>
  </g>

  <g s:type="split" s:width="5" s:height="40">
    <rect width="5" height="40" class="splitjoinBody" s:generic="body"/>
    <s:alias val="$_split_"/>
    <g s:x="0" s:y="20" s:pid="in"/>
    <g transform="translate(5, 10)" s:x="4" s:y="10" s:pid="out0">
      <text x="5" y="-4">hi:lo</text>
    </g>
    <g transform="translate(5, 30)" s:x="4" s:y="30" s:pid="out1">
      <text x="5" y="-4">hi:lo</text>
    </g>
  </g>

  <g s:type="join" s:width="4" s:height="40">
    <rect width="5" height="40" class="splitjoinBody" s:generic="body"/>
    <s:alias val="$_join_"/>
    <g s:x="5" s:y="20"  s:pid="out"/>
    <g transform="translate(0, 10)" s:x="0" s:y="10" s:pid="in0">
      <text x="-3" y="-4" class="inputPortLabel">hi:lo</text>
    </g>
    <g transform="translate(0, 30)" s:x="0" s:y="30" s:pid="in1">
      <text x="-3" y="-4" class="inputPortLabel">hi:lo</text>
    </g>
  </g>

  <g s:type="generic" s:width="30" s:height="40">
    <text x="15" y="-4" class="nodelabel $cell_id" s:attribute="ref">generic</text>
    <rect width="30" height="40" s:generic="body" class="$cell_id"/>
    <g transform="translate(30, 10)" s:x="30" s:y="10" s:pid="out0">
      <text x="5" y="-4" style="fill:#000; stroke:none" class="$cell_id">out0</text>
    </g>
    <g transform="translate(30, 30)" s:x="30" s:y="30" s:pid="out1">
      <text x="5" y="-4" style="fill:#000;stroke:none" class="$cell_id">out1</text>
    </g>
    <g transform="translate(0, 10)" s:x="0" s:y="10" s:pid="in0">
      <text x="-3" y="-4" class="inputPortLabel $cell_id">in0</text>
    </g>
    <g transform="translate(0, 30)" s:x="0" s:y="30" s:pid="in1">
      <text x="-3" y="-4" class="inputPortLabel $cell_id">in1</text>
    </g>
  </g>
'''
FOOTER = '</svg>\n'


def input_ys(n_in, h):
    """Evenly spaced Y coordinates along the left edge for n_in input pins."""
    step = h / (n_in + 1.0)
    return [round(step * (i + 1), 1) for i in range(n_in)]


def gate_entry(type_name, kind, in_pids, out_pid, invert_out=False, invert_in_pids=None):
    """kind is one of: and, or, xor, xnor_extra(handled by invert), not"""
    invert_in_pids = invert_in_pids or []
    n = len(in_pids)
    h = max(25.0, 12.0 * n + 8.0)
    w = 30.0
    ys = input_ys(n, h)
    lines = []
    lines.append('  <g s:type="%s" s:width="%g" s:height="%g">' % (type_name, w + (6 if invert_out else 0), h))
    lines.append('    <s:alias val="%s"/>' % type_name)

    if kind == 'and':
        body = 'M0,0 L0,%g L%g,%g A%g %g 0 0 0 %g,0 Z' % (h, w * 0.5, h, w * 0.5, h / 2.0, w * 0.5)
        lines.append('    <path d="%s" class="$cell_id"/>' % body)
        out_x = w
    elif kind == 'or':
        front = ('M0,%g L0,%g L%g,%g A%g %g 0 0 0 %g,0 L0,0'
                 % (h, h, w * 0.6, h, w * 0.6, h / 2.0, w * 0.6))
        back = 'M0,0 A%g %g 0 0 1 0,%g' % (w * 0.5, h / 2.0, h)
        lines.append('    <path d="%s" class="$cell_id"/>' % front)
        lines.append('    <path d="%s" class="$cell_id"/>' % back)
        out_x = w * 0.6
    elif kind == 'xor':
        front = ('M4,%g L4,%g L%g,%g A%g %g 0 0 0 %g,0 L4,0'
                 % (h, h, w * 0.6 + 4, h, w * 0.6, h / 2.0, w * 0.6 + 4))
        back = 'M4,0 A%g %g 0 0 1 4,%g' % (w * 0.5, h / 2.0, h)
        extra_back = 'M0,0 A%g %g 0 0 1 0,%g' % (w * 0.5, h / 2.0, h)
        lines.append('    <path d="%s" class="$cell_id"/>' % front)
        lines.append('    <path d="%s" class="$cell_id"/>' % back)
        lines.append('    <path d="%s" class="$cell_id"/>' % extra_back)
        out_x = w * 0.6 + 4
    elif kind == 'not':
        lines.append('    <path d="M0,0 L0,%g L%g,%g Z" class="$cell_id"/>' % (h, w, h / 2.0))
        out_x = w
    elif kind == 'buf':
        lines.append('    <path d="M0,0 L0,%g L%g,%g Z" class="$cell_id"/>' % (h, w, h / 2.0))
        out_x = w
    else:
        raise ValueError(kind)

    if invert_out:
        cx = out_x + 3
        lines.append('    <circle cx="%g" cy="%g" r="3" class="$cell_id"/>' % (cx, h / 2.0))
        out_x = out_x + 6

    for pid, y in zip(in_pids, ys):
        bubble = ''
        x = 0
        if pid in invert_in_pids:
            lines.append('    <circle cx="-3" cy="%g" r="3" class="$cell_id"/>' % y)
            x = -6
        lines.append('    <g s:x="%g" s:y="%g" s:pid="%s"/>' % (x, y, pid))
    lines.append('    <g s:x="%g" s:y="%g" s:pid="%s"/>' % (out_x, h / 2.0, out_pid))
    lines.append('    <text x="-3" y="-6" class="nodelabel">%s</text>' % type_name.replace('sky130_fd_sc_hd__', ''))
    lines.append('  </g>')
    return '\n'.join(lines)


def dff_entry(type_name, extra_pins):
    """extra_pins: list of (pid, label) for RESET_B/SET_B, drawn on bottom."""
    w, h = 40.0, 50.0
    lines = []
    lines.append('  <g s:type="%s" s:width="%g" s:height="%g">' % (type_name, w, h))
    lines.append('    <s:alias val="%s"/>' % type_name)
    lines.append('    <path d="M0,0 L0,%g L%g,%g L%g,0 Z" class="$cell_id"/>' % (h, w, h, w))
    lines.append('    <path d="M0,%g L6,%g L0,%g" class="$cell_id"/>' % (h - 10, h - 5, h))
    lines.append('    <g s:x="0" s:y="%g" s:pid="D"/>' % (h * 0.3))
    lines.append('    <g s:x="0" s:y="%g" s:pid="CLK"/>' % (h - 5))
    lines.append('    <g s:x="%g" s:y="%g" s:pid="Q"/>' % (w, h * 0.3))
    for i, (pid, label) in enumerate(extra_pins):
        lines.append('    <g s:x="%g" s:y="%g" s:pid="%s"/>' % (w * (i + 1) / (len(extra_pins) + 1), h, pid))
    lines.append('    <text x="2" y="-6" class="nodelabel">%s</text>' % type_name.replace('sky130_fd_sc_hd__', ''))
    lines.append('    <text x="2" y="%g" style="font-size:8px">D</text>' % (h * 0.3 - 3))
    lines.append('    <text x="%g" y="%g" style="font-size:8px" class="outputPortLabel">Q</text>' % (w - 10, h * 0.3 - 3))
    lines.append('  </g>')
    return '\n'.join(lines)


def mux2_entry():
    w, h = 25.0, 40.0
    lines = []
    lines.append('  <g s:type="sky130_fd_sc_hd__mux2_1" s:width="%g" s:height="%g">' % (w, h))
    lines.append('    <s:alias val="sky130_fd_sc_hd__mux2_1"/>')
    lines.append('    <path d="M0,0 L%g,%g L%g,%g L0,%g Z" class="$cell_id"/>' % (w, h * 0.25, w, h * 0.75, h))
    lines.append('    <g s:x="0" s:y="%g" s:pid="A0"/>' % (h * 0.2))
    lines.append('    <g s:x="0" s:y="%g" s:pid="A1"/>' % (h * 0.8))
    lines.append('    <g s:x="%g" s:y="%g" s:pid="S"/>' % (w * 0.5, h))
    lines.append('    <g s:x="%g" s:y="%g" s:pid="X"/>' % (w, h * 0.5))
    lines.append('    <text x="2" y="%g" style="font-size:8px">0</text>' % (h * 0.2 - 3))
    lines.append('    <text x="2" y="%g" style="font-size:8px">1</text>' % (h * 0.8 - 3))
    lines.append('    <text x="10" y="-6" class="nodelabel">mux2</text>')
    lines.append('  </g>')
    return '\n'.join(lines)


def conb_entry():
    w, h = 20.0, 20.0
    lines = []
    lines.append('  <g s:type="sky130_fd_sc_hd__conb_1" s:width="%g" s:height="%g">' % (w, h))
    lines.append('    <s:alias val="sky130_fd_sc_hd__conb_1"/>')
    lines.append('    <path d="M0,0 L0,%g L%g,%g L%g,0 Z" class="$cell_id"/>' % (h, w, h, w))
    lines.append('    <g s:x="%g" s:y="5" s:pid="HI"/>' % w)
    lines.append('    <g s:x="%g" s:y="15" s:pid="LO"/>' % w)
    lines.append('    <text x="2" y="12" style="font-size:8px">1/0</text>')
    lines.append('  </g>')
    return '\n'.join(lines)


def build_skin():
    entries = []

    # inverter / buffers (non-inverting) --------------------------------
    entries.append(gate_entry('sky130_fd_sc_hd__inv_2', 'not', ['A'], 'Y', invert_out=True))
    for name in ['sky130_fd_sc_hd__buf_2', 'sky130_fd_sc_hd__clkbuf_4',
                 'sky130_fd_sc_hd__clkbuf_8', 'sky130_fd_sc_hd__clkbuf_16']:
        entries.append(gate_entry(name, 'buf', ['A'], 'X'))

    # AND family ----------------------------------------------------------
    entries.append(gate_entry('sky130_fd_sc_hd__and2_2', 'and', ['A', 'B'], 'X'))
    entries.append(gate_entry('sky130_fd_sc_hd__and2b_2', 'and', ['A_N', 'B'], 'X', invert_in_pids=['A_N']))
    entries.append(gate_entry('sky130_fd_sc_hd__and3_2', 'and', ['A', 'B', 'C'], 'X'))
    entries.append(gate_entry('sky130_fd_sc_hd__and3b_2', 'and', ['A_N', 'B', 'C'], 'X', invert_in_pids=['A_N']))
    entries.append(gate_entry('sky130_fd_sc_hd__and4_2', 'and', ['A', 'B', 'C', 'D'], 'X'))
    entries.append(gate_entry('sky130_fd_sc_hd__and4b_2', 'and', ['A_N', 'B', 'C', 'D'], 'X', invert_in_pids=['A_N']))
    entries.append(gate_entry('sky130_fd_sc_hd__and4bb_2', 'and', ['A_N', 'B_N', 'C', 'D'], 'X', invert_in_pids=['A_N', 'B_N']))

    # NAND family -----------------------------------------------------------
    entries.append(gate_entry('sky130_fd_sc_hd__nand2_2', 'and', ['A', 'B'], 'Y', invert_out=True))
    entries.append(gate_entry('sky130_fd_sc_hd__nand2b_2', 'and', ['A_N', 'B'], 'Y', invert_out=True, invert_in_pids=['A_N']))
    entries.append(gate_entry('sky130_fd_sc_hd__nand3_2', 'and', ['A', 'B', 'C'], 'Y', invert_out=True))
    entries.append(gate_entry('sky130_fd_sc_hd__nand3b_2', 'and', ['A_N', 'B', 'C'], 'Y', invert_out=True, invert_in_pids=['A_N']))
    entries.append(gate_entry('sky130_fd_sc_hd__nand4_2', 'and', ['A', 'B', 'C', 'D'], 'Y', invert_out=True))

    # OR family ---------------------------------------------------------
    entries.append(gate_entry('sky130_fd_sc_hd__or2_2', 'or', ['A', 'B'], 'X'))
    entries.append(gate_entry('sky130_fd_sc_hd__or3_2', 'or', ['A', 'B', 'C'], 'X'))
    entries.append(gate_entry('sky130_fd_sc_hd__or3b_2', 'or', ['A', 'B', 'C_N'], 'X', invert_in_pids=['C_N']))
    entries.append(gate_entry('sky130_fd_sc_hd__or4_2', 'or', ['A', 'B', 'C', 'D'], 'X'))
    entries.append(gate_entry('sky130_fd_sc_hd__or4b_2', 'or', ['A', 'B', 'C', 'D_N'], 'X', invert_in_pids=['D_N']))
    entries.append(gate_entry('sky130_fd_sc_hd__or4bb_2', 'or', ['A', 'B', 'C_N', 'D_N'], 'X', invert_in_pids=['C_N', 'D_N']))

    # NOR family ----------------------------------------------------------
    entries.append(gate_entry('sky130_fd_sc_hd__nor2_2', 'or', ['A', 'B'], 'Y', invert_out=True))
    entries.append(gate_entry('sky130_fd_sc_hd__nor3_2', 'or', ['A', 'B', 'C'], 'Y', invert_out=True))
    entries.append(gate_entry('sky130_fd_sc_hd__nor3b_2', 'or', ['A', 'B', 'C_N'], 'Y', invert_out=True, invert_in_pids=['C_N']))
    entries.append(gate_entry('sky130_fd_sc_hd__nor4_2', 'or', ['A', 'B', 'C', 'D'], 'Y', invert_out=True))
    entries.append(gate_entry('sky130_fd_sc_hd__nor4b_2', 'or', ['A', 'B', 'C', 'D_N'], 'Y', invert_out=True, invert_in_pids=['D_N']))

    # XOR/XNOR -----------------------------------------------------------
    entries.append(gate_entry('sky130_fd_sc_hd__xor2_2', 'xor', ['A', 'B'], 'X'))
    entries.append(gate_entry('sky130_fd_sc_hd__xnor2_2', 'xor', ['A', 'B'], 'Y', invert_out=True))

    # mux / dff / tie cells -----------------------------------------------
    entries.append(mux2_entry())
    entries.append(dff_entry('sky130_fd_sc_hd__dfxtp_2', []))
    entries.append(dff_entry('sky130_fd_sc_hd__dfrtp_2', [('RESET_B', 'R')]))
    entries.append(dff_entry('sky130_fd_sc_hd__dfstp_2', [('SET_B', 'S')]))
    entries.append(conb_entry())

    return HEADER + '\n'.join(entries) + '\n' + FALLBACK_ENTRIES + '\n' + FOOTER


def print_stats(json_path, skin_types):
    import json
    d = json.load(open(json_path))
    # find the module with the most cells (heuristically the top)
    top = max(d['modules'].values(), key=lambda m: len(m.get('cells', {})))
    from collections import Counter
    c = Counter(cell['type'] for cell in top['cells'].values())
    covered = sum(n for t, n in c.items() if t in skin_types)
    total = sum(c.values())
    print("%s: %d/%d cell instances (%.0f%%) have custom symbols; "
          "remaining use netlistsvg's generic box fallback" %
          (json_path, covered, total, 100.0 * covered / total if total else 0))
    uncovered = sorted((t, n) for t, n in c.items() if t not in skin_types)
    if uncovered:
        print("  uncovered types:", ", ".join("%s(%d)" % tn for tn in uncovered))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", default="sky130_skin.svg")
    ap.add_argument("--stats", action="append", default=[],
                     help="Yosys JSON file(s) to report symbol-coverage stats for")
    args = ap.parse_args()

    skin = build_skin()
    with open(args.output, "w") as f:
        f.write(skin)
    print("Wrote %s" % args.output)

    if args.stats:
        import re as _re
        types = set(_re.findall(r's:type="(sky130_fd_sc_hd__\w+)"', skin))
        for path in args.stats:
            print_stats(path, types)


if __name__ == "__main__":
    main()

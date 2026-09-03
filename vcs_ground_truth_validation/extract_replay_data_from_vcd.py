#!/usr/bin/env python3
"""
Stage 04: Reconstruct the per-cycle replay-data file
(replay_data_from_real_vcd.txt) from the raw real-chip capture
(example_inputs.vcd).

This is a from-scratch VCD parser for the puzzle chip's simple, flat
top-level scope (clk, rst_n, enable, I, O[7:0], success -- see the
$var lines at the top of the VCD). It samples all signals once per clock
period. Output format matches replay_data_from_real_vcd.txt: one line per
cycle, columns "rst_n enable I O success" (O printed as an 8-bit decimal
value 0-255).

Usage:
    python3 extract_replay_data_from_vcd.py example_inputs.vcd > replay_data_regenerated.txt
    diff replay_data_regenerated.txt replay_data_from_real_vcd.txt
"""
import sys

IDS = {'!': 'clk', '"': 'rst_n', '#': 'enable', '$': 'I', '%': 'O', '&': 'success'}


def parse_vcd(path):
    vals = {v: None for v in IDS.values()}
    t = None
    rows = []
    in_dump = False
    with open(path) as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('$enddefinitions'):
                in_dump = True
                continue
            if not in_dump:
                continue
            line = line.strip()
            if not line or line.startswith('$'):
                continue
            if line.startswith('#'):
                if t is not None:
                    rows.append((t, dict(vals)))
                t = int(line[1:])
                continue
            if line[0] in '01xXzZ':
                val, ident = line[0], line[1:]
                if ident in IDS:
                    vals[IDS[ident]] = val
            elif line[0] == 'b':
                parts = line.split()
                binval, ident = parts[0][1:], parts[1]
                if ident in IDS:
                    vals[IDS[ident]] = binval
        if t is not None:
            rows.append((t, dict(vals)))
    return rows


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <example_inputs.vcd>", file=sys.stderr)
        sys.exit(1)

    rows = parse_vcd(sys.argv[1])
    # Sample once per clock period at the settled (clk=='0') point, matching
    # the convention used for the VC Formal extraction in stage 05.
    settled = [(t, v) for t, v in rows if v['clk'] == '0']
    for t, v in settled:
        o = v['O']
        o_int = int(o, 2) if o and 'x' not in o else 0
        rst_n = 1 if v['rst_n'] == '1' else 0
        enable = 1 if v['enable'] == '1' else 0
        i_bit = 1 if v['I'] == '1' else 0
        success = 1 if v['success'] == '1' else 0
        print(f"{rst_n} {enable} {i_bit} {o_int} {success}")


if __name__ == '__main__':
    main()

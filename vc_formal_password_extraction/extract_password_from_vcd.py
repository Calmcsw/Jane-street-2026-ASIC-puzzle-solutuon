#!/usr/bin/env python3
"""
Step 7: Parse the plain-text VCD produced by step 06 and extract the
121-bit serial password from VC Formal's counterexample trace.

Key lesson learned during development: the top-level `puzzle` scope in
the VCD contains the real signal values, but sampling exactly "at" a
posedge timestamp catches a mid-transition/race value for some signals
(this affects `I` even though `enable` itself is now pinned continuously
via a tcl-level `fvassume`, see fv_run_*.tcl). The settled,
self-consistent values are found at the NEGEDGE (clk=='0') samples
between two posedges.

Unlike the earlier wrapper-based pipeline (which had an explicit `cyc`
counter register to identify which password-entry cycle each sample
belonged to), this version has no wrapper module and no `cyc` signal at
all -- the protocol timing is expressed purely via tcl (`fvregister`/
`fvassign`/`fvassume` calls in fv_run_cover_property.tcl etc.), so
password-bit indexing is instead done by ordinal position: the Nth
negedge sample with enable=='1' is bit N of the 121-bit password.

Usage:
    python3 extract_password_from_vcd.py trace_success_full.vcd > password.txt
"""
import sys

# Identifier codes for the top-level `puzzle`-scope signals of interest.
# These are assigned by fsdb2vcd and are stable for this specific trace;
# if you regenerate the FSDB/VCD, re-check the $var lines near the top of
# the file (search for "$scope module puzzle") and update this map.
IDS = {
    '!': 'success',
    '@!': 'rst_n',
    'C!': 'enable',
    'D!': 'clk',
    'U*': 'I',
}


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
            if not line:
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
        print(f"Usage: {sys.argv[0]} <trace.vcd>", file=sys.stderr)
        sys.exit(1)

    rows = parse_vcd(sys.argv[1])

    # Only keep the settled (negedge, clk=='0') samples.
    settled = [(t, v) for t, v in rows if v['clk'] == '0']

    # Password bit N is the Nth settled sample where enable=='1' (enable
    # is now held continuously for exactly the 121-cycle session, so a
    # simple ordinal count replaces the old cyc-based indexing).
    bits = [v['I'] for t, v in settled if v['enable'] == '1']

    if len(bits) != 121:
        print(f"WARNING: expected 121 enable=='1' samples, got {len(bits)} "
              f"-- trace may not be self-consistent!", file=sys.stderr)

    password = ''.join(bits)
    print(password)


if __name__ == '__main__':
    main()

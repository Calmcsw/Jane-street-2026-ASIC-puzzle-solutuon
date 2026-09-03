#!/usr/bin/env python3
"""
spice2v.py - Convert a hierarchical SPICE netlist (as produced by Magic's
`ext2spice`) into a plain structural Verilog gate-level netlist.

This is NOT a synthesis/RTL tool. It does not infer any behavior. It simply
walks the SPICE `.subckt`/`.ends` blocks and, for every subcircuit that is
"structural" (i.e. it instantiates other subcircuits/standard cells rather
than raw transistors), emits an equivalent Verilog module with the same
instances, using named port connections. Transistor-level ("leaf") subckts
(e.g. standard cell internals made of sky130_fd_pr__*fet* devices) are left
as black-box module references - the assumption is that real behavioral or
gate-level Verilog models for those cells already exist elsewhere (e.g. the
PDK's own `.../libs.ref/<lib>/verilog/*.v` files).

Usage:
    ./spice2v.py input.spice -o output.v [--top CELLNAME]
                 [--inputs a,b,c] [--outputs x,y,z]
                 [--drop-cells REGEX]
                 [--drop-power-pins [LIST]]
                 [--buffer-cells REGEX]

Notes:
- --drop-power-pins omits power/ground/bulk pins from every emitted
  module's port list *and* from every instance's connection list. Takes
  a comma-separated LIST of exact pin names (case-insensitive); with no
  LIST given, defaults to "VPWR,VGND,VPB,VNB". Use this when targeting
  vendor cell models that have no power pins at all (e.g. the PDK's
  bare, non-`USE_POWER_PINS` `.functional.v` files), as opposed to the
  power-pin-aware variants. Since SPICE has no pin-name information on
  the instantiating side, this only works for pins on subckts that have
  a local `.subckt` definition in the same file (so their declared pin
  names are known) -- unknown/undefined black-box cells keep all their
  connections as-is (a warning is printed listing any such cases).
- --buffer-cells collapses instances of matching cells into a plain
  `assign out = in;`, instead of instantiating them, provided the cell
  has a local `.subckt` definition with exactly 2 non-power pins (after
  --drop-power-pins filtering, if given) -- i.e. it is structurally a
  pure pass-through/buffer. This is intended for cells like the
  sky130_fd_sc_hd__udp_pwrgood_pp$PG/$P/$G power-sanity UDPs, which are
  always just `X = A` at nominal power: collapsing them removes the
  black-box reference (and any need for a model of that cell) entirely.
  Example: --buffer-cells "udp_pwrgood_pp"
  Cells matched but not shaped like a 2-pin buffer are instantiated
  normally instead (a warning listing any such cases is printed).
- Net/instance names containing characters that aren't valid in a plain
  Verilog identifier (e.g. '/', '#') are emitted as Verilog *escaped
  identifiers* (\\name ) so no information is lost.
- Port/net names of the form `foo[3]` are treated as literal bit-select
  references into a vector `foo`, and the vector is declared once with an
  inferred [msb:0] range.
- Since SPICE carries no signal-direction information, module ports are
  declared as `inout` by default. Use --inputs/--outputs to override the
  direction of specific top-level ports if known.
- Leaf (transistor-only) subckts are skipped - only structural subckts
  produce `module ... endmodule` blocks. A summary of black-box cell types
  referenced (and how many times) is printed to stderr.
"""
import argparse
import re
import sys
from collections import OrderedDict, defaultdict

BUS_RE = re.compile(r'^(.*)\[(\d+)\]$')
PLAIN_ID_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_$]*$')


def verilog_id(name):
    """Return a safe Verilog identifier for `name`, preserving it exactly.
    Plain identifiers pass through unchanged; anything else becomes a
    Verilog escaped identifier."""
    if PLAIN_ID_RE.match(name):
        return name
    return '\\' + name + ' '


def read_logical_lines(path):
    """Read a SPICE file, stripping comments and joining '+' continuation
    lines into a single logical line each."""
    lines = []
    with open(path) as f:
        for raw in f:
            line = raw.rstrip('\n')
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('*'):
                continue
            if stripped.startswith('+'):
                if lines:
                    lines[-1] += ' ' + stripped[1:].strip()
                continue
            lines.append(stripped)
    return lines


def parse_instance(tokens):
    """tokens = ['Xname', node1, node2, ..., cellname, key=val, key=val, ...]
    Returns (inst_name, nodes, cellname, has_params)"""
    inst_name = tokens[0][1:]  # drop leading X/x
    param_start = len(tokens)
    for i, t in enumerate(tokens):
        if '=' in t:
            param_start = i
            break
    cellname = tokens[param_start - 1]
    nodes = tokens[1:param_start - 1]
    has_params = param_start < len(tokens)
    return inst_name, nodes, cellname, has_params


def parse_subckts(lines):
    subckts = OrderedDict()
    current = None
    for line in lines:
        lower = line.lower()
        if lower.startswith('.subckt'):
            tokens = line.split()
            name = tokens[1]
            ports = tokens[2:]
            current = {'ports': ports, 'insts': []}
            subckts[name] = current
        elif lower.startswith('.ends'):
            current = None
        elif line[0] in ('x', 'X') and current is not None:
            tokens = line.split()
            inst_name, nodes, cellname, has_params = parse_instance(tokens)
            current['insts'].append({
                'name': inst_name, 'nodes': nodes,
                'cell': cellname, 'has_params': has_params,
            })
    return subckts


def is_leaf(subckt):
    """A subckt is a 'leaf' (transistor-level) definition if every
    instance within it carries device parameters (w=, l=, ad=, ...) i.e.
    it's calling primitive fet models, not other subckts/cells."""
    insts = subckt['insts']
    if not insts:
        return True
    return all(i['has_params'] for i in insts)


def group_into_buses(names):
    """Given a list of net/port names, return:
        ordered list of declarations: either ('scalar', name)
                                    or ('vector', busname, msb)
        and a lookup set of names that are part of a vector (so we don't
        re-declare them as scalars).
    """
    bus_bits = defaultdict(dict)  # busname -> {index: full_name}
    scalars = []
    seen_bus = OrderedDict()
    for n in names:
        m = BUS_RE.match(n)
        if m:
            base, idx = m.group(1), int(m.group(2))
            bus_bits[base][idx] = n
            seen_bus.setdefault(base, True)
        else:
            scalars.append(n)
    decls = []
    for base in seen_bus:
        msb = max(bus_bits[base].keys())
        decls.append(('vector', base, msb))
    for n in scalars:
        decls.append(('scalar', n, None))
    return decls


def net_ref(name):
    """Verilog reference for a net name: bit-select if it matches foo[N],
    otherwise an (escaped, if needed) plain identifier."""
    m = BUS_RE.match(name)
    if m:
        base, idx = m.group(1), m.group(2)
        return '%s[%s]' % (verilog_id(base), idx)
    return verilog_id(name)


def resolve_instance(inst, subckts, power_pins, buffer_re):
    """Decide what an instance becomes in the emitted Verilog (drop it,
    collapse it into a continuous assign, or instantiate it with its
    power pins filtered out), independent of writing any output. This is
    used both to compute which nets are actually still referenced (for
    wire declarations) and to emit the module body, so the two stay in
    sync."""
    cell = inst['cell']
    cell_ports = subckts[cell]['ports'] if cell in subckts else None

    if buffer_re and buffer_re.search(cell):
        if cell_ports is not None and len(cell_ports) == len(inst['nodes']):
            io_pins = [(p, n) for p, n in zip(cell_ports, inst['nodes'])
                       if not (power_pins and p.upper() in power_pins)]
        else:
            io_pins = None
        if io_pins is not None and len(io_pins) == 2:
            return {'action': 'buffer', 'cell': cell, 'name': inst['name'],
                    'out_net': io_pins[0][1], 'in_net': io_pins[1][1]}
        # falls through to normal instantiation below, but flag it as
        # unbufferable so the caller can warn about it
        unbufferable = True
    else:
        unbufferable = False

    if cell_ports is not None and len(cell_ports) == len(inst['nodes']):
        conns = [(pin, net) for pin, net in zip(cell_ports, inst['nodes'])
                 if not (power_pins and pin.upper() in power_pins)]
        unknown_power = False
    else:
        conns = [(None, net) for net in inst['nodes']]
        unknown_power = bool(power_pins)
    return {'action': 'inst', 'cell': cell, 'name': inst['name'],
            'conns': conns, 'unbufferable': unbufferable,
            'unknown_power': unknown_power}


def emit_module(name, subckt, subckts, directions, drop_re, power_pins, buffer_re, out):
    ports = subckt['ports']
    insts = subckt['insts']

    if power_pins:
        ports = [p for p in ports if p.upper() not in power_pins]

    port_set = set(ports)

    dropped = 0
    resolved = []
    for inst in insts:
        if drop_re and drop_re.search(inst['cell']):
            dropped += 1
            continue
        resolved.append(resolve_instance(inst, subckts, power_pins, buffer_re))

    internal_nets = OrderedDict()
    for r in resolved:
        if r['action'] == 'buffer':
            nets = (r['out_net'], r['in_net'])
        else:
            nets = (net for _, net in r['conns'])
        for n in nets:
            if n not in port_set:
                internal_nets[n] = True

    out.write('module %s (\n' % verilog_id(name))
    port_decls = group_into_buses(ports)
    port_lines = []
    for kind, base, msb in port_decls:
        direction = directions.get(base, 'inout')
        if kind == 'vector':
            port_lines.append('    %s [%d:0] %s' % (direction, msb, verilog_id(base)))
        else:
            port_lines.append('    %s %s' % (direction, verilog_id(base)))
    out.write(',\n'.join(port_lines))
    out.write('\n);\n\n')

    # wire declarations for internal (non-port) nets
    wire_decls = group_into_buses(list(internal_nets.keys()))
    for kind, base, msb in wire_decls:
        if kind == 'vector':
            out.write('  wire [%d:0] %s;\n' % (msb, verilog_id(base)))
        else:
            out.write('  wire %s;\n' % verilog_id(base))
    if wire_decls:
        out.write('\n')

    buffered = 0
    blackbox_counts = defaultdict(int)
    unknown_power_cells = set()
    unbufferable_cells = set()
    for r in resolved:
        cell = r['cell']
        if r['action'] == 'buffer':
            out.write('  assign %s = %s; // buffer: %s (%s)\n' %
                      (net_ref(r['out_net']), net_ref(r['in_net']), cell, r['name']))
            buffered += 1
            continue

        if r['unbufferable']:
            unbufferable_cells.add(cell)
        if r['unknown_power']:
            unknown_power_cells.add(cell)

        blackbox_counts[cell] += 1
        out.write('  %s %s (\n' % (verilog_id(cell), verilog_id(r['name'])))
        conns = []
        for pin, net in r['conns']:
            if pin is None:
                conns.append('    %s' % net_ref(net))
            else:
                conns.append('    .%s(%s)' % (verilog_id(pin), net_ref(net)))
        out.write(',\n'.join(conns))
        out.write('\n  );\n')

    out.write('endmodule\n\n')
    return blackbox_counts, dropped, unknown_power_cells, buffered, unbufferable_cells


def find_top(subckts, structural_names):
    """Pick the structural subckt that is never instantiated by another
    structural subckt - i.e. it's the root of the hierarchy."""
    referenced = set()
    for name in structural_names:
        for inst in subckts[name]['insts']:
            referenced.add(inst['cell'])
    candidates = [n for n in structural_names if n not in referenced]
    if candidates:
        return candidates[-1]
    return structural_names[-1] if structural_names else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spice_file')
    ap.add_argument('-o', '--output', default=None,
                     help='Output Verilog file (default: <input>.v)')
    ap.add_argument('--top', default=None,
                     help='Name of the top-level subckt to convert '
                          '(default: auto-detect the un-referenced structural subckt)')
    ap.add_argument('--all', action='store_true',
                     help='Emit Verilog modules for every structural subckt found, '
                          'not just the top-level one')
    ap.add_argument('--inputs', default='',
                     help='Comma-separated list of top-level port names to mark as input')
    ap.add_argument('--outputs', default='',
                     help='Comma-separated list of top-level port names to mark as output')
    ap.add_argument('--drop-cells', default=None,
                     help='Regex of cell names to drop from the output entirely '
                          '(e.g. decap/fill/tap cells with no logical function): '
                          r'--drop-cells "__(decap|fill|tapvpwrvgnd)_"')
    ap.add_argument('--drop-power-pins', nargs='?', const='VPWR,VGND,VPB,VNB',
                     default=None, metavar='LIST',
                     help='Omit power/ground/bulk pins from every module port list '
                          'and instance connection. Takes a comma-separated LIST of '
                          'exact pin names (case-insensitive); with no LIST given, '
                          'defaults to "VPWR,VGND,VPB,VNB". Use this when targeting '
                          'vendor cell models that have no power pins at all (e.g. '
                          'non-USE_POWER_PINS .functional.v files).')
    ap.add_argument('--buffer-cells', default=None, metavar='REGEX',
                     help='Regex of cell names to collapse into a plain '
                          '`assign out = in;` instead of instantiating, provided '
                          'the cell has exactly 2 non-power pins (i.e. it is a pure '
                          'pass-through/buffer). Intended for cells like the '
                          'sky130_fd_sc_hd__udp_pwrgood_pp$PG/$P/$G power-sanity '
                          'UDPs (always X=A at nominal power): '
                          r'--buffer-cells "udp_pwrgood_pp"')
    args = ap.parse_args()

    lines = read_logical_lines(args.spice_file)
    subckts = parse_subckts(lines)

    structural_names = [n for n, s in subckts.items() if not is_leaf(s)]
    leaf_names = [n for n, s in subckts.items() if is_leaf(s)]

    if not structural_names:
        sys.exit('error: no structural (non-leaf) subckts found in %s' % args.spice_file)

    top = args.top or find_top(subckts, structural_names)
    if top not in subckts:
        sys.exit('error: top cell %r not found in %s' % (top, args.spice_file))

    directions = {}
    for n in args.inputs.split(','):
        n = n.strip()
        if n:
            directions[n] = 'input'
    for n in args.outputs.split(','):
        n = n.strip()
        if n:
            directions[n] = 'output'

    drop_re = re.compile(args.drop_cells) if args.drop_cells else None
    power_pins = None
    if args.drop_power_pins:
        power_pins = {p.strip().upper() for p in args.drop_power_pins.split(',') if p.strip()}
    buffer_re = re.compile(args.buffer_cells) if args.buffer_cells else None

    targets = structural_names if args.all else [top]
    # Always process 'top' first-ish; order doesn't matter much for correctness.
    if top in targets:
        targets = [top] + [t for t in targets if t != top]

    out_path = args.output or (args.spice_file.rsplit('.', 1)[0] + '.v')
    total_blackbox = defaultdict(int)
    total_dropped = 0
    total_buffered = 0
    total_unknown_power_cells = set()
    total_unbufferable_cells = set()
    with open(out_path, 'w') as out:
        out.write('// Auto-generated structural Verilog netlist\n')
        out.write('// Source: %s\n' % args.spice_file)
        out.write('// Top module: %s\n' % top)
        out.write('// Generated by spice2v.py - a plain SPICE->Verilog structural\n')
        out.write('// netlist converter (no synthesis/behavior inferred).\n\n')
        for name in targets:
            bb, dropped, unknown_power_cells, buffered, unbufferable_cells = emit_module(
                name, subckts[name], subckts, directions, drop_re, power_pins, buffer_re, out)
            for k, v in bb.items():
                total_blackbox[k] += v
            total_dropped += dropped
            total_buffered += buffered
            total_unknown_power_cells |= unknown_power_cells
            total_unbufferable_cells |= unbufferable_cells

    sys.stderr.write('Wrote %s\n' % out_path)
    sys.stderr.write('Structural subckts converted: %s\n' % ', '.join(targets))
    sys.stderr.write('Leaf (transistor-level) subckts skipped: %d (%s)\n' %
                      (len(leaf_names), ', '.join(leaf_names[:10]) + ('...' if len(leaf_names) > 10 else '')))
    if drop_re:
        sys.stderr.write('Instances dropped by --drop-cells: %d\n' % total_dropped)
    if buffer_re:
        sys.stderr.write('Instances collapsed to assign by --buffer-cells: %d\n' % total_buffered)
        if total_unbufferable_cells:
            sys.stderr.write(
                'WARNING: --buffer-cells matched these cell types, but they are '
                'not shaped like a 2-pin buffer (no local .subckt definition, or '
                'not exactly 2 non-power pins), so they were instantiated '
                'normally instead: %s\n' % ', '.join(sorted(total_unbufferable_cells)))
    if power_pins and total_unknown_power_cells:
        sys.stderr.write(
            'WARNING: --drop-power-pins requested, but these black-box cell '
            'types have no local .subckt definition (pin names unknown), so '
            'their power-pin connections could NOT be dropped: %s\n' %
            ', '.join(sorted(total_unknown_power_cells)))
    sys.stderr.write('Black-box cell instances referenced in output:\n')
    for cell, count in sorted(total_blackbox.items(), key=lambda kv: -kv[1]):
        sys.stderr.write('  %6d  %s\n' % (count, cell))


if __name__ == '__main__':
    main()

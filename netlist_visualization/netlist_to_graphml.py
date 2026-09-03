#!/usr/bin/env python3
"""netlist_to_graphml.py - Convert a Yosys JSON netlist (as produced by
netlist_to_json.py) into a NetworkX graph and export it as GraphML.

Nodes:
  - one node per cell instance (attrs: type=<sky130 cell type>,
    kind='dff'/'comb', shape, fill_color, border_color)
  - one node per top-level port (attrs: kind='input_port'/'output_port',
    shape, fill_color, border_color)
  D flip-flops/latches render as blue rectangles, combinational cells as
  orange ellipses, input ports as green diamonds, output ports as red
  diamonds. By default the GraphML also carries yEd (yFiles) visual
  markup so these shapes/colors render immediately when opened in yEd;
  pass --no-yed-visuals for plain GraphML (shape/fill_color are still
  present as generic data attributes other tools like Gephi/Cytoscape can
  map to their own visual styling).

Edges (directed, driver -> sink):
  - one edge per single-bit net connection, attrs: net_name (if known from
    'netnames'), bit (the Yosys internal bit id), src_port/dst_port (the
    pin names on each end).

This lets you load the netlist into any GraphML-capable tool (Gephi,
Cytoscape, yEd, igraph, etc.) or keep working with it directly in
NetworkX for graph analysis (fan-in/fan-out, shortest paths from inputs
to 'success', connected components, etc).

Usage:
    python3 netlist_to_graphml.py extract_puzzle/puzzle_d2j.json \\
        --top puzzle -o extract_puzzle/puzzle.graphml
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

import networkx as nx

# sky130_fd_sc_hd cell-type name fragments that identify sequential
# (state-holding) cells: D flip-flops (dfxtp/dfrtp/dfstp/dfbbn/dfbbp and
# scan/edge-triggered/enable variants sdfxtp/sedfxtp/etc.) and latches
# (dlxtp/dlxbp/dlrtp/dlclkp/sdlclkp). Everything else in the library is
# purely combinational (gates, muxes, buffers, tie cells).
SEQUENTIAL_MARKERS = (
    "dfxtp", "dfrtp", "dfstp", "dfbbn", "dfbbp",
    "sdfxtp", "sdfrtp", "sdfstp", "sdfbbn", "sdfbbp",
    "sedfxtp", "sedfxbp", "edfxtp", "edfxbp",
    "dlxtp", "dlxbp", "dlrtp", "dlclkp", "sdlclkp",
)

# Visual style per node category: (shape, fill_color, border_color)
NODE_STYLE = {
    "dff":          ("rectangle", "#4C72B0", "#20345C"),  # blue box
    "comb":         ("ellipse",   "#DD8452", "#8C4A22"),  # orange ellipse
    "input_port":   ("diamond",   "#55A868", "#2C5A38"),  # green diamond
    "output_port":  ("diamond",   "#C44E52", "#6E1F22"),  # red diamond
}


def classify_cell_type(cell_type):
    """Return 'dff' if the sky130 cell type is a sequential (flip-flop or
    latch) cell, else 'comb' (combinational)."""
    t = cell_type.lower()
    return "dff" if any(marker in t for marker in SEQUENTIAL_MARKERS) else "comb"


def build_graph(data, top, strip_power=True):
    mod = data["modules"][top]
    g = nx.MultiDiGraph()

    # bit -> (node_id, port_name) that DRIVES this bit
    driver_of = {}
    # bit -> list of (node_id, port_name) that this bit feeds INTO
    sinks_of = {}

    def add_sink(bit, node, port):
        sinks_of.setdefault(bit, []).append((node, port))

    def add_driver(bit, node, port):
        # Multiple drivers on one bit (e.g. shared power rails) - just keep
        # the first; a warning is printed for visibility.
        if bit in driver_of and driver_of[bit] != (node, port):
            print("warning: bit %s already driven by %s.%s, ignoring "
                  "second driver %s.%s" % (bit, driver_of[bit][0],
                                            driver_of[bit][1], node, port),
                  file=sys.stderr)
            return
        driver_of[bit] = (node, port)

    power_names = {"VGND", "VPWR", "VNB", "VPB", "VDD", "VSS", "GND"}

    # Top-level module ports: from the top module's own perspective, an
    # 'input' port is a SOURCE feeding the internal netlist, and an
    # 'output' port is a SINK receiving from the internal netlist.
    for pname, port in mod["ports"].items():
        if strip_power and pname.upper() in power_names:
            continue
        node_id = "PORT_%s" % pname
        direction = port["direction"]
        kind = "input_port" if direction == "input" else "output_port"
        shape, fill, border = NODE_STYLE[kind]
        g.add_node(node_id, kind=kind, label=pname,
                   shape=shape, fill_color=fill, border_color=border)
        for bit in port["bits"]:
            if isinstance(bit, str):
                continue  # constant '0'/'1'/'x'/'z' bit, not a real net
            if direction == "input":
                add_driver(bit, node_id, pname)
            else:
                add_sink(bit, node_id, pname)

    # Cell instances
    for cname, cell in mod.get("cells", {}).items():
        node_id = cname
        cell_type = cell.get("type", "")
        kind = classify_cell_type(cell_type)
        shape, fill, border = NODE_STYLE[kind]
        g.add_node(node_id, kind=kind, type=cell_type, label=cname,
                   shape=shape, fill_color=fill, border_color=border)
        port_dirs = cell.get("port_directions", {})
        conns = cell.get("connections", {})
        for pname, pdir in port_dirs.items():
            if strip_power and pname.upper() in power_names:
                continue
            for bit in conns.get(pname, []):
                if isinstance(bit, str):
                    continue
                if pdir == "output":
                    add_driver(bit, node_id, pname)
                else:
                    add_sink(bit, node_id, pname)

    # netnames dict: bit -> real signal name(s), for nicer edge labels
    bit_to_name = {}
    for nname, ninfo in mod.get("netnames", {}).items():
        for bit in ninfo.get("bits", []):
            if isinstance(bit, str):
                continue
            bit_to_name.setdefault(bit, nname)

    n_edges = 0
    n_undriven = 0
    for bit, sinks in sinks_of.items():
        driver = driver_of.get(bit)
        if driver is None:
            n_undriven += 1
            continue
        dnode, dport = driver
        net_name = bit_to_name.get(bit, "net%d" % bit)
        for snode, sport in sinks:
            g.add_edge(dnode, snode, net=net_name, bit=bit,
                       src_port=dport, dst_port=sport)
            n_edges += 1

    n_dff = sum(1 for _, d in g.nodes(data=True) if d.get("kind") == "dff")
    n_comb = sum(1 for _, d in g.nodes(data=True) if d.get("kind") == "comb")
    print("Built graph: %d nodes (%d dff, %d comb, %d ports), %d edges "
          "(%d sink bits had no driver)" %
          (g.number_of_nodes(), n_dff, n_comb,
           g.number_of_nodes() - n_dff - n_comb, n_edges, n_undriven),
          file=sys.stderr)
    return g


YFILES_NS = "http://www.yworks.com/xml/graphml"
GRAPHML_NS = "http://graphml.graphdrawing.org/xmlns"


def fix_duplicate_edge_ids(graphml_path):
    """Work around a networkx write_graphml bug/quirk: for a MultiDiGraph,
    it writes each <edge>'s XML 'id' attribute as the multigraph edge KEY
    (which is scoped per node-pair, e.g. 0 for the first parallel edge
    between two nodes) rather than a globally unique id. Since almost every
    net in our netlist is the first (only) edge between its two endpoints,
    this means nearly all 200+ edges end up with the literal id="0" -
    GraphML requires ids to be unique, and strict readers like Gephi
    interpret same-id edges as duplicates/overwrites of a single edge,
    silently dropping the rest. Renumber every <edge> id to be unique."""
    ET.register_namespace("", GRAPHML_NS)
    ET.register_namespace("y", YFILES_NS)
    tree = ET.parse(graphml_path)
    root = tree.getroot()
    ns = {"g": GRAPHML_NS}
    graph_el = root.find("g:graph", ns)
    n = 0
    for edge_el in graph_el.findall("g:edge", ns):
        edge_el.set("id", "e%d" % n)
        n += 1
    tree.write(graphml_path, xml_declaration=True, encoding="UTF-8")
    return n


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


# GEXF only supports 4 built-in viz:shape values (disc, square, triangle,
# diamond) - map our conceptual shapes onto the closest of these.
GEXF_SHAPE = {"rectangle": "square", "ellipse": "disc", "diamond": "diamond"}


def write_gexf(g, path):
    """Write the graph as GEXF with native <viz:color>/<viz:shape> markup.
    Unlike GraphML, Gephi reads GEXF's viz extension directly on import -
    nodes are colored/shaped correctly immediately, with no manual
    Partition-coloring step required (which is error-prone: Gephi's
    auto-generated Partition palette is arbitrary and does NOT correspond
    to our intended kind->color mapping, e.g. it might color
    'output_port' - a 2-node, 0.27%-of-graph slice - some shade that looks
    'blue', while the real dff cells, 12%+ of the graph, get a different
    color entirely)."""
    GEXF_NS = "http://gexf.net/1.2draft"
    VIZ_NS = "http://gexf.net/1.2draft/viz"
    ET.register_namespace("", GEXF_NS)
    ET.register_namespace("viz", VIZ_NS)

    gexf = ET.Element("{%s}gexf" % GEXF_NS, {"version": "1.2"})
    graph_el = ET.SubElement(gexf, "{%s}graph" % GEXF_NS, {
        "mode": "static", "defaultedgetype": "directed",
    })

    # Declare node attribute columns (kind/type/label) so they're still
    # available in Gephi's data table even though color/shape are now
    # carried natively via viz: elements.
    attrs_el = ET.SubElement(graph_el, "{%s}attributes" % GEXF_NS, {"class": "node"})
    node_attr_names = ["kind", "type"]
    attr_ids = {}
    for i, name in enumerate(node_attr_names):
        attr_ids[name] = str(i)
        ET.SubElement(attrs_el, "{%s}attribute" % GEXF_NS,
                       {"id": str(i), "title": name, "type": "string"})

    nodes_el = ET.SubElement(graph_el, "{%s}nodes" % GEXF_NS)
    for node_id, d in g.nodes(data=True):
        node_el = ET.SubElement(nodes_el, "{%s}node" % GEXF_NS, {
            "id": node_id, "label": d.get("label", node_id),
        })
        r, gg, b = hex_to_rgb(d.get("fill_color", "#CCCCCC"))
        ET.SubElement(node_el, "{%s}color" % VIZ_NS,
                       {"r": str(r), "g": str(gg), "b": str(b)})
        shape = GEXF_SHAPE.get(d.get("shape"), "disc")
        ET.SubElement(node_el, "{%s}shape" % VIZ_NS, {"value": shape})
        attvalues_el = ET.SubElement(node_el, "{%s}attvalues" % GEXF_NS)
        for name in node_attr_names:
            if name in d:
                ET.SubElement(attvalues_el, "{%s}attvalue" % GEXF_NS,
                               {"for": attr_ids[name], "value": str(d[name])})

    edges_el = ET.SubElement(graph_el, "{%s}edges" % GEXF_NS)
    for i, (u, v, d) in enumerate(g.edges(data=True)):
        edge_el = ET.SubElement(edges_el, "{%s}edge" % GEXF_NS, {
            "id": "e%d" % i, "source": u, "target": v,
        })

    tree = ET.ElementTree(gexf)
    ET.indent(tree, space="  ")
    tree.write(path, xml_declaration=True, encoding="UTF-8")


def add_yed_visuals(graphml_path):
    """Post-process a plain networkx-written GraphML file to add yEd
    (yFiles) visual markup so shapes/colors actually render when the file
    is opened in yEd, instead of only being available as plain data
    attributes for tools like Gephi/Cytoscape to map manually."""
    ET.register_namespace("", GRAPHML_NS)
    ET.register_namespace("y", YFILES_NS)
    tree = ET.parse(graphml_path)
    root = tree.getroot()
    ns = {"g": GRAPHML_NS}

    # Register new <key> elements for the yFiles nodegraphics/edgegraphics
    # extension data blocks (inserted first, before the <graph> element).
    graph_el = root.find("g:graph", ns)
    node_key_id = "d_yed_node"
    edge_key_id = "d_yed_edge"
    key_node = ET.Element("{%s}key" % GRAPHML_NS, {
        "for": "node", "id": node_key_id,
        "yfiles.type": "nodegraphics",
    })
    key_edge = ET.Element("{%s}key" % GRAPHML_NS, {
        "for": "edge", "id": edge_key_id,
        "yfiles.type": "edgegraphics",
    })
    root.insert(0, key_edge)
    root.insert(0, key_node)

    # Find which plain <data key="..."> ids correspond to our own
    # shape/fill_color/label attributes so we can read them back off per
    # node/edge (networkx assigns key ids like 'd0','d1',... in whatever
    # order attributes were first seen).
    attr_name_to_key = {}
    for key_el in root.findall("g:key", ns):
        attr_name = key_el.get("attr.name")
        if attr_name:
            attr_name_to_key[attr_name] = key_el.get("id")

    def get_data(el, attr_name, default=None):
        key_id = attr_name_to_key.get(attr_name)
        if key_id is None:
            return default
        d = el.find("g:data[@key='%s']" % key_id, ns)
        return d.text if d is not None else default

    for node_el in graph_el.findall("g:node", ns):
        label = get_data(node_el, "label", node_el.get("id"))
        shape = get_data(node_el, "shape", "rectangle")
        fill = get_data(node_el, "fill_color", "#CCCCCC")
        border = get_data(node_el, "border_color", "#000000")

        data_el = ET.SubElement(node_el, "{%s}data" % GRAPHML_NS, {"key": node_key_id})
        shape_node = ET.SubElement(data_el, "{%s}ShapeNode" % YFILES_NS)
        ET.SubElement(shape_node, "{%s}Fill" % YFILES_NS,
                       {"color": fill, "transparent": "false"})
        ET.SubElement(shape_node, "{%s}BorderStyle" % YFILES_NS,
                       {"color": border, "type": "line", "width": "1.0"})
        label_el = ET.SubElement(shape_node, "{%s}NodeLabel" % YFILES_NS)
        label_el.text = label
        ET.SubElement(shape_node, "{%s}Shape" % YFILES_NS, {"type": shape})

    for edge_el in graph_el.findall("g:edge", ns):
        data_el = ET.SubElement(edge_el, "{%s}data" % GRAPHML_NS, {"key": edge_key_id})
        poly_edge = ET.SubElement(data_el, "{%s}PolyLineEdge" % YFILES_NS)
        ET.SubElement(poly_edge, "{%s}LineStyle" % YFILES_NS,
                       {"color": "#666666", "type": "line", "width": "1.0"})
        ET.SubElement(poly_edge, "{%s}Arrows" % YFILES_NS,
                       {"source": "none", "target": "standard"})

    tree.write(graphml_path, xml_declaration=True, encoding="UTF-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("netlist_json", help="Yosys JSON netlist file")
    ap.add_argument("--top", required=True, help="Top-level module name")
    ap.add_argument("-o", "--output", default=None,
                     help="Output GraphML path (default: <input>.graphml)")
    ap.add_argument("--yed-visuals", action="store_true",
                     help="Add yEd (yFiles) shape/color markup so shapes "
                          "render immediately when opened in yEd. Off by "
                          "default: this markup uses yfiles.type keys "
                          "without attr.name/attr.type, which Gephi's "
                          "stricter GraphML parser rejects with an "
                          "'unknown attribute' warning. Plain "
                          "shape/fill_color/kind data attributes are "
                          "always written regardless of this flag, for "
                          "Gephi/Cytoscape/igraph to map to their own "
                          "visual styling (e.g. Gephi: Appearance panel > "
                          "Nodes > Color > Partition > 'kind').")
    ap.add_argument("--keep-power-nets", action="store_true",
                     help="Don't strip VGND/VPWR/VNB/VPB power-rail "
                          "connections (they're usually pure clutter for "
                          "graph analysis - one 'node' with huge fan-out)")
    ap.add_argument("--gexf", action="store_true",
                     help="Also write a .gexf sibling file with native "
                          "viz:color/viz:shape markup. Recommended for "
                          "Gephi: unlike GraphML's plain data columns "
                          "(which need manual Partition-coloring in "
                          "Gephi's UI, an error-prone step since Gephi's "
                          "auto-generated partition palette does NOT "
                          "correspond to our intended kind->color "
                          "mapping), GEXF colors/shapes apply "
                          "automatically on import with no extra steps.")
    args = ap.parse_args()

    with open(args.netlist_json) as f:
        data = json.load(f)

    if args.top not in data["modules"]:
        sys.exit("error: module '%s' not found in JSON; available: %s" %
                  (args.top, ", ".join(list(data["modules"].keys())[:20])))

    g = build_graph(data, args.top, strip_power=not args.keep_power_nets)

    out_path = args.output or (args.netlist_json.rsplit(".", 1)[0] + ".graphml")
    nx.write_graphml(g, out_path)
    n_fixed = fix_duplicate_edge_ids(out_path)
    print("Renumbered %d edge ids to be globally unique (works around a "
          "networkx MultiDiGraph GraphML export bug that otherwise "
          "collapses parallel/same-key edges in strict readers like "
          "Gephi)" % n_fixed, file=sys.stderr)
    if args.yed_visuals:
        add_yed_visuals(out_path)
    print("Wrote %s" % out_path, file=sys.stderr)

    if args.gexf:
        gexf_path = out_path.rsplit(".", 1)[0] + ".gexf"
        write_gexf(g, gexf_path)
        print("Wrote %s (native colors/shapes, recommended for Gephi)" %
              gexf_path, file=sys.stderr)


if __name__ == "__main__":
    main()

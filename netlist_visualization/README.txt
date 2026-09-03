Stage 03: Netlist visualization (Yosys JSON, netlistsvg, GraphML, digitaljs)
==============================================================================

Purely for human comprehension of the extracted netlist -- none of these
outputs feed back into the actual password-solving logic, but they were
essential for the manual reverse-engineering work (an earlier stage
since removed from this pipeline -- see the top-level README.txt).

Files:

netlist_to_json.py
    Drives Yosys (yowasp-yosys) to read the puzzle Verilog (stage
    02 output + the PDK's behavioral sky130_fd_sc_hd Verilog cell models)
    and emit a Yosys JSON netlist. Includes several preprocessing fixups
    needed to make the PDK's Verilog and Yosys's JSON output usable
    downstream:
      - strips SystemVerilog `specify` timing blocks (Yosys chokes on
        some constructs inside them),
      - fixes `inout` ports (used for VPWR/VGND power pins) which
        netlistsvg's schema doesn't accept -- rewritten to `input`,
      - handles pullup/pulldown primitives and power-pin stripping.
    Usage: python3 netlist_to_json.py <top.v> <cell_models.v ...> --top <top_module> -o out.json

generate_skin.py
    Generates a custom netlistsvg "skin" (SVG symbol library) so gates
    render as recognizable schematic symbols (AND/OR/XOR/DFF shapes)
    instead of generic labeled boxes. Used with netlistsvg's default
    renderer: `netlistsvg out.json -o out.svg --skin custom_skin.svg`.

netlist_to_graphml.py
    Builds a NetworkX MultiDiGraph from the Yosys JSON (nodes = cells +
    top-level ports, edges = net bit connections) and exports GraphML for
    Gephi/yEd. Classifies cells as `dff` (sequential) vs `comb`
    (combinational) based on cell-name markers (dfxtp/dfrtp/dfstp/... ->
    dff), assigns distinct node shapes/colors per class, and injects
    yEd/yFiles `<y:ShapeNode>` XML for direct rendering in yEd. Also fixes
    a NetworkX `write_graphml()` bug where every multigraph edge gets a
    literal `id="0"` (which made Gephi collapse all edges down to one).

convert_to_digitaljs.js
    Node.js script using the `yosys2digitaljs` library to convert the
    Yosys JSON into a digitaljs schematic (for interactive,
    drag-and-drop-style circuit viewing/simulation in a browser).

Result of this stage: interactive/visual netlist representations
(extract_puzzle/puzzle_*.svg, *.graphml, *.gexf, *_digitaljs.json) used
purely to aid the manual signal-tracing work from that same removed
stage.

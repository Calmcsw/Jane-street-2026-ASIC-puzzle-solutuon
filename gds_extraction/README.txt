Stage 01: GDS -> gate-level netlist extraction (Magic)
=========================================================

Uses Magic VLSI (loaded with the sky130A PDK from stage 00) to read the raw
puzzle GDS layout, run device/net extraction, and emit a flat SPICE
netlist.

Files, in the order they were used:

extract_puzzle_gds_to_spice.tcl
    Single Magic batch script for jane/puzzle.gds covering the whole
    stage: reads the GDS, selects the top cell, expands it, runs
    `extract all` (writing Magic's internal extracted-circuit
    representation to extract_puzzle/puzzle.ext), then converts that to a
    flat SPICE netlist via `ext2spice lvs` + `ext2spice -o`
    (extract_puzzle/puzzle.spice, ~252KB).
    Run with: magic -dnull -noconsole -rcfile <sky130A.magicrc> extract_puzzle_gds_to_spice.tcl

Result of this stage: extract_puzzle/puzzle.spice -- a flat, transistor/
cell-instance-level SPICE netlist with top-level ports
`I, O[0:7], clk, enable, rst_n, success`, ~4400 logic cells (excluding 601
decap fillers) and 241 flip-flops (210 dfrtp + 31 dfxtp).

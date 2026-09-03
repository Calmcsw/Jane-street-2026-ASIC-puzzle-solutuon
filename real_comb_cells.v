// real_comb_cells.v
//
// Common, power-pin-free combinational-cell include file, shared by both
// the VC Formal (formal PV) and VCS (simulation) scripts in this solution
// pipeline. For use with netlists produced by
// spice_to_verilog/spice2v.py --drop-power-pins (e.g.
// extract_puzzle/puzzle_nopower.v).
//
// Directly `include's the vendor's own drive-strength wrapper files
// (e.g. _2.v) which already provide the exact suffixed module names.
// `USE_POWER_PINS is deliberately left undefined here, so each vendor
// _N.v wrapper's own `ifndef USE_POWER_PINS branch is taken: the emitted
// module has no VPWR/VGND/VPB/VNB ports at all (they become internal
// supply1/supply0 nets instead), matching the power-pin-free netlist
// exactly -- no hand-built adapter needed.
//
// The pwrgood power-good UDPs (pp$PG/pp$P/pp$G), which required a
// handwritten stand-in workaround under `USE_POWER_PINS in an earlier,
// now-retired power-pin-carrying version of this file, are not an issue
// here: they are only referenced from the .behavioral.v model variant,
// never from .functional.v, so with `FUNCTIONAL defined (and no
// `USE_POWER_PINS) they are never `include'd at all -- confirmed by
// grepping every vendor *.functional.v file for "pwrgood" (zero matches).
//
// NOTE on paths: the `include lines below use bare vendor filenames only
// (no directory component), so this file carries no machine-specific or
// repo-specific absolute paths. The caller (VCS: an `+incdir+<dir>` per
// PDK cell subdirectory, built automatically by compile_and_run_vcs.sh;
// VC Formal: an equivalent search-path option) is responsible for making
// the vendor cell directories under jane/pdk/libraries/sky130_fd_sc_hd/
// findable at compile/analyze time.
`define FUNCTIONAL
`include "sky130_fd_sc_hd__a2111oi_2.v"
`include "sky130_fd_sc_hd__a211o_2.v"
`include "sky130_fd_sc_hd__a211oi_2.v"
`include "sky130_fd_sc_hd__a21bo_2.v"
`include "sky130_fd_sc_hd__a21boi_2.v"
`include "sky130_fd_sc_hd__a21o_2.v"
`include "sky130_fd_sc_hd__a21oi_2.v"
`include "sky130_fd_sc_hd__a221o_2.v"
`include "sky130_fd_sc_hd__a221oi_2.v"
`include "sky130_fd_sc_hd__a22o_2.v"
`include "sky130_fd_sc_hd__a22oi_2.v"
`include "sky130_fd_sc_hd__a311o_2.v"
`include "sky130_fd_sc_hd__a31o_2.v"
`include "sky130_fd_sc_hd__a31oi_2.v"
`include "sky130_fd_sc_hd__a32o_2.v"
`include "sky130_fd_sc_hd__a41oi_2.v"
`include "sky130_fd_sc_hd__and2_2.v"
`include "sky130_fd_sc_hd__and2b_2.v"
`include "sky130_fd_sc_hd__and3_2.v"
`include "sky130_fd_sc_hd__and3b_2.v"
`include "sky130_fd_sc_hd__and4_2.v"
`include "sky130_fd_sc_hd__and4b_2.v"
`include "sky130_fd_sc_hd__and4bb_2.v"
`include "sky130_fd_sc_hd__buf_2.v"
`include "sky130_fd_sc_hd__clkbuf_16.v"
`include "sky130_fd_sc_hd__clkbuf_4.v"
`include "sky130_fd_sc_hd__clkbuf_8.v"
`include "sky130_fd_sc_hd__diode_2.v"
`include "sky130_fd_sc_hd__inv_2.v"
`include "sky130_fd_sc_hd__nand2_2.v"
`include "sky130_fd_sc_hd__nand2b_2.v"
`include "sky130_fd_sc_hd__nand3_2.v"
`include "sky130_fd_sc_hd__nand3b_2.v"
`include "sky130_fd_sc_hd__nand4_2.v"
`include "sky130_fd_sc_hd__nor2_2.v"
`include "sky130_fd_sc_hd__nor3_2.v"
`include "sky130_fd_sc_hd__nor3b_2.v"
`include "sky130_fd_sc_hd__nor4_2.v"
`include "sky130_fd_sc_hd__nor4b_2.v"
`include "sky130_fd_sc_hd__o211a_2.v"
`include "sky130_fd_sc_hd__o211ai_2.v"
`include "sky130_fd_sc_hd__o21a_2.v"
`include "sky130_fd_sc_hd__o21ai_2.v"
`include "sky130_fd_sc_hd__o21ba_2.v"
`include "sky130_fd_sc_hd__o21bai_2.v"
`include "sky130_fd_sc_hd__o221a_2.v"
`include "sky130_fd_sc_hd__o22a_2.v"
`include "sky130_fd_sc_hd__o22ai_2.v"
`include "sky130_fd_sc_hd__o2bb2a_2.v"
`include "sky130_fd_sc_hd__o311a_2.v"
`include "sky130_fd_sc_hd__o31a_2.v"
`include "sky130_fd_sc_hd__o31ai_2.v"
`include "sky130_fd_sc_hd__o32a_2.v"
`include "sky130_fd_sc_hd__o32ai_2.v"
`include "sky130_fd_sc_hd__or2_2.v"
`include "sky130_fd_sc_hd__or3_2.v"
`include "sky130_fd_sc_hd__or3b_2.v"
`include "sky130_fd_sc_hd__or4_2.v"
`include "sky130_fd_sc_hd__or4b_2.v"
`include "sky130_fd_sc_hd__or4bb_2.v"
`include "sky130_fd_sc_hd__xnor2_2.v"
`include "sky130_fd_sc_hd__xor2_2.v"


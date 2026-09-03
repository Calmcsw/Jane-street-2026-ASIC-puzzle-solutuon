// real_seq_cells.v
//
// Common, power-pin-free sequential-cell include file, shared by both
// the VC Formal (formal PV) and VCS (simulation) scripts in this solution
// pipeline. For use with netlists produced by
// spice_to_verilog/spice2v.py --drop-power-pins (e.g.
// extract_puzzle/puzzle_nopower.v).
//
// Uses the adapter technique (vendor's bare .functional.v under
// `default_nettype wire, wrapped in a small hand-built module giving it
// the drive-strength-suffixed module name expected by the netlist)
// because the vendor's own suffixed _2.v wrapper files set
// `default_nettype none internally, which breaks 3 of the 4 sequential
// UDP primitives (udp_dff_ps, udp_dff_p, udp_mux_2to1) under a static
// formal/VCS parser. The wrapper module ports here omit
// VPWR/VGND/VPB/VNB entirely, since the netlist no longer connects them.
//
// NOTE on paths: the `include lines below use bare vendor filenames only
// (no directory component), so this file carries no machine-specific or
// repo-specific absolute paths. The caller (VCS: an `+incdir+<dir>` per
// PDK cell subdirectory, built automatically by compile_and_run_vcs.sh;
// VC Formal: an equivalent search-path option) is responsible for making
// the vendor cell directories under jane/pdk/libraries/sky130_fd_sc_hd/
// findable at compile/analyze time.
`default_nettype wire

`include "sky130_fd_sc_hd__dfrtp.functional.v"
`include "sky130_fd_sc_hd__dfstp.functional.v"
`include "sky130_fd_sc_hd__dfxtp.functional.v"
`include "sky130_fd_sc_hd__mux2.functional.v"

module sky130_fd_sc_hd__dfrtp_2 (
    Q,
    CLK,
    D,
    RESET_B
);
    output Q;
    input CLK;
    input D;
    input RESET_B;
    sky130_fd_sc_hd__dfrtp base_inst (.Q(Q), .CLK(CLK), .D(D), .RESET_B(RESET_B));
endmodule

module sky130_fd_sc_hd__dfstp_2 (
    Q,
    CLK,
    D,
    SET_B
);
    output Q;
    input CLK;
    input D;
    input SET_B;
    sky130_fd_sc_hd__dfstp base_inst (.Q(Q), .CLK(CLK), .D(D), .SET_B(SET_B));
endmodule

module sky130_fd_sc_hd__dfxtp_2 (
    Q,
    CLK,
    D
);
    output Q;
    input CLK;
    input D;
    sky130_fd_sc_hd__dfxtp base_inst (.Q(Q), .CLK(CLK), .D(D));
endmodule

module sky130_fd_sc_hd__mux2_1 (
    X,
    A0,
    A1,
    S
);
    output X;
    input A0;
    input A1;
    input S;
    sky130_fd_sc_hd__mux2 base_inst (.X(X), .A0(A0), .A1(A1), .S(S));
endmodule

// conb_1: trivial constant tie-cell (HI=1, LO=0). No vendor primitive
// involved -- kept as a small handwritten pass-through model, same as
// vcs_sim/conb_only.v.
module sky130_fd_sc_hd__conb_1 (HI, LO);
  output HI, LO;
  assign HI = 1'b1;
  assign LO = 1'b0;
endmodule

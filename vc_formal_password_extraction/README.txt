README - VC Formal password-extraction pipeline
=================================================

This directory collects, in order, the scripts that were used to find and
verify the 121-bit serial password that makes the Jane Street puzzle chip
(jane/puzzle.gds -> puzzle.v) assert `success`.

Background: the puzzle netlist has three relevant ports: a 1-bit serial
data input `I`, a session-enable input `enable`, and a 1-bit `success`
output. The real chip's protocol (confirmed against jane/example_inputs.vcd)
is:
  - cycles 0-2:    rst_n=0, enable=0                (reset)
  - cycle 3:       rst_n=1, enable=0                (idle release cycle)
  - cycles 4-124:  enable=1, one password bit per cycle on I (121 bits)
  - cycles 125+:   enable=0                          (idle / read-result)

A prior brute-force/SAT (Yosys) sweep over this exact protocol reported
UNSAT (no password exists), while a commercial formal verification tool
(Synopsys VC Formal) reported the opposite: `success` IS reachable,
covered at internal step 124. This pipeline resolves that contradiction
by extracting the tool's actual counterexample values and validating
them independently in VCS against the real gate-level netlist.

Architecture note (wrapperless): earlier versions of this pipeline used a
SystemVerilog testbench wrapper (`fv_wrapper.sv` / `fv_wrapper_assert.sv`)
around the `puzzle` netlist to add a `cyc` protocol counter and the
cover/assert properties themselves. Those wrapper files have been removed.
The entire formal environment -- DUT elaboration, protocol-timing
registers, and the cover/assert properties -- is now built entirely
within the formal tool's own setup script, directly against the real
`puzzle` module, with no separate wrapper module/instance needed. This
removes an extra file/layer of indirection with no change in the formal
result.

Files, in the order they were used
-----------------------------------

NOTE on proprietary tooling: the three fv_run_*.tcl files below are
OVERVIEWS ONLY -- plain-language descriptions of what each formal run
does conceptually. They are not executable and contain no real
commercial-tool command syntax. The actual setup was done with a
proprietary commercial formal verification tool (Synopsys VC Formal);
its specific commands are intentionally not reproduced anywhere in this
directory.

fv_run_cover_property.tcl
    Sets up the formal environment (design load, clock, reset, and the
    121-cycle protocol-timing signal described below) and poses the
    question "can `success` ever become 1?" as a reachability/coverage
    query, leaving the serial input `I` completely free for the tool to
    search over.
    Result: the tool reported `success` reachable, 124 internal steps in.

fv_run_confirm_assert.tcl
    Identical setup, but poses the same underlying question as a
    pass/fail assertion instead ("success never becomes 1") rather than
    a reachability query. This reformulation exists only because the
    tool's counterexample/trace-export feature works for ordinary
    assertions, not for reachability/coverage-style properties.
    Result: the assertion was disproved, with a counterexample 124
    internal steps in -- the exact same step count as the reachability
    result above, confirming both formulations describe the same
    underlying result.

fv_run_export_fsdb.tcl
    The key extraction step. Reuses the same setup as
    fv_run_confirm_assert.tcl, then asks the tool to write its
    counterexample (the exact `I`/`enable`/`rst_n` values over time that
    make `success` become 1) out to a waveform trace file, including the
    leading reset portion so the file contains the full
    reset-through-success timeline in one place.

How the 121-cycle "enable" timing was built
--------------------------------------------
All three formal runs above share the same underlying timing construct,
built directly in the tool's own setup script (no separate testbench
module):

  - A 1-cycle-delayed copy of `rst_n` is created, so the exact cycle
    reset releases can be detected (`rst_n` true, its delayed copy still
    false).
  - That single-cycle pulse is then propagated, one step per clock
    cycle, through a chain of 121 one-bit stages -- each stage is a
    simple register that copies only the *previous* stage's value, never
    itself. This means exactly one stage is active on each of the 121
    post-reset cycles.
  - ORing all 121 stages together gives a single signal that is high for
    exactly the 121-cycle password-entry window.
  - `enable` is then pinned, continuously (not just at sampled clock
    edges), to equal that window signal, for the entire run -- matching
    the real chip's protocol exactly.

NOTE on why a plain incrementing counter wasn't used instead: the formal
tool's register-definition command evaluates a stage's defining
expression *before* the stage itself exists as a named signal, so an
expression that references its own future value (as a simple "count + 1"
accumulator would) is rejected as an unknown signal. There is no way in
this tool to define a self-referencing counter in one step, hence the
121-stage chained-pulse design above, where each stage only ever
references an already-existing prior signal.

NOTE on continuous vs. clock-edge-only constraints: the tool distinguishes
between a plain clocked assertion/assumption (which only pins a signal's
value at the sampled clock edge, leaving it free to toggle between edges
in an exported trace) and a "hold this value at every simulation instant"
constraint. `enable` (and `rst_n`) use the latter, which is why both
signals appear perfectly clean (no spurious toggling) in the exported
waveform, even though the free input `I` still shows a sampling artifact
between edges (see below).

NOTE on property naming: unless a property is explicitly named, this
tool auto-names each one in strict declaration order. Across all three
scripts, the very first (implicit) property consumes the first
auto-generated name, and the actual cover/assert property that matters
becomes the second. This was confirmed deterministic and reproducible
given the exact same script structure described above; if the number or
order of constraints changes, this naming would need to be re-verified
via the tool's own setup-summary output before the trace-export step
references it.

fsdb2vcd_convert.sh
    Converts the FSDB from fv_run_export_fsdb.tcl into a plain-text VCD
    file that can be parsed with ordinary tools (no proprietary API
    needed for the final extraction step). Defaults to reading
    `traces/trace_success_full.fsdb`.
    NOTE: the generated waveform artifacts (`traces/`, the FSDB itself,
    and the converted `trace_success_full.vcd`) are NOT kept in this
    repository -- they are large, regeneratable binary/text outputs, not
    source. Re-running fv_run_export_fsdb.tcl's real (proprietary)
    counterpart recreates `traces/trace_success_full.fsdb`; the commands
    below then recreate the VCD and the final password file from it.
    NOTE on proprietary tooling: this script does not hardcode a specific
    commercial FSDB-to-VCD conversion utility -- set the
    `FSDB_CONVERT_CMD` environment variable to your own conversion
    command first (see the script's own header comment for details).
    This repo does not ship a working value for this variable -- this
    pipeline is documentation of the original process, not a runnable
    end-to-end tool, e.g.:
        export FSDB_CONVERT_CMD=<your-fsdb-to-vcd-conversion-command>
        ./fsdb2vcd_convert.sh traces/trace_success_full.fsdb trace_success_full.vcd

extract_password_from_vcd.py
    Parses the VCD from fsdb2vcd_convert.sh and extracts the 121-bit
    password. Because there is no wrapper and no `cyc` counter anymore,
    password-bit indexing is done by ordinal position rather than by
    reading a counter value: the Nth settled sample where `enable=='1'`
    is bit N of the password.
    Key detail: the VCD contains two samples per clock period (one at the
    literal posedge timestamp, one at the following negedge). The
    posedge-timestamp sample can catch a transient/race value for signals
    like `I`; the NEGEDGE sample (`clk=='0'`, i.e. the settled value
    between two edges) is the one that is self-consistent with `enable`
    being pinned high for exactly 121 cycles. The script filters for
    these settled samples and warns if it doesn't find exactly 121 bits.
    The top-level VCD identifier map (`!`=success, `@!`=rst_n, `C!`=enable,
    `D!`=clk, `U*`=I) is specific to this exact design/trace -- if you
    regenerate the FSDB/VCD, re-check the `$var` lines right after
    `$scope module puzzle $end` and update the `IDS` dict if they've
    changed.
        python3 extract_password_from_vcd.py trace_success_full.vcd > password.txt

tb_ground_truth_protocol.v
    Plain-Verilog VCS testbench that drives the real `puzzle` netlist
    with exactly the ground-truth protocol timing (reset cycles 0-2,
    idle cycle 3, 121-cycle enable session cycles 4-124, then idle),
    reading its 121 input bits from a file `i_sequence_120.txt` in the
    current directory. This is the same testbench design used throughout
    the project to validate any password candidate against the real,
    gate-level netlist (independent of any formal-tool internals).

compile_and_run_vcs.sh
    Wrapper script that copies a candidate password file into
    `i_sequence_120.txt`, compiles tb_ground_truth_protocol.v together
    with the common cell library files (`../real_comb_cells.v`,
    `../real_seq_cells.v`) and the power-pin-free netlist
    (`../../extract_puzzle/puzzle_nopower.v`), runs the simulation, and
    greps the result line. Fully self-contained -- can be run from
    anywhere, with no dependency on jane/formal_test/vcs_sim/.
    NOTE on proprietary tooling: this script does not hardcode a specific
    commercial RTL simulator's invocation -- set the `RTL_SIM_CMD`
    environment variable to your own simulator's compile command first
    (see the script's own header comment for details). This repo does
    not ship a working value for this variable -- this pipeline is
    documentation of the original process, not a runnable end-to-end
    tool, e.g.:
        export RTL_SIM_CMD=<your-rtl-simulator-compile-command>
        ./compile_and_run_vcs.sh password_121bits.txt

Cell library files (shared by formal PV and simulation)
--------------------------------------------------------------------------------------------------------------------

fv_run_cover_property.tcl, fv_run_confirm_assert.tcl,
fv_run_export_fsdb.tcl (formal PV) and compile_and_run_vcs.sh
(simulation) all reference the same two cell library files, one
directory up, at `jane/solution_pipeline/real_comb_cells.v` and
`real_seq_cells.v` -- there is exactly one copy of each, so formal PV and
VCS simulation are guaranteed to be checking the identical cell models.
Both files reference the real vendor sky130_fd_sc_hd cells directly --
there are no handwritten behavioral re-implementations of any cell with
real logic anywhere in this pipeline. The only handwritten model is a
trivial `conb_1` tie-cell pass-through (2 constant assigns, no vendor
primitive involved -- nothing to model).

These are the power-pin-free variants (this is now the pipeline's only/
default cell library -- the earlier power-pin-carrying versions, and the
formal_test/vcs_sim/adapter_cells.v + conb_only.v + incdirs.f files they
depended on, have been retired/removed now that this consolidated,
simpler scheme is validated and in place). They are designed for use
with a netlist produced by spice_to_verilog/spice2v.py's
`--drop-power-pins` option, i.e. one with NO VPWR/VGND/VPB/VNB ports or
connections anywhere -- see `jane/extract_puzzle/puzzle_nopower.v`,
generated via:
    python3 spice2v.py <puzzle.spice> --top puzzle \
        --inputs clk,enable,rst_n,I --outputs O,success \
        --drop-cells "__(decap|fill|tapvpwrvgnd)_" \
        --drop-power-pins -o puzzle_nopower.v

../real_comb_cells.v
    Provides all 59 combinational sky130_fd_sc_hd cell types used by
    puzzle_nopower.v (e.g. a2111oi, o21ai, xnor2, ...). Directly
    `` `include``s the real vendor PDK per-cell drive-strength wrapper
    files (jane/pdk/libraries/sky130_fd_sc_hd/latest/cells/<cell>/sky130_fd_sc_hd__<cell>_<drive>.v)
    with `` `define FUNCTIONAL`` set and `` `USE_POWER_PINS`` deliberately
    left UNDEFINED, so each vendor file's own `` `ifndef USE_POWER_PINS``
    branch is taken: the emitted module has no power ports at all
    (VPWR/VGND/VPB/VNB become internal supply1/supply0 nets instead) --
    an exact match for the power-pin-free netlist, with NO hand-built
    adapter needed for any of the 59 combinational cell types, and NOT a
    modified vendor file. The vendor's 3 "power-good" UDP primitive files
    (pwrgood pp$PG/$P/$G), which required a handwritten stand-in
    workaround in an earlier power-pin-carrying version of this file, are
    a non-issue here: they are only ever `` `include``d from the
    `.behavioral.v` model variant, never from `.functional.v` (confirmed
    by grepping every vendor cell's `*.functional.v` for "pwrgood": zero
    matches), so with `` `FUNCTIONAL`` defined they're never reached.

../real_seq_cells.v
    Provides the sequential cells used by puzzle_nopower.v: dfrtp, dfstp,
    dfxtp (flip-flops with async reset/set) and mux2. The vendor's own
    drive-strength-suffixed wrapper files for these cells set
    `` `default_nettype none`` internally before including their bare
    base cell, which breaks 3 of the 4 UDP primitive files involved
    (udp_dff_ps, udp_dff_p, udp_mux_2to1 -- only udp_dff_pr, used by
    dfrtp, was patched by the vendor itself with that directive commented
    out) under a static formal/VCS parser. So this file instead
    `` `include``s the vendor's bare (unsuffixed, no power pins)
    `.functional.v` bodies directly under `` `default_nettype wire``, then
    adds a small hand-built wrapper module per cell giving it the
    drive-strength-suffixed name the netlist expects, with power-pin
    ports omitted entirely (the netlist never connects them). `` `define
    UNIT_DELAY=`` must be passed to `analyze`/`vcs` because the vendor UDP
    files reference an otherwise undefined `` `UNIT_DELAY`` macro on their
    table instantiation line. `conb_1` (tie-hi/lo) has no vendor primitive
    to adapt -- it remains a tiny handwritten pass-through, appended at
    the bottom of this file.

Validation performed when this scheme was adopted (see checkpoint history
for full detail): (1) VCS ground-truth replay
(vcs_ground_truth_validation's tb_replay_vs_real_vcd.v, pointed at
puzzle_nopower.v + these two files): 0 mismatches out of 622 cycles
checked against the real chip capture. (2) VC Formal
(fv_run_cover_property.tcl): `covered:124`, identical to the original
power-pin-carrying scheme. (3) After consolidating both formal PV and
`compile_and_run_vcs.sh` to reference these same two files directly (no
more separate per-flow copies), re-ran both and confirmed identical
results: `covered:124` (formal) and the real 121-bit password
(password_121bits.txt) still asserts `success` in VCS simulation.

NOTE on VCS +incdir+: because the vendor's suffixed `_2.v` wrapper files
`` `include`` their own base cell body via a path relative to their own
directory, plain `vcs` (unlike VC Formal's `analyze`, which resolves
relative includes against the includer's own directory automatically)
needs an explicit `+incdir+<dir>` for every PDK cell subdirectory.
compile_and_run_vcs.sh builds this list automatically from
`jane/pdk/libraries/sky130_fd_sc_hd/latest/cells/*/`.

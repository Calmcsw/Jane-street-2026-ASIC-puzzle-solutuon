jane/solution_pipeline -- full project pipeline, GDS to password
====================================================================

THE ANSWER
----------
121-bit serial password (MSB first, one bit fed into `I` per clock cycle
while `enable`=1):

    0000000101010000100000000000010101010000000000001010000001000001
    000000100000101000010000000100000010000010010001010000000

Feeding this into the real puzzle chip / its extracted netlist makes
`success` assert, and the 8-bit ASCII output `O` spells:

    (* TWO STARS *)

This was found via VC Formal (stage 05) and independently confirmed
bit-exact against the real gate-level netlist in VCS (stage 05,
compile_and_run_vcs.sh) -- see vc_formal_password_extraction/README.txt
for the full step-by-step derivation.


WHAT THIS DIRECTORY IS
-----------------------
A curated, numbered, re-runnable collection of every kind of script used
across the whole project, from the very first GDS decompilation through
to the final validated password -- not just the successful final path,
but also the earlier tool (Yosys SAT) whose failure motivated switching
to VC Formal, and the ground-truth VCS validation work that made us
trust VC Formal's answer over Yosys's.

Each stage subdirectory has its own README.txt with full detail on every
script in it (what it does, exact usage, and what result it produced).
This file is just the top-level map.


STAGE-BY-STAGE MAP
-------------------
pdk_and_toolchain_setup/
    Build the sky130 PDK + Magic + netgen toolchain (no root access).

gds_extraction/
    Magic: puzzle.gds -> puzzle.ext -> puzzle.spice (extraction).

spice_to_verilog/
    spice2v.py: puzzle.spice -> puzzle.v (structural Verilog netlist).

netlist_visualization/
    Yosys JSON + netlistsvg/GraphML/digitaljs, for human comprehension
    of the netlist while doing manual gate-level tracing.

(Removed stage: manual RE + Yosys SAT attempts)
    An earlier stage of this project (formerly numbered stage 04)
    involved manual gate-level signal tracing (which established the
    enable/reset/serial-password protocol used by every later stage)
    plus Yosys's built-in SAT solver attempting to *automatically* find
    the password -- both of its SAT runs reported UNSAT (no password
    exists), which was later shown to be wrong and motivated the switch
    to VC Formal below. This stage's scripts/notes were never carried
    into this pipeline directory, so it has been removed rather than
    left as a broken reference, and the stages below renumbered down by
    one to close the gap; see vc_formal_password_extraction/README.txt
    for the approach that superseded it.

vcs_ground_truth_validation/
    Gate-level VCS simulation of the extracted netlist, replaying the
    real captured chip session (example_inputs.vcd) and confirming a
    100% match -- this is what let us trust the enable/reset protocol
    timing and the extracted netlist itself, and later let us
    independently confirm VC Formal's counterexample was real (not a
    formal-tool artifact).

vc_formal_password_extraction/
    VC Formal (Synopsys) formal-verification-based password search:
    wrote a cover property for "success=1 is reachable", asked VC Formal
    to find a reaching trace, exported it, converted it to VCD, and
    extracted the actual `I` bit sequence -- this succeeded where Yosys's
    SAT solver did not, and its result was proven correct via a second,
    independent VCS run (05/06) replaying the extracted password itself.


COMMON CELL LIBRARY FILES (real_comb_cells.v / real_seq_cells.v)
--------------------------------------------------------------------
`real_comb_cells.v` and `real_seq_cells.v`, right here in this base
directory, are the single, shared, power-pin-free sky130_fd_sc_hd cell
library used by BOTH the formal PV scripts (fv_run_*.tcl) and the VCS
simulation script (compile_and_run_vcs.sh) in
vc_formal_password_extraction/ -- there is exactly one copy of each, so
formal PV and simulation are always checking identical cell models. They
pair with `jane/extract_puzzle/puzzle_nopower.v`, a power-pin-free
netlist generated via spice_to_verilog/spice2v.py's `--drop-power-pins`
option. See vc_formal_password_extraction/README.txt for full detail on
how these files work and how they're referenced.


WHAT WAS DELIBERATELY LEFT OUT
--------------------------------
- jane/formal_test/ contains ~60+ near-duplicate Yosys .ys SAT scripts
  (one per cycle-count/step-count variant tried) and ~30 VC Formal .tcl
  scripts from the exploratory process; only representative/final
  examples were copied in here (see the removed-stage note above and
  stage 05's README for which ones and why). The full raw exploration
  history is still on disk at jane/formal_test/ if needed.
- The sky130 PDK / Magic / netgen source code itself is third-party
  (open_pdks, upstream Magic/netgen) and not copied here -- stage 00
  documents the build commands only.
- Generated waveform artifacts (`vc_formal_password_extraction/traces/`,
  its FSDB/XML files, and the converted `trace_success_full.vcd`) are
  not kept here either -- they're large, regeneratable binary/text
  outputs, not source. See vc_formal_password_extraction/README.txt for
  how to recreate them. (`vcs_ground_truth_validation/example_inputs.vcd`
  is different -- it's the real captured chip session data used as an
  input, not a generated pipeline output, so it IS kept.)

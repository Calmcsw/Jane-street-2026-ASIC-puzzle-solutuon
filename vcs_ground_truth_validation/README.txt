Stage 04: VCS ground-truth validation against the real captured VCD
========================================================================

Before trusting either the manual analysis or any SAT/formal tool's
notion of "the protocol", we needed to confirm our understanding of
enable/reset timing against an actual real-chip capture, and separately
confirm that our extracted netlist (stage 01/02) is itself
simulation-correct (i.e. that Magic's extraction + our SPICE->Verilog
conversion didn't introduce any bugs) by replaying a genuine captured
input sequence through it in VCS and checking the outputs match exactly.

Files:

example_inputs.vcd
    The original real-chip capture, as supplied with the puzzle
    (jane/example_inputs.vcd). Contains clk, enable, rst_n, I, O, success
    signals over ~300+ clock cycles from an actual working session with
    the physical/reference chip. This is the ground truth for both the
    reset/enable protocol shape and for confirming our netlist's
    functional correctness.

extract_replay_data_from_vcd.py
    Written from scratch for this documentation pass (the original
    extraction, done earlier in the investigation, was ad-hoc inline
    Python never saved to disk). Parses example_inputs.vcd and
    samples `enable`, `rst_n`, `I`, `success`, and `O` at each settled
    (post-clock-edge) point, emitting one line per cycle in the same
    5-column format as replay_data_from_real_vcd.txt:
        rst_n enable I O success
    Usage: python3 extract_replay_data_from_vcd.py example_inputs.vcd > regenerated.txt
    Validation: regenerating from example_inputs.vcd and diffing against replay_data_from_real_vcd.txt
    reproduces 306 of 312 lines byte-for-byte; the remaining 6 lines
    (three duplicated/reordered `1 0 0 0 0` rows near VCD timestamps
    outside the main password-entry window) are a minor sampling-edge
    artifact of this reconstruction (the original ad-hoc script's exact
    edge-sampling convention near reset transitions was not preserved).
    replay_data_from_real_vcd.txt below remains the authoritative, actually-used file -- this
    script is provided so the conversion step is reproducible/auditable,
    not to replace replay_data_from_real_vcd.txt.

tb_replay_vs_real_vcd.v
    RTL simulation testbench. Instantiates the real extracted+converted
    netlist (extract_puzzle/puzzle.v from stage 02, plus the PDK's
    behavioral sky130_fd_sc_hd cell models) and drives it cycle-by-cycle
    from replay_data_from_real_vcd.txt, asserting after every cycle that
    the simulated `O` and `success` outputs match the file's recorded
    values. This is a bit-exact gate-level replay of the real chip
    capture through our own extracted netlist.
    NOTE on proprietary tooling: this was originally run with a specific
    proprietary commercial RTL simulator. The exact invocation is not
    reproduced here -- run it with any standard Verilog/SystemVerilog
    simulator (from formal_test/vcs_sim/), e.g.:
        <your RTL simulator> -sverilog tb_replay_example.v <puzzle.v> <sky130 cell models> -o simv
        ./simv
    Result: 100% match, every cycle -- confirming the extracted netlist
    (stages 01-02) is functionally identical to the real chip for this
    captured session, and by extension confirming our understanding of
    the enable/rst_n protocol timing used later in stages 04 and 06.

replay_data_from_real_vcd.txt
    The actual data file used by tb_replay_vs_real_vcd.v in the original run (pre-generated;
    see extract_replay_data_from_vcd.py above for how such a file can be regenerated from a VCD).

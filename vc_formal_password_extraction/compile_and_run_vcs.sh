#!/bin/bash
# Step 9: Compile and run the ground-truth-protocol RTL simulation
# testbench against a candidate 121-bit password, using the real
# gate-level netlist.
#
# This script is self-contained: it uses the common, power-pin-free cell
# include files (../real_comb_cells.v, ../real_seq_cells.v) and the
# power-pin-free netlist (../../extract_puzzle/puzzle_nopower.v) shared
# with the formal PV (fv_run_*.tcl) scripts in this same directory. The
# simulator needs an explicit include-directory search path entry for
# every PDK cell directory (vendor _2.v files `include their own base
# cell body by bare filename); this script builds that list automatically.
#
# NOTE on proprietary tooling: the original version of this script
# invoked a specific proprietary commercial RTL simulator directly. That
# has been removed and replaced with a generic $RTL_SIM_CMD variable
# below, so this script no longer names or hardcodes any specific
# commercial tool. Set RTL_SIM_CMD to your own simulator's compile
# invocation (any standard Verilog/SystemVerilog simulator that accepts
# a list of source files, `+incdir+<dir>` include paths, and `+define+`
# macros, producing a single runnable output binary named by `-o`, will
# work here) before running this script. This repo does not ship a
# working value for this variable -- this pipeline is documentation of
# the original process, not a runnable end-to-end tool.
#
# Usage (from anywhere):
#   compile_and_run_vcs.sh <path-to-121-bit-password-file>
#
# The password file should contain exactly 121 '0'/'1' characters (with or
# without a trailing newline).

set -e
: "${RTL_SIM_CMD:?Set RTL_SIM_CMD to your RTL simulator compile command first}"
PASSWORD_FILE="${1:?Usage: $0 <121-bit-password-file>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PDK_CELLS="$SCRIPT_DIR/../../pdk/libraries/sky130_fd_sc_hd/latest/cells"

# The testbench (tb_ground_truth_protocol.v) reads its 121-bit input
# sequence from a file named i_sequence_120.txt in the CWD.
cp "$PASSWORD_FILE" i_sequence_120.txt
cp "$SCRIPT_DIR/tb_ground_truth_protocol.v" tb_ground_truth.v

# The vendor _2.v wrapper files (`include'd by ../real_comb_cells.v) use a
# bare-filename `include for their own base cell body, so the simulator
# needs an explicit include-path entry for every cell directory.
INCDIRS=""
for d in "$PDK_CELLS"/*/; do
  INCDIRS="$INCDIRS +incdir+$d"
done

bash -lc "$RTL_SIM_CMD +define+FUNCTIONAL '+define+UNIT_DELAY=' \
    $INCDIRS \
    '$SCRIPT_DIR/../real_comb_cells.v' '$SCRIPT_DIR/../real_seq_cells.v' \
    '$SCRIPT_DIR/../../extract_puzzle/puzzle_nopower.v' tb_ground_truth.v -o simv_ground_truth" \
    > sim_compile.log 2>&1

./simv_ground_truth > sim_run.log 2>&1

echo "=== Result ==="
grep -E "RESULT|SUCCESS asserted|Final success" sim_run.log
echo
echo "Full log: $(pwd)/sim_run.log"

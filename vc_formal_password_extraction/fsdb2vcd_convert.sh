#!/bin/bash
# Step 6: Convert the FSDB counterexample trace (produced by step 05) into a
# plain-text VCD file that can be parsed without any Synopsys tooling.
#
# NOTE on proprietary tooling: the original version of this script
# invoked a specific proprietary commercial waveform utility directly,
# via a hardcoded install path. That has been removed and replaced with
# a generic $FSDB_CONVERT_CMD variable below, so this script no longer
# names or hardcodes any specific commercial tool or install location.
# Set FSDB_CONVERT_CMD to your own FSDB-to-VCD conversion command (any
# tool that accepts an input FSDB path, an `-o <output>` flag, and
# writes plain-text VCD will work here). This repo does not ship a
# working value for this variable -- this pipeline is documentation of
# the original process, not a runnable end-to-end tool.
#
# Usage:
#   ./fsdb2vcd_convert.sh <input.fsdb> <output.vcd>

set -e
: "${FSDB_CONVERT_CMD:?Set FSDB_CONVERT_CMD to your FSDB-to-VCD conversion command first}"
IN_FSDB="${1:-traces/trace_success_full.fsdb}"
OUT_VCD="${2:-trace_success_full.vcd}"

bash -lc "$FSDB_CONVERT_CMD '$IN_FSDB' -o '$OUT_VCD'"

echo "Converted $IN_FSDB -> $OUT_VCD"

# =====================================================================
# OVERVIEW ONLY -- this file is not executable and is not meant to be
# run. It describes, in plain language, how the final "export the
# counterexample" step was set up.
#
# The actual, original setup used a proprietary commercial formal
# verification tool (Synopsys VC Formal) and its own tcl command
# language. Those exact commands are intentionally NOT reproduced here.
# =====================================================================
#
# This step reuses the exact same design/clock/reset/protocol/assertion
# setup as fv_run_confirm_assert.tcl (see that file for the full
# description of "success never becomes 1" being disproved). Once the
# formal tool disproves that claim, it holds a concrete counterexample
# internally: the exact `I`, `enable`, and `rst_n` values, cycle by
# cycle, that make `success` become 1.
#
# The one additional thing this step does is ask the tool to write that
# counterexample out to a waveform trace file (including the leading
# reset portion, so the file contains the full reset-through-success
# timeline in one place), so it can be inspected and processed outside
# the formal tool entirely.
#
# From this point on, every remaining step in the pipeline is ordinary,
# non-proprietary tooling: the exported waveform file is converted to
# plain-text VCD format, and a small standalone script parses that VCD
# to recover the actual 121-bit password value -- see README.txt in this
# directory for the full narrative and exact commands used for those
# later, non-proprietary steps.
#
# ---------------------------------------------------------------------
# Illustrative pseudocode (invented, generic syntax -- NOT a real
# formal-tool language, and not meant to run anywhere).
# ---------------------------------------------------------------------
#
#   setup_environment_same_as("fv_run_confirm_assert")
#
#   claim  = always(success == 0)
#   result = formal_tool.check(claim)
#
#   if result.status == DISPROVED:
#       export_waveform(
#           trace          = result.witness_trace,
#           include_reset  = true,                 # prepend the reset lead-in
#           output_file    = "trace_success_full.<waveform_format>"
#       )
#
#   # downstream, non-proprietary steps:
#   #   waveform_convert("trace_success_full.<waveform_format>") -> "trace_success_full.vcd"
#   #   extract_password_from_vcd("trace_success_full.vcd")      -> 121-bit password

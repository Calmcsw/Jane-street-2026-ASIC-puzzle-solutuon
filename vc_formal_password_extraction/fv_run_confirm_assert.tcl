# =====================================================================
# OVERVIEW ONLY -- this file is not executable and is not meant to be
# run. It describes, in plain language, how this variant of the formal
# run was set up.
#
# The actual, original setup used a proprietary commercial formal
# verification tool (Synopsys VC Formal) and its own tcl command
# language. Those exact commands are intentionally NOT reproduced here.
# =====================================================================
#
# This run uses the exact same design/clock/reset/protocol setup as
# fv_run_cover_property.tcl (see that file for the full description),
# but poses the question differently: instead of asking "can success
# ever become 1?" (a reachability/coverage question), it asserts the
# opposite as a claim to be checked -- "success never becomes 1" -- and
# asks the formal tool to prove or disprove that claim.
#
# Why phrase it this way at all, if it's the same underlying question?
# The commercial tool's counterexample/trace-export feature only works
# for ordinary pass/fail assertions, not for reachability/coverage-style
# properties. So this reformulation exists purely so that, if the claim
# turns out to be false, the tool can hand back the concrete
# counterexample (the exact signal values over time that disprove it) as
# an exportable waveform trace -- see fv_run_export_fsdb.tcl for that
# next step.
#
# Result: the claim "success never becomes 1" was disproved -- the tool
# found a concrete counterexample 124 internal steps in, matching the
# reachability result from fv_run_cover_property.tcl exactly (as
# expected, since both are really asking the same underlying question).
#
# ---------------------------------------------------------------------
# Illustrative pseudocode (invented, generic syntax -- NOT a real
# formal-tool language, and not meant to run anywhere).
# ---------------------------------------------------------------------
#
#   setup_environment_same_as("fv_run_cover_property")   # design, clock,
#                                                         # reset, in_password_window,
#                                                         # enable constrained, I free
#
#   claim  = always(success == 0)                        # "success never happens"
#   result = formal_tool.check(claim)
#
#   if result.status == DISPROVED:
#       counterexample = result.witness_trace
#       print("disproved at step", result.step)
#   # -> disproved at step 124 (matches the reachability result exactly)

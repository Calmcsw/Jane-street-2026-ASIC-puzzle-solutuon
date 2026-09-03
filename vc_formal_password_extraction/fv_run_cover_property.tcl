# =====================================================================
# OVERVIEW ONLY -- this file is not executable and is not meant to be
# run. It describes, in plain language, how the formal verification
# environment for the "success is reachable" query was set up.
#
# The actual, original setup used a proprietary commercial formal
# verification tool (Synopsys VC Formal) and its own tcl command
# language. Those exact commands are intentionally NOT reproduced here.
# =====================================================================
#
# Question this formal run answers: is there ANY 121-bit sequence fed
# into the chip's serial input `I`, following its real reset/enable
# protocol, that makes the output `success` become 1? This is checked
# directly against the real gate-level netlist (not an RTL model), with
# no simulation test vectors -- the formal tool explores every possible
# 121-bit value on its own.
#
# How the environment was set up, conceptually:
#
#   1. Design load
#      The gate-level netlist (the `puzzle` module, together with its
#      standard-cell library models) was loaded and elaborated as the
#      device under test.
#
#   2. Clock and reset
#      A single clock was declared (10ns period), and the chip's
#      synchronous, active-low reset (`rst_n`) was declared as the
#      formal reset condition.
#
#   3. Recreating the real 121-cycle password-entry window
#      The real chip protocol holds `enable` high for exactly 121
#      cycles, starting one cycle after reset releases. Rather than
#      writing a separate testbench/wrapper module, this timing window
#      was built directly as a small chain of derived signals: a single
#      pulse marking "reset just released", propagated one step per
#      clock cycle through 121 chained one-bit stages, so that exactly
#      one stage is active on each of the 121 cycles. ORing all 121
#      stages together gives a single "we are inside the password-entry
#      window" signal.
#
#   4. Constraining the inputs to match the real protocol
#      `enable` was pinned, for the whole run, to equal that
#      "password-entry window" signal above -- i.e. the formal
#      environment drives the chip with the exact real-world timing.
#      The serial data input `I`, however, was left completely free: the
#      formal tool is allowed to choose any value for it, on every
#      cycle, in its search for a satisfying trace.
#
#   5. The property being checked
#      A reachability ("coverage") question was posed: can `success`
#      ever become 1, given the constraints above? The formal tool
#      performs an exhaustive proof (not simulation) over all possible
#      values of the free input `I`.
#
# Result: yes -- the tool reported `success` reachable, 124 internal
# steps after the run begins. See README.txt in this directory for the
# full narrative of how the actual 121-bit password value was
# subsequently recovered from the tool's witness trace.
#
# ---------------------------------------------------------------------
# Illustrative pseudocode (invented, generic syntax -- NOT a real
# formal-tool language, and not meant to run anywhere). This is only a
# schematic of the logic described above, in the same shape/order the
# steps happened in.
# ---------------------------------------------------------------------
#
#   load_design(design = "puzzle", cells = [comb_cell_models, seq_cell_models])
#
#   define_clock(name = clk, period = 10ns)
#   define_reset(signal = rst_n, active_when = LOW)
#
#   just_released = rst_n AND NOT prev_cycle(rst_n)
#
#   stage[0] = just_released
#   for i in 1..121:
#       stage[i] = prev_cycle(stage[i-1])          # one-cycle delay each step
#
#   in_password_window = OR(stage[1], stage[2], ..., stage[121])
#
#   constrain_always(enable == in_password_window)
#   leave_free(I)                                   # tool may pick any value, any cycle
#
#   question = can_reach(success == 1)
#   result   = formal_tool.check(question)
#
#   print("result:", result.status, "at step", result.step)
#   # -> result: reachable at step 124

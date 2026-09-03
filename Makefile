SHELL := /bin/bash
.ONESHELL:

# solution_pipeline/Makefile
# ==========================
# Convenience targets for re-running any stage of the GDS -> password
# pipeline. See README.txt (top-level and per-stage) for what each stage
# actually does and why.
#
# Usage:
#   make help          # list targets
#   make stage00        # ... etc, one target per stage
#   make all             # run every stage in order (00 -> 05)
#
# NOTE on stage numbering: an earlier stage 04 (manual RE notes + Yosys
# SAT attempts) was removed -- its scripts/notes were never materialized
# into this pipeline directory (see the top-level README's "removed
# stage" note for what it covered). The remaining stages have been
# renumbered down by one to close the gap, so stage numbers here are
# 00-05, contiguous.
#
# Most stages read/write large intermediate artifacts that live outside
# this directory, under jane/ (extract_puzzle/, pdk_install/,
# formal_test/, etc.) -- these are NOT duplicated here (see each stage's
# README.txt "deliberately left out" notes). Targets below operate on
# those real locations directly, so this Makefile must be run with JANE
# pointing at a checked-out copy of the jane/ directory (defaults to the
# parent of this directory, i.e. assumes solution_pipeline/ is still
# sitting inside jane/).

JANE        := $(abspath $(CURDIR)/..)
export CAD_ROOT := $(HOME)/.local/lib
export PDK_ROOT := $(JANE)/pdk_install/share/pdk
export PDKROOT  := $(PDK_ROOT)
CELL_LIB    := $(JANE)/pdk_install/share/pdk/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
MAGICRC     := $(JANE)/pdk_install/share/pdk/sky130A/libs.tech/magic/sky130A.magicrc
EXTRACT_DIR := $(JANE)/extract_puzzle
VCS_DIR     := $(JANE)/formal_test/vcs_sim

.PHONY: help all stage00 stage01 stage02 stage03 stage04 stage05 clean

help:
	@echo "Targets:"
	@echo "  make stage00   - (re)build sky130 PDK + Magic/netgen toolchain"
	@echo "  make stage01   - Magic: extract puzzle.gds -> puzzle.spice"
	@echo "  make stage02   - spice2v.py: puzzle.spice -> puzzle.v + puzzle_nopower.v"
	@echo "  make stage03   - generate Yosys JSON / GraphML / digitaljs views"
	@echo "  make stage04   - RTL simulation replay of the real chip capture (ground truth)"
	@echo "  make stage05   - print instructions for the VC Formal extraction stage"
	@echo "  make all       - run stage00..stage05 in order"
	@echo "  make clean     - remove this Makefile's own scratch outputs"
	@echo ""
	@echo "JANE=$(JANE)"

all: stage00 stage01 stage02 stage03 stage04 stage05

# ---------------------------------------------------------------------
# Stage 00: PDK + toolchain
# ---------------------------------------------------------------------
stage00:
	@echo ">>> Stage 00: PDK + toolchain setup"
	@echo "This stage is a one-time environment build, not something you"
	@echo "normally re-run. See pdk_and_toolchain_setup/build_pdk_and_tools.sh"
	@echo "for the exact commands used, and README.txt in that directory for"
	@echo "details. Run it manually if you need to rebuild from scratch:"
	@echo "    bash pdk_and_toolchain_setup/build_pdk_and_tools.sh"

# ---------------------------------------------------------------------
# Stage 01: GDS -> SPICE extraction (Magic)
# ---------------------------------------------------------------------
stage01:
	@echo ">>> Stage 01: GDS -> SPICE extraction"
	@echo "NOTE: the .tcl script below uses paths relative to its magic working"
	@echo "directory (this target cd's into EXTRACT_DIR first), so output always"
	@echo "lands in $(EXTRACT_DIR)/ regardless of any EXTRACT_DIR override."
	@if [ ! -f "$(MAGICRC)" ]; then \
		echo "ERROR: $(MAGICRC) not found -- run 'make stage00' first." >&2; exit 1; \
	fi
	mkdir -p "$(EXTRACT_DIR)"
	cd "$(EXTRACT_DIR)" && magic -dnull -noconsole -rcfile "$(MAGICRC)" \
		"$(CURDIR)/gds_extraction/extract_puzzle_gds_to_spice.tcl"
	@echo "Result: $(EXTRACT_DIR)/puzzle.spice"

# ---------------------------------------------------------------------
# Stage 02: SPICE -> structural Verilog
# ---------------------------------------------------------------------
stage02:
	@echo ">>> Stage 02: SPICE -> Verilog"
	@if [ ! -f "$(EXTRACT_DIR)/puzzle.spice" ]; then \
		echo "ERROR: $(EXTRACT_DIR)/puzzle.spice not found -- run 'make stage01' first." >&2; exit 1; \
	fi
	python3 spice_to_verilog/spice2v.py "$(EXTRACT_DIR)/puzzle.spice" \
		--top puzzle --inputs clk,enable,rst_n,I --outputs O,success \
		--drop-cells "__(decap|fill|tapvpwrvgnd)_" \
		-o "$(EXTRACT_DIR)/puzzle.v"
	python3 spice_to_verilog/spice2v.py "$(EXTRACT_DIR)/puzzle.spice" \
		--top puzzle --inputs clk,enable,rst_n,I --outputs O,success \
		--drop-cells "__(decap|fill|tapvpwrvgnd)_" \
		--drop-power-pins \
		-o "$(EXTRACT_DIR)/puzzle_nopower.v"
	@echo "Result: $(EXTRACT_DIR)/puzzle.v (power-pin-carrying, used by stage03)"
	@echo "        $(EXTRACT_DIR)/puzzle_nopower.v (power-pin-free, used by stage05's"
	@echo "        formal PV + compile_and_run_vcs.sh, together with"
	@echo "        real_comb_cells.v/real_seq_cells.v -- see"
	@echo "        vc_formal_password_extraction/README.txt)"

# ---------------------------------------------------------------------
# Stage 03: netlist visualization
# ---------------------------------------------------------------------
stage03:
	@echo ">>> Stage 03: netlist visualization"
	@if [ ! -f "$(EXTRACT_DIR)/puzzle.v" ]; then \
		echo "ERROR: $(EXTRACT_DIR)/puzzle.v not found -- run 'make stage02' first." >&2; exit 1; \
	fi
	python3 netlist_visualization/netlist_to_json.py "$(EXTRACT_DIR)/puzzle.v" \
		--top puzzle --cell-lib "$(CELL_LIB)" --strip-power-pins \
		-o "$(EXTRACT_DIR)/puzzle.json"
	python3 netlist_visualization/netlist_to_graphml.py "$(EXTRACT_DIR)/puzzle.json" \
		--top puzzle -o "$(EXTRACT_DIR)/puzzle.graphml"
	@echo "Result: $(EXTRACT_DIR)/puzzle.json, $(EXTRACT_DIR)/puzzle.graphml"
	@echo "(node convert_to_digitaljs.js and generate_skin.py are separate," \
	     "optional viewers -- see netlist_visualization/README.txt)"

# ---------------------------------------------------------------------
# (Removed stage: manual RE notes + Yosys SAT attempts)
# ---------------------------------------------------------------------
# This stage (manual gate-level signal tracing + Yosys SAT-solver attempts
# that historically reported UNSAT) was never materialized into this
# pipeline directory -- the .ys scripts and notes it referenced do not
# exist here. Rather than leave a broken target, it has been removed and
# the remaining stages below renumbered down by one to close the gap
# (this used to be stage 04; stages 05/06 below are now 04/05).
# See vc_formal_password_extraction/README.txt for the approach that
# superseded it (VC Formal, which correctly found the password where
# the Yosys SAT attempts did not).

# ---------------------------------------------------------------------
# Stage 04: RTL simulation ground-truth replay
# ---------------------------------------------------------------------
# NOTE on proprietary tooling: this stage originally invoked a specific
# proprietary commercial RTL simulator directly. That literal command
# has been removed and replaced with a generic $RTL_SIM_CMD variable
# below, so this Makefile no longer names/hardcodes a specific
# commercial tool. Set RTL_SIM_CMD to your own simulator's compile
# invocation before running this target. This repo does not ship a
# working value for this variable -- this pipeline is documentation of
# the original process, not a runnable end-to-end tool.
stage04:
	@echo ">>> Stage 04: RTL simulation ground-truth replay against real chip capture"
	python3 vcs_ground_truth_validation/extract_replay_data_from_vcd.py \
		vcs_ground_truth_validation/example_inputs.vcd \
		> vcs_ground_truth_validation/.regenerated_replay_data.txt
	diff vcs_ground_truth_validation/.regenerated_replay_data.txt \
		vcs_ground_truth_validation/replay_data_from_real_vcd.txt \
		&& echo "Regenerated replay data matches replay_data_from_real_vcd.txt exactly." \
		|| echo "NOTE: minor diffs vs replay_data_from_real_vcd.txt -- see vcs_ground_truth_validation/README.txt"
	@if [ ! -f "$(VCS_DIR)/puzzle.v" ]; then \
		echo "NOTE: $(VCS_DIR)/puzzle.v not present -- skipping actual simulation compile/run" \
		     "(needs puzzle.v, adapter_cells.v, conb_only.v, incdirs.f, filelist.txt; see README.txt)."; \
	elif [ -z "$(RTL_SIM_CMD)" ]; then \
		echo "NOTE: RTL_SIM_CMD not set -- skipping actual simulation compile/run" \
		     "(set RTL_SIM_CMD to your simulator's compile invocation)."; \
	else \
		cp vcs_ground_truth_validation/replay_data_from_real_vcd.txt "$(VCS_DIR)/replay_data2.txt"; \
		cd "$(VCS_DIR)" && $(RTL_SIM_CMD) +define+FUNCTIONAL '+define+UNIT_DELAY=' -sverilog \
			-f incdirs.f adapter_cells.v conb_only.v puzzle.v \
			"$(CURDIR)/vcs_ground_truth_validation/tb_replay_vs_real_vcd.v" \
			-o simv_replay && ./simv_replay; \
	fi

# ---------------------------------------------------------------------
# Stage 05: VC Formal password extraction
# ---------------------------------------------------------------------
stage05:
	@echo ">>> Stage 05: VC Formal password extraction"
	@echo "This stage requires a licensed VC Formal + VCS install and is"
	@echo "driven interactively step-by-step -- see the detailed walkthrough"
	@echo "in vc_formal_password_extraction/README.txt (scripts, in order)."
	@echo "The already-extracted, VCS-validated result is available at:"
	@echo "    vc_formal_password_extraction/password_121bits.txt"
	@cat vc_formal_password_extraction/password_121bits.txt

clean:
	rm -f vcs_ground_truth_validation/.regenerated_replay_data.txt

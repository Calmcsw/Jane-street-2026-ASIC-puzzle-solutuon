Stage 02: SPICE -> structural Verilog conversion
==================================================

Files:
  spice2v.py
      Generalized SPICE-to-Verilog converter, written from scratch for
      this project (not a third-party tool). Parses the SPICE
      `.subckt`/`.ends` hierarchy produced by Magic (stage 01) and
      classifies each subckt as:
        - "leaf" (transistor-level -- all instances have MOSFET device
          parameters like W=/L=) -- these are the sky130 standard cells
          themselves, and are NOT re-emitted (the real behavioral
          sky130_fd_sc_hd Verilog models are used instead, from the PDK).
        - "structural" (instantiates other subckts) -- these ARE emitted
          as plain structural Verilog modules with simple wire
          declarations and cell instantiations.
      This produces a plain structural netlist (module instantiations
      only, no behavioral logic invented) -- i.e. exactly what Magic
      extracted, just in Verilog syntax instead of SPICE syntax.

      Usage:
          python3 spice2v.py <input.spice> --top <top_module_name> \
              --inputs clk,enable,rst_n,I --outputs O,success \
              --drop-cells "__(decap|fill|tapvpwrvgnd)_" -o out.v

      (The --inputs/--outputs/--drop-cells values above are exactly what
      was used to produce extract_puzzle/puzzle.v from puzzle.spice --
      real port directions are not recoverable from flat SPICE alone, and
      decap/fill/tap cells are non-functional layout filler with no
      logical role, so they're dropped from the emitted instances while
      their now-dangling internal wire declarations are harmlessly left
      in place.)

      Applied to the extracted puzzle netlist (puzzle.spice -> puzzle.v).

      --drop-power-pins is now ALSO used in production, as a second pass
      producing extract_puzzle/puzzle_nopower.v (in addition to the
      original puzzle.v above, which remains unchanged and is still used
      by stages 03-05):
          python3 spice2v.py <puzzle.spice> --top puzzle \
              --inputs clk,enable,rst_n,I --outputs O,success \
              --drop-cells "__(decap|fill|tapvpwrvgnd)_" \
              --drop-power-pins -o puzzle_nopower.v
      puzzle_nopower.v pairs with the power-pin-free
      solution_pipeline/real_comb_cells.v and real_seq_cells.v, and is
      the netlist used by stage05's VC Formal (fv_run_*.tcl) and VCS
      (compile_and_run_vcs.sh) scripts -- see
      vc_formal_password_extraction/README.txt for detail. (make stage02
      generates both puzzle.v and puzzle_nopower.v.)

      Flag detail:
        --drop-power-pins [LIST]
            Comma-separated, case-insensitive list of exact pin names to
            strip from every emitted module's port list and from every
            instance's connections (default list when the bare flag is
            given: VPWR,VGND,VPB,VNB). Only works for instances whose
            cell has a known local .subckt definition in the same file
            (needed to know which positional node is which named pin);
            unknown/black-box cells can't be filtered and are left
            unchanged, with a warning listing the affected cell types.
            Internal wire declarations for now-unreferenced power nets
            are also correctly omitted (no dangling/unused wires).
        --buffer-cells REGEX
            Collapses instances whose cell name matches REGEX into a
            direct `assign out = in;` instead of a module instantiation,
            eliminating the black-box reference entirely. Intended for
            pure pass-through cells such as the sky130 `pwrgood` UDPs
            (`X = A` at nominal power). A match is only collapsed if,
            after removing any --drop-power-pins pins, exactly 2 pins
            remain -- the first (per the subckt's declared port order)
            is treated as the output, the second as the input. Cells
            that match the regex but don't fit that 2-pin shape fall
            back to normal instantiation, with a warning. (Not needed/
            used for puzzle_nopower.v -- see note below.)
        Note: puzzle.spice (Magic's flat transistor-level extraction)
        does not itself contain any `pwrgood`-style cells -- those only
        appear in the vendor's separately-`` `include``d Verilog models
        used later in solution_pipeline/real_comb_cells.v, not in the
        SPICE domain, so --buffer-cells is unnecessary for
        puzzle_nopower.v and was verified separately with a small
        synthetic .spice test (see git history / session notes).

Result of this stage: extract_puzzle/puzzle.v -- the structural Verilog
netlist used as the basis for every later step (Yosys JSON generation,
Yosys SAT solving, VC Formal, and every VCS testbench).

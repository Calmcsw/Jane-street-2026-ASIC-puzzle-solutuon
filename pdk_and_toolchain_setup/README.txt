Stage 00: sky130 PDK + Magic/netgen toolchain setup
====================================================

Before any reverse engineering of jane/puzzle.gds could happen, we needed a
full open-source EDA toolchain capable of reading a raw GDS layout and
extracting a gate-level netlist from it, with no root/sudo access on this
machine (everything installed to user-writable locations).

Files:
  build_pdk_and_tools.sh
      Documents (as a runnable-shape script) the actual commands used to:
        - build Magic VLSI from source into ~/.local
        - build netgen (LVS tool) from source into ~/.local
        - configure + build + install the sky130 PDK via open_pdks into
          jane/pdk_install/
        - set up jane/.envrc (direnv) so CAD_ROOT/PDKROOT/PATH are
          automatically exported when working in the jane/ directory.

      Full raw build logs (very long, mostly third-party build-system
      chatter) are preserved at jane/open_pdks_build.log and
      jane/open_pdks_install.log for reference.

Why this stage exists: Magic needs the sky130A.tech technology file (from
the PDK) to know how to interpret polygon layers in the GDS as transistors
and interconnect; netgen needs the PDK's netgen setup script to know sky130
device/cell equivalences for LVS checks in stage 01.

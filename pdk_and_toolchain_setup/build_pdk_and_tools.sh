#!/bin/bash
# Stage 00: Build the sky130 PDK (via open_pdks) and the Magic/netgen tools
# needed to extract a gate-level netlist from a GDS layout.
#
# This is a from-source build of third-party open-source EDA tools; there is
# no custom code here, just the documented commands actually run to set the
# toolchain up in a user-writable, non-root location (no sudo access on this
# machine). Kept here for completeness/reproducibility of the full pipeline.
#
# Prerequisites assumed already cloned:
#   jane/open_pdks   (https://github.com/RTimothyEdwards/open_pdks)
#   jane/pdk         (https://github.com/google/skywater-pdk, or the
#                      fossi-foundation fork used by open_pdks)
#   jane/netgen_src  (git://opencircuitdesign.com/netgen)
#   Magic VLSI       (git://opencircuitdesign.com/magic), installed to
#                      ~/.local

set -e
JANE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# --- Magic VLSI ---
# Built from source into ~/.local. Requires CAD_ROOT=$HOME/.local/lib set
# in the environment (jane/.envrc exports this via direnv) so Magic can find
# its own sys/minimum.tech at runtime.
#   cd magic-src && ./configure --prefix=$HOME/.local && make -j && make install

# --- netgen (LVS tool) ---
# Built from source into ~/.local.
#   cd "$JANE_DIR/netgen_src"
#   ./configure --prefix=$HOME/.local
#   make -j
#   make install

# --- sky130 PDK, via open_pdks ---
# open_pdks' sky130 makefile downloads/builds the PDK library sources
# (sky130_fd_pr, sky130_fd_sc_hd, ...) and stages them for Magic/netgen.
cd "$JANE_DIR/open_pdks"
./configure --enable-sky130-pdk="$JANE_DIR/pdk" \
            --with-sky130-local-path="$JANE_DIR/pdk_install"
(cd sky130 && make -j all)     # see ../open_pdks_build.log for full output
(cd sky130 && make install)    # see ../open_pdks_install.log for full output

# Result: PDK installed under $JANE_DIR/pdk_install/share/pdk/sky130A/
# (libs.tech/magic/sky130A.tech, libs.tech/netgen/sky130A_setup.tcl, etc.)

# --- jane/.envrc (direnv) used throughout the rest of the pipeline ---
cat <<'EOF'
export CAD_ROOT=$HOME/.local/lib
export PDKROOT=$JANE_DIR/pdk_install/share/pdk
export PDK_ROOT=$PDKROOT
export PATH=$HOME/.local/bin:$PATH
EOF

echo "Verify with: magic -rcfile \$PDKROOT/sky130A/libs.tech/magic/sky130A.magicrc"

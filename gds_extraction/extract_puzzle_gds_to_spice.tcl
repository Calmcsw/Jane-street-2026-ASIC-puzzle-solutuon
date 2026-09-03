# NOTE: paths below are relative to the working directory magic is run
# from. The Makefile (stage01) cd's into extract_puzzle/ before invoking
# this script, so "." is extract_puzzle/ itself and "../puzzle.gds" is
# jane/puzzle.gds. If running this script manually, cd into
# jane/extract_puzzle/ first (creating it if needed).
gds read ../puzzle.gds
load puzzle
select top cell
expand
extract path .
extract all
ext2spice lvs
ext2spice -o puzzle.spice puzzle
puts "Done puzzle extraction"
quit -noprompt

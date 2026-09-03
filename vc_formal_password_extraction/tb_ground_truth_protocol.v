`timescale 1ns/1ps
module tb;
  reg clk = 0;
  reg rst_n = 0;
  reg enable = 0;
  reg I = 0;
  wire success;
  wire [7:0] O;

  integer fd;
  integer c;
  reg [0:255] iseq;
  integer nbits;
  integer i;
  reg found;
  integer total_cycles;

  puzzle dut (
    .O(O),
    .I(I),
    .clk(clk),
    .enable(enable),
    .rst_n(rst_n),
    .success(success)
  );

  always #5 clk = ~clk;

  initial begin
    fd = $fopen("i_sequence_120.txt", "r");
    if (fd == 0) begin
      $display("ERROR: could not open i_sequence_120.txt");
      $finish;
    end
    nbits = 0;
    while (!$feof(fd)) begin
      c = $fgetc(fd);
      if (c == "0" || c == "1") begin
        iseq[nbits] = (c == "1") ? 1'b1 : 1'b0;
        nbits = nbits + 1;
      end
    end
    $fclose(fd);
    $display("Loaded %0d bits", nbits);

    found = 1'b0;

    // Matches example_inputs.vcd protocol:
    // cycles 0..2: rst_n=0, enable=0
    // cycle 3: rst_n=1 (released), enable still 0
    // cycle 4..124 (121 cycles): enable=1, feed I = password bits (120), then 1 pad cycle
    // cycle 125+: enable=0, keep clocking to observe O (display) and success

    rst_n = 0; enable = 0; I = 0;
    @(posedge clk); #1;
    $display("cyc=0 rst_n=0 enable=0 O=%b success=%b", O, success);
    @(posedge clk); #1;
    $display("cyc=1 rst_n=0 enable=0 O=%b success=%b", O, success);
    @(posedge clk); #1;
    $display("cyc=2 rst_n=0 enable=0 O=%b success=%b", O, success);

    rst_n = 1;
    @(posedge clk); #1;
    $display("cyc=3 rst_n=1 enable=0 O=%b success=%b", O, success);

    enable = 1;
    for (i = 0; i < nbits; i = i + 1) begin
      I = iseq[i];
      @(posedge clk); #1;
      $display("cyc=%0d(enable, bit %0d) I=%b O=%b success=%b", i+4, i, iseq[i], O, success);
      if (success === 1'b1 && !found) begin
        $display("*** SUCCESS asserted at cycle %0d (bit index %0d) ***", i+4, i);
        found = 1'b1;
      end
    end
    // one extra pad cycle while still enabled (matches 121-cycle session in example)
    I = 0;
    @(posedge clk); #1;
    $display("cyc=%0d(enable, pad) O=%b success=%b", nbits+4, O, success);
    if (success === 1'b1 && !found) begin
      $display("*** SUCCESS asserted at cycle %0d (pad cycle) ***", nbits+4);
      found = 1'b1;
    end

    enable = 0;
    // Now watch for settle + O display for many more cycles
    for (i = 0; i < 100; i = i + 1) begin
      @(posedge clk); #1;
      $display("cyc=%0d(post-enable, watch) O=%b (%c) success=%b", nbits+5+i, O, O, success);
      if (success === 1'b1 && !found) begin
        $display("*** SUCCESS asserted at cycle %0d (post-enable) ***", nbits+5+i);
        found = 1'b1;
      end
    end

    if (!found)
      $display("RESULT: success never asserted");
    else
      $display("RESULT: success WAS asserted (see above).");

    $display("Final success value = %b", success);
    $finish;
  end

  initial begin
    #100000;
    $display("TIMEOUT - simulation did not finish");
    $finish;
  end
endmodule

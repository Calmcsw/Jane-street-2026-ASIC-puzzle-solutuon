`timescale 1ns/1ps
module tb_replay_example;
    reg clk = 0;
    reg rst_n_r, enable_r, I_r;
    wire [7:0] O_w;
    wire success_w;

    integer NUM = 312;
    reg [0:0] rst_n_arr [0:311];
    reg [0:0] enable_arr [0:311];
    reg [0:0] I_arr [0:311];
    reg [7:0] O_arr [0:311];
    reg [0:0] success_arr [0:311];

    integer i, k;
    integer mismatches;
    integer fd;

    puzzle dut (
        .clk(clk),
        .rst_n(rst_n_r),
        .enable(enable_r),
        .I(I_r),
        .O(O_w),
        .success(success_w)
    );

    always #5 clk = ~clk;

    initial begin
        fd = $fopen("replay_data2.txt", "r");
        for (i = 0; i < 312; i = i + 1) begin
            $fscanf(fd, "%d %d %d %d %d\n",
                rst_n_arr[i], enable_arr[i], I_arr[i], O_arr[i], success_arr[i]);
        end
        $fclose(fd);

        mismatches = 0;
        rst_n_r = rst_n_arr[0];
        enable_r = enable_arr[0];
        I_r = I_arr[0];

        for (k = 0; k < 311; k = k + 1) begin
            @(posedge clk);
            #1;
            // apply next cycle's inputs
            rst_n_r = rst_n_arr[k+1];
            enable_r = enable_arr[k+1];
            I_r = I_arr[k+1];
            // compare our settled O/success (from end of cycle k, just before this edge)
            // against expected values recorded at sample k+1 (per convention derived from VCD sampling)
            if (O_w !== O_arr[k]) begin
                mismatches = mismatches + 1;
                if (mismatches < 20)
                    $display("MISMATCH O at cycle %0d: got %b expected %b", k, O_w, O_arr[k]);
            end
            if (success_w !== success_arr[k+1]) begin
                mismatches = mismatches + 1;
                if (mismatches < 20)
                    $display("MISMATCH success at cycle %0d: got %b expected %b", k+1, success_w, success_arr[k+1]);
            end
        end
        $display("TOTAL MISMATCHES: %0d out of %0d cycles checked", mismatches, 311*2);
        $finish;
    end
endmodule

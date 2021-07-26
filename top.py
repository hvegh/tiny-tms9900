#!/usr/bin/env python3
import os
import argparse
import pprint

from migen import *
from litex_boards.platforms import colorlight_5a_75b as board
#from litex_boards.platforms import lattice_ice40up5k_evn as board
from litex.soc.cores.clock import *


"""
Basic SRAM class

Signals:
    input  addr
    input  re
    output dat_r
    input  we
    input  dat_w
"""
class sram(Module):
    def __init__(self, addr, re, dat_r, we, dat_w):
        assert len(dat_r) == len(dat_w), "ERROR: length of data busses must be equal"

        self.specials.mem = Memory(
            len(dat_r),
            2**len(addr),
            init=[1, 2, 3]
        )
        p1 = self.mem.get_port(write_capable=True, has_re=True)
        self.specials += p1
        p1.addr  = addr
        p1.re    = re
        p1.dat_r = dat_r
        p1.we    = we
        p1.dat_w = dat_w
        self.ios = {p1.adr, p1.re, p1.dat_r, p1.we, p1.dat_w }

class pll_top(Module):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()

        self.addr       = Signal(16)
        self.data_out   = Signal(16)
        self.data_in    = Signal(16)
        self.rd         = Signal()
        self.wr         = Signal()
        self.rd_now     = Signal()
        self.iaq        = Signal()
        self.int_ack    = Signal()
        self.cruclk     = Signal()
        self.cruout     = Signal()
        self.cruin      = Signal()
        self.holda      = Signal()
        self.stuck      = Signal()
        self.waits      = Signal(8, reset=8)

        self.rom_o      = Signal(16)
        self.ram_o      = Signal(16)

        self.nce_9902   = Signal()
        self.nce_rom    = Signal()
        self.wr_ram     = Signal()
        self.rd_ram     = Signal()


        self.clock_domains.cd_sys    = ClockDomain()

        # # #

        sysclk = None
        clk = platform.request(platform.default_clk_name)
        clk_freq = 1e9/platform.default_clk_period

        if(sys_clk_freq is not None and sys_clk_freq != clk_freq):
            print("INFO: clk freq", sys_clk_freq, "using PLL")

            # PLL
            self.submodules.pll = pll = ECP5PLL()
            self.comb += pll.reset.eq(self.rst)
            pll.register_clkin(clk, clk_freq)
            pll.create_clkout(self.cd_sys, sys_clk_freq)
            sysclk = ClockSignal("sys")
        else:
            sysclk       = clk
            sys_clk_freq = clk_freq
            print("INFO: clk freq", sys_clk_freq, "using", platform.default_clk_name)


        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(platform)
        print(type(platform))

        """
        TMS9900 - Microprocessor Core
        """
        self.specials += Instance("tms9900",
            i_clk       = sysclk, 
            i_reset     = self.rst,
            o_addr_out  = self.addr,        # [15:0]
            i_data_in   = self.data_in,     # [15:0]
            o_data_out  = self.data_out,    # [15:0]
            o_rd        = self.rd,          # reg
            o_wr        = self.wr,          # reg
            o_rd_now    = self.rd_now,      # reg
            i_cache_hit = 1,
            i_use_ready = 1,
            i_ready     = 1,
            o_iaq       = self.iaq,         # reg 
            # o_as,           # reg
            i_int_req   = 1,
            i_ic03      = 4,# [3:0] 
            o_int_ack   = self.int_ack,     # reg 
            i_cruin     = self.cruin,
            o_cruout    = self.cruout,      # reg
            o_cruclk    = self.cruclk,
            i_hold      = 1,
            o_holda     = self.holda,       # reg
            i_waits     = self.waits,       # [7:0]
            o_stuck     = self.stuck,       # reg
            #o_ir_out,       # [15:0]
            #o_pc_ir_out,    # [15:0]
            #o_pc_ir_out2    # [15:0]   // previous
        )

        self.comb += self.nce_9902.eq(~(self.addr[6:16] == 0))
        self.comb += self.nce_rom.eq(self.addr[15])
        self.comb += self.wr_ram.eq(self.addr[15] & self.wr)
        self.comb += self.rd_ram.eq(self.addr[15] & self.rd)

        self.sync += self.data_in.eq(Mux(self.nce_rom, self.ram_o, self.rom_o))

        serial = platform.request("serial", 0)
        """
        TMS9902 - Async. Communications Controller
        
        CRU Memory region:
            0x0000, size = 32 bits
            addr[0] is ignored
        """
        assert sys_clk_freq < 64e6 and sys_clk_freq/1e6 == int(sys_clk_freq/1e6), "system clock must be integer and < 64 MHz"
        self.specials += Instance("tms9902",
            p_CLK_FREQ  = int(sys_clk_freq/1e6),
            i_CLK       = sysclk,
            #o_nRTS,
            #i_nDSR,
            #o_nCTS,
            #i_nINT,
            i_nCE       = self.nce_9902,
            o_CRUOUT    = self.cruout,
            o_CRUIN     = self.cruin,
            i_CRUCLK    = self.cruclk,
            o_XOUT      = serial.tx,
            i_RIN       = serial.rx,
            i_S         = self.addr[1:6]    # [4:0]
        )


        """
        ROM - Preloaded with TIBUG/EVMBUG monitor code

        Memory region:
            0x0000, size = 4096 words (repeated 0x0000 - 0x7FFF)
            addr[0] is ignored
        """
        self.specials += Instance("ROM",
            i_CLK   = sysclk,  
            i_nCS   = self.nce_rom,
            i_ADDR  = self.addr[1:13],  # [12:0]
            o_DO    = self.rom_o
        )


        """
        RAM

        Memory region:
            0x0000, size = 16k words (repeated 0x8000 - 0xFFFF)
            addr[0] is ignored
        """
        self.submodules.sram = sram(
            addr    = self.addr[1:13],
            re      = self.rd_ram,
            dat_r   = self.ram_o,
            we      = self.wr_ram,
            dat_w   = self.data_out
        )

def top_test(m):
    for i in range(200):
        yield m.addr
        yield m.data_out
        yield m.data_in
        yield m.rd
        yield m.wr


    # remember: values are written after the tick, and read before the tick.
    # wait one tick for the memory to update.
    yield
    # read what we have written, plus some initialization data
    for i in range(10):
        value = yield dut.mem[i]
        print(value)

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Colorlight 5A-75X")
    parser.add_argument("--clk",               default=None, type=int,     help="processor speed: 48e6 (default)")
    parser.add_argument("--build",             action="store_true",        help="Build bitstream")
    parser.add_argument("--sim",               action="store_true",        help="Simulate toplevel design")
    parser.add_argument("--load",              action="store_true",        help="Load bitstream")
    parser.add_argument("--revision",          default="7.0", type=str,    help="Board revision: 7.0 (default), 6.0 or 6.1")
    args = parser.parse_args()

    # Create our platform (fpga interface)
    #platform = board.Platform(revision=args.revision)
    platform = board.Platform()
    #for source in "top.v tms9900.v alu9900.v tms9902.v ram.v rom.v spram.v".split(" "):
    for source in "tms9900.v alu9900.v tms9902.v ram.v rom.v".split(" "):
        print("INFO: adding", source)
        platform.add_source(source)
    top = pll_top(platform, args.clk)

    # Build
    if(args.build):
        platform.build(top)

    # Simulate
    if(args.sim):
        run_simulation(top, top_test(top))

if __name__ == "__main__":
    main()


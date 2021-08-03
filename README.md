# tiny-tms9900

This is a simple TMS9900 CPU system for the ICE40UP5K FPGA.
The board I used for development is the UPduino V3 board.

Information about the board: https://github.com/tinyvision-ai-inc/UPduino-v3.0

The core runs at 12MHz, the ICE40UP5K is a quite slow FPGA. FPGA's internal high speed clock is used for clock generation. The core includes:
* my TMS9900 core in verilog (CPU)
* pnr's TMS9902 core (UART)
* 8K ROM, containing EVMBUG (modified to run UART at 9600 8N1)
* 32K RAM (top 32K of the address space)

The initial design uses about 57% of the logic resources of the FPGA.

The EVMBUG is nicely docymented by Stuart Conner at http://www.stuartconner.me.uk/tibug_evmbug/tibug_evmbug.htm#evmbug

The FTDI chip is used for serial communication after configuring the FPGA. Just use a terminal program to communicate with the system. 

Building the core
-----------------
This is simple: install the IceStorm toolchain and issue `make`.

Program the chip
----------------
iceprog top.bin

Reprogramming
-------------
Sometimes it is necessary to issue the programming command twice, or do `iceprog -e 128` to erase a portion of the flash to be able to communicate with the serial flash chip. When the core has already been programmed, it uses some of the pins used for programming the configuration flash chip.


# Forked from https://github.com/Speccery/tiny-tms9900

Reconfigured the system using the migen/Litex build system

Tasks TODO
----------
- Write some verilator scripts
- Validate tms9900 working
- Validate tms9902 working
- add tms9901
- add tms9918a

Tasks DONE
----------
- top.py


# Quick start guide

1. Install Python 3.6+ and FPGA vendor's development tools and/or [Verilator](http://www.veripool.org/):

```sh
$ git clone https://github.com/verilator/verilator
$ cd verilator
$ autoconf        # Create ./configure script
$ ./configure     # Configure and create Makefile
$ make -j         # Build Verilator itself
```

2. Install Migen/LiteX and the LiteX's cores:

```sh
$ wget https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py
$ chmod +x litex_setup.py
$ ./litex_setup.py init install --user (--user to install to user directory)
```
  Later, if you need to update all repositories:
```sh
$ ./litex_setup.py update
```

3. Buid the bitstream:

```sh
$ git clone https://github.com/hvegh/tiny-tms9900.git
$ cd tiny-tms9900
$ python top.py --build
```

# Results

Current utilisation for 32KB ram, 8 KB rom, tms9900 and tms9902:
----------------------------------------------------------------
```
Info: Device utilisation:
Info: 	       TRELLIS_SLICE:  1641/12144    13%
Info: 	          TRELLIS_IO:     3/  197     1%
Info: 	                DCCA:     1/   56     1%
Info: 	              DP16KD:     8/   56    14%
Info: 	          MULT18X18D:     0/   28     0%
Info: 	              ALU54B:     0/   14     0%
Info: 	             EHXPLLL:     0/    2     0%
Info: 	             EXTREFB:     0/    1     0%
Info: 	                DCUA:     0/    1     0%
Info: 	           PCSCLKDIV:     0/    2     0%
Info: 	             IOLOGIC:     0/  128     0%
Info: 	            SIOLOGIC:     0/   69     0%
Info: 	                 GSR:     0/    1     0%
Info: 	               JTAGG:     0/    1     0%
Info: 	                OSCG:     0/    1     0%
Info: 	               SEDGA:     0/    1     0%
Info: 	                 DTR:     0/    1     0%
Info: 	             USRMCLK:     0/    1     0%
Info: 	             CLKDIVF:     0/    4     0%
Info: 	           ECLKSYNCB:     0/   10     0%
Info: 	             DLLDELD:     0/    8     0%
Info: 	              DDRDLL:     0/    4     0%
Info: 	             DQSBUFM:     0/    8     0%
Info: 	     TRELLIS_ECLKBUF:     0/    8     0%
Info: 	        ECLKBRIDGECS:     0/    2     0%

Info: Max frequency for clock '$glbnet$clk25$TRELLIS_IO_IN': 78.70 MHz (PASS at 25.00 MHz)
```

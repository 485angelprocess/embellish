import unittest

from core import CoreTop, CoreComponent, Instruction, Special

from amaranth.sim import *

from bus_sim import *

def run_with_capture(sim, filename):
    with sim.write_vcd("bench/{}".format(filename)):
        sim.run()
    

class TestCore(unittest.TestCase):
    def test_mem(self):
        dut = CoreTop()
        
        async def process(ctx):
            await set_dest(ctx, dut.consume, CoreComponent.MEM)
            await single_write(ctx, dut.consume, 0, 11)
            await single_write(ctx, dut.consume, 1, 13)
            await single_write(ctx, dut.consume, 2, 15)
            assert await single_read(ctx, dut.consume, 0) == 11
            assert await single_read(ctx, dut.consume, 1) == 13
            assert await single_read(ctx, dut.consume, 2) == 15
            
        sim = Simulator(dut)
        sim.add_clock(1e-8)
        sim.add_testbench(process)
        
        run_with_capture(sim, "tb_mem.vcd")
        
    def test_run_add(self):
        dut = CoreTop()
        
        async def process(ctx):
            
            await set_dest(ctx, dut.consume, CoreComponent.PRO)
            await double_write(ctx, dut.consume, 0, Instruction.make(Instruction.LOADI, 0, 11))
            await double_write(ctx, dut.consume, 2, Instruction.make(Instruction.LOADI, 1, 12))
            await double_write(ctx, dut.consume, 4, Instruction.make(Instruction.ADD, 0, 0, 1)) # Place result of r0+r1 into r0
            
            # Enable program
            await set_dest(ctx, dut.consume, CoreComponent.SPE)
            await single_write(ctx, dut.consume, Special.CTL, 1) # Enable program
            
            # Wait for program to run
            await ctx.tick().repeat(16)
            
            await set_dest(ctx, dut.consume, CoreComponent.REG)
            assert await single_read(ctx, dut.consume, 0) == 23
            
        sim = Simulator(dut)
        sim.add_clock(1e-8)
        sim.add_testbench(process)
        
        run_with_capture(sim, "tb_add.vcd")
        
if __name__ == "__main__":
    unittest.main()
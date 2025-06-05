import unittest
from amaranth.sim import *
from amaranth.lib import wiring
from amaranth import *

from bus_sim import *
from risc_core import RiscCore
from core import Memory

def map_bit(value, fromstart, fromstop, tostart, tostop):
    # Mapping
    bits = list()
    
    for i in range(fromstart, fromstop + 1):
        bits.append((value >> i) & 0b1)
        
        
    print(bits)
    j = 0
    sum = 0
    for i in range(tostart, tostop + 1):
        sum += bits[j] << i
        j += 1
    
    return sum

class InstructionBuilder(object):
    def __init__(self, *args):
        self.word = sum(args)
        
    def value(self):
        return self.word
        
    @classmethod
    def u(cls, imm, rd, op):
        return cls(
            imm << 12,
            rd  << 7,
            op
        )
        
    @classmethod
    def i(cls, imm, rs, f, rd, op):
        return cls(
            imm << 20,
            rs << 15,
            f  << 12,
            rd << 7,
            op
        )
        
    @classmethod
    def jal(cls, offset):
        
        #offset = offset & 0b1111_1111_1111_1111_1111
        print("Offset original 0x{:08X}".format(offset))
     
        offset = offset & 0x1F_FF_FF
        
        print("Offset truncated to 20 0x{:08X}".format(offset))
        
        offsetp = 0
        offsetp += map_bit(offset, 20, 20, 31, 31) # sign
        offsetp += map_bit(offset, 1,  10, 21, 30)
        offsetp += map_bit(offset, 11, 11, 20, 20)
        offsetp += map_bit(offset, 12, 19, 12, 19)
        
        print("Offset mapped 0x{:08X}".format(offsetp))
        
        # Stupid but don't wanna map offset rn
        return cls(
            offsetp,
            0b1101111
        )
        
        
    @classmethod
    def addi(cls, value, rs, rd):
        return InstructionBuilder.i(value, rs, 0b000, rd, 0b0010011)
        
    @classmethod
    def andi(cls, value, rs, rd):
        return InstructionBuilder.i(value, rs, 0b111, rd, 0b0010011)
        
    @classmethod
    def storeword(cls, offset, rs2, rs1):
        return InstructionBuilder(
            (offset & 0b111111100000) << 25,
            rs2 << 20,
            rs1 <<  15,
            0b010 << 12,
            (offset & 0b000000011111) << 7,
            0b0100011
        )
        
def core_with_program(program):
    m = Module()
        
    core = m.submodules.core = RiscCore()
    prog = m.submodules.prog = Memory(32, len(program) << 1, init = program)
        
    wiring.connect(m, core.prog, prog.bus)
        
    return m, core, prog
        
class TestRiscCore(unittest.TestCase):
    def test_set_reg_to_value(self):
        prog = list()
        
        prog.append(InstructionBuilder.andi(0, 0, 0)) # Clear register (and with 0)
        prog.append(InstructionBuilder.addi(11, 0, 0)) # add constand to register
        
        prog.append(InstructionBuilder.andi(0, 1, 1)) # Clear register 0
        prog.append(InstructionBuilder.addi(13, 1, 1)) # add constant
        
        # Store word at register 1 (13) with value from register 0 (11)
        prog.append(InstructionBuilder.storeword(0, 0, 1))
        
        prog = [p.value() for p in prog]
        
        dut, core, prog = core_with_program(prog)
        
        async def mem_process(ctx):
            assert await receive(ctx, core.bus) == (13, 11, 1)
            assert await receive(ctx, core.bus) == (14, 0, 1)
            assert await receive(ctx, core.bus) == (15, 0, 1)
            assert await receive(ctx, core.bus) == (16, 0, 1)
                
        sim = Simulator(dut)
        sim.add_clock(1e-8)
        sim.add_testbench(mem_process)
        
        with sim.write_vcd("bench/risc_set_reg.vcd"):
            sim.run()

if __name__ == "__main__":
    unittest.main()
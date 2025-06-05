from amaranth import *
from amaranth.lib import wiring, memory, enum, data
from amaranth.lib.wiring import In, Out

from signature import Bus
from switch import BusSwitch

class CoreComponent(enum.Enum):
    PRO = 0 # Program memory
    MEM = 1 # Data memory
    REG = 2 # Registers (general purpose)
    SPE = 3 # Special registers
    
class Special(enum.Enum):
    CTL = 0 # bit 0 - enable
    R = 1 # color channels
    G = 2
    B = 3
    X = 4 # location
    Y = 5 
    Z = 6
    F = 7 # frame count

class Instruction(enum.Enum):
    NOOP = 0  # Noop
    SYS = 1   # Sys call
    LOADI = 2 # Load immediate
    ADD = 3   # Add two registers
    MUL = 4   # Multiply two registers
    AND = 5   # Bitwise and
    OR = 6    # Bitwise or
    BEZ = 7   # Branch if equal to zero
    J = 8     # Jump
    BE  = 9
    BLE = 10
    
    @staticmethod
    def make(inst, a, b, c = 0):
        return inst.value | (a << 16) | (b << 32) | (c << 48)

class SysCall(enum.Enum):
    MSG = 0 # Send/receive on video line

class WishboneMemory(wiring.Component):
    """
    Memory device for local core memory
    """
    def __init__(self, shape, depth, init = []):
        self.shape = shape
        self.depth = depth
        self.init = init
        
        super().__init__({
            "bus": In(Bus(32, shape))
        })
        
    def elaborate(self, platform):
        m = Module()
        
        mem = m.submodules.mem = memory.Memory(shape = self.shape, depth = self.depth, init = self.init)
        
        read_port = mem.read_port()
        write_port = mem.write_port()
        
        # Access memory
        with m.If(self.bus.w_en):
            m.d.comb += write_port.en.eq(self.bus.stb & self.bus.cyc)
        
        m.d.comb += read_port.en.eq((~self.bus.w_en) & self.bus.stb & self.bus.cyc)
            
        # Address
        m.d.comb += write_port.addr.eq(self.bus.addr)
        m.d.comb += read_port.addr.eq(self.bus.addr)
        
        # Ack signal
        with m.If(self.bus.ack):
            m.d.sync += self.bus.ack.eq(0)
        with m.Else():
            m.d.sync += self.bus.ack.eq(write_port.en | read_port.en)
        
        m.d.comb += self.bus.r_data.eq(read_port.data)
        
        m.d.comb += write_port.data.eq(self.bus.w_data)
        
        return m
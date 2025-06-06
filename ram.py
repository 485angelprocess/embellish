from amaranth import *
from amaranth.lib import wiring, memory, enum, data
from amaranth.lib.wiring import In, Out

from signature import Bus

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
from amaranth import *
from amaranth.lib import wiring, memory, enum, data
from amaranth.lib.wiring import In, Out

from signature import Bus

class WishboneMemory(wiring.Component):
    """
    Memory device for local core memory
    """
    def __init__(self, shape, depth, init = [], granularity = 0):
        self.shape = shape
        self.depth = depth
        self.init = init
        self.granularity = granularity
        
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
        m.d.comb += write_port.addr.eq(self.bus.addr >> self.granularity)
        m.d.comb += read_port.addr.eq(self.bus.addr >> self.granularity)
        
        # Ack signal
        write_ok = Signal()
        
        m.d.comb += write_ok.eq(write_port.en)
        
        read_ok = Signal()
        
        m.d.sync += read_ok.eq(read_port.en)
        
        m.d.comb += self.bus.ack.eq(write_ok | read_ok)
        
        m.d.comb += self.bus.r_data.eq(read_port.data)
        
        m.d.comb += write_port.data.eq(self.bus.w_data)
        
        return m
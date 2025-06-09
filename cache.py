from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from signature import Bus

class InstructionDebug(object):
    def __init__(self):
        self.ready = None
        self.state = None

class InstructionCache(wiring.Component):
    def __init__(self):
        self.debug = InstructionDebug()
        
        super().__init__({
            "proc": In(Bus(32, 32)),
            "mem": Out(Bus(32, 8))
        })
        
    def elaborate(self, platform):
        m = Module()
        
        cache_width = 4
        
        cache_address = Array([Signal(32, name = "a{}".format(i)) for i in range(cache_width)])
        
        cache_ready = Array([Signal(name = "r{}".format(i)) for i in range(cache_width)])
        
        self.debug.ready = cache_ready
        
        cache = Array([Signal(32, name = "c{}".format(i)) for i in range(cache_width)])
        
        read_pointer = Signal(range(cache_width))
        write_pointer = Signal(range(cache_width))
        
        cache_hit = Signal()
        
        # Correct cache address is queued
        m.d.comb += cache_hit.eq(
                        (cache_address[read_pointer] == self.proc.addr) &
                        (cache_ready[read_pointer])
                    )
        
        address = Signal(32)
        
        byte_counter = Signal(2, init = 0)
        
        m.d.comb += self.proc.r_data.eq(cache[read_pointer])
        m.d.comb += self.mem.addr.eq(address + byte_counter)
        
        #write_next = Signal(range(cache_width))
        #m.d.comb += write_next.eq(write_pointer + 1)
        
        with m.FSM() as fsm:
            with m.State("Reset"):
                # Clear cache
                m.d.sync += read_pointer.eq(0)
                m.d.sync += write_pointer.eq(0)
                # Indicate first address we're loading
                m.d.sync += cache_address[0].eq(address)
                
                for i in range(cache_width):
                    m.d.sync += cache_ready[i].eq(0)
                m.next = "Load"
            with m.State("Load"):
                # Load words into cache
                with m.If(~cache_ready[write_pointer]):
                    m.d.sync += cache_address[write_pointer].eq(address)
                    m.d.comb += self.mem.stb.eq(1)
                    m.d.comb += self.mem.cyc.eq(1)
                    with m.If(self.mem.ack):
                        m.d.sync += cache[write_pointer].eq(
                                                (cache[write_pointer] >> 8) + 
                                                (self.mem.r_data << 24))
                        with m.If(byte_counter == 3):
                            # Finished reading word
                            m.d.sync += byte_counter.eq(0)
                            m.d.sync += write_pointer.eq(write_pointer + 1)
                            m.d.sync += cache_ready[write_pointer].eq(1)
                            m.d.sync += address.eq(address + 4) # ?
                        with m.Else():
                            # Next byte of word
                            m.d.sync += byte_counter.eq(byte_counter + 1)
                
                with m.If(self.proc.stb & self.proc.cyc & self.proc.ack):
                    m.d.sync += read_pointer.eq(read_pointer + 1) # Next value
                    m.d.sync += cache_ready[read_pointer].eq(0) # Clear ready flag
                
                with m.If(self.proc.stb & self.proc.cyc):
                    with m.If(cache_address[read_pointer] == self.proc.addr):
                        # Wait for program to be loaded
                        m.d.comb += self.proc.ack.eq(cache_ready[read_pointer])
                    with m.Else():
                        # Cache miss, set new address and clear cache
                        m.d.sync += address.eq(self.proc.addr)
                        m.next = "Reset"
        
        self.debug.state = fsm.state
        
        return m
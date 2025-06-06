"""
Send and receive data between cores
"""
from amaranth import *
from amaranth.lib import wiring, fifo, enum
from amaranth.lib.wiring import In, Out

from signature import Bus

class DelegateRegister(enum.Enum):
    WRITE_DATA = 0x00
    READ_DATA  = 0x01
    BUFFER_SIZE = 0x02
    INTERRUPT_DEST = 0x03
    INTERRUPT_SIZE = 0x04

class Delegate(wiring.Component):
    def __init__(self, shape = 8, buffer_size = 16):
        self.buffer_size = buffer_size
        
        self.interrupt_msg = 0x01
        
        self.shape = shape
        
        super().__init__({
            "bus": In(Bus(32, 8)),
            "interrupt": Out(Bus(32, 8))
        })
        
    def elaborate(self, platform):
        m = Module()
        
        mfifo = m.submodules.mfifo = fifo.SyncFIFO(depth = self.buffer_size, width = self.shape)
        
        m.d.comb += mfifo.w_data.eq(self.bus.w_data)
        
        interrupt_message = Signal(8, init = self.interrupt_msg)
        interrupt_size = Signal(range(self.buffer_size))
        
        m.d.comb += self.interrupt.w_data.eq(interrupt_message)
        m.d.comb += self.interrupt.w_en.eq(1)
        
        with m.If(mfifo.w_en & (mfifo.level == interrupt_size)):
            m.d.sync += self.interrupt.stb.eq(1)
            m.d.sync += self.interrupt.cyc.eq(1)
        with m.If(self.interrupt.ack):
            m.d.sync += self.interrupt.stb.eq(0)
            m.d.sync += self.interrupt.cyc.eq(0)
        
        with m.If(self.bus.w_en):
            with m.Switch(self.bus.addr):
                with m.Case(DelegateRegister.WRITE_DATA):
                    # Write data to buffer
                    m.d.comb += mfifo.w_en.eq(self.bus.cyc & self.bus.stb)
                    m.d.comb += self.bus.ack.eq(mfifo.w_rdy & self.bus.cyc & self.bus.stb)
                with m.Case(DelegateRegister.INTERRUPT_DEST):
                    with m.If(self.bus.cyc & self.bus.stb):
                        m.d.comb += self.bus.ack.eq(1)
                        m.d.sync += self.interrupt.dest.eq(self.bus.w_data)
                with m.Case(DelegateRegister.INTERRUPT_SIZE):
                    with m.If(self.bus.cyc & self.bus.stb):
                        m.d.comb += self.bus.ack.eq(1)
                        m.d.sync += interrupt_size.eq(self.bus.w_data)
                with m.Default():
                    # Invalid write
                    m.d.comb += self.bus.ack.eq(self.bus.cyc & self.bus.stb)
        with m.Else():
            with m.Switch(self.bus.addr):
                with m.Case(DelegateRegister.READ_DATA):
                    # Get data from read
                    m.d.comb += self.bus.r_data.eq(mfifo.r_data)
                    m.d.comb += self.bus.ack.eq(mfifo.r_rdy & self.bus.cyc & self.bus.stb)
                with m.Case(DelegateRegister.BUFFER_SIZE):
                    # Get size of buffer
                    m.d.comb += self.bus.r_data.eq(mfifo.level)
                    m.d.comb += self.bus.ack.eq(self.bus.cyc & self.bus.stb)
                with m.Case(DelegateRegister.INTERRUPT_DEST):
                    m.d.comb += self.bus.r_data.eq(self.interrupt.dest)
                    m.d.comb += self.bus.ack.eq(self.bus.cyc & self.bus.stb)
                with m.Case(DelegateRegister.INTERRUPT_SIZE):
                    m.d.comb += self.bus.r_data.eq(interrupt_size)
                    m.d.comb += self.bus.ack.eq(self.bus.cyc & self.bus.stb)
                with m.Default():
                    # Nothing to read
                    m.d.comb += self.bus.ack.eq(self.bus.cyc & self.bus.stb)
        
        self.level = mfifo.level
        
        return m
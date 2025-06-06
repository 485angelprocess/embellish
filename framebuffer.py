from amaranth import *
from amaranth.lib import wiring, enum, memory
from amaranth.lib.wiring import In, Out

from signature import Bus, Stream

class DisplayRegister(enum.Enum):
    FILL = 0 # Fill frame with color
    FILLR = 1
    FILLG = 2
    FILLB = 3

class FrameBuffer(wiring.Component):
    def __init__(self, shape = 24, width = 32, height = 32):
        self.width = width
        self.height = height
        
        super().__init__({
            "consume": In(Bus(32, 8)),
            "ram": Out(Bus(32, 8)),
            "produce": Out(Stream(shape))
        })
        
    def elaborate(self, platform):
        m = Module()
        
        num_pixels = self.width * self.height
        
        color_counter = Signal(range(3))
        address_counter = Signal(range(num_pixels))
        
        col_counter = Signal(range(self.width))
        
        pixel = Signal(24)
        
        m.d.comb += self.produce.tdata.eq(pixel)
        m.d.comb += self.produce.tuser.eq(col_counter == self.width - 1)
        m.d.comb += self.produce.tlast.eq(address_counter == (num_pixels*3) - 1)
        
        with m.FSM():
            with m.State("Startup"):
                m.next = "Stream"
            with m.State("Stream"):
                with m.If(self.consume.cyc):
                    m.next = "Access"
                
                m.d.comb += self.ram.addr.eq(address_counter)
                # Stream out data
                m.d.comb += self.ram.cyc.eq(self.produce.tready)
                m.d.comb += self.ram.stb.eq(self.produce.tready)
                
                m.d.comb += self.produce.tvalid.eq((self.ram.ack) & (color_counter == 2))
                
                with m.If(self.ram.cyc & self.ram.stb & self.ram.ack):
                        # Just one more color channel
                        m.d.sync += address_counter.eq(address_counter + 1)
                        
                        with m.If(color_counter == 2):
                            with m.If(self.produce.tlast):
                                # End of frame
                                m.d.sync += address_counter.eq(0)
                                m.d.sync += col_counter.eq(0)
                            with m.Elif(self.produce.tuser):
                                # End of row
                                m.d.sync += address_counter.eq(address_counter + 1)
                                m.d.sync += col_counter.eq(0)
                            with m.Else():
                                m.d.sync += col_counter.eq(col_counter + 1)
                            m.d.sync += color_counter.eq(0)
                        with m.Else():
                            m.d.sync += color_counter.eq(color_counter + 1)
            with m.State("Access"):
                wiring.connect(m, self.consume, self.ram)
                    
                with m.If(~self.consume.cyc):
                    m.next = "Stream"
        
        return m
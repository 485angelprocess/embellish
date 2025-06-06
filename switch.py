from amaranth import *
from amaranth.lib import wiring, memory, enum
from amaranth.lib.wiring import In, Out

from signature import Bus

class SwitchPortDef(object):
    def __init__(self, addr, data):
        self.addr = addr
        self.data = data

class BusDebug(object):
    def __init__(self, size = 2):
        self.cyc = [None for _ in range(size)]
        self.w_en = [None for _ in range(size)]
        self.select = None
        
class RangeToDest(wiring.Component):
    def __init__(self, major = (16,32), minor = (0,16), dest_shape = 1):
        self.major = major
        self.minor = minor
        
        super().__init__({
            "consume": In(Bus(32, 32)),
            "produce": Out(Bus(32, 32, dest_shape = dest_shape))
        })
        
    def elaborate(self, platform):
        m = Module()
        
        m.d.comb += [
            # Split address and destination at points
            self.produce.addr.eq(self.consume.addr[self.minor[0]:self.minor[1]]),
            self.produce.dest.eq(self.consume.addr[self.major[0]:self.major[1]]),
            
            # Transaction
            self.produce.stb.eq(self.consume.stb),
            self.produce.cyc.eq(self.consume.cyc),
            self.consume.ack.eq(self.produce.ack),
            
            self.produce.w_en.eq(self.consume.w_en),
            
            # Data
            self.produce.w_data.eq(self.consume.w_data),
            self.consume.r_data.eq(self.produce.r_data)
        ]
        
        return m

class DestToAddress(wiring.Component):
    def __init__(self, shift = 16, dest_shape = 1):
        self.shift = shift
        
        super().__init__({
            "consume": In(Bus(32, 32, dest_shape = dest_shape)),
            "produce": Out(Bus(32, 32))
        })
        
    def elaborate(self, platform):
        m = Module()
        
        m.d.comb += [
            # Split address and destination at points
            self.produce.addr.eq(self.consume.addr + (self.consume.dest << self.shift)),
            self.produce.dest.eq(0),
            
            # Transaction
            self.produce.stb.eq(self.consume.stb),
            self.produce.cyc.eq(self.consume.cyc),
            self.consume.ack.eq(self.produce.ack),
            
            self.produce.w_en.eq(self.consume.w_en),
            
            # Data
            self.produce.w_data.eq(self.consume.w_data),
            self.consume.r_data.eq(self.produce.r_data)
        ]
        
        return m

class BusSwitch(wiring.Component):
    def __init__(self, ports, dest_shape, addr = 16, data = 32):
        self.n = len(ports)
        
        p = dict()
        for i in range(len(ports)):
            p["p_{:02X}".format(i)] = Out(Bus(ports[i].addr, ports[i].data))
        
        super().__init__({
            "c_00": In(Bus(addr, data, dest_shape)),
            "c_01": In(Bus(addr, data, dest_shape)),
        } | p)
        
    def elaborate(self, platform):
        m = Module()
        
        select = Signal()
        
        # For visualizing
        self.debug = BusDebug()
        
        self.debug.cyc[0] = self.c_00.cyc
        self.debug.cyc[1] = self.c_01.cyc
        
        self.debug.w_en = [
            self.c_00.w_en,
            self.c_01.w_en
        ]
        
        self.debug.select = select
        
        with m.If(select == 0):
            with m.If(~self.c_00.cyc):
                # Check other input
                m.d.sync += select.eq(1)
            with m.Switch(self.c_00.dest):
                # Connect
                for i in range(self.n):
                    with m.Case(i):
                        p = getattr(self, "p_{:02X}".format(i))
                        c = self.c_00
                        m.d.comb += [
                            p.stb.eq(c.stb),
                            p.cyc.eq(c.cyc),
                            c.ack.eq(p.ack),
                            p.addr.eq(c.addr),
                            p.w_en.eq(c.w_en),
                            p.w_data.eq(c.w_data),
                            c.r_data.eq(p.r_data)
                        ]
                        
        with m.If(select == 1):
            with m.If(~self.c_01.cyc):
                # Check other input
                m.d.sync += select.eq(0)
            with m.Switch(self.c_01.dest):
                # Connect
                for i in range(self.n):
                    with m.Case(i):
                        p = getattr(self, "p_{:02X}".format(i))
                        c = self.c_01
                        m.d.comb += [
                            p.stb.eq(c.stb),
                            p.cyc.eq(c.cyc),
                            c.ack.eq(p.ack),
                            p.addr.eq(c.addr),
                            p.w_en.eq(c.w_en),
                            p.w_data.eq(c.w_data),
                            c.r_data.eq(p.r_data)
                        ]
        
        return m
        
class AddressSwitch(wiring.Component):
    def __init__(self, split = 256):
        self.split = split
        
        super().__init__({
            "consume": In(Bus(32, 32)),
            "a": Out(Bus(32, 32)),
            "b": Out(Bus(32, 32))
        })
        
    def elaborate(self, platform):
        m = Module()
        
        anb = Signal()
        
        m.d.comb += anb.eq(self.consume.addr < self.split)
        
        b_address = Signal(32)
        
        m.d.comb += b_address.eq(self.consume.addr - self.split)
        
        m.d.comb += [
            self.a.addr.eq(self.consume.addr),
            self.a.w_en.eq(self.consume.w_en),
            self.a.w_data.eq(self.consume.w_data)
        ]
        
        m.d.comb += [
            self.b.addr.eq(b_address),
            self.b.w_en.eq(self.consume.w_en),
            self.b.w_data.eq(self.consume.w_data)
        ]
        
        # Direct to a or b
        with m.If(anb):
            m.d.comb += [
                self.a.stb.eq(self.consume.stb),
                self.a.cyc.eq(self.consume.cyc),
                self.consume.ack.eq(self.a.ack),
                self.consume.r_data.eq(self.a.r_data)
            ]
        with m.Else():
            m.d.comb += [
                self.b.stb.eq(self.consume.stb),
                self.b.cyc.eq(self.consume.cyc),
                self.consume.ack.eq(self.b.ack),
                self.consume.r_data.eq(self.b.r_data)
            ]
        
        return m
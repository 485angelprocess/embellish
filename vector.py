def PointLayout(shape):
    return data.StructLayout({
        "x": shape,
        "y": shape
    })

class DrawLine(wiring.Component):
    def __init__(self, shape = signed(16)):
        self.shape = shape
        
        super.__init__({
            # Input
            "start": In(PointLayout(shape)),
            "stop" : In(PointLayout(shape)),
            "en":  In (1),
            
            # Output
            "valid": Out(1),
            "ready": In(1),
            "out":  Out(PointLayout(shape)),
            "last": Out(1)
        })
        
    def elaborate(self, platform):
        m = Module()
        
        start = Signal(PointLayout(self.shape))
        stop = Signal(PointLayout(self.shape))
        
        out = Signal(PointLayout(self.shape))
        
        t = Signal(self.shape) # Parameterized variable
        
        downsample = 2
        
        done = Signal()
        
        x_done = Signal()
        y_done = Signal()
        
        # Have we gotten to end of line
        with m.If(start.x < stop.x):
            m.d.comb += x_done.eq(out.x >= stop.x)
        with m.Else():
            m.d.comb += x_done.eq(out.x <= start.x)
            
        with m.If(start.y < stop.y):
            m.d.comb += y_done.eq(out.y >= stop.y)
        with m.Else():
            m.d.comb += y_done.eq(out.y <= start.y)
            
        m.d.comb += done.eq(x_done & y_done)
            
        # May need to do multiplication in steps
        m.d.comb += out.x.eq(
            ( (start.x << downsample)
                + (t * (stop.x - start.y))
            ) >> downsample
        )
        
        m.d.comb += out.y.eq(
            ( (start.y << downsample)
                + (t * (stop.y - start.y))
            ) >> downsample
        )
        
        m.d.comb += self.out.eq(out)
        
        # KX = KXa + KT(Xb-Xa)
        with m.FSM():
            with m.State("Idle"):
                with m.If(self.en):
                    # Load points
                    m.d.sync += start.eq(self.start)
                    m.d.sync += stop.eq(self.stop)
                    m.next = "Draw"
            with m.State("Active"):
                # Stream out points
                m.d.comb += self.valid.eq(1)
                m.d.comb += self.last.eq(done)
                with m.If(self.ready):
                    with m.If(done):
                        m.d.sync += t.eq(0)
                    with m.Else():
                        m.d.sync += t.eq(t + 1)
        
        return m
        
class VectorModule(wiring.Component):
    def __init__(self, shape = signed(16), out_shape = 8):
        self.shape = shape
        super().__init__({
            "consume": In(Bus(32, 32)),
            "produce": Out(Stream(8))
        })
        
    def elaborate(self, platform):
        m = Module()
        
        num_points = Signal(8)
        
        mem = m.submodules.mem = Memory(shape = self.shape, depth = 256, init = [])
        
        write_port = mem.write_port()
        read_port = mem.read_port()
        
        m.d.comb += write_port.addr.eq(self.consume.addr - 1)
        m.d.comb += write_port.data.eq(self.consume.w_data[0:16])
        
        with m.If(self.consume.stb & self.consume.cyc & self.consume.w_en):
            m.d.comb += self.consume.ack.eq(1)
            with m.If(self.consume.addr == 0):
                m.d.sync += num_points.eq(self.consume.w_data)
            with m.Else():
                m.d.comb += write_port.en.eq(1)
        
        counter = Signal(8)
        
        points = Array([Signal(self.shape, name = "p{}".format(i)) for i in range(4)])
        
        point_counter = Signal(range(4))
        
        m.d.comb += read_port.addr.eq(counter)
        
        line = m.submodules.line = DrawLine(self.shape)
        
        m.d.comb += line.start.x.eq(points[0])
        m.d.comb += line.start.y.eq(points[1])
        m.d.comb += line.stop.x.eq(points[2])
        m.d.comb += line.stop.y.eq(points[3])
        
        with m.FSM():
            with m.State("Idle"):
                with m.If(num_points > 0):
                    m.d.sync += point_counter.eq(0)
                    m.next = "Read"
            # Get each line segment
            with m.State("Read"):
                m.d.comb += read_port.en.eq(1)
                m.next = "Load"
            with m.State("Load"):
                m.d.sync += points[point_counter].eq(read_port.data)
                with m.If(point_counter == 3):
                    m.next = "Run"
                with m.Else():
                    m.d.sync += point_counter.eq(point_counter + 1)
                    with m.If(counter == (num_points << 1) - 1):
                        m.d.sync += counter.eq(0)
                    with m.Else():
                        m.d.sync += counter.eq(counter + 1)
                    m.d.sync += counter.eq(counter + 1)
                    m.next = "Read"
            with m.State("Run"):
                m.d.comb += line.en.eq(1)
                m.next = "Shift"
            with m.State("Shift"):
                # data out
                m.d.comb += line.ready.eq(1)
        return m
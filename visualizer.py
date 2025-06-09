import tkinter as tk

from widget import *
from ram import WishboneMemory
from risc_core import RiscCore
from cache import InstructionCache
from switch import BusSwitch, SwitchPortDef, RangeToDest
from delegate import Delegate
from framebuffer import FrameBuffer
from test_risc_core import InstructionBuilder

from amaranth import *
from amaranth.sim import *
from amaranth.lib import wiring

import random

import time

def sample_program():
    prog = list()
        
    prog.append(InstructionBuilder.andi(0, 0, 0)) # Clear register (and with 0)
    prog.append(InstructionBuilder.addi(11, 0, 0)) # add constand to register
    
    prog.append(InstructionBuilder.andi(0, 1, 1)) # Clear register 0
    prog.append(InstructionBuilder.addi(150, 1, 1)) # add constant
    
    # Store word at register 1 (13) with value from register 0 (11)
    prog.append(InstructionBuilder.storeword(0, 0, 1))
    
    offset = -4 * len(prog)
    
    prog.append(InstructionBuilder.jal(offset))
    
    prog = [p.value() for p in prog]
        
    pbytes = list()
        
    for p in prog:
        pbytes.append((p >>  0) & 0xFF)
        pbytes.append((p >>  8) & 0xFF)
        pbytes.append((p >> 16) & 0xFF)
        pbytes.append((p >> 24) & 0xFF)
        
    print(pbytes)
        
    return pbytes

window = tk.Tk()
window.title("Embellish Visualizer")

canvas = tk.Canvas(window, width = 1200, height = 800, bg = 'black')
canvas.pack(anchor = tk.NW, expand = True)

def cpu_setup():
    m = Module()
    
    #m.submodules.sc = sc = StackCore()
    
    m.submodules.mem = mem = WishboneMemory(8, 256, init = sample_program())
    m.submodules.switch = switch = BusSwitch([SwitchPortDef(32, 8)], 1, 32, 8, num_inputs = 2)
    m.submodules.cache = cache = InstructionCache()
    m.submodules.core = core = RiscCore()
        
    # Access to program memory
    wiring.connect(m, cache.mem, switch.c_00)
    wiring.connect(m, cache.proc, core.prog)
    
    wiring.connect(m, switch.p_00, mem.bus)
    
    # Map memory transactions to ram and peripherals
    wiring.connect(m, core.bus,  switch.c_01)
    
    #############################
    ## Widgets for visualizer ###
    #############################
    widgets = list()
    
    # Memory device
    mw = MemoryWidget(mem, WidgetParam(50, 100, 300, 550))
    membus = BusWidget(mem.bus, mw.param.spawn_right(100, 75, y_offset = 250), name = "mem")
    sw = SwitchWidget(switch, membus.param.spawn_right(50, 550, y_offset = -250))
    
    # CPU
    cachew = InstructionCacheWidget(cache, sw.param.spawn_right(100, 100, y_offset = 50))
    cw = RiscCoreWidget(core, cachew.param.spawn_right(200, 400, y_offset = -50))
    
    widgets.append(mw)
    widgets.append(membus)
    widgets.append(sw)
    widgets.append(cachew)
    widgets.append(cw)
    
    return m, widgets
    
def fb_setup():
    m = Module()
    
    m.submodules.mem = mem = WishboneMemory(8, 1024, init = [random.randrange(0, 256) for _ in range(1024)])
    m.submodules.fb = fb = FrameBuffer(width = 16, height = 16)
    
    wiring.connect(m, mem.bus, fb.ram)
    
    # m.d.comb += [
    #     mem.bus.stb.eq(fb.ram.stb),
    #     mem.bus.cyc.eq(fb.ram.cyc),
    #     fb.ram.ack.eq(mem.bus.ack),
    #     mem.bus.addr.eq(fb.ram.addr),
    #     mem.bus.w_en.eq(fb.ram.w_en),
    #     mem.bus.w_data.eq(fb.ram.w_data),
    #     fb.ram.r_data.eq(mem.bus.r_data)
    # ]
    
    mw = MemoryWidget(mem, WidgetParam(50, 100, 200, 250))    
    membus = BusWidget(mem.bus, mw.param.spawn_right(100, 100), name = "mem")
    
    fbw = FrameDisplayWidget(fb.produce, membus.param.spawn_right(100, 100))
    
    widgets = [fbw, mw, membus]
    
    return m, widgets
    
#m, widgets = cpu_setup()
m, widgets = fb_setup()
       
async def update(ctx):
    while True:
        for w in widgets:
            w.update(ctx)
        #assert ctx.get(m.submodules.fb.ram.ack) == ctx.get(m.submodules.mem.bus.ack)
        await ctx.tick()
        
sim = Simulator(m)
sim.add_clock(1e-8)
#sim.add_process(random_read)
sim.add_testbench(update)

for w in widgets:
    w.setup(canvas)

while True:
    for w in widgets:
        w.draw(canvas)    
    sim.advance()
    window.update_idletasks()
    window.update()
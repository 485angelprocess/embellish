import tkinter as tk

from widget import *
from stack_core import StackCore
from core import WishboneMemory
from risc_core import RiscCore
from cache import InstructionCache
from switch import BusSwitch, SwitchPortDef
from test_risc_core import InstructionBuilder

from amaranth import *
from amaranth.sim import *
from amaranth.lib import wiring

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

m = Module()

#m.submodules.sc = sc = StackCore()

m.submodules.mem = mem = WishboneMemory(8, 256, init = sample_program())
m.submodules.switch = switch = BusSwitch([SwitchPortDef(32, 8)], 1, 32, 8)
m.submodules.cache = cache = InstructionCache()
m.submodules.core = core = RiscCore()

wiring.connect(m, mem.bus, switch.p_00)
wiring.connect(m, cache.mem, switch.c_00)
wiring.connect(m, cache.proc, core.prog)
wiring.connect(m, core.bus,  switch.c_01)

widgets = list()
#sc = StackCoreWidget(sc)
#send = sc.from_bus_send("send")

mw = MemoryWidget(mem, WidgetParam(100, 100, 300, 550))
membus = BusWidget(mem.bus, mw.param.spawn_right(100, 75, y_offset = 250), name = "mem")
sw = SwitchWidget(switch, membus.param.spawn_right(50, 550, y_offset = -250))

cachew = InstructionCacheWidget(cache, sw.param.spawn_right(100, 100, y_offset = 100))

cw = RiscCoreWidget(core, cachew.param.spawn_right(200, 400, y_offset = -50))

widgets.append(mw)
widgets.append(membus)
widgets.append(sw)
widgets.append(cachew)
widgets.append(cw)

import random

async def random_read(ctx):
    # TEMP random reads
    port = cache.proc
    while True:
        address = random.randrange(0, 256)
        ctx.set(port.addr, address)
        await ctx.tick().repeat(10)
        ctx.set(port.stb, 1)
        ctx.set(port.cyc, 1)
        await ctx.tick().until(mem.bus.ack)
        ctx.set(port.stb, 0)
        ctx.set(port.cyc, 0)
        await ctx.tick().repeat(10)
    
async def update(ctx):
    while True:
        for w in widgets:
            w.update(ctx)
        await ctx.tick()
        
sim = Simulator(m)
sim.add_clock(1e-8)
#sim.add_process(random_read)
sim.add_testbench(update)

#with sim.write_vcd("bench/visualize.vcd"):
while True:
    canvas.delete("all") # Stupid and inefficient but fuck off
    for w in widgets:
        w.draw(canvas)    
    sim.advance()
    window.update_idletasks()
    window.update()
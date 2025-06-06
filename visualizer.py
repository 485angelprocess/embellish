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

canvas = tk.Canvas(window, width = 1600, height = 800, bg = 'black')
canvas.pack(anchor = tk.NW, expand = True)

m = Module()

#m.submodules.sc = sc = StackCore()

m.submodules.mem = mem = WishboneMemory(8, 256, init = sample_program())
m.submodules.switch = switch = BusSwitch([SwitchPortDef(32, 8)], 1, 32, 8, num_inputs = 3)
m.submodules.cache = cache = InstructionCache()
m.submodules.core = core = RiscCore()

m.submodules.periph_map = periph_map = RangeToDest()
m.submodules.periph_switch = periph_switch = BusSwitch(
                        [SwitchPortDef(32, 8), SwitchPortDef(32, 8)],
                        1,
                        addr = 32,
                        data = 8,
                        num_inputs = 1)
m.submodules.fb = fb = FrameBuffer(width = 16, height = 16)
m.submodules.vram = vram = WishboneMemory(8, 1024)

                        
# Access to program memory
wiring.connect(m, cache.mem, switch.c_00)
wiring.connect(m, cache.proc, core.prog)

wiring.connect(m, switch.p_00, mem.bus)

# Map memory transactions to ram and peripherals
wiring.connect(m, core.bus,  periph_map.consume)
# Map to secondary switch
wiring.connect(m, periph_map.produce, periph_switch.c_00)
# Switch to ram access
wiring.connect(m, periph_switch.p_00, switch.c_01)

# Framebuffer 
# Direct access by CPU
wiring.connect(m, fb.consume, periph_switch.p_01)
# Controller to memory device
wiring.connect(m, fb.ram, vram.bus)

#############################
## Widgets for visualizer ###
#############################
widgets = list()

# Memory device
mw = MemoryWidget(mem, WidgetParam(50, 100, 300, 550))
membus = BusWidget(mem.bus, mw.param.spawn_right(100, 75, y_offset = 250), name = "mem")
sw = SwitchWidget(switch, membus.param.spawn_right(50, 550, y_offset = -250))

periph_sw = SwitchWidget(periph_switch, WidgetParam(700, 325, 50, 100))

# CPU
cachew = InstructionCacheWidget(cache, sw.param.spawn_right(100, 100, y_offset = 50))
cw = RiscCoreWidget(core, cachew.param.spawn_right(200, 400, y_offset = -50))

# Framebuffer
vramw = MemoryWidget(vram, cw.param.spawn_right(100, 200))
displayw = FrameDisplayWidget(fb.produce, vramw.param.spawn_right(100, 100))

widgets.append(mw)
widgets.append(membus)
widgets.append(sw)
widgets.append(periph_sw)
widgets.append(cachew)
widgets.append(cw)
widgets.append(vramw)
widgets.append(displayw)
    
async def update(ctx):
    while True:
        for w in widgets:
            w.update(ctx)
        await ctx.tick()
        
sim = Simulator(m)
sim.add_clock(1e-8)
#sim.add_process(random_read)
sim.add_testbench(update)

with sim.write_vcd("bench/visualize.vcd"):
    while True:
        canvas.delete("all") # Stupid and inefficient but fuck off
        for w in widgets:
            w.draw(canvas)    
        sim.advance()
        window.update_idletasks()
        window.update()
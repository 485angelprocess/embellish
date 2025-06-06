import tkinter as tk
from PIL import Image, ImageTk

FONT_HEADING = "tkDefaultFont 12"
FONT_NORMAL =  "tkDefaultFont 10"
FONT_SMALL =   "tkDefaultFont 8"

def clip(v, min = 0, max = 255):
    if v > max:
        return max
    if v < min:
        return min
    return v

class Color(object):
    def __init__(self, r, g, b):
        self.c = [r, g, b]
        
    def fade_white(self, step = 1):
        for i in range(len(self.c)):
            if self.c[i] < 255:
                self.c[i] = clip(self.c[i] + step)
                
    def fade_black(self, step = 1):
        for i in range(len(self.c)):
            if self.c[i] > 0:
                self.c[i] -= step
            if self.c[i] < 0:
                self.c[i] = 0
                
    def set_r(self, r, max = 255):
        self.c[0] = clip(self.c[0] + r, max = max)
        
    def set_g(self, g, max = 255):
        self.c[1] = clip(self.c[1] + g, max = max)
        
    def set_b(self, b, max = 255):
        self.c[2] = clip(self.c[2] + b, max = max)
        
    def is_black(self):
        return all([c == 0 for c in self.c])
        
    def as_hex(self, scale = 100):
        color = [int(c * scale / 100) for c in self.c]
        return "#{:02X}{:02X}{:02X}".format(*color)

class WidgetBase(object):
    def draw(self):
        pass
        
    def update(self, ctx):
        pass
        
    def box(self):
        return self.param
        
class WidgetParam(object):
    """
    Define a box for a visualizer element
    """
    def __init__(self, x, y, w, h, margin = 20, padding = 10):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        
        self.padding = padding
        self.margin = margin
        
    def top_left(self):
        return (self.x + self.margin, self.y + self.margin)
        
    def bottom_right(self):
        return (self.x + self.w + self.margin, self.y + self.h + self.margin)
        
    def top_left_padded(self, x_offset = 0, y_offset = 0):
        return (self.x + self.padding + self.margin + x_offset, 
                self.y + self.padding + self.margin + y_offset)

    def inner_size(self):
        return (
            self.w - (2*(self.padding)),
            self.h - (2*(self.padding))
        )
        
    def offset(self, offset_x, offset_y, margin, padding):
        
        return WidgetParam(
            x = self.top_left_padded()[0] + offset_x,
            y = self.top_left_padded()[1] + offset_y,
            w = self.w - self.margin - self.padding,
            h = self.h - self.margin - self.padding,
            margin = margin,
            padding = padding
        )
        
    def spawn_right(self, w, h, y_offset = 0):
        x = self.x + self.w + (2*self.margin)
        y = self.y + y_offset
        return WidgetParam(
            x = x,
            y = y,
            w = w,
            h = h,
            margin = self.margin,
            padding = self.padding
        )
        
class BusWidget(WidgetBase):
    """
    Displays wishbone bus transactions
    """
    def __init__(self, bus, box, name = "bus"):
        self.bus = bus
        self.param = box
        self.name = name
        
        self.cyc = False
        self.stb = False
        self.ack = False
        
        self.addr = None
        self.data = None
        
        self.color = Color(255, 255, 255)
        
    def update(self, ctx):
        self.cyc = ctx.get(self.bus.cyc)
        self.stb = ctx.get(self.bus.stb)
        self.ack = ctx.get(self.bus.ack)
        
        self.data = ctx.get(self.bus.r_data)
        self.addr = ctx.get(self.bus.addr)
        
        if self.ack and self.cyc and self.stb:
            if ctx.get(self.bus.w_en):
                self.color.set_r(-200)
                self.color.set_g(-200)
            else:
                self.color.set_r(-200)
                self.color.set_b(-200)
        
    def draw(self, canvas):
        color = self.color.as_hex()
            
        canvas.create_rectangle(self.param.top_left(), 
                                self.param.bottom_right(),
                                outline = color)
                                
        canvas.create_text(
            self.param.top_left_padded(),
            text = self.name,
            fill = color,
            font = FONT_NORMAL,
            anchor = tk.NW
        )
        
        if self.addr is not None:
            canvas.create_text(
                self.param.top_left_padded(y_offset = 12),
                text = "addr: 0x{:02X}".format(self.addr),
                fill = color,
                font = FONT_NORMAL,
                anchor = tk.NW
            )
        
        if self.data is not None:
            canvas.create_text(
                self.param.top_left_padded(y_offset = 24),
                text = "data: 0x{:02X}".format(self.data),
                fill = color,
                font = FONT_NORMAL,
                anchor = tk.NW
            )
        
        self.color.fade_white(20)

class InstructionCacheWidget(object):
    """
    Displays instruction cache state
    """
    def __init__(self, cache, param):
        self.cache = cache
        self.param = param
        
        self.ready = None
        self.state = 0
        
    def update(self, ctx):
        debug = self.cache.debug
        if debug is None:
            return
        # Hardcoded for now
        self.ready = [ctx.get(debug.ready[i]) for i in range(4)]
        self.state = ctx.get(debug.state)
        
    def draw(self, canvas):
        canvas.create_rectangle(self.param.top_left(), 
                                self.param.bottom_right(),
                                outline = "white")
        
        canvas.create_text(self.param.top_left_padded(),
                            text = "Cache",
                            fill = "white",
                            font = FONT_NORMAL,
                            anchor = tk.NW)
        
        msg = " " 
        if self.state == 0:
            msg = "..."
            
        canvas.create_text(self.param.top_left_padded(y_offset = 12),
                            text = msg,
                            fill = "white",
                            font = FONT_NORMAL,
                            anchor = tk.NW)
        
        if self.ready is not None:
            msg = ["_" for _ in range(4)]
            for i in range(len(self.ready)):
                if self.ready[i]:
                    msg[i] = "x"
            
            canvas.create_text(self.param.top_left_padded(y_offset = 24),
                            text = " ".join(msg),
                            fill = "white",
                            font = FONT_NORMAL,
                            anchor = tk.NW)

class MemoryTransaction(object):
    """
    Displays memory transactions,
    highlights reads and writes
    """
    def __init__(self):
        self.mode = None
        self.timer = 0
        self.address = None
        
        self.colors = dict()
        self.colors["ready"] = (125, 125, 0)
        self.colors["active"] = (0, 255, 0)
        self.colors["write"] = (0, 125, 255)
        
    def ready(self, address, write = False, intensity = 100):
        self.mode = "ready"
        self.timer = intensity
        self.address = address
        
    def start(self, address, write = False, intensity = 100):
        self.mode = "active"
        if write:
            self.mode = "write"
        self.timer = intensity
        self.address = address
        
    def update(self):
        if self.timer > 0:
            self.timer -= 1
        else:
            self.timer = 0
        
    def color(self):
        color = (0, 0, 0)
        if self.mode in self.colors:
            color = self.colors[self.mode]
        
        color = [int(c * self.timer / 100) for c in color]
        
        return "#{:02X}{:02X}{:02X}".format(*color)
        
    def active(self):
        return self.timer > 0
        
class MemoryWidget(WidgetBase):
    def __init__(self, mem, param, size = 256):
        self.mem = mem
        self.param = param
        self.size = size
        
        self.t = 0
        self.transactions = [MemoryTransaction() for _ in range(16)]
        
    def draw_address(self, canvas, address, x, y, w, h):
        fill = "white"
        for trans in self.transactions:
            if trans.address == address:
                canvas.create_rectangle((x, y),
                                (x + w, y + h),
                                fill = trans.color())
            
        if h > 10:
            canvas.create_text((x+1, y+1),
                                text = "0x{:02X}".format(address),
                                fill = "white",
                                font = FONT_SMALL,
                                anchor = tk.NW)
                            
    def update(self, ctx):
        if ctx.get(self.mem.bus.stb) and ctx.get(self.mem.bus.cyc):
            if ctx.get(self.mem.bus.ack):
                self.transactions[self.t].start(ctx.get(self.mem.bus.addr), ctx.get(self.mem.bus.w_en))
                self.t = (self.t + 1) % len(self.transactions)
            else:
                self.transactions[self.t].ready(ctx.get(self.mem.bus.addr), ctx.get(self.mem.bus.w_en))
            
        [trans.update() for trans in self.transactions]
        
    def draw(self, canvas):
        canvas.create_rectangle(self.param.top_left(), 
                                self.param.bottom_right(),
                                outline = "white")
        
        # Create grid of memory locations
        cols = 8
        rows = int(self.size / cols)
        
        w, h = self.param.inner_size()
        tx, ty = self.param.top_left_padded()
        
        col_width = w/cols
        row_width = h/rows
        
        #assert(row_width > 12)
        
        addr = 0
        for c in range(cols):
            for r in range(rows):
                x = tx + (c * col_width)
                y = ty + (r * row_width) + 2
                self.draw_address(canvas, addr, x, y, col_width, row_width)
                addr += 1

class SwitchWidget(WidgetBase):
    def __init__(self, switch, param):
        self.switch = switch
        self.param = param
        
        self.n = self.switch.num_inputs
        
        self.colors = [Color(0, 0, 0) for _ in range(self.n)]
        
    def update(self, ctx):
        debug = self.switch.debug
        for i in range(self.n):
            if ctx.get(debug.cyc[i]) and (ctx.get(debug.select) == i):
                if ctx.get(debug.w_en[i]):
                    self.colors[i].set_b(255)
                else:
                    self.colors[i].set_g(255)
                if ctx.get(debug.ack[i]):
                    self.colors[i].set_r(100)
                    self.colors[i].set_g(50)
                    self.colors[i].set_b(50)
                
            
    def draw_section(self, canvas, color, offset, w, h):
        x, y = self.param.top_left_padded()
        canvas.create_rectangle((x,     y + offset), 
                                (x + w, y + h + offset),
                                fill = color.as_hex())
            
    def draw(self, canvas):
        canvas.create_rectangle(self.param.top_left(), 
                                self.param.bottom_right(),
                                outline = "white")
                                
        w, h = self.param.inner_size()
        
        halfh = int(h / self.n)
        
        for i in range(self.n):
            if not self.colors[i].is_black():
                self.draw_section(canvas, self.colors[i], i*halfh, w, halfh)
            self.colors[i].fade_black(10)
    
class RiscRegister(object):
    def __init__(self, value = 0):
        self.value = value
        
        self.color = Color(0, 0, 0)
        
    def update(self, new_value):
        if new_value != self.value:
            self.value = new_value
            self.color.set_b(40, max = 200)
            self.color.set_g(40, max = 200)
            
    def draw(self, canvas, x, y, w, h):
        canvas.create_rectangle((x, y), 
                                (x + w, y + h),
                                fill = self.color.as_hex())
        
        canvas.create_text((x + 1, y + 1),
                            text = "0x{:04X}".format(self.value),
                            fill = "white",
                            font = FONT_SMALL,
                            anchor = tk.NW)
                            
        self.color.fade_black()
    
class RiscCoreWidget(WidgetBase):
    def __init__(self, core, param):
        self.core = core
        self.param = param
        
        self.pc = 0
        
        self.reg = [RiscRegister() for _ in range(32)]
        
    def update(self, ctx):
        self.pc = ctx.get(self.core.debug.pc)
        
        for i in range(32):
            self.reg[i].update(ctx.get(self.core.debug.reg[i]))
        
    def draw(self, canvas):
        canvas.create_rectangle(self.param.top_left(), 
                                self.param.bottom_right(),
                                outline = "white")
                                
        canvas.create_text(self.param.top_left_padded(),
                            text = "Risc CPU",
                            fill = "white",
                            font = FONT_NORMAL,
                            anchor = tk.NW)
                            
        row_size = 18
        col_size = 50
        
        canvas.create_text(self.param.top_left_padded(y_offset = 1 * row_size),
                            text = "PC: 0x{:02X}".format(self.pc),
                            fill = "white",
                            font = FONT_NORMAL,
                            anchor = tk.NW)
        
        tx, ty = self.param.top_left_padded(y_offset = 1 * row_size)
        
        i = 0
        for c in range(2):
            for r in range(16):
                x = tx + (col_size * c)
                y = ty + (row_size * (r+2))
                self.reg[i].draw(canvas, x, y, col_size, row_size)
                i += 1
                
import random
import numpy as np
    
class FrameDisplayWidget(WidgetBase):
    def __init__(self, stream, param):
        self.stream = stream
        self.param = param
        
        self.x = 0
        self.y = 0
        
        self.contents = np.full(shape=(16, 16, 3), fill_value=[135, 206, 250], dtype=np.uint8)
        
        self.update_img()
        
    def update_img(self):
        m_img = Image.fromarray(self.contents, 'RGB')
        m_img = m_img.resize(self.param.inner_size())
        img = ImageTk.PhotoImage(image = m_img)
        self.img = img
        
    def update(self, ctx):
        ctx.set(self.stream.tready, 1)
        if ctx.get(self.stream.tvalid):
            
            # Insert new pixels
            self.contents[self.y][self.x] = ctx.get(self.stream.tdata)
            
            # Keep track of scanner
            if ctx.get(self.stream.tlast):
                self.x = 0
                self.y = 0
            elif ctx.get(self.stream.tuser):
                self.x = 0
                self.y += 1
            else:
                self.x += 1
                
            self.update_img()
    
    def draw(self, canvas):
        canvas.create_rectangle(self.param.top_left(), 
                                self.param.bottom_right(),
                                outline = "white")
                                
        
        canvas.create_image(self.param.top_left_padded(), anchor = "nw", image = self.img)
async def set_dest(ctx, port, dest):
    ctx.set(port.dest, dest)

async def single_write(ctx, port, addr, data):
    ctx.set(port.addr, addr)
    ctx.set(port.w_data, data)
    ctx.set(port.stb, 1)
    ctx.set(port.cyc, 1)
    ctx.set(port.w_en, 1)
    await ctx.tick().until(port.ack)
    ctx.set(port.stb, 0)
    ctx.set(port.cyc, 0)
    ctx.set(port.w_en, 0)
    
async def double_write(ctx, port, addr, data, size = 32):
    ctx.set(port.addr, addr)
    ctx.set(port.w_data, data)
    ctx.set(port.stb, 1)
    ctx.set(port.cyc, 1)
    ctx.set(port.w_en, 1)
    await ctx.tick().until(port.ack)
    ctx.set(port.addr, addr + 1)
    ctx.set(port.w_data, data >> size)
    await ctx.tick().until(port.ack)
    ctx.set(port.stb, 0)
    ctx.set(port.cyc, 0)
    ctx.set(port.w_en, 0)
    
async def single_read(ctx, port, addr):
    ctx.set(port.addr, addr)
    ctx.set(port.stb, 1)
    ctx.set(port.cyc, 1)
    data,  = await ctx.tick().sample(port.r_data).until(port.ack)
    ctx.set(port.stb, 0)
    ctx.set(port.cyc, 0)
    return data
    
async def receive(ctx, port, timeout = 100):
    while True:
        ctx.set(port.ack, 1)
        stb, addr, w_data, w_en = await ctx.tick().sample(port.stb, port.addr, port.w_data, port.w_en).until(port.cyc)
        if stb:
            return addr, w_data, w_en
        timeout -= 1
        if timeout == 0:
            raise Exception("Timed out on bus receive")
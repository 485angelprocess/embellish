from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

class Bus(wiring.Signature):
    def __init__(self, address_shape, data_shape, dest_shape = 1, user = None):
        super().__init__({
            "cyc": Out(1),
            "stb": Out(1),
            "ack": In(1),
            "addr": Out(address_shape),
            "w_en": Out(1),
            "w_data": Out(data_shape),
            "r_data": In(data_shape),
            "dest": In(dest_shape)
        })
        
class Stream(wiring.Signature):
    def __init__(self, data_shape, user_shape = 1):
        super().__init__({
            "tdata": Out(data_shape),
            "tvalid": Out(1),
            "tready": In(1),
            "tuser": Out(user_shape),
            "tlast": Out(1)
        })
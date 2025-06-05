"""
CPU with small register stack
"""
from amaranth import *
from amaranth.lib import wiring, data, enum
from amaranth.lib.wiring import In, Out

from signature import Bus

InstLayout = data.StructLayout({
    "op": 16,
    "v":  16
})

class Instruction(enum.Enum):
    NOOP = 0
    JUMP = 1 
    LDLP = 2 # pushes the value at the workspace onto stack
    PFIX = 3 # pushes a constant onto operand
    LDNL = 4 # Loads value from A + 4*operand
    LDC  = 5 # pushes constand
    LDNLP= 6 # Load non local pointer
    NFIX = 7 # Complements prefix register
    LDL  = 8 # Loads value at at stack pointer
    ADC  = 9 # Add constant
    AJW  = 10# Adjust workspace
    EQC  = 11# equals constant
    STL  = 12# Store local at stack pointer + operand
    STNL = 13# Store B at A + operand
    
class StackDebug(object):
    def __init__(self, stack, operand, workspace, prog_counter, op, fsm):
        self.stack = stack
        self.operand = operand
        self.workspace = workspace
        self.prog_counter = prog_counter
        self.op = op
        self.fsm = fsm

class StackCore(wiring.Component):
    def __init__(self, stack_size = 3):
        self.stack_size = stack_size
        
        super().__init__({
            "prog": Out(Bus(16, 32)),
            "mem":  Out(Bus(16, 32)),
            "send": Out(Bus(16, 32)),
            "int":  In(Bus(16, 8))
        })
        
    def elaborate(self, platform):
        m = Module()
        
        # Register space
        stack = Array([Signal(signed(32), name = "stack_{}".format(i)) for i in range(self.stack_size)])
        # Working register
        prefix = Signal(signed(32))
        
        # Memory pointer
        workspace = Signal(32)
        # Program counter
        prog_counter = Signal(32)
        
        push = Signal()
        push_value = Signal(32)
        
        op = Signal(16)
        v  = Signal(16)
        
        # Split incoming program
        m.d.comb += op.eq(self.prog.r_data[16:32])
        m.d.comb += v.eq(self.prog.r_data[0:16])
         
        # Memory to read from
        load_pointer = Signal(32)
        
        with m.If(push):
            for i in range(self.stack_size - 1):
                m.d.sync += stack[i + 1].eq(stack[i])
            m.d.sync += stack[0].eq(push_value)
            
        # Operand is the prefix and the lower 16
        operand = Signal(32)
        
        m.d.comb += operand.eq((prefix << 16) + v)
        
        with m.FSM() as fsm:
            with m.State("Run"):
                with m.If(self.prog.stb & self.prog.cyc & self.prog.ack):
                    with m.Switch(op):
                        with m.Case(Instruction.NOOP):
                            pass
                        with m.Case(Instruction.LDL):
                            # Load value relative to workspace
                            m.d.sync += load_pointer.eq(workspace + (operand))
                            m.d.sync += prefix.eq(0)
                            m.next = "Load"
                        with m.Case(Instruction.LDLP):
                            m.d.comb += push_value.eq(workspace + operand)
                            m.d.comb += push.eq(1)
                            m.d.sync += prefix.eq(0)
                        with m.Case(Instruction.PFIX):
                            # Shift in constant to operand register
                            m.d.sync += prefix.eq((operand << 16) + v)
                        with m.Case(Instruction.LDNL):
                            # Load value relative to first in stack
                            m.d.sync += load_pointer.eq(stack[0] + (operand))
                            m.d.sync += prefix.eq(0)
                            m.next = "Load"
                        with m.Case(Instruction.LDC):
                            # Load immediate into stack
                            m.d.comb += push_value.eq(operand)
                            m.d.comb += push.eq(1)
                            m.d.sync += prefix.eq(0)
                        with m.Case(Instruction.LDNLP):
                            # Load non local pointer
                            m.d.comb += push_value.eq(stack[0] + operand)
                            m.d.comb += push.eq(1)
                            m.d.sync += prefix.eq(0)
                        with m.Default():
                            Assert(1, "Instruction not implemented")
            with m.State("Load"):
                # Load value from memory into stack
                m.d.comb += self.mem.addr.eq(load_pointer)
                m.d.comb += self.mem.stb.eq(1)
                m.d.comb += self.mem.cyc.eq(1)
                m.d.comb += push.eq(self.mem.ack)
                m.d.comb += push_value.eq(self.mem.r_data)
                with m.If(self.mem.ack):
                    m.next = "Run"
                    
        # Use for visualizer
        self.debug = StackDebug(stack = stack, 
                                operand = operand,
                                workspace = workspace,
                                prog_counter = prog_counter,
                                op = op,
                                fsm = fsm)
                
        return m
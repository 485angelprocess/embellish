"""
Implementation of RV32I instructions
"""
from amaranth import *
from amaranth.lib import wiring, enum, data
from amaranth.lib.wiring import In, Out
from signature import Bus

class Registers(enum.Enum):
    SEND_SIZE = 0 # number of words to send
    SEND_DEST = 1 # where to send words
    SEND_BUF  = 2 # location of buffer

class Instruction(enum.Enum):
    # These are the op codes for the base instruction set
    LUI         = 0b0110111 # Load upper immediate
    AUIPC       = 0b0010111 # Add upper immediate to program counter
    ARITHIMM    = 0b0010011
    JAL         = 0b1101111
    BRANCH      = 0b1100011
    JALR        = 0b1100111
    MEMORYLOAD  = 0b0000011
    MEMORYSTORE = 0b0100011
    ARITH       = 0b0110011
    FENCE       = 0b0001111
    E           = 0b1110011
    
risc_instruction_layout = data.UnionLayout({
    "op": 7,
    "r": data.StructLayout({
        "op": 7,
        "rd": 5,
        "f_lower": 3,
        "rs1": 5,
        "rs2": 5,
        "f_upper":  7
    }),
    "i": data.StructLayout({
        "op": 7,
        "rd": 5,
        "f" : 3,
        "rs": 5,
        "imm":signed(12) 
    }),
    "u": data.StructLayout({
        "op":  7,
        "rd":  5,
        "imm": signed(20)
    }),
    "s": data.StructLayout({
        "op": 7,
        "imm_lower": 5,
        "f": 3,
        "rs1": 5,
        "rs2": 5,
        "imm_upper": 7
    }),
    "j": data.StructLayout({
        "op": 7,
        "rd": 5,
        "offset": signed(20)
    }),
    "b": data.StructLayout({
        "op": 7,
        "offset_lower": 5,
        "f": 3,
        "rs1": 5,
        "rs2": 5,
        "offset_upper": 7
    })
})
    
class CoreDebug(object):
    def __init__(self):
        self.instruction = None
        self.reg = None
        self.pc = None
    
class RiscCore(wiring.Component): # RISCV 32I implementation (32E has 16 regs)
    def __init__(self, n_regs = 32):
        self.n_regs = 32
        
        super().__init__({
            "bus": Out(Bus(32, 8)),
            "prog": Out(Bus(32, 32)),
            "int": In(Bus(32, 8))
        })
        
    def elaborate(self, platform):
        m = Module()
        
        enable = Signal(init = 1)
        
        reg = Array([Signal(signed(32), name = "r{:02X}".format(i)) for i in range(32)])
        
        program_address_shape = 32
        
        program_counter = Signal(program_address_shape)
        
        instruction = Signal(risc_instruction_layout)
        
        m.d.comb += self.prog.addr.eq(program_counter)
        
        instruction_cache = Signal(32)
        
        mem_counter = Signal(range(4))
        mem_register = Signal(32)
        mem_address = Signal(32)
        
        jal_offset = Signal(signed(21))
        
        # jal offset mapping
        # offset[20|10:1|11|19:12]
        m.d.comb += jal_offset.eq(
            (instruction.j.offset[0:8] << 12) + # offset[19:12]
            (instruction.j.offset[8]   << 11) + # offset[11]
            (instruction.j.offset[9:19]<< 1)  + # offset[10:1]
            (instruction.j.offset[19]  << 20)   # offset[20]
        )
        
        branch_offset = Signal(signed(13))
        
        # branch offset mapping
        # offset_upper[12|10:5], offset_lower[4:1|11]
        m.d.comb += branch_offset.eq(
            (instruction.b.offset_lower[0] << 11) +
            (instruction.b.offset_lower[1:5] << 1) +
            (instruction.b.offset_upper[0:6] << 5) +
            (instruction.b.offset_upper[6] << 12)
        )
        
        branch_next = Signal(32)
        
        m.d.comb += branch_next.eq(
            program_counter +
            branch_offset - 4
        )
        
        branch_en = Signal()
        
        with m.If(branch_en):
            m.d.sync += program_counter.eq(branch_next)
        
        # This is for debugging information
        opcode = Signal(Instruction)
        m.d.comb += opcode.eq(instruction.op)
        
        with m.FSM() as fsm:
            with m.State("Run"):
                # Read program when active
                m.d.comb += self.prog.cyc.eq(enable)
                m.d.comb += self.prog.stb.eq(enable)
                
                # Instruction is ready
                with m.If(self.prog.cyc & self.prog.stb & self.prog.ack):
                    m.d.sync += instruction_cache.eq(self.prog.r_data)
                    m.d.sync += program_counter.eq(program_counter + 4)
                    with m.Switch(opcode):
                        with m.Case(Instruction.LUI):
                            # Load upper immediate
                            m.d.sync += reg[instruction.u.rd].eq(
                                instruction.u.imm << 12
                            )
                        with m.Case(Instruction.AUIPC):
                            # Add upper immediate to pc
                            m.d.sync += reg[instruction.u.rd].eq(
                                program_counter +
                                (instruction.u.imm << 12)
                            )
                        with m.Case(Instruction.JAL):
                            # jump and link
                            m.d.sync += reg[instruction.j.rd].eq(
                                program_counter + 4
                            )
                            m.d.sync += program_counter.eq(
                                program_counter + jal_offset
                            )
                        with m.Case(Instruction.JALR):
                            # jump and link register
                            m.d.sync += reg[instruction.i.rd].eq(
                                program_counter + 4
                            )
                            m.d.sync += program_counter.eq(
                                (reg[instruction.i.rs] +
                                instruction.i.imm.as_signed())
                                & ~1
                            )
                        with m.Case(Instruction.ARITHIMM):
                            # take a clock cycle to do math
                            m.next = "ArithImm"
                        with m.Case(Instruction.ARITH):
                            m.next = "Arith"
                        with m.Case(Instruction.MEMORYSTORE):
                            m.next = "MemoryStore"
                        with m.Case(Instruction.MEMORYLOAD):
                            m.next = "MemoryLoad"
                        with m.Case(Instruction.BRANCH):
                            m.next = "Branch"
                        with m.Default():
                            m.d.sync += Print("Op code not implemented", instruction.op)
            with m.State("Branch"):
                with m.Switch(instruction.b.f):
                    with m.Case(0b000):
                        # Branch if Equal
                        m.d.comb += branch_en.eq(
                            reg[instruction.b.rs1] == reg[instruction.b.rs2]
                        )
                    with m.Case(0b001):
                        # Branch if not equal
                        m.d.comb += branch_en.eq(
                            reg[instruction.b.rs1] != reg[instruction.b.rs2]
                        )
                    with m.Case(0b100):
                        # Branch less than
                        m.d.comb += branch_en.eq(
                            reg[instruction.b.rs1] < reg[instruction.b.rs2]
                        )
                    with m.Case(0b101):
                        # Branch greater than or equal
                        m.d.comb += branch_en.eq(
                            reg[instruction.b.rs1] >= reg[instruction.b.rs2]
                        )
                    with m.Case(0b110):
                        # Branch less than unsigned
                        m.d.comb += branch_en.eq(
                            reg[instruction.b.rs1].as_unsigned() <
                            reg[instruction.b.rs2].as_unsigned()
                        )
                    with m.Case(0b111):
                        # Branch less than signed
                        m.d.comb += branch_en.eq(
                            reg[instruction.b.rs1].as_unsigned() >=
                            reg[instruction.b.rs2].as_unsigned()
                        )
                m.next = "Run"
            with m.State("MemoryLoad"):
                # Load value from memory
                offset = instruction.i.imm
                m.d.sync += mem_address.eq(reg[instruction.i.rs] + offset.as_signed())
                m.d.sync += reg[instruction.i.rd].eq(0)
                with m.Switch(instruction.i.f):
                    with m.Case(0b000):
                        # Load byte
                        m.d.sync += mem_counter.eq(0)
                    with m.Case(0b001):
                        # Load half word
                        m.d.sync += mem_counter.eq(1)
                    with m.Case(0b010):
                        # Load word
                        m.d.sync += mem_counter.eq(2)
            with m.State("MemoryLoadBus"):
                # Run n bus transactions to load data
                m.d.comb += self.bus.cyc.eq(1)
                m.d.comb += self.bus.stb.eq(1)
                m.d.comb += self.bus.addr.eq(mem_address)
                with m.If(self.bus.ack):
                    # Read ready
                    # Shift in data
                    m.d.sync += reg[instruction.i.rd].eq(
                                            (reg[instruction.i.rd] << 8) +
                                            self.bus.r_data)
                    with m.If(mem_counter == 0):
                        m.next = "Run"
                    with m.Else():
                        m.d.sync += mem_counter.eq(mem_counter - 1)
            with m.State("MemoryStore"):
                offset = instruction.s.imm_lower + (instruction.s.imm_upper << 5)
                m.d.sync += mem_address.eq(reg[instruction.s.rs1] + offset.as_signed())
                with m.Switch(instruction.s.f):
                    with m.Case(0b000):
                        # Store byte
                        m.d.sync += mem_register.eq(reg[instruction.s.rs2][0:8])
                        m.d.sync += mem_counter.eq(0)
                    with m.Case(0b001):
                        # Store 2 bytes
                        m.d.sync += mem_register.eq(reg[instruction.s.rs2][0:16])
                        m.d.sync += mem_counter.eq(1)
                    with m.Case(0b010):
                        # Store word
                        m.d.sync += mem_register.eq(reg[instruction.s.rs2][0:32])
                        m.d.sync += mem_counter.eq(3)
                m.next = "MemoryStoreBus"
            with m.State("MemoryStoreBus"):
                # Shift out bytes of data
                # Alternatively could add a flag for width of data
                m.d.comb += self.bus.cyc.eq(1)
                m.d.comb += self.bus.stb.eq(1)
                m.d.comb += self.bus.w_en.eq(1)
                
                m.d.comb += self.bus.addr.eq(mem_address)
                m.d.comb += self.bus.w_data.eq(mem_register[0:8])
                
                with m.If(self.bus.ack):
                    with m.If(mem_counter == 0):
                        # Finished writing bytes to memory
                        m.next = "Run"
                    with m.Else():
                        m.d.sync += mem_register.eq(mem_register >> 8)
                        m.d.sync += mem_counter.eq(mem_counter - 1)
                        m.d.sync += mem_address.eq(mem_address + 1)
            with m.State("Arith"):
                with m.Switch(instruction.r.f_lower):
                    with m.Case(0b000):
                        with m.If(instruction.r.f_upper == 0b0000000):
                            # Add
                            m.d.sync += reg[instruction.r.rd].eq(
                                reg[instruction.r.rs1] +
                                reg[instruction.r.rs2]
                            )
                        with m.Elif(instruction.r.f_upper == 0b0100000):
                            # Subtract
                            m.d.sync += reg[instruction.r.rd].eq(
                                reg[instruction.r.rs1] -
                                reg[instruction.r.rs2]
                            )
                        with m.Else():
                            m.d.sync += Assert(0, "Function not implemented")
                    with m.Case(0b001):
                        with m.If(instruction.r.f_upper == 0b0000000):
                            # Shift left
                            # TODO not quite right,
                            # if rs2 is above a value, it's 0,
                            # otherwise actually shift
                            with m.If(reg[instruction.r.rs2] > 5):
                                m.d.sync += reg[instruction.r.rd].eq(0)
                            with m.Else():
                                m.d.sync += reg[instruction.r.rd].eq(
                                    reg[instruction.r.rs1] <<
                                    reg[instruction.r.rs2].as_unsigned()[0:3]
                                )
                        with m.Else():
                            m.d.sync += Assert(0, "Function not implemented")
                    with m.Case(0b010):
                        with m.If(instruction.r.f_upper == 0b0000000):
                            # Less than
                            m.d.sync += reg[instruction.r.rd].eq(
                                reg[instruction.r.rs1] <
                                reg[instruction.r.rs2]
                            )
                    with m.Case(0b011):
                        with m.If(instruction.r.f_upper == 0b0000000):
                            # Unsigned less than
                            m.d.sync += reg[instruction.r.rd].eq(
                                reg[instruction.r.rs1].as_unsigned() <
                                reg[instruction.r.rs2].as_unsigned()
                            )
                    with m.Case(0b100):
                        with m.If(instruction.r.f_upper == 0b000000):
                            m.d.sync += reg[instruction.r.rd].eq(
                                reg[instruction.r.rs1] ^
                                reg[instruction.r.rs2]
                            )
                    with m.Case(0b101):
                        with m.If(instruction.r.f_upper == 0b00000_00):
                            # Logical shift right
                            m.d.sync += reg[instruction.r.rd].eq(
                                reg[instruction.r.rs1] >>
                                reg[instruction.r.rs2].as_unsigned()
                            )
                        with m.Elif(instruction.r.f_upper == 0b01000_00):
                            # Arithmetic shift right
                            m.d.sync += reg[instruction.r.rd][0:31].eq(
                                reg[instruction.r.rs1] >>
                                reg[instruction.r.rs2].as_unsigned()
                            )
                            m.d.sync += reg[instruction.r.rd][-1].eq(
                                reg[instruction.r.rs1][-1]
                            )
                    with m.Case(0b110):
                        # OR
                        with m.If(instruction.r.f_upper == 0b00000_00):
                            m.d.sync += reg[instruction.r.rd].eq(
                                reg[instruction.r.rs1] |
                                reg[instruction.r.rs2]
                            )
                    with m.Case(0b111):
                        # AND
                        with m.If(instruction.r.f_upper == 0b00000_00):
                            m.d.sync += reg[instruction.r.rd].eq(
                                reg[instruction.r.rs1] &
                                reg[instruction.r.rs2]
                            )
            with m.State("ArithImm"):
                with m.Switch(instruction.i.f):
                    with m.Case(0b000): # ADDI
                        # Add immediate
                        m.d.sync += reg[instruction.i.rd].eq(
                            reg[instruction.i.rs] +
                            instruction.i.imm
                        )
                    with m.Case(0b010): #SLTI
                        # Set less than immeddiate
                        m.d.sync += reg[instruction.i.rd].eq(
                            reg[instruction.i.rs] <
                            instruction.i.imm
                        )
                    with m.Case(0b011): # SLTIU
                        # Set less than immediate unsigned
                        m.d.sync += reg[instruction.i.rd].eq(
                            reg[instruction.i.rs].as_unsigned() <
                            instruction.i.imm.as_unsigned()
                        )
                    with m.Case(0b100): # XORI
                        # bitwise xori
                        m.d.sync += reg[instruction.i.rd].eq(
                            reg[instruction.i.rs] ^
                            instruction.i.imm
                        )
                    with m.Case(0b111): # ANDI
                        # And immediate
                        m.d.sync += reg[instruction.i.rd].eq(
                            reg[instruction.i.rs] &
                            instruction.i.imm
                        )
                    with m.Case(0b001): # SLLI
                        # Shift left
                        m.d.sync += reg[instruction.i.rd].eq(
                            reg[instruction.i.rs] <<
                            instruction.i.imm[0:5].as_unsigned()
                        )
                    with m.Case(0b101): # SRLI
                        with m.If(instruction.as_value()[27:] == 0b00000):
                            # Shift right logical
                            m.d.sync += reg[instruction.i.rd].eq(
                                reg[instruction.i.rs] >>
                                instruction.i.imm[0:5].as_unsigned()
                            )
                        with m.Elif(instruction.as_value()[27:] == 0b01000):
                            # Shift right arithmetic
                            m.d.sync += reg[instruction.i.rd][0:31].eq(
                                reg[instruction.i.rs] >>
                                instruction.i.imm[0:5].as_unsigned()
                            )
                            m.d.sync += reg[instruction.i.rd][-1].eq(
                                reg[instruction.i.rs][-1]
                            )
                        with m.Else():
                            m.d.sync += Assert(0, "Shift function not implemented")
                    with m.Default():
                        m.d.sync += Assert(0, "Function not implemented")
                m.next = "Run"
        
        # Don't assume that data is maintained except on successful
        # transaction
        with m.If(fsm.ongoing("Run")):
            m.d.comb += instruction.eq(self.prog.r_data)
        with m.Else():
            m.d.comb += instruction.eq(instruction_cache)
        
        self.debug = CoreDebug()
        
        self.debug.pc = program_counter
        self.debug.reg = reg
        self.instruction = instruction
        
        return m
    
#!/usr/bin/python3

# Author: David Basin
# Purpose of the program is to update a set of registers, including a pc, based
# on the given input machine code

from collections import namedtuple
import re
import argparse

Constants = namedtuple("Constants",["NUM_REGS", "MEM_SIZE", "REG_SIZE"])
constants = Constants(NUM_REGS = 8, 
                      MEM_SIZE = 2**15,
                      REG_SIZE = 2**16)

# The load_machine_code features code given by Professor Epstein in his starter code. It takes
# an E20 machine code file and loads it into the memory list, ignoring everything besides for
# the binary digits
def load_machine_code(machine_code, mem):
    machine_code_re = re.compile("^ram\[(\d+)\] = 16'b(\d+);.*$")
    expectedaddr = 0
    for line in machine_code:
        match = machine_code_re.match(line)
        if not match:
            raise Exception("Can't parse line: %s" % line)
        addr, instr = match.groups()
        addr = int(addr,10)
        instr = int(instr,2)
        if addr != expectedaddr:
            raise Exception("Memory addresses encountered out of sequence: %s" % addr)
        expectedaddr += 1
        mem[addr] = instr

# The print_state function features code given by Professor Epstein in his starter code. It
# is used to describe the final state of the program after the program has hit a halt. It
# lists the current program counter value, the values of the registers, and a certain number
# of memory elements in hex form
def print_state(pc, regs, memory, memquantity):
    print("Final state:")
    print("\tpc="+format(pc,"5d"))
    for reg, regval in enumerate(regs):
        print(("\t$%s=" % reg)+format(regval,"5d"))
    line = ""
    for count in range(memquantity):
        line += format(memory[count], "04x")+ " "
        if count % 8 == 7:
            print(line)
            line = ""
    if line != "":
        print(line)

# The threereg function deals with any machine code starting with "000" and thus instructions
# that deal with three registers. It returns the location that the pc will be at next
def threereg(pc, regs, instr):
    dstIndex = int(instr[9:12],2)
    srcA_Index = int(instr[3:6],2)
    srcB_Index = int(instr[6:9],2)
    if instr[-4:] == "0000": #add
        regs[dstIndex] = (regs[srcA_Index] + regs[srcB_Index]) % 2**16
    elif instr[-4:] == "0001": #sub
        regs[dstIndex] = (regs[srcA_Index] - regs[srcB_Index]) % 2**16
    elif instr[-4:] == "0010": #and
        regs[dstIndex] = regs[srcA_Index] & regs[srcB_Index]
    elif instr[-4:] == "0011": #or
        regs[dstIndex] = regs[srcA_Index] | regs[srcB_Index]
    elif instr[-4:] == "0100": #slt
        if regs[srcA_Index] < regs[srcB_Index]: regs[dstIndex] = 1
        else: regs[dstIndex] = 0
    elif instr[-4:] == "1000": #jr
        # returns the value inside the register, because that's the value pc will take next
        return regs[srcA_Index]
    return pc+1

# The tworegImm function deals with machine code that features two registers and an imm
# value, specifically slti and addi. It returns the location that the pc will be at next. 
def tworegImm(pc, regs, instr):
    dstIndex = int(instr[6:9],2)
    srcIndex = int(instr[3:6],2)
    imm = int(instr[10:],2)
    # If the MSB of the immediate is a 1, the immediate is actually negative
    if instr[9] == "1":
        imm -= 64
    if instr[:3] == "001": #slti
        if regs[srcIndex] < (imm % 2**16): regs[dstIndex] = 1
        else: regs[dstIndex] = 0
    elif instr[:3] == "111": #addi or movi
        regs[dstIndex] = (regs[srcIndex] + imm) % 2**16
    return pc+1

# The mem function deals with machine code that features two registers and an imm
# value and deals with memory location (sw and lw). It then returns pc+1 as the next pc.
def memImm(pc, regs, memory, instr):
    addrIndex = int(instr[3:6],2)
    imm = int(instr[10:],2)
    if instr[9] == "1":
        imm -= 64
    if instr[:3] == "100": #lw
        dstIndex = int(instr[6:9],2)
        regs[dstIndex] = memory[(regs[addrIndex]+imm)]
    elif instr[:3] == "101": #sw
        srcIndex = int(instr[6:9],2)
        memory[(regs[addrIndex]+imm)] = regs[srcIndex]
    return pc+1

# The jeq function deals specifically with a jeq instruction. If it does jump, the function
# returns the immediate (pc+1+rel_imm), and pc+1 otherwise.
def jeq(pc, regs, instr):
    regA_Index = int(instr[3:6],2)
    regB_Index = int(instr[6:9],2)
    rel_imm = int(instr[10:],2)
    if instr[9] == "1":
        rel_imm -= 64
    if regs[regA_Index] == regs[regB_Index]:
        return pc+1+rel_imm
    else:
        return pc+1

# The j_or_jal function is called whenever there's a jump with a 13-bit immediate (thus,
# j or jal). If the pc is equal to the immediate, then we will set Halt to true in the
# return statement, indicating for the program to stop. The immediate value will be returned
# as the next pc location
def j_or_jal(pc, regs, instr):
    if instr[:3] == "011":
        regs[7] = pc+1
    imm = int(instr[3:],2)
    if pc == imm: return (imm,True)
    else: return (imm, False)
    

def main():
    # The main features some code given by Professor Epstein in his starter code
    parser = argparse.ArgumentParser(description='Simulate E20 machine')
    parser.add_argument('filename', help='The file containing machine code, typically with .bin suffix')
    cmdline = parser.parse_args()

    # initialize system
    pc = 0
    regs = [0] * constants.NUM_REGS
    memory = [0] * constants.MEM_SIZE

    # load program into memory
    with open(cmdline.filename) as file:
        load_machine_code(file.readlines(), memory)
        
    # set halt to False to indicate the program shouldn't stop
    halt = False;
    # while the program isn't halted, we turn the instruction in the memory to a
    # 16-bit string, and check the first 3 or 2 characters in order to determine
    # which instruction function should be called
    while not halt:
        instr = bin(memory[pc])[2:].zfill(16)
        if instr[:3] == "000": pc = threereg(pc,regs,instr)
        elif instr[:3] in {"001","111"}: pc = tworegImm(pc,regs,instr)
        elif instr[:2] == "10":
            pc = memImm(pc,regs,memory,instr)
        elif instr[:3] == "110": pc = jeq(pc,regs,instr)
        # If a jump is detected, we recheck whether the program should be halted or not
        elif instr[:2] == "01":
            result = j_or_jal(pc,regs,instr)
            if result[1]: halt = True
            else:
                pc = result[0]

    print_state(pc, regs, memory, 128)

if __name__ == "__main__":
    main()

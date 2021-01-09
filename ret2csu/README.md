# ELI5 ret2csu 

As far as my understanding goes, take it with a grain of salt

<div id="table-of-contents">
<h2>Table of Contents</h2>
<div id="text-table-of-contents">
<ul>
<li><a href="#sec-1">Who dis?</a></li>
<li><a href="#sec-2">When dis?</a></li>
<li><a href="#sec-3">Why dis?</a></li>
<li><a href="#sec-4">How even?</a></li>
<li><a href="#sec-5">But still.. how?</a></li>
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


***How does a C code actually start?***

A correctly compiled and linked C code with gcc shares some attached code since C code requires some support libraries such as the gcc runtime and libc in order to run.

By following the special symbol `_start` of a gcc properly compiled and linked binary image, 

ie: `objdump -d mybinary | grep -A15 "_start"` , one will notice some call to `_libc_start_main` preceding a hlt instruction.


***So how does control flow actually pass to our C code?***

Running the program stepi from GDB, then some Python script to produce a graph, a sequence of function calls can be order and summarized as the graph below:

![Function calls sequence][calls]


Cool, so what does `_libc_start_main` actually do? Ignoring some details, here's a list of things that it does for a statically linked program:

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
For example, the `_libc_csu_init` (which, as you can see above, is called before the user's main) calls into special code that's inserted by the linker. 
The same goes for `_libc_csu_fini` and finalization.
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
`_libc_csu_init` goes over this array and calls all functions listed in it.

Cool, now we have a better picture of how and from where control flow goes.

***So, since some extra code is attached, what would finding universal gadgets in this code result in?***

Obviously, universal ROP.

## But still.. how?<a id="sec-5" name="sec-5"></a>

***Where does these gadgets reside? What would they look like? How would one chain those? one asks.***




[whodis]: https://raw.githubusercontent.com/kaftejiman/pwn/main/ret2csu/whodis.jpeg 
[calls]: https://raw.githubusercontent.com/kaftejiman/pwn/main/ret2csu/call_seq.png
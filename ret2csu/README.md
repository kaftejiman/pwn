<div id="table-of-contents">
<h2>Table of Contents</h2>
<div id="text-table-of-contents">
<ul>
<li><a href="#sec-1">1. Who dis?</a></li>
<li><a href="#sec-2">2. When dis?</a></li>
<li><a href="#sec-3">3. Why dis?</a></li>
<li><a href="#sec-4">4. How even?</a></li>
<li><a href="#sec-5">5. But still.. how?</a></li>
</ul>
</div>
</div>

ELI5 ret2csu 
DISCLAIMER: as far as I understand, take it with a grain of salt

# Who dis?<a id="sec-1" name="sec-1"></a>

[meme confused black girl]
A Universal ROP specific to GNU/Linux that exists in every ELF executable linked against libc. (aka most of them)

# When dis?<a id="sec-2" name="sec-2"></a>

When in lack of sufficient gadgets to build your rop (aka lack of control over some register ie: when compiled code is tiny).

# Why dis?<a id="sec-3" name="sec-3"></a>

To have full control over a call.
To bypass some security measures (ie: ASLR) by leaking arbitrary executable memory resulting in a direct libc de-randomization.

# How even?<a id="sec-4" name="sec-4"></a>

If I am actually compiling an empty C code (ie: only return) where does those ret2csu gadgets come from?
To get a clearer picture one should try to understand the context. 

How does a program start?

A program binary image is probably created by the system linker ld which links against a set of provided objects.
By default, ld looks for a special symbol called \_start in one of the object files linked into the program, and sets the entry point to the address of that symbol.

How does a C code actually start?

A correctly compiled and linked C code with gcc shares some attached code since C code requires some support libraries such as the gcc runtime and libc in order to run.
By following the special symbol \_start of a gcc properly compiled and linked binary image (ie: \`\`\`objdump -d mybinary | grep -A15 "<<sub>start</sub>"\`\`\` ), one will notice some call to \_<sub>libc</sub><sub>start</sub><sub>main</sub> preceding a hlt instruction.
So how does control flow actually pass to our C code?

Running the program stepi from GDB, then some Python script to produce a graph, a sequence of function calls can be summarized as below:

[call graph]

Cool, so what does \_<sub>libc</sub><sub>start</sub><sub>main</sub> actually do? Ignoring some details, here's a list of things that it does for a statically linked program:

1- Figure out where environment variables are on the stack.
2- Prepare the auxiliary vector, if required.
3- Initialize thread-specific functionality (ie: pthreads)
4- Perform some security-related book-keeping.
5- Initialize libc itself.
6- Call the program initialization function through the passed pointer (init).
7- Register the program finalization function (fini) for execution on exit.
8- Call main(argc, argv, envp)
9- Call exit with the result of main as the exit code.

Some programming environments require running custom code before and after main.
This is implemented by means of cooperation between the compiler/linker and the C library.
For example, the \_<sub>libc</sub><sub>csu</sub><sub>init</sub> (which, as you can see above, is called before the user's main) calls into special code that's inserted by the linker. 
The same goes for \_<sub>libc</sub><sub>csu</sub><sub>fini</sub> and finalization.

You can also ask the compiler to register your function to be executed as one of the constructors or destructors. For example:

\`\`\`
\\#include <stdio.h>

int main() {
    printf("actual main");
    return 0;
}

\_<sub>attribute</sub>\_<sub>((constructor))</sub>
void myconstructor() {
    printf("this will run before main\n");
}
\`\`\`

myconstructor will run before main. The linker places its address in a special array of constructors located in the .ctors section. \_<sub>libc</sub><sub>csu</sub><sub>init</sub> goes over this array and calls all functions listed in it.

Cool, now we have a better picture of how and from where control flow goes.

So, since some extra code is attached, what would finding universal gadgets in this code result in?

Obviously, universal ROP.

# But still.. how?<a id="sec-5" name="sec-5"></a>

Where does these gadgets reside? What would they look like? How would one chain those? one asks

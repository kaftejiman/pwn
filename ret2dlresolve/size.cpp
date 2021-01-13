#include <iostream>
#include "llvm/BinaryFormat/ELF.h"

using namespace std;

int main(){

    cout << sizeof(llvm::ELF::Elf32_Rel) << endl;
    return 0;
}
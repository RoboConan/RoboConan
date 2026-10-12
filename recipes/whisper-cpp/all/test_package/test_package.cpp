#include <whisper.h>
#include <parakeet.h>
#include <cassert>
#include <cstring>
#include <iostream>

int main() {
    assert(std::strcmp(whisper_version(), "1.9.5") == 0);
    assert(std::strcmp(parakeet_version(), "1.9.5") == 0);
    std::cout << whisper_print_system_info() << std::endl;
    std::cout << parakeet_print_system_info() << std::endl;
}

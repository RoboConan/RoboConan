#include <dlfcn.h>

#include <iostream>

int main() {
    std::cout << "Loading UNO plugin" << std::endl;
    void* plugin = dlopen(TEST_PLUGIN_PATH, RTLD_NOW);
    if (plugin == nullptr) {
        std::cerr << dlerror() << std::endl;
        return 1;
    }
    auto test_uno_logger = reinterpret_cast<void (*)()>(dlsym(plugin, "test_uno_logger"));
    if (test_uno_logger == nullptr) {
        std::cerr << dlerror() << std::endl;
        return 1;
    }
    test_uno_logger();
    dlclose(plugin);
}

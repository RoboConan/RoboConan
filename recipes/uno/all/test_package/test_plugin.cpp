#include <uno/tools/Logger.hpp>

extern "C" void test_uno_logger() {
    uno::Logger::set_logger("INFO");
    uno::INFO << "UNO logger initialized from a loaded plugin" << std::endl;
}

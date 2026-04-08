// Workaround for a missing <limits> include in wilzegers-autotest/0.0+git.20200921
#include <limits>

#include <autotest/autotest.hpp>
#include <fstream>

int main() {
    AutoTest::Args::integralRange(1, 3);
    return 0;
}

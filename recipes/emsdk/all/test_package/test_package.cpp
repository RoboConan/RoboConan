#include <cstdlib>
#include <iostream>

extern "C" int test_package_answer(void);

int main()
{
    std::cout << "RoboConan " << test_package_answer() << '\n';
    return EXIT_SUCCESS;
}

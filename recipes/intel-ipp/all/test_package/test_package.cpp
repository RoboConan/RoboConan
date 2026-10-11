#include <iw++/iw.hpp>

#include <iostream>

int main() {
    ipp::IwVersion version;
    std::cout << "Intel IPP IW " << version.getString() << '\n';
    return 0;
}

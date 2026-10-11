#include <Corrade/Corrade.h>
#include <Corrade/version.h>

#ifdef WITH_UTILITY
  #include <Corrade/Utility/Debug.h>
#endif

#include <iostream>

int main() {
  std::cout << "Test package for Corrade\n";

  std::cout << "Corrade " << CORRADE_VERSION_YEAR << "." << CORRADE_VERSION_MONTH << std::endl;

  #ifdef WITH_UTILITY
    Corrade::Utility::Debug{} << "Success";
  #endif
}

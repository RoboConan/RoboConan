#include <fatrop/fatrop.hpp>
#ifdef TEST_FATROP_C_INTERFACE
#include <fatrop/ocp/OCPCInterface.h>
#endif

int main() {
    fatrop::OptionRegistry options;
#ifdef TEST_FATROP_C_INTERFACE
    (void)fatrop_ocp_c_option_type("tol");
#endif
}

#ifdef TEST_MADNLP_LEGACY
#include <madnlp_c.h>
#else
#include <libMad.h>
#endif

int main() {
#ifdef TEST_MADNLP_LEGACY
    shutdown_julia(0);
#else
    OptsDict* options = nullptr;
    libmad_create_options_dict(&options);
    libmad_delete_options_dict(options);
#endif
}

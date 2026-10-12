#include <libMad.h>

static int (*volatile create_options)(OptsDict**) = libmad_create_options_dict;

int main(void) {
    (void)create_options;
}

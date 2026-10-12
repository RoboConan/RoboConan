#include <stdio.h>

#define QOI_IMPLEMENTATION
#include "qoi.h"

int main(void) {
    printf("qoi_desc size: %zu\n", sizeof(qoi_desc));

    return EXIT_SUCCESS;
}

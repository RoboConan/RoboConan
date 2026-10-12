#include <lacemodelica/lacemodelica.h>

int main(void) {
    (void)lacemodelica_status_string(LACEMODELICA_SUCCESS);
    return lacemodelica_parse_bmo(TEST_BMO_PATH) == LACEMODELICA_SUCCESS ? 0 : 1;
}

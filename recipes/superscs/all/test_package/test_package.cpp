#include <superscs/scs.h>
#include <stdarg.h>
#include <stdio.h>

#ifdef SCS_CASADI
extern "C" int casadi_printf(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    int result = vprintf(fmt, args);
    va_end(args);
    return result;
}
#endif

int main() {
    ScsSolution *sol = scs_init_sol();
    printf("SuperSCS version: %s\n", SCS_VERSION);
}

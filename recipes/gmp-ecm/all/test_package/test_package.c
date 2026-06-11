#include <gmp.h>
#include <ecm.h>

int main(void)
{
    mpz_t n, f;
    int res;
    ecm_params params;

    mpz_init(n);
    mpz_init(f);
    /* a small composite to factor */
    mpz_set_str(n, "1234567890123456789012345678901", 10);

    ecm_init(params);
    res = ecm_factor(f, n, 100.0, params);
    ecm_clear(params);

    mpz_clear(n);
    mpz_clear(f);
}

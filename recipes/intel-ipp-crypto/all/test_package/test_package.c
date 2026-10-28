#include <ippcp.h>

#ifdef WITH_CRYPTO_MB
#include <crypto_mb/rsa.h>
#include <crypto_mb/version.h>
#endif

int main(void) {
    (void)cryptoGetLibVersion();
#ifdef WITH_CRYPTO_MB
    (void)mbx_getversion();
#endif
}

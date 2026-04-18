#include <monocypher.h>
#include <stdio.h>

int main() {
    uint8_t key[32] = {0};
    uint8_t pub[32];
    crypto_x25519_public_key(pub, key);
    printf("Monocypher x25519 public key: ");
    for (int i = 0; i < 8; i++)
        printf("%02x", pub[i]);
    printf("...\n");
}

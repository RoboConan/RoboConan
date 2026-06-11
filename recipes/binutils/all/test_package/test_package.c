#define PACKAGE
#include <bfd.h>
#include <stdio.h>

int main() {
    printf("bfd_plugin_enabled: %d\n", bfd_plugin_enabled());
}

#include <nauty/nauty.h>
#include <stdio.h>

int main() {
    printf("nauty version: %s\n", NAUTYVERSION);
    nauty_freedyn();
}

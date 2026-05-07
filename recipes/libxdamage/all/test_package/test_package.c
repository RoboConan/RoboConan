#include <X11/extensions/Xdamage.h>

#include <stddef.h>

void dummy() {
    XDamageCreate(NULL, 0, 0);
}

int main() {
}

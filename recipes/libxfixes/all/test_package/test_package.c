#include <X11/extensions/Xfixes.h>

#include <stddef.h>

void dummy() {
    XFixesGetCursorName(NULL, 0, NULL);
}

int main() {
}

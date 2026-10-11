#include <dxc/dxcapi.h>

int main() {
    auto* volatile create_instance = &DxcCreateInstance;
    (void)create_instance;
}

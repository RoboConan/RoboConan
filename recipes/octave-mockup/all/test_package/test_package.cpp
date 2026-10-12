#include <mex.h>

int main() {
    mexLock();
    mxIsClass(nullptr, "double");
    mxIsInt8(nullptr);
    mxIsUint8(nullptr);
    mexMakeArrayPersistent(nullptr);
}

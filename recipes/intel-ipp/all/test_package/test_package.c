#include <ipp.h>
#include <iw.h>

#include <stdio.h>

int main(void) {
    const IppLibraryVersion *ipp = ippGetLibVersion();
    IwVersion iw;
    iwGetLibVersion(&iw);
    printf("Intel IPP %s, IPP IW %s\n", ipp->Version, iw.m_versionStr);
    return 0;
}

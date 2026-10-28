#include <ipp.h>
#include <ippcore_tl.h>
#include <iw.h>

#include <stdio.h>

int main(void) {
    const IppLibraryVersion *ipp = ippGetLibVersion();
    IwVersion iw;
    IppThreadingType threading;
    iwGetLibVersion(&iw);
    ippGetThreadingType_LT(&threading);
    printf("Intel IPP %s, IPP IW %s\n", ipp->Version, iw.m_versionStr);
    return 0;
}

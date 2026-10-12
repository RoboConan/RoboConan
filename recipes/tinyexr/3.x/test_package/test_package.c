#include <stdio.h>

#include <exr.h>

int main(void)
{
    printf("TinyEXR %d.%d.%d: %s\n",
           EXR_VERSION_MAJOR, EXR_VERSION_MINOR, EXR_VERSION_PATCH,
           exr_result_string(EXR_SUCCESS));
    return 0;
}

#include <stdio.h>
#include "jpeglib.h"
#ifdef WITH_TURBOJPEG
#include "turbojpeg.h"
#endif

int main() {
    struct jpeg_decompress_struct info;
    struct jpeg_error_mgr err;
    info.err = jpeg_std_error(&err);
    jpeg_create_decompress(&info);
    jpeg_destroy_decompress(&info);
#ifdef WITH_TURBOJPEG
    tjhandle tj = tjInitDecompress();
    if (!tj)
        return 1;
    tjDestroy(tj);
#endif
}

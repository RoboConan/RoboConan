#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_ERRORS_H
#include FT_CONFIG_OPTIONS_H
#include <stdio.h>

int main() {
    FT_Library library;
    int major, minor, patch;
    FT_Init_FreeType(&library);
    FT_Library_Version(library, &major, &minor, &patch);
    printf("Freetype library version: %d.%d.%d\n", major, minor, patch);
#ifdef FT_CONFIG_OPTION_ERROR_STRINGS
    const char *error_string = FT_Error_String(FT_Err_Cannot_Open_Resource);
    if (!error_string) {
        return 1;
    }
    printf("Freetype error string: %s\n", error_string);
#endif
    FT_Done_FreeType(library);
}

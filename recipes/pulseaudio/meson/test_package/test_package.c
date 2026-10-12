#include <stdio.h>
#include <pulse/pulseaudio.h>
#include <pulse/simple.h>
#ifdef TEST_PULSE_GLIB
#include <pulse/glib-mainloop.h>
#endif

int main()
{
    void (*simple_free)(pa_simple *) = pa_simple_free;
#ifdef TEST_PULSE_GLIB
    void (*glib_free)(pa_glib_mainloop *) = pa_glib_mainloop_free;
    (void)glib_free;
#endif
    (void)simple_free;
    printf("pulse audio verions %s\n", pa_get_library_version());
    return 0;
}

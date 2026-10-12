#include <stddef.h>

#include <alsa/topology.h>

#include <stdlib.h>

int main(void)
{
    snd_tplg_t *topology = snd_tplg_new();
    if (topology == NULL)
        return EXIT_FAILURE;
    snd_tplg_free(topology);
    return EXIT_SUCCESS;
}

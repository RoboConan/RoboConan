#include <vkd3d_shader.h>
#include <vkd3d_utils.h>

int main()
{
    PFN_vkd3d_create_instance volatile create_instance = vkd3d_create_instance;
    const char *(*volatile get_shader_version)(unsigned int *, unsigned int *) = vkd3d_shader_get_version;
    HRESULT (WINAPI *volatile create_blob)(SIZE_T, ID3DBlob **) = D3DCreateBlob;
    (void)create_instance;
    (void)get_shader_version;
    (void)create_blob;
}

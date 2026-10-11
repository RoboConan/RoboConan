#include <wsl/winadapter.h>
#include <directx/d3dx12.h>
#include <dxguids/dxguids.h>

int main()
{
    InlineIsEqualGUID(GUID{}, GUID{});
#ifdef __D3D12_PROPERTY_LAYOUT_FORMAT_TABLE_H__
    D3D12_PROPERTY_LAYOUT_FORMAT_TABLE::GetNumFormats();
#endif
}

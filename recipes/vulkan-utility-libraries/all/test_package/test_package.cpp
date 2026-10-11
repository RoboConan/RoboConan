#include <vulkan/layer/vk_layer_settings.hpp>
#include <vulkan/utility/vk_safe_struct.hpp>
#include <vulkan/utility/vk_struct_helper.hpp>

int main() {
    VkuLayerSettingSet layerSettingSet = VK_NULL_HANDLE;
    vkuCreateLayerSettingSet("VK_LAYER_LUNARG_conan", nullptr, nullptr, nullptr, &layerSettingSet);
    vku::safe_VkApplicationInfo applicationInfo;
    auto instanceCreateInfo = vku::InitStruct<VkInstanceCreateInfo>();
}

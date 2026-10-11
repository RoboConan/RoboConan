#include <vulkan/vulkan_profiles.hpp>

int main()
{
#ifdef VULKAN_PROFILES_NEW_API
    uint32_t profileCount = 0;
    vpGetProfiles(&profileCount, nullptr);
#else
    VpCapabilities capabilities = VK_NULL_HANDLE;
    VpCapabilitiesCreateInfo createInfo;
    createInfo.apiVersion = VK_API_VERSION_1_1;
    createInfo.flags = VP_PROFILE_CREATE_STATIC_BIT;
    createInfo.pVulkanFunctions = nullptr;
    vpCreateCapabilities(&createInfo, nullptr, &capabilities);
#endif
}

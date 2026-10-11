#include <cstdlib>
#include <iostream>

#define NS_PRIVATE_IMPLEMENTATION
#define CA_PRIVATE_IMPLEMENTATION
#define MTL_PRIVATE_IMPLEMENTATION

#include <Foundation/Foundation.hpp>
#include <Metal/Metal.hpp>
#include <QuartzCore/QuartzCore.hpp>

#if __has_include(<MetalFX/MetalFX.hpp>)
#define MTLFX_PRIVATE_IMPLEMENTATION
#include <MetalFX/MetalFX.hpp>
#endif


int main()
{
    NS::AutoreleasePool* autoreleasePool = NS::AutoreleasePool::alloc()->init();
    MTL::Device* metalDevice = MTL::CreateSystemDefaultDevice();
    if (metalDevice == nullptr)
    {
        std::cerr << "No Metal device available" << std::endl;
        autoreleasePool->release();
        return EXIT_FAILURE;
    }

    std::cout << "Metal device detected: " << metalDevice->name()->cString(NS::ASCIIStringEncoding) << std::endl;

    metalDevice->release();
    autoreleasePool->release();
    return EXIT_SUCCESS;
}

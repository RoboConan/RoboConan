#include <DiligentCore/Common/interface/RefCntAutoPtr.hpp>
#include <DiligentCore/Graphics/GraphicsEngine/interface/PipelineState.h>
#include <DiligentCore/Graphics/GraphicsEngine/interface/SwapChain.h>
#include <DiligentCore/Graphics/GraphicsEngine/interface/DeviceContext.h>
#include <DiligentCore/Graphics/GraphicsEngine/interface/RenderDevice.h>

#include <DiligentTools/AssetLoader/interface/GLTFLoader.hpp>

#include <DiligentFX/Components/interface/ShadowMapManager.hpp>

#include <imgui.h>
#include <ImGuizmo.h>

#include <iostream>


int main()
{

#ifdef PLATFORM_WIN32
  std::cout << "PLATFORM_WIN32: " << PLATFORM_WIN32;
#endif

#ifdef PLATFORM_MACOS
  std::cout << "PLATFORM_MACOS: " << PLATFORM_MACOS;
#endif

#ifdef PLATFORM_LINUX
  std::cout << "PLATFORM_LINUX: " << PLATFORM_LINUX;
#endif

#ifdef PLATFORM_ANDROID
  std::cout << "PLATFORM_ANDROID: " << PLATFORM_ANDROID;
#endif

#ifdef PLATFORM_IOS
  std::cout << "PLATFORM_IOS: " << PLATFORM_IOS;
#endif

#ifdef PLATFORM_EMSCRIPTEN
  std::cout << "PLATFORM_EMSCRIPTEN: " << PLATFORM_EMSCRIPTEN;
#endif

#ifdef PLATFORM_TVOS
  std::cout << "PLATFORM_TVOS: " << PLATFORM_TVOS;
#endif

  Diligent::RefCntAutoPtr<Diligent::IRenderDevice>  _pDevice;
  Diligent::RefCntAutoPtr<Diligent::IDeviceContext> _pImmediateContext;
  Diligent::RefCntAutoPtr<Diligent::ISwapChain>     _pSwapChain;

  Diligent::GLTF::Material material;

  Diligent::ShadowMapManager manager;

  // DiligentTools publicly exposes its external ImGuizmo replacement.
  ImGuizmo::SetRect(0.f, 0.f, 1.f, 1.f);
}

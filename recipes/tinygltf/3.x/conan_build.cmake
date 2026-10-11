if(TINYGLTF3_BUILD_LIBRARY)
    add_library(tinygltf tiny_gltf_v3.c)
    target_include_directories(tinygltf PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
    if(WIN32 AND BUILD_SHARED_LIBS)
        target_compile_definitions(tinygltf PRIVATE "TINYGLTF3_API=__declspec(dllexport)")
    endif()
    if(TINYGLTF3_ENABLE_FS)
        target_compile_definitions(tinygltf PRIVATE TINYGLTF3_ENABLE_FS)
    endif()
    install(TARGETS tinygltf)
endif()

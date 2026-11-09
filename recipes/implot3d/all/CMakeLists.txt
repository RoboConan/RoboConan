cmake_minimum_required(VERSION 3.15)
project(implot3d LANGUAGES CXX)

find_package(imgui CONFIG REQUIRED)

add_library(implot3d
    implot3d.cpp
    implot3d_items.cpp
)
if(IMPLOT3D_BUILD_DEMO)
    target_sources(implot3d PRIVATE implot3d_demo.cpp)
endif()
if(IMPLOT3D_BUILD_MESHES)
    target_sources(implot3d PRIVATE implot3d_meshes.cpp)
endif()
target_include_directories(implot3d
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR}
)
target_link_libraries(implot3d PUBLIC imgui::imgui)
target_compile_features(implot3d PUBLIC cxx_std_11)
set_target_properties(implot3d PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

include(GenerateExportHeader)
generate_export_header(implot3d
    EXPORT_MACRO_NAME IMPLOT3D_API
    DEPRECATED_MACRO_NAME IMPLOT3D_EXPORT_DEPRECATED
    EXPORT_FILE_NAME implot3d_export.h
)

include(GNUInstallDirs)
install(TARGETS implot3d)
install(FILES
    implot3d.h
    implot3d_internal.h
    ${CMAKE_CURRENT_BINARY_DIR}/implot3d_export.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

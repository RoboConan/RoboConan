cmake_minimum_required(VERSION 3.15)
project(imgui-godot LANGUAGES CXX)

find_package(godot-cpp REQUIRED CONFIG)
find_package(imgui REQUIRED CONFIG)

add_library(imgui-godot-native SHARED
    gdext/src/CanvasRenderer.cpp
    gdext/src/Context.cpp
    gdext/src/Fonts.cpp
    gdext/src/GdsCache.cpp
    gdext/src/ImGuiController.cpp
    gdext/src/ImGuiControllerHelper.cpp
    gdext/src/ImGuiGD.cpp
    gdext/src/ImGuiLayer.cpp
    gdext/src/ImGuiSync.cpp
    gdext/src/Input.cpp
    gdext/src/InputLocal.cpp
    gdext/src/main.cpp
    gdext/src/RdRenderer.cpp
    gdext/src/RdRendererThreadSafe.cpp
    gdext/src/Viewports.cpp
)

if(IMGUI_GODOT_GDSCRIPT_BINDINGS)
    target_sources(imgui-godot-native PRIVATE
        gdext/src/ImGuiAPI.cpp
        ${IMGUI_GODOT_BINDINGS_DIR}/cimgui.cpp
    )
else()
    target_sources(imgui-godot-native PRIVATE gdscript_stubs.cpp)
endif()

target_compile_features(imgui-godot-native PRIVATE cxx_std_20)
target_compile_definitions(imgui-godot-native PRIVATE
    IMGUI_USER_CONFIG="imconfig-godot.h"
    IGN_EXPORT
)
target_include_directories(imgui-godot-native PRIVATE
    gdext/src
    gdext/include
)
if(IMGUI_GODOT_GDSCRIPT_BINDINGS)
    target_include_directories(imgui-godot-native PRIVATE ${IMGUI_GODOT_BINDINGS_DIR})
endif()
target_link_libraries(imgui-godot-native PUBLIC
    godot-cpp::godot-cpp
    imgui::imgui
)
if(CMAKE_DL_LIBS)
    target_link_libraries(imgui-godot-native PRIVATE ${CMAKE_DL_LIBS})
endif()

set_target_properties(imgui-godot-native PROPERTIES
    OUTPUT_NAME "${IMGUI_GODOT_LIBRARY_NAME}"
    WINDOWS_EXPORT_ALL_SYMBOLS OFF
)

include(GNUInstallDirs)
install(TARGETS imgui-godot-native
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${IMGUI_GODOT_ADDON_DIR}/bin
    RUNTIME DESTINATION ${IMGUI_GODOT_ADDON_DIR}/bin
)
install(DIRECTORY addons/imgui-godot/scripts
    DESTINATION ${IMGUI_GODOT_ADDON_DIR}
    FILES_MATCHING PATTERN "*.gd"
)
install(DIRECTORY addons/imgui-godot/data
    DESTINATION ${IMGUI_GODOT_ADDON_DIR}
)
install(FILES addons/imgui-godot/plugin.cfg
    DESTINATION ${IMGUI_GODOT_ADDON_DIR}
)
install(DIRECTORY gdext/include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/imgui-godot
    FILES_MATCHING PATTERN "*.h"
)

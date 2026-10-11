cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

set(_magnum_components Trade)
if(WITH_MATERIAL_TOOLS)
    list(APPEND _magnum_components MaterialTools)
endif()
if(WITH_SCENE_TOOLS)
    list(APPEND _magnum_components SceneTools)
endif()
if(WITH_SHADER_TOOLS)
    list(APPEND _magnum_components ShaderTools)
endif()
if(NOT SHARED_PLUGINS)
    list(APPEND _magnum_components ObjImporter)
    # ObjImporter pulls in MeshTools. Magnum's installed config does not
    # recursively add MeshTools' conditional GL dependency.
    # https://github.com/mosra/magnum/blob/a816a15a4a8dd227734b66a529a8ccd3c26b570f/modules/FindMagnum.cmake#L483-L486
    # https://github.com/mosra/magnum/blob/a816a15a4a8dd227734b66a529a8ccd3c26b570f/modules/FindMagnum.cmake#L563-L607
    if(TARGET_GL)
        list(APPEND _magnum_components GL)
    endif()
endif()
foreach(_executable IN ITEMS
    gl-info
    al-info
    vk-info
    distancefieldconverter
    fontconverter
    imageconverter
    sceneconverter
    shaderconverter)
    string(REPLACE "-" "_" _executable_variable "${_executable}")
    string(TOUPPER "EXEC_${_executable_variable}" _executable_variable)
    if(${_executable_variable})
        list(APPEND _magnum_components ${_executable})
    endif()
endforeach()
find_package(Magnum REQUIRED COMPONENTS ${_magnum_components} CONFIG)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/configure.h.in
               ${CMAKE_CURRENT_BINARY_DIR}/configure.h)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE Magnum::Magnum Magnum::Trade)
if(WITH_MATERIAL_TOOLS)
    target_link_libraries(${PROJECT_NAME} PRIVATE Magnum::MaterialTools)
endif()
if(WITH_SCENE_TOOLS)
    target_link_libraries(${PROJECT_NAME} PRIVATE Magnum::SceneTools)
endif()
if(WITH_SHADER_TOOLS)
    target_link_libraries(${PROJECT_NAME} PRIVATE Magnum::ShaderTools)
endif()
target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
if(NOT SHARED_PLUGINS)
    target_link_libraries(${PROJECT_NAME} PRIVATE Magnum::ObjImporter)
endif()
set_target_properties(${PROJECT_NAME}
    PROPERTIES
        CXX_STANDARD 11
        CXX_STANDARD_REQUIRED ON
        CXX_EXTENSIONS OFF
)


# Run some executables (we can only be sure they exist if native build)
if (EXEC_GL_INFO AND NOT CMAKE_CROSSCOMPILING)
    add_custom_command(
        TARGET ${PROJECT_NAME} PRE_BUILD
        COMMAND Magnum::gl-info
        ARGS "--help"
        COMMENT "Running magnum-gl-info"
    )
endif()

if (EXEC_AL_INFO AND NOT CMAKE_CROSSCOMPILING)
    add_custom_command(
        TARGET ${PROJECT_NAME} PRE_BUILD
        COMMAND Magnum::al-info
        ARGS "--help"
        COMMENT "Running magnum-al-info"
    )
endif()

if (EXEC_DISTANCEFIELDCONVERTER AND NOT CMAKE_CROSSCOMPILING)
    add_custom_command(
        TARGET ${PROJECT_NAME} PRE_BUILD
        COMMAND Magnum::distancefieldconverter
        ARGS "--help"
        COMMENT "Running magnum-distancefieldconverter"
    )
endif()

if (EXEC_FONTCONVERTER AND NOT CMAKE_CROSSCOMPILING)
    add_custom_command(
        TARGET ${PROJECT_NAME} PRE_BUILD
        COMMAND Magnum::fontconverter
        ARGS "--help"
        COMMENT "Running magnum-fontconverter"
    )
endif()

if (EXEC_IMAGECONVERTER AND NOT CMAKE_CROSSCOMPILING)
    add_custom_command(
        TARGET ${PROJECT_NAME} PRE_BUILD
        COMMAND Magnum::imageconverter
        ARGS "--help"
        COMMENT "Running magnum-imageconverter"
    )
endif()

if (EXEC_SCENECONVERTER AND NOT CMAKE_CROSSCOMPILING)
    add_custom_command(
        TARGET ${PROJECT_NAME} PRE_BUILD
        COMMAND Magnum::sceneconverter
        ARGS "--help"
        COMMENT "Running magnum-sceneconverter"
    )
endif()

if (EXEC_VK_INFO AND NOT CMAKE_CROSSCOMPILING)
    add_custom_command(
        TARGET ${PROJECT_NAME} PRE_BUILD
        COMMAND Magnum::vk-info
        ARGS "--help"
        COMMENT "Running magnum-vk-info"
    )
endif()

if (EXEC_SHADERCONVERTER AND NOT CMAKE_CROSSCOMPILING)
    add_custom_command(
        TARGET ${PROJECT_NAME} PRE_BUILD
        COMMAND Magnum::shaderconverter
        ARGS "--help"
        COMMENT "Running magnum-shaderconverter"
    )
endif()

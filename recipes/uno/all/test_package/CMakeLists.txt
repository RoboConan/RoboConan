cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

find_package(uno REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE uno::uno)

add_executable(test_c_api test_c_api.c)
target_link_libraries(test_c_api PRIVATE uno::uno)
set_property(TARGET test_c_api PROPERTY LINKER_LANGUAGE CXX)

if(UNIX)
    add_library(test_plugin MODULE test_plugin.cpp)
    target_link_libraries(test_plugin PRIVATE uno::uno)

    add_executable(test_dlopen test_dlopen.cpp)
    target_link_libraries(test_dlopen PRIVATE ${CMAKE_DL_LIBS})
    target_compile_definitions(test_dlopen PRIVATE TEST_PLUGIN_PATH="$<TARGET_FILE:test_plugin>")
endif()

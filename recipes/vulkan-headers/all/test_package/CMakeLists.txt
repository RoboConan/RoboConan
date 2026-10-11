cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

find_package(VulkanHeaders REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} Vulkan::Headers)

if(TEST_VULKAN_HPP_MODULE)
    add_executable(${PROJECT_NAME}_module test_package.cpp)
    set_target_properties(${PROJECT_NAME}_module PROPERTIES CXX_SCAN_FOR_MODULES ON)
    target_link_libraries(${PROJECT_NAME}_module PRIVATE Vulkan::HppModule)
endif()

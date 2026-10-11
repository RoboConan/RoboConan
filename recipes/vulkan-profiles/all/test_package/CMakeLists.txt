cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(vulkan-profiles REQUIRED)
add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE vulkan-profiles::vulkan-profiles)

add_executable(check_vulkan_layers check_vulkan_layers.cpp)
target_link_libraries(check_vulkan_layers PRIVATE Vulkan::Loader)

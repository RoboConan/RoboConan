cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(CpuFeatures REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE CpuFeatures::cpu_features)

if(ANDROID)
    add_executable(test_ndk_compat test_ndk_compat.c)
    target_link_libraries(test_ndk_compat PRIVATE CpuFeatures::ndk_compat)
endif()

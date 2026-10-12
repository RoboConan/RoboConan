cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(OpenEXR REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE OpenEXR::OpenEXR)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)

add_executable(test_openexr_core test_openexr_core.cpp)
target_link_libraries(test_openexr_core PRIVATE OpenEXR::OpenEXRCore)
target_compile_features(test_openexr_core PRIVATE cxx_std_17)

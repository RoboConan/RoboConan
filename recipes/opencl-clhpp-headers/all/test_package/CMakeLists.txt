cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCLHeadersCpp REQUIRED CONFIG)
find_package(OpenCLICDLoader REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_compile_definitions(${PROJECT_NAME} PRIVATE
    CL_HPP_MINIMUM_OPENCL_VERSION=120
    CL_HPP_TARGET_OPENCL_VERSION=120
)
target_link_libraries(${PROJECT_NAME} PRIVATE OpenCL::HeadersCpp OpenCL::OpenCL)

if(OpenCLHeadersCpp_VERSION VERSION_GREATER 2020.06.16)
    target_compile_definitions(${PROJECT_NAME} PRIVATE USE_OPENCL_HPP)
endif()

if(OpenCLHeadersCpp_VERSION VERSION_GREATER_EQUAL 2026.05.29)
    add_executable(${PROJECT_NAME}_opencl31 test_package.cpp)
    target_compile_definitions(${PROJECT_NAME}_opencl31 PRIVATE
        CL_HPP_MINIMUM_OPENCL_VERSION=120
        CL_HPP_TARGET_OPENCL_VERSION=310
        USE_OPENCL_HPP
    )
    target_link_libraries(${PROJECT_NAME}_opencl31 PRIVATE OpenCL::HeadersCpp OpenCL::OpenCL)
endif()

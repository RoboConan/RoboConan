cmake_minimum_required(VERSION 3.15)
project(cmake_wrapper)

if(ENABLE_OPT)
    find_package(SPIRV-Tools REQUIRED CONFIG)
endif()

add_subdirectory(src)

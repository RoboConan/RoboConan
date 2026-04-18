cmake_minimum_required(VERSION 3.15)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE None)
endif()

project(test_package LANGUAGES C)

find_package(libopencm3 REQUIRED CONFIG)

add_library(${PROJECT_NAME} STATIC test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE libopencm3::libopencm3)

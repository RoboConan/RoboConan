cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

add_library(test_package_c test_package.c)
add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE test_package_c)

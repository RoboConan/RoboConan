cmake_minimum_required(VERSION 3.18)
project(test_package LANGUAGES Fortran)

add_library(test_library STATIC test_library.f90)
add_executable(test_package test_package.f90)
target_link_libraries(test_package PRIVATE test_library)

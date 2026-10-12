cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

find_package(ampl-asl REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE asl)

if(TARGET asl2-mt)
    add_executable(test_openmp_cxx test_openmp_cxx.cpp)
    target_link_libraries(test_openmp_cxx PRIVATE asl2-mt)
endif()

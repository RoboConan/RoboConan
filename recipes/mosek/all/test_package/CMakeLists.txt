cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

find_package(mosek REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE mosek64)

if(TEST_FUSION_CXX)
    add_executable(test_fusion test_fusion.cpp)
    target_link_libraries(test_fusion PRIVATE fusion64)
endif()

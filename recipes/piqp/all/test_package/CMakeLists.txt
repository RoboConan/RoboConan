cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

find_package(piqp REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE piqp::piqp)

if(TARGET piqp::piqp_c)
    add_executable(test_c_api test_c_api.c)
    target_link_libraries(test_c_api PRIVATE piqp::piqp_c)
endif()

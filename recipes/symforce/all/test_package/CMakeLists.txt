cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(symforce REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE symforce::symforce)
if(TARGET symforce::symforce_opt)
    target_compile_definitions(${PROJECT_NAME} PRIVATE HAVE_SYMFORCE_OPT)
endif()

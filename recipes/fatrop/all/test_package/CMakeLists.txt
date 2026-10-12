cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(fatrop REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE fatrop::fatrop)
if(TEST_FATROP_C_INTERFACE)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_FATROP_C_INTERFACE)
endif()

cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(KleidiAI REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE KleidiAI::kleidiai)

if(WITH_EXPERIMENTAL_OPS)
    if(NOT TARGET KleidiAIOps::kleidiai_ops)
        find_package(KleidiAIOps REQUIRED CONFIG)
    endif()
    target_compile_definitions(${PROJECT_NAME} PRIVATE WITH_EXPERIMENTAL_OPS)
    target_link_libraries(${PROJECT_NAME} PRIVATE KleidiAIOps::kleidiai_ops)
endif()

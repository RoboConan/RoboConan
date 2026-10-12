cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(ZLIB REQUIRED)

add_executable(${PROJECT_NAME} test_package.c)
if(TARGET ZLIB::ZLIB)
    target_link_libraries(${PROJECT_NAME} PRIVATE ZLIB::ZLIB)
elseif(TARGET ZLIB::ZLIBSTATIC)
    target_link_libraries(${PROJECT_NAME} PRIVATE ZLIB::ZLIBSTATIC)
else()
    message(FATAL_ERROR "No installed zlib CMake target is available")
endif()

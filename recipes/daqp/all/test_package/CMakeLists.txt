cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

find_package(daqp REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE daqp)

if(TARGET daqp_eigen)
    add_executable(test_package_eigen test_package.cpp)
    target_link_libraries(test_package_eigen PRIVATE daqp_eigen)
endif()

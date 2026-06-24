cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(souffle REQUIRED CONFIG)

add_executable(test_package "${CMAKE_BINARY_DIR}/hello.cpp")
target_link_libraries(test_package PRIVATE souffle::souffle)

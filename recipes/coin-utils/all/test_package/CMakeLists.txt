cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(coin-utils REQUIRED CONFIG)
add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE coin-utils::coin-utils)
target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_GMPL_PATH="${CMAKE_CURRENT_SOURCE_DIR}/test.mod")

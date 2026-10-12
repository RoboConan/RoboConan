cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

include(FindPkgConfig)
pkg_check_modules(OsiCbc REQUIRED IMPORTED_TARGET osi-cbc)
add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE PkgConfig::OsiCbc)

pkg_check_modules(Cbc REQUIRED IMPORTED_TARGET cbc)
add_executable(test_solver test_solver.cpp)
target_link_libraries(test_solver PRIVATE PkgConfig::Cbc)

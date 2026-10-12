cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(PkgConfig REQUIRED)
pkg_check_modules(OsiUnitTests REQUIRED IMPORTED_TARGET osi-unittests)
pkg_check_modules(OsiGlpk QUIET IMPORTED_TARGET osi-glpk)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE PkgConfig::OsiUnitTests)

if(TARGET PkgConfig::OsiGlpk)
    add_executable(glpk_test glpk_test.cpp)
    target_link_libraries(glpk_test PRIVATE PkgConfig::OsiGlpk)
endif()

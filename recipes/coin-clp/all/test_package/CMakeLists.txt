cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(coin-clp REQUIRED CONFIG)
find_package(PkgConfig REQUIRED)
pkg_check_modules(OsiClp REQUIRED IMPORTED_TARGET osi-clp)

add_executable(pkg_config_test test_package.cpp)
target_link_libraries(pkg_config_test PRIVATE PkgConfig::OsiClp)

add_executable(libclp_test libclp_test.cpp)
target_link_libraries(libclp_test PRIVATE coin-clp::libclp)

add_executable(solver_test solver_test.cpp)
target_link_libraries(solver_test PRIVATE coin-clp::solver)

add_executable(osi_clp_test osi_clp_test.cpp)
target_link_libraries(osi_clp_test PRIVATE coin-clp::osi-clp)

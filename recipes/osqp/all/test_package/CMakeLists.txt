cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(osqp REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE osqp::osqp)
target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_OSQP_SOLVE=$<BOOL:${TEST_OSQP_SOLVE}>)

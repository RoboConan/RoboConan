cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(blasfeo REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE blasfeo)
if(TEST_EXTERNAL_BLAS)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_EXTERNAL_BLAS)
endif()
if(TEST_FORTRAN_BLAS_API)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_FORTRAN_BLAS_API)
endif()

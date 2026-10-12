cmake_minimum_required(VERSION 3.15)
project(test_package)

find_package(BLAS CONFIG REQUIRED)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} BLAS::BLAS)

message(STATUS "CONAN_BLA_VENDOR: ${CONAN_BLA_VENDOR}")

cmake_minimum_required(VERSION 3.15)
project(test_package)

find_package(${OPENBLAS_CMAKE_PACKAGE} CONFIG REQUIRED)
foreach(target IN LISTS OPENBLAS_COMPATIBILITY_TARGETS)
    if(NOT TARGET ${target})
        message(FATAL_ERROR "Expected compatibility target ${target} was not generated")
    endif()
endforeach()

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} ${OPENBLAS_CMAKE_TARGET})

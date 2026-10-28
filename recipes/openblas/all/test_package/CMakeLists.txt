cmake_minimum_required(VERSION 3.15)
project(test_package)

if(OPENBLAS_TEST_INTEL_FORTRAN_ALIASES)
    enable_language(Fortran)
endif()

find_package(${OPENBLAS_CMAKE_PACKAGE} CONFIG REQUIRED)
foreach(target IN LISTS OPENBLAS_COMPATIBILITY_TARGETS)
    if(NOT TARGET ${target})
        message(FATAL_ERROR "Expected compatibility target ${target} was not generated")
    endif()
endforeach()

add_executable(${PROJECT_NAME} test_package.cpp)
if(OPENBLAS_TEST_INTEL_FORTRAN_ALIASES)
    target_sources(${PROJECT_NAME} PRIVATE test_fortran.f90)
endif()
target_link_libraries(${PROJECT_NAME} ${OPENBLAS_CMAKE_TARGET})

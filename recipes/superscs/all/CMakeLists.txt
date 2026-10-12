cmake_minimum_required(VERSION 3.15)
project(SuperSCS LANGUAGES C)

option(BUILD_DIRECT "Build scsdir" ON)
option(BUILD_INDIRECT "Build scsindir" ON)
option(USE_OPENMP "Enable OpenMP parallelization" OFF)
option(FLOAT "Use single precision floating point" OFF)
option(DLONG "Use 64-bit integers" ON)
option(BLAS64 "Use 64-bit BLAS" OFF)
option(GPU "Enable GPU acceleration with CUDA" OFF)

set(CMAKE_C_STANDARD 99 CACHE STRING "")
set(CMAKE_C_STANDARD_REQUIRED ON)

# Compiler definitions
add_compile_definitions(
    CTRLC=1
    SVD_ACTIVATED=1
    COPYAMATRIX=1
)
if(FLOAT)
    add_compile_definitions(SCS_FLOAT=1)
endif()
if(DLONG)
    add_compile_definitions(SCS_DLONG=1)
endif()
if(BLAS64)
    add_compile_definitions(BLAS64=1)
endif()

# Find dependencies
find_package(BLAS REQUIRED)
find_package(LAPACK REQUIRED)
add_compile_definitions(USE_LAPACK=1 LAPACK_LIB_FOUND=1)
if(USE_OPENMP)
    find_package(OpenMP REQUIRED)
    add_compile_definitions(USE_OPENMP=1)
endif()

include_directories(scsdir PUBLIC . include linsys)

# Core source files
set(SCS_SOURCES
    src/scs.c
    src/util.c
    src/cones.c
    src/cs.c
    src/linAlg.c
    src/ctrlc.c
    src/scs_version.c
    src/directions.c
    src/unit_test_util.c
    src/scs_parser.c
    linsys/common.c
)

# Direct solver library
if(BUILD_DIRECT)
    find_package(LDL REQUIRED)
    add_library(scsdir ${SCS_SOURCES} linsys/direct/private.c)
    target_link_libraries(scsdir PUBLIC SuiteSparse::LDL)
    target_include_directories(scsdir PUBLIC linsys/direct)
    if(DLONG)
        target_compile_definitions(scsdir PRIVATE DLONG=1 LDL_LONG=1)
    endif()
    list(APPEND ALL_TARGETS scsdir)
endif()

# Indirect solver library
if(BUILD_INDIRECT)
    add_library(scsindir ${SCS_SOURCES} linsys/indirect/private.c)
    target_include_directories(scsindir PUBLIC linsys/indirect)
    target_compile_definitions(scsindir PRIVATE INDIRECT=1)
    list(APPEND ALL_TARGETS scsindir)
endif()

# GPU solver library
if(GPU)
    find_package(CUDAToolkit REQUIRED)
    add_compile_definitions(GPU=1)
    add_library(scsgpu ${SCS_SOURCES} linsys/gpu/private.c)
    target_include_directories(scsgpu PUBLIC linsys/gpu)
    target_compile_definitions(scsgpu PRIVATE GPU=1)
    target_link_libraries(scsgpu PRIVATE CUDA::cudart CUDA::cublas CUDA::cusparse)
    list(APPEND ALL_TARGETS scsgpu)
endif()

foreach(target ${ALL_TARGETS})
    if(UNIX AND NOT APPLE)
        target_link_libraries(${target} PUBLIC m rt)
    elseif(APPLE)
        target_link_libraries(${target} PUBLIC m)
    endif()

    target_link_libraries(${target} PUBLIC ${BLAS_LIBRARIES} ${LAPACK_LIBRARIES})

    if(USE_OPENMP)
        target_link_libraries(${target} PUBLIC OpenMP::OpenMP_C)
    endif()

    if(CMAKE_BUILD_TYPE STREQUAL "Release")
        target_compile_options(${target} PRIVATE -O3 -ffast-math)
    endif()
endforeach()

# Installation
include(GNUInstallDirs)
install(TARGETS ${ALL_TARGETS}
    EXPORT SuperSCSTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/superscs
    FILES_MATCHING PATTERN "*.h"
)
install(FILES
    linsys/amatrix.h
    linsys/common.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/linsys
)

cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(dnnl REQUIRED CONFIG)

foreach(_variable
        DNNL_CPU_RUNTIME
        DNNL_CPU_THREADING_RUNTIME
        DNNL_GPU_RUNTIME
        DNNL_BLAS_VENDOR
        DNNL_GPU_VENDOR)
    if(NOT DEFINED ${_variable})
        message(FATAL_ERROR "${_variable} was not exported by the dnnl package")
    endif()
    if("${${_variable}}" STREQUAL "")
        message(FATAL_ERROR "${_variable} was exported with an empty value")
    endif()
endforeach()

if(DNNL_CPU_RUNTIME STREQUAL "NONE")
    set(_expected_cpu_threading_runtime "SEQ")
elseif(DNNL_CPU_RUNTIME STREQUAL "SYCL")
    set(_expected_cpu_threading_runtime "TBB")
else()
    set(_expected_cpu_threading_runtime "${DNNL_CPU_RUNTIME}")
endif()
if(NOT "${DNNL_CPU_THREADING_RUNTIME}" STREQUAL "${_expected_cpu_threading_runtime}")
    message(FATAL_ERROR
        "DNNL_CPU_THREADING_RUNTIME=${DNNL_CPU_THREADING_RUNTIME}, expected ${_expected_cpu_threading_runtime}")
endif()

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE DNNL::dnnl)

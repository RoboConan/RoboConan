cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(MKL REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE MKL::MKL)
if(TEST_MKL_BLACS)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_MKL_BLACS)
    target_link_libraries(${PROJECT_NAME} PRIVATE MKL::MKL_BLACS MKL::MKL_CDFT MKL::MKL_SCALAPACK)
endif()

if(TEST_MKL_SYCL_DISTRIBUTED_DFT)
    enable_language(CXX)
    add_executable(test_distributed_dft test_distributed_dft.cpp)
    target_link_libraries(test_distributed_dft PRIVATE MKL::MKL_SYCL_DISTRIBUTED_DFT)
endif()

cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(Python 3.10 REQUIRED COMPONENTS
             Interpreter Development.Module Development.SABIModule)
find_package(nanobind CONFIG REQUIRED)

nanobind_add_module(test_package_static NB_STATIC FREE_THREADED test_package.cpp)
target_compile_definitions(test_package_static PRIVATE TEST_MODULE=test_package_static)

nanobind_add_module(test_package_shared NB_SHARED FREE_THREADED test_package.cpp)
target_compile_definitions(test_package_shared PRIVATE TEST_MODULE=test_package_shared)

if(COMMAND nanobind_add_backend)
    nanobind_add_backend(test_package_backend)
    nanobind_add_module(test_package_split FREE_THREADED
                        BACKEND_MODULE test_package_backend test_package.cpp)
    target_compile_definitions(test_package_split PRIVATE TEST_MODULE=test_package_split)
endif()

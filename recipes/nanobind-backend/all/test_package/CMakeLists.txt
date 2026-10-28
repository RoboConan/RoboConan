cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(Python 3.10 REQUIRED COMPONENTS
             Interpreter Development.Module Development.SABIModule)
find_package(nanobind CONFIG REQUIRED)

nanobind_add_module(test_package FREE_THREADED
                    BACKEND_MODULE nanobind_backend test_package.cpp)

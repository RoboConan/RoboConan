cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(IPPCrypto CONFIG REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE IPPCrypto::ippcp)
if(WITH_CRYPTO_MB)
    target_compile_definitions(test_package PRIVATE WITH_CRYPTO_MB)
    target_link_libraries(test_package PRIVATE IPPCrypto::crypto_mb)
endif()

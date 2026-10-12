cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(GTSAM REQUIRED CONFIG)

find_package(GTSAMCMakeTools REQUIRED CONFIG)
include(GtsamPrinting)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE gtsam)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_${TEST_CXX_STANDARD})

if(TEST_BOOST_SERIALIZATION)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_BOOST_SERIALIZATION)
endif()

if(TEST_CEPHES)
    target_link_libraries(${PROJECT_NAME} PRIVATE cephes-gtsam-if)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_CEPHES)
endif()

if(TEST_CPPUNITLITE)
    target_link_libraries(${PROJECT_NAME} PRIVATE CppUnitLite)
endif()

if(TEST_CUDA)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_CUDA)
endif()

if(TEST_CUDSS)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_CUDSS)
endif()

if(TEST_METIS)
    target_link_libraries(${PROJECT_NAME} PRIVATE metis-gtsam-if)
endif()

if(TEST_MKL)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_MKL)
endif()

if(TEST_MOSEK)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_MOSEK)
endif()

if(TEST_UNSTABLE)
    target_link_libraries(${PROJECT_NAME} PRIVATE gtsam_unstable)
endif()

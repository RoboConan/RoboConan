cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(TBB REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE TBB::tbb)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_11)

if(WITH_TBBMALLOC)
    add_executable(test_tbbmalloc test_tbbmalloc.cpp)
    target_link_libraries(test_tbbmalloc PRIVATE TBB::tbbmalloc)
    target_compile_features(test_tbbmalloc PRIVATE cxx_std_11)
endif()

if(WITH_TBBPROXY)
    add_executable(test_tbbmalloc_proxy test_tbbmalloc_proxy.cpp)
    target_link_libraries(test_tbbmalloc_proxy PRIVATE TBB::tbbmalloc_proxy)
    target_compile_features(test_tbbmalloc_proxy PRIVATE cxx_std_11)
endif()

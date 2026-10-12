cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(libraw REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE libraw::libraw)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_11)

if(TARGET libraw::libraw_r)
    add_executable(${PROJECT_NAME}_r test_package.cpp)
    target_link_libraries(${PROJECT_NAME}_r PRIVATE libraw::libraw_r)
    target_compile_features(${PROJECT_NAME}_r PRIVATE cxx_std_11)
endif()

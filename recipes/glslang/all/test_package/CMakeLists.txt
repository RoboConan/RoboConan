cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(glslang REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
if(TARGET glslang::MachineIndependent)
    target_link_libraries(${PROJECT_NAME} PRIVATE glslang::MachineIndependent)
else()
    target_link_libraries(${PROJECT_NAME} PRIVATE glslang::glslang)
endif()
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_11)

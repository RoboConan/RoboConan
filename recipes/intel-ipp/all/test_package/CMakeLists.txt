cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

find_package(IPP REQUIRED CONFIG COMPONENTS ipp_iw ippcv)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE IPP::ipp_iw IPP::ippcv)

add_executable(test_package_cpp test_package.cpp)
target_link_libraries(test_package_cpp PRIVATE IPP::ipp_iw)

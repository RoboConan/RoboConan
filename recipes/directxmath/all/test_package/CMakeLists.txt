cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(directxmath REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE Microsoft::DirectXMath)

if(TARGET Microsoft::XDSP)
    add_executable(test_xdsp test_xdsp.cpp)
    target_link_libraries(test_xdsp PRIVATE Microsoft::XDSP)
endif()

if(TARGET Microsoft::DirectXSH)
    add_executable(test_directxsh test_directxsh.cpp)
    target_link_libraries(test_directxsh PRIVATE Microsoft::DirectXSH)
endif()

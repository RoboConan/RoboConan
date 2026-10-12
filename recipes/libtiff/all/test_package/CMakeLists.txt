cmake_minimum_required(VERSION 3.15)
project(test_package C CXX)

find_package(tiff REQUIRED CONFIG)
find_package(TIFF REQUIRED MODULE)

add_executable(${PROJECT_NAME}_c test_package.c)
target_link_libraries(${PROJECT_NAME}_c PRIVATE TIFF::tiff)

if(TARGET TIFF::tiffxx)
    add_executable(${PROJECT_NAME}_cxx test_package.cpp)
    target_link_libraries(${PROJECT_NAME}_cxx PRIVATE TIFF::tiffxx)
endif()

add_executable(${PROJECT_NAME}_module_c test_package.c)
target_link_libraries(${PROJECT_NAME}_module_c PRIVATE TIFF::TIFF)

if(TARGET TIFF::CXX)
    add_executable(${PROJECT_NAME}_module_cxx test_package.cpp)
    target_link_libraries(${PROJECT_NAME}_module_cxx PRIVATE TIFF::CXX)
endif()

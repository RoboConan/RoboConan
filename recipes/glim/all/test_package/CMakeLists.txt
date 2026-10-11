cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(glim REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE glim::glim)
if(GLIM_WITH_CUDA)
  target_link_libraries(${PROJECT_NAME} PRIVATE glim::odometry_estimation_gpu)
endif()
if(GLIM_WITH_VIEWER)
  target_link_libraries(${PROJECT_NAME} PRIVATE glim::map_editor)
endif()
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)

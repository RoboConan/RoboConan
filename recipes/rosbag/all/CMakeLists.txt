# Based on https://gitlab.com/VladyslavUsenko/basalt/-/blob/0f3b2b52c807f70ff4e2973ce253c73329eea7bc/vcpkg/ports/rosbag/cmake/CMakeLists.txt.in
cmake_minimum_required(VERSION 3.15)
project(rosbag LANGUAGES C CXX)

set(WINDOWS_EXPORT_ALL_SYMBOLS ON)

find_package(Boost REQUIRED COMPONENTS date_time filesystem program_options regex thread)
find_package(BZip2 REQUIRED)
find_package(console_bridge REQUIRED)
find_package(lz4 REQUIRED)

file(GLOB CPP_COMMON_SRCS "roscpp_core/cpp_common/src/*.cpp")
file(GLOB ROSCPP_SERIALIZATION_SRCS "roscpp_core/roscpp_serialization/src/*.cpp")
file(GLOB ROSTIME_SRCS "roscpp_core/rostime/src/*.cpp")
file(GLOB ROSBAG_SRCS "ros_comm/tools/rosbag_storage/src/*.cpp")
file(GLOB ROSLZ4_SRCS "ros_comm/utilities/roslz4/src/[a-z]*.c")

add_library(rosbag
  ${ROSBAG_SRCS}
  ${ROSTIME_SRCS}
  ${CPP_COMMON_SRCS}
  ${ROSCPP_SERIALIZATION_SRCS}
  ${ROSLZ4_SRCS}
)

if(NOT MSVC)
  target_compile_options(rosbag PRIVATE -Wno-unused-parameter -Wno-deprecated-declarations)
endif()
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  target_compile_options(rosbag PRIVATE -Wno-catch-value)
endif()

target_include_directories(rosbag
  PUBLIC
    ros_comm/tools/rosbag_storage/include
    roscpp_core/cpp_common/include
    roscpp_core/rostime/include
    roscpp_core/roscpp_serialization/include
    roscpp_core/roscpp_traits/include
    ros_comm/utilities/roslz4/include
)

target_link_libraries(rosbag
  PUBLIC
    Boost::date_time
    Boost::filesystem
    Boost::program_options
    Boost::regex
    Boost::thread
    BZip2::BZip2
    console_bridge::console_bridge
    lz4::lz4
)

install(TARGETS rosbag RUNTIME DESTINATION bin LIBRARY DESTINATION lib ARCHIVE DESTINATION lib)

install(DIRECTORY "ros_comm/tools/rosbag_storage/include/" DESTINATION include)
install(DIRECTORY "roscpp_core/cpp_common/include/" DESTINATION include)
install(DIRECTORY "roscpp_core/rostime/include/" DESTINATION include)
install(DIRECTORY "roscpp_core/roscpp_serialization/include/" DESTINATION include)
install(DIRECTORY "roscpp_core/roscpp_traits/include/" DESTINATION include)
install(DIRECTORY "ros_comm/utilities/roslz4/include/" DESTINATION include)

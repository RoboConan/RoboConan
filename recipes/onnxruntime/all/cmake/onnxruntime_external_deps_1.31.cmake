# Replacement for https://github.com/microsoft/onnxruntime/blob/v1.31.0/cmake/external/onnxruntime_external_deps.cmake

if(NOT onnxruntime_DISABLE_ABSEIL)
  find_package(absl REQUIRED CONFIG)
  include_directories(${absl_INCLUDE_DIRS})
  set(ABSEIL_LIBS abseil::abseil)
endif()

find_package(re2 REQUIRED CONFIG)
find_package(Flatbuffers REQUIRED CONFIG)

find_package(Protobuf REQUIRED CONFIG)
if(onnxruntime_USE_FULL_PROTOBUF)
  set(PROTOBUF_LIB protobuf::libprotobuf)
else()
  set(PROTOBUF_LIB protobuf::libprotobuf-lite)
endif()
set(ONNX_CUSTOM_PROTOC_EXECUTABLE protoc)
set(PROTOC_EXECUTABLE protoc)

find_package(date REQUIRED CONFIG)
include_directories(${date_INCLUDE_DIRS})
add_library(date_interface INTERFACE)

find_package(Boost REQUIRED CONFIG)
find_package(nlohmann_json REQUIRED CONFIG)

find_package(cpuinfo REQUIRED CONFIG)
list(APPEND ONNXRUNTIME_CPUINFO_TARGETS cpuinfo::cpuinfo)
set(CPUINFO_SUPPORTED ${cpuinfo_FOUND})
if(CPUINFO_SUPPORTED)
  if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
    set(IOS ON CACHE INTERNAL "")
    set(IOS_ARCH "${CMAKE_OSX_ARCHITECTURES}" CACHE INTERNAL "")
  endif()
  if(NOT CMAKE_SYSTEM_NAME STREQUAL "Emscripten")
    string(APPEND CMAKE_CXX_FLAGS " -DCPUINFO_SUPPORTED")
  endif()
endif()
if(TARGET cpuinfo::cpuinfo AND NOT TARGET cpuinfo)
  add_library(cpuinfo ALIAS cpuinfo::cpuinfo)
endif()

if(NOT WIN32)
  find_package(nsync REQUIRED CONFIG)
  include_directories(${nsync_INCLUDE_DIRS})
  add_library(nsync_cpp INTERFACE)
endif()

find_package(Microsoft.GSL 4.0 REQUIRED CONFIG)
set(GSL_TARGET Microsoft.GSL::GSL)
include_directories(${Microsoft.GSL_INCLUDE_DIRS})

find_package(safeint REQUIRED CONFIG)
include_directories(${safeint_INCLUDE_DIRS})
add_library(safeint_interface IMPORTED INTERFACE)

find_package(ONNX REQUIRED CONFIG)

find_package(Eigen3 REQUIRED CONFIG)
set(eigen_INCLUDE_DIRS ${Eigen3_INCLUDE_DIRS})

if(WIN32)
  find_package(wil REQUIRED CONFIG)
  set(WIL_TARGET WIL::WIL)
  include_directories(${wil_INCLUDE_DIRS})
endif()

if(onnxruntime_USE_XNNPACK)
  if(onnxruntime_DISABLE_CONTRIB_OPS)
    message(FATAL_ERROR "XNNPACK EP requires the internal NHWC contrib ops")
  endif()
  find_package(xnnpack REQUIRED CONFIG)
  find_package(pthreadpool REQUIRED CONFIG)
  set(onnxruntime_EXTERNAL_LIBRARIES_XNNPACK xnnpack::xnnpack pthreadpool)
  if(NOT TARGET XNNPACK)
    add_library(XNNPACK ALIAS xnnpack::xnnpack)
  endif()
endif()

if(onnxruntime_USE_MIMALLOC)
  find_package(mimalloc REQUIRED CONFIG)
  add_definitions(-DUSE_MIMALLOC)
endif()

set(onnxruntime_EXTERNAL_LIBRARIES ${onnxruntime_EXTERNAL_LIBRARIES_XNNPACK} ${WIL_TARGET} nlohmann_json::nlohmann_json
                                  onnx onnx_proto ${PROTOBUF_LIB} re2::re2 Boost::mp11 safeint_interface
                                  flatbuffers::flatbuffers ${GSL_TARGET} ${ABSEIL_LIBS} date::date
                                  ${ONNXRUNTIME_CPUINFO_TARGETS} Eigen3::Eigen)

set(onnxruntime_EXTERNAL_DEPENDENCIES onnx_proto flatbuffers::flatbuffers)

file(TO_NATIVE_PATH ${CMAKE_BINARY_DIR} ORT_BINARY_DIR)
file(TO_NATIVE_PATH ${PROJECT_SOURCE_DIR} ORT_SOURCE_DIR)

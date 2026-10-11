cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

enable_testing()

set(TESTED_MODULES
    # Main modules
    "calib" "core" "dnn" "features" "flann" "geometry" "highgui" "imgcodecs"
    "imgproc" "objdetect" "photo" "ptcloud" "stereo" "stitching" "video" "videoio"
    # Extra modules
    "alphamat" "bgsegm" "bioinspired" "ccalib" "datasets" "dnn_superres" "face"
    "freetype" "fuzzy" "gapi" "hdf" "hfs" "img_hash" "intensity_transform"
    "line_descriptor" "ml" "optflow" "phase_unwrapping" "plot" "quality" "reg"
    "rgbd" "saliency" "sfm" "shape" "signal" "structured_light" "superres"
    "surface_matching" "text" "tracking" "wechat_qrcode" "xfeatures2d"
    "ximgproc" "xobjdetect" "xphoto" "xstereo"
)

set(GENERIC_TESTED_MODULES
    "cudaarithm" "cudabgsegm" "cudacodec" "cudafeatures2d" "cudafilters"
    "cudaimgproc" "cudalegacy" "cudaobjdetect" "cudaoptflow" "cudastereo"
    "cudawarping" "cvv" "dnn_objdetect" "dpm" "ovis" "rapid" "videostab" "viz"
)

set(_opencv_components core)
foreach(_module ${TESTED_MODULES} ${GENERIC_TESTED_MODULES})
    string(TOUPPER ${_module} _module_upper)
    if(OPENCV_WITH_${_module_upper})
        if(TEST_OPENCV_WORLD AND NOT TEST_OPENCV_SHARED)
            if(_module STREQUAL "img_hash" OR _module STREQUAL "sfm")
                list(APPEND _opencv_components ${_module})
            endif()
        else()
            list(APPEND _opencv_components ${_module})
        endif()
    endif()
endforeach()
if(TEST_OPENCV_WORLD AND NOT TEST_OPENCV_SHARED)
    list(REMOVE_ITEM _opencv_components core)
    list(PREPEND _opencv_components opencv_world)
endif()
list(REMOVE_DUPLICATES _opencv_components)

find_package(OpenCV REQUIRED COMPONENTS ${_opencv_components} CONFIG)

foreach(_component ${_opencv_components})
    if(NOT OpenCV_${_component}_FOUND)
        message(FATAL_ERROR "OpenCV did not report requested component '${_component}' as found")
    endif()
    if(_component MATCHES "^opencv_")
        set(_component_target ${_component})
    else()
        set(_component_target opencv_${_component})
    endif()
    if(NOT TARGET ${_component_target})
        message(FATAL_ERROR "OpenCV did not define requested target '${_component_target}'")
    endif()
endforeach()
if(NOT "${OpenCV_LIBS}" STREQUAL "${OpenCV_LIBRARIES}")
    message(FATAL_ERROR "OpenCV_LIBS and OpenCV_LIBRARIES differ")
endif()

add_executable(test_compatibility_variables test_core.cpp)
target_link_libraries(test_compatibility_variables PRIVATE ${OpenCV_LIBRARIES})
target_compile_features(test_compatibility_variables PRIVATE cxx_std_17)
add_test(NAME test_compatibility_variables COMMAND test_compatibility_variables)

foreach(_module ${TESTED_MODULES})
    string(TOUPPER ${_module} _module_upper)
    if(OPENCV_WITH_${_module_upper})
        set(_test_target test_${_module})
        if(TEST_OPENCV_WORLD AND NOT TEST_OPENCV_SHARED
           AND NOT _module STREQUAL "img_hash" AND NOT _module STREQUAL "sfm")
            set(_module_target opencv_world)
        else()
            set(_module_target opencv_${_module})
        endif()
        add_executable(${_test_target} ${_test_target}.cpp)
        target_link_libraries(${_test_target} PRIVATE ${_module_target})
        target_compile_features(${_test_target} PRIVATE cxx_std_17)
        if(NOT ${_module} STREQUAL "highgui")
            add_test(NAME ${_test_target} COMMAND ${_test_target})
        endif()
    endif()
endforeach()

foreach(_module ${GENERIC_TESTED_MODULES})
    string(TOUPPER ${_module} _module_upper)
    if(OPENCV_WITH_${_module_upper})
        set(_test_target test_link_${_module})
        if(TEST_OPENCV_WORLD AND NOT TEST_OPENCV_SHARED)
            set(_module_target opencv_world)
        else()
            set(_module_target opencv_${_module})
        endif()
        add_executable(${_test_target} test_link.cpp)
        target_compile_definitions(${_test_target} PRIVATE TEST_OPENCV_MODULE_${_module_upper})
        target_link_libraries(${_test_target} PRIVATE ${_module_target})
        target_compile_features(${_test_target} PRIVATE cxx_std_17)
        add_test(NAME ${_test_target} COMMAND ${_test_target})
    endif()
endforeach()

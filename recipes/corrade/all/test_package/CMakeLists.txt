cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

set(_corrade_components)
if(WITH_MAIN)
    list(APPEND _corrade_components Main)
endif()
if(WITH_UTILITY)
    list(APPEND _corrade_components Utility)
endif()
if(_corrade_components)
    find_package(Corrade REQUIRED COMPONENTS ${_corrade_components} CONFIG)
else()
    find_package(Corrade REQUIRED CONFIG)
endif()

add_executable(${PROJECT_NAME} test_package.cpp)
if(WITH_MAIN)
    target_link_libraries(${PROJECT_NAME} Corrade::Main)
endif()
if(WITH_UTILITY)
	target_compile_definitions(${PROJECT_NAME} PRIVATE WITH_UTILITY)
	target_link_libraries(${PROJECT_NAME} Corrade::Utility)
endif()

set_target_properties(${PROJECT_NAME}
    PROPERTIES
    	CXX_STANDARD 11
    	CXX_STANDARD_REQUIRED ON
    	CXX_EXTENSIONS OFF
)

cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(MagnumExtras REQUIRED CONFIG)

function(test_imported_executable target)
    if(NOT TARGET ${target})
        message(FATAL_ERROR "${target} target is missing")
    endif()
    get_target_property(location ${target} IMPORTED_LOCATION_RELEASE)
    if(NOT location)
        get_target_property(location ${target} IMPORTED_LOCATION)
    endif()
    if(NOT EXISTS "${location}")
        message(FATAL_ERROR "${target} location does not exist: ${location}")
    endif()
endfunction()

if(TEST_PLAYER)
    test_imported_executable(MagnumExtras::player)
endif()
if(TEST_UI_GALLERY)
    test_imported_executable(MagnumExtras::ui-gallery)
endif()

if(TEST_UI)
    add_executable(${PROJECT_NAME} test_package.cpp)
    target_link_libraries(${PROJECT_NAME} PRIVATE MagnumExtras::Ui)
    set_target_properties(${PROJECT_NAME}
        PROPERTIES
            CXX_STANDARD 11
            CXX_STANDARD_REQUIRED ON
            CXX_EXTENSIONS OFF
    )
endif()

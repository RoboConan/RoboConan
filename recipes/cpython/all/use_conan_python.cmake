get_filename_component(_PREFIX_PATH "@PREFIX_PATH@" ABSOLUTE)

if(DEFINED Python3_VERSION_STRING)
    set(_PYTHON "Python3")
else()
    set(_PYTHON "Python")
endif()

# Allow Python_EXECUTABLE to be overridden for cross-compilation support
if(NOT DEFINED ${_PYTHON}_EXECUTABLE)
    set(${_PYTHON}_EXECUTABLE "@PYTHON_EXECUTABLE@")
endif()

set(${_PYTHON}_LIBRARY "@PYTHON_LIBRARY@")
@PYTHON_FIND_ABI@

# FindPython fails if these are set beforehand
unset(${_PYTHON}_INCLUDE_DIRS)
unset(${_PYTHON}_INCLUDE_DIR)

include(${CMAKE_ROOT}/Modules/Find${_PYTHON}.cmake)

# A cross build uses the runnable build-context interpreter above. Restore ABI
# metadata from the target package so extension modules get target suffixes.
set(${_PYTHON}_SOABI "@PYTHON_SOABI@")
set(${_PYTHON}_SOSABI "@PYTHON_SOSABI@")
set(${_PYTHON}_FREE_THREADED @PYTHON_FREE_THREADED@)

# Sanity check: The former comes from FindPython(3), the latter comes from the injected find module
if(NOT ${_PYTHON}_VERSION VERSION_EQUAL ${_PYTHON}_VERSION_STRING)
    message(FATAL_ERROR "CMake detected wrong cpython version - this is likely a bug with the cpython Conan package: "
                        "found ${${_PYTHON}_VERSION} but expected ${_PYTHON}_VERSION_STRING}")
endif()

if (TARGET ${_PYTHON}::Module)
    set_target_properties(${_PYTHON}::Module PROPERTIES INTERFACE_LINK_LIBRARIES cpython::python)
endif()
if (TARGET ${_PYTHON}::SABIModule)
    set_target_properties(${_PYTHON}::SABIModule PROPERTIES INTERFACE_LINK_LIBRARIES cpython::python)
endif()
if (TARGET ${_PYTHON}::Python)
    set_target_properties(${_PYTHON}::Python PROPERTIES INTERFACE_LINK_LIBRARIES cpython::embed)
endif()

unset(_PYTHON)

#! /usr/bin/python
# Usage: ./update_options.py <vtk-source-path> > options/<version>.json
# Run with --dump-metadata to get the raw metadata extracted from module.vtk files instead.

import argparse
import json
from collections import defaultdict
from pathlib import Path


#### EXTRACT METADATA ####

# Based on https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/CMake/vtkModule.cmake?ref_type=tags
OPTIONS = {
    "implementable",
    "exclude_wrap",
    "third_party",
    "include_marshal",
}
SINGLE_VALUE = {
    "library_name",
    "name",
    "kit",
    "spdx_download_location",
    "spdx_custom_license_file",
    "spdx_custom_license_name",
    # Moved from MULTI_VALUE
    "spdx_license_identifier",
    "description",
}
MULTI_VALUE = {
    "groups",
    "depends",  # if one of these is no, then this module will not be built
    "private_depends",  # if one of these is no, then this module will not be built
    "optional_depends",  # if one of these is no, does not stop the module from building
    "order_depends",
    "test_depends",
    "test_optional_depends",
    "test_labels",
    "condition",
    "implements",
    "license_files",
    "spdx_copyright_text",
}

def parse_vtk_module(path):
    with open(path, "r", encoding="utf8") as f:
        lines = f.readlines()
    module = {}
    key = None
    values = []
    for line in lines:
        line = line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("  "):
            values.append(line.strip())
        else:
            if key is None and values:
                raise RuntimeError("Unexpected values without any key")
            if key is not None:
                module[key] = values
            key = line.strip().lower()
            values = []
    if key is not None:
        module[key] = values
    for key, values in list(module.items()):
        if key in OPTIONS:
            module[key] = True
        elif key in SINGLE_VALUE:
            if len(values) != 1:
                raise RuntimeError(f"Expected single value for {key}, got {values}")
            module[key] = values[0]
        elif key in MULTI_VALUE:
            module[key] = values
    return module


def find_vtk_modules(root, name="vtk.module", exclude=("Examples", "Testing")):
    root = Path(root)
    for path in root.rglob(name):
        rel_path = path.relative_to(root)
        if not str(rel_path).startswith(exclude):
            yield path


def load_vtk_module_details(root):
    modules = {}
    for path in find_vtk_modules(root, "vtk.module"):
        module_info = parse_vtk_module(path)
        module_info["path"] = str(path.parent.relative_to(root))
        name = module_info["name"]
        del module_info["name"]
        modules[name] = module_info
    return modules

def load_vtk_kit_details(root):
    kits = {}
    for path in find_vtk_modules(root, "vtk.kit"):
        kit_info = parse_vtk_module(path)
        kit_info["path"] = str(path.parent.relative_to(root))
        name = kit_info["name"]
        del kit_info["name"]
        kits[name] = kit_info
    return kits

def load_vtk_info(root):
    return {
        "modules": load_vtk_module_details(root),
        "kits": load_vtk_kit_details(root),
    }


#### DUMP OPTIONS ####

# Third-party modules kept in the generated dependency graph. Most are bundled;
# some are externally supplied without their own VTK module.
tracked_third_party_modules = {
    "conduit",
    "diy2",
    "exodusII",
    "fides",
    "gl2ps",
    "glad",
    "h5hut",
    "ioss",
    "kwiml",
    "metaio",
    "mpi4py",
    "octree",
    "token",
    "verdict",
    "viskores",
    "vpic",
    "vtkm",
    "x11",
    "xdmf2",
    "xdmf3",
}

# Modules that should be always built and have no optional dependencies
required_modules = {
    "sys",
    "CommonArchive",
    "CommonColor",
    "CommonComputationalGeometry",
    "CommonCore",
    "CommonDataModel",
    "CommonExecutionModel",
    "CommonMath",
    "CommonMisc",
    "CommonPython",
    "CommonSystem",
    "CommonTransforms",
    "FiltersCore",
    "FiltersGeneral",
    "FiltersVerdict",
}

# Non-optional third-party deps
ignored_deps = {
    "exprtk",
    "fmt",
    "fast_float",
    "kissfft",
    "kwiml",
    "libarchive",
    "loguru",
    "lz4",
    "lzma",
    "nlohmannjson",
    "pegtl",
    "pugixml",
    "scn",
    "utf8",
    "verdict",
    "zlib",
}

# These dependencies have no external package support but are required by
# otherwise-unconditional modules. Keep their own third-party modules in the
# generated metadata while omitting them from module option requirements.
always_internal_deps = {
    "glad",
    "token",
    "x11",
}

# Dependencies that are not modelled via modules and are used directly instead
missing_deps = {
    "CommonArchive": ["libarchive"],
    "DomainsMicroscopy": ["openslide"],
    "FiltersReebGraph": ["boost"],
    "GUISupportQt": ["qt"],
    "GUISupportQtQuick": ["qt"],
    "GUISupportQtSQL": ["qt"],
    "GeovisGDAL": ["gdal"],
    "FiltersONNX": ["onnxruntime"],
    "IOADIOS2": ["adios2"],
    "IOAlembic": ["alembic"],
    "IOCatalystConduit": ["catalyst"],
    "IOFFMPEG": ["ffmpeg"],
    "IOGDAL": ["gdal"],
    "IOIFC": ["boost", "ifcopenshell", "opencascade"],
    "IOLAS": ["liblas", "boost"],
    "IONanoVDB": ["nanovdb"],
    "IOMySQL": ["mysql"],
    "IOOCCT": ["opencascade"],
    "IOODBC": ["odbc"],
    "IOOpenVDB": ["openvdb"],
    "IOPDAL": ["pdal"],
    "IOPostgreSQL": ["postgresql"],
    "IOUSD": ["openusd"],
    "InfovisBoost": ["boost"],
    "InfovisBoostGraphAlgorithms": ["boost"],
    "RenderingFreeTypeFontConfig": ["fontconfig"],
    "RenderingAnari": ["anari"],
    "RenderingOpenVR": ["openvr"],
    "RenderingOpenXR": ["openxr"],
    "RenderingOpenXRRemoting": ["openxr", "openxrremoting"],
    "RenderingQt": ["qt"],
    "RenderingVR": ["zeromq"],
    "RenderingZSpace": ["zspace"],
    "ViewsQt": ["qt"],
    "fides": ["adios2"],
    "xdmf3": ["boost"],
}
missing_optional_deps = {
    "CommonCore": ["memkind"],
    "RenderingOpenGL2": ["x11", "wayland", "cocoa", "directx"],
    "RenderingRayTracing": ["ospray", "openimagedenoise", "visrtx"],
    "RenderingUI": ["x11", "wayland", "cocoa"],
    "RenderingWebGPU": ["dawn", "wayland"],
}

def _strip_prefix(name):
    name = name.replace("VTK::", "")
    if name.startswith("vtk"):
        return name[3:]
    return name

def _is_ext_dep(name):
    return name[0].islower() and name != "sys"

def _flattened_deps(dependencies_map):
    def _traverse(module_name, visiting):
        if module_name in flat_deps:
            return flat_deps[module_name]
        if module_name in visiting:
            return set()
        visiting.add(module_name)
        deps = set()
        for dep in dependencies_map.get(module_name, set()):
            if _is_ext_dep(dep):
                deps.add(dep)
            else:
                deps.update(_traverse(dep, visiting))
        visiting.remove(module_name)
        flat_deps[module_name] = deps
        return deps

    flat_deps = {}
    for mod in dependencies_map:
        _traverse(mod, set())
    return flat_deps

def dump_options(vtk_info):
    modules_deps = {}
    for module_name, module_info in vtk_info["modules"].items():
        module_name = _strip_prefix(module_name)
        deps = module_info.get("depends", []) + module_info.get("private_depends", []) + missing_deps.get(module_name, [])
        deps = set(_strip_prefix(dep) for dep in deps) - ignored_deps - always_internal_deps
        modules_deps[module_name] = deps
    flat_deps = _flattened_deps(modules_deps)
    for req in required_modules:
        assert not flat_deps[req], f"Required module {req} has dependencies: {flat_deps[req]}"
    flat_deps = {
        k: sorted(v)
        for k, v in sorted(flat_deps.items())
        if k not in required_modules and (not _is_ext_dep(k) or k in tracked_third_party_modules)
    }

    conditions = defaultdict(list)
    for module_name, module_info in vtk_info["modules"].items():
        module_name = _strip_prefix(module_name)
        for condition in module_info.get("condition", []):
            conditions[condition].append(module_name)
    conditions = {k: sorted(v) for k, v in sorted(conditions.items())}

    opt_deps = {}
    for module_name, module_info in sorted(vtk_info["modules"].items()):
        module_name = _strip_prefix(module_name)
        if not _is_ext_dep(module_name):
            deps = set(_strip_prefix(d) for d in module_info.get("optional_depends", []) + missing_optional_deps.get(module_name, []))
            deps = sorted(d for d in deps - ignored_deps if _is_ext_dep(d))
            if deps:
                opt_deps[module_name] = deps

    print(json.dumps({
        "flat_external_deps": flat_deps,
        "optional_external_deps": opt_deps,
        "conditions": conditions,
    }, indent=2))

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Conan VTK Recipe Helper for adding new VTK versions to recipe - tool for extracting module information from VTK source",
    )
    parser.add_argument("source_path")
    parser.add_argument("--dump-metadata", action="store_true")
    args = parser.parse_args(argv)
    vtk_info = load_vtk_info(args.source_path)
    if args.dump_metadata:
        print(json.dumps(vtk_info, indent=2))
    else:
        dump_options(vtk_info)


if __name__ == "__main__":
    main()

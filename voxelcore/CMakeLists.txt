include(CheckCXXSourceCompiles)
cmake_minimum_required(VERSION 3.21)
project(voxelcore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

add_compile_options(-Wall -Wextra -Wno-unused-parameter)
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_compile_options(-O3)
endif()

# Engine interface library (header-first for now; split into .cpp TUs as they grow).
add_library(voxelcore_engine INTERFACE)
target_include_directories(voxelcore_engine INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/engine)
find_package(Threads REQUIRED)

# zlib probe: try the unversioned name first, then the glibc soname.
set(_zlib_found FALSE)
foreach(_lib IN ITEMS "z" "-l:libz.so.1")
    set(CMAKE_REQUIRED_LIBRARIES "${_lib}")
    unset(VOXELCORE_ZLIB_WORKS CACHE)
    check_cxx_source_compiles("
extern \"C\" {
    unsigned long compressBound(unsigned long);
    int compress2(unsigned char*, unsigned long*, const unsigned char*, unsigned long, int);
    int uncompress(unsigned char*, unsigned long*, const unsigned char*, unsigned long);
    }
    int main() {
        unsigned char src[4] = {1,2,3,4}, dst[64], out[64];
        unsigned long dlen = sizeof(dst);
        if (compress2(dst, &dlen, src, sizeof(src), 6) != 0) return 1;
        unsigned long olen = sizeof(out);
        if (uncompress(out, &olen, dst, dlen) != 0) return 2;
        return out[0] == 1 ? 0 : 3;
    }" VOXELCORE_ZLIB_WORKS)
    if(VOXELCORE_ZLIB_WORKS)
        target_compile_definitions(voxelcore_engine INTERFACE VOXELCORE_HAVE_ZLIB)
        target_link_libraries(voxelcore_engine INTERFACE ${_lib})
        message(STATUS "zlib: found (${_lib})")
        set(_zlib_found TRUE)
        break()
    endif()
endforeach()
unset(CMAKE_REQUIRED_LIBRARIES)
if(NOT _zlib_found)
    message(WARNING "zlib: NOT found — region-file writes will fail at runtime; reads of compressed data will fail loudly")
endif()
target_link_libraries(voxelcore_engine INTERFACE Threads::Threads)

add_executable(voxelcore tools/voxelcore-cli/main.cpp)
target_link_libraries(voxelcore PRIVATE voxelcore_engine)

add_executable(voxelcore_tests tests/test_main.cpp)
target_link_libraries(voxelcore_tests PRIVATE voxelcore_engine)

add_executable(voxelcore_bench benchmarks/bench_main.cpp)
target_link_libraries(voxelcore_bench PRIVATE voxelcore_engine)

# ---- Vulkan headless renderer (Stage 4/5) -----------------------------
# Compile-verified wherever Vulkan-Headers are available. RUNTIME-verified only where a
# Vulkan ICD exists (CI: Mesa lavapipe on ubuntu-latest). Skipped cleanly otherwise.
option(VOXELCORE_WITH_VULKAN "Build Vulkan headless renderer" ON)
if(VOXELCORE_WITH_VULKAN)
    # 1) Vulkan-Headers: system package, local cache (.vulkan-headers/), or FetchContent.
    set(VOXELCORE_VK_HEADERS_DIR "" CACHE PATH "Path to Vulkan-Headers root (contains include/vulkan/vulkan.h)")
    if(NOT VOXELCORE_VK_HEADERS_DIR AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../.vulkan-headers/include/vulkan/vulkan.h")
        set(VOXELCORE_VK_HEADERS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../.vulkan-headers")
    endif()
    if(NOT VOXELCORE_VK_HEADERS_DIR)
        find_path(VOXELCORE_VK_HEADERS_DIR vulkan/vulkan.h
                  PATHS /usr/include /usr/local/include /opt/homebrew/include
                  PATH_SUFFIXES "" "vulkan-headers")
    endif()
    if(NOT VOXELCORE_VK_HEADERS_DIR)
        message(STATUS "Vulkan-Headers not found locally — will fetch via FetchContent (needs network)")
        include(FetchContent)
        FetchContent_Declare(vulkan_headers GIT_REPOSITORY https://github.com/KhronosGroup/Vulkan-Headers.git GIT_TAG v1.4.313)
        FetchContent_MakeAvailable(vulkan_headers)
        set(VOXELCORE_VK_HEADERS_DIR ${vulkan_headers_SOURCE_DIR})
    endif()
    message(STATUS "Vulkan-Headers: ${VOXELCORE_VK_HEADERS_DIR}")

    # 2) SPIR-V compiler: glslangValidator → fallback glslc → fallback pip glslang wheel.
    # Khronos glslang names it glslangValidator (older) / glslang (newer stand-alone); glslc is Shaderc.
    find_program(VOXELCORE_GLSLANG NAMES glslangValidator glslang glslc)
    if(VOXELCORE_GLSLANG)
        message(STATUS "SPIR-V compiler: ${VOXELCORE_GLSLANG}")
    else()
        message(WARNING "No glslangValidator/glslc found — SPIR-V blobs will use the committed fallback if present; vulkan_render will report 'shader missing' otherwise")
    endif()

    set(VOXELCORE_SPV_DIR "${CMAKE_CURRENT_BINARY_DIR}/shaders_spv")
    file(MAKE_DIRECTORY "${VOXELCORE_SPV_DIR}")
    configure_file("${CMAKE_CURRENT_SOURCE_DIR}/vulkan_build_config.hpp.in"
                   "${CMAKE_CURRENT_BINARY_DIR}/vulkan_build_config.hpp" @ONLY)
    set(VOXELCORE_SPV_CONFIG_INC "${CMAKE_CURRENT_BINARY_DIR}")
    set(_vert "${CMAKE_CURRENT_SOURCE_DIR}/engine/rendering/vulkan/shaders/voxelcore.vert")
    set(_frag "${CMAKE_CURRENT_SOURCE_DIR}/engine/rendering/vulkan/shaders/voxelcore.frag")
    set(_recvert "${CMAKE_CURRENT_SOURCE_DIR}/engine/rendering/vulkan/shaders/records.vert")
    if(VOXELCORE_GLSLANG)
        add_custom_command(OUTPUT "${VOXELCORE_SPV_DIR}/voxelcore.vert.spv" "${VOXELCORE_SPV_DIR}/voxelcore.frag.spv" "${VOXELCORE_SPV_DIR}/records.vert.spv"
                           COMMAND "${VOXELCORE_GLSLANG}" -V "${_vert}" -o "${VOXELCORE_SPV_DIR}/voxelcore.vert.spv"
                           COMMAND "${VOXELCORE_GLSLANG}" -V "${_frag}" -o "${VOXELCORE_SPV_DIR}/voxelcore.frag.spv"
                           COMMAND "${VOXELCORE_GLSLANG}" -V "${_recvert}" -o "${VOXELCORE_SPV_DIR}/records.vert.spv"
                           DEPENDS "${_vert}" "${_frag}" "${_recvert}" VERBATIM)
        add_custom_target(voxelcore_shaders ALL DEPENDS "${VOXELCORE_SPV_DIR}/voxelcore.vert.spv" "${VOXELCORE_SPV_DIR}/voxelcore.frag.spv" "${VOXELCORE_SPV_DIR}/records.vert.spv")
    else()
        add_custom_target(voxelcore_shaders ALL COMMAND ${CMAKE_COMMAND} -E echo "voxelcore_shaders: no compiler — runtime will report shader missing")
    endif()

    # The renderer dlopens libvulkan at runtime (like Android), so the build itself never
    # requires a system Vulkan loader — only the headers. Runtime absence degrades to a
    # clean skip (exit 77) instead of a configure/link failure.
    add_executable(vulkan_render tools/vulkan_render.cpp)
    add_dependencies(vulkan_render voxelcore_shaders)
    add_executable(records_parity tools/records_parity.cpp)
    add_dependencies(records_parity voxelcore_shaders)
    target_compile_definitions(records_parity PRIVATE VOXELCORE_WITH_VULKAN VOXELCORE_SPV_CONFIG)
    target_include_directories(records_parity PRIVATE "${VOXELCORE_VK_HEADERS_DIR}/include" "${VOXELCORE_SPV_CONFIG_INC}")
    target_link_libraries(records_parity PRIVATE voxelcore_engine ${CMAKE_DL_LIBS})
    target_compile_definitions(vulkan_render PRIVATE VOXELCORE_WITH_VULKAN VOXELCORE_SPV_CONFIG)
    target_include_directories(vulkan_render PRIVATE "${VOXELCORE_VK_HEADERS_DIR}/include" "${VOXELCORE_SPV_CONFIG_INC}")
    target_link_libraries(vulkan_render PRIVATE voxelcore_engine ${CMAKE_DL_LIBS})
    message(STATUS "Vulkan: dlopen-based runtime loader — vulkan_render always builds")
endif()

enable_testing()
add_test(NAME unit COMMAND voxelcore_tests)

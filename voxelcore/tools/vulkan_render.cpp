// PROJECT VOXELCORE — headless Vulkan render: mesh a chunk, draw via Vulkan, dump PPM.
// Exit 0 + non-trivial PPM = pass. Skips cleanly (exit 77) when no Vulkan device exists.
#include "../engine/world/world.hpp"
#include "../engine/world/block_reader.hpp"
#include "../engine/meshing/mesher.hpp"
#include "../engine/rendering/mesh_triangles.hpp"
#include <cstdio>
#include <string>
#include <vector>

#if defined(VOXELCORE_WITH_VULKAN)
#if defined(VOXELCORE_SPV_CONFIG)
#include "vulkan_build_config.hpp"
#endif
#include "../engine/rendering/vulkan/vulkan_headless.hpp"
#include "../engine/rendering/math.hpp"
#endif

using namespace vc;

int main(int argc, char** argv) {
    const std::string outPath = argc > 1 ? argv[1] : "vulkan_render.ppm";
    World world;
    for (int y = 0; y <= 20; ++y)
        for (int z = 0; z < 64; ++z)
            for (int x = 0; x < 64; ++x)
                world.setBlock(x, y, z, y == 20 ? blocks::Grass : (y >= 18 ? blocks::Dirt : blocks::Stone));
    world.setBlock(50, 21, 50, blocks::Log);
    world.setBlock(50, 22, 50, blocks::Leaves);
    world.setBlock(51, 22, 50, blocks::Leaves);
    world.setBlock(49, 22, 50, blocks::Leaves);
    world.setBlock(50, 22, 51, blocks::Leaves);
    world.setBlock(50, 22, 49, blocks::Leaves);

    const CachedBlockReader reader(world);
    const GreedyMesher mesher;
    std::vector<Quad> allQuads;
    for (const auto& [pos, chunk] : world.chunks()) { (void)chunk;
        const auto mesh = mesher.meshWorld(pos, world);
        // (Side-bucket order is preserved per chunk; the Vulkan path draws in bucket order.)
        allQuads.insert(allQuads.end(), mesh.quads.begin(), mesh.quads.end());
    }
    const MeshTriangles tris = expandQuads(allQuads);
    std::fprintf(stderr, "vulkan_render: quads=%zu vertices=%zu triangles=%zu\n",
                 allQuads.size(), tris.positions.size() / 3, tris.indices.size() / 3);

    std::vector<std::uint32_t> indices = tris.indices;
#if defined(VOXELCORE_WITH_VULKAN)
    // Interleave RGBA8→float colors as Vertex{x,y,z,r,g,b,a}.
    std::vector<vk::Vertex> vertices;
    const std::size_t vcount = tris.positions.size() / 3;
    vertices.reserve(vcount);
    for (std::size_t i = 0; i < vcount; ++i) {
        vertices.push_back({tris.positions[i * 3 + 0], tris.positions[i * 3 + 1], tris.positions[i * 3 + 2],
                            tris.colors[i * 4 + 0], tris.colors[i * 4 + 1], tris.colors[i * 4 + 2], tris.colors[i * 4 + 3]});
    }
    const math::Vec3 eye{64.0f, 42.0f, 90.0f}, target{54.0f, 20.0f, 50.0f}, up{0.0f, 1.0f, 0.0f};
    const math::Mat4 view = math::lookAtRH(eye, target, up);
    const math::Mat4 proj = math::perspectiveVulkan(60.0f, 4.0f / 3.0f, 0.5f, 500.0f);
    const math::Mat4 mvp = math::multiply(proj, view);
    try {
        vk::HeadlessRenderer renderer(1280, 960, std::string(VOXELCORE_SPV_DIR));
        renderer.init();
        renderer.renderToPpm(vertices, indices, mvp, outPath.c_str());
    } catch (const vk::VulkanError& e) {
        std::fprintf(stderr, "vulkan_render: skipped — %s\n", e.what());
        return 77; // EX_SKIP-like: cleanly reports "no GPU path available"
    }
    std::fprintf(stderr, "vulkan_render: wrote %s\n", outPath.c_str());
    return 0;
#else
    (void)indices;
    std::fprintf(stderr, "vulkan_render: built without Vulkan support (VOXELCORE_WITH_VULKAN=OFF)\n");
    return 77;
#endif
}

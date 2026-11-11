// voxelcore CLI — headless verification driver:
//   voxelcore gen  <world-dir> [seed] [chunks]      generate terrain, print stats
//   voxelcore mesh <world-dir> [seed] [chunks]      generate + greedy-mesh, print stats
//   voxelcore render <out.ppm> [seed] [chunks] [px] render isometric view to PPM
//   voxelcore lod  <world-dir> [seed] [chunks]      bake LOD level 2 and print stats
#include "../../engine/world/world.hpp"
#include "../../engine/terrain/terrain_gen.hpp"
#include "../../engine/meshing/mesher.hpp"
#include "../../engine/lod/heightfield_lod.hpp"
#include "../../engine/rendering/software_renderer.hpp"
#include "../../engine/jobs/job_system.hpp"
#include "../../engine/core/timing.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>

using namespace vc;

static World generateWorld(std::uint64_t seed, int radiusChunks) {
    TerrainConfig cfg; cfg.seed = seed;
    TerrainGenerator gen(cfg);
    World world;
    for (int cz = -radiusChunks; cz <= radiusChunks; ++cz)
        for (int cx = -radiusChunks; cx <= radiusChunks; ++cx)
            gen.generate(world.getOrCreate({cx, cz}));
    return world;
}

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage: voxelcore <gen|mesh|render|lod> ...\n"); return 2; }
    const char* cmd = argv[1];
    const std::uint64_t seed = (argc > 3) ? std::strtoull(argv[3], nullptr, 10) : 1337;
    const int chunks = (argc > 4) ? std::atoi(argv[4]) : 1; // radius in chunks for gen/mesh/lod; ignored by render's px arg

    if (std::strcmp(cmd, "gen") == 0) {
        Stopwatch sw; sw.reset();
        World w = generateWorld(seed, chunks);
        std::printf("generated %zu chunks (r=%d) seed=%llu in %.1f ms; approx %.2f MB\n",
                    w.chunkCount(), chunks, (unsigned long long)seed, sw.millis(), w.approxBytes() / 1048576.0);
        return 0;
    }
    if (std::strcmp(cmd, "mesh") == 0) {
        Stopwatch sw; sw.reset();
        World w = generateWorld(seed, chunks);
        const double genMs = sw.millis();
        GreedyMesher mesher;
        sw.reset();
        MeshStats total;
        for (const auto& [pos, c] : w.chunks()) {
            (void)c;
            auto r = mesher.meshWorld(pos, w);
            total.quads += r.stats.quads; total.vertices += r.stats.vertices; total.indices += r.stats.indices;
            total.faceArea += r.stats.faceArea; total.naiveFaces += r.stats.naiveFaces;
        }
        const double meshMs = sw.millis();
        const double ratio = total.naiveFaces ? (100.0 * total.quads / total.naiveFaces) : 0.0;
        std::printf("chunks=%zu gen=%.1fms mesh=%.1fms\n", w.chunkCount(), genMs, meshMs);
        std::printf("naiveFaces=%llu quads=%llu (%.1f%% of naive) vertices=%llu indices=%llu\n",
                    (unsigned long long)total.naiveFaces, (unsigned long long)total.quads, ratio,
                    (unsigned long long)total.vertices, (unsigned long long)total.indices);
        std::printf("faceArea==naiveFaces: %s\n", total.faceArea == total.naiveFaces ? "PASS" : "FAIL");
        return total.faceArea == total.naiveFaces ? 0 : 1;
    }
    if (std::strcmp(cmd, "render") == 0) {
        const char* out = (argc > 2) ? argv[2] : "voxelcore.ppm";
        const int px = (argc > 5) ? std::atoi(argv[5]) : 640;
        Stopwatch sw; sw.reset();
        World w = generateWorld(seed, 1);
        std::fprintf(stderr, "gen %.1f ms\n", sw.millis());
        GreedyMesher mesher;
        std::vector<std::pair<ChunkPos, GreedyMesher::Result>> meshes;
        for (const auto& [pos, c] : w.chunks()) { (void)c; meshes.push_back({pos, mesher.meshWorld(pos, w)}); }
        SoftwareRenderer r;
        r.resize(px, static_cast<int>(px * 9.0 / 16.0));
        Camera& cam = r.camera;
        cam.eyeX = 24; cam.eyeY = 46; cam.eyeZ = -34;
        cam.targetX = 8; cam.targetY = 20; cam.targetZ = 8;
        cam.fovDeg = 68; cam.aspect = 16.0f/9.0f;
        r.clear(0xFF8AB4E0u); // sky blue
        for (const auto& [pos, m] : meshes) r.drawQuads(m.quads, static_cast<float>(pos.x*16), static_cast<float>(pos.z*16));
        r.writePPM(out);
        std::fprintf(stderr, "wrote %s in %.1f ms total\n", out, sw.millis());
        return 0;
    }
    if (std::strcmp(cmd, "lod") == 0) {
        World w = generateWorld(seed, chunks ? chunks : 1);
        Stopwatch sw; sw.reset();
        const int level = 2;
        auto tile = HeightfieldLod::bake(w, 0, 0, level);
        auto mesh = HeightfieldLod::mesh(tile, 0, 0, level);
        std::printf("LOD level %d (%dm cells): %zu columns baked in %.1f ms; mesh %zu vertices, %zu triangles\n",
                    level, 1 << level, tile.size(), sw.millis(), mesh.positions.size() / 3, mesh.indices.size() / 3);
        return 0;
    }
    std::fprintf(stderr, "unknown command %s\n", cmd);
    return 2;
}

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
#include "../../engine/storage/chunk_io.hpp"
#include <filesystem>
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
    if (argc < 2) { std::fprintf(stderr, "usage: voxelcore <gen|mesh|render|lod|saveload> ...\n"); return 2; }
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
        World w = generateWorld(seed, chunks);
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
    if (std::strcmp(cmd, "saveload") == 0) {
        const char* out = (argc > 2) ? argv[2] : "/tmp/voxelcore_cli_region";
        std::filesystem::create_directories(out);
        const std::string path = std::string(out) + "/r.0.0.mca";
        std::filesystem::remove(path);
        TerrainConfig cfg; cfg.seed = seed; TerrainGenerator gen(cfg);
        Chunk chunk({0, 0}); gen.generate(chunk);
        anvil::RegionFile region(path, true);
        if (!chunk_io::saveChunk(region, chunk, 0, 0)) { std::fprintf(stderr, "save failed\n"); return 1; }
        region.flush(1700000000u);
        anvil::RegionFile regionBack(path, false);
        auto back = chunk_io::loadChunk(regionBack, 0, 0);
        if (!back) { std::fprintf(stderr, "load failed\n"); return 1; }
        bool identical = true;
        for (int y = 0; y < kChunkHeight; ++y)
            for (int z = 0; z < 16; ++z)
                for (int x = 0; x < 16; ++x)
                    if (chunk.getBlock(x, y, z) != back->getBlock(x, y, z)) identical = false;
        const auto sz = std::filesystem::file_size(path);
        std::printf("saved+reloaded chunk of seed %llu: %s (region %llu bytes)\n",
                    (unsigned long long)seed, identical ? "IDENTICAL" : "MISMATCH", (unsigned long long)sz);
        return identical ? 0 : 1;
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

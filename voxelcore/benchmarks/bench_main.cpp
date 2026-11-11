// PROJECT VOXELCORE — micro-benchmark harness (no external deps; CSV output).
#include "../engine/core/timing.hpp"
#include "../engine/core/packed_storage.hpp"
#include "../engine/core/paletted_section.hpp"
#include "../engine/terrain/terrain_gen.hpp"
#include "../engine/world/world.hpp"
#include "../engine/meshing/mesher.hpp"
#include "../engine/jobs/job_system.hpp"
#include <cstdio>
#include <vector>
#include <functional>
#include <string>

using namespace vc;

struct Bench { std::string name; int iterations; std::function<void()> fn; };

int main() {
    std::printf("benchmark,iterations,total_ms,per_op_us\n");
    auto run = [](const std::string& name, int iters, const std::function<void()>& fn) {
        // warmup
        for (int i = 0; i < (iters > 2 ? 2 : 1); ++i) fn();
        Stopwatch sw; sw.reset();
        for (int i = 0; i < iters; ++i) fn();
        const double total = sw.millis();
        std::printf("%s,%d,%.3f,%.3f\n", name.c_str(), iters, total, total * 1000.0 / static_cast<double>(iters));
        std::fflush(stdout);
    };

    run("packed_storage_set_4096", 2000, [] {
        PackedArray a(8, 4096);
        for (std::size_t i = 0; i < 4096; ++i) a.set(i, i * 7 + 1);
    });
    run("packed_storage_get_4096", 2000, [] {
        PackedArray a(8, 4096);
        for (std::size_t i = 0; i < 4096; ++i) a.set(i, i * 7 + 1);
        std::uint64_t acc = 0;
        for (std::size_t i = 0; i < 4096; ++i) acc += a.get(i);
        if (acc == 0xDEADBEEF) std::fprintf(stderr, "!\n");
    });
    run("paletted_section_set_fill", 500, [] {
        PalettedSection s;
        for (std::size_t i = 0; i < kSectionVolume; ++i) s.set(i, static_cast<BlockId>(1 + (i * 2654435761u) % 9));
    });
    run("terrain_gen_chunk", 20, [] {
        TerrainConfig cfg; cfg.seed = 1234;
        TerrainGenerator gen(cfg);
        World w;
        gen.generate(w.getOrCreate({0, 0}));
    });
    run("greedy_mesh_generated_chunk", 20, [] {
        TerrainConfig cfg; cfg.seed = 1234;
        TerrainGenerator gen(cfg);
        World w;
        gen.generate(w.getOrCreate({0, 0}));
        GreedyMesher mesher;
        auto r = mesher.meshWorld({0, 0}, w);
        if (r.quads.empty()) std::fprintf(stderr, "empty mesh!\n");
    });
    run("job_system_parallel_for_1M", 20, [] {
        JobSystem jobs(4);
        std::atomic<int> sink{0};
        jobs.parallelFor(1000000, 4096, [&](std::size_t i) { sink.fetch_add(1, std::memory_order_relaxed); (void)i; });
    });
    return 0;
}

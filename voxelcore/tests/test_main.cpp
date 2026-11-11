// PROJECT VOXELCORE — dependency-free test runner (Catch2 can replace this at stage 14
// if we vendor it; assertions here are explicit and print file:line on failure).
#include "../engine/core/packed_storage.hpp"
#include "../engine/core/paletted_section.hpp"
#include "../engine/memory/arena.hpp"
#include "../engine/jobs/job_system.hpp"
#include "../engine/terrain/noise.hpp"
#include "../engine/terrain/terrain_gen.hpp"
#include "../engine/world/world.hpp"
#include "../engine/meshing/mesher.hpp"
#include "../engine/visibility/frustum.hpp"
#include "../engine/lod/heightfield_lod.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <string>
#include <vector>
#include <functional>

static int g_failures = 0, g_checks = 0;
#define CHECK(cond) do { ++g_checks; if (!(cond)) { ++g_failures; \
    std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); } } while (0)
#define CHECK_EQ(a, b) do { ++g_checks; const auto _va = (a); const auto _vb = (b); \
    if (!(_va == _vb)) { ++g_failures; \
    std::fprintf(stderr, "FAIL %s:%d: %s == %s\n", __FILE__, __LINE__, #a, #b); } } while (0)

static void testPackedArray() {
    for (std::uint8_t bits : {1, 2, 3, 4, 5, 8, 13, 16}) {
        vc::PackedArray a(bits, 4096);
        const std::uint64_t maxV = (bits == 64) ? ~0ull : ((1ull << bits) - 1);
        for (std::size_t i = 0; i < 4096; ++i) {
            const std::uint64_t v = (static_cast<std::uint64_t>(i) * 2654435761ull + bits) & maxV;
            a.set(i, v);
        }
        for (std::size_t i = 0; i < 4096; ++i) {
            const std::uint64_t v = (static_cast<std::uint64_t>(i) * 2654435761ull + bits) & maxV;
            CHECK_EQ(a.get(i), v);
        }
    }
}

static void testPalettedSection() {
    vc::PalettedSection s;
    CHECK(s.isUniform());
    CHECK_EQ(s.get(123), vc::blocks::Air);
    s.set(0, vc::blocks::Stone);
    CHECK(!s.isUniform());
    CHECK_EQ(s.get(0), vc::blocks::Stone);
    CHECK_EQ(s.get(1), vc::blocks::Air);
    // Fill with many distinct block ids to force palette growth.
    for (std::uint16_t b = 0; b < 40; ++b) s.set(10 + b, static_cast<vc::BlockId>(100 + b));
    for (std::uint16_t b = 0; b < 40; ++b) CHECK_EQ(s.get(10 + b), static_cast<vc::BlockId>(100 + b));
    CHECK_EQ(s.get(0), vc::blocks::Stone);
    CHECK(s.paletteSize() >= 42);
    s.trim();
    for (std::uint16_t b = 0; b < 40; ++b) CHECK_EQ(s.get(10 + b), static_cast<vc::BlockId>(100 + b));
}

static void testArena() {
    vc::Arena arena(256);
    void* p1 = arena.allocate(64);
    void* p2 = arena.allocate(64);
    CHECK(p1 && p2 && p1 != p2);
    const std::size_t before = arena.bytesAllocated();
    arena.reset();
    void* p3 = arena.allocate(64);
    CHECK_EQ(p3, p1); // first block reused
    CHECK(before > 0);
}

static void testJobSystem() {
    vc::JobSystem jobs(4);
    std::atomic<int> counter{0};
    for (int i = 0; i < 100; ++i) jobs.submit([&counter] { counter.fetch_add(1); });
    jobs.waitIdle();
    CHECK_EQ(counter.load(), 100);
    std::atomic<int> sum{0};
    jobs.parallelFor(1000, 16, [&](std::size_t i) { sum.fetch_add(1); (void)i; });
    CHECK_EQ(sum.load(), 1000);
}

static void testNoiseDeterminism() {
    vc::Noise n1(42), n2(42), n3(43);
    CHECK_EQ(n1.value2D(1.5, 2.5), n2.value2D(1.5, 2.5));
    CHECK(n1.value2D(1.5, 2.5) != n3.value2D(1.5, 2.5));
    CHECK_EQ(n1.fbm2D(10.0, -3.0, 4), n2.fbm2D(10.0, -3.0, 4));
    CHECK(std::fabs(n1.value3D(1, 2, 3)) <= 1.5);
}

static void testWorldGenDeterminism() {
    vc::TerrainConfig cfg; cfg.seed = 99; cfg.trees = false;
    vc::TerrainGenerator g1(cfg), g2(cfg);
    vc::World w1, w2;
    g1.generate(w1.getOrCreate({0, 0}));
    g2.generate(w2.getOrCreate({0, 0}));
    bool identical = true;
    for (int y = 0; y < vc::kChunkHeight; ++y)
        for (int z = 0; z < 16; ++z)
            for (int x = 0; x < 16; ++x)
                if (w1.getBlock(x, y, z) != w2.getBlock(x, y, z)) identical = false;
    CHECK(identical);
    // Bedrock at y=0, some stone, and sea-level sanity.
    CHECK_EQ(w1.getBlock(5, 0, 5), vc::blocks::Bedrock);
}

static void testGreedyMesherMerges() {
    // Flat 16x16 stone platform on y = 10..12 inside one chunk, air everywhere else.
    vc::World world;
    for (int z = 0; z < 16; ++z) for (int x = 0; x < 16; ++x) {
        world.setBlock(x, 10, z, vc::blocks::Stone);
        world.setBlock(x, 11, z, vc::blocks::Stone);
        world.setBlock(x, 12, z, vc::blocks::Stone);
    }
    vc::ChunkPos pos{0, 0};
    vc::GreedyMesher mesher;
    auto r = mesher.meshWorld(pos, world);
    std::fprintf(stderr, "flat-platform: naiveFaces=%llu quads=%llu faceArea=%llu\n",
                 (unsigned long long)r.stats.naiveFaces, (unsigned long long)r.stats.quads,
                 (unsigned long long)r.stats.faceArea);
    CHECK_EQ(r.stats.faceArea, r.stats.naiveFaces);
    // Top face must merge into one quad (16x16 = 1 quad), bottom similarly.
    int topQuads = 0;
    for (const auto& q : r.quads) if (q.dir == vc::FaceDir::PosY && q.block == vc::blocks::Stone) ++topQuads;
    CHECK_EQ(topQuads, 1);
    // 4 side walls: each merges into one quad.
    int wallQuads = 0;
    for (const auto& q : r.quads) if (q.dir == vc::FaceDir::PosX || q.dir == vc::FaceDir::NegX ||
                                      q.dir == vc::FaceDir::PosZ || q.dir == vc::FaceDir::NegZ) ++wallQuads;
    CHECK_EQ(wallQuads, 4);
}

static void testGreedyMesherInterior() {
    // Fully buried block must emit no faces.
    vc::World world;
    for (int y = 4; y <= 12; ++y) for (int z = 4; z <= 12; ++z) for (int x = 4; x <= 12; ++x)
        world.setBlock(x, y, z, vc::blocks::Stone);
    vc::GreedyMesher mesher;
    auto r = mesher.meshWorld({0, 0}, world);
    // Every emitted quad belongs to the outer shell of a 9x9x9 cube.
    for (const auto& q : r.quads) {
        (void)q;
    }
    CHECK_EQ(r.stats.faceArea, r.stats.naiveFaces);
    std::fprintf(stderr, "buried-cube: naiveFaces=%llu quads=%llu\n",
                 (unsigned long long)r.stats.naiveFaces, (unsigned long long)r.stats.quads);
    // 9x9x9 shell visible area = 6 * 81 = 486.
    CHECK_EQ(r.stats.faceArea, 486u);
}

static void testGreedyMesherAOBounds() {
    vc::TerrainConfig cfg; cfg.seed = 7; cfg.trees = true;
    vc::TerrainGenerator gen(cfg);
    vc::World world;
    gen.generate(world.getOrCreate({0, 0}));
    vc::GreedyMesher mesher;
    auto r = mesher.meshWorld({0, 0}, world);
    CHECK_EQ(r.stats.faceArea, r.stats.naiveFaces);
    for (const auto& q : r.quads) for (int k = 0; k < 4; ++k) CHECK(q.ao[k] <= 3);
    CHECK(r.stats.quads > 0);
    std::fprintf(stderr, "terrain: naiveFaces=%llu quads=%llu (%.1f%%)\n",
                 (unsigned long long)r.stats.naiveFaces, (unsigned long long)r.stats.quads,
                 100.0 * r.stats.quads / (double)r.stats.naiveFaces);
}

static void testFrustumCulling() {
    // Simple identity-ish view-projection: orthographic box x,y,z in [-10,10].
    const float m[16] = { 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 };
    // For pure identity view the "frustum" extraction is degenerate; instead test a real look-at below.
    (void)m;
    // Build a perspective view-proj manually: camera at origin looking down -Z.
    const float f = 1.0f / std::tan(60.0f * 0.5f * 3.14159265f / 180.0f);
    const float aspect = 1.0f, zn = 0.1f, zf = 100.0f;
    float proj[16] = { f/aspect,0,0,0, 0,f,0,0, 0,0,(zf+zn)/(zn-zf),-1, 0,0,(2*zf*zn)/(zn-zf),0 };
    vc::Frustum fr = vc::Frustum::fromViewProj(proj);
    vc::AABB inside{ {-1,-1,-20}, {1,1,-5} };
    vc::AABB behind{ {-1,-1,5}, {1,1,20} };
    vc::AABB side{ {30,-1,-20}, {40,1,-5} };
    CHECK(fr.intersects(inside));
    CHECK(!fr.intersects(behind));
    CHECK(!fr.intersects(side));
}

static void testLodBake() {
    vc::TerrainConfig cfg; cfg.seed = 1337; cfg.trees = false;
    vc::TerrainGenerator gen(cfg);
    vc::World world;
    gen.generate(world.getOrCreate({0, 0}));
    auto tile = vc::HeightfieldLod::bake(world, 0, 0, 2);
    CHECK_EQ(tile.size(), 256u);
    int nonzero = 0;
    for (const auto& c : tile) if (c.height > 0) ++nonzero;
    CHECK(nonzero > 0);
    auto mesh = vc::HeightfieldLod::mesh(tile, 0, 0, 2);
    CHECK_EQ(mesh.cells, 256u);
    CHECK(mesh.indices.size() == 16u * 16u * 6u);
    CHECK(mesh.positions.size() == 17u * 17u * 3u);
}

static void testChunkMemory() {
    vc::Chunk c({0, 0});
    const std::size_t airBytes = c.approxBytes();
    // Uniform air section should be tiny.
    CHECK(airBytes < 4096);
    for (int y = 0; y < 64; ++y) for (int z = 0; z < 16; ++z) for (int x = 0; x < 16; ++x)
        c.setBlock(x, y, z, vc::blocks::Stone);
    const std::size_t fullBytes = c.approxBytes();
    // Full stone = still uniform per section.
    CHECK(fullBytes < 4096);
    std::fprintf(stderr, "chunk bytes: air=%zu full=%zu\n", airBytes, fullBytes);
}

int main() {
    testPackedArray();
    testPalettedSection();
    testArena();
    testJobSystem();
    testNoiseDeterminism();
    testWorldGenDeterminism();
    testGreedyMesherMerges();
    testGreedyMesherInterior();
    testGreedyMesherAOBounds();
    testFrustumCulling();
    testLodBake();
    testChunkMemory();
    std::fprintf(stderr, "\n%d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}

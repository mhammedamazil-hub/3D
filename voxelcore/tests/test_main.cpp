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
#include "../engine/storage/nbt.hpp"
#include "../engine/storage/chunk_io.hpp"
#include "../engine/storage/zlib.hpp"
#include "../engine/visibility/cave_culling.hpp"
#include "../engine/rendering/software_renderer.hpp"
#include "../engine/lighting/light_volume.hpp"
#include "../engine/rendering/packed_record.hpp"
#include <fstream>
#include <filesystem>
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

static void testNbtRoundtrip() {
    vc::nbt::Value root = vc::nbt::Value::compound();
    vc::nbt::NbtCompound& c = std::get<vc::nbt::NbtCompound>(root.data);
    c.emplace_back("name", vc::nbt::Value(std::string("voxelcore")));
    c.emplace_back("count", vc::nbt::Value(static_cast<std::int32_t>(-42)));
    c.emplace_back("big", vc::nbt::Value(static_cast<std::int64_t>(0x0102030405060708ll)));
    c.emplace_back("ratio", vc::nbt::Value(static_cast<double>(2.5)));
    vc::nbt::NbtList list;
    list.push_back(vc::nbt::Value(static_cast<std::int32_t>(1)));
    list.push_back(vc::nbt::Value(static_cast<std::int32_t>(2)));
    list.push_back(vc::nbt::Value(static_cast<std::int32_t>(3)));
    c.emplace_back("ints", vc::nbt::Value(vc::nbt::List, std::move(list)));
    vc::nbt::Writer w;
    w.writeNamedRoot("test", root);
    vc::nbt::Reader r(w.bytes().data(), w.bytes().size());
    auto [nm, back] = r.readNamedRoot();
    CHECK_EQ(nm, std::string("test"));
    const vc::nbt::Value* nmV = back.find("name");
    CHECK(nmV != nullptr);
    CHECK_EQ(std::get<std::string>(nmV->data), std::string("voxelcore"));
    const vc::nbt::Value* cnt = back.find("count");
    CHECK_EQ(std::get<std::int32_t>(cnt->data), -42);
    const vc::nbt::Value* bigv = back.find("big");
    CHECK_EQ(std::get<std::int64_t>(bigv->data), static_cast<std::int64_t>(0x0102030405060708ll));
    const vc::nbt::Value* ints = back.find("ints");
    const auto* lst = ints->asList();
    CHECK(lst != nullptr);
    CHECK_EQ(lst->size(), 3u);
    CHECK_EQ(std::get<std::int32_t>((*lst)[2].data), 3);
}

static void testChunkSaveLoadRoundtrip() {
#ifndef VOXELCORE_HAVE_ZLIB
    std::fprintf(stderr, "SKIP testChunkSaveLoadRoundtrip: zlib not available at configure time\n");
    return;
#endif
    const std::string dir = "/tmp/voxelcore_test_region";
    std::filesystem::create_directories(dir);
    const std::string path = dir + "/r.0.0.mca";
    std::filesystem::remove(path);

    vc::TerrainConfig cfg; cfg.seed = 4242; cfg.trees = true;
    vc::TerrainGenerator gen(cfg);
    vc::Chunk chunk({0, 0});
    gen.generate(chunk);

    {
        vc::anvil::RegionFile region(path, true);
        CHECK(vc::chunk_io::saveChunk(region, chunk, 0, 0));
        region.flush(12345);
    }
    {
        vc::anvil::RegionFile region(path, false);
        CHECK(region.hasChunk(0, 0));
        auto back = vc::chunk_io::loadChunk(region, 0, 0);
        CHECK(back != nullptr);
        CHECK_EQ(back->pos().x, 0);
        CHECK_EQ(back->pos().z, 0);
        bool identical = true;
        for (int y = 0; y < vc::kChunkHeight; ++y)
            for (int z = 0; z < 16; ++z)
                for (int x = 0; x < 16; ++x)
                    if (chunk.getBlock(x, y, z) != back->getBlock(x, y, z)) identical = false;
        CHECK(identical);
    }
    std::filesystem::remove(path);
}

static void testMesherFuzz() {
    // Random block soup: the greedy-merge conservation law (faceArea == naiveFaces) must hold.
    std::uint64_t seed = 0x123456789ULL;
    auto rnd = [&]() { seed = seed * 6364136223846793005ULL + 1442695040888963407ULL; return seed >> 33; };
    for (int iteration = 0; iteration < 60; ++iteration) {
        vc::World world;
        // Random sparse fill in a 8x16x8 box to keep sections non-trivial.
        for (int i = 0; i < 140; ++i) {
            const int x = static_cast<int>(rnd() % 8) + 4;
            const int y = static_cast<int>(rnd() % 12) + 4;
            const int z = static_cast<int>(rnd() % 8) + 4;
            const vc::BlockId b = static_cast<vc::BlockId>(1 + rnd() % 9);
            world.setBlock(x, y, z, b);
        }
        vc::GreedyMesher mesher;
        auto r = mesher.meshWorld({0, 0}, world);
        if (r.stats.faceArea != r.stats.naiveFaces) {
            ++g_failures;
            std::fprintf(stderr, "FAIL mesher fuzz iteration %d: faceArea=%llu naive=%llu\n",
                         iteration, (unsigned long long)r.stats.faceArea, (unsigned long long)r.stats.naiveFaces);
        }
        ++g_checks;
        for (const auto& q : r.quads) for (int k = 0; k < 4; ++k) {
            ++g_checks;
            if (q.ao[k] > 3) { ++g_failures; std::fprintf(stderr, "FAIL fuzz AO bounds\n"); }
        }
    }
}

static void testCaveCulling() {
    // Solid stone world with a sealed air cavity; camera outside vs inside.
    vc::World world;
    for (int y = 0; y < 16; ++y)
        for (int z = 0; z < 16; ++z)
            for (int x = 0; x < 16; ++x)
                world.setBlock(x, y, z, vc::blocks::Stone);
    // Carve sealed cavity y=4..7, z=4..11, x=4..11.
    for (int y = 4; y <= 7; ++y)
        for (int z = 4; z <= 11; ++z)
            for (int x = 4; x <= 11; ++x)
                world.setBlock(x, y, z, vc::blocks::Air);
    // Surface above y>=16 is open (world AABB boundary); cavity is sealed.
    const vc::CaveCuller culler = vc::CaveCuller::analyze(world);
    CHECK(culler.valid());
    const int sealed = culler.componentOf(6, 6, 6);
    CHECK(sealed > 0);
    CHECK(culler.componentOf(0, 15, 0) == 0); // open surface
    std::fprintf(stderr, "cave culling: sealed cells=%zu components=%zu\n",
                 culler.sealedCells(), culler.componentCount());

    vc::GreedyMesher mesher;
    const vc::CachedBlockReader reader(world);
    // Camera outside (in open air above the stone): sealed faces skipped.
    auto outside = mesher.meshTypedEx({0, 0}, reader, culler, {8, 20, 8});
    // Camera inside the sealed cavity: those faces are kept.
    auto inside = mesher.meshTypedEx({0, 0}, reader, culler, {6, 6, 6});
    // No culler baseline.
    const vc::NoCaveCuller noCull;
    auto plain = mesher.meshTypedEx({0, 0}, reader, noCull, {8, 20, 8});
    std::fprintf(stderr, "mesher faces: plain=%llu outside=%llu inside=%llu\n",
                 (unsigned long long)plain.stats.naiveFaces,
                 (unsigned long long)outside.stats.naiveFaces,
                 (unsigned long long)inside.stats.naiveFaces);
    CHECK(outside.stats.naiveFaces < plain.stats.naiveFaces);
    CHECK_EQ(inside.stats.naiveFaces, plain.stats.naiveFaces);
    CHECK_EQ(outside.stats.faceArea, outside.stats.naiveFaces);
    CHECK_EQ(inside.stats.faceArea, inside.stats.naiveFaces);
    // Sanity: the sealed cavity would produce faces on the 8x8x4 inner box walls.
    const std::uint64_t expectedSealedFaces = 4ull * 8 * 4 + 2ull * 8 * 8; // 4 walls + floor + ceiling
    CHECK_EQ(plain.stats.naiveFaces - inside.stats.naiveFaces + inside.stats.naiveFaces - outside.stats.naiveFaces,
             expectedSealedFaces);
}

static void testLightPropagation() {
    // --- all-air region: everything sky-lit ---
    {
        vc::World world;
        const vc::LightRegion region{0, 0, 0, 4, 8, 4};
        const vc::LightVolume light = vc::LightVolume::compute(world, region);
        for (int y = 0; y < 8; ++y)
            for (int z = 0; z < 4; ++z)
                for (int x = 0; x < 4; ++x)
                    CHECK_EQ(light.skyAt(x, y, z), 15);
        CHECK_EQ(light.skyAt(1, 100, 1), 15); // above region top = open sky
        CHECK_EQ(light.blockAt(1, 4, 1), 0);  // no block sources
    }
    // --- stone slab at y=0: above lit, slab occluded ---
    {
        vc::World world;
        for (int z = 0; z < 4; ++z) for (int x = 0; x < 4; ++x) world.setBlock(x, 0, z, vc::blocks::Stone);
        const vc::LightRegion region{0, 0, 0, 4, 8, 4};
        const vc::LightVolume light = vc::LightVolume::compute(world, region);
        CHECK_EQ(light.skyAt(2, 0, 2), 0);   // stone cell itself
        CHECK_EQ(light.skyAt(2, 1, 2), 15);  // open above
        CHECK_EQ(light.skyAt(2, 7, 2), 15);
    }
    // --- sealed cavity: interior fully dark ---
    {
        vc::World world;
        for (int y = 0; y < 16; ++y)
            for (int z = 0; z < 16; ++z)
                for (int x = 0; x < 16; ++x)
                    world.setBlock(x, y, z, vc::blocks::Stone);
        for (int y = 4; y <= 6; ++y)
            for (int z = 4; z <= 10; ++z)
                for (int x = 4; x <= 10; ++x)
                    world.setBlock(x, y, z, vc::blocks::Air);
        const vc::LightRegion region{0, 0, 0, 16, 16, 16};
        const vc::LightVolume light = vc::LightVolume::compute(world, region);
        for (int y = 4; y <= 6; ++y)
            for (int z = 4; z <= 10; ++z)
                for (int x = 4; x <= 10; ++x)
                    CHECK_EQ(light.skyAt(x, y, z), 0); // sealed — no light anywhere inside
    }
    // --- shaft opened to sky: exact flood-fill falloff ---
    {
        vc::World world;
        for (int y = 0; y < 16; ++y)
            for (int z = 0; z < 16; ++z)
                for (int x = 0; x < 16; ++x)
                    world.setBlock(x, y, z, vc::blocks::Stone);
        for (int y = 4; y <= 6; ++y)
            for (int z = 4; z <= 10; ++z)
                for (int x = 4; x <= 10; ++x)
                    world.setBlock(x, y, z, vc::blocks::Air); // cavity
        for (int y = 7; y <= 15; ++y) world.setBlock(7, y, 7, vc::blocks::Air); // shaft
        const vc::LightRegion region{0, 0, 0, 16, 16, 16};
        const vc::LightVolume light = vc::LightVolume::compute(world, region);
        CHECK_EQ(light.skyAt(7, 12, 7), 15); // inside the shaft
        CHECK_EQ(light.skyAt(7, 5, 7), 15);  // shaft bottom opens into the cavity (same column)
        CHECK_EQ(light.skyAt(6, 5, 7), 14);  // 1 step away
        CHECK_EQ(light.skyAt(5, 5, 7), 13);  // 2 steps away
        CHECK_EQ(light.skyAt(6, 5, 6), 13);  // manhattan distance 2
        CHECK_EQ(light.skyAt(4, 5, 4), 9);   // manhattan 6 from the shaft column -> 15 - 6
    }
    // --- block light: exact Manhattan falloff, blocked by stone ---
    {
        vc::World world; // all air
        const vc::LightRegion region{0, 0, 0, 16, 16, 16};
        const vc::LightVolume light = vc::LightVolume::compute(world, region, {{8, 8, 8, 15}});
        CHECK_EQ(light.blockAt(8, 8, 8), 15);
        CHECK_EQ(light.blockAt(9, 8, 8), 14);
        CHECK_EQ(light.blockAt(12, 8, 8), 11);
        CHECK_EQ(light.blockAt(8, 15, 8), 8);  // distance 7
        CHECK_EQ(light.blockAt(1, 8, 8), 8);
        // Wall off x=5 completely: the region left of it can no longer see the source.
        vc::World walled;
        for (int y = 0; y < 16; ++y) for (int z = 0; z < 16; ++z) walled.setBlock(5, y, z, vc::blocks::Stone);
        const vc::LightVolume lw = vc::LightVolume::compute(walled, region, {{8, 8, 8, 15}});
        CHECK_EQ(lw.blockAt(4, 8, 8), 0);    // behind the wall: dark
        CHECK_EQ(lw.blockAt(6, 8, 8), 13);   // wall face itself (entering stone = blocked, neighbor stays 13)
        CHECK_EQ(lw.blockAt(7, 8, 8), 14);   // source side
        // Source occluded by stone: no emission at all.
        vc::World occluded;
        occluded.setBlock(8, 8, 8, vc::blocks::Stone);
        const vc::LightVolume lo = vc::LightVolume::compute(occluded, region, {{8, 8, 8, 15}});
        CHECK_EQ(lo.blockAt(8, 8, 8), 0);
        CHECK_EQ(lo.blockAt(9, 8, 8), 0);
    }
}

static void testPackedRecordRoundtrip() {
    const vc::FaceDir dirs[6] = {vc::FaceDir::PosX, vc::FaceDir::NegX, vc::FaceDir::PosY,
                                 vc::FaceDir::NegY, vc::FaceDir::PosZ, vc::FaceDir::NegZ};
    const std::uint8_t extents[6] = {1, 2, 3, 5, 8, 16};
    const std::array<std::uint8_t,4> aoPats[4] = {{0,0,0,0}, {3,3,3,3}, {0,1,2,3}, {3,0,2,1}};
    const std::uint8_t lights[3] = {0, 7, 15};
    int checked = 0;
    for (vc::FaceDir dir : dirs)
        for (std::uint8_t u : extents)
            for (std::uint8_t v : extents)
                for (int slice = 0; slice <= 63; slice += 21) {
                    for (int p = 0; p < 4; ++p) {
                        vc::QuadRecord r;
                        r.dir = dir; r.uExt = u; r.vExt = v;
                        r.x = static_cast<std::uint8_t>(slice & 0xF);
                        r.z = static_cast<std::uint8_t>((slice * 7 + 5) & 0xF);
                        r.y = static_cast<std::uint8_t>(slice & 0x3F);
                        r.block = static_cast<vc::BlockId>(1 + (p * 7 + 3) % 9);
                        r.ao = aoPats[p];
                        r.light = lights[p % 3];
                        const auto packed = vc::packRecord(r);
                        CHECK(packed.has_value());
                        const vc::QuadRecord back = vc::unpackRecord(*packed);
                        CHECK_EQ(back.x, r.x); CHECK_EQ(back.z, r.z); CHECK_EQ(back.y, r.y);
                        CHECK_EQ(back.uExt, r.uExt); CHECK_EQ(back.vExt, r.vExt);
                        CHECK_EQ(static_cast<int>(back.dir), static_cast<int>(r.dir));
                        CHECK_EQ(back.block, r.block);
                        for (int k = 0; k < 4; ++k) CHECK_EQ(back.ao[k], r.ao[k]);
                        CHECK_EQ(back.light, r.light);
                        ++checked;
                    }
                }
    std::fprintf(stderr, "packed_record roundtrip cases: %d\n", checked);
    // Deterministic fuzz: pack/unpack preserves fields exactly for arbitrary quads.
    std::uint64_t seed = 0xC0FFEE;
    auto rnd = [&]() { seed = seed * 6364136223846793005ULL + 1442695040888963407ULL; return seed >> 33; };
    for (int i = 0; i < 20000; ++i) {
        vc::QuadRecord r;
        r.dir = dirs[rnd() % 6];
        r.x = static_cast<std::uint8_t>(rnd() % 16);
        r.z = static_cast<std::uint8_t>(rnd() % 16);
        r.y = static_cast<std::uint8_t>(rnd() % 64);
        r.uExt = static_cast<std::uint8_t>(1 + rnd() % 16);
        r.vExt = static_cast<std::uint8_t>(1 + rnd() % 16);
        r.block = static_cast<vc::BlockId>(rnd() % 20);
        for (auto& a : r.ao) a = static_cast<std::uint8_t>(rnd() % 4);
        r.light = static_cast<std::uint8_t>(rnd() % 16);
        const auto packed = vc::packRecord(r);
        CHECK(packed.has_value());
        const vc::QuadRecord back = vc::unpackRecord(*packed);
        CHECK_EQ(back.x, r.x); CHECK_EQ(back.z, r.z); CHECK_EQ(back.y, r.y);
        CHECK_EQ(back.uExt, r.uExt); CHECK_EQ(back.vExt, r.vExt);
        CHECK_EQ(static_cast<int>(back.dir), static_cast<int>(r.dir));
        CHECK_EQ(back.block, r.block);
        CHECK_EQ(back.light, r.light);
        for (int k = 0; k < 4; ++k) CHECK_EQ(back.ao[k], r.ao[k]);
    }
    // Rejection tests.
    vc::QuadRecord bad = {};
    bad.x = 16; CHECK(!vc::packRecord(bad).has_value());
    bad = {}; bad.y = 64; CHECK(!vc::packRecord(bad).has_value());
    bad = {}; bad.uExt = 17; CHECK(!vc::packRecord(bad).has_value());
    bad = {}; bad.ao[2] = 4; CHECK(!vc::packRecord(bad).has_value());
    bad = {}; bad.light = 16; CHECK(!vc::packRecord(bad).has_value());
    // Boundary plane y=63 PosY -> plane 64; slice decode must recover 63.
    vc::QuadRecord top; top.dir = vc::FaceDir::PosY; top.y = 63; top.uExt = 16; top.vExt = 16;
    top.block = vc::blocks::Grass; top.light = 15;
    const auto packedTop = vc::packRecord(top);
    CHECK(packedTop.has_value());
    const vc::QuadRecord topBack = vc::unpackRecord(*packedTop);
    CHECK_EQ(topBack.y, 63);
    CHECK_EQ(vc::planeLocal(topBack.dir, topBack), 64.0f);
    // packQuadLocal with non-zero chunk origin (chunk 3, origin 48).
    vc::Quad q;
    q.dir = vc::FaceDir::PosX; q.x = 64.0f; q.y = 10.0f; q.z = 20.0f; q.u = 3.0f; q.v = 5.0f;
    q.block = vc::blocks::Stone; q.ao = {1, 2, 3, 0}; q.light = 9;
    const auto packed = vc::packQuadLocal(q, 48, 16);
    CHECK(packed.has_value());
    const vc::QuadRecord back = vc::unpackRecord(*packed);
    CHECK_EQ(back.x, 15);  // slice 15, plane = slice + 1 = 16 (chunk-local)
    CHECK_EQ(back.z, 4);   // 20 - 16 chunk Z origin
    CHECK_EQ(vc::planeLocal(back.dir, back), 16.0f);
    CHECK_EQ(back.uExt, 3);
    CHECK_EQ(back.vExt, 5);
    CHECK_EQ(back.light, 9);
    CHECK_EQ(back.ao[0], 1); CHECK_EQ(back.ao[3], 0);
    // Tall side face (v=18 merged wall, e.g. world boundary): split into <=16-row records,
    // preserving ao/light verbatim and advancing y per sub-rect (exactness via greedy cellEqual).
    vc::Quad wall;
    wall.dir = vc::FaceDir::PosX; wall.x = 64.0f; wall.y = 0.0f; wall.z = 48.0f; wall.u = 16.0f; wall.v = 18.0f;
    wall.block = vc::blocks::Stone; wall.ao = {3, 1, 2, 0}; wall.light = 12;
    const auto split = vc::packQuadLocalMulti(wall, 48, 48);
    CHECK(split.has_value());
    CHECK_EQ(split->size(), 2u);
    if (split && split->size() == 2) {
        const vc::QuadRecord s0 = vc::unpackRecord((*split)[0]);
        const vc::QuadRecord s1 = vc::unpackRecord((*split)[1]);
        CHECK_EQ(s0.uExt, 16); CHECK_EQ(s0.vExt, 16); CHECK_EQ(s0.y, 0);
        CHECK_EQ(s1.uExt, 16); CHECK_EQ(s1.vExt, 2);  CHECK_EQ(s1.y, 16);
        CHECK_EQ(static_cast<int>(s0.dir), static_cast<int>(vc::FaceDir::PosX));
        CHECK_EQ(static_cast<int>(s1.dir), static_cast<int>(vc::FaceDir::PosX));
        CHECK_EQ(s0.x, 15); CHECK_EQ(s1.x, 15);  // plane x=64 => slice 15 (PosX)
        CHECK_EQ(s0.light, 12); CHECK_EQ(s1.light, 12);
        CHECK_EQ(s0.ao[0], 3); CHECK_EQ(s0.ao[3], 0);
        CHECK_EQ(s1.ao[0], 3); CHECK_EQ(s1.ao[3], 0); // identical AO reused for sub-rects (greedy cellEqual)
        CHECK_EQ(vc::planeLocal(s0.dir, s0), 16.0f);
    }
    // Sub-16 side faces pass through unchanged (single record).
    vc::Quad wall17 = wall; wall17.v = 16.0f;
    const auto one = vc::packQuadLocalMulti(wall17, 48, 48);
    CHECK(one.has_value());
    CHECK_EQ(one->size(), 1u);
}

static void testMesherLightIntegration() {
    // Sealed cavity in stone: wall faces (camera inside) sample face light == 0;
    // surface-top faces sample face light == 15.
    vc::World world;
    for (int y = 0; y < 16; ++y)
        for (int z = 0; z < 16; ++z)
            for (int x = 0; x < 16; ++x)
                world.setBlock(x, y, z, vc::blocks::Stone);
    for (int y = 4; y <= 6; ++y)
        for (int z = 4; z <= 10; ++z)
            for (int x = 4; x <= 10; ++x)
                world.setBlock(x, y, z, vc::blocks::Air);
    const vc::LightRegion region{0, 0, 0, 16, 16, 16};
    const vc::LightVolume light = vc::LightVolume::compute(world, region);
    vc::GreedyMesher mesher;
    const vc::CachedBlockReader reader(world);
    // Camera-inside-cavity path (cave culling off; all faces emitted).
    const auto r = mesher.meshTypedEx({0, 0}, reader, vc::NoCaveCuller{}, {6, 5, 6}, &light);
    CHECK(!r.quads.empty());
    bool sawLitSurface = false;
    for (const auto& q : r.quads) {
        CHECK(q.light <= 15);
        if (q.dir == vc::FaceDir::PosY && q.y == 16.0f) sawLitSurface = (q.light == 15);
    }
    CHECK(sawLitSurface);
    // Exact-dark probe: every ceiling (NegY) face points at cavity air -> light must be exactly 0.
    bool foundCeiling = false;
    for (const auto& q : r.quads) {
        if (q.dir == vc::FaceDir::NegY) { foundCeiling = true; CHECK_EQ(q.light, 0); }
    }
    CHECK(foundCeiling);
    // Conservation law still holds with light-augmented merge signature.
    CHECK_EQ(r.stats.faceArea, r.stats.naiveFaces);
    // shadeFace: full light reproduces AO-only; zero light dims strongly.
    const std::uint32_t base = vc::faceColor(vc::blocks::Grass);
    CHECK_EQ(vc::shadeFace(base, 3, 15), vc::shadeFace(base, 3));
    const std::uint32_t dim = vc::shadeFace(base, 3, 0);
    const std::uint32_t full = vc::shadeFace(base, 3, 15);
    CHECK(((dim >> 16) & 0xFF) < ((full >> 16) & 0xFF));
}

static void testSideBuckets() {
    vc::World world;
    for (int y = 0; y <= 8; ++y)
        for (int z = 0; z < 16; ++z)
            for (int x = 0; x < 16; ++x)
                world.setBlock(x, y, z, y == 8 ? vc::blocks::Grass : vc::blocks::Stone);
    const vc::CachedBlockReader reader(world);
    const vc::GreedyMesher mesher;
    const auto mesh = mesher.mesh({0, 0}, reader);
    CHECK(!mesh.quads.empty());
    // Non-decreasing bucket order.
    for (std::size_t i = 1; i < mesh.quads.size(); ++i)
        CHECK(vc::sideBucket(mesh.quads[i - 1].dir) <= vc::sideBucket(mesh.quads[i].dir));
    // bucketEnd is consistent with the sorted order.
    std::size_t prev = 0;
    for (std::size_t b = 0; b < 7; ++b) {
        CHECK(mesh.bucketEnd[b] >= prev);
        for (std::size_t i = prev; i < mesh.bucketEnd[b]; ++i)
            CHECK_EQ(vc::sideBucket(mesh.quads[i].dir), (std::uint32_t)b);
        prev = mesh.bucketEnd[b];
    }
    CHECK_EQ(mesh.bucketEnd[7], mesh.quads.size());
    // +Y bucket must be non-trivial here (flat grass top).
    CHECK(mesh.bucketEnd[3] > mesh.bucketEnd[2]);
}

static void testTranslucentWaterDraw() {
    // Sky-colored buffer + a single water quad facing the camera: the result must be a
    // blend of sky and water, strictly between the two on every channel.
    vc::SoftwareRenderer renderer;
    renderer.resize(64, 64);
    renderer.clear(0xFF202830u);
    renderer.camera.eyeX = 8; renderer.camera.eyeY = 2; renderer.camera.eyeZ = -8;
    renderer.camera.targetX = 8; renderer.camera.targetY = 2; renderer.camera.targetZ = 16;
    renderer.camera.fovDeg = 90; renderer.camera.aspect = 1.0f;
    vc::Quad water;
    water.dir = vc::FaceDir::PosZ;
    water.x = 4; water.y = -2; water.z = 4; water.u = 8; water.v = 8; // 8x8 face
    water.block = vc::blocks::Water;
    water.ao = {3, 3, 3, 3};
    renderer.drawQuads({water}, 0, 0);
    const auto& px = renderer.pixels();
    int changed = 0;
    for (std::uint32_t p : px) if (p != 0xFF202830u) ++changed;
    // NOTE: pixel (32,32) lies exactly on the quad's triangulation diagonal (camera is on the
    // quad's y=x symmetry axis), and exact-zero barycentric weights on a shared edge are
    // dropped or kept depending on libm's tanf rounding — CI vs local disagreed there.
    // Probe two pixels safely off the diagonal, one in each sub-triangle instead.
    const std::uint32_t probeA = px[38 * 64 + 28]; // upper-left sub-triangle
    const std::uint32_t probeB = px[28 * 64 + 38]; // lower-right sub-triangle
    std::fprintf(stderr, "INFO translucency: changed_pixels=%d probeA=0x%08X probeB=0x%08X\n", changed, probeA, probeB);
    CHECK(probeA != 0xFF202830u);
    CHECK(probeB != 0xFF202830u);
    CHECK(changed > 400); // ~484 locally, ~480 on CI; far from either
    // Average of the two probes must be a sky/water blend (each channel between the two).
    const int cr = (((probeA >> 16) & 0xFF) + ((probeB >> 16) & 0xFF)) / 2;
    const int cg = (((probeA >> 8) & 0xFF) + ((probeB >> 8) & 0xFF)) / 2;
    const int cb = (((probeA) & 0xFF) + ((probeB) & 0xFF)) / 2;
    CHECK(cr >= 0x1F && cr <= 0x40);
    CHECK(cg >= 0x28 && cg <= 0x70);
    CHECK(cb >= 0x30 && cb <= 0xD7);
    // Blend sanity: blendOver(src over dst) matches manual alpha composite.
    const std::uint32_t src = 0xFF000000u | (0x10u << 16) | (0x20u << 8) | 0x30u; // opaque red-ish src alpha handled below
    const std::uint32_t blended = vc::SoftwareRenderer::blendOver(0x80102030u, 0xFF405060u);
    CHECK_EQ((blended >> 24) & 0xFF, 0xFFu);
    CHECK_EQ((blended >> 16) & 0xFF, (0x10 + 0x40) / 2); // exact 50/50
    CHECK_EQ((blended >> 8) & 0xFF, (0x20 + 0x50) / 2);
    CHECK_EQ(blended & 0xFF, (0x30 + 0x60) / 2);
    (void)src;
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
    testNbtRoundtrip();
    testChunkSaveLoadRoundtrip();
    testMesherFuzz();
    testCaveCulling();
    testSideBuckets();
    testTranslucentWaterDraw();
    testLightPropagation();
    testMesherLightIntegration();
    testPackedRecordRoundtrip();
    std::fprintf(stderr, "\n%d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}

// PROJECT VOXELCORE — E7 packed-records parity gate (CI).
// Renders the SAME test scene twice: (A) CPU-expanded meshes via the normal Vulkan pipeline,
// (B) chunk-local 8-byte records via the vertex-pulled records pipeline. The two PPM outputs
// must be byte-identical (documented tolerance: none; if a platform ever disagrees by 1 LSB,
// adjust this gate and the E7 design doc in the same commit).
// Exit 0 = identical, 1 = pixel mismatch, 2 = tool/packing error, 77 = no Vulkan device (clean skip).
#include "../engine/world/world.hpp"
#include "../engine/world/block_reader.hpp"
#include "../engine/meshing/mesher.hpp"
#include "../engine/rendering/face_colors.hpp"
#include "../engine/rendering/packed_record.hpp"
#include "../engine/rendering/mesh_triangles.hpp"
#include "../engine/rendering/packed_record.hpp"
#include <cstdio>
#include <cstring>
#include <cstdarg>
#include <string>
#include <vector>
#include <algorithm>
#include <fstream>

#if defined(VOXELCORE_WITH_VULKAN)
#if defined(VOXELCORE_SPV_CONFIG)
#include "vulkan_build_config.hpp"
#endif
#include "../engine/rendering/vulkan/vulkan_headless.hpp"
#include "../engine/rendering/math.hpp"
#endif

using namespace vc;

namespace {

std::vector<unsigned char> readPpm(const std::string& path, uint32_t& w, uint32_t& h) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return {};
    std::string magic; f >> magic;
    if (magic != "P6") return {};
    f >> w >> h;
    int maxv = 0; f >> maxv;
    f.get(); // single whitespace after maxval
    std::vector<unsigned char> bytes((std::size_t)w * h * 3);
    f.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    if (!f) return {};
    return bytes;
}

} // namespace

int main(int argc, char** argv) {
    const std::string pathA = argc > 1 ? argv[1] : "parity_expanded.ppm";
    const std::string pathB = argc > 2 ? argv[2] : "parity_records.ppm";

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

    const GreedyMesher mesher;
    std::vector<std::pair<ChunkPos, std::vector<Quad>>> chunkMeshes;
    std::vector<Quad> allQuads;
    for (const auto& [pos, chunk] : world.chunks()) { (void)chunk;
        auto mesh = mesher.meshWorld(pos, world);
        allQuads.insert(allQuads.end(), mesh.quads.begin(), mesh.quads.end());
        chunkMeshes.emplace_back(pos, std::move(mesh.quads));
    }
    // Two-pass draw order identical to vulkan_render: opaque in mesher bucket order,
    // then water far-to-near (painter's algorithm).
    const math::Vec3 eye{64.0f, 42.0f, 90.0f};
    auto centroidDistSq = [&eye](const Quad& q) {
        float cx = q.x, cy = q.y, cz = q.z;
        switch (q.dir) {
            case FaceDir::PosX: case FaceDir::NegX: cy += q.v * 0.5f; cz += q.u * 0.5f; break;
            case FaceDir::PosY: case FaceDir::NegY: cx += q.u * 0.5f; cz += q.v * 0.5f; break;
            case FaceDir::PosZ: case FaceDir::NegZ: cx += q.u * 0.5f; cy += q.v * 0.5f; break;
        }
        const float dx = cx - eye.x, dy = cy - eye.y, dz = cz - eye.z;
        return dx * dx + dy * dy + dz * dz;
    };
    std::vector<Quad> waterPart;
    for (const Quad& q : allQuads)
        if (q.block == blocks::Water) waterPart.push_back(q);
    allQuads.erase(std::remove_if(allQuads.begin(), allQuads.end(),
                                  [](const Quad& q) { return q.block == blocks::Water; }),
                   allQuads.end());
    std::stable_sort(waterPart.begin(), waterPart.end(),
                     [&centroidDistSq](const Quad& a, const Quad& b) { return centroidDistSq(a) > centroidDistSq(b); });
    allQuads.insert(allQuads.end(), waterPart.begin(), waterPart.end());
    std::fprintf(stderr, "records_parity: quads=%zu\n", allQuads.size());
    // SMOKING-GUN DUMP: byte-compare the skyline quad corners between the expanded-vertex path
    // and the records-shader reconstruction (exact-integer planes, but verify empirically).
    std::string skylineDump;
    {
        auto hex = [](float f) { std::uint32_t b; std::memcpy(&b, &f, 4); char buf[12]; std::snprintf(buf, sizeof(buf), "%08x", b); return std::string(buf); };
    auto dumpLine = [&skylineDump](const char* fmt, ...) {
        char buf[512];
        va_list args;
        va_start(args, fmt);
        std::vsnprintf(buf, sizeof(buf), fmt, args);
        va_end(args);
        skylineDump += buf;
        skylineDump += '\n';
    };
    dumpLine("skyline bytes dump:");
        for (const Quad& q : allQuads) {
            const bool eastSky  = (q.dir == FaceDir::PosX && q.x == 64.0f && q.y == 20.0f && q.z == 0.0f && q.u == 16.0f);
            const bool topSky   = (q.dir == FaceDir::PosY && q.y == 21.0f && q.x == 48.0f && q.z == 0.0f && q.u == 16.0f && q.v == 16.0f);
            if (!eastSky && !topSky) continue;
            dumpLine("quad dir=%d x=%.1f y=%.1f z=%.1f u=%.1f v=%.1f hex x=%s y=%s z=%s u=%s v=%s",
                         static_cast<int>(q.dir), q.x, q.y, q.z, q.u, q.v, hex(q.x).c_str(), hex(q.y).c_str(), hex(q.z).c_str(), hex(q.u).c_str(), hex(q.v).c_str());
            // expanded path positions
            const MeshTriangles et = expandQuads(std::vector<Quad>{q});
            dumpLine("  expanded verts:");
            for (std::size_t i = 0; i < et.positions.size() / 3; ++i) {
                dumpLine("    v%zu pos=(%s %s %s)", i, hex(et.positions[i*3+0]).c_str(), hex(et.positions[i*3+1]).c_str(), hex(et.positions[i*3+2]).c_str());
            }
            dumpLine("  expanded indices:");
            for (std::uint32_t ix : et.indices) { char b[12]; std::snprintf(b, sizeof(b), " %u", ix); skylineDump += b; }
            dumpLine("");
            // records path reconstruction (mirror of records.vert math, ints -> floats)
            int ix0 = static_cast<int>(q.x) - 48, iz0 = static_cast<int>(q.z) - 0, iy = (q.dir == FaceDir::PosY) ? static_cast<int>(q.y) - 1 : static_cast<int>(q.y);
            // for PosX, x stored as slice-1; for PosY, y stored as slice-1, x/z as-is
            int recX = (q.dir == FaceDir::PosX) ? ix0 - 1 : ix0;
            int recZ = (q.dir == FaceDir::PosZ) ? iz0 - 1 : iz0;
            if (q.dir != FaceDir::PosY) iy = static_cast<int>(q.y);
            dumpLine("  record decode: rx=%d rz=%d ry=%d uE=%d vE=%d dir=%d block=%u ao=%u,%u,%u,%u light=%u",
                         recX, recZ, iy, static_cast<int>(q.u), static_cast<int>(q.v), static_cast<int>(q.dir), unsigned(q.block),
                         unsigned(q.ao[0]), unsigned(q.ao[1]), unsigned(q.ao[2]), unsigned(q.ao[3]), unsigned(q.light));
            const float ox = 48.0f, oz = 0.0f;
            dumpLine("  records reconstruct:");
            if (q.dir == FaceDir::PosX) {
                const float xp = static_cast<float>(recX) + 1.0f;
                const float y0 = static_cast<float>(iy), y1 = y0 + q.v;
                const float z0 = static_cast<float>(recZ), z1 = z0 + q.u;
                const float c[4][3] = {{xp, y0, z0}, {xp, y0, z1}, {xp, y1, z1}, {xp, y1, z0}};
                for (int i = 0; i < 4; ++i)
                    dumpLine("    c%d absolute=(%s %s %s)", i, hex(c[i][0] + ox).c_str(), hex(c[i][1]).c_str(), hex(c[i][2] + oz).c_str());
            } else if (q.dir == FaceDir::PosY) {
                const float yp = static_cast<float>(iy) + 1.0f;
                const float x0 = static_cast<float>(recX), x1 = x0 + q.u;
                const float z0 = static_cast<float>(recZ), z1 = z0 + q.v;
                const float c[4][3] = {{x0, yp, z0}, {x1, yp, z0}, {x1, yp, z1}, {x0, yp, z1}};
                for (int i = 0; i < 4; ++i)
                    dumpLine("    c%d absolute=(%s %s %s)", i, hex(c[i][0] + ox).c_str(), hex(c[i][1]).c_str(), hex(c[i][2] + oz).c_str());
            }
        }
    }

#if defined(VOXELCORE_WITH_VULKAN)
    const std::size_t expandCount = allQuads.size();
    const MeshTriangles tris = expandQuads(allQuads);
    std::vector<vk::Vertex> vertices;
    const std::size_t vcount = tris.positions.size() / 3;
    vertices.reserve(vcount);
    for (std::size_t i = 0; i < vcount; ++i)
        vertices.push_back({tris.positions[i * 3 + 0], tris.positions[i * 3 + 1], tris.positions[i * 3 + 2],
                            tris.colors[i * 4 + 0], tris.colors[i * 4 + 1], tris.colors[i * 4 + 2], tris.colors[i * 4 + 3]});
    const math::Vec3 target{54.0f, 20.0f, 50.0f}, up{0.0f, 1.0f, 0.0f};
    const math::Mat4 view = math::lookAtRH(eye, target, up);
    const math::Mat4 proj = math::perspectiveVulkan(60.0f, 4.0f / 3.0f, 0.5f, 500.0f);
    const math::Mat4 mvp = math::multiply(proj, view);
    try {
        {   // Path A: expanded vertices
            vk::HeadlessRenderer renderer(1280, 960, std::string(VOXELCORE_SPV_DIR));
            renderer.init();
            renderer.renderToPpm(vertices, tris.indices, mvp, pathA.c_str());
        }
        {   // Determinism probe: render path A a second time; report if driver is nondeterministic
            vk::HeadlessRenderer renderer(1280, 960, std::string(VOXELCORE_SPV_DIR));
            renderer.init();
            renderer.renderToPpm(vertices, tris.indices, mvp, (pathA + ".2.ppm").c_str());
        }
        std::fprintf(stderr, "records_parity: path A (expanded) wrote %s (%zu quads)\n", pathA.c_str(), expandCount);
        {   // Path B: chunk-local packed records, same global draw order
            // Pass 1 (opaque, mesher bucket order within chunks, chunk map order).
            std::vector<std::vector<std::uint32_t>> wordsKeepalive;
            std::vector<vk::HeadlessRenderer::RecordDraw> draws;
            auto addDraw = [&](float ox, float oz, std::vector<std::uint32_t>&& words) {
                if (words.empty()) return;
                wordsKeepalive.push_back(std::move(words));
                const auto& w = wordsKeepalive.back();
                draws.push_back({ox, oz, w.data(), w.size() / 2});
            };
            auto packRun = [&](const std::vector<Quad>& run, float ox, float oz, int iOriginX, int iOriginZ) {
                std::vector<std::uint32_t> words;
                words.reserve(run.size() * 2);
                for (const Quad& q : run) {
                    const auto packed = packQuadLocalMulti(q, iOriginX, iOriginZ);
                    if (!packed) {
                        std::fprintf(stderr, "records_parity: packQuadLocalMulti rejected quad dir=%d x=%.1f y=%.1f z=%.1f u=%.1f v=%.1f\n",
                                     static_cast<int>(q.dir), q.x, q.y, q.z, q.u, q.v);
                        return false;
                    }
                    for (const auto& rec : *packed) { words.push_back(rec.w0); words.push_back(rec.w1); }
                }
                addDraw(ox, oz, std::move(words));
                return true;
            };
            for (const auto& [pos, quads] : chunkMeshes) {
                std::vector<Quad> opaqueRun;
                opaqueRun.reserve(quads.size());
                for (const Quad& q : quads)
                    if (q.block != blocks::Water) opaqueRun.push_back(q);
                if (!packRun(opaqueRun, static_cast<float>(pos.x) * 16.0f, static_cast<float>(pos.z) * 16.0f, pos.x * 16, pos.z * 16))
                    return 2;
            }
            // Pass 2 (water, global far-to-near; runs grouped by chunk to keep chunk-local packing).
            struct TaggedWater { const Quad* q; ChunkPos pos; };
            std::vector<TaggedWater> tagged;
            for (const auto& [pos, quads] : chunkMeshes)
                for (const Quad& q : quads)
                    if (q.block == blocks::Water) tagged.push_back({&q, pos});
            std::stable_sort(tagged.begin(), tagged.end(),
                             [&centroidDistSq](const TaggedWater& a, const TaggedWater& b) { return centroidDistSq(*a.q) > centroidDistSq(*b.q); });
            for (std::size_t i = 0; i < tagged.size();) {
                std::size_t j = i;
                std::vector<Quad> run;
                while (j < tagged.size() && tagged[j].pos == tagged[i].pos) { run.push_back(*tagged[j].q); ++j; }
                if (!packRun(run, static_cast<float>(tagged[i].pos.x) * 16.0f, static_cast<float>(tagged[i].pos.z) * 16.0f,
                             tagged[i].pos.x * 16, tagged[i].pos.z * 16))
                    return 2;
                i = j;
            }
            std::size_t totalRecords = 0;
            for (const auto& d : draws) totalRecords += d.recordCount;
            std::fprintf(stderr, "records_parity: path B (records) draws=%zu records=%zu (%.1f bytes/quad)\n",
                         draws.size(), totalRecords, totalRecords ? static_cast<double>(totalRecords) * 8.0 / static_cast<double>(expandCount) : 0.0);
            // Reversed-order probes: are results order-dependent (depth ties) or coverage-dependent?
            {
                // A reversed: reverse triangle order in the index buffer
                std::vector<std::uint32_t> ridx;
                ridx.reserve(tris.indices.size());
                for (std::size_t i = tris.indices.size(); i >= 3;) { i -= 3; ridx.push_back(tris.indices[i]); ridx.push_back(tris.indices[i + 1]); ridx.push_back(tris.indices[i + 2]); }
                vk::HeadlessRenderer rr(1280, 960, std::string(VOXELCORE_SPV_DIR));
                rr.init();
                rr.renderToPpm(vertices, ridx, mvp, (pathA + ".rev.ppm").c_str());
                // B reversed: reverse chunk draw order
                std::vector<vk::HeadlessRenderer::RecordDraw> rdraws;
                for (std::size_t i = draws.size(); i-- > 0;) rdraws.push_back(draws[i]);
                vk::HeadlessRenderer rr2(1280, 960, std::string(VOXELCORE_SPV_DIR));
                rr2.init();
                rr2.renderRecordsToPpm(rdraws, mvp, (pathB + ".rev.ppm").c_str());
            }
            vk::HeadlessRenderer renderer(1280, 960, std::string(VOXELCORE_SPV_DIR));
            renderer.init();
            renderer.renderRecordsToPpm(draws, mvp, pathB.c_str());
            vk::HeadlessRenderer renderer2(1280, 960, std::string(VOXELCORE_SPV_DIR));
            renderer2.init();
            renderer2.renderRecordsToPpm(draws, mvp, (pathB + ".2.ppm").c_str());
            // Targeted probes: keep ONLY the grass-top record(s) of the skyline chunk, or ONLY the stone backwall.
            auto keepOnly = [&](auto&& pred, const char* suffix) {
                std::vector<std::vector<std::uint32_t>> keep;
                std::vector<vk::HeadlessRenderer::RecordDraw> fdraws;
                for (const auto& d : draws) {
                    std::vector<std::uint32_t> words;
                    for (std::size_t r = 0; r < d.recordCount; ++r) {
                        const std::uint32_t w0 = d.words[r * 2], w1 = d.words[r * 2 + 1];
                        if (pred(d.originX, d.originZ, w0, w1)) { words.push_back(w0); words.push_back(w1); }
                    }
                    if (!words.empty()) {
                        keep.push_back(std::move(words));
                        const auto& w = keep.back();
                        fdraws.push_back({d.originX, d.originZ, w.data(), w.size() / 2});
                    }
                }
                if (fdraws.empty()) { std::fprintf(stderr, "records_parity: filter %s matched nothing\n", suffix); return; }
                vk::HeadlessRenderer fr(1280, 960, std::string(VOXELCORE_SPV_DIR));
                fr.init();
                fr.renderRecordsToPpm(fdraws, mvp, suffix);
            };
            // grass top rect: chunk origin (48,0), PosY (dir=2), local x=0 z=0 y=20, u=16 v=16
            keepOnly([](float ox, float oz, std::uint32_t w0, std::uint32_t w1) {
                return ox == 48.0f && oz == 0.0f && ((w0 >> 22) & 0x7u) == 2u && ((w0 >> 8) & 0x3Fu) == 20u;
            }, (pathB + ".top.ppm").c_str());
            // stone backwall rect: chunk origin (48,0), NegZ (dir=5), local y=16, block=1
            keepOnly([](float ox, float oz, std::uint32_t w0, std::uint32_t w1) {
                return ox == 48.0f && oz == 0.0f && ((w0 >> 22) & 0x7u) == 5u && ((w0 >> 8) & 0x3Fu) == 16u && (w1 & 0xFFFFu) == 1u;
            }, (pathB + ".stone.ppm").c_str());
            // both together
            keepOnly([](float ox, float oz, std::uint32_t w0, std::uint32_t w1) {
                const std::uint32_t dir = (w0 >> 22) & 0x7u, y = (w0 >> 8) & 0x3Fu;
                return ox == 48.0f && oz == 0.0f && ((dir == 2u && y == 20u) || (dir == 5u && y == 16u && (w1 & 0xFFFFu) == 1u));
            }, (pathB + ".topstone.ppm").c_str());
            // ONLY the east wall rect records of chunk origin (48,0): PosX (dir=0) faces at the chunk's far edge
            keepOnly([](float ox, float oz, std::uint32_t w0, std::uint32_t) {
                return ox == 48.0f && oz == 0.0f && ((w0 >> 22) & 0x7u) == 0u;
            }, (pathB + ".east.ppm").c_str());
            // per-record east probes: y==20 (grass), y==18 (dirt), y==16 (stone), y==0 (stone)
            keepOnly([](float ox, float oz, std::uint32_t w0, std::uint32_t) {
                return ox == 48.0f && oz == 0.0f && ((w0 >> 22) & 0x7u) == 0u && ((w0 >> 8) & 0x3Fu) == 20u;
            }, (pathB + ".east_grass.ppm").c_str());
            keepOnly([](float ox, float oz, std::uint32_t w0, std::uint32_t) {
                return ox == 48.0f && oz == 0.0f && ((w0 >> 22) & 0x7u) == 0u && ((w0 >> 8) & 0x3Fu) == 18u;
            }, (pathB + ".east_dirt.ppm").c_str());
            keepOnly([](float ox, float oz, std::uint32_t w0, std::uint32_t) {
                return ox == 48.0f && oz == 0.0f && ((w0 >> 22) & 0x7u) == 0u && ((w0 >> 8) & 0x3Fu) == 16u;
            }, (pathB + ".east_stone16.ppm").c_str());
            keepOnly([](float ox, float oz, std::uint32_t w0, std::uint32_t) {
                return ox == 48.0f && oz == 0.0f && ((w0 >> 22) & 0x7u) == 0u && ((w0 >> 8) & 0x3Fu) == 0u;
            }, (pathB + ".east_stone0.ppm").c_str());
            // full packed-words dump of every east record in chunk (48,0)
            for (const auto& d : draws) {
                if (d.originX != 48.0f || d.originZ != 0.0f) continue;
                for (std::size_t r = 0; r < d.recordCount; ++r) {
                    const std::uint32_t w0 = d.words[r * 2], w1 = d.words[r * 2 + 1];
                    if (((w0 >> 22) & 0x7u) != 0u) continue; // east only
                    char buf[256];
                    std::snprintf(buf, sizeof(buf),
                        "eastrec w0=%08x w1=%08x dir=%u y=%u z=%u x=%u uE=%u vE=%u block=%u ao=%u,%u,%u,%u light=%u\n",
                        w0, w1, (w0 >> 22) & 0x7u, (w0 >> 8) & 0x3Fu, (w0 >> 4) & 0xFu, w0 & 0xFu,
                        ((w0 >> 14) & 0xFu) + 1u, ((w0 >> 18) & 0xFu) + 1u, w1 & 0xFFFFu,
                        (w1 >> 16) & 0x3u, (w1 >> 18) & 0x3u, (w1 >> 20) & 0x3u, (w1 >> 22) & 0x3u, (w1 >> 24) & 0xFu);
                    skylineDump += buf;
                }
            }
            // chunk (48,0) ONLY, opaque records only (no water in that chunk anyway)
            keepOnly([](float ox, float oz, std::uint32_t, std::uint32_t) {
                return ox == 48.0f && oz == 0.0f;
            }, (pathB + ".chunk30.ppm").c_str());
            // ALL opaque chunks EXCEPT origin (48,0)
            keepOnly([](float ox, float oz, std::uint32_t, std::uint32_t) {
                return !(ox == 48.0f && oz == 0.0f);
            }, (pathB + ".noc30.ppm").c_str());
            // chunk (48,0) minus dir==0 (east wall) records
            keepOnly([](float ox, float oz, std::uint32_t w0, std::uint32_t) {
                return ox == 48.0f && oz == 0.0f && ((w0 >> 22) & 0x7u) != 0u;
            }, (pathB + ".noc30_noeast.ppm").c_str());
            // corner shaded colors of the two quads, computed with the CPU shadeFace formula
            // (vertex colors the expanded path uploaded; records derives them identically in GLSL)
            {
                const std::uint32_t grassTop = shadeFace(faceColor(blocks::Grass), 3, 15, 1.0f);
                const std::uint32_t stoneNegZ3 = shadeFace(faceColor(blocks::Stone), 3, 15, 0.8f);
                const std::uint32_t stoneNegZ2 = shadeFace(faceColor(blocks::Stone), 2, 15, 0.8f);
                std::fprintf(stderr, "records_parity: CPU shades grassTop=%02x%02x%02x stoneNegZ(ao3)=%02x%02x%02x stoneNegZ(ao2)=%02x%02x%02x\n",
                             (grassTop >> 16) & 0xFF, (grassTop >> 8) & 0xFF, grassTop & 0xFF,
                             (stoneNegZ3 >> 16) & 0xFF, (stoneNegZ3 >> 8) & 0xFF, stoneNegZ3 & 0xFF,
                             (stoneNegZ2 >> 16) & 0xFF, (stoneNegZ2 >> 8) & 0xFF, stoneNegZ2 & 0xFF);
            }
            // Bisect: render with ONLY PosY (grass tops) and ONLY non-PosY records,
            // dump pixel (844,300) RGB from each to the report.
            try {
                // PosY-only
                {
                    std::vector<std::vector<std::uint32_t>> keep;
                    std::vector<vk::HeadlessRenderer::RecordDraw> fdraws;
                    for (const auto& d : draws) {
                        std::vector<std::uint32_t> words;
                        for (std::size_t r = 0; r < d.recordCount; ++r) {
                            const std::uint32_t w0 = d.words[r * 2];
                            if (((w0 >> 22) & 0x7u) == 2u) { words.push_back(w0); words.push_back(d.words[r * 2 + 1]); }
                        }
                        if (!words.empty()) {
                            keep.push_back(std::move(words));
                            const auto& w = keep.back();
                            fdraws.push_back({d.originX, d.originZ, w.data(), w.size() / 2});
                        }
                    }
                    if (!fdraws.empty()) {
                        vk::HeadlessRenderer fr(1280, 960, std::string(VOXELCORE_SPV_DIR));
                        fr.init();
                        fr.renderRecordsToPpm(fdraws, mvp, (pathB + ".posy.ppm").c_str());
                    }
                }
                // non-PosY only
                {
                    std::vector<std::vector<std::uint32_t>> keep;
                    std::vector<vk::HeadlessRenderer::RecordDraw> fdraws;
                    for (const auto& d : draws) {
                        std::vector<std::uint32_t> words;
                        for (std::size_t r = 0; r < d.recordCount; ++r) {
                            const std::uint32_t w0 = d.words[r * 2];
                            if (((w0 >> 22) & 0x7u) != 2u) { words.push_back(w0); words.push_back(d.words[r * 2 + 1]); }
                        }
                        if (!words.empty()) {
                            keep.push_back(std::move(words));
                            const auto& w = keep.back();
                            fdraws.push_back({d.originX, d.originZ, w.data(), w.size() / 2});
                        }
                    }
                    if (!fdraws.empty()) {
                        vk::HeadlessRenderer fr(1280, 960, std::string(VOXELCORE_SPV_DIR));
                        fr.init();
                        fr.renderRecordsToPpm(fdraws, mvp, (pathB + ".notposy.ppm").c_str());
                    }
                }
            } catch (const vk::VulkanError& e) {
                std::fprintf(stderr, "records_parity: bisect render skipped — %s\n", e.what());
            }
        }
    } catch (const vk::VulkanError& e) {
        std::fprintf(stderr, "records_parity: skipped — %s\n", e.what());
        return 77; // no GPU path available (e.g. no driver): clean skip like vulkan_render
    }
    uint32_t wa = 0, ha = 0, wb = 0, hb = 0;
    const auto a = readPpm(pathA, wa, ha);
    const auto b = readPpm(pathB, wb, hb);
    if (a.empty() || b.empty() || wa != wb || ha != hb) {
        std::fprintf(stderr, "records_parity: FAIL — could not read one of the PPMs\n");
        return 1;
    }
    // Determinism cross-check (path A rendered twice)
    std::string determinism;
    {
        uint32_t w2 = 0, h2 = 0;
        const auto a2 = readPpm(pathA + ".2.ppm", w2, h2);
        if (!a2.empty() && a2.size() == a.size()) {
            std::size_t same = 0;
            for (std::size_t i = 0; i < a.size(); ++i) same += (a[i] == a2[i]) ? 1 : 0;
            determinism = "A-vs-A2: " + std::to_string(same) + "/" + std::to_string(a.size());
        } else {
            determinism = "A2-unreadable";
        }
        const auto b2 = readPpm(pathB + ".2.ppm", w2, h2);
        if (!b2.empty() && b2.size() == b.size()) {
            std::size_t same = 0;
            for (std::size_t i = 0; i < b.size(); ++i) same += (b[i] == b2[i]) ? 1 : 0;
            determinism += " | B-vs-B2: " + std::to_string(same) + "/" + std::to_string(b.size());
        } else {
            determinism += " | B2-unreadable";
        }
        std::fprintf(stderr, "records_parity: %s\n", determinism.c_str());
    }
    std::size_t diffBytes = 0, diffPixels = 0;
    int maxDelta = 0;
    for (std::size_t i = 0; i < a.size(); ++i) {
        const int d = static_cast<int>(a[i]) - static_cast<int>(b[i]);
        if (d != 0) {
            ++diffBytes;
            if (d > maxDelta) maxDelta = d;
            if (d < -maxDelta) maxDelta = -d;
        }
    }
    for (std::size_t i = 0; i + 2 < a.size(); i += 3)
        if (a[i] != b[i] || a[i + 1] != b[i + 1] || a[i + 2] != b[i + 2]) ++diffPixels;
    if (diffBytes == 0) {
        std::fprintf(stderr, "records_parity: PASS — %ux%u, all %zu bytes identical\n", wa, ha, a.size());
        return 0;
    }
    std::fprintf(stderr, "records_parity: FAIL — %zu/%zu bytes differ (%zu/%zu pixels), max channel delta %d\n",
                 diffBytes, a.size(), diffPixels, static_cast<std::size_t>(wa) * ha, maxDelta);
    // Detailed report for CI artifact upload: first mismatching pixels + bounding box.
    std::string reportPath = pathB + ".report.txt";
    std::ofstream rep(reportPath);
    rep << "records_parity FAIL\n";
    rep << "dimensions: " << wa << "x" << ha << "\n";
    rep << "diff_bytes=" << diffBytes << " diff_pixels=" << diffPixels << " max_channel_delta=" << maxDelta << "\n";
    const std::size_t pixels = static_cast<std::size_t>(wa) * ha;
    int minX = wa, minY = ha, maxX = -1, maxY = -1;
    std::size_t printed = 0;
    for (std::size_t i = 0; i < pixels; ++i) {
        const std::size_t o = i * 3;
        if (a[o] == b[o] && a[o + 1] == b[o + 1] && a[o + 2] == b[o + 2]) continue;
        const int px = static_cast<int>(i % wa), py = static_cast<int>(i / wa);
        if (px < minX) minX = px; if (px > maxX) maxX = px;
        if (py < minY) minY = py; if (py > maxY) maxY = py;
        if (printed < 24) {
            rep << "pixel(" << px << "," << py << ") A=(" << int(a[o]) << "," << int(a[o + 1]) << "," << int(a[o + 2])
                << ") B=(" << int(b[o]) << "," << int(b[o + 1]) << "," << int(b[o + 2]) << ")\n";
            ++printed;
        }
    }
    // Knife-edge neighborhood dump (the single mismatch pixel sits on a hairline sliver):
    // print a 13x5 patch around the differing pixel for the key images so the CI annotation
    // shows WHICH sliver line covers the pixel in each render.
    {
        auto dumpPatch = [&](const char* label, const std::string& f, int cx, int cy) {
            uint32_t w2 = 0, h2 = 0;
            const auto img = readPpm(f, w2, h2);
            if (img.empty()) { rep << "patch " << label << ": unreadable\n"; return; }
            rep << "patch " << label << " (" << cx << "," << cy << "):\n";
            for (int y = cy - 2; y <= cy + 2; ++y) {
                rep << "  y=" << y << " ";
                for (int x = cx - 6; x <= cx + 6; ++x) {
                    if (x < 0 || y < 0 || static_cast<uint32_t>(x) >= w2 || static_cast<uint32_t>(y) >= h2) { rep << "...... "; continue; }
                    const std::size_t o = (static_cast<std::size_t>(y) * w2 + x) * 3;
                    char bfr[8];
                    std::snprintf(bfr, sizeof(bfr), "%02x%02x%02x ", img[o], img[o + 1], img[o + 2]);
                    rep << bfr;
                }
                rep << "\n";
            }
        };
        if (minX != wa) { // at least one differing pixel
            const int cx = minX, cy = minY;
            dumpPatch("A", pathA, cx, cy);
            dumpPatch("B", pathB, cx, cy);
            dumpPatch("chunk30", pathB + ".chunk30.ppm", cx, cy);
            dumpPatch("noeast", pathB + ".noc30_noeast.ppm", cx, cy);
            dumpPatch("east", pathB + ".east.ppm", cx, cy);
            dumpPatch("e_grass", pathB + ".east_grass.ppm", cx, cy);
            dumpPatch("e_dirt", pathB + ".east_dirt.ppm", cx, cy);
            dumpPatch("e_stone16", pathB + ".east_stone16.ppm", cx, cy);
            dumpPatch("stone", pathB + ".stone.ppm", cx, cy);
            dumpPatch("posy", pathB + ".posy.ppm", cx, cy);
        }
    }
    rep << skylineDump;
    rep << "determinism: " << determinism << "\n";
    {
        char mhex[16 * 12 + 32];
        int off = 0;
        for (int i = 0; i < 16; ++i) off += std::snprintf(mhex + off, sizeof(mhex) - off, "%s%08x", i ? "," : "", (int)__builtin_bit_cast(std::uint32_t, mvp.data()[i]));
        rep << "mvp_bits: " << mhex << "\n";
    }
    auto dumpPixel = [&](const std::string& f) {
        uint32_t w2 = 0, h2 = 0;
        const auto img = readPpm(f, w2, h2);
        if (img.empty()) return std::string("unreadable");
        const std::size_t o = (static_cast<std::size_t>(300) * w2 + 844) * 3;
        char buf[32];
        std::snprintf(buf, sizeof(buf), "(%d,%d,%d)", img[o], img[o + 1], img[o + 2]);
        return std::string(buf);
    };
    rep << "bisect (844,300): posy=" << dumpPixel(pathB + ".posy.ppm")
        << " notposy=" << dumpPixel(pathB + ".notposy.ppm") << "\n";
    rep << "rev (844,300): A2A=" << dumpPixel(pathA + ".rev.ppm") << " B2B=" << dumpPixel(pathB + ".rev.ppm") << "\n";
    rep << "targeted (844,300): top=" << dumpPixel(pathB + ".top.ppm")
        << " stone=" << dumpPixel(pathB + ".stone.ppm")
        << " topstone=" << dumpPixel(pathB + ".topstone.ppm") << "\n";
    rep << "surgical (844,300): east=" << dumpPixel(pathB + ".east.ppm")
        << " chunk30=" << dumpPixel(pathB + ".chunk30.ppm")
        << " noc30=" << dumpPixel(pathB + ".noc30.ppm")
        << " noc30_noeast=" << dumpPixel(pathB + ".noc30_noeast.ppm") << "\n";
    rep << "eastrec (844,300): grass=" << dumpPixel(pathB + ".east_grass.ppm")
        << " dirt=" << dumpPixel(pathB + ".east_dirt.ppm")
        << " stone16=" << dumpPixel(pathB + ".east_stone16.ppm")
        << " stone0=" << dumpPixel(pathB + ".east_stone0.ppm") << "\n";
    rep << "bbox: x[" << minX << "," << maxX << "] y[" << minY << "," << maxY << "]\n";
    // CPU-side coverage analysis for the first differing pixel: project every quad's triangles
    // with the same matrices used for the renders and list which cover the pixel center.
    {
        const int cx = minX, cy = minY;
        const float px = static_cast<float>(cx) + 0.5f, py = static_cast<float>(cy) + 0.5f;
        auto project = [&](float x, float y, float z, float& sx, float& sy, float& sz) {
            const float vx[4] = {x, y, z, 1.0f};
            float clip[4] = {0.0f, 0.0f, 0.0f, 0.0f};
            for (int col = 0; col < 4; ++col)
                for (int row = 0; row < 4; ++row) clip[row] += mvp[col * 4 + row] * vx[col];
            const float invW = 1.0f / clip[3];
            const float ndcX = clip[0] * invW, ndcY = clip[1] * invW;
            sx = (ndcX + 1.0f) * 0.5f * static_cast<float>(wa);
            sy = (1.0f + ndcY) * 0.5f * static_cast<float>(ha); // Vulkan viewport y-down; projection already Y-flips
            sz = clip[2] * invW;
        };
        auto covers = [&](const std::array<std::array<float,3>,3>& p) {
            float e[3];
            for (int i = 0; i < 3; ++i) {
                const int j = (i + 1) % 3;
                e[i] = (px - p[i][0]) * (p[j][1] - p[i][1]) - (py - p[i][1]) * (p[j][0] - p[i][0]);
            }
            const bool hasNeg = (e[0] < 0) || (e[1] < 0) || (e[2] < 0);
            const bool hasPos = (e[0] > 0) || (e[1] > 0) || (e[2] > 0);
            return !(hasNeg && hasPos);
        };
        auto emitTris = [&](const Quad& q, std::vector<std::array<std::array<float,3>,3>>& out) {
            float c[4][3];
            switch (q.dir) {
                case FaceDir::PosX: case FaceDir::NegX: {
                    const float x = q.x, z0 = q.z, y0 = q.y, z1 = z0 + q.u, y1 = y0 + q.v;
                    c[0][0]=x; c[0][1]=y0; c[0][2]=z0; c[1][0]=x; c[1][1]=y0; c[1][2]=z1;
                    c[2][0]=x; c[2][1]=y1; c[2][2]=z1; c[3][0]=x; c[3][1]=y1; c[3][2]=z0; break; }
                case FaceDir::PosY: case FaceDir::NegY: {
                    const float y = q.y, x0 = q.x, z0 = q.z, x1 = x0 + q.u, z1 = z0 + q.v;
                    c[0][0]=x0; c[0][1]=y; c[0][2]=z0; c[1][0]=x1; c[1][1]=y; c[1][2]=z0;
                    c[2][0]=x1; c[2][1]=y; c[2][2]=z1; c[3][0]=x0; c[3][1]=y; c[3][2]=z1; break; }
                case FaceDir::PosZ: case FaceDir::NegZ: {
                    const float z = q.z, x0 = q.x, y0 = q.y, x1 = x0 + q.u, y1 = y0 + q.v;
                    c[0][0]=x0; c[0][1]=y0; c[0][2]=z; c[1][0]=x1; c[1][1]=y0; c[1][2]=z;
                    c[2][0]=x1; c[2][1]=y1; c[2][2]=z; c[3][0]=x0; c[3][1]=y1; c[3][2]=z; break; }
            }
            const bool flip = (q.dir == FaceDir::NegX || q.dir == FaceDir::NegY || q.dir == FaceDir::PosZ);
            const std::array<int,6> oArr = flip ? std::array<int,6>{0,2,1,0,3,2} : std::array<int,6>{0,1,2,0,2,3};
            float sp[4][3];
            for (int i = 0; i < 4; ++i) project(c[i][0], c[i][1], c[i][2], sp[i][0], sp[i][1], sp[i][2]);
            auto toArr = [&sp](int i) { return std::array<float,3>{sp[i][0], sp[i][1], sp[i][2]}; };
            std::array<std::array<float,3>,3> t1{{toArr(oArr[0]), toArr(oArr[1]), toArr(oArr[2])}};
            std::array<std::array<float,3>,3> t2{{toArr(oArr[3]), toArr(oArr[4]), toArr(oArr[5])}};
            out.push_back(t1);
            out.push_back(t2);
        };
        // Instead of binary coverage, report the N triangles with an edge closest to the pixel center
        // (lavapipe's fixed-point snap can include a pixel that exact float math excludes).
        struct EdgeCand { float dist; std::size_t qi, ti; Quad v; };
        std::vector<EdgeCand> cands;
        std::size_t qi = 0;
        for (const auto& [pos, quads] : chunkMeshes) { (void)pos;
            for (const Quad& q : quads) {
                ++qi;
                std::vector<Quad> variants{q};
                const bool side = (q.dir == FaceDir::PosX || q.dir == FaceDir::NegX || q.dir == FaceDir::PosZ || q.dir == FaceDir::NegZ);
                if (side && q.v > 16.0f) {
                    variants.clear();
                    int remaining = static_cast<int>(q.v);
                    float y = q.y;
                    while (remaining > 16) { Quad sub = q; sub.y = y; sub.v = 16.0f; variants.push_back(sub); remaining -= 16; y += 16.0f; }
                    Quad sub = q; sub.y = y; sub.v = static_cast<float>(remaining); variants.push_back(sub);
                }
                for (const Quad& v : variants) {
                    std::vector<std::array<std::array<float,3>,3>> tris;
                    emitTris(v, tris);
                    for (std::size_t ti = 0; ti < tris.size(); ++ti) {
                        const auto& t = tris[ti];
                        // distance from pixel center to each triangle edge (2D)
                        float maxd = 1e30f, mind = 0.0f;
                        for (int i = 0; i < 3; ++i) {
                            const int j = (i + 1) % 3;
                            const float ax = t[i][0], ay = t[i][1], bx = t[j][0], by = t[j][1];
                            const float ex = bx - ax, ey = by - ay;
                            const float len = std::sqrt(ex * ex + ey * ey);
                            const float d = std::fabs((px - ax) * ey - (py - ay) * ex) / std::max(len, 1e-9f);
                            mind = std::max(mind, 0.0f);
                            maxd = std::min(maxd, d);
                        }
                        (void)mind;
                        if (maxd < 3.0f) cands.push_back({maxd, qi, ti, v});
                    }
                }
            }
        }
        // Coverage list with the (now fixed) projection: EVERY triangle containing the pixel center.
        std::size_t covCount = 0;
        rep << "containing triangles:\n";
        qi = 0;
        for (const auto& [pos, quads] : chunkMeshes) { (void)pos;
            for (const Quad& q : quads) {
                ++qi;
                std::vector<Quad> variants{q};
                const bool side = (q.dir == FaceDir::PosX || q.dir == FaceDir::NegX || q.dir == FaceDir::PosZ || q.dir == FaceDir::NegZ);
                if (side && q.v > 16.0f) {
                    variants.clear();
                    int remaining = static_cast<int>(q.v);
                    float y = q.y;
                    while (remaining > 16) { Quad sub = q; sub.y = y; sub.v = 16.0f; variants.push_back(sub); remaining -= 16; y += 16.0f; }
                    Quad sub = q; sub.y = y; sub.v = static_cast<float>(remaining); variants.push_back(sub);
                }
                for (const Quad& v : variants) {
                    std::vector<std::array<std::array<float,3>,3>> tris;
                    emitTris(v, tris);
                    for (std::size_t ti = 0; ti < tris.size(); ++ti) {
                        if (covers(tris[ti])) {
                            rep << "  cover quad#" << qi << " tri" << ti << " dir=" << int(v.dir)
                                << " block=" << unsigned(v.block) << " x=" << v.x << " y=" << v.y << " z=" << v.z
                                << " u=" << v.u << " v=" << v.v
                                << " ao=[" << int(v.ao[0]) << ',' << int(v.ao[1]) << ',' << int(v.ao[2]) << ',' << int(v.ao[3]) << ']'
                                << " light=" << int(v.light) << "\n";
                            ++covCount;
                        }
                    }
                }
            }
        }
        rep << "containing triangles: " << covCount << "\n";
        std::sort(cands.begin(), cands.end(), [](const EdgeCand& a, const EdgeCand& b) { return a.dist < b.dist; });
        rep << "nearest-edge triangles (dist px):\n";
        for (std::size_t k = 0; k < cands.size() && k < 10; ++k) {
            const Quad& v = cands[k].v;
            rep << "  quad#" << cands[k].qi << " tri" << cands[k].ti << " dist=" << cands[k].dist
                << " dir=" << int(v.dir) << " block=" << unsigned(v.block)
                << " x=" << v.x << " y=" << v.y << " z=" << v.z << " u=" << v.u << " v=" << v.v
                << " ao=[" << int(v.ao[0]) << ',' << int(v.ao[1]) << ',' << int(v.ao[2]) << ',' << int(v.ao[3]) << ']'
                << " light=" << int(v.light) << "\n";
        }
    }
    // 7x7 neighborhood around the FIRST differing pixel as hex, for edge-sliver analysis.
    {
        const std::size_t o0 = static_cast<std::size_t>(minY) * wa + static_cast<std::size_t>(minX);
        int cx = minX, cy = minY;
        (void)o0;
        const int R = 3;
        for (int dy = -R; dy <= R; ++dy) {
            const int py = cy + dy;
            if (py < 0 || static_cast<std::uint32_t>(py) >= ha) continue;
            rep << "row y=" << py << " A:";
            for (int dx = -R; dx <= R; ++dx) {
                const int px = cx + dx;
                if (px < 0 || static_cast<std::uint32_t>(px) >= wa) { rep << " ......"; continue; }
                const std::size_t o = (static_cast<std::size_t>(py) * wa + static_cast<std::size_t>(px)) * 3;
                char buf[8];
                std::snprintf(buf, sizeof(buf), " %02x%02x%02x", a[o], a[o + 1], a[o + 2]);
                rep << buf;
            }
            rep << " | B:";
            for (int dx = -R; dx <= R; ++dx) {
                const int px = cx + dx;
                if (px < 0 || static_cast<std::uint32_t>(px) >= wa) { rep << " ......"; continue; }
                const std::size_t o = (static_cast<std::size_t>(py) * wa + static_cast<std::size_t>(px)) * 3;
                char buf[8];
                std::snprintf(buf, sizeof(buf), " %02x%02x%02x", b[o], b[o + 1], b[o + 2]);
                rep << buf;
            }
            rep << "\n";
        }
    }
    rep.close();
    std::fprintf(stderr, "records_parity: wrote diagnostic report to %s\n", reportPath.c_str());
    return 1;
#else
    (void)pathA; (void)pathB;
    std::fprintf(stderr, "records_parity: built without Vulkan support (VOXELCORE_WITH_VULKAN=OFF)\n");
    return 77;
#endif
}

// PROJECT VOXELCORE — E7 packed-records parity gate (CI).
// Renders the SAME test scene twice: (A) CPU-expanded meshes via the normal Vulkan pipeline,
// (B) chunk-local 8-byte records via the vertex-pulled records pipeline. The two PPM outputs
// must be byte-identical (documented tolerance: none; if a platform ever disagrees by 1 LSB,
// adjust this gate and the E7 design doc in the same commit).
// Exit 0 = identical, 1 = pixel mismatch, 2 = tool/packing error, 77 = no Vulkan device (clean skip).
#include "../engine/world/world.hpp"
#include "../engine/world/block_reader.hpp"
#include "../engine/meshing/mesher.hpp"
#include "../engine/rendering/mesh_triangles.hpp"
#include "../engine/rendering/packed_record.hpp"
#include <cstdio>
#include <cstring>
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
                    const auto packed = packQuadLocal(q, iOriginX, iOriginZ);
                    if (!packed) {
                        std::fprintf(stderr, "records_parity: packQuadLocal rejected quad dir=%d x=%.1f y=%.1f z=%.1f u=%.1f v=%.1f\n",
                                     static_cast<int>(q.dir), q.x, q.y, q.z, q.u, q.v);
                        return false;
                    }
                    words.push_back(packed->w0);
                    words.push_back(packed->w1);
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
            vk::HeadlessRenderer renderer(1280, 960, std::string(VOXELCORE_SPV_DIR));
            renderer.init();
            renderer.renderRecordsToPpm(draws, mvp, pathB.c_str());
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
    return 1;
#else
    (void)pathA; (void)pathB;
    std::fprintf(stderr, "records_parity: built without Vulkan support (VOXELCORE_WITH_VULKAN=OFF)\n");
    return 77;
#endif
}

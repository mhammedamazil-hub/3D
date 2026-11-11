// PROJECT VOXELCORE — greedy meshing with visible-face elimination and per-corner AO.
//
// Visible-face elimination: a face is emitted only when the adjacent cell does not fully
// occlude it. Internal solid faces never enter the mask.
//
// Greedy merge: per 6 face orientations, cells whose (block, 4-corner-AO signature) match
// are merged into maximal rectangles. Merged rectangles preserve exact per-corner AO, so
// output is pixel-identical to per-face emission with baked AO, with far fewer quads.
//
// Cross-chunk faces: the reader callback supplies absolute coordinates; the world returns
// Air for absent chunks, so edge faces are emitted (conservative, never missing geometry).
#pragma once

#include "../core/types.hpp"
#include "../chunks/block_ids.hpp"
#include "../chunks/chunk.hpp"
#include "../world/world.hpp"
#include "../world/block_reader.hpp"
#include <cstdint>
#include <functional>
#include <vector>
#include <array>

namespace vc {

using BlockReader = std::function<BlockId(int, int, int)>;

// For maximum speed, mesh() templates over the reader functor (no std::function indirection).

enum class FaceDir : std::uint8_t { PosX = 0, NegX = 1, PosY = 2, NegY = 3, PosZ = 4, NegZ = 5 };

struct Quad {
    float x = 0, y = 0, z = 0;   // min corner of the merged rectangle in the face plane (absolute voxels)
    float u = 1, v = 1;          // extents along the two in-plane axes (whole blocks)
    FaceDir dir = FaceDir::PosY;
    BlockId block = 0;
    std::array<std::uint8_t, 4> ao = {3, 3, 3, 3}; // per corner, 3 = unoccluded (order: (-u,-v),(+u,-v),(+u,+v),(-u,+v))
};

struct MeshStats {
    std::uint64_t quads = 0;
    std::uint64_t vertices = 0;
    std::uint64_t indices = 0;
    std::uint64_t faceArea = 0;   // sum of w*h — must equal naiveFaces (checked by tests)
    std::uint64_t naiveFaces = 0; // visible faces before merging
};

class GreedyMesher {
public:
    struct Result {
        std::vector<Quad> quads;
        MeshStats stats;
    };

    Result mesh(ChunkPos pos, const BlockReader& read) const {
        return meshTyped(pos, read);
    }
    template <typename Reader>
    Result meshTyped(ChunkPos pos, const Reader& read) const {
        Result out;
        const int ox = pos.x * 16, oz = pos.z * 16;
        for (int d = 0; d < 6; ++d) meshDirection(static_cast<FaceDir>(d), ox, oz, read, out);
        return out;
    }

    // Convenience: mesh a chunk of `world`, reading absolute coordinates from the world.
    Result meshWorld(const ChunkPos pos, const World& world) const {
        const CachedBlockReader reader(world);
        return meshTyped(pos, reader);
    }

private:
    struct Cell {
        BlockId block = 0;
        std::array<std::uint8_t, 4> ao = {3, 3, 3, 3};
        bool present = false;
    };
    static bool cellEqual(const Cell& a, const Cell& b) {
        return a.present == b.present && a.block == b.block
            && a.ao[0] == b.ao[0] && a.ao[1] == b.ao[1] && a.ao[2] == b.ao[2] && a.ao[3] == b.ao[3];
    }

    template <typename Reader>
    void meshDirection(FaceDir dir, int ox, int oz, const Reader& read, Result& out) const {
        int axis = 0, sign = 1;
        switch (dir) {
            case FaceDir::PosX: axis = 0; sign = +1; break;
            case FaceDir::NegX: axis = 0; sign = -1; break;
            case FaceDir::PosY: axis = 1; sign = +1; break;
            case FaceDir::NegY: axis = 1; sign = -1; break;
            case FaceDir::PosZ: axis = 2; sign = +1; break;
            case FaceDir::NegZ: axis = 2; sign = -1; break;
        }
        const int sliceCount = (axis == 1) ? kChunkHeight : 16;
        const int dimV = (axis == 1) ? 16 : kChunkHeight;

        std::array<std::array<Cell, 16>, kChunkHeight> mask{};
        std::array<std::array<bool, 16>, kChunkHeight> used{};

        for (int slice = 0; slice < sliceCount; ++slice) {
            for (int v = 0; v < dimV; ++v) {
                for (int u = 0; u < 16; ++u) {
                    int wx, wy, wz;
                    if (axis == 0)      { wx = ox + slice; wz = oz + u; wy = v; }
                    else if (axis == 2) { wz = oz + slice; wx = ox + u; wy = v; }
                    else                { wy = slice;      wx = ox + u; wz = oz + v; }
                    const Cell c = faceCell(wx, wy, wz, axis, sign, read);
                    if (c.present) out.stats.naiveFaces += 1;
                    mask[static_cast<std::size_t>(v)][static_cast<std::size_t>(u)] = c;
                    used[static_cast<std::size_t>(v)][static_cast<std::size_t>(u)] = false;
                }
            }
            // Greedy rectangle merge.
            for (int v = 0; v < dimV; ++v) {
                for (int u = 0; u < 16; ) {
                    const Cell base = mask[static_cast<std::size_t>(v)][static_cast<std::size_t>(u)];
                    if (!base.present || used[static_cast<std::size_t>(v)][static_cast<std::size_t>(u)]) { ++u; continue; }
                    int w = 1;
                    while (u + w < 16 && !used[static_cast<std::size_t>(v)][static_cast<std::size_t>(u + w)]
                           && cellEqual(base, mask[static_cast<std::size_t>(v)][static_cast<std::size_t>(u + w)])) ++w;
                    int h = 1;
                    bool stop = false;
                    while (!stop && v + h < dimV) {
                        for (int k = 0; k < w; ++k) {
                            if (used[static_cast<std::size_t>(v + h)][static_cast<std::size_t>(u + k)]
                                || !cellEqual(base, mask[static_cast<std::size_t>(v + h)][static_cast<std::size_t>(u + k)])) { stop = true; break; }
                        }
                        if (!stop) ++h;
                    }
                    for (int dv = 0; dv < h; ++dv)
                        for (int du = 0; du < w; ++du)
                            used[static_cast<std::size_t>(v + dv)][static_cast<std::size_t>(u + du)] = true;

                    out.stats.quads += 1;
                    out.stats.vertices += 4;
                    out.stats.indices += 6;
                    out.stats.faceArea += static_cast<std::uint64_t>(w) * static_cast<std::uint64_t>(h);

                    const float plane = static_cast<float>(slice) + (sign > 0 ? 1.0f : 0.0f);
                    Quad q;
                    q.dir = dir;
                    q.block = base.block;
                    q.ao = base.ao;
                    q.u = static_cast<float>(w);
                    q.v = static_cast<float>(h);
                    if (axis == 0)      { q.x = plane; q.z = static_cast<float>(oz + u); q.y = static_cast<float>(v); }
                    else if (axis == 2) { q.z = plane; q.x = static_cast<float>(ox + u); q.y = static_cast<float>(v); }
                    else                { q.y = plane; q.x = static_cast<float>(ox + u); q.z = static_cast<float>(oz + v); }
                    out.quads.push_back(q);
                    u += w;
                }
            }
        }
    }

    template <typename Reader>
    Cell faceCell(int wx, int wy, int wz, int axis, int sign, const Reader& read) const {
        Cell cell;
        const BlockId self = read(wx, wy, wz);
        if (!blocks::renders(self)) return cell;
        int nx = wx, ny = wy, nz = wz;
        if (axis == 0) nx += sign; else if (axis == 1) ny += sign; else nz += sign;
        const BlockId other = read(nx, ny, nz);
        if (blocks::opaque(other)) return cell;
        if (self == blocks::Leaves && other == blocks::Leaves) return cell;
        if (self == blocks::Water && other == blocks::Water) return cell;
        cell.block = self;
        cell.present = true;
        cell.ao = cornerAO(wx, wy, wz, axis, sign, read);
        return cell;
    }

    template <typename Reader>
    std::array<std::uint8_t, 4> cornerAO(int wx, int wy, int wz, int axis, int sign, const Reader& read) const {
        const int uAxis = (axis == 0) ? 2 : 0;
        const int vAxis = (axis == 1) ? 2 : 1;
        auto occ = [&](int du, int dv) {
            int p[3] = {wx, wy, wz};
            p[axis] += sign;
            p[uAxis] += du;
            p[vAxis] += dv;
            return blocks::opaque(read(p[0], p[1], p[2])) ? 1 : 0;
        };
        const std::array<std::pair<int,int>,4> corners{{{-1,-1},{+1,-1},{+1,+1},{-1,+1}}};
        std::array<std::uint8_t,4> ao{};
        for (std::size_t i = 0; i < 4; ++i) {
            const int du = corners[i].first, dv = corners[i].second;
            const int s1 = occ(du, 0), s2 = occ(0, dv), corner = occ(du, dv);
            const int occluded = (s1 && s2) ? 3 : (s1 + s2 + corner);
            ao[i] = static_cast<std::uint8_t>(3 - std::min(occluded, 3));
        }
        return ao;
    }
};

} // namespace vc

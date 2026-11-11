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
#include "../visibility/cave_culling.hpp"
#include <cstdint>
#include <functional>
#include <vector>
#include <algorithm>
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

// Horizon-compatible side buckets (mesher/sides.rs): +X, +Z, other, +Y, -Z, -X, -Y.
// Ordering mesh output by bucket keeps the eye-facing runs to ~1-2 buckets per frame.
// "other" (index 2) is reserved for future non-cube faces (E7/E9); the loop below never emits it.
inline std::uint32_t sideBucket(FaceDir d) {
    switch (d) {
        case FaceDir::PosX: return 0;
        case FaceDir::PosZ: return 1;
        case FaceDir::PosY: return 3;
        case FaceDir::NegZ: return 4;
        case FaceDir::NegX: return 5;
        case FaceDir::NegY: return 6;
    }
    return 2;
}
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
        // 8 boundaries: bucketEnd[b] = exclusive end offset of bucket b (sideBucket(dir), 0..6).
        // Bucket b occupies quads[bucketEnd[b-1] .. bucketEnd[b]) (bucketEnd[-1] treated as 0).
        // bucketEnd[7] == quads.size(). quads are stably sorted by bucket (coplanar order preserved).
        std::array<std::size_t, 8> bucketEnd = {0, 0, 0, 0, 0, 0, 0, 0};
    };

    Result mesh(ChunkPos pos, const BlockReader& read) const {
        return meshTyped(pos, read);
    }
    template <typename Reader>
    Result meshTyped(ChunkPos pos, const Reader& read) const {
        const NoCaveCuller culler;
        return meshTypedEx(pos, read, culler, {0, 0, 0});
    }
    template <typename Reader, typename Culler>
    Result meshTypedEx(ChunkPos pos, const Reader& read, const Culler& culler, std::array<int,3> cameraCell) const {
        Result out;
        const int ox = pos.x * 16, oz = pos.z * 16;
        const int camComponent = culler.cameraComponent(cameraCell[0], cameraCell[1], cameraCell[2]);
        for (int d = 0; d < 6; ++d) meshDirection(static_cast<FaceDir>(d), ox, oz, read, culler, camComponent, out);
        // E6: stable 7-way partition into side buckets (single cursor scatter, O(n));
        // coplanar insertion order preserved inside each bucket.
        std::array<std::size_t, 7> cursor{};
        for (const Quad& q : out.quads) cursor[sideBucket(q.dir)]++;
        std::size_t acc = 0;
        for (std::size_t b = 0; b < 7; ++b) { const std::size_t c = cursor[b]; cursor[b] = acc; acc += c; }
        std::vector<Quad> sorted(out.quads.size());
        for (const Quad& q : out.quads) sorted[cursor[sideBucket(q.dir)]++] = q;
        out.quads = std::move(sorted);
        std::size_t qi = 0;
        for (std::size_t b = 0; b < 7; ++b) {
            while (qi < out.quads.size() && sideBucket(out.quads[qi].dir) == b) ++qi;
            out.bucketEnd[b] = qi;
        }
        out.bucketEnd[7] = out.quads.size();
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

    template <typename Reader, typename Culler>
    void meshDirection(FaceDir dir, int ox, int oz, const Reader& read, const Culler& culler, int camComponent, Result& out) const {
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
                    const Cell c = faceCell(wx, wy, wz, axis, sign, read, culler, camComponent);
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

    template <typename Reader, typename Culler>
    Cell faceCell(int wx, int wy, int wz, int axis, int sign, const Reader& read, const Culler& culler, int camComponent) const {
        Cell cell;
        const BlockId self = read(wx, wy, wz);
        if (!blocks::renders(self)) return cell;
        int nx = wx, ny = wy, nz = wz;
        if (axis == 0) nx += sign; else if (axis == 1) ny += sign; else nz += sign;
        const BlockId other = read(nx, ny, nz);
        if (blocks::opaque(other)) return cell;
        if (self == blocks::Leaves && other == blocks::Leaves) return cell;
        if (self == blocks::Water && other == blocks::Water) return cell;
        // Cave culling: a face against sealed non-opaque cells is visible only
        // from inside that same sealed component (camera already in it -> componentOf matches).
        if (const int sealedComp = culler.componentOf(nx, ny, nz); sealedComp > 0 && sealedComp != camComponent) {
            return cell;
        }
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

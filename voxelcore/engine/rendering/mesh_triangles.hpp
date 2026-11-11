// PROJECT VOXELCORE — expand greedy-mesher quads to a triangle soup for direct GPU upload.
#pragma once

#include "../meshing/mesher.hpp"
#include "face_colors.hpp"

namespace vc {

struct MeshTriangles {
    std::vector<float> positions; // xyz triplets
    std::vector<float> colors;    // rgba quadruplets, AO-shaded (alpha < 1 for water)
    std::vector<std::uint32_t> indices;
};

inline MeshTriangles expandQuads(const std::vector<Quad>& quads) {
    MeshTriangles out;
    out.positions.reserve(quads.size() * 12);
    out.colors.reserve(quads.size() * 16);
    out.indices.reserve(quads.size() * 6);
    for (const Quad& q : quads) {
        float c[4][3];
        switch (q.dir) {
            case FaceDir::PosX: case FaceDir::NegX: {
                const float x = q.x, z0 = q.z, y0 = q.y, z1 = z0 + q.u, y1 = y0 + q.v;
                c[0][0]=x; c[0][1]=y0; c[0][2]=z0;  c[1][0]=x; c[1][1]=y0; c[1][2]=z1;
                c[2][0]=x; c[2][1]=y1; c[2][2]=z1;  c[3][0]=x; c[3][1]=y1; c[3][2]=z0;
                break; }
            case FaceDir::PosY: case FaceDir::NegY: {
                const float y = q.y, x0 = q.x, z0 = q.z, x1 = x0 + q.u, z1 = z0 + q.v;
                c[0][0]=x0; c[0][1]=y; c[0][2]=z0;  c[1][0]=x1; c[1][1]=y; c[1][2]=z0;
                c[2][0]=x1; c[2][1]=y; c[2][2]=z1;  c[3][0]=x0; c[3][1]=y; c[3][2]=z1;
                break; }
            case FaceDir::PosZ: case FaceDir::NegZ: {
                const float z = q.z, x0 = q.x, y0 = q.y, x1 = x0 + q.u, y1 = y0 + q.v;
                c[0][0]=x0; c[0][1]=y0; c[0][2]=z;  c[1][0]=x1; c[1][1]=y0; c[1][2]=z;
                c[2][0]=x1; c[2][1]=y1; c[2][2]=z;  c[3][0]=x0; c[3][1]=y1; c[3][2]=z;
                break; }
        }
        const std::uint32_t base = faceColor(q.block);
        const std::uint32_t cornerCol[4] = {
            shadeFace(base, q.ao[0]), shadeFace(base, q.ao[1]),
            shadeFace(base, q.ao[2]), shadeFace(base, q.ao[3]),
        };
        const std::uint32_t vi = static_cast<std::uint32_t>(out.positions.size() / 3);
        for (int i = 0; i < 4; ++i) {
            out.positions.push_back(c[i][0]); out.positions.push_back(c[i][1]); out.positions.push_back(c[i][2]);
            const std::uint32_t col = cornerCol[i];
            out.colors.push_back(((col >> 16) & 0xFF) / 255.0f);
            out.colors.push_back(((col >> 8) & 0xFF) / 255.0f);
            out.colors.push_back((col & 0xFF) / 255.0f);
            out.colors.push_back(((col >> 24) & 0xFF) / 255.0f);
        }
        // Consistent winding per face so a future backface-culling pass is well-defined.
        const bool flip = (q.dir == FaceDir::NegX || q.dir == FaceDir::NegY || q.dir == FaceDir::PosZ);
        if (!flip) {
            out.indices.insert(out.indices.end(), {vi, vi + 1, vi + 2, vi, vi + 2, vi + 3});
        } else {
            out.indices.insert(out.indices.end(), {vi, vi + 2, vi + 1, vi, vi + 3, vi + 2});
        }
    }
    return out;
}

} // namespace vc

// PROJECT VOXELCORE — view frustum planes + AABB culling (Gribb–Hartmann from view-projection).
#pragma once

#include <array>
#include <cmath>
#include <cstdint>

namespace vc {

struct Vec3 { float x, y, z; };
struct AABB { Vec3 min, max; };

struct Plane { float a, b, c, d; }; // ax + by + cz + d = 0, normal points inward when normalized from outward store

struct Frustum {
    std::array<Plane, 6> planes{}; // left, right, bottom, top, near, far

    // m is column-major view-projection (m[col*4+row]).
    static Frustum fromViewProj(const float m[16]) {
        Frustum f;
        auto row = [&](int r) { return std::array<float,4>{m[r], m[4 + r], m[8 + r], m[12 + r]}; };
        const auto r0 = row(0), r1 = row(1), r2 = row(2), r3 = row(3);
        auto mk = [&](std::array<float,4> a, std::array<float,4> b, float sign) {
            // sign=+1: a+b ; sign=-1: a-b
            Plane p{ (sign > 0 ? a[0] + b[0] : a[0] - b[0]),
                     (sign > 0 ? a[1] + b[1] : a[1] - b[1]),
                     (sign > 0 ? a[2] + b[2] : a[2] - b[2]),
                     (sign > 0 ? a[3] + b[3] : a[3] - b[3]) };
            const float len = std::sqrt(p.a * p.a + p.b * p.b + p.c * p.c);
            if (len > 0) { p.a /= len; p.b /= len; p.c /= len; p.d /= len; }
            return p;
        };
        f.planes[0] = mk(r3, r0, +1); // left   = row3 + row0
        f.planes[1] = mk(r3, r0, -1); // right  = row3 - row0
        f.planes[2] = mk(r3, r1, +1); // bottom = row3 + row1
        f.planes[3] = mk(r3, r1, -1); // top    = row3 - row1
        f.planes[4] = mk(r3, r2, +1); // near   = row3 + row2
        f.planes[5] = mk(r3, r2, -1); // far    = row3 - row2
        return f;
    }

    bool intersects(const AABB& box) const {
        for (const Plane& p : planes) {
            // Positive-vertex test: the box corner furthest along the plane normal.
            const float px = p.a >= 0 ? box.max.x : box.min.x;
            const float py = p.b >= 0 ? box.max.y : box.min.y;
            const float pz = p.c >= 0 ? box.max.z : box.min.z;
            if (p.a * px + p.b * py + p.c * pz + p.d < 0) return false;
        }
        return true;
    }
};

} // namespace vc

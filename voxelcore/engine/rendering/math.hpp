// PROJECT VOXELCORE — minimal float math for rendering paths (shared by CPU rasterizer and Vulkan).
// Right-handed coordinates, column-major storage, w-axis last.
#pragma once

#include <array>
#include <cmath>
#include <cstdint>

namespace vc::math {

struct Vec3 { float x, y, z; };
using Mat4 = std::array<float, 16>; // column-major: m[col*4 + row]

inline Mat4 identity() { return {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1}; }

inline Mat4 multiply(const Mat4& a, const Mat4& b) {
    Mat4 r{};
    for (int col = 0; col < 4; ++col)
        for (int row = 0; row < 4; ++row) {
            float sum = 0;
            for (int k = 0; k < 4; ++k) sum += a[k * 4 + row] * b[col * 4 + k];
            r[col * 4 + row] = sum;
        }
    return r;
}

inline Mat4 lookAtRH(Vec3 eye, Vec3 target, Vec3 up) {
    const float fx = target.x - eye.x, fy = target.y - eye.y, fz = target.z - eye.z;
    const float fl = std::sqrt(fx * fx + fy * fy + fz * fz);
    const float f[3] = {fx / fl, fy / fl, fz / fl};
    float s[3] = {f[1] * up.z - f[2] * up.y, f[2] * up.x - f[0] * up.z, f[0] * up.y - f[1] * up.x};
    const float sl = std::sqrt(s[0] * s[0] + s[1] * s[1] + s[2] * s[2]);
    s[0] /= sl; s[1] /= sl; s[2] /= sl;
    const float u[3] = {s[1] * f[2] - s[2] * f[1], s[2] * f[0] - s[0] * f[2], s[0] * f[1] - s[1] * f[0]};
    Mat4 r = identity();
    r[0] = s[0]; r[4] = s[1]; r[8] = s[2];
    r[1] = u[0]; r[5] = u[1]; r[9] = u[2];
    r[2] = -f[0]; r[6] = -f[1]; r[10] = -f[2];
    r[12] = -(s[0] * eye.x + s[1] * eye.y + s[2] * eye.z);
    r[13] = -(u[0] * eye.x + u[1] * eye.y + u[2] * eye.z);
    r[14] = (f[0] * eye.x + f[1] * eye.y + f[2] * eye.z);
    return r;
}

// Vulkan-style projection: z in [0, 1], Y flipped for top-left origin.
inline Mat4 perspectiveVulkan(float fovDeg, float aspect, float zn, float zf, bool flipY = true) {
    const float f = 1.0f / std::tan(fovDeg * 0.5f * 3.14159265f / 180.0f);
    Mat4 r{};
    r[0] = f / aspect;
    r[5] = flipY ? -f : f;
    r[10] = zf / (zn - zf);
    r[11] = -1.0f;
    r[14] = (zf * zn) / (zn - zf);
    return r;
}

} // namespace vc::math

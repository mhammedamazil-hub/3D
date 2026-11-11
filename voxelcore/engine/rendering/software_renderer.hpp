// PROJECT VOXELCORE — minimal z-buffered CPU rasterizer for headless verification.
// Not a shipping renderer: proves the mesh → triangle → pixels path end to end without a
// GPU. Desktop/mobile GPU backends (Vulkan, OpenGL ES) are layered on in later stages.
#pragma once

#include "../meshing/mesher.hpp"
#include <vector>
#include <cstdint>
#include <cmath>
#include <algorithm>
#include <limits>

namespace vc {

struct Camera {
    float eyeX = 0, eyeY = 40, eyeZ = -40;
    float targetX = 0, targetY = 0, targetZ = 0;
    float fovDeg = 70.0f;
    float aspect = 16.0f / 9.0f;
    float nearZ = 0.1f, farZ = 500.0f;
    bool orthographicTop = false; // top-down heightmap view for tooling
    float topSpan = 200.0f;       // world units across the image in top view
};

class SoftwareRenderer {
public:
    void resize(int width, int height) {
        width_ = width; height_ = height;
        color_.assign(static_cast<std::size_t>(width) * height, 0xFF202830u); // sky-ish
        depth_.assign(static_cast<std::size_t>(width) * height, std::numeric_limits<float>::infinity());
    }

    void clear(std::uint32_t argb) {
        std::fill(color_.begin(), color_.end(), argb);
        std::fill(depth_.begin(), depth_.end(), std::numeric_limits<float>::infinity());
    }

    // Draw the quads of one chunk mesh. ao14: 8-bit ARGB shading per-vertex from AO.
    void drawQuads(const std::vector<Quad>& quads, float originX, float originZ) {
        for (const Quad& q : quads) {
            // 4 corners of the rect in absolute coords.
            float c[4][3];
            quadCorners(q, originX, originZ, c);
            // Two triangles: 0,1,2 and 0,2,3. AO per corner.
            const std::uint32_t base = faceColor(q.block);
            const std::uint32_t c0 = shade(base, q.ao[0]), c1 = shade(base, q.ao[1]);
            const std::uint32_t c2 = shade(base, q.ao[2]), c3 = shade(base, q.ao[3]);
            drawTriangle(c[0], c[1], c[2], c0, c1, c2);
            drawTriangle(c[0], c[2], c[3], c0, c2, c3);
        }
    }

    const std::vector<std::uint32_t>& pixels() const { return color_; }
    int width() const { return width_; }
    int height() const { return height_; }

    // Orbit-style camera used by drawQuads internally. Set before drawing.
    Camera camera;

    void writePPM(const char* path) const {
        FILE* f = std::fopen(path, "wb");
        if (!f) return;
        std::fprintf(f, "P6\n%d %d\n255\n", width_, height_);
        for (std::uint32_t px : color_) {
            const unsigned char rgb[3] = { static_cast<unsigned char>((px >> 16) & 0xFF),
                                           static_cast<unsigned char>((px >> 8) & 0xFF),
                                           static_cast<unsigned char>(px & 0xFF) };
            std::fwrite(rgb, 1, 3, f);
        }
        std::fclose(f);
    }

private:
    static std::uint32_t shade(std::uint32_t argb, std::uint8_t ao) {
        const float k = 0.35f + 0.2167f * static_cast<float>(ao); // ao 0..3 → 0.35..1.0
        const std::uint32_t r = static_cast<std::uint32_t>(((argb >> 16) & 0xFF) * k);
        const std::uint32_t g = static_cast<std::uint32_t>(((argb >> 8) & 0xFF) * k);
        const std::uint32_t b = static_cast<std::uint32_t>((argb & 0xFF) * k);
        return 0xFF000000u | (r << 16) | (g << 8) | b;
    }
    static std::uint32_t faceColor(BlockId b) {
        switch (b) {
            case blocks::Grass:  return 0xFF5E9C3F;
            case blocks::Dirt:   return 0xFF79553A;
            case blocks::Stone:  return 0xFF888888;
            case blocks::Sand:   return 0xFFD6CCA1;
            case blocks::Water:  return 0xFF3F6FD6;
            case blocks::Log:    return 0xFF6B4A2B;
            case blocks::Leaves: return 0xFF2F6B2F;
            case blocks::Bedrock:return 0xFF333333;
            case blocks::Snow:   return 0xFFF2F5F7;
            default:             return 0xFFAA33AA;
        }
    }

    static void quadCorners(const Quad& q, float ox, float oz, float c[4][3]) {
        const float planeOff = 0.0f;
        switch (q.dir) {
            case FaceDir::PosX: case FaceDir::NegX: {
                const float x = q.x + planeOff, z0 = q.z, y0 = q.y, z1 = z0 + q.u, y1 = y0 + q.v;
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
        (void)ox; (void)oz;
    }

    // --- projection (simple look-at, row-major, right-handed) ---
    void buildBasis(float fwd[3], float right[3], float up[3]) const {
        const float fx = camera.targetX - camera.eyeX, fy = camera.targetY - camera.eyeY, fz = camera.targetZ - camera.eyeZ;
        const float fl = std::sqrt(fx*fx + fy*fy + fz*fz);
        fwd[0]=fx/fl; fwd[1]=fy/fl; fwd[2]=fz/fl;
        const float rx = -fwd[2], rz = fwd[0]; // cross(fwd, worldUp) // cross(fwd, worldUp=(0,1,0))... gives right
        const float rl = std::sqrt(rx*rx + rz*rz);
        right[0]=rx/rl; right[1]=0; right[2]=rz/rl;
        up[0] = right[1]*fwd[2] - right[2]*fwd[1];
        up[1] = right[2]*fwd[0] - right[0]*fwd[2];
        up[2] = right[0]*fwd[1] - right[1]*fwd[0];
    }

    bool project(const float p[3], float& sx, float& sy, float& depth) const {
        float fwd[3], right[3], up[3];
        buildBasis(fwd, right, up);
        const float dx = p[0]-camera.eyeX, dy = p[1]-camera.eyeY, dz = p[2]-camera.eyeZ;
        const float z = dx*fwd[0] + dy*fwd[1] + dz*fwd[2];
        if (z < camera.nearZ) return false;
        const float x = dx*right[0] + dy*right[1] + dz*right[2];
        const float y = dx*up[0] + dy*up[1] + dz*up[2];
        const float f = 1.0f / std::tan(camera.fovDeg * 0.5f * 3.14159265f / 180.0f);
        const float nx = x * f / camera.aspect / z;
        const float ny = y * f / z;
        sx = (nx * 0.5f + 0.5f) * static_cast<float>(width_);
        sy = (0.5f - ny * 0.5f) * static_cast<float>(height_);
        depth = z;
        return true;
    }

    std::uint32_t lerpColor(std::uint32_t a, std::uint32_t b, float t) const {
        const int ar=(a>>16)&0xFF, ag=(a>>8)&0xFF, ab=a&0xFF;
        const int br=(b>>16)&0xFF, bg=(b>>8)&0xFF, bb=b&0xFF;
        const int r=static_cast<int>(ar+(br-ar)*t), g=static_cast<int>(ag+(bg-ag)*t), bl=static_cast<int>(ab+(bb-ab)*t);
        return 0xFF000000u | (static_cast<std::uint32_t>(r)<<16) | (static_cast<std::uint32_t>(g)<<8) | static_cast<std::uint32_t>(bl);
    }

    void drawTriangle(const float p0[3], const float p1[3], const float p2[3],
                      std::uint32_t c0, std::uint32_t c1, std::uint32_t c2) {
        float sx0, sy0, d0, sx1, sy1, d1, sx2, sy2, d2;
        if (!project(p0, sx0, sy0, d0)) return;
        if (!project(p1, sx1, sy1, d1)) return;
        if (!project(p2, sx2, sy2, d2)) return;
        const float minXf = std::floor(std::min({sx0, sx1, sx2})), maxXf = std::ceil(std::max({sx0, sx1, sx2}));
        const float minYf = std::floor(std::min({sy0, sy1, sy2})), maxYf = std::ceil(std::max({sy0, sy1, sy2}));
        const int minX = std::max(0, static_cast<int>(minXf)), maxX = std::min(width_ - 1, static_cast<int>(maxXf));
        const int minY = std::max(0, static_cast<int>(minYf)), maxY = std::min(height_ - 1, static_cast<int>(maxYf));
        const float denom = (sy1 - sy2) * (sx0 - sx2) + (sx2 - sx1) * (sy0 - sy2);
        if (std::fabs(denom) < 1e-12f) return;
        for (int py = minY; py <= maxY; ++py) {
            for (int px = minX; px <= maxX; ++px) {
                const float w0 = ((sy1 - sy2) * (px + 0.5f - sx2) + (sx2 - sx1) * (py + 0.5f - sy2)) / denom;
                const float w1 = ((sy2 - sy0) * (px + 0.5f - sx2) + (sx0 - sx2) * (py + 0.5f - sy2)) / denom;
                const float w2 = 1.0f - w0 - w1;
                if (w0 < 0 || w1 < 0 || w2 < 0) continue;
                const float z = w0 * d0 + w1 * d1 + w2 * d2;
                const std::size_t idx = static_cast<std::size_t>(py) * width_ + px;
                if (z >= depth_[idx]) continue;
                depth_[idx] = z;
                // Perspective-correct-ish color interp (affine is fine for tiny tris).
                std::uint32_t col = lerpColor(lerpColor(c0, c1, w1 / (w0 + w1 + 1e-9f)), c2, w2);
                color_[idx] = col;
            }
        }
    }

    int width_ = 0, height_ = 0;
    std::vector<std::uint32_t> color_;
    std::vector<float> depth_;
};

} // namespace vc

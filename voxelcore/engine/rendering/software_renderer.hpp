// PROJECT VOXELCORE — minimal z-buffered CPU rasterizer for headless verification.
// Not a shipping renderer: proves the mesh → triangle → pixels path end to end without a
// GPU. Desktop/mobile GPU backends (Vulkan, OpenGL ES) are layered on in later stages.
#pragma once

#include "../meshing/mesher.hpp"
#include "face_colors.hpp"
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

    // Draw the quads of one chunk mesh with per-corner AO shading.
    // Pass 1 (opaque + cutout): backface-culled, z-buffered with depth writes.
    // Pass 2 (water/translucent): both-sided, depth-tested (against pass-1 depth) but no depth
    // writes, alpha-blended back-to-front (painter's algorithm) so nested water sorts correctly.
    void drawQuads(const std::vector<Quad>& quads, float originX, float originZ) {
        const float fwdX = camera.targetX - camera.eyeX, fwdY = camera.targetY - camera.eyeY, fwdZ = camera.targetZ - camera.eyeZ;
        // --- Pass 1: opaque + cutout ---
        for (const Quad& q : quads) {
            if (q.block == blocks::Water) continue; // deferred to pass 2
            const bool cutout = (q.block == blocks::Leaves);
            if (!cutout) {
                float nx = 0, ny = 0, nz = 0;
                switch (q.dir) {
                    case FaceDir::PosX: nx = 1; break; case FaceDir::NegX: nx = -1; break;
                    case FaceDir::PosY: ny = 1; break; case FaceDir::NegY: ny = -1; break;
                    case FaceDir::PosZ: nz = 1; break; case FaceDir::NegZ: nz = -1; break;
                }
                // Skip if the face normal points away from the camera.
                if (nx * fwdX + ny * fwdY + nz * fwdZ >= 0.0f) continue;
            }
            drawOneQuad(q, originX, originZ, /*blend=*/false);
        }
        // --- Pass 2: translucent (water), far to near ---
        struct WaterItem { const Quad* q; float distSq; };
        std::vector<WaterItem> water;
        for (const Quad& q : quads) {
            if (q.block != blocks::Water) continue;
            float cx = q.x, cy = q.y, cz = q.z;
            switch (q.dir) {
                case FaceDir::PosX: case FaceDir::NegX: cx += 0.0f; cy += q.v * 0.5f; cz += q.u * 0.5f; break;
                case FaceDir::PosY: case FaceDir::NegY: cx += q.u * 0.5f; cz += q.v * 0.5f; break;
                case FaceDir::PosZ: case FaceDir::NegZ: cx += q.u * 0.5f; cy += q.v * 0.5f; break;
            }
            // Quad coords are absolute world coords (originX/originZ unused by the mesher today).
            const float dx = cx - camera.eyeX, dy = cy - camera.eyeY, dz = cz - camera.eyeZ;
            water.push_back({&q, dx * dx + dy * dy + dz * dz});
        }
        std::stable_sort(water.begin(), water.end(), [](const WaterItem& a, const WaterItem& b) { return a.distSq > b.distSq; });
        for (const WaterItem& w : water) drawOneQuad(*w.q, originX, originZ, /*blend=*/true);
    }

    static std::uint32_t blendOver(std::uint32_t src, std::uint32_t dst) {
        const float a = static_cast<float>((src >> 24) & 0xFF) / 255.0f;
        const float inv = 1.0f - a;
        const std::uint32_t r = static_cast<std::uint32_t>(((src >> 16) & 0xFF) * a + ((dst >> 16) & 0xFF) * inv + 0.5f);
        const std::uint32_t g = static_cast<std::uint32_t>(((src >> 8) & 0xFF) * a + ((dst >> 8) & 0xFF) * inv + 0.5f);
        const std::uint32_t b = static_cast<std::uint32_t>((src & 0xFF) * a + (dst & 0xFF) * inv + 0.5f);
        return 0xFF000000u | (r << 16) | (g << 8) | b;
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

    void drawOneQuad(const Quad& q, float originX, float originZ, bool blend) {
        float c[4][3];
        quadCorners(q, originX, originZ, c);
        const std::uint32_t base = vc::faceColor(q.block);
        const std::uint32_t c0 = vc::shadeFace(base, q.ao[0], q.light), c1 = vc::shadeFace(base, q.ao[1], q.light);
        const std::uint32_t c2 = vc::shadeFace(base, q.ao[2], q.light), c3 = vc::shadeFace(base, q.ao[3], q.light);
        drawTriangle(c[0], c[1], c[2], c0, c1, c2, blend);
        drawTriangle(c[0], c[2], c[3], c0, c2, c3, blend);
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
        const int ar=(a>>16)&0xFF, ag=(a>>8)&0xFF, ab=a&0xFF, aa=(a>>24)&0xFF;
        const int br=(b>>16)&0xFF, bg=(b>>8)&0xFF, bb=b&0xFF, ba=(b>>24)&0xFF;
        const int r=static_cast<int>(ar+(br-ar)*t), g=static_cast<int>(ag+(bg-ag)*t), bl=static_cast<int>(ab+(bb-ab)*t), al=static_cast<int>(aa+(ba-aa)*t);
        return (static_cast<std::uint32_t>(al)<<24) | (static_cast<std::uint32_t>(r)<<16) | (static_cast<std::uint32_t>(g)<<8) | static_cast<std::uint32_t>(bl);
    }

    void drawTriangle(const float p0[3], const float p1[3], const float p2[3],
                      std::uint32_t c0, std::uint32_t c1, std::uint32_t c2, bool blend = false) {
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
                if (z >= depth_[idx]) continue; // already occluded
                // Perspective-correct-ish color interp (affine is fine for tiny tris).
                const std::uint32_t col = lerpColor(lerpColor(c0, c1, w1 / (w0 + w1 + 1e-9f)), c2, w2);
                if (blend) {
                    color_[idx] = blendOver(col, color_[idx]); // no depth write: water is transparent
                } else {
                    depth_[idx] = z;
                    color_[idx] = col;
                }
            }
        }
    }

    int width_ = 0, height_ = 0;
    std::vector<std::uint32_t> color_;
    std::vector<float> depth_;
};

} // namespace vc

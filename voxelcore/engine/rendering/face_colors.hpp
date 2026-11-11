// PROJECT VOXELCORE — shared block-face colors + AO shading (software rasterizer & Vulkan).
#pragma once

#include "../chunks/block_ids.hpp"
#include <cstdint>

namespace vc {

inline std::uint32_t faceColor(BlockId b) {
    switch (b) {
        case blocks::Grass:  return 0xFF5E9C3F;
        case blocks::Dirt:   return 0xFF79553A;
        case blocks::Stone:  return 0xFF888888;
        case blocks::Sand:   return 0xFFD6CCA1;
        case blocks::Water:  return 0x9F3F6FD6; // translucent (alpha ~0.62)
        case blocks::Log:    return 0xFF6B4A2B;
        case blocks::Leaves: return 0xFF2F6B2F;
        case blocks::Bedrock:return 0xFF333333;
        case blocks::Snow:   return 0xFFF2F5F7;
        default:             return 0xFFAA33AA;
    }
}

// ao 0..3 (Minecraft corner AO), light 0..15 (Minecraft sky/block face light).
// AO factor: 0.35..1.0. Light factor: 0.2..1.0. light=15 reproduces the AO-only result exactly.
inline std::uint32_t shadeFace(std::uint32_t argb, std::uint8_t ao, std::uint8_t light = 15) {
    const float aoK = 0.35f + 0.2167f * static_cast<float>(ao);
    const float lightK = 0.2f + 0.8f * (static_cast<float>(light) / 15.0f);
    const float k = aoK * lightK;
    const std::uint32_t r = static_cast<std::uint32_t>(((argb >> 16) & 0xFF) * k);
    const std::uint32_t g = static_cast<std::uint32_t>(((argb >> 8) & 0xFF) * k);
    const std::uint32_t b = static_cast<std::uint32_t>((argb & 0xFF) * k);
    return (argb & 0xFF000000u) | (r << 16) | (g << 8) | b; // preserve source alpha
}

// Opaque face vs open (cutout/translucent) block.
inline bool faceIsOpen(BlockId b) { return b == blocks::Leaves || b == blocks::Water; }

} // namespace vc

// PROJECT VOXELCORE — deterministic 2D/3D gradient (Perlin-style) noise with fBm.
// Reference-quality terrain noise without external dependencies. Integer-hash based,
// so results are identical on every platform for a given seed.
#pragma once

#include <cstdint>
#include <cmath>
#include <algorithm>

namespace vc {

class Noise {
public:
    explicit Noise(std::uint64_t seed = 0) : seed_(seed) {}

    // 2D gradient noise in roughly [-1, 1].
    double value2D(double x, double y) const {
        const std::int32_t xi = fastFloor(x), yi = fastFloor(y);
        const double xf = x - static_cast<double>(xi), yf = y - static_cast<double>(yi);
        const double u = fade(xf), v = fade(yf);
        const double g00 = grad2(hash2(xi, yi), xf, yf);
        const double g10 = grad2(hash2(xi + 1, yi), xf - 1.0, yf);
        const double g01 = grad2(hash2(xi, yi + 1), xf, yf - 1.0);
        const double g11 = grad2(hash2(xi + 1, yi + 1), xf - 1.0, yf - 1.0);
        return lerp(lerp(g00, g10, u), lerp(g01, g11, u), v);
    }

    // 3D gradient noise in roughly [-1, 1].
    double value3D(double x, double y, double z) const {
        const std::int32_t xi = fastFloor(x), yi = fastFloor(y), zi = fastFloor(z);
        const double xf = x - xi, yf = y - yi, zf = z - zi;
        const double u = fade(xf), v = fade(yf), w = fade(zf);
        double acc[2];
        for (int iz = 0; iz < 2; ++iz) {
            double accY[2];
            for (int iy = 0; iy < 2; ++iy) {
                const double g00 = grad3(hash3(xi,     yi + iy, zi + iz), xf,     yf - iy, zf - iz);
                const double g10 = grad3(hash3(xi + 1, yi + iy, zi + iz), xf - 1, yf - iy, zf - iz);
                accY[iy] = lerp(g00, g10, u);
            }
            acc[iz] = lerp(accY[0], accY[1], v);
        }
        return lerp(acc[0], acc[1], w);
    }

    double fbm2D(double x, double y, int octaves, double lacunarity = 2.0, double gain = 0.5) const {
        double amp = 1.0, freq = 1.0, sum = 0.0, norm = 0.0;
        for (int i = 0; i < octaves; ++i) {
            sum += amp * value2D(x * freq, y * freq);
            norm += amp;
            amp *= gain; freq *= lacunarity;
        }
        return sum / norm;
    }

    double fbm3D(double x, double y, double z, int octaves, double lacunarity = 2.0, double gain = 0.5) const {
        double amp = 1.0, freq = 1.0, sum = 0.0, norm = 0.0;
        for (int i = 0; i < octaves; ++i) {
            sum += amp * value3D(x * freq, y * freq, z * freq);
            norm += amp;
            amp *= gain; freq *= lacunarity;
        }
        return sum / norm;
    }

private:
    static std::int32_t fastFloor(double v) {
        const std::int32_t i = static_cast<std::int32_t>(v);
        return (v < i) ? i - 1 : i;
    }
    static double fade(double t) { return t * t * t * (t * (t * 6.0 - 15.0) + 10.0); }
    static double lerp(double a, double b, double t) { return a + (b - a) * t; }

    std::uint64_t hash2(std::int32_t x, std::int32_t y) const {
        std::uint64_t h = seed_ ^ (static_cast<std::uint64_t>(static_cast<std::uint32_t>(x)) << 32) ^ static_cast<std::uint64_t>(static_cast<std::uint32_t>(y));
        h ^= h >> 33; h *= 0xFF51AFD7ED558CCDull; h ^= h >> 33; h *= 0xC4CEB9FE1A85EC53ull; h ^= h >> 33;
        return h;
    }
    std::uint64_t hash3(std::int32_t x, std::int32_t y, std::int32_t z) const {
        std::uint64_t h = seed_
            ^ (static_cast<std::uint64_t>(static_cast<std::uint32_t>(x)) * 0x9E3779B97F4A7C15ull)
            ^ (static_cast<std::uint64_t>(static_cast<std::uint32_t>(y)) * 0xC2B2AE3D27D4EB4Full)
            ^ (static_cast<std::uint64_t>(static_cast<std::uint32_t>(z)) * 0x165667B19E3779F9ull);
        h ^= h >> 33; h *= 0xFF51AFD7ED558CCDull; h ^= h >> 33; h *= 0xC4CEB9FE1A85EC53ull; h ^= h >> 33;
        return h;
    }
    static double grad2(std::uint64_t h, double x, double y) {
        switch (h & 7) {
            case 0: return  x + y; case 1: return  x - y; case 2: return -x + y; case 3: return -x - y;
            case 4: return  x;     case 5: return -x;     case 6: return  y;     default: return -y;
        }
    }
    static double grad3(std::uint64_t h, double x, double y, double z) {
        const std::uint64_t g = h & 15;
        const double u = (g < 8) ? x : y;
        const double v = (g < 4) ? y : ((g == 12 || g == 14) ? x : z);
        return ((g & 1) ? -u : u) + ((g & 2) ? -v : v);
    }

    std::uint64_t seed_;
};

} // namespace vc

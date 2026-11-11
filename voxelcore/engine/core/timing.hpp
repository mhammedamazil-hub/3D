// PROJECT VOXELCORE — steady-clock timing helpers for benchmarks and instrumentation.
#pragma once
#include <chrono>
#include <cstdint>

namespace vc {
class Stopwatch {
public:
    using Clock = std::chrono::steady_clock;
    void reset() { t0_ = Clock::now(); }
    double seconds() const { return std::chrono::duration<double>(Clock::now() - t0_).count(); }
    double millis() const { return seconds() * 1e3; }
    double micros() const { return seconds() * 1e6; }
private:
    Clock::time_point t0_ = Clock::now();
};
} // namespace vc

# Horizon Performance Baseline (reference, not measured locally)

**Honesty note:** Horizon was NOT built or run in this sandbox (no Rust toolchain; rustup hosts unreachable). All Horizon numbers below are taken from reports committed in the Horizon repository (`benchmarks/perf/`) and the project README, measured by the Horizon team on stated hardware. VOXELCORE numbers in `PERFORMANCE_REPORT.md` are our own measurements.

## Published machine: 2026-10-29/30, Windows 11, Ryzen 7 9800X3D + RTX 5080, 1280×720, fresh world seed 1234, mean of 4 scenes, VSync off, 3 games per figure (source: `benchmarks/perf/windows-9800x3d-5080-2026-10-29.md`, README)

| Render distance | Horizon v0.2.97 | Vanilla 26.3 | Vanilla + Sodium 0.9.2 / Lithium 0.26.2 / FerriteCore 9.0.0 / ImmediatelyFast 1.17.1 |
|---|---|---|---|
| 8 chunks | **3,289 FPS** (1% low 1,327) | 2,437 (640) | 2,375 (709) |
| 16 chunks | **2,074 FPS** (598) | 1,661 (375) | 1,586 (432) |
| 32 chunks | **1,207 FPS** (333) | 1,031 (176) | 879 (264) |

Startup to title screen: Horizon 2.9–3.2 s vs vanilla 7.5–7.7 s vs modded 10.8–11.1 s. Chunk load 2.9–3.8× faster. Working set 1.1–1.7 GB vs 1.9–2.9 GB. 1% lows improve more than means at RD 32 (333 vs 176) — horizon's scheduling, not just throughput.

## Method (so our comparisons are fair)

`tools/perf_bench.py` flies the camera over village/forest/ocean/mountain scenes in a fresh world (seed 1234), waits for terrain settle, measures with 1% lows, machine idle-gated (<15 % other-process CPU), discarded runs rerun. Full reports: `benchmarks/perf/windows-9800x3d-5080-rd{8,16,32}.json`, plus macOS M4 Pro/Mac mini reports.

## What this baseline means for VOXELCORE targets

- RD 8/16/32 parity with vanilla is the entry bar; beating Sodium-class modded vanilla is the credibility bar; approaching Horizon is the ambition bar.
- The gap between Horizon and vanilla at RD 32 comes mostly from: less CPU per frame (lock-free-ish scheduling, async light/mesh, vertex arena), less GPU work (packed records, side buckets, cave/leaf/GPU culling), and distant-terrain LOD removing far-chunk sim.
- **We will re-baseline on identical hardware once the Vulkan backend exists; until then all voxelcore perf claims are micro-benchmarks and mesh-count metrics only** (see `PERFORMANCE_REPORT.md`).

## Gaps in this baseline

- No Horizon GPU frame-time capture, no RenderDoc traces reviewed locally.
- Published numbers are one machine class; macOS numbers exist in-repo but are not reproduced here.
- We have not verified the benchmark methodology end-to-end; we trust but do not re-derive it.

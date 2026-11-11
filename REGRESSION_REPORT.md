# REGRESSION REPORT — PROJECT VOXELCORE

## 2026-11-11 — greedy mesher `used[]` initialization bug (fixed in-session)
Baseline symptom: `faceArea (1312) != naiveFaces (704)` on the flat-platform test; buried 9³ cube reported 438 quads instead of 6; tests caught it before commit.
Root cause: outer greedy-merge loop checked `mask.present` but not `used`, re-emitting already-merged cells as 1×1 quads. Fix: base-cell `used` check. Verified: 6-quad flat platform, 6-quad cube, invariant holds; suite 33,435 checks / 0 failures.
Correctness impact: rendering only (duplicate quads); no storage corruption. Lesson: the faceArea invariant is non-negotiable in CI.

## 2026-11-11 — frustum near/far plane sign (fixed in-session)
Baseline symptom: frustum rejected everything / kept nothing (depending on normal direction); unit test `testFrustumCulling` failed.
Root cause: near plane built as `-(row3+row2)` instead of `row3 - row2` after normalization (Gribb–Hartmann row convention). Fix: proper add/subtract per plane. Verified by dedicated test.

## 2026-11-11 — software-renderer mirrored image (fixed in-session)
Root cause: `right = (fwd.z, 0, -fwd.x)` flipped the image horizontally; corrected to `cross(fwd, worldUp)`. Verified visually (see voxelcore/sample_render.png).

## Process notes
No performance regressions were found in the two benchmarked runs; bench noise on shared runners exceeds E4's gain. CI runs the suite on every push.

## 2026-11-11 — Arena reset() dropped (not reused) the first block (fixed in-session)
ASan/UBSan run surfaced `p3 == p1` failure in `testArena` (Debug catches what Release didn't reveal). Root cause: `reset()` recreated a fresh first block instead of retaining it. Fix: keep `blocks_[0]`, erase the rest. Verified: ASan build 33,435/0 failures; Release unchanged.

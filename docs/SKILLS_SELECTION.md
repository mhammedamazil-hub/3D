# Skill selection — PROJECT VOXELCORE (2026-11-11)

Requested: use the `find-skills` skill to find skills suitable for this project.

## What find-skills does

The `find-skills` skill (iizcm/find-skills-skill, MIT) directs to the open agent skills ecosystem:
search via `npx skills find <query>`, verify install count / source reputation / stars, inspect before installing.

## What we found

- The skills.sh registry backend returns **zero results for every query** tried from this environment
  (c++, cpp, vulkan, graphics, rendering, performance, cmake, game, shader, android, testing, code review,
  security, documentation, github actions, rust, optimization, and even react). The registry API route
  appears unreachable/empty here (skills.sh is not on this sandbox's allowed host list).
- We then searched GitHub directly (`gh search`) for the named candidates from the project brief
  (Superpowers, Everything Claude Code) and for C++-relevant skills.

## What we installed (all MIT, all inspected pre-install; 156 KB total, in `.agents/skills/`)

| Skill | Source | Why it fits VOXELCORE |
|---|---|---|
| cpp-coding-standards | ECC (300k★) | C++ Core Guidelines review/authoring — our whole codebase |
| cpp-testing | ECC | CTest/GoogleTest/sanitizer workflows — matches our CI |
| benchmark-optimization-loop | ECC | Baseline → one-hypothesis variants → correctness gate → promote; exactly our E-catalog discipline |
| architecture-decision-records | ECC | Matches our docs/ARCHITECTURE_DECISIONS.md practice |
| verification-loop | ECC | Six-phase session verification — aligns with CI/ASan gates |
| security-review | ECC | Skill files run with agent permissions; review discipline for repo/CI changes |
| verification-before-completion | Superpowers (315k★) | Evidence-before-claims; enforces run-tests-before-"done" |
| systematic-debugging | Superpowers | Root-cause-first; complements our REGRESSION_REPORT.md process |
| test-driven-development | Superpowers | RED→GREEN→REFACTOR for engine features |

## What we rejected and why

- `android-clean-architecture` (ECC) — Kotlin/KMP/Room/Ktor mobile architecture; VOXELCORE Android is NDK/C++ (ADR-011).
- `benchmark-methodology` (ECC) — competitive-positioning marketing benchmarks, not engine benchmarking. ECC's `benchmark-optimization-loop` is the right one and was installed.
- `latency-critical-systems` (ECC) — HFT/streaming-specific; its p50/p95/p99 discipline is already covered by our PERFORMANCE_REPORT methodology.
- `writing-plans` (Superpowers) — our DEVELOPMENT_STATUS.md + REIMPLEMENTATION_PLAN.md already encode the plan-of-record; adding a second planning layer would duplicate it.
- Any skill claiming Vulkan/graphics expertise — **none exist** in the registry or in ECC/Superpowers feature lists; graphics work remains expert-driven (see RESEARCH_REPORT.md).

## Notes & caveats

- Skills are reference documents, not code we execute; `systematic-debugging/find-polluter.sh` is a benign
  test-bisection utility (inspected). No lifecycle scripts run at install or runtime.
- Install command used: `npx skills add <owner/repo@skill> -y` (project-local install, not global).
- Registry search returning zero results means this list should be re-checked when skills.sh is reachable.

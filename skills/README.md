# Installed skill library

## realistic-blender-production/

The production-method skill attached by the user on 2026-11-07 (`SKILL.md`,
verbatim copy). It governs the full loop: brief → audit → blockout → lookdev →
tests → frozen scene → resumable render → independent verification → delivery.

## blender-skills/

Companion specialist library, installed per the production skill §2.

- Upstream: https://github.com/arjun988/blender-skills
- Pinned commit: `8f778d2405a214b508d4c7d80742be8e43acdd52` (2026-07-10, v1.3.0)
- License: MIT (retained verbatim in `blender-skills/LICENSE`)
- Contents: **94 specialist skills** + shared `references/` directory
  (`.claude/skills/<name>/SKILL.md`), 175 reference documents
- Installed as a plain copy (upstream `.git` removed); no local skills existed
  to overwrite. Do not edit in place — treat as vendored upstream.

Key specialists for realistic work (all present): `blender-director`,
`blender-modeler`, `environment-artist`, `vegetation-artist`, `materials`,
`lighting`, `realistic-style`, `camera-cinematography`, `animation`,
`geometry-nodes`, `vfx-fx`, `rendering`, `compositing`, `asset-optimization`,
`qa-review`.

Read only the relevant specialist for the task; supplier examples are guidance,
not authority over the user's brief or this sandbox's measured limits.
